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

# Only act on Write and Edit
case "$tool_name" in
  Write|Edit) ;;
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
# Modes: enforce (default — deny), warn (log + systemMessage, allow), off (skip).
# assets/ is a passthrough — no contract check (automated tools may write attachments).
# ---------------------------------------------------------------------------
contract_mode="${VAULT_BRIDGE_WRITE_CONTRACT:-enforce}"

if [ "$contract_mode" != "off" ]; then
  agent_id=$(printf '%s' "$payload" | jq -r '
    .agent_name // .subagent_type // .agent.name // .agent.type // .attributionAgent // empty
  ' 2>/dev/null || true)

  if [ -n "$agent_id" ] && [ "$top_dir" != "assets" ]; then
    contract_msg="Vault writes must be user-initiated slash commands (/save-session, /vault-commit). Subagent ($agent_id) vault write blocked. To author content from a subagent, return a draft to the main context and let the user invoke a slash command."

    if [ "$contract_mode" = "enforce" ]; then
      # Emit both permissionDecisionReason (for the deny dialog) AND systemMessage
      # (so the user actually sees the revert/disable hint in their transcript).
      jq -nc --arg reason "$contract_msg" \
        '{permissionDecision:"deny", permissionDecisionReason:$reason, systemMessage:("vault-bridge contract: " + $reason + " Set VAULT_BRIDGE_WRITE_CONTRACT=warn to allow, =off to disable.")}'
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
# Matches: _index.md, Home.md, home.md
#
# _index.md is the structural vault/folder index — it mirrors audit-validate.py
# `filename_conforms`/`EXEMPT_FILES` (always valid at any path) and is NOT a MOC
# remnant. Kept consistent with audit-validate.py `filename_conforms`.
#
# The hand-written MOC pattern (moc-*.md) was retired per v4 §9.5 (#166): MOC is
# rejected as a separate slot and #118 `.base` views replace hand-written MOC.
# After removal, moc-foo.md in notes/ still passes via the kebab pattern; in
# inbox/ it now correctly fails the capture|session pattern.
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
  inbox)
    # capture and session notes only (v4 §3.6). plan/decision/note live in notes/.
    expected_pattern='^(capture|session)-[0-9]{4}-[0-9]{2}-[0-9]{2}(-[a-z0-9-]+)?(-v[0-9]+)?\.md$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="inbox/ filenames must match: {type}-YYYY-MM-DD[-slug][-vN].md  (type ∈ capture|session — plan/decision/note belong in notes/)"
    fi
    ;;
  notes)
    # Intentionally loose kebab-case — preserves user freedom (v4 §3.1); OVM `note` enforces prefix convention.
    # .base allowed alongside .md (Obsidian Bases view files, #118): same kebab stem, NEVER overwrites notes.
    expected_pattern='^[a-z0-9][a-z0-9-]*(-v[0-9]+)?\.(md|base)$'
    if ! validate_pattern "$filename" "$expected_pattern"; then
      violation="notes/ filenames must match: {lowercase-kebab}[-vN].(md|base)"
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
