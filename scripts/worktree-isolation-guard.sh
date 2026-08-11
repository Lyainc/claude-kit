#!/usr/bin/env bash
# claude-kit work-rules — worktree isolation guard (PreToolUse Write|Edit hook, #594).
#
# Enforces rules/RULES.md §1 "Concurrent work goes in an isolated git worktree (#234)"
# — the claude-kit-concrete form of machine work-rule P1. Until #594 that rule had NO
# deterministic guard at all: enforcement was the prose rule plus the §4 self-check.
#
# WHAT IT CATCHES (and what it does not). #594's 8th recorded near-miss was a NEW shape:
# not two sessions colliding, but ONE session that never isolated itself — it edited the
# shared MAIN CHECKOUT on the DEFAULT BRANCH for several commits, and was found only by a
# stray `git status --short`. No hook, no warning, nothing. That shape IS deterministically
# detectable, which is why it gets a guard while P1's general question stays SOFT:
#   "is another session working this repo right now?"  → judgment, NOT detectable (SOFT).
#   "am I writing the main checkout on its default branch?" → two git commands, no judgment.
# So this guard answers only the second question. It is the self-isolation half of P1;
# the sibling-occupancy half is #594's claim-file proposal and is deliberately NOT here.
#
# KNOWN GAP (deliberate, same honest-slip threat model as the sibling guards): a write to
# the main checkout while it sits on a FEATURE branch is not flagged. That is #594's
# original incident shape, but it is also ordinary solo work in the main checkout, so
# flagging it would fire on the legitimate case with no way to tell them apart. Closing it
# needs the claim file (who else is live right now), not a branch comparison.
#
# Fires on every PreToolUse Write|Edit. It acts ONLY when the target file resolves inside a
# working tree that is the MAIN checkout (git-dir == git-common-dir; a linked worktree's
# differ) OF THE REPOSITORY THIS SESSION IS WORKING ($CLAUDE_PROJECT_DIR's, compared by common
# dir so a session inside a worktree still matches its own main checkout), while that checkout
# is on its DEFAULT branch (origin/HEAD, else main, else master), and only for a path git does
# not ignore. Deterministic shell — zero per-turn LLM cost (CON-2). Fails OPEN when jq or git
# is absent (a missing tool must never block a legitimate write).
#
# Mode (env): CLAUDE_KIT_WORKTREE_GUARD = warn (default) | enforce | off.
#   warn    — allow, emit a systemMessage + stderr warning. DEFAULT, because P1 is SOFT:
#             a false block costs a real session (same reasoning as worktree-collision-warn).
#   enforce — deny the write (permissionDecision:deny) + systemMessage.
#   off     — no-op.
#
# The WARNING fires once per (session, repo): the isolation decision is made once, and a
# per-write repeat trains the reader to ignore exactly the line that matters. A payload
# without `.session_id` gets no dedup (warn every time) rather than a silent guard. A DENY is
# never deduped — an agent answers one deny by re-issuing the identical Write.
#
# Wiring (per-developer; .claude/ is gitignored — NOT auto-registered):
#   { "hooks": { "PreToolUse": [ { "matcher": "Write|Edit", "hooks": [ { "type": "command",
#       "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/worktree-isolation-guard.sh\"" } ] } ] } }
# Wire it in the MAIN checkout's .claude/settings.json — that is the checkout it protects.

set -uo pipefail

MODE="${CLAUDE_KIT_WORKTREE_GUARD:-warn}"
[ "$MODE" = "off" ] && exit 0

# An inherited GIT_DIR/GIT_WORK_TREE outranks `git -C`, which would silently point every
# lookup below at the wrong repository (a linked worktree read as the main checkout).
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE

# jq / git absent → fail open (never block a write because a tool is missing).
command -v jq >/dev/null 2>&1 || exit 0
command -v git >/dev/null 2>&1 || exit 0

PAYLOAD="$(cat 2>/dev/null || printf '{}')"
[ -n "$PAYLOAD" ] || PAYLOAD='{}'

RAW_PATH="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
[ -n "$RAW_PATH" ] || exit 0

CWD="$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null || true)"
[ -n "$CWD" ] || CWD="$PWD"

