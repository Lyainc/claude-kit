#!/usr/bin/env bash
# Regression for feedback-loop/scripts/retro-telemetry.sh (the extracted retro
# Phase-1 stamp + Phase-3 emit helper). Asserts: opt-in gate, schema-shaped emit
# line with the three retro counters, numeric duration after a stamp, and the
# null fallback when the stamp is missing/corrupt.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${SCRIPT_DIR}/../retro-telemetry.sh"
fail() { echo "FAIL: $1"; exit 1; }

TMP="$(mktemp -d)"
export CLAUDE_KIT_TELEMETRY=1
export CLAUDE_KIT_TELEMETRY_DIR="$TMP/events"
export CLAUDE_SESSION_ID="retro-telem-test-$$"
mkdir -p "$CLAUDE_KIT_TELEMETRY_DIR"
LOG="$CLAUDE_KIT_TELEMETRY_DIR/events-$(date -u +%Y-%m-%d).jsonl"
STAMP_FILE="/tmp/retro-start-${CLAUDE_SESSION_ID}.ms"
# Leave no stamp behind on any exit path (the temp events dir is mktemp/-d in /tmp).
trap 'trash-put "$STAMP_FILE" 2>/dev/null || true' EXIT

# 1. opt-in off → no write
( unset CLAUDE_KIT_TELEMETRY; "$SCRIPT" emit 1 1 1 )
[ -f "$LOG" ] && fail "wrote a line while telemetry off"

# 2. stamp + emit → one schema-shaped line, numeric duration, stamp cleaned
"$SCRIPT" stamp
[ -f "$STAMP_FILE" ] || fail "stamp not written"
"$SCRIPT" emit 5 2 5
LINE="$(cat "$LOG")"
echo "$LINE" | jq -e '.event=="skill_invoke" and .name=="retro" and .qualified_name=="feedback-loop:retro" and .plugin=="feedback-loop"' >/dev/null || fail "envelope shape wrong"
echo "$LINE" | jq -e '.meta.retro_items_processed==5 and .meta.items_deduped==2 and .meta.budget_used==5' >/dev/null || fail "meta counters wrong"
echo "$LINE" | jq -e '.meta.duration_ms|type=="number"' >/dev/null || fail "duration not numeric after stamp"
[ -f "$STAMP_FILE" ] && fail "stamp not cleaned after emit"

# 3. corrupt stamp → duration null (must NOT resolve to 0)
echo "not-a-number" > "$STAMP_FILE"
: > "$LOG"
"$SCRIPT" emit 1 0 1
cat "$LOG" | jq -e '.meta.duration_ms==null' >/dev/null || fail "corrupt stamp did not fall back to null"

# 4. missing stamp → duration null
trash-put "$STAMP_FILE" 2>/dev/null || true
: > "$LOG"
"$SCRIPT" emit 1 0 1
cat "$LOG" | jq -e '.meta.duration_ms==null' >/dev/null || fail "missing stamp did not fall back to null"

# 5. #528 batching regression guard: the 4 independent Phase-1 collect commands
# (stamp / report.py / sequence.py / prior-retro grep) must live in ONE fenced
# code block in retro/SKILL.md, not four separate ones (else the wrap chain
# pays 4 Bash-tool turns instead of 1).
SKILL="${SCRIPT_DIR}/../../skills/retro/SKILL.md"
BLOCK="$(awk '/retro-telemetry\.sh" stamp/{f=1} f{print} f&&/```$/{exit}' "$SKILL")"
echo "$BLOCK" | grep -q 'retro-telemetry.sh" stamp' || fail "#528: stamp missing from the combined collect block"
echo "$BLOCK" | grep -q 'report\.py"' || fail "#528: report.py not batched into the combined collect block"
echo "$BLOCK" | grep -q 'sequence\.py"' || fail "#528: sequence.py not batched into the combined collect block"
echo "$BLOCK" | grep -q 'name":"retro"' || fail "#528: prior-retro grep not batched into the combined collect block"

echo "OK: all retro-telemetry cases passed"
