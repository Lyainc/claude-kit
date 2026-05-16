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

# Resume handoff injection: surface a prior session's resume.md to the *model*
# via additionalContext — systemMessage would reach only the user. The python3
# guard leaves the file intact when no interpreter is available, rather than
# consuming an undelivered handoff note.
_PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
_RESUME_FILE="$_PROJECT_ROOT/.claude-kit/vault-bridge/resume.md"
if [ -f "$_RESUME_FILE" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$_RESUME_FILE" <<'PYEOF'
import sys, json
try:
    content = open(sys.argv[1]).read().strip()
    lines = content.split('\n')
    if lines and lines[0].strip() == '---':
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                content = '\n'.join(lines[i + 1:]).strip()
                break
    if content:
        msg = '이전 세션의 인수인계 메모입니다:\n\n' + content
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'SessionStart',
                'additionalContext': msg,
            }
        }))
except Exception:
    pass
PYEOF
  rm -f "$_RESUME_FILE"
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
