#!/usr/bin/env bash
# vault-bridge PreToolUse hook — Vault file naming convention guard.
#
# Fires on every Write/Edit tool call. If the target path resolves to
# inside ~/vault/, validates the filename against per-directory conventions.
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
#   VAULT_BRIDGE_VAULT_ROOT=PATH    — override default ~/vault
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

# Only act on Write and Edit
case "$tool_name" in
  Write|Edit) ;;
  *) exit 0 ;;
esac

# ---------------------------------------------------------------------------
# W1 D5 preflight payload dump (rev3 Architect 2nd round N2)
# When VAULT_BRIDGE_DUMP_PAYLOAD=1, append the full payload to telemetry's
# preflight log BEFORE existing enforcement runs. Single entry point — the
# enforcement logic below executes unchanged. Used to verify whether a
# Skill-dispatched Write surfaces an agent identifier in the PreToolUse
# payload, which determines whether W2 enforce flip is safe.
#
# The dump target lives in claude-kit/telemetry/ (gitignored). We locate the
# claude-kit checkout via CLAUDE_PROJECT_ROOT (Phase 1 portability) and only
# write if that directory exists.
# ---------------------------------------------------------------------------
if [ "${VAULT_BRIDGE_DUMP_PAYLOAD:-}" = "1" ]; then
  dump_root="${CLAUDE_PROJECT_ROOT:-$PWD}/telemetry"
  if [ -d "$dump_root" ]; then
    printf '%s\n' "$payload" >> "$dump_root/preflight-d5-payloads.jsonl" 2>/dev/null
  fi
fi

# Determine vault root (absolute)
VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-${HOME}/vault}"

# Vault must exist; CI/remote environments without vault → silent exit
if [ ! -d "$VAULT_ROOT" ]; then
  exit 0
fi

# Resolve vault root to absolute path (handle symlinks)
vault_abs=$(cd "$VAULT_ROOT" 2>/dev/null && pwd -P) || exit 0

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
# Write Role Contract enforcement
# Policy: vault writes must originate from main context (user-initiated slash
# commands). Subagent vault writes are out of policy.
# Modes: warn (default — log + systemMessage, allow), enforce (deny), off (skip).
# 50_Archive/ is an OVM territory — exempt regardless of mode.
# ---------------------------------------------------------------------------
contract_mode="${VAULT_BRIDGE_WRITE_CONTRACT:-enforce}"

if [ "$contract_mode" != "off" ]; then
  agent_id=$(printf '%s' "$payload" | jq -r '
    .agent_name // .subagent_type // .agent.name // .agent.type // .attributionAgent // empty
  ' 2>/dev/null || true)

  if [ -n "$agent_id" ] && [ "$top_dir" != "50_Archive" ]; then
    contract_msg="Vault writes must be user-initiated slash commands (/save-session, /save-plan-doc, /vault-commit). Subagent ($agent_id) vault write blocked. To author content from a subagent, return a draft to the main context and let the user invoke a slash command."

    if [ "$contract_mode" = "enforce" ]; then
      jq -nc --arg reason "$contract_msg" \
        '{permissionDecision:"deny", permissionDecisionReason:$reason}'
      exit 0
    else
      # warn mode: log + systemMessage, fall through to filename validation
      printf '[vault-bridge pre-write-guard] CONTRACT WARNING: %s\n' "$contract_msg" >&2
      jq -nc --arg msg "$contract_msg" \
        '{systemMessage: ("vault-bridge contract: " + $msg + " Set VAULT_BRIDGE_WRITE_CONTRACT=enforce to block, =off to disable.")}'
      # do not exit — continue to filename validation below
    fi
  fi
fi

# Extract filename (basename)
filename=$(basename "$abs_path")

# ---------------------------------------------------------------------------
# Whitelist — always allowed regardless of directory
# Matches: _index.md, Home.md, home.md, MOC-*.md (case-insensitive MOC prefix)
# ---------------------------------------------------------------------------
case "$filename" in
  _index.md|Home.md|home.md)
    exit 0
    ;;
esac
# MOC prefix check (case-insensitive)
lower_filename=$(printf '%s' "$filename" | tr '[:upper:]' '[:lower:]')
case "$lower_filename" in
  moc-*.md)
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
  00_Inbox)
    expected_pattern='^(session|capture|plan)-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[a-z0-9-]+)?(-v[0-9]+)?\.md$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="00_Inbox/ filenames must match: {type}-YYYY-MM-DD[-topic][-vN].md  (type ∈ session|capture|plan)"
    fi
    ;;
  30_Notes)
    expected_pattern='^[a-z0-9-]+\.md$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="30_Notes/ filenames must match: {lowercase-kebab}.md  (no date prefix allowed)"
    fi
    ;;
  20_Projects)
    # _index.md is already caught by whitelist above; check for project-scoped files
    expected_pattern='^(session|plan|capture)-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[a-z0-9-]+)?(-v[0-9]+)?\.md$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="20_Projects/{name}/ filenames must be _index.md or match: {type}-YYYY-MM-DD[-topic][-vN].md  (type ∈ session|plan|capture)"
    fi
    ;;
  50_Archive)
    # Archive: allow all filenames; log-only warning for awareness
    violation="50_Archive/ write detected — ensure this is an intentional archive operation (original filename preserved)"
    ;;
  10_MOC)
    # MOC-*.md caught by whitelist; anything else here is unexpected
    violation="10_MOC/ writes should use MOC-{name}.md pattern or whitelist filenames (_index.md, Home.md)"
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
if [ -n "$expected_pattern" ] && [ "$top_dir" != "50_Archive" ] && [ "$top_dir" != "10_MOC" ]; then
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
