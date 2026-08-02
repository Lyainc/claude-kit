#!/usr/bin/env bash
# feedback-loop/scripts/test/test-event-logger.sh
#
# Unit test for event-logger.sh's meta extractors (extract_end_meta /
# extract_stop_meta) and the .session-model cache sweep (cleanup_stale_session_models,
# #514) against SYNTHETIC hook payloads / fixture files.
#
# Coverage:
#   - happy path (full tool_response.usage block)
#   - missing tool_response  -> {duration_ms:null} (end)
#   - missing usage          -> tokens omitted, duration preserved where present
#   - jq-invalid payload     -> safe {} fallback (no stray output, no crash)
#   - extract_stop_meta always -> {} (confirmed #168: real Stop payloads carry
#     no usage/token field at any key path, see event-logger.sh's extractor)
#   - cleanup_stale_session_models removes files older than the stale threshold
#     and preserves recent ones (#514)
#
# Standalone-runnable. Exits non-zero on any assertion failure.
#
# Strategy: event-logger.sh is a flat script (opt-in gate + side-effecting case
# body), so sourcing it whole would run the logging path. We instead slice out
# only the pure functions by their name markers and source that slice. This
# keeps the test free of file writes and the opt-in gate.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# event-logger.sh sits one level up (scripts/), test lives in scripts/test/.
LOGGER="${SCRIPT_DIR}/../event-logger.sh"

if [ ! -f "$LOGGER" ]; then
  printf 'FAIL: cannot find event-logger.sh at %s\n' "$LOGGER" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  printf 'FAIL: jq not found on PATH (required by the extractors)\n' >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf 'FAIL: python3 not found on PATH (required to backdate fixture files)\n' >&2
  exit 1
fi

# --- Slice the pure functions out of the logger and source them ------------
# awk prints each `name() { ... }` block: start at the function header, stop
# after the first line that is a bare `}` at column 0 (the function closer).
# CONSTRAINT: this name-marker slice assumes each function's closing brace is
# the FIRST bare `}` at column 0 in its body. If a function ever introduces a
# column-0 `}` (e.g. a heredoc terminator or a nested subshell brace flush-left),
# the slice would cut early and the sourced function would be malformed. These
# functions keep all inner braces indented, so the marker holds — preserve that
# (indent inner braces) when editing event-logger.sh's extract_*/cleanup_* functions.
FN_SLICE="$(mktemp 2>/dev/null || printf '/tmp/test-event-logger-%s.sh' "$$")"
MODEL_DIR="$(mktemp -d 2>/dev/null || printf '/tmp/test-event-logger-model-%s' "$$")"
CLEANUP_DIR="$(mktemp -d 2>/dev/null || printf '/tmp/test-event-logger-cleanup-%s' "$$")"
mkdir -p "$MODEL_DIR" "$CLEANUP_DIR" 2>/dev/null || true
trap 'rm -f "$FN_SLICE"; rm -rf "$MODEL_DIR" "$CLEANUP_DIR"' EXIT

awk '
  /^extract_end_meta\(\)/  { grab=1 }
  /^extract_stop_meta\(\)/ { grab=1 }
  /^cleanup_stale_session_models\(\)/ { grab=1 }
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
if ! declare -F cleanup_stale_session_models >/dev/null 2>&1; then
  printf 'FAIL: cleanup_stale_session_models not defined after sourcing slice\n' >&2
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
# extract_end_meta — meta.model relay from session-scoped state (#511)
# ============================================================================

# session_id has a cached model -> meta.model rides alongside duration/tokens.
printf '%s' "claude-sonnet-5" > "${MODEL_DIR}/sess-1"
assert_json_eq "end:cached session model injected" \
  "$(extract_end_meta "$end_happy" "sess-1" "$MODEL_DIR")" \
  '{"duration_ms":1234,"input_tokens":500,"output_tokens":120,"cache_read_tokens":42,"model":"claude-sonnet-5"}'

# session_id with no cached model file -> model key omitted, same as no session_id.
assert_json_eq "end:no cached model -> model omitted" \
  "$(extract_end_meta "$end_happy" "sess-unknown" "$MODEL_DIR")" \
  '{"duration_ms":1234,"input_tokens":500,"output_tokens":120,"cache_read_tokens":42}'

