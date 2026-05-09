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

# Scope: match keys inside the first --- frontmatter block if present,
# otherwise match anywhere (handles flat .vault-link files). Strips surrounding
# quotes so `key: "true"` parses the same as bare scalars.
_yaml_value() {
  awk -v key="$2" '
    BEGIN { in_fm=0; saw_fm=0 }
    /^---[[:space:]]*$/ {
      if (saw_fm == 0) { saw_fm=1; in_fm=1; next }
      else if (in_fm) { exit }
    }
    saw_fm == 0 || in_fm {
      if (match($0, "^" key "[[:space:]]*:[[:space:]]*")) {
        val = substr($0, RSTART + RLENGTH)
        sub(/[[:space:]]+$/, "", val)
        if (val ~ /^".*"$/ || val ~ /^\047.*\047$/) {
          val = substr(val, 2, length(val) - 2)
        }
        print val
        exit
      }
    }
  ' "$1" 2>/dev/null
}
_is_truthy() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    true|yes|1) return 0;;
    *) return 1;;
  esac
}

# Layer 1 opt-in gate
_is_truthy "$(_yaml_value "$vault_link_file" auto_capture)" || exit 0

# Extract + sanitize vault_path. Reject empty values and ".." traversal up
# front — the value flows into a filesystem path next. Note: ANSI-C quoting
# ($'\n', $'\0') in case patterns false-matches under Bash 3.2 + set -euo
# pipefail (Apple's stock bash), so keep patterns to plain glob; grep above
# already collapses any embedded newline since it reads line by line.
vault_path="$(_yaml_value "$vault_link_file" vault_path)"
if [ -z "$vault_path" ]; then
  exit 0
fi
# Reject literal traversal and absolute paths up front.
case "$vault_path" in
  *..*|/*) exit 0;;
esac

vault_root="${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}"
index_file="${vault_root}/${vault_path}/_index.md"

# Symlink-aware containment check: resolve both vault_root and the candidate
# directory, then verify the candidate stays within vault_root. Defends against
# `vault_path` like `legit/inner` where `legit` is a symlink to `../../etc`.
if ! python3 - "$vault_root" "${vault_root}/${vault_path}" <<'PY' 2>/dev/null
import os, sys
root = os.path.realpath(sys.argv[1])
cand = os.path.realpath(sys.argv[2])
sys.exit(0 if cand == root or cand.startswith(root + os.sep) else 1)
PY
then
  exit 0
fi

if [ ! -f "$index_file" ]; then
  exit 0
fi

# Layer 2 opt-in gate
_is_truthy "$(_yaml_value "$index_file" auto_capture)" || exit 0

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
