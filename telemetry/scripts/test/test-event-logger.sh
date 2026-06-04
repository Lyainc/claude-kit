#!/usr/bin/env bash
# telemetry/scripts/test/test-event-logger.sh
#
# Unit test for event-logger.sh's meta extractors (extract_end_meta /
# extract_stop_meta) against SYNTHETIC hook payloads. This is the verification
# vehicle for the unverified stop `.usage` key path (#153 Item 2): real Stop
# payloads are not available here, so the contract is locked against synthetic
# fixtures instead.
#
# Coverage:
#   - happy path (full tool_response.usage / .usage block)
#   - missing tool_response  -> {duration_ms:null} (end) / {} (stop)
#   - missing usage          -> tokens omitted, duration preserved where present
#   - jq-invalid payload     -> safe {} fallback (no stray output, no crash)
#
# Standalone-runnable. Exits non-zero on any assertion failure.
#
# Strategy: event-logger.sh is a flat script (opt-in gate + side-effecting case
# body), so sourcing it whole would run the logging path. We instead slice out
# only the two pure functions by their name markers and source that slice. This
# keeps the test free of file writes and the opt-in gate.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="${SCRIPT_DIR}/../../event-logger.sh"

if [ ! -f "$LOGGER" ]; then
  printf 'FAIL: cannot find event-logger.sh at %s\n' "$LOGGER" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  printf 'FAIL: jq not found on PATH (required by the extractors)\n' >&2
  exit 1
fi

# --- Slice the two pure functions out of the logger and source them ----------
# awk prints each `name() { ... }` block: start at the function header, stop
# after the first line that is a bare `}` at column 0 (the function closer).
# CONSTRAINT: this name-marker slice assumes each extractor's closing brace is
# the FIRST bare `}` at column 0 in its body. If a function ever introduces a
# column-0 `}` (e.g. a heredoc terminator or a nested subshell brace flush-left),
# the slice would cut early and the sourced function would be malformed. The two
# extractors keep all inner braces indented, so the marker holds — preserve that
# (indent inner braces) when editing event-logger.sh's extract_* functions.
FN_SLICE="$(mktemp 2>/dev/null || printf '/tmp/test-event-logger-%s.sh' "$$")"
trap 'rm -f "$FN_SLICE"' EXIT

awk '
  /^extract_end_meta\(\)/  { grab=1 }
  /^extract_stop_meta\(\)/ { grab=1 }
  grab { print }
  grab && /^}/ { grab=0 }
' "$LOGGER" > "$FN_SLICE"

# shellcheck disable=SC1090
. "$FN_SLICE"

if ! declare -F extract_end_meta >/dev/null 2>&1; then
  printf 'FAIL: extract_end_meta not defined after sourcing slice\n' >&2
  exit 1
fi
if ! declare -F extract_stop_meta >/dev/null 2>&1; then
  printf 'FAIL: extract_stop_meta not defined after sourcing slice\n' >&2
  exit 1
fi

# --- Tiny assertion harness --------------------------------------------------
FAILURES=0
PASSES=0

# Compare two JSON strings for semantic equality (key order independent) via jq.
assert_json_eq() {
  local label="$1" got="$2" want="$3"
  if jq -e --argjson a "$got" --argjson b "$want" -n '$a == $b' >/dev/null 2>&1; then
    PASSES=$((PASSES + 1))
    printf 'ok   %s\n' "$label"
  else
    FAILURES=$((FAILURES + 1))
    printf 'FAIL %s\n     got:  %s\n     want: %s\n' "$label" "$got" "$want" >&2
  fi
}

# ============================================================================
# extract_end_meta — PostToolUse end-event meta
# ============================================================================

