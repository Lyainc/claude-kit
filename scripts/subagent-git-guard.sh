#!/usr/bin/env bash
# claude-kit work-rules — subagent git side-effect guard (PreToolUse Bash hook, #209).
#
# Enforces rules/RULES.md §1 "Subagents do not cause git side effects": a subagent
# (Workflow agent(), Agent/Task) leaves its changes in the working tree — it does NOT
# commit, push, or create/merge PRs. The MAIN CONTEXT owns git. #209 recorded a real
# recurrence: an executor subagent ignored an explicit "Do NOT commit" prompt and
# committed + pushed + opened PR #205. The prompt-level contract alone was not enough,
# so this deterministic guard is the HARD enforcement (rules/RULES.md §2 POLICY — the
# violation is OBJECTIVE DAMAGE: a broken isolated-critique premise plus an unapproved
# outward-facing publish).
#
# Fires on every PreToolUse Bash call. It acts ONLY when the call carries a subagent
# identifier; a main-context call (no identifier) is always allowed, because the main
# context owns git. It then blocks git commit / git push / gh pr create / gh pr merge
# inside that command. Reads (status, log, diff, show, ...) are never blocked.
#
# Scope (honest-subagent threat model): it flags git/gh only in COMMAND POSITION (the verb
# being run), not when "git push" appears as an argument — so `echo git push`, `man git
# commit`, `grep "git push" f` are NOT flagged. It catches the realistic direct forms —
# git commit/push and gh pr create/merge, including &&/||/;/| chaining, a trailing
# background &, subshell/brace grouping and $(...) command substitution (the inner verb is
# exposed by the segmenter), a full-path / sudo / env-assignment / time-style prefix, git
# global value-options (git -C / -c ...), gh global value-options (gh -R / --repo ...), and
# backslash-newline line continuations. It deliberately does NOT try to defeat arbitrary
# indirection (eval, sh -c "...", backticks, a shell-function wrapper, xargs): the target
# is an honest LLM subagent that ignored a prose "Do NOT commit" contract (#209), not a
# deliberate adversary, and those forms cannot be caught statically without false
# positives. Those residual gaps are encoded as KNOWN_EVASIONS in the regression test.
#
# CON-2 (deterministic hook, zero per-turn LLM cost): pure shell plus a small inline
# python tokenizer for the git/gh subcommand parse. No LLM call, no loop risk.
#
# Modes (CLAUDE_KIT_SUBAGENT_GIT_CONTRACT, default enforce):
#   enforce — deny the Bash call (permissionDecision:deny) + systemMessage.
#   warn    — allow, but emit a systemMessage + stderr warning.
#   off     — skip entirely.
# Kill switch: CLAUDE_KIT_SUBAGENT_GIT_DISABLE=1 (skip entirely).
#
# Wiring (per-developer, by design — .claude/ is gitignored): this handler is committed
# under scripts/ (shared, no external-orchestrator dependency) but activated locally by
# adding it to your own .claude/settings.json (mirrors rules/RULES.md §4 reminder hook):
#   { "hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [ { "type": "command",
#       "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/subagent-git-guard.sh\"" } ] } ] } }
#
# Performance: short-circuits before invoking python3 — it exits cheaply when there is
# no subagent identifier or the command mentions neither `git` nor `gh`.

set -uo pipefail

# Kill switch.
[ "${CLAUDE_KIT_SUBAGENT_GIT_DISABLE:-0}" = "1" ] && exit 0

mode="${CLAUDE_KIT_SUBAGENT_GIT_CONTRACT:-enforce}"
[ "$mode" = "off" ] && exit 0

# jq is required to parse the payload; without it, fail OPEN (never break the session).
command -v jq >/dev/null 2>&1 || exit 0

payload=$(cat 2>/dev/null || true)

# Only act on Bash tool calls.
tool_name=$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null || true)
[ "$tool_name" = "Bash" ] || exit 0

# Subagent identity: act ONLY when a subagent identifier is present. Main context (no
# identifier) owns git and is always allowed. Same fields as vault-bridge pre-write-guard.
agent_id=$(printf '%s' "$payload" | jq -r '
  .agent_name // .subagent_type // .agent.name // .agent.type // .attributionAgent // empty
' 2>/dev/null || true)
[ -n "$agent_id" ] || exit 0

# The command under inspection.
command_str=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
[ -n "$command_str" ] || exit 0

# Cheap pre-filter: if neither `git` nor `gh` appears at all, there is nothing to guard.
# (Loose substring match: a hit only routes to the precise python parser below — it never
# blocks on its own, so a false pre-filter hit costs one python3 call, not a false deny.)
case "$command_str" in
  *git*|*gh*) : ;;
  *) exit 0 ;;
