#!/usr/bin/env bash
# telemetry/event-logger.sh — claude-kit Phase 1 local dogfooding logger.
#
# Opt-in: logs only when CLAUDE_KIT_TELEMETRY=1. Otherwise silent exit 0.
#
# Invariants:
#   - stdout/stderr MUST be empty in the LLM-visible path. Hook handlers feed
#     Claude's context; any stray output pollutes the model. All writes go to
#     files; jq errors are swallowed.
#   - jsonl append uses POSIX O_APPEND single write() for sub-PIPE_BUF lines
#     (~600B by schema). Lockless by design — see telemetry/README.md
#     "Lock strategy" for the atomicity argument.
#   - Hook failures must never break a turn — jq errors and missing fields
#     fall through to a best-effort entry or silent exit.
#
# Phase 2 portability (rev3 Principle #6):
#   - Path uses ${BASH_SOURCE[0]}-resolved SCRIPT_DIR (self-relative). No
#     hard-coded absolute paths inside this handler.
#   - Migration map: telemetry/ → ${CLAUDE_PLUGIN_ROOT}/scripts/ at Phase 2.
#
# Invocation:
#   event-logger.sh <event_type>   < hook_payload_json
#
# Event types (one per hook registration):
#   skill_invoke_start  skill_invoke_end
#   agent_spawn_start   agent_spawn_end
#   command_run         stop
#   session_start       session_end

set -uo pipefail

# --- 1. Opt-in gate (silent exit if not enabled) ---------------------------
[ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] || exit 0

# --- 2. Resolve telemetry root from script location ------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || exit 0
LOG_DIR="${SCRIPT_DIR}/events"
LOG_FILE="${LOG_DIR}/events-$(date -u +%Y-%m-%d).jsonl"
PLUGIN_MAP="${SCRIPT_DIR}/plugin-map.json"

mkdir -p "$LOG_DIR" 2>/dev/null || exit 0

EVENT_TYPE="${1:-}"
[ -n "$EVENT_TYPE" ] || exit 0

# --- 3. Read payload (may be empty for some hook events) -------------------
PAYLOAD="$(cat 2>/dev/null || printf '{}')"
[ -n "$PAYLOAD" ] || PAYLOAD='{}'

# --- 4. Common fields ------------------------------------------------------
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SESSION_ID="$(printf '%s' "$PAYLOAD" | jq -r '.session_id // empty' 2>/dev/null || true)"
CWD="$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null || true)"
[ -n "$CWD" ] || CWD="${PWD:-}"
TOOL_USE_ID="$(printf '%s' "$PAYLOAD" | jq -r '.tool_use_id // empty' 2>/dev/null || true)"

# --- 5. Plugin resolver ----------------------------------------------------
# qualified name "plugin:skill" → plugin; bare name → plugin-map.json lookup;
# otherwise "unknown".
resolve_plugin() {
  local qname="$1"
  local bare="$2"
  case "$qname" in
    *:*) printf '%s' "${qname%%:*}"; return ;;
  esac
  if [ -n "$bare" ] && [ -f "$PLUGIN_MAP" ]; then
    local mapped
    mapped="$(jq -r --arg n "$bare" '.[$n] // empty' "$PLUGIN_MAP" 2>/dev/null || true)"
    if [ -n "$mapped" ]; then
      printf '%s' "$mapped"
      return
    fi
  fi
  printf 'unknown'
}