# Happy path: duration + full usage block.
end_happy='{
  "tool_response": {
    "duration_ms": 1234,
    "usage": {
      "input_tokens": 500,
      "output_tokens": 120,
      "cache_read_input_tokens": 42
    }
  }
}'
assert_json_eq "end:happy full usage" \
  "$(extract_end_meta "$end_happy")" \
  '{"duration_ms":1234,"input_tokens":500,"output_tokens":120,"cache_read_tokens":42}'

# Missing tool_response entirely: duration falls back to top-level (.duration_ms),
# absent here too -> null. No usage -> token keys omitted.
end_no_response='{"session_id":"x"}'
assert_json_eq "end:missing tool_response -> duration null, no tokens" \
  "$(extract_end_meta "$end_no_response")" \
  '{"duration_ms":null}'

# Top-level duration_ms fallback when tool_response lacks it.
end_toplevel_dur='{"duration_ms":99,"tool_response":{}}'
assert_json_eq "end:top-level duration_ms fallback" \
  "$(extract_end_meta "$end_toplevel_dur")" \
  '{"duration_ms":99}'

# Missing usage block: duration present, all token keys omitted.
end_no_usage='{"tool_response":{"duration_ms":7}}'
assert_json_eq "end:missing usage -> tokens omitted" \
  "$(extract_end_meta "$end_no_usage")" \
  '{"duration_ms":7}'

# Partial usage: only some token fields present -> only those emitted.
end_partial_usage='{"tool_response":{"duration_ms":5,"usage":{"input_tokens":10}}}'
assert_json_eq "end:partial usage -> only present tokens" \
  "$(extract_end_meta "$end_partial_usage")" \
  '{"duration_ms":5,"input_tokens":10}'

# Explicit null token field -> omitted (the != null guard).
end_null_token='{"tool_response":{"duration_ms":5,"usage":{"input_tokens":null,"output_tokens":3}}}'
assert_json_eq "end:null token field omitted" \
  "$(extract_end_meta "$end_null_token")" \
  '{"duration_ms":5,"output_tokens":3}'

# jq-invalid payload -> safe {} fallback, no crash, no stray stdout.
end_invalid='{ this is not json'
assert_json_eq "end:jq-invalid -> {} fallback" \
  "$(extract_end_meta "$end_invalid")" \
  '{}'

# ============================================================================
# extract_stop_meta — Stop-event turn-usage meta (#153 synthetic verification)
# ============================================================================

# Happy path: a .usage block with turn token totals (the UNVERIFIED key path —
# this synthetic case is exactly what locks its current shape).
stop_happy='{"usage":{"input_tokens":1500,"output_tokens":300}}'
assert_json_eq "stop:happy .usage -> turn tokens" \
  "$(extract_stop_meta "$stop_happy")" \
  '{"turn_input_tokens":1500,"turn_output_tokens":300}'

# Missing usage entirely -> empty meta {}.
stop_no_usage='{"session_id":"x"}'
assert_json_eq "stop:missing usage -> {}" \
  "$(extract_stop_meta "$stop_no_usage")" \
  '{}'

# Partial usage: only input present.
stop_partial='{"usage":{"input_tokens":42}}'
assert_json_eq "stop:partial usage -> only present token" \
  "$(extract_stop_meta "$stop_partial")" \
  '{"turn_input_tokens":42}'

# Null token field -> omitted.
stop_null='{"usage":{"input_tokens":null,"output_tokens":9}}'
assert_json_eq "stop:null token field omitted" \
  "$(extract_stop_meta "$stop_null")" \
  '{"turn_output_tokens":9}'

# jq-invalid payload -> safe {} fallback.
stop_invalid='}{ broken'
assert_json_eq "stop:jq-invalid -> {} fallback" \
  "$(extract_stop_meta "$stop_invalid")" \
  '{}'

# --- Summary -----------------------------------------------------------------
printf '\n%d passed, %d failed\n' "$PASSES" "$FAILURES"
if [ "$FAILURES" -ne 0 ]; then
  exit 1
fi
printf 'OK: all event-logger meta-extractor cases passed\n'
exit 0