esac

# Precise detection: tokenize each &&/||/;/|/()/{}-delimited segment, find the git/gh
# subcommand (skipping git global options that take a value), and flag only
# commit / push / gh pr create / gh pr merge. Emits the matched verb on stdout (empty =
# no violation). python3 keeps the parse portable across macOS/Linux.
verb=$(printf '%s' "$command_str" | python3 -c '
import re, sys

cmd = sys.stdin.read()
# Join backslash-newline line continuations first (the shell collapses them to a space),
# so a verb split across lines (git \<newline> push) is not torn apart by the segmenter.
cmd = cmd.replace("\\\n", " ")
# Split into command segments on shell separators; never cross these boundaries. A lone
# "&" (background) is a boundary too, so a glued "git push&" still tokenizes cleanly; the
# "&&" alternation is tried first, so chaining is not mis-split into empty operators.
segments = re.split(r"&&|\|\||[;\n|&(){}]", cmd)

# git global options that consume the NEXT token as their value.
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"}
# gh global options that consume the NEXT token as their value (may precede the subcommand).
GH_VALUE_OPTS = {"-R", "--repo"}
# Wrapper commands / shell keywords that PREFIX a real command (they run or gate what
# follows), so the guarded verb may legitimately sit after them. A leading run of these —
# plus FOO=bar env-assignments — is skipped to find the actual command in the segment. Match
# on COMMAND POSITION (git/gh must be the command, not an argument), so `echo git push`,
# `man git commit`, `grep "git push" f` are NOT flagged, while `sudo git push`,
# `env X=1 git commit`, `time git push` still are. Indirection wrappers that take the
# command as data (eval, sh -c, xargs, backticks) are intentionally NOT prefixes — they are
# the documented KNOWN_EVASIONS (honest-subagent threat model, see the test).
PREFIXES = {"sudo", "env", "command", "exec", "time", "nice", "ionice", "nohup", "stdbuf",
            "setsid", "builtin", "if", "then", "elif", "else", "while", "until", "do", "!"}

def base(tok):
    return tok.rsplit("/", 1)[-1]

def is_assignment(tok):
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok) is not None

found = ""
for seg in segments:
    toks = seg.split()
    n = len(toks)
    # Advance to the command position: skip leading wrapper-prefixes + env-assignments.
    i = 0
    while i < n and (base(toks[i]) in PREFIXES or is_assignment(toks[i])):
        i += 1
    if i >= n:
        continue
    b = base(toks[i])
    if b == "git":
        j = i + 1
        while j < n and toks[j].startswith("-"):
            j += 2 if toks[j] in GIT_VALUE_OPTS else 1
        if j < n and toks[j] in ("commit", "push"):
            found = "git " + toks[j]
            break
    elif b == "gh":
        # Skip leading global options (consuming a value for -R/--repo) the same way the
        # git branch does, so a flag BEFORE the subcommand (gh -R o/r pr create) is caught,
        # not just the flag-after form (gh pr create -R o/r).
        j = i + 1
        while j < n and toks[j].startswith("-"):
            j += 2 if toks[j] in GH_VALUE_OPTS else 1
        if j + 1 < n and toks[j] == "pr" and toks[j + 1] in ("create", "merge"):
            found = "gh pr " + toks[j + 1]
            break

sys.stdout.write(found)
' 2>/dev/null || true)

[ -n "$verb" ] || exit 0

# ---------------------------------------------------------------------------
# Violation: a subagent attempted a git side effect.
# ---------------------------------------------------------------------------
reason="Subagent ($agent_id) attempted '$verb' — subagents do NOT commit/push/create PRs (rules/RULES.md §1, #209). Leave changes in the working tree; the main context owns git. To publish, hand the diff back to the main context and let the user run git."

if [ "$mode" = "warn" ]; then
  printf '[subagent-git-guard] CONTRACT WARNING: %s\n' "$reason" >&2
  jq -nc --arg msg "$reason" \
    '{systemMessage: ("subagent-git-guard: " + $msg + " Set CLAUDE_KIT_SUBAGENT_GIT_CONTRACT=enforce to block, =off to disable.")}'
  exit 0
fi

# enforce (default): deny the Bash call. permissionDecision/permissionDecisionReason must
# nest under hookSpecificOutput (documented PreToolUse schema) — a top-level
# permissionDecision is silently ignored by Claude Code and the call goes through anyway.
# systemMessage stays top-level so the revert/disable hint still lands in the transcript.
jq -nc --arg reason "$reason" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason:$reason}, systemMessage:("subagent-git-guard: " + $reason + " Set CLAUDE_KIT_SUBAGENT_GIT_CONTRACT=warn to allow, =off to disable.")}'
exit 0