# Build the meta object for PostToolUse end events (skill_invoke_end /
# agent_spawn_end). Token counts come from tool_response.usage.* and are
# dropped entirely when absent or explicitly null (`!= null` guard → key
# omitted), so empty/garbage keys never pollute the schema. duration_ms is
# emitted as null when the payload carries no timing, per the schema contract
# (Latency analysis treats null as "no datum"). Any jq error → `{}`.
extract_end_meta() {
  local payload="$1"
  printf '%s' "$payload" | jq -c '
    (.tool_response // {}) as $r
    | ($r.usage // {}) as $u
    | {duration_ms: ($r.duration_ms // .duration_ms // null)}
      + (if ($u.input_tokens != null) then {input_tokens: $u.input_tokens} else {} end)
      + (if ($u.output_tokens != null) then {output_tokens: $u.output_tokens} else {} end)
      + (if ($u.cache_read_input_tokens != null) then {cache_read_tokens: $u.cache_read_input_tokens} else {} end)
  ' 2>/dev/null || printf '{}'
}

# Build the meta object for the Stop event. Turn token totals come from a
# usage block on the Stop payload when present; absent/null keys are omitted.
extract_stop_meta() {
  local payload="$1"
  printf '%s' "$payload" | jq -c '
    (.usage // {}) as $u
    | {}
      + (if ($u.input_tokens != null) then {turn_input_tokens: $u.input_tokens} else {} end)
      + (if ($u.output_tokens != null) then {turn_output_tokens: $u.output_tokens} else {} end)
  ' 2>/dev/null || printf '{}'
}

# --- 6. Per-event field extraction -----------------------------------------
PLUGIN=""
NAME=""
QNAME=""
TRIGGER=""
OUTCOME=""
# META holds a JSON object string injected via --argjson at compose time.
# Empty inner keys are omitted (jq `// empty`) to avoid schema pollution; an
# event with no extractable telemetry stays `{}`. jq failures fall back to {}.
META='{}'

case "$EVENT_TYPE" in
  skill_invoke_start|skill_invoke_end)
    QNAME="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)"
    case "$QNAME" in
      *:*) NAME="${QNAME##*:}" ;;
      *)   NAME="$QNAME" ;;
    esac
    PLUGIN="$(resolve_plugin "$QNAME" "$NAME")"
    TRIGGER="explicit"
    if [ "$EVENT_TYPE" = "skill_invoke_start" ]; then
      OUTCOME="started"
    else
      if printf '%s' "$PAYLOAD" | jq -e '.tool_response.is_error // false' >/dev/null 2>&1; then
        OUTCOME="error"
      elif printf '%s' "$PAYLOAD" | jq -e '.tool_response.permission_denied // false' >/dev/null 2>&1; then
        OUTCOME="blocked"
      else
        OUTCOME="success"
      fi
      META="$(extract_end_meta "$PAYLOAD")"
    fi
    ;;

  agent_spawn_start|agent_spawn_end)
    NAME="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null || true)"
    QNAME="$NAME"
    PLUGIN="$(resolve_plugin "$QNAME" "$NAME")"
    TRIGGER="explicit"
    if [ "$EVENT_TYPE" = "agent_spawn_start" ]; then
      OUTCOME="started"
    else
      if printf '%s' "$PAYLOAD" | jq -e '.tool_response.is_error // false' >/dev/null 2>&1; then
        OUTCOME="error"
      else
        OUTCOME="success"
      fi
      META="$(extract_end_meta "$PAYLOAD")"
    fi
    ;;

  command_run)
    PROMPT="$(printf '%s' "$PAYLOAD" | jq -r '.prompt // empty' 2>/dev/null || true)"
    # First whitespace-token of first non-empty line.
    FIRST_TOKEN="$(printf '%s' "$PROMPT" | awk 'NF{print $1; exit}' 2>/dev/null || true)"
    case "$FIRST_TOKEN" in
      /*)
        QNAME="${FIRST_TOKEN#/}"
        case "$QNAME" in
          *:*) NAME="${QNAME##*:}" ;;
          *)   NAME="$QNAME" ;;
        esac
        PLUGIN="$(resolve_plugin "$QNAME" "$NAME")"
        TRIGGER="explicit"
        OUTCOME="started"
        ;;
      *)
        exit 0  # Not a slash command — skip silently.
        ;;
    esac
    ;;

  session_start|session_end|stop)
    PLUGIN="claude-kit"
    TRIGGER="auto"
    OUTCOME="success"
    if [ "$EVENT_TYPE" = "stop" ]; then
      META="$(extract_stop_meta "$PAYLOAD")"
    fi
    ;;

  *)
    exit 0
    ;;
esac

# Logical event field (collapse start/end variants).
case "$EVENT_TYPE" in
  skill_invoke_*) EVENT="skill_invoke" ;;
  agent_spawn_*)  EVENT="agent_spawn" ;;
  *)              EVENT="$EVENT_TYPE" ;;
esac

# Guard: a blank META (jq error / empty substitution) must not break --argjson.
[ -n "$META" ] || META='{}'

# --- 7. Compose jsonl line via jq -nc (single output line) -----------------
LINE="$(
  jq -nc \
    --arg ts          "$TS" \
    --arg session_id  "$SESSION_ID" \
    --arg cwd         "$CWD" \
    --arg plugin      "$PLUGIN" \
    --arg event       "$EVENT" \
    --arg name        "$NAME" \
    --arg qname       "$QNAME" \
    --arg trigger     "$TRIGGER" \
    --arg outcome     "$OUTCOME" \
    --arg tool_use_id "$TOOL_USE_ID" \
    --argjson meta    "$META" \
    '{
      ts: $ts,
      session_id: $session_id,
      cwd: $cwd,
      plugin: $plugin,
      event: $event,
      name: $name,
      qualified_name: $qname,
      trigger: $trigger,
      outcome: $outcome,
      tool_use_id: $tool_use_id,
      meta: $meta
    }' 2>/dev/null
)"

[ -n "$LINE" ] || exit 0

# --- 8. Single-write append (sub-PIPE_BUF, atomic by POSIX O_APPEND) -------
# PIPE_BUF safety: skip writes that approach the POSIX atomic-append guarantee.
# Threshold mirrors validate-schema.py PIPE_BUF_WARN_BYTES (3500). If meta ever
# balloons a line past this, drop the event silently rather than tear writes.
[ "${#LINE}" -lt 3500 ] || exit 0
printf '%s\n' "$LINE" >> "$LOG_FILE" 2>/dev/null

exit 0
