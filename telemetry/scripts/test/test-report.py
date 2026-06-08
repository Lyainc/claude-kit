#!/usr/bin/env python3
"""
Regression test — telemetry/scripts/report.py latency_by_event() + per-event breakdown.

PR #161 claude-review flagged latency_by_event as the only new logic without a
runnable check. This locks the per-event-type bucketing contract:

  - events bucket by their logical `event` field (skill_invoke / agent_spawn / ...)
  - each bucket runs latency_stats → {count, p50, p95} (nearest-rank percentiles)
  - "no datum → skip": an event type with NO numeric meta.duration_ms sample
    (missing meta, meta={}, meta=None, null / non-numeric / bool duration_ms) is
    OMITTED entirely — its bucket must not appear in latency_by_event
  - main()'s --event filter is applied to the events list BEFORE latency_by_event,
    so a single-type filter collapses to exactly one bucket
  - JSON output rounds p50/p95 to 1 decimal under key latency_by_event (sorted);
    table output renders a "by event type:" block with per-type lines

Run: python3 telemetry/scripts/test/test-report.py
Exit 0 on pass, 1 on fail.
"""

import contextlib
import io
import json
import sys
from pathlib import Path

# report.py lives in the parent dir; put it on sys.path and import directly.
SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import report  # noqa: E402


def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _ev(event: str, duration_ms=..., plugin: str = "p", name: str = "n") -> dict:
    """Build a telemetry event.

    duration_ms sentinel handling:
      - ... (default)  → no meta key at all (meta absent)
      - "__empty__"    → meta = {}
      - "__none__"     → meta = None
      - any other val  → meta = {"duration_ms": val}  (incl. None inside dict)
    """
    e: dict = {"plugin": plugin, "event": event, "name": name, "outcome": "ok"}
    if duration_ms is ...:
        return e
    if duration_ms == "__empty__":
        e["meta"] = {}
    elif duration_ms == "__none__":
        e["meta"] = None
    else:
        e["meta"] = {"duration_ms": duration_ms}
    return e


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def case_event_bucketing(errors: list[str]) -> None:
    """Two event types each with numeric durations → separate buckets, correct stats."""
    print("\ncase: event_bucketing")
    events = [
        _ev("skill_invoke", 10), _ev("skill_invoke", 20), _ev("skill_invoke", 30),
        _ev("skill_invoke", 40), _ev("skill_invoke", 50),
        _ev("agent_spawn", 100), _ev("agent_spawn", 200), _ev("agent_spawn", 300),
    ]
    res = report.latency_by_event(events)
    _assert(set(res.keys()) == {"skill_invoke", "agent_spawn"},
            f"exactly two buckets (got: {sorted(res.keys())})", errors)
    # skill_invoke [10,20,30,40,50]: p50 rank ceil(.5*5)=3 → 30; p95 rank ceil(.95*5)=5 → 50
    _assert(res["skill_invoke"] == {"count": 5, "p50": 30.0, "p95": 50.0},
            f"skill_invoke stats (got: {res['skill_invoke']})", errors)
    # agent_spawn [100,200,300]: p50 rank ceil(.5*3)=2 → 200; p95 rank ceil(.95*3)=3 → 300
    _assert(res["agent_spawn"] == {"count": 3, "p50": 200.0, "p95": 300.0},
            f"agent_spawn stats (got: {res['agent_spawn']})", errors)


def case_no_datum_skip(errors: list[str]) -> None:
    """Event types with no numeric duration sample are omitted entirely."""
    print("\ncase: no_datum_skip")
    events = [
        _ev("skill_invoke", 10), _ev("skill_invoke", 20), _ev("skill_invoke", 30),
        _ev("stop"),            # meta absent
        _ev("stop"),            # meta absent
    ]
    res = report.latency_by_event(events)
    _assert("stop" not in res, f"stop bucket omitted (got keys: {sorted(res.keys())})", errors)
    _assert("skill_invoke" in res, "skill_invoke bucket present", errors)
    _assert(res["skill_invoke"]["count"] == 3,
            f"skill_invoke count=3 (got: {res.get('skill_invoke')})", errors)


