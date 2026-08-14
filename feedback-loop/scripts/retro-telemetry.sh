#!/usr/bin/env bash
# feedback-loop/scripts/retro-telemetry.sh — retro pipeline telemetry helper.
#
# Extracts the duration-stamp + emit bash that was inlined twice in
# skills/retro/SKILL.md (Phase 1 stamp, Phase 3 emit). Inlining it in two
# places risked drifting from event-logger.sh's shared conventions (events-dir
# resolution, opt-in gate, schema envelope, PIPE_BUF guard). This helper owns
# those once so the skill body just calls it.
#
# Opt-in + best-effort + silent, exactly like event-logger.sh: it does nothing
# unless CLAUDE_KIT_TELEMETRY=1 AND the events dir is resolvable, and every
# failure exits 0 without output (stdout/stderr must stay clean in the
# LLM-visible path) — except `stamp`'s one line of stdout, which the retro
# skill body is expected to read and carry forward (see below).
#
# Events-dir rule (single shared rule, same as event-logger.sh):
#   ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}/.claude-kit/telemetry/events}
#
# Usage:
#   retro-telemetry.sh stamp
#       Print the Phase-1 start time (epoch ms) to stdout. No file is written:
#       Phase 1 and Phase 3 are separate Bash-tool calls (fresh shell each
#       time), so there is no process/session id stable enough to key a
#       shared /tmp file on (#580 — $PPID/$CLAUDE_SESSION_ID both drift
#       between the two calls in practice, corrupting duration_ms and
#       orphaning stamp files). The retro skill itself connects the two
#       calls: it reads this stdout value and inlines it as the first
#       argument to Phase 3's `emit` call below.
#   retro-telemetry.sh emit <start_ms> <processed> <deduped> <budget_used>
#       Append ONE schema-valid retro skill_invoke line whose meta carries the
#       three retro counters PLUS duration_ms (now − start_ms; null when
#       start_ms is missing/non-numeric). (items_promoted was dropped with
#       the PROMOTE phase, #480 — retro no longer writes the vault.)

set -uo pipefail

# --- opt-in gate + events dir (single shared rule) -------------------------
[ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] || exit 0
PROJ_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")}"
EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${PROJ_ROOT}/.claude-kit/telemetry/events}"
[ -d "$EVENTS_DIR" ] || exit 0

now_ms() { python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || true; }

case "${1:-}" in
  stamp)
    now_ms
    ;;

  emit)
    # duration_ms = now − start_ms (passed in, not read off disk); require
    # both all-digits before arithmetic so a missing/corrupt start_ms falls
    # back to null, not a bogus 0.
    START_MS="${2:-}"; PROCESSED="${3:-0}"; DEDUPED="${4:-0}"; BUDGET_USED="${5:-0}"
    END_MS="$(now_ms)"
    if [[ "$START_MS" =~ ^[0-9]+$ ]] && [[ "$END_MS" =~ ^[0-9]+$ ]]; then
      DURATION_MS=$((END_MS - START_MS))
    else
      DURATION_MS=null
    fi
    LINE="$(jq -nc \
      --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --arg sid "${CLAUDE_SESSION_ID:-unknown}" --arg cwd "$PROJ_ROOT" \
      --argjson processed "$PROCESSED" \
      --argjson deduped "$DEDUPED" --argjson budget "$BUDGET_USED" \
      --argjson duration "$DURATION_MS" \
      '{ts:$ts, session_id:$sid, cwd:$cwd, plugin:"feedback-loop",
        event:"skill_invoke", name:"retro", qualified_name:"feedback-loop:retro",
        trigger:"explicit", outcome:"success", tool_use_id:"",
        meta:{retro_items_processed:$processed,
              items_deduped:$deduped, budget_used:$budget, duration_ms:$duration}}' 2>/dev/null)"
    # PIPE_BUF guard mirrors event-logger.sh / validate-schema.py (3500B).
    [ -n "$LINE" ] && [ "${#LINE}" -lt 3500 ] && \
      { printf '%s\n' "$LINE" >> "${EVENTS_DIR}/events-$(date -u +%Y-%m-%d).jsonl"; } 2>/dev/null
    ;;

  *)
    exit 0
    ;;
esac

exit 0
