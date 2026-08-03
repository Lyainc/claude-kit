#!/usr/bin/env bash
# feedback-loop/scripts/retro-telemetry.sh — retro pipeline telemetry helper.
#
# Extracts the duration-stamp + emit bash that was inlined twice in
# skills/retro/SKILL.md (Phase 1 stamp, Phase 4 emit). Inlining it in two
# places risked drifting from event-logger.sh's shared conventions (events-dir
# resolution, opt-in gate, schema envelope, PIPE_BUF guard). This helper owns
# those once so the skill body just calls it.
#
# Opt-in + best-effort + silent, exactly like event-logger.sh: it does nothing
# unless CLAUDE_KIT_TELEMETRY=1 AND the events dir is resolvable, and every
# failure exits 0 without output (stdout/stderr must stay clean in the
# LLM-visible path).
#
# Events-dir rule (single shared rule, same as event-logger.sh):
#   ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}/.claude-kit/telemetry/events}
#
# Usage:
#   retro-telemetry.sh stamp
#       Write the Phase-1 start time (ms) to the per-session stamp file.
#   retro-telemetry.sh emit <processed> <deduped> <budget_used>
#       Append ONE schema-valid retro skill_invoke line whose meta carries the
#       three retro counters PLUS duration_ms (now − stamp; null when the stamp
#       is missing/corrupt), then remove the stamp. (items_promoted was dropped
#       with the PROMOTE phase, #480 — retro no longer writes the vault.)

set -uo pipefail

# --- opt-in gate + events dir (single shared rule) -------------------------
[ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] || exit 0
PROJ_ROOT="${CLAUDE_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")}"
EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${PROJ_ROOT}/.claude-kit/telemetry/events}"
[ -d "$EVENTS_DIR" ] || exit 0

# Per-session stamp path. Measured 2026-08-03 (#529): concurrent sid-less
# retros DO collide on a shared `unknown` path in practice — one session's
# `emit` deletes the stamp out from under the other, forcing its duration_ms
# to null. `$PPID` is the harness's persistent per-session shell PID (stable
# across the separate `stamp` and `emit` Bash calls within one retro run,
# distinct across concurrent sessions), so it substitutes for a real PID
# without breaking the stamp/emit pairing a raw `$$` would (a new process
# each invocation).
STAMP="/tmp/retro-start-${CLAUDE_SESSION_ID:-$PPID}.ms"

now_ms() { python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || true; }

case "${1:-}" in
  stamp)
    now_ms > "$STAMP" 2>/dev/null || true
    ;;

  emit)
    PROCESSED="${2:-0}"; DEDUPED="${3:-0}"; BUDGET_USED="${4:-0}"
    # duration_ms = now − start stamp; require both all-digits before arithmetic
    # so a corrupt/non-numeric stamp falls back to null, not a bogus 0.
    START_MS="$(cat "$STAMP" 2>/dev/null || true)"
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
      printf '%s\n' "$LINE" >> "${EVENTS_DIR}/events-$(date -u +%Y-%m-%d).jsonl" 2>/dev/null
    rm -f "$STAMP" 2>/dev/null || true
    ;;

  *)
    exit 0
    ;;
esac

exit 0
