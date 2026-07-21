#!/usr/bin/env bash
# feedback-loop/scripts/event-logger.sh — claude-kit local dogfooding logger.
#
# Opt-in: logs only when CLAUDE_KIT_TELEMETRY=1. Otherwise silent exit 0.
#
# Invariants:
#   - stdout/stderr MUST be empty in the LLM-visible path. Hook handlers feed
#     Claude's context; any stray output pollutes the model. All writes go to
#     files; jq errors are swallowed.
#   - jsonl append uses POSIX O_APPEND single write() for sub-PIPE_BUF lines
#     (~600B by schema). Lockless by design — see feedback-loop/README.md
#     "Lock strategy" for the atomicity argument.
#   - Hook failures must never break a turn — jq errors and missing fields
#     fall through to a best-effort entry or silent exit.
#
# Path resolution (CON-2 deterministic):
#   - ${CLAUDE_PLUGIN_ROOT} resolves THIS handler in the plugin.json hook command
#     path only — never the events output path.
#   - The events OUTPUT dir is user-writable (NOT the plugin install cache):
#       ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}/.claude-kit/telemetry/events}
#     This is the single events-dir rule shared by retro + report/validate scripts.
#   - plugin-map.json ships with the plugin, so it stays SCRIPT_DIR-relative.
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

# --- 2. Resolve paths ------------------------------------------------------
# plugin-map.json ships with the plugin (SCRIPT_DIR-relative). The events dir is
# user-writable and resolved by the single shared rule (env override → project
# root → never the install cache).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || exit 0
# $PWD is the hook's CWD, which is NOT the project root when a hook fires from a
# subdirectory — that scattered .claude-kit/telemetry/ dirs across 5 subdirs
# (feedback-loop/, .github/ISSUE_TEMPLATE/, ...). git toplevel is the stable anchor.
PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")}"
LOG_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${PROJECT_ROOT}/.claude-kit/telemetry/events}"
LOG_FILE="${LOG_DIR}/events-$(date -u +%Y-%m-%d).jsonl"
PLUGIN_MAP="${SCRIPT_DIR}/plugin-map.json"

mkdir -p "$LOG_DIR" 2>/dev/null || exit 0

EVENT_TYPE="${1:-}"
[ -n "$EVENT_TYPE" ] || exit 0

# --- 3. Read payload (may be empty for some hook events) -------------------
PAYLOAD="$(cat 2>/dev/null || printf '{}')"
[ -n "$PAYLOAD" ] || PAYLOAD='{}'

# --- 3b. Optional raw-payload capture (dogfooding instrument) ---------------
# Gate: CLAUDE_KIT_TELEMETRY_DUMP_PAYLOAD=1. When set, append the raw stdin
# payload (verbatim, one JSON object per line) to a per-event-type dump file
# under events/raw/. This was the #153/#168 dogfooding hook used to confirm the
# real Stop hook payload shape (see extract_stop_meta below — resolved). Kept
# as a general capture instrument for future payload-shape questions on other
# event types. Silent + best-effort: any failure (mkdir, write) falls through
# without affecting the logging path. Like VAULT_BRIDGE_DUMP_PAYLOAD (README
# "History"), enable it only for the ONE session you need to inspect.
if [ "${CLAUDE_KIT_TELEMETRY_DUMP_PAYLOAD:-}" = "1" ]; then
  RAW_DIR="${LOG_DIR}/raw"
  if mkdir -p "$RAW_DIR" 2>/dev/null; then
    # Compact to a single line so the dump file stays one-payload-per-line even
    # if the hook delivers pretty-printed JSON. jq failure (non-JSON) → raw
    # bytes are still captured so a malformed payload is not silently lost.
    DUMP_LINE="$(printf '%s' "$PAYLOAD" | jq -c . 2>/dev/null)"
    [ -n "$DUMP_LINE" ] || DUMP_LINE="$PAYLOAD"
    # Traversal guard: strip any chars outside [a-z0-9_-] so a crafted EVENT_TYPE
    # like "../../foo" cannot escape the events/raw/ directory.
    EVENT_TYPE_SAFE="$(printf '%s' "$EVENT_TYPE" | tr -cd 'a-z0-9_-')"
    [ -n "$EVENT_TYPE_SAFE" ] || EVENT_TYPE_SAFE=unknown
    printf '%s\n' "$DUMP_LINE" >> "${RAW_DIR}/${EVENT_TYPE_SAFE}.jsonl" 2>/dev/null || true
  fi
fi

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

# Build the meta object for the Stop event.
#
# CONFIRMED (#168, resolves #153): a real Stop hook payload was captured via
# CLAUDE_KIT_TELEMETRY_DUMP_PAYLOAD=1 against a live Claude Code session. Its
# keys are session_id, transcript_path, cwd, prompt_id, permission_mode,
# effort, hook_event_name, stop_hook_active, last_assistant_message,
# background_tasks, session_crons — no usage/token field anywhere, not
# `.usage.*`, `.turn_usage.*`, `.message.usage.*`, nor a top-level token field.
# Stop simply carries no per-turn token usage, so turn-token telemetry is
# dropped for this event type. This extractor is a confirmed no-op, kept only
# as the single wiring point if a future Stop schema ever adds real usage data.
extract_stop_meta() {
  printf '{}'
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

  rule_fire)
    # A work-rule guard fired (a check-*.py violation, a task-end reminder, or a
    # landed add-policy hook guard catching a violation). The schema reserves this
    # event (validate-schema.py VALID_EVENTS); this case fills the previously-empty
    # emitter slot. EMIT-ONLY data contract (CON-5): the guard shells out to THIS
    # script — a process call, never a code import — so feedback-loop pulls in no
    # leaf/guard code. Identity (G20 #258): rule_fire carries no tool_input; its
    # rule_id rides in the incoming meta, so we LIFT meta.rule_id into name /
    # qualified_name — report.py's `top` keys on (plugin, event, name), so without
    # the lift every rule would collapse into one undifferentiated bucket.
    NAME="$(printf '%s' "$PAYLOAD" | jq -r '.meta.rule_id // empty' 2>/dev/null || true)"
    QNAME="$NAME"
    # plugin: an optional meta.plugin (which harness owns the rule), else claude-kit.
    PLUGIN="$(printf '%s' "$PAYLOAD" | jq -r '.meta.plugin // "claude-kit"' 2>/dev/null || printf 'claude-kit')"
    [ -n "$PLUGIN" ] || PLUGIN="claude-kit"
    TRIGGER="auto"
    OUTCOME="fired"
    # Pass through the conventional rule_fire meta keys (rule_id / severity / file /
    # count), dropping any that are absent/null so the envelope stays clean. This is
    # liveness telemetry: a fire means a violation was CAUGHT, never that a rule was
    # "followed" — a perfectly-obeyed rule fires zero times (G20 honesty contract).
    META="$(printf '%s' "$PAYLOAD" | jq -c '
      (.meta // {}) as $m
      | {}
        + (if ($m.rule_id  != null) then {rule_id:  $m.rule_id}  else {} end)
        + (if ($m.severity != null) then {severity: $m.severity} else {} end)
        + (if ($m.file     != null) then {file:     $m.file}     else {} end)
        + (if ($m.count    != null) then {count:    $m.count}    else {} end)
    ' 2>/dev/null || printf '{}')"
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