def case_no_datum_meta_variants(errors: list[str]) -> None:
    """meta={}, meta=None, null/non-numeric/bool duration_ms all count as no-datum."""
    print("\ncase: no_datum_meta_variants")
    events = [
        _ev("skill_invoke", 42),          # the only real sample
        _ev("empty_meta", "__empty__"),   # meta = {}
        _ev("none_meta", "__none__"),     # meta = None
        _ev("null_dur", None),            # meta = {"duration_ms": None}
        _ev("str_dur", "fast"),           # non-numeric
        _ev("bool_dur", True),            # bool rejected (int subclass)
    ]
    res = report.latency_by_event(events)
    _assert(set(res.keys()) == {"skill_invoke"},
            f"only skill_invoke survives (got: {sorted(res.keys())})", errors)
    for absent in ("empty_meta", "none_meta", "null_dur", "str_dur", "bool_dur"):
        _assert(absent not in res, f"{absent} bucket omitted", errors)


def case_event_filter_single_bucket(errors: list[str]) -> None:
    """Mirror main()'s --event filter: filter to one type, then latency_by_event → 1 bucket."""
    print("\ncase: event_filter_single_bucket")
    all_events = [
        _ev("skill_invoke", 10), _ev("skill_invoke", 20),
        _ev("agent_spawn", 100), _ev("agent_spawn", 200),
        _ev("stop"),
    ]
    filtered = [e for e in all_events if e.get("event") == "agent_spawn"]
    res = report.latency_by_event(filtered)
    _assert(set(res.keys()) == {"agent_spawn"},
            f"exactly one bucket after filter (got: {sorted(res.keys())})", errors)
    _assert(res["agent_spawn"]["count"] == 2,
            f"agent_spawn count=2 (got: {res['agent_spawn']})", errors)


def case_percentile_accuracy(errors: list[str]) -> None:
    """Exact nearest-rank percentiles, cross-checked against percentile() directly."""
    print("\ncase: percentile_accuracy")
    # [10,20,30,40,50] → p50=30, p95=50
    res = report.latency_by_event(
        [_ev("e", v) for v in (10, 20, 30, 40, 50)]
    )
    _assert(res["e"]["p50"] == 30.0, f"p50=30 (got: {res['e']['p50']})", errors)
    _assert(res["e"]["p95"] == 50.0, f"p95=50 (got: {res['e']['p95']})", errors)

    # Direct percentile() checks on pre-sorted lists.
    # n=4 [1,2,3,4]: p50 rank ceil(.5*4)=2 → 2.0; p95 rank ceil(.95*4)=4 → 4.0
    _assert(report.percentile([1.0, 2.0, 3.0, 4.0], 0.50) == 2.0,
            "percentile n=4 p50 → 2.0", errors)
    _assert(report.percentile([1.0, 2.0, 3.0, 4.0], 0.95) == 4.0,
            "percentile n=4 p95 → 4.0", errors)
    # n=10 [1..10]: p50 rank ceil(.5*10)=5 → 5.0; p95 rank ceil(.95*10)=10 → 10.0
    ten = [float(i) for i in range(1, 11)]
    _assert(report.percentile(ten, 0.50) == 5.0, "percentile n=10 p50 → 5.0", errors)
    _assert(report.percentile(ten, 0.95) == 10.0, "percentile n=10 p95 → 10.0", errors)
    # single element → both percentiles are that element (rank clamped to 1)
    _assert(report.percentile([7.0], 0.50) == 7.0, "percentile n=1 p50 → 7.0", errors)
    _assert(report.percentile([7.0], 0.95) == 7.0, "percentile n=1 p95 → 7.0", errors)


# --- end-to-end main() exercises -------------------------------------------

# Shared fixture: skill_invoke (3 numeric) + agent_spawn (2 numeric) + stop (no datum)
FIXTURE_EVENTS = [
    _ev("skill_invoke", 10, name="a"),
    _ev("skill_invoke", 20, name="b"),
    _ev("skill_invoke", 30, name="c"),
    _ev("agent_spawn", 100, name="x"),
    _ev("agent_spawn", 300, name="y"),
    _ev("stop"),
    _ev("stop"),
]


