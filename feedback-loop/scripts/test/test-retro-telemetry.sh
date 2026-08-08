#!/usr/bin/env bash
# Regression for feedback-loop/scripts/retro-telemetry.sh (the extracted retro
# Phase-1 stamp + Phase-3 emit helper). Asserts: opt-in gate, schema-shaped emit
# line with the three retro counters, numeric duration when a start_ms is
# passed through, the null fallback when it is missing/corrupt, and — #580 —
# that `stamp` never writes a /tmp file (the whole point of the redesign: a
# fresh shell per Bash-tool call means no process id is stable enough to key
# a shared file on, so the value travels as stdout text the skill carries
# forward instead).
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

# 1. opt-in off → no write, no stdout from stamp
STAMP_OFF="$( unset CLAUDE_KIT_TELEMETRY; "$SCRIPT" stamp )"
[ -z "$STAMP_OFF" ] || fail "stamp printed a value while telemetry off"
( unset CLAUDE_KIT_TELEMETRY; "$SCRIPT" emit 999999 1 1 1 )
[ -f "$LOG" ] && fail "wrote a line while telemetry off"

# 2. stamp + emit → one schema-shaped line, numeric duration, no /tmp file ever
BEFORE="$(ls /tmp | grep -c '^retro-start-' || true)"
START_MS="$("$SCRIPT" stamp)"
[[ "$START_MS" =~ ^[0-9]+$ ]] || fail "stamp did not print a numeric epoch-ms value (got: $START_MS)"
AFTER="$(ls /tmp | grep -c '^retro-start-' || true)"
[ "$BEFORE" = "$AFTER" ] || fail "#580: stamp wrote a /tmp/retro-start-* file (should be stdout-only)"
"$SCRIPT" emit "$START_MS" 5 2 5
LINE="$(cat "$LOG")"
echo "$LINE" | jq -e '.event=="skill_invoke" and .name=="retro" and .qualified_name=="feedback-loop:retro" and .plugin=="feedback-loop"' >/dev/null || fail "envelope shape wrong"
echo "$LINE" | jq -e '.meta.retro_items_processed==5 and .meta.items_deduped==2 and .meta.budget_used==5' >/dev/null || fail "meta counters wrong"
echo "$LINE" | jq -e '.meta.duration_ms|type=="number"' >/dev/null || fail "duration not numeric after stamp"
echo "$LINE" | jq -e '.meta.duration_ms>=0' >/dev/null || fail "duration negative"

# 3. corrupt start_ms → duration null (must NOT resolve to 0)
: > "$LOG"
"$SCRIPT" emit "not-a-number" 1 0 1
cat "$LOG" | jq -e '.meta.duration_ms==null' >/dev/null || fail "corrupt start_ms did not fall back to null"

# 4. missing start_ms → duration null
: > "$LOG"
"$SCRIPT" emit "" 1 0 1
cat "$LOG" | jq -e '.meta.duration_ms==null' >/dev/null || fail "missing start_ms did not fall back to null"

# 5. two overlapping "sessions" (no shared state left to collide on, #580 —
# the class of bug #529 patched around $PPID/$CLAUDE_SESSION_ID drift is now
# structurally impossible since nothing is written to disk between stamp and
# emit) never cross-contaminate each other's duration.
: > "$LOG"
START_A="$("$SCRIPT" stamp)"
START_B="$("$SCRIPT" stamp)"
"$SCRIPT" emit "$START_A" 3 1 3
"$SCRIPT" emit "$START_B" 7 2 7
LINE_COUNT="$(wc -l < "$LOG" | tr -d ' ')"
[ "$LINE_COUNT" = "2" ] || fail "expected 2 emitted lines, got $LINE_COUNT"
sed -n '1p' "$LOG" | jq -e '.meta.retro_items_processed==3 and (.meta.duration_ms|type=="number")' >/dev/null || fail "session A line wrong"
sed -n '2p' "$LOG" | jq -e '.meta.retro_items_processed==7 and (.meta.duration_ms|type=="number")' >/dev/null || fail "session B line wrong"

# 6. #528 batching regression guard: the 4 independent Phase-1 collect commands
# (stamp / report.py / sequence.py / prior-retro grep) must live in ONE fenced
# code block in retro/SKILL.md, not four separate ones (else the wrap chain
# pays 4 Bash-tool turns instead of 1).
SKILL="${SCRIPT_DIR}/../../skills/retro/SKILL.md"
BLOCK="$(awk '/retro-telemetry\.sh" stamp/{f=1} f{print} f&&/```$/{exit}' "$SKILL")"
echo "$BLOCK" | grep -q 'retro-telemetry.sh" stamp' || fail "#528: stamp missing from the combined collect block"
echo "$BLOCK" | grep -q 'report\.py"' || fail "#528: report.py not batched into the combined collect block"
echo "$BLOCK" | grep -q 'sequence\.py"' || fail "#528: sequence.py not batched into the combined collect block"
echo "$BLOCK" | grep -q 'name":"retro"' || fail "#528: prior-retro grep not batched into the combined collect block"

# 7. #580: Phase 3's emit call must pass START_MS as its first argument, not
# just the three counters (a partial edit that updated the helper but left
# the SKILL.md call site on the old 3-arg shape would silently duration=null
# forever, since $2 would be $PROCESSED, non-numeric, and always fall through).
grep -q 'retro-telemetry.sh" emit "\$START_MS" "\$PROCESSED" "\$DEDUPED" "\$BUDGET_USED"' "$SKILL" \
  || fail "#580: Phase 3 emit call site does not pass \$START_MS first"

echo "OK: all retro-telemetry cases passed"
