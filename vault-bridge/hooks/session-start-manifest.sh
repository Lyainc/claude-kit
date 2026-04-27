#!/usr/bin/env bash
# vault-bridge SessionStart hook — Vault Manifest Staleness Check & Regeneration
#
# Runs at the start of every Claude Code session. Checks whether the vault
# manifest needs regeneration and triggers generate-manifest.py if so.
# Failures are always silent — this hook must never block session startup.
#
# Environment variables:
#   VAULT_BRIDGE_DISABLE=1        — skip entirely (kill switch)
#   VAULT_BRIDGE_VAULT_ROOT=PATH  — override default ~/vault

set -uo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-}" = "1" ]; then
  exit 0
fi

# Determine vault root
VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-${HOME}/vault}"

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

# Run generator in background with a 10-second timeout guard.
# The generator itself is fast (incremental mtime checks), but we cap wall time
# to avoid blocking on very large vaults or slow filesystems.
# We discard stdout/stderr — stats are not needed here.
(
  timeout 10 python3 "$GENERATOR" --vault-root "$VAULT_ROOT" \
    >/dev/null 2>/dev/null
) &

exit 0
