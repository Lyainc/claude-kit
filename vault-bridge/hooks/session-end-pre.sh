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

vault_root="${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}"
vault_link_file="${project_root}/.vault-link"

# ── Layer 1: .vault-link presence + auto_capture flag ─────────────────────────
vl_present=false
auto_capture_l1=false
vault_path=""

if [ -f "$vault_link_file" ]; then
  vl_present=true
  # Anchored grep — never match `# auto_capture: true` comments.
  if grep -qE '^auto_capture[[:space:]]*:[[:space:]]*true' "$vault_link_file" 2>/dev/null; then
    auto_capture_l1=true
  fi
  vault_path=$(grep -E '^vault_path[[:space:]]*:' "$vault_link_file" 2>/dev/null \
    | head -n1 | sed 's/.*:[[:space:]]*//' | tr -d '[:space:]' || true)
fi

# ── Layer 2: vault project _index.md auto_capture ─────────────────────────────
index_present=false
auto_capture_l2=false
index_file=""

if [ -n "$vault_path" ]; then
  index_file="${vault_root}/${vault_path}/_index.md"
  if [ -f "$index_file" ]; then
    index_present=true
    if grep -qE '^auto_capture[[:space:]]*:[[:space:]]*true' "$index_file" 2>/dev/null; then
      auto_capture_l2=true
    fi
  fi
fi

# ── Plan-doc candidates (only meaningful when both layers opted in) ───────────
plan_doc_already_asked=false
[ -f "${state_dir}/plan-doc-asked" ] && plan_doc_already_asked=true

# Always scan candidates so the prompt can decide whether to suggest;
# gating happens in the prompt by combining auto_capture_l1 ∧ auto_capture_l2.
candidates_json="[]"
if [ "$auto_capture_l1" = "true" ] && [ "$auto_capture_l2" = "true" ]; then
  found=()
  for d in "docs/discussions" "docs/design" "docs/plans" ".omc/plans"; do
    if [ -d "${project_root}/${d}" ]; then
      while IFS= read -r f; do
        [ -n "$f" ] && found+=("${f#${project_root}/}")
      done < <(find "${project_root}/${d}" -name '*.md' 2>/dev/null | head -10)
    fi
  done
  for f in "${project_root}/PLAN.md" "${project_root}/DESIGN.md"; do
    [ -f "$f" ] && found+=("${f#${project_root}/}")
  done
  while IFS= read -r f; do
    [ -n "$f" ] && found+=("${f#${project_root}/}")
  done < <(find "${project_root}" -maxdepth 1 -name 'RFC-*.md' 2>/dev/null)

  if [ "${#found[@]}" -gt 0 ]; then
    # Build JSON array via python3 to escape any path that might contain
    # quotes/backslashes safely.
    candidates_json=$(python3 -c '
import json, sys
print(json.dumps(sys.argv[1:]))
' "${found[@]}")
  fi
fi

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
# Build the JSON in Python to escape strings safely. Booleans and the
# nested candidates array are passed in via env vars so we avoid mixing
# Bash-literal `true`/`false` into Python source.
SESSION_ID="$session_id" \
SESSION_STATE_DIR="$state_dir" \
PROJECT_ROOT="$project_root" \
VAULT_ROOT="$vault_root" \
VL_PRESENT="$vl_present" \
AUTO_CAPTURE_L1="$auto_capture_l1" \
VAULT_PATH="$vault_path" \
INDEX_FILE="$index_file" \
INDEX_PRESENT="$index_present" \
AUTO_CAPTURE_L2="$auto_capture_l2" \
PLAN_DOC_ALREADY_ASKED="$plan_doc_already_asked" \
CANDIDATES_JSON="$candidates_json" \
DIRECT_ACCESS_COUNT="$direct_access_count" \
python3 - <<'PY' > "$state_file"
import json, os

def b(name):
    return os.environ.get(name, "false") == "true"

def s(name):
    return os.environ.get(name, "")

candidates = json.loads(os.environ.get("CANDIDATES_JSON", "[]"))
auto_l1 = b("AUTO_CAPTURE_L1")
auto_l2 = b("AUTO_CAPTURE_L2")

state = {
    "version": 1,
    "disabled": False,
    "session_id": s("SESSION_ID"),
    "session_state_dir": s("SESSION_STATE_DIR"),
    "project_root": s("PROJECT_ROOT"),
    "vault_root": s("VAULT_ROOT"),
    "vault_link": {
        "present": b("VL_PRESENT"),
        "auto_capture_l1": auto_l1,
        "vault_path": s("VAULT_PATH"),
    },
    "vault_index": {
        "path": s("INDEX_FILE"),
        "present": b("INDEX_PRESENT"),
        "auto_capture_l2": auto_l2,
    },
    "plan_docs": {
        "auto_capture_active": auto_l1 and auto_l2,
        "already_asked": b("PLAN_DOC_ALREADY_ASKED"),
        "candidates": candidates,
    },
    "direct_access_count": int(os.environ.get("DIRECT_ACCESS_COUNT", "0") or 0),
}
print(json.dumps(state, indent=2))
PY

# Print a one-line breadcrumb the harness can show as systemMessage so the
# prompt knows where to find the state without grep-discovery.
printf 'vault-bridge SessionEnd state: %s\n' "$state_file"

exit 0
