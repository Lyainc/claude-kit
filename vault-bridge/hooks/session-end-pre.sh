#!/usr/bin/env bash
# vault-bridge — session-end-pre.sh
#
# Deterministic state collector that runs immediately before the SessionEnd
# prompt-type hook fires. Writes a single JSON state file the prompt then
# reads via Bash, so the prompt no longer has to embed grep/find/cat
# pipelines and conditional templating.
#
# Trigger: SessionEnd (chained before the prompt hook in plugin.json).
# No LLM call. No writes outside /tmp/vault-bridge-session-${SID}/.
# Always exits 0 — failures degrade to {"disabled": true, "errors": [...]}
# so the prompt can still run with reasonable defaults.

set -uo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-0}" = "1" ]; then
  echo '{"version": 1, "disabled": true, "reason": "VAULT_BRIDGE_DISABLE=1"}'
  exit 0
fi

# Sanitize CLAUDE_SESSION_ID — only [A-Za-z0-9_-] survives interpolation
# into a /tmp path. Falls back to pid- if blank after sanitization.
session_id="${CLAUDE_SESSION_ID:-unknown}"
session_id="${session_id//[^a-zA-Z0-9_-]/}"
[ -z "$session_id" ] && session_id="pid-$$"

state_dir="/tmp/vault-bridge-session-${session_id}"
mkdir -p "$state_dir" 2>/dev/null || true
chmod 700 "$state_dir" 2>/dev/null || true

state_file="${state_dir}/session-end-state.json"

# Resolve project root: prefer the harness-provided CLAUDE_PROJECT_ROOT
# so a session-internal `cd` doesn't break .vault-link discovery.
project_root="${CLAUDE_PROJECT_ROOT:-$(pwd)}"

# Resolve vault root: VAULT_BRIDGE_VAULT_ROOT (env override) >
# VAULT_BRIDGE_VAULT_PATH (userConfig, set by Claude Code) > $HOME/vault (default).
_raw_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_raw_vr" ] && _raw_vr="${HOME}/vault"
vault_root="${_raw_vr/#\~/$HOME}"
unset _raw_vr
vault_link_file="${project_root}/.vault-link"

# ── .vault-link presence ──────────────────────────────────────────────────────
vl_present=false
[ -f "$vault_link_file" ] && vl_present=true

# ── Direct-access counter (set by pre-access-guard.sh) ────────────────────────
direct_access_count=0
counter_file="${state_dir}/direct-access-count"
if [ -f "$counter_file" ]; then
  v=$(cat "$counter_file" 2>/dev/null || echo 0)
  case "$v" in
    ''|*[!0-9]*) direct_access_count=0 ;;
    *) direct_access_count=$v ;;
  esac
fi

# ── Emit the JSON state ──────────────────────────────────────────────────────
# Build the JSON in Python to escape strings safely. Booleans are passed in via
# env vars so we avoid mixing Bash-literal `true`/`false` into Python source.
SESSION_ID="$session_id" \
SESSION_STATE_DIR="$state_dir" \
PROJECT_ROOT="$project_root" \
VAULT_ROOT="$vault_root" \
VL_PRESENT="$vl_present" \
DIRECT_ACCESS_COUNT="$direct_access_count" \
python3 - <<'PY' > "$state_file"
import json, os

def b(name):
    return os.environ.get(name, "false") == "true"

def s(name):
    return os.environ.get(name, "")

state = {
    "version": 1,
    "disabled": False,
    "session_id": s("SESSION_ID"),
    "session_state_dir": s("SESSION_STATE_DIR"),
    "project_root": s("PROJECT_ROOT"),
    "vault_root": s("VAULT_ROOT"),
    "vault_link": {
        "present": b("VL_PRESENT"),
    },
    "direct_access_count": int(os.environ.get("DIRECT_ACCESS_COUNT", "0") or 0),
}
print(json.dumps(state, indent=2))
PY

# Print a one-line breadcrumb the harness can show as systemMessage so the
# prompt knows where to find the state without grep-discovery.
printf 'vault-bridge SessionEnd state: %s\n' "$state_file"

exit 0
