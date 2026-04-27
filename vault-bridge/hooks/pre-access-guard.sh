#!/usr/bin/env bash
# vault-bridge PreToolUse hook — Direct vault access soft warning.
#
# Fires on every Read/Grep/Glob tool call. If the target path resolves to
# inside ~/vault/, emits a systemMessage suggesting vault-searcher instead.
# Never blocks (exit 0 always). No LLM call — deterministic <50ms.
#
# Environment variables:
#   VAULT_BRIDGE_DISABLE=1        — skip entirely (kill switch)
#   VAULT_BRIDGE_VAULT_ROOT=PATH  — override default ~/vault

set -uo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-}" = "1" ]; then
  exit 0
fi

# Read the PreToolUse JSON payload from stdin
payload=$(cat)

# Extract tool_name
tool_name=$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null || true)

# Only act on Read, Grep, Glob
case "$tool_name" in
  Read|Grep|Glob) ;;
  *) exit 0 ;;
esac

# Determine vault root (absolute)
VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-${HOME}/vault}"

# Vault must exist; CI/remote environments without vault → silent exit
if [ ! -d "$VAULT_ROOT" ]; then
  exit 0
fi

# Resolve vault root to absolute path (handle symlinks)
vault_abs=$(cd "$VAULT_ROOT" 2>/dev/null && pwd -P) || exit 0

# Extract target path from tool_input based on tool type
# Read → file_path, Grep/Glob → path (may be absent = CWD)
tool_input=$(printf '%s' "$payload" | jq -r '.tool_input // {}' 2>/dev/null || echo '{}')

case "$tool_name" in
  Read)
    raw_path=$(printf '%s' "$tool_input" | jq -r '.file_path // empty' 2>/dev/null || true)
    ;;
  Grep|Glob)
    raw_path=$(printf '%s' "$tool_input" | jq -r '.path // empty' 2>/dev/null || true)
    ;;
esac

# Empty path → CWD; not inside vault → skip
if [ -z "${raw_path:-}" ]; then
  exit 0
fi

# Expand ~ and resolve to absolute path.
# GNU realpath has -m (no-existence-required); BSD realpath (macOS default) does not.
# Use python3 unconditionally — handles missing paths and symlinks via os.path.realpath.
abs_path=$(python3 -c "import os,sys; p=sys.argv[1]; print(os.path.realpath(os.path.expanduser(p)))" "$raw_path" 2>/dev/null || true)

if [ -z "${abs_path:-}" ]; then
  exit 0
fi

# Check if path is inside vault root
case "$abs_path" in
  "$vault_abs"/*|"$vault_abs")
    : # path is inside vault — proceed to warning
    ;;
  *)
    exit 0
    ;;
esac

# Increment session counter
session_id="${CLAUDE_SESSION_ID:-pid-$$}"
session_id="${session_id//[^a-zA-Z0-9_-]/}"
[ -z "$session_id" ] && session_id="pid-$$"
counter_dir="/tmp/vault-bridge-session-${session_id}"
counter_file="${counter_dir}/direct-access-count"
log_file="${counter_dir}/direct-access-log"

mkdir -p "$counter_dir" 2>/dev/null || true

# Read current count, increment, write back
current=0
if [ -f "$counter_file" ]; then
  current=$(cat "$counter_file" 2>/dev/null || echo 0)
  # Ensure it's a valid integer
  case "$current" in
    ''|*[!0-9]*) current=0 ;;
  esac
fi
new_count=$((current + 1))
printf '%d' "$new_count" > "$counter_file" 2>/dev/null || true

# Append to debug log (timestamp + tool + path)
printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$tool_name" "$abs_path" \
  >> "$log_file" 2>/dev/null || true

# Emit systemMessage (JSON to stdout)
# Shorten displayed path relative to vault root for readability
rel_path="${abs_path#"$vault_abs"/}"

jq -nc \
  --arg tool "$tool_name" \
  --arg path "$rel_path" \
  --arg count "$new_count" \
  '{
    systemMessage: ("vault-bridge notice: Direct vault access detected (" + $tool + " on vault:/" + $path + "). For token-efficient search (97% savings), prefer vault-searcher agent (Mode 2/3) which reads the manifest index first. Direct access count this session: " + $count + ". Set VAULT_BRIDGE_DISABLE=1 to silence these notices.")
  }'

exit 0