# Expand ~, then resolve a relative path against the session cwd.
ABS="${RAW_PATH/#\~/${HOME:-}}"
case "$ABS" in /*) ;; *) ABS="$CWD/$ABS" ;; esac

# The file may not exist yet (Write creates it), and neither may its parent chain — walk up
# to the nearest existing directory, which is what git must be asked about.
DIR="$(dirname "$ABS")"
while [ ! -d "$DIR" ] && [ "$DIR" != "/" ]; do DIR="$(dirname "$DIR")"; done
[ -d "$DIR" ] || exit 0

# No working tree to isolate → nothing this rule can be about. Rules out a bare repo and a
# write inside .git/ itself (a git-hook install), where --git-dir and --git-common-dir both
# answer "." and would otherwise compare equal as if it were a main checkout.
git -C "$DIR" rev-parse --is-inside-work-tree 2>/dev/null | grep -qx true || exit 0

# Normalize both git dirs the same way (cd + pwd -P) so a symlinked TMPDIR or repo path
# cannot make an identical pair compare unequal.
GITDIR="$(cd "$DIR" 2>/dev/null && cd "$(git rev-parse --git-dir 2>/dev/null)" 2>/dev/null && pwd -P)" || exit 0
[ -n "$GITDIR" ] || exit 0
COMMONDIR="$(cd "$DIR" 2>/dev/null && cd "$(git rev-parse --git-common-dir 2>/dev/null)" 2>/dev/null && pwd -P)" || exit 0
[ -n "$COMMONDIR" ] || exit 0

# Linked worktree → already isolated, which is the whole point of the rule. Nothing to say.
[ "$GITDIR" = "$COMMONDIR" ] || exit 0

# Only the repository THIS session is working. Without this the guard fires on every other
# repo the session happens to write — `~/vault` above all, which is a git repo on its default
# branch that /vault-save writes to routinely, and where `git worktree add` is no remedy at
# all. The common dir is the right identity: a session running inside a linked worktree still
# resolves to the same repository as the main checkout it must not write.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$CWD}"
PROJECT_COMMONDIR="$(cd "$PROJECT_DIR" 2>/dev/null && cd "$(git rev-parse --git-common-dir 2>/dev/null)" 2>/dev/null && pwd -P)" || exit 0
[ -n "$PROJECT_COMMONDIR" ] || exit 0
[ "$COMMONDIR" = "$PROJECT_COMMONDIR" ] || exit 0

# Detached HEAD → symbolic-ref fails → not on a branch, so not on the default branch.
BRANCH="$(git -C "$DIR" symbolic-ref --short -q HEAD 2>/dev/null || true)"
[ -n "$BRANCH" ] || exit 0

# Default branch: origin/HEAD is authoritative when present; else the conventional names.
DEFAULT="$(git -C "$DIR" symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null || true)"
DEFAULT="${DEFAULT#origin/}"
if [ -z "$DEFAULT" ]; then
  for c in main master; do
    if git -C "$DIR" show-ref --verify -q "refs/heads/$c"; then DEFAULT="$c"; break; fi
  done
fi
[ -n "$DEFAULT" ] || exit 0
[ "$BRANCH" = "$DEFAULT" ] || exit 0

# A git-ignored path is local state (.claude/settings.json, scratch output), not repo work.
git -C "$DIR" check-ignore -q "$ABS" 2>/dev/null && exit 0

TOPLEVEL="$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$DIR")"

MSG="P1 워크트리 격리 위반 가능성: 메인 체크아웃($TOPLEVEL)의 기본 브랜치($DEFAULT)에 직접 쓰고 있어요. 동시 작업 중이라면 다른 세션과 서로를 덮어씁니다 — 전용 워크트리에서 작업하세요 (git worktree add). CLAUDE_KIT_WORKTREE_GUARD=enforce로 차단, =off로 끄기."

# enforce denies EVERY offending write. Dedup below is a warn-mode concern only: a deny that
# fired once and then went quiet is worse than no guard, because the agent simply re-issues
# the identical Write and it lands.
if [ "$MODE" = "enforce" ]; then
  printf '[worktree-isolation-guard] %s\n' "$MSG" >&2
  # permissionDecision/permissionDecisionReason must nest under hookSpecificOutput
  # (documented PreToolUse schema) — a top-level permissionDecision is silently ignored
  # by Claude Code and the write goes through anyway. systemMessage stays top-level.
  jq -nc --arg m "$MSG" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason:$m}, systemMessage:("worktree-isolation-guard: " + $m)}'
  exit 0
fi

# Once per (session, repo). No session_id → no dedup, rather than a permanently silent guard.
SID="$(printf '%s' "$PAYLOAD" | jq -r '.session_id // empty' 2>/dev/null || true)"
if [ -n "$SID" ]; then
  KEY="$(printf '%s|%s' "$SID" "$COMMONDIR" | shasum 2>/dev/null | cut -c1-16)"
  if [ -n "$KEY" ]; then
    MARKER="${TMPDIR:-/tmp}/claude-kit-worktree-guard.$KEY"
    [ -e "$MARKER" ] && exit 0
    : >"$MARKER" 2>/dev/null || true
  fi
fi

printf '[worktree-isolation-guard] %s\n' "$MSG" >&2
jq -nc --arg m "$MSG" '{systemMessage: ("worktree-isolation-guard: " + $m + " 이 경고는 세션·저장소당 한 번만 뜹니다.")}'
exit 0
