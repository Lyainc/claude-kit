#!/usr/bin/env bash
# Regression test for vault-bridge/hooks/stop-check.sh.
#
# stop-check.sh fires on every Stop event and emits a /save-session
# suggestion only when the last user message matches a closing-signal
# regex. A regression that misses Korean closing tokens (locale issue) or
# masks the user prompt with a trailing tool_result would silently break
# the closing-signal detection on every session.
#
# VAULT_BRIDGE_DISABLE=1 keeps tests hermetic — the hook's vault dirty
# check would otherwise probe the user's real ~/vault/ git repo.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$(cd "$SCRIPT_DIR/../.." && pwd)/hooks/stop-check.sh"
[ -f "$HOOK" ] || { echo "FAIL: $HOOK not found" >&2; exit 1; }

TMPDIR_T=$(mktemp -d)
trap 'rm -rf "$TMPDIR_T"' EXIT

PASS=0
FAIL=0

run_case() {
  local name="$1" payload_path="$2" expect="$3"
  local actual
  actual=$(VAULT_BRIDGE_DISABLE=1 printf '{"transcript_path":"%s"}' "$payload_path" | VAULT_BRIDGE_DISABLE=1 bash "$HOOK" 2>&1)
  if [[ "$expect" == "match" && "$actual" == *"systemMessage"* ]]; then
    echo "  ok   $name"; PASS=$((PASS+1))
  elif [[ "$expect" == "silent" && -z "$actual" ]]; then
    echo "  ok   $name"; PASS=$((PASS+1))
  else
    echo "  FAIL $name (expected=$expect, got='$actual')" >&2; FAIL=$((FAIL+1))
  fi
}

# Case 1: Korean closing keyword
cat > "$TMPDIR_T/c1.jsonl" <<'EOF'
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"세션 끝"}]}}
EOF
run_case "Korean closing 세션 끝" "$TMPDIR_T/c1.jsonl" match

# Case 2: English closing keyword (case-insensitive, with apostrophe)
cat > "$TMPDIR_T/c2.jsonl" <<'EOF'
{"type":"user","message":{"role":"user","content":"Let's call it a day"}}
EOF
run_case "English closing call it a day" "$TMPDIR_T/c2.jsonl" match

# Case 3: No closing signal
cat > "$TMPDIR_T/c3.jsonl" <<'EOF'
{"type":"user","message":{"role":"user","content":"create a new file"}}
EOF
run_case "Non-closing message → silent" "$TMPDIR_T/c3.jsonl" silent

# Case 4: Trailing tool_result must NOT mask the earlier user prompt
cat > "$TMPDIR_T/c4.jsonl" <<'EOF'
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"오늘은 여기까지"}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"ok"}]}}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"r"}]}}
EOF
run_case "Trailing tool_result preserves earlier closing prompt" "$TMPDIR_T/c4.jsonl" match

# Case 5: Missing transcript file → silent exit 0
run_case "Missing transcript path → silent" "/nonexistent/path.jsonl" silent

# Case 6: Korean closing under bare C locale (regression guard for locale probe)
cat > "$TMPDIR_T/c6.jsonl" <<'EOF'
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"마무리하자"}]}}
EOF
actual=$(LC_ALL=C LANG=C VAULT_BRIDGE_DISABLE=1 bash -c "printf '{\"transcript_path\":\"%s\"}' '$TMPDIR_T/c6.jsonl' | VAULT_BRIDGE_DISABLE=1 bash $HOOK")
if [[ "$actual" == *"systemMessage"* ]]; then
  echo "  ok   Korean closing under LC_ALL=C"; PASS=$((PASS+1))
else
  echo "  FAIL Korean closing under LC_ALL=C (got='$actual')" >&2; FAIL=$((FAIL+1))
fi

# Case 7: Malformed JSON payload → silent (no set -e crash from jq error)
actual=$(printf 'not-json' | VAULT_BRIDGE_DISABLE=1 bash "$HOOK" 2>&1)
if [[ -z "$actual" ]]; then
  echo "  ok   Malformed payload → silent (jq error suppressed)"; PASS=$((PASS+1))
else
  echo "  FAIL Malformed payload should be silent (got='$actual')" >&2; FAIL=$((FAIL+1))
fi

echo ""
printf 'Result: %d pass, %d fail\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
