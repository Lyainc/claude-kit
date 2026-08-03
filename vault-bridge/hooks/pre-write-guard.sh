#!/usr/bin/env bash
# vault-bridge PreToolUse hook — Write Role Contract + vault file naming guard.
#
# Fires on every Write/Edit/Bash tool call.
#   Write|Edit — if the target path resolves to inside ~/vault/, enforce the Write Role
#                Contract (no subagent writes) and validate the filename convention.
#   Bash       — enforce the Write Role Contract ONLY (#381): the Write|Edit matcher alone
#                left the contract bypassable, since a subagent holding Bash could write the
#                vault with `echo > ~/vault/x.md`, `mv`, `tee`. Same command-position
#                detection discipline as scripts/subagent-git-guard.sh (#209).
#
# Default mode (log-only): exit 0 always; warnings emitted to stderr and
# injected as a systemMessage. Never blocks user workflow.
#
# Strict mode (VAULT_BRIDGE_STRICT_NAMING=1): exit 2 on violation; stderr
# contains the expected pattern. Blocks the write.
#
# Environment variables:
#   VAULT_BRIDGE_DISABLE=1          — skip entirely (kill switch)
#   VAULT_BRIDGE_STRICT_NAMING=1    — enable blocking mode (default: log-only)
#   VAULT_BRIDGE_VAULT_ROOT=PATH    — explicit env override (highest priority)
#   VAULT_BRIDGE_VAULT_PATH=PATH    — userConfig vault path (set by Claude Code plugin settings)
#
# Performance target: <50ms

set -uo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-}" = "1" ]; then
  exit 0
fi

# Read the PreToolUse JSON payload from stdin
payload=$(cat)

# Extract tool_name
tool_name=$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null || true)

# Only act on Write, Edit and Bash
case "$tool_name" in
  Write|Edit|Bash) ;;
  *) exit 0 ;;
esac

# Resolve vault root: VAULT_BRIDGE_VAULT_ROOT (env override) >
# VAULT_BRIDGE_VAULT_PATH (userConfig, set by Claude Code) > $HOME/vault (default).
_raw_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_raw_vr" ] && _raw_vr="${HOME}/vault"
VAULT_ROOT="${_raw_vr/#\~/$HOME}"
unset _raw_vr

# Vault must exist; CI/remote environments without vault → silent exit
if [ ! -d "$VAULT_ROOT" ]; then
  exit 0
fi

# Resolve vault root to absolute path (handle symlinks)
vault_abs=$(cd "$VAULT_ROOT" 2>/dev/null && pwd -P) || exit 0