def _run_main(argv: list[str]) -> str:
    """Run report.main() with load_events stubbed to FIXTURE_EVENTS; return stdout."""
    saved_load = report.load_events
    saved_argv = sys.argv
    try:
        report.load_events = lambda *a, **k: list(FIXTURE_EVENTS)
        sys.argv = argv
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = report.main()
        if rc != 0:
            raise AssertionError(f"main() returned {rc}")
        return buf.getvalue()
    finally:
        report.load_events = saved_load
        sys.argv = saved_argv


def case_json_output_end_to_end(errors: list[str]) -> None:
    """--format=json: latency_by_event keys + rounded p50_ms/p95_ms; no-datum type excluded."""
    print("\ncase: json_output_end_to_end")
    out = _run_main(["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    lbe = payload["latency_by_event"]
    _assert(set(lbe.keys()) == {"skill_invoke", "agent_spawn"},
            f"json buckets = skill_invoke+agent_spawn (got: {sorted(lbe.keys())})", errors)
    _assert("stop" not in lbe, "json excludes no-datum stop bucket", errors)
    # skill_invoke [10,20,30]: p50 rank ceil(.5*3)=2 → 20; p95 rank ceil(.95*3)=3 → 30
    _assert(lbe["skill_invoke"] == {"count": 3, "p50_ms": 20.0, "p95_ms": 30.0},
            f"json skill_invoke (got: {lbe['skill_invoke']})", errors)
    # agent_spawn [100,300]: p50 rank ceil(.5*2)=1 → 100; p95 rank ceil(.95*2)=2 → 300
    _assert(lbe["agent_spawn"] == {"count": 2, "p50_ms": 100.0, "p95_ms": 300.0},
            f"json agent_spawn (got: {lbe['agent_spawn']})", errors)


def case_table_output_end_to_end(errors: list[str]) -> None:
    """--format=table: 'by event type:' block + per-type lines render; no-datum type absent."""
    print("\ncase: table_output_end_to_end")
    out = _run_main(["report.py", "--since=all", "--format=table"])
    _assert("by event type:" in out, "table has 'by event type:' block", errors)
    _assert("skill_invoke" in out and "agent_spawn" in out,
            "table lists both numeric event types", errors)
    # Per-type line shape: "<type> ... n=<count> p50=...ms p95=...ms"
    si_line = next((ln for ln in out.splitlines()
                    if "skill_invoke" in ln and "p50=" in ln), None)
    _assert(si_line is not None and "n=3" in si_line and "p50=20ms" in si_line
            and "p95=30ms" in si_line,
            f"skill_invoke per-type line renders (got: {si_line!r})", errors)
    # The no-datum 'stop' type must not appear as its own latency line.
    stop_lat_line = next((ln for ln in out.splitlines()
                          if "stop" in ln and "p50=" in ln), None)
    _assert(stop_lat_line is None,
            f"no latency line for no-datum stop (got: {stop_lat_line!r})", errors)


def case_event_filter_end_to_end(errors: list[str]) -> None:
    """--event=skill_invoke: main() filters before latency_by_event → single bucket."""
    print("\ncase: event_filter_end_to_end")
    out = _run_main(["report.py", "--since=all", "--event=skill_invoke", "--format=json"])
    payload = json.loads(out)
    lbe = payload["latency_by_event"]
    _assert(set(lbe.keys()) == {"skill_invoke"},
            f"--event filter collapses to single bucket (got: {sorted(lbe.keys())})", errors)
    _assert(lbe["skill_invoke"]["count"] == 3,
            f"filtered skill_invoke count=3 (got: {lbe['skill_invoke']})", errors)
    _assert(payload["total"] == 3, f"total reflects filtered events (got: {payload['total']})", errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"Running report.py latency_by_event regression tests against: {SCRIPT_DIR / 'report.py'}")
    errors: list[str] = []

    case_event_bucketing(errors)
    case_no_datum_skip(errors)
    case_no_datum_meta_variants(errors)
    case_event_filter_single_bucket(errors)
    case_percentile_accuracy(errors)
    case_json_output_end_to_end(errors)
    case_table_output_end_to_end(errors)
    case_event_filter_end_to_end(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
