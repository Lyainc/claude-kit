#!/usr/bin/env bash
# vault-bridge W8 — plan-doc-sync.sh
#
# Deterministic plan document detection script.
# Scans the current project for plan/design docs matching default patterns
# and emits a systemMessage suggestion when candidates are found.
#
# Trigger: SessionEnd (via plugin.json) — fires once at session close.
# No LLM call. No writes. Dry-run only — reports candidates for user decision.
#
# PostToolUse (DEBUG) mode is intentionally NOT wired in production.
# Set VAULT_BRIDGE_PLAN_DOC_DEBUG=1 to enable PostToolUse detection locally.

set -euo pipefail

# Kill switch
if [ "${VAULT_BRIDGE_DISABLE:-0}" = "1" ]; then
  exit 0
fi

# Read hook payload from stdin
payload=$(cat)

# Resolve project root (CWD from hook context, fallback to pwd)
project_root="${CLAUDE_PROJECT_ROOT:-$(pwd)}"

# Only operate if a .vault-link file exists
vault_link_file="${project_root}/.vault-link"
if [ ! -f "$vault_link_file" ]; then
  exit 0
fi

# Layer 1 opt-in gate: auto_capture: true in .vault-link
auto_capture_l1=$(grep -E '^auto_capture\s*:' "$vault_link_file" 2>/dev/null \
  | sed 's/.*:\s*//' | tr -d '[:space:]' || echo "false")

if [ "$auto_capture_l1" != "true" ]; then
  exit 0
fi

# Layer 2 opt-in gate: auto_capture: true in _index.md
vault_path=$(grep -E '^vault_path\s*:' "$vault_link_file" 2>/dev/null \
  | sed 's/.*:\s*//' | tr -d '[:space:]' || echo "")

vault_root="${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}"
index_file="${vault_root}/${vault_path}/_index.md"

if [ ! -f "$index_file" ]; then
  exit 0
fi

auto_capture_l2=$(grep -E '^auto_capture\s*:' "$index_file" 2>/dev/null \
  | sed 's/.*:\s*//' | tr -d '[:space:]' || echo "false")

if [ "$auto_capture_l2" != "true" ]; then
  exit 0
fi

# Session-level 1-ask guard: track whether we already fired this session.
# Uses a per-session temp dir (same pattern as other vault-bridge hooks).
session_id="${CLAUDE_SESSION_ID:-unknown}"
session_id="${session_id//[^a-zA-Z0-9_-]/}"
[ -z "$session_id" ] && session_id="unknown"
state_dir="/tmp/vault-bridge-session-${session_id}"
asked_flag="${state_dir}/plan-doc-asked"

mkdir -p "$state_dir" 2>/dev/null || true
chmod 700 "$state_dir" 2>/dev/null || true

if [ -f "$asked_flag" ]; then
  # Already suggested once this session — skip to enforce 1-ask limit.
  exit 0
fi

# Discover candidates via syncer (handles default + .vault-link override + vault-native + excludes)
# Spec §3.2 default patterns + .vault-link autosync_paths_include/exclude (v1.1) merged inside syncer.
syncer="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/scripts/plan-doc-syncer.py"
filtered=()
while IFS= read -r line; do
  [ -n "$line" ] && filtered+=("$line")
done < <(python3 "$syncer" --discover "$project_root" --vault-link "$vault_link_file" 2>/dev/null)

# If no candidates, nothing to suggest
if [ "${#filtered[@]}" -eq 0 ]; then
  exit 0
fi

# Mark that we've fired once this session
touch "$asked_flag" 2>/dev/null || true

# Build the file list string (max 5 shown to keep message compact)
max_shown=5
shown=("${filtered[@]:0:$max_shown}")
file_list=""
for f in "${shown[@]}"; do
  file_list="${file_list}  • ${f}\n"
done
remaining=$(( ${#filtered[@]} - max_shown ))
if [ "$remaining" -gt 0 ]; then
  file_list="${file_list}  … 외 ${remaining}개\n"
fi

count="${#filtered[@]}"
msg="세션 중 plan/design 문서 ${count}개 감지됨 (vault autosync 활성화됨).\n\n${file_list}\nvault 프로젝트(${vault_path})에 스냅샷 저장: \`/save-plan-doc\` 실행."

printf '%s' "$msg" | jq -Rsc '{systemMessage: .}'

exit 0
