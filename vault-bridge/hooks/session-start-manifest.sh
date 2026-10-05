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

# One-line user notice (#763) via SessionStart `systemMessage`; never blocks startup.
_notice() {
  local m="${1//\\/\\\\}"
  printf '{"systemMessage": "%s"}\n' "${m//\"/\\\"}"
}
_howto='VAULT_BRIDGE_VAULT_ROOT 환경변수(~/.claude/settings.json의 env)나 플러그인 설정 vault_path로 지정해 주세요.'

# Vault must exist; if not, say so once and exit 0 (the session still starts).
if [ ! -d "$VAULT_ROOT" ]; then
  _notice "vault-bridge: vault 루트 ${VAULT_ROOT}가 없어요. 볼트가 다른 곳에 있다면 ${_howto}"
  exit 0
fi
if [ ! -d "$VAULT_ROOT/.obsidian" ]; then
  _notice "vault-bridge: ${VAULT_ROOT}에 .obsidian/이 없어 Obsidian 볼트가 아닐 수 있어요. 다른 경로라면 ${_howto}"
fi

# Locate this script's directory to find the generator relative to plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
GENERATOR="${PLUGIN_ROOT}/scripts/generate-manifest.py"

if [ ! -f "$GENERATOR" ]; then
  exit 0
fi

# Detect a usable timeout binary (macOS has neither `timeout` by default —
# see obsidian-vault-manager/reference/obsidian-cli.md). Run unwrapped if absent
# rather than silently no-op: a bare `timeout 10 ...` on such a host is a
# "command not found" that >/dev/null 2>&1 below swallows completely (#484).
if command -v timeout >/dev/null 2>&1; then
  MANIFEST_TO="timeout 10"
elif command -v gtimeout >/dev/null 2>&1; then
  MANIFEST_TO="gtimeout 10"
else
  MANIFEST_TO=""
fi

# Run generator in background with a 10s wall-time cap to handle large vaults
# or slow filesystems. The generator itself is fast (incremental mtime checks).
# Discard stdout/stderr — stats are not needed here.
(
  $MANIFEST_TO python3 "$GENERATOR" --vault-root "$VAULT_ROOT" >/dev/null 2>&1
) &

exit 0
