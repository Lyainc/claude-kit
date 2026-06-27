#!/usr/bin/env bash
# Regression for thinking-tools/hooks/session-start-welcome.sh (#117).
# Asserts: 3-session grace then silence, kill switch, corrupt-counter recovery,
# and that every emission is valid JSON carrying additionalContext.
set -uo pipefail

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/hooks/session-start-welcome.sh"
fail=0
check() { if [ "$1" = "$2" ]; then :; else echo "FAIL: $3 (got '$1', want '$2')"; fail=1; fi; }

run() { CLAUDE_CONFIG_DIR="$1" CLAUDE_KIT_WELCOME_DISABLE="${2:-}" bash "$HOOK"; }

# --- grace: shown on sessions 1-3, silent on 4+ ---
d=$(mktemp -d)
for n in 1 2 3; do
  out=$(run "$d")
  [ -n "$out" ] || { echo "FAIL: session $n expected a message"; fail=1; }
  # SessionStart surfaces via hookSpecificOutput.additionalContext (systemMessage is ignored here).
  printf '%s' "$out" | python3 -c "import json,sys; o=json.load(sys.stdin)['hookSpecificOutput']; assert o['hookEventName']=='SessionStart'; assert o['additionalContext']" \
    || { echo "FAIL: session $n not valid SessionStart additionalContext JSON"; fail=1; }
done
check "$(cat "$d/.claude-kit/welcome-count")" "3" "counter reaches 3"
out4=$(run "$d"); check "$out4" "" "session 4 is silent"
out5=$(run "$d"); check "$out5" "" "session 5 stays silent"
rm -rf "$d"

# --- kill switch: silent even on first session ---
d=$(mktemp -d)
out=$(run "$d" "1"); check "$out" "" "kill switch silences"
[ -f "$d/.claude-kit/welcome-count" ] && { echo "FAIL: kill switch wrote state"; fail=1; }
rm -rf "$d"

# --- corrupt counter recovers to 0 (still shows, not crash) ---
d=$(mktemp -d); mkdir -p "$d/.claude-kit"; printf 'garbage' > "$d/.claude-kit/welcome-count"
out=$(run "$d"); [ -n "$out" ] || { echo "FAIL: corrupt counter should show"; fail=1; }
check "$(cat "$d/.claude-kit/welcome-count")" "1" "corrupt counter reset to 0 then incremented"
rm -rf "$d"

if [ "$fail" -eq 0 ]; then echo "OK: all session-start-welcome cases passed"; else exit 1; fi
