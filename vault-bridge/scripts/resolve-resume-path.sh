#!/usr/bin/env bash
# resolve-resume-path.sh — Canonical resume.md destination resolver for /handoff.
#
# Echoes the absolute path where resume.md should be written and ensures the
# parent directory exists. Refuses (exit 1 + stderr error) if the destination
# resolves into vault body trees (inbox/, notes/, assets/).
# .claude-kit/ is explicitly whitelisted even when nested under vault root.
#
# Priority (mirrors all other vault-bridge scripts):
#   1. VAULT_BRIDGE_VAULT_ROOT  — explicit env override
#   2. VAULT_BRIDGE_VAULT_PATH  — set from userConfig by Claude Code
#   3. $HOME/vault              — built-in default
#
# Usage:
#   RESUME_PATH=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-resume-path.sh")

set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
TARGET="${PROJECT_ROOT}/.claude-kit/vault-bridge/resume.md"

# Resolve vault root (3-level priority, expand tilde)
_raw_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_raw_vr" ] && _raw_vr="${HOME}/vault"
VAULT_ROOT="${_raw_vr/#\~/$HOME}"

# Ensure parent directory exists so realpath-style resolution works
mkdir -p "$(dirname "$TARGET")"
TARGET_ABS="$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")"

# .claude-kit/ is always an allowed write zone — even if nested under vault root
case "$TARGET_ABS" in
  */.claude-kit/*) echo "$TARGET_ABS"; exit 0 ;;
esac

# Block only vault BODY trees: inbox/, notes/, assets/
# Vault root itself and vault-adjacent paths are NOT blocked.
case "$TARGET_ABS" in
  "$VAULT_ROOT"/inbox/*|"$VAULT_ROOT"/notes/*|"$VAULT_ROOT"/assets/*)
    echo "ERROR: /handoff resume.md path resolved into vault body tree (${TARGET_ABS}) — refusing to write. Check CLAUDE_PROJECT_ROOT." >&2
    exit 1
    ;;
esac

echo "$TARGET_ABS"
