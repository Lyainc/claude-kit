#!/usr/bin/env bash
# baseline-measure.sh — time ovm-primitives subcommands against a fixture vault

set -euo pipefail

if [[ "${VAULT_BRIDGE_DISABLE:-}" == "1" ]]; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIMITIVES="$SCRIPT_DIR/../ovm-primitives.sh"
GEN_FIXTURE="$SCRIPT_DIR/gen-fixture.sh"

[[ -x "$PRIMITIVES" ]] || { echo "ERROR: ovm-primitives.sh not executable at $PRIMITIVES" >&2; exit 1; }

log() { echo "$*" >&2; }

# ── fixture setup ──────────────────────────────────────────────────────────────

if [[ -n "${OVM_FIXTURE_DIR:-}" && -d "$OVM_FIXTURE_DIR" ]]; then
  FIXTURE="$OVM_FIXTURE_DIR"
  log "Using existing fixture: $FIXTURE"
else
  log "Generating fixture ..."
  FIXTURE="$("$GEN_FIXTURE")"
fi

log "Fixture: $FIXTURE"
log ""

# Override vault root for primitives to point at fixture
export VAULT_ROOT="$FIXTURE"
export AUDIT_STATE_PATH="$FIXTURE/.ovm/audit-state.json"

# ── timing helper ──────────────────────────────────────────────────────────────

time_cmd() {
  local label="$1"
  shift
  local start_ms
  start_ms=$(python3 -c "import time; print(int(time.time()*1000))")
  "$@" > /dev/null
  local end_ms
  end_ms=$(python3 -c "import time; print(int(time.time()*1000))")
  echo $((end_ms - start_ms))
}

measure_cmd() {
  local label="$1"
  shift
  local elapsed
  elapsed=$(time_cmd "$label" "$@")
  log "  ${label}: ${elapsed}ms"
  echo "$elapsed"
}

# ── count fixture notes ────────────────────────────────────────────────────────

NOTE_COUNT=$(find "$FIXTURE" -name "*.md" -not -path "*/.ovm/*" | wc -l | tr -d ' ')
VAULT_BYTES=$(du -sk "$FIXTURE" | awk '{print $1 * 1024}')

log "Fixture stats: $NOTE_COUNT notes, ${VAULT_BYTES} bytes"
log ""

# ── benchmark each primitive ───────────────────────────────────────────────────

log "Benchmarking scan-frontmatter (full vault) ..."
T_SCAN_FM=$(measure_cmd "scan-frontmatter" bash "$PRIMITIVES" scan-frontmatter "$FIXTURE")

log "Benchmarking scan-filename (full vault) ..."
T_SCAN_FN=$(measure_cmd "scan-filename" bash "$PRIMITIVES" scan-filename "$FIXTURE")

log "Benchmarking extract-wikilinks (single file) ..."
SAMPLE_FILE="$FIXTURE/30_Notes/note-001.md"
T_WIKILINKS=$(measure_cmd "extract-wikilinks" bash "$PRIMITIVES" extract-wikilinks "$SAMPLE_FILE")

log "Benchmarking audit-state mark-clean (100 files) ..."
MARK_START=$(python3 -c "import time; print(int(time.time()*1000))")
for i in $(seq 1 100); do
  relpath="30_Notes/note-$(printf '%03d' $i).md"
  bash "$PRIMITIVES" audit-state mark-clean "$relpath" > /dev/null
done
MARK_END=$(python3 -c "import time; print(int(time.time()*1000))")
T_MARK_CLEAN=$(( (MARK_END - MARK_START) / 100 ))
log "  mark-clean (avg per file): ${T_MARK_CLEAN}ms"

log "Benchmarking audit-state list-dirty-since ..."
T_LIST_DIRTY=$(measure_cmd "list-dirty-since" bash "$PRIMITIVES" audit-state list-dirty-since "2026-04-01T00:00:00+00:00")

log "Benchmarking metrics start/stop/report ..."
# #670: metrics stop/report need the token `start` printed (no shared /tmp path by
# process/session identity anymore) — measure_cmd discards stdout, so start is timed
# and captured separately here, then its token is threaded into stop/report.
METRICS_START_BEGIN=$(python3 -c "import time; print(int(time.time()*1000))")
METRICS_START_OUT="$(bash "$PRIMITIVES" metrics start "baseline-test")"
METRICS_START_END=$(python3 -c "import time; print(int(time.time()*1000))")
T_METRICS_START=$((METRICS_START_END - METRICS_START_BEGIN))
METRICS_TOKEN="$(printf '%s' "$METRICS_START_OUT" | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")"
log "  metrics-start: ${T_METRICS_START}ms"
T_METRICS_STOP=$(measure_cmd "metrics-stop" bash "$PRIMITIVES" metrics stop "$METRICS_TOKEN")
T_METRICS_REPORT=$(measure_cmd "metrics-report" bash "$PRIMITIVES" metrics report "$METRICS_TOKEN")

log ""
log "All benchmarks complete."
log ""

# ── emit JSON report ───────────────────────────────────────────────────────────

python3 - \
  "$NOTE_COUNT" "$VAULT_BYTES" \
  "$T_SCAN_FM" "$T_SCAN_FN" "$T_WIKILINKS" \
  "$T_MARK_CLEAN" "$T_LIST_DIRTY" \
  "$T_METRICS_START" "$T_METRICS_STOP" "$T_METRICS_REPORT" \
  "$FIXTURE" \
  <<'PYEOF'
import sys, json
from datetime import datetime, timezone

note_count   = int(sys.argv[1])
vault_bytes  = int(sys.argv[2])
t_scan_fm    = int(sys.argv[3])
t_scan_fn    = int(sys.argv[4])
t_wikilinks  = int(sys.argv[5])
t_mark_clean = int(sys.argv[6])
t_list_dirty = int(sys.argv[7])
t_met_start  = int(sys.argv[8])
t_met_stop   = int(sys.argv[9])
t_met_report = int(sys.argv[10])
fixture      = sys.argv[11]

report = {
    "measured_at": datetime.now(timezone.utc).isoformat(),
    "fixture": fixture,
    "vault_stats": {
        "note_count": note_count,
        "vault_size_bytes": vault_bytes,
        "ms_per_note_scan_frontmatter": round(t_scan_fm / note_count, 2) if note_count else 0,
        "ms_per_note_scan_filename": round(t_scan_fn / note_count, 2) if note_count else 0,
    },
    "timings_ms": {
        "scan_frontmatter_full_vault": t_scan_fm,
        "scan_filename_full_vault": t_scan_fn,
        "extract_wikilinks_single_file": t_wikilinks,
        "audit_state_mark_clean_avg_per_file": t_mark_clean,
        "audit_state_list_dirty_since": t_list_dirty,
        "metrics_start": t_met_start,
        "metrics_stop": t_met_stop,
        "metrics_report": t_met_report,
    }
}

print(json.dumps(report, indent=2))
PYEOF