# ---------------------------------------------------------------------------
# Write Role Contract — shared by the Write/Edit and Bash paths.
# Policy: vault writes must originate from main context (user-initiated slash
# commands). Subagent vault writes are out of policy.
# Modes: enforce (default — deny), warn (log + systemMessage, allow), off (skip).
# assets/ is a passthrough — no contract check (automated tools may write attachments).
# Subagent identity fields mirror scripts/subagent-git-guard.sh; no identifier = main
# context, which owns vault writes and is always allowed.
# ---------------------------------------------------------------------------
contract_mode="${VAULT_BRIDGE_WRITE_CONTRACT:-enforce}"
agent_id=$(printf '%s' "$payload" | jq -r '
  .agent_name // .subagent_type // .agent.name // .agent.type // .attributionAgent // empty
' 2>/dev/null || true)

# Emit the contract decision (deny in enforce mode, systemMessage in warn mode).
emit_contract_violation() {
  local detail="$1"
  local msg="Vault writes must be user-initiated slash commands (/vault-save, /vault-commit). Subagent ($agent_id) vault write blocked${detail}. To author content from a subagent, return a draft to the main context and let the user invoke a slash command."

  if [ "$contract_mode" = "enforce" ]; then
    # Emit both permissionDecisionReason (for the deny dialog) AND systemMessage
    # (so the user actually sees the revert/disable hint in their transcript).
    jq -nc --arg reason "$msg" \
      '{permissionDecision:"deny", permissionDecisionReason:$reason, systemMessage:("vault-bridge contract: " + $reason + " Set VAULT_BRIDGE_WRITE_CONTRACT=warn to allow, =off to disable.")}'
  else
    printf '[vault-bridge pre-write-guard] CONTRACT WARNING: %s\n' "$msg" >&2
    jq -nc --arg msg "$msg" \
      '{systemMessage: ("vault-bridge contract: " + $msg + " Set VAULT_BRIDGE_WRITE_CONTRACT=enforce to block, =off to disable.")}'
  fi
}

# ---------------------------------------------------------------------------
# Bash path (#381) — contract check only.
#
# Deliberate scope limit: no filename-convention validation on Bash writes. One command
# can name many targets, and in the default enforce mode the contract denies before a name
# would matter; add per-target naming checks only if a warn-mode Bash write is ever
# observed landing a non-conforming filename.
# ---------------------------------------------------------------------------
if [ "$tool_name" = "Bash" ]; then
  [ "$contract_mode" = "off" ] && exit 0
  [ -n "$agent_id" ] || exit 0

  command_str=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
  [ -n "$command_str" ] || exit 0

  cwd=$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null || true)

  # Cheap pre-filter: any command that reaches the vault must name it (its root's
  # basename appears in every absolute/~/$HOME form) — unless the call already runs
  # from inside the vault, where a bare relative path suffices.
  case "$command_str" in
    *"$(basename "$vault_abs")"*) : ;;
    *)
      case "${cwd:-}" in
        "$vault_abs"|"$vault_abs"/*) : ;;
        *) exit 0 ;;
      esac
      ;;
  esac

  # Precise detection: tokenize quote-aware (shlex, non-POSIX so a quoted ">" stays
  # quoted and is NOT a redirection), split into shell segments, and flag only writes
  # whose TARGET resolves inside the vault. Reads pass: `grep -r x ~/vault`,
  # `cat ~/vault/x.md`, `cd ~/vault && git status`, `cp ~/vault/x.md /tmp/` (vault is
  # the source, not the destination).
  #
  # Threat model = honest subagent that ignored the prose contract (same as #209), not
  # an adversary. Deliberately NOT defeated: indirection (eval, sh -c, backticks,
  # xargs, `python3 -c "open(...)"`) and $(...)-computed paths. Those cannot be caught
  # statically without false positives; they are the documented KNOWN_EVASIONS in
  # scripts/test/test-pre-write-guard.py.
  target=$(printf '%s' "$command_str" | VB_VAULT_ABS="$vault_abs" VB_CWD="${cwd:-}" python3 -c '
import os, re, shlex, sys

VAULT = os.environ["VB_VAULT_ABS"]
cwd = os.environ.get("VB_CWD") or os.getcwd()
cmd = sys.stdin.read()

SEPS = {";", "&&", "||", "|", "&", "(", ")", "{", "}", "\n"}
# Output redirections. shlex(punctuation_chars=True) merges a contiguous run of ();<>|&
# into ONE token, so the compound Bash forms arrive glued: `&>`, `&>>`, `>&`, `>|`. They
# are ordinary idioms an honest subagent reaches for (`script.sh &> ~/vault/log.md`), so
# missing them left the whole guard open — cover every token whose operator part contains
# a `>`, with an optional fd digit and/or `&` in front.
REDIR = re.compile(r"^(\d*&?>>?\|?|>&)$")
# Wrapper/keyword prefixes that precede a real command (mirrors subagent-git-guard.sh).
PREFIXES = {"sudo", "env", "command", "exec", "time", "nice", "ionice", "nohup", "stdbuf",
            "setsid", "builtin", "if", "then", "elif", "else", "while", "until", "do", "!"}
# Writers whose destination is the LAST positional arg (earlier ones are sources).
DEST_LAST = {"mv", "cp", "rsync", "install", "ln"}
# Writers where EVERY positional arg is a target.
DEST_ALL = {"tee", "touch", "mkdir", "rmdir", "rm", "truncate", "sed"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# chr(39) is the single quote: this whole program is embedded in a shell -c
# single-quoted string, so a literal one cannot appear anywhere below.
QUOTES = chr(34) + chr(39)

def unquote(t):
    return t[1:-1] if len(t) > 1 and t[0] == t[-1] and t[0] in QUOTES else t

def resolve(tok, base):
    t = unquote(tok)
    if not t or t.startswith("-"):
        return None
    return os.path.realpath(os.path.join(base, os.path.expanduser(os.path.expandvars(t))))

def in_vault(tok, base):
    p = resolve(tok, base)
    if p is None:
        return None
    if p != VAULT and not p.startswith(VAULT + os.sep):
        return None
    # assets/ passthrough — attachments are exempt from the contract.
    rel = os.path.relpath(p, VAULT)
    if rel.split(os.sep)[0] == "assets":
        return None
    return p

try:
    lex = shlex.shlex(cmd, posix=False, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
except ValueError:
    sys.exit(0)  # unbalanced quotes — fail open

segments, cur = [], []
for t in toks:
    if t in SEPS:
        segments.append(cur)
        cur = []
    else:
        cur.append(t)
segments.append(cur)

found = ""
for seg in segments:
    if found:
        break
    if not seg:
        continue
    # Redirection anywhere in the segment: `> path`, `>> path`, `2> path`.
    for i, t in enumerate(seg):
        if REDIR.match(t) and i + 1 < len(seg):
            hit = in_vault(seg[i + 1], cwd)
            if hit:
                found = hit
                break
    if found:
        break
    # Command position: skip wrapper prefixes and FOO=bar assignments.
    i = 0
    while i < len(seg) and (os.path.basename(unquote(seg[i])) in PREFIXES or ASSIGN.match(seg[i])):
        i += 1
    if i >= len(seg):
        continue
    verb = os.path.basename(unquote(seg[i]))
    args = seg[i + 1:]
    positional = [a for a in args if not a.startswith("-")]

    # `cd` inside the command moves the base for later segments relative paths resolve against.
    if verb == "cd":
        if positional:
            p = resolve(positional[0], cwd)
            if p:
                cwd = p
        continue
    # sed only writes with -i.
    if verb == "sed" and not any(a.startswith("-i") for a in args):
        continue
    # dd writes to of=PATH.
    if verb == "dd":
        for a in args:
            if a.startswith("of="):
                hit = in_vault(a[3:], cwd)
                if hit:
                    found = hit
                    break
        continue
    if verb in DEST_LAST:
        # GNU coreutils -t DIR / --target-directory=DIR moves the destination OUT of the
        # last-positional slot (every positional is then a source), so check the flag first.
        targets = []
        # rsync -t/--times is a boolean (preserve timestamps) with no target-directory
        # equivalent at all — unlike mv/cp/install/ln, none of -t/-tDIR/--target-directory
        # is ever a destination there, so rsync is excluded from every prong below.
        if verb != "rsync":
            for k, a in enumerate(args):
                if a in ("-t", "--target-directory") and k + 1 < len(args):
                    targets = [args[k + 1]]
                elif a.startswith("--target-directory="):
                    targets = [a.split("=", 1)[1]]
                elif a.startswith("-") and not a.startswith("--") and len(a) > 1 and "t" in a[1:]:
                    # GNU getopt: a value-taking short option must be the last flag in
                    # its cluster. Whatever follows "t" in the same token is its inline
                    # value (-tDIR); if "t" is the last char, the value is the next
                    # token (-rt DIR, -vt DIR).
                    # KNOWN GAP (#401, same non-adversarial threat model as the Bash
                    # KNOWN_EVASIONS below): a cluster where another value-taking short
                    # flag precedes "t" (cp -St, cp -Zt) actually hands the remainder to
                    # THAT flag under real getopt, not to -t. No caller in this repo
                    # builds such a cluster, so it is left undetected rather than modeled.
                    idx = a.index("t", 1)
                    rest = a[idx + 1:]
                    if rest:
                        targets = [rest]
                    elif k + 1 < len(args):
                        targets = [args[k + 1]]
        if not targets:
            targets = positional[-1:]
    elif verb in DEST_ALL:
        targets = positional
    else:
        continue
    for a in targets:
        hit = in_vault(a, cwd)
        if hit:
            found = hit
            break

sys.stdout.write(found)
' 2>/dev/null || true)

  [ -n "${target:-}" ] || exit 0

  emit_contract_violation " — command writes to ${target#"$vault_abs"/} via Bash"
  exit 0
fi

# Extract file_path from tool_input
tool_input=$(printf '%s' "$payload" | jq -r '.tool_input // {}' 2>/dev/null || echo '{}')
raw_path=$(printf '%s' "$tool_input" | jq -r '.file_path // empty' 2>/dev/null || true)

if [ -z "${raw_path:-}" ]; then
  exit 0
fi

# Expand ~ and resolve to absolute path (python3 handles missing paths + symlinks)
abs_path=$(python3 -c "import os,sys; p=sys.argv[1]; print(os.path.realpath(os.path.expanduser(p)))" "$raw_path" 2>/dev/null || true)

if [ -z "${abs_path:-}" ]; then
  exit 0
fi

# Check if path is inside vault root
case "$abs_path" in
  "$vault_abs"/*|"$vault_abs")
    : # path is inside vault — proceed to validation
    ;;
  *)
    exit 0
    ;;
esac

# Derive relative path + top-level directory from vault root
rel_path="${abs_path#"$vault_abs"/}"
top_dir=$(printf '%s' "$rel_path" | cut -d'/' -f1)

# ---------------------------------------------------------------------------
# Write Role Contract enforcement (Write/Edit path — see the shared block above)
# ---------------------------------------------------------------------------
if [ "$contract_mode" != "off" ] && [ -n "$agent_id" ] && [ "$top_dir" != "assets" ]; then
  emit_contract_violation ""
  # enforce: the deny decision is final. warn: fall through to filename validation.
  [ "$contract_mode" = "enforce" ] && exit 0
fi

# Extract filename (basename)
filename=$(basename "$abs_path")

# ---------------------------------------------------------------------------
# Whitelist — always allowed regardless of directory
# Matches: _index.md, Home.md, home.md
#
# _index.md is the structural vault/folder index — it mirrors audit-validate.py
# `filename_conforms`/`EXEMPT_FILES` (always valid at any path) and is NOT a MOC
# remnant. Kept consistent with audit-validate.py `filename_conforms`.
#
# The hand-written MOC pattern (moc-*.md) was retired per v4 §9.5 (#166): MOC is
# rejected as a separate slot and #118 `.base` views replace hand-written MOC.
# After removal, moc-foo.md in notes/ still passes via the kebab pattern; in
# sources/ it now correctly fails the capture|session pattern.
#
# Home.md|home.md stay as landing-page aliases (out of #166 scope).
# ---------------------------------------------------------------------------
case "$filename" in
  _index.md|Home.md|home.md)
    exit 0
    ;;
esac

# Regex patterns per directory — python3 handles POSIX ERE consistently across
# macOS BSD grep and GNU grep.
validate_pattern() {
  local fname="$1"
  local pattern="$2"
  python3 -c "
import re, sys
fname = sys.argv[1]
pattern = sys.argv[2]
sys.exit(0 if re.match(pattern, fname) else 1)
" "$fname" "$pattern"
}

violation=""
expected_pattern=""

case "$top_dir" in
  sources)
    # capture and session notes only (v4 §3.6). plan/decision/note live in notes/.
    expected_pattern='^(capture|session)-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[a-z0-9-]+)?(-v[0-9]+)?\.md$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="sources/ filenames must match: {type}-YYYY-MM-DD[-slug][-vN].md  (type ∈ capture|session — plan/decision/note belong in notes/)"
    fi
    ;;
  notes)
    # Intentionally loose kebab-case — preserves user freedom (v4 §3.6); OVM `note` enforces prefix convention.
    # .base allowed alongside .md (Obsidian Bases view files, #118): same kebab stem, NEVER overwrites notes.
    # Bare YYYY-MM- prefix excluded (#531): v4 §3.6 reserves that shape for sources/capture-*
    # and sources/session-*; a date-first name under notes/ needs a {type}- prefix
    # (decision-/plan-YYYY-MM-DD-{slug}, still allowed below) or no date at all. Without this
    # exclusion the guard let through exactly what audit-validate.py's filename_conforms()
    # flags as a P0 filename_convention_violation on every run.
    expected_pattern='^(?!\d{4}-\d{2}-)[a-z0-9][a-z0-9-]*(-v[0-9]+)?\.(md|base)$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="notes/ filenames must match: {lowercase-kebab}[-vN].(md|base), and may not start with a bare YYYY-MM- date (that shape is reserved for sources/)"
    fi
    ;;
  wiki)
    # v5 §3 A-layer LLM wiki: evergreen kebab slugs, no date prefix (same shape as notes .md).
    # The OVM `wiki` skill compounds onto an existing page; -vN is only a genuine slug collision.
    expected_pattern='^[a-z0-9][a-z0-9-]*(-v[0-9]+)?\.md$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="wiki/ filenames must match: {lowercase-kebab}[-vN].md"
    fi
    ;;
  assets)
    exit 0  # attachments — no naming policy
    ;;
  *)
    # Unknown top-level dir or .vault-bridge/: no policy applied
    exit 0
    ;;
esac

# No violation → clean exit
if [ -z "$violation" ]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# Violation handling
# ---------------------------------------------------------------------------

strict="${VAULT_BRIDGE_STRICT_NAMING:-0}"

# Always write warning to stderr
printf '[vault-bridge pre-write-guard] NAMING VIOLATION: %s\n' "$violation" >&2
printf '  Path: %s\n' "$rel_path" >&2
if [ -n "$expected_pattern" ]; then
  printf '  Expected pattern: %s\n' "$expected_pattern" >&2
fi

if [ "$strict" = "1" ]; then
  # Strict mode: block the write (exit 2)
  printf '[vault-bridge pre-write-guard] BLOCKED (VAULT_BRIDGE_STRICT_NAMING=1). Fix the filename and retry.\n' >&2
  exit 2
fi

# Log-only mode: emit systemMessage and exit 0 (never blocks)
jq -nc \
  --arg path "$rel_path" \
  --arg violation "$violation" \
  --arg filename "$filename" \
  '{
    systemMessage: ("vault-bridge naming warning: \"" + $filename + "\" in vault:/" + $path + " may not follow the vault file naming convention. " + $violation + ". Set VAULT_BRIDGE_STRICT_NAMING=1 to block non-conforming writes. Set VAULT_BRIDGE_DISABLE=1 to silence all vault-bridge hooks.")
  }'

exit 0
