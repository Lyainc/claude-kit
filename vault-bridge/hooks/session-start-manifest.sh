#!/usr/bin/env bash
# vault-bridge SessionStart hook — Vault Manifest Staleness Check & Regeneration
#
# Runs at the start of every Claude Code session. Checks whether the vault
# manifest needs regeneration and triggers generate-manifest.py if so.
# Failures are always silent — this hook must never block session startup.
#
# Environment variables:
#   VAULT_BRIDGE_DISABLE=1        — skip entirely (kill switch)
#   VAULT_BRIDGE_VAULT_ROOT=PATH  — explicit env override (highest priority)
#   VAULT_BRIDGE_VAULT_PATH=PATH  — userConfig vault path (set by Claude Code plugin settings)

set -uo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-}" = "1" ]; then
  exit 0
fi

# Resolve vault root: VAULT_BRIDGE_VAULT_ROOT (env override) >
# VAULT_BRIDGE_VAULT_PATH (userConfig, set by Claude Code) > $HOME/vault (default).
_raw_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_raw_vr" ] && _raw_vr="${HOME}/vault"
VAULT_ROOT="${_raw_vr/#\~/$HOME}"
unset _raw_vr

# Vault must exist; if not, silently exit (external projects may not have a vault)
if [ ! -d "$VAULT_ROOT" ]; then
  exit 0
fi

# Locate this script's directory to find the generator relative to plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
GENERATOR="${PLUGIN_ROOT}/scripts/generate-manifest.py"

if [ ! -f "$GENERATOR" ]; then
  exit 0
fi

# Run generator in background with a 10s wall-time cap to handle large vaults
# or slow filesystems. The generator itself is fast (incremental mtime checks).
# Discard stdout/stderr — stats are not needed here.
(
  timeout 10 python3 "$GENERATOR" --vault-root "$VAULT_ROOT" >/dev/null 2>&1
) &

exit 0