# Traversal-guard: a crafted session_id with path-escape chars is sanitized before
# the filesystem lookup, so it neither crashes nor reads outside MODEL_DIR.
assert_json_eq "end:traversal-guard session_id -> model omitted safely" \
  "$(extract_end_meta "$end_happy" "../../etc/passwd" "$MODEL_DIR")" \
  '{"duration_ms":1234,"input_tokens":500,"output_tokens":120,"cache_read_tokens":42}'

# ============================================================================
# extract_stop_meta — Stop-event meta (#168 confirmed: no usage in real payload)
# ============================================================================

# A real Stop payload shape (session_id/transcript_path/cwd/prompt_id/
# permission_mode/effort/hook_event_name/stop_hook_active/last_assistant_message/
# background_tasks/session_crons, captured #168) carries no usage/token field.
stop_real_shape='{"session_id":"x","transcript_path":"/x.jsonl","cwd":"/","prompt_id":"p","permission_mode":"default","effort":{"level":"xhigh"},"hook_event_name":"Stop","stop_hook_active":false,"last_assistant_message":"2","background_tasks":[],"session_crons":[]}'
assert_json_eq "stop:real payload shape -> {}" \
  "$(extract_stop_meta "$stop_real_shape")" \
  '{}'

# Even a payload that happens to carry a .usage-shaped block -> still {}
# (extractor no longer reads the payload at all; kept for signature compat).
stop_with_usage_shaped_field='{"usage":{"input_tokens":1500,"output_tokens":300}}'
assert_json_eq "stop:.usage-shaped field ignored -> {}" \
  "$(extract_stop_meta "$stop_with_usage_shaped_field")" \
  '{}'

# jq-invalid payload -> still {} (no crash; extractor doesn't touch the arg).
stop_invalid='}{ broken'
assert_json_eq "stop:jq-invalid -> {} fallback" \
  "$(extract_stop_meta "$stop_invalid")" \
  '{}'

# ============================================================================
# cleanup_stale_session_models — .session-model cache sweep (#514)
# ============================================================================

SESSION_MODEL_STALE_DAYS=2

# Fixture: one stale file (backdated well past the threshold) + one recent file.
OLD_FILE="${CLEANUP_DIR}/old-session"
RECENT_FILE="${CLEANUP_DIR}/recent-session"
printf 'claude-sonnet-5' > "$OLD_FILE"
printf 'claude-sonnet-5' > "$RECENT_FILE"
OLD_TS="$(python3 -c "import datetime; print((datetime.datetime.now()-datetime.timedelta(days=5)).strftime('%Y%m%d%H%M.%S'))")"
touch -t "$OLD_TS" "$OLD_FILE"

cleanup_stale_session_models "$CLEANUP_DIR"

if [ -f "$OLD_FILE" ]; then
  FAILURES=$((FAILURES + 1))
  printf 'FAIL cleanup: stale file (>%dd old) not removed\n' "$SESSION_MODEL_STALE_DAYS" >&2
else
  PASSES=$((PASSES + 1))
  printf 'ok   cleanup: stale file removed\n'
fi

if [ -f "$RECENT_FILE" ]; then
  PASSES=$((PASSES + 1))
  printf 'ok   cleanup: recent file preserved\n'
else
  FAILURES=$((FAILURES + 1))
  printf 'FAIL cleanup: recent file was wrongly removed\n' >&2
fi

# A missing directory (never yet created) must be a silent no-op, not a crash —
# this is the state on a brand-new project before the first session_start.
if cleanup_stale_session_models "${CLEANUP_DIR}/does-not-exist" >/dev/null 2>&1; then
  PASSES=$((PASSES + 1))
  printf 'ok   cleanup: missing directory is a silent no-op\n'
else
  FAILURES=$((FAILURES + 1))
  printf 'FAIL cleanup: missing directory caused a non-zero exit\n' >&2
fi

# --- Summary -----------------------------------------------------------------
printf '\n%d passed, %d failed\n' "$PASSES" "$FAILURES"
if [ "$FAILURES" -ne 0 ]; then
  exit 1
fi
printf 'OK: all event-logger meta-extractor cases passed\n'
exit 0
