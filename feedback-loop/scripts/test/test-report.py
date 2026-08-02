#!/usr/bin/env python3
"""
Regression test — feedback-loop/scripts/report.py latency_by_event() + per-event breakdown.

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

Run: python3 feedback-loop/scripts/test/test-report.py
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

# Shared fixture: skill_invoke (3 numeric) + agent_spawn (2 numeric) + stop (no datum).
# skill_invoke events carry qualified_name (#210 N2) so a catalog-matched lifecycle run
# can exercise the fired path; the shared cases don't stub a catalog, so these names stay
# never-fired there (they match no real skill) — see case_lifecycle_fired_bottom_e2e for
# the hermetic, catalog-stubbed fired/stale/bottom coverage.
FIXTURE_EVENTS = [
    {**_ev("skill_invoke", 10, name="a"), "qualified_name": "p:a"},
    {**_ev("skill_invoke", 20, name="b"), "qualified_name": "p:b"},
    {**_ev("skill_invoke", 30, name="c"), "qualified_name": "p:c"},
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


def _run_main_with(events: list[dict], argv: list[str],
                   catalog: list[str] | None = None) -> str:
    """Like _run_main but with a caller-supplied event fixture (not the shared one).

    When `catalog` is given, scan_skill_catalog is ALSO stubbed (#210 N3) so the
    lifecycle e2e is hermetic — it no longer depends on the live repo's */skills/*
    layout, letting the fired/stale/bottom paths be exercised deterministically.
    """
    saved_load = report.load_events
    saved_scan = report.scan_skill_catalog
    saved_argv = sys.argv
    try:
        report.load_events = lambda *a, **k: list(events)
        if catalog is not None:
            report.scan_skill_catalog = lambda *a, **k: list(catalog)
        sys.argv = argv
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = report.main()
        if rc != 0:
            raise AssertionError(f"main() returned {rc}")
        return buf.getvalue()
    finally:
        report.load_events = saved_load
        report.scan_skill_catalog = saved_scan
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
# Lifecycle view cases
# ---------------------------------------------------------------------------

def case_lifecycle_never_fired(errors: list[str]) -> None:
    """A skill in catalog with zero events must appear in never_fired."""
    print("\ncase: lifecycle_never_fired")
    # Catalog: two fake skills; events only fire one of them.
    catalog = ["fake-plugin:active-skill", "fake-plugin:zero-count-skill"]
    events = [
        _ev("skill_invoke", plugin="fake-plugin", name="active-skill"),
        _ev("skill_invoke", plugin="fake-plugin", name="active-skill"),
    ]
    # Patch qualified_name onto these events (report uses qualified_name for matching).
    for e in events:
        e["qualified_name"] = "fake-plugin:active-skill"

    result = report.skill_lifecycle_view(events, catalog=catalog)

    _assert("fake-plugin:zero-count-skill" in result["never_fired"],
            "zero-count skill appears in never_fired", errors)
    _assert("fake-plugin:active-skill" not in result["never_fired"],
            "active skill absent from never_fired", errors)
    _assert(len(result["never_fired"]) == 1,
            f"exactly one never-fired skill (got: {result['never_fired']})", errors)


def case_lifecycle_stale_note(errors: list[str]) -> None:
    """A --since window <= the stale threshold must surface a stale_note (not silence).

    Under e.g. --since=7d no loaded event can be >14d old, so the stale section is
    structurally inert — the view must say so instead of rendering a bare "(none)"
    (isolated-critique MEDIUM finding, 2026-06-10).
    """
    print("\ncase: lifecycle_stale_note")
    catalog = ["fake-plugin:some-skill"]

    bounded = report.skill_lifecycle_view([], catalog=catalog, since_days=7)
    _assert(bounded["stale_note"] is not None,
            "since_days=7 (<= stale threshold) sets stale_note", errors)

    unbounded = report.skill_lifecycle_view([], catalog=catalog, since_days=None)
    _assert(unbounded["stale_note"] is None,
            "since_days=None (--since=all) leaves stale_note None", errors)

    wide = report.skill_lifecycle_view([], catalog=catalog, since_days=30)
    _assert(wide["stale_note"] is None,
            "since_days=30 (> stale threshold) leaves stale_note None", errors)


def case_lifecycle_caveat_in_output(errors: list[str]) -> None:
    """Table output must contain the measurement-scope caveat string."""
    print("\ncase: lifecycle_caveat_in_output")
    out = _run_main(["report.py", "--since=all", "--format=table"])
    _assert(
        "측정범위: claude-kit 레포 내 세션 기준 (telemetry Option A)" in out,
        "table output contains measurement-scope caveat",
        errors,
    )
    _assert(
        "Skill lifecycle" in out,
        "table output has 'Skill lifecycle' section header",
        errors,
    )


def case_lifecycle_caveat_in_json(errors: list[str]) -> None:
    """JSON output must include a lifecycle key with caveat and never_fired."""
    print("\ncase: lifecycle_caveat_in_json")
    out = _run_main(["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    _assert("lifecycle" in payload, "json has 'lifecycle' key", errors)
    lc = payload.get("lifecycle", {})
    _assert(
        lc.get("caveat") == "측정범위: claude-kit 레포 내 세션 기준 (telemetry Option A)",
        f"json lifecycle.caveat correct (got: {lc.get('caveat')!r})",
        errors,
    )
    _assert("never_fired" in lc, "json lifecycle has 'never_fired' list", errors)
    _assert("stale" in lc, "json lifecycle has 'stale' list", errors)
    _assert("bottom" in lc, "json lifecycle has 'bottom' list", errors)
    _assert("guide" in lc, "json lifecycle has 'guide' string", errors)


def case_lifecycle_fired_bottom_e2e(errors: list[str]) -> None:
    """#210 N2/N3: hermetic e2e lifecycle over a STUBBED catalog — exercises the
    fired/bottom paths (not just all-never-fired) without depending on the live repo."""
    print("\ncase: lifecycle_fired_bottom_e2e")
    catalog = ["fx:hot", "fx:cold", "fx:dead"]
    events = [
        {**_ev("skill_invoke", name="hot"), "qualified_name": "fx:hot",
         "ts": "2099-01-01T00:00:00Z"},
        {**_ev("skill_invoke", name="hot"), "qualified_name": "fx:hot",
         "ts": "2099-01-01T00:00:00Z"},
        {**_ev("skill_invoke", name="hot"), "qualified_name": "fx:hot",
         "ts": "2099-01-01T00:00:00Z"},
        {**_ev("skill_invoke", name="cold"), "qualified_name": "fx:cold",
         "ts": "2099-01-01T00:00:00Z"},
    ]
    out = _run_main_with(events, ["report.py", "--since=all", "--format=json"], catalog=catalog)
    lc = json.loads(out)["lifecycle"]
    _assert("fx:dead" in lc["never_fired"],
            "unfired catalog skill in never_fired", errors)
    _assert("fx:hot" not in lc["never_fired"] and "fx:cold" not in lc["never_fired"],
            "fired skills absent from never_fired", errors)
    bottom = {d["skill"]: d["count"] for d in lc["bottom"]}
    _assert(bottom.get("fx:cold") == 1 and bottom.get("fx:hot") == 3,
            f"bottom-N carries per-skill fired counts (got: {bottom})", errors)
    # #210 N1: --since=all earns the absolute label; a window must say "no events in <w>".
    _assert(lc.get("never_fired_label") == "never-fired",
            f"since=all → absolute never-fired label (got: {lc.get('never_fired_label')})", errors)
    wout = _run_main_with(events, ["report.py", "--since=7d", "--format=json"], catalog=catalog)
    wlc = json.loads(wout)["lifecycle"]
    _assert(wlc.get("never_fired_label") == "no events in 7d window",
            f"windowed never_fired_label not overstated (got: {wlc.get('never_fired_label')})", errors)


# ---------------------------------------------------------------------------
# Rule-fire liveness cases (G20 #258)
# ---------------------------------------------------------------------------

def case_rule_fire_per_rule_id(errors: list[str]) -> None:
    """rule_fire_view counts per rule_id (lifted into name) — no single-bucket collision."""
    print("\ncase: rule_fire_per_rule_id")
    events = [
        _ev("rule_fire", name="no-pyyaml"),
        _ev("rule_fire", name="no-pyyaml"),
        _ev("rule_fire", name="trash-not-rm"),
        _ev("skill_invoke", name="note"),   # non-rule_fire ignored
    ]
    res = report.rule_fire_view(events)
    _assert(res == {"no-pyyaml": 2, "trash-not-rm": 1},
            f"per-rule_id counts, distinct rules not collapsed (got: {res})", errors)
    # An empty / no-rule_fire event list yields an empty view (0-fire is invisible).
    _assert(report.rule_fire_view([_ev("stop")]) == {},
            "no rule_fire events → empty view (0-fire rules unobservable)", errors)
    # A rule_fire with no rule_id (empty name) lands in the honest "(unnamed rule)"
    # catch-all, never silently dropped or merged with a named rule.
    anon = report.rule_fire_view([_ev("rule_fire", name=""), _ev("rule_fire", name="x")])
    _assert(anon == {"(unnamed rule)": 1, "x": 1},
            f"rule_id-less fire → '(unnamed rule)' bucket (got: {anon})", errors)


def case_rule_fire_view_end_to_end(errors: list[str]) -> None:
    """main(): json carries per-rule_id rule_fire + caveat; table renders the section inline."""
    print("\ncase: rule_fire_view_end_to_end")
    fixture = [
        _ev("rule_fire", plugin="claude-kit", name="no-pyyaml"),
        _ev("rule_fire", plugin="claude-kit", name="no-pyyaml"),
        _ev("rule_fire", plugin="claude-kit", name="trash-not-rm"),
        _ev("skill_invoke", 10, name="note"),
    ]
    # JSON: rule_fire = per-rule_id counts, plus a non-null caveat alongside.
    out = _run_main_with(fixture, ["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    _assert(payload.get("rule_fire") == {"no-pyyaml": 2, "trash-not-rm": 1},
            f"json rule_fire per-rule_id (got: {payload.get('rule_fire')})", errors)
    _assert(bool(payload.get("rule_fire_caveat")),
            "json carries rule_fire_caveat when fires exist", errors)
    _assert("liveness" in (payload.get("rule_fire_caveat") or "")
            and "준수" in (payload.get("rule_fire_caveat") or ""),
            "caveat states liveness != compliance", errors)
    # Table: the liveness section renders AND the caveat prints inline with the counts.
    tout = _run_main_with(fixture, ["report.py", "--since=all", "--format=table"])
    _assert("Rule-fire liveness (enforcement, NOT compliance):" in tout,
            "table renders rule-fire liveness section", errors)
    _assert("no-pyyaml" in tout and "trash-not-rm" in tout,
            "table lists per-rule_id fire counts", errors)
    _assert("0-fire는 telemetry에 안 보이고" in tout,
            "table prints the 0-fire honesty caveat inline (not just counts)", errors)
    # Honesty floor: when nothing fired, the caveat must be null (no fabricated section).
    empty = _run_main_with([_ev("skill_invoke", 10, name="note")],
                           ["report.py", "--since=all", "--format=json"])
    _assert(json.loads(empty).get("rule_fire_caveat") is None,
            "no fires → rule_fire_caveat is null (no fabricated liveness claim)", errors)


# ---------------------------------------------------------------------------
# Token/cost view cases (#500)
# ---------------------------------------------------------------------------

def _meta_ev(model=None, input_tokens=None, output_tokens=None,
            cache_creation_tokens=None, cache_read_tokens=None) -> dict:
    """Build a bare event with only a meta dict (no plugin/event/name needed
    by token_cost_view — it only reads meta)."""
    meta = {}
    if model is not None:
        meta["model"] = model
    if input_tokens is not None:
        meta["input_tokens"] = input_tokens
    if output_tokens is not None:
        meta["output_tokens"] = output_tokens
    if cache_creation_tokens is not None:
        meta["cache_creation_tokens"] = cache_creation_tokens
    if cache_read_tokens is not None:
        meta["cache_read_tokens"] = cache_read_tokens
    return {"meta": meta}


def case_token_cost_weighted_calculation(errors: list[str]) -> None:
    """Priced events: tokens sum plainly, cost is token_count/1e6 * per-model rate."""
    print("\ncase: token_cost_weighted_calculation")
    events = [
        _meta_ev(model="claude-sonnet-5", input_tokens=1_000_000,
                 output_tokens=100_000, cache_creation_tokens=50_000,
                 cache_read_tokens=2_000_000),
    ]
    res = report.token_cost_view(events)
    _assert(res["tokens"] == {"input": 1_000_000, "output": 100_000,
                               "cache_write": 50_000, "cache_read": 2_000_000},
            f"token totals match input (got: {res['tokens']})", errors)
    # Sonnet 5 rates: input $3, output $15, cache_write $3.75, cache_read $0.30 per MTok
    expected_cost = {
        "input": 1.0 * 3.00, "output": 0.1 * 15.00,
        "cache_write": 0.05 * 3.75, "cache_read": 2.0 * 0.30,
    }
    _assert(res["cost"] is not None, "cost computed when model is priced", errors)
    for kind, exp in expected_cost.items():
        got = res["cost"][kind]
        _assert(abs(got - exp) < 1e-9,
                f"cost[{kind}] == {exp} (got: {got})", errors)
    _assert(res["priced_events"] == 1 and res["excluded_events"] == 0,
            f"1 priced, 0 excluded (got: priced={res['priced_events']} "
            f"excluded={res['excluded_events']})", errors)


def case_token_cost_ranking_inversion(errors: list[str]) -> None:
    """The #499/#500 motivating case: cache_read dominates token share, cache_write
    dominates cost share less than expected by tokens alone — rankings must differ."""
    print("\ncase: token_cost_ranking_inversion")
    events = [
        _meta_ev(model="claude-sonnet-5",
                 cache_read_tokens=50_400_000,   # 94.4% of tokens
                 cache_creation_tokens=2_600_000,  # 4.9% of tokens
                 output_tokens=400_000,           # 0.7% of tokens
                 input_tokens=1_000),
    ]
    res = report.token_cost_view(events)
    tokens = res["tokens"]
    cost = res["cost"]
    total_tok = sum(tokens.values())
    total_cost = sum(cost.values())
    tok_rank = sorted(tokens, key=lambda k: -tokens[k])
    cost_rank = sorted(cost, key=lambda k: -cost[k])
    _assert(tok_rank[0] == "cache_read",
            f"token ranking: cache_read is #1 by volume (got: {tok_rank})", errors)
    _assert(cost_rank[0] == "cache_read" and cost_rank[1] == "cache_write",
            f"cost ranking: cache_read #1, cache_write #2 (got: {cost_rank})", errors)
    # cache_write's token share is tiny but its cost share is not proportional to it —
    # the entire point of #500. Assert the share actually diverges.
    cw_tok_share = tokens["cache_write"] / total_tok
    cw_cost_share = cost["cache_write"] / total_cost
    _assert(cw_cost_share > cw_tok_share * 3,
            f"cache_write cost share ({cw_cost_share:.3f}) far exceeds its token "
            f"share ({cw_tok_share:.3f}) — the ranking inversion #500 exists to surface",
            errors)


def case_token_cost_missing_model_excluded(errors: list[str]) -> None:
    """No model on any event → tokens still counted, cost is None with a reason."""
    print("\ncase: token_cost_missing_model_excluded")
    events = [_meta_ev(input_tokens=500, output_tokens=100)]
    res = report.token_cost_view(events)
    _assert(res["tokens"] == {"input": 500, "output": 100, "cache_write": 0, "cache_read": 0},
            f"tokens counted even with no model (got: {res['tokens']})", errors)
    _assert(res["cost"] is None, "cost is None when no event has a model", errors)
    _assert(res["excluded_events"] == 1 and res["priced_events"] == 0,
            f"1 excluded, 0 priced (got: excluded={res['excluded_events']} "
            f"priced={res['priced_events']})", errors)
    _assert("(model 없음)" in res["unpriced_models"],
            f"unpriced_models names the no-model case (got: {res['unpriced_models']})",
            errors)


def case_token_cost_unregistered_model_excluded(errors: list[str]) -> None:
    """A model not in MODEL_PRICING is excluded from cost, never estimated."""
    print("\ncase: token_cost_unregistered_model_excluded")
    events = [_meta_ev(model="claude-made-up-9", input_tokens=1000)]
    res = report.token_cost_view(events)
    _assert(res["cost"] is None,
            "cost is None when the only event's model is unregistered", errors)
    _assert(res["unpriced_models"] == ["claude-made-up-9"],
            f"unpriced_models names the unregistered model (got: {res['unpriced_models']})",
            errors)


def case_token_cost_date_suffixed_model_matches_bare_key(errors: list[str]) -> None:
    """#510 item 1 / #511: a real model id carrying a date suffix beyond a
    registered bare key (e.g. Sonnet 5 gaining a future dated release) still
    prices correctly via prefix match, instead of silently landing in
    unpriced_models."""
    print("\ncase: token_cost_date_suffixed_model_matches_bare_key")
    events = [_meta_ev(model="claude-sonnet-5-20260601", input_tokens=1_000_000)]
    res = report.token_cost_view(events)
    _assert(res["cost"] is not None, "date-suffixed sonnet id still prices", errors)
    _assert(abs(res["cost"]["input"] - 3.00) < 1e-9,
            f"prefix match uses the bare sonnet rate (got: {res['cost']})", errors)
    _assert(res["priced_events"] == 1 and res["excluded_events"] == 0,
            "date-suffixed id counts as priced, not excluded/unpriced", errors)


def case_token_cost_mixed_priced_and_unpriced(errors: list[str]) -> None:
    """Mixing a priced and an unpriced event: cost reflects only the priced one,
    and the unpriced one is surfaced as excluded rather than silently dropped."""
    print("\ncase: token_cost_mixed_priced_and_unpriced")
    events = [
        _meta_ev(model="claude-haiku-4-5-20251001", input_tokens=1_000_000),
        _meta_ev(model=None, input_tokens=1_000_000),  # no model at all
    ]
    res = report.token_cost_view(events)
    _assert(res["tokens"]["input"] == 2_000_000,
            f"token total includes both events (got: {res['tokens']['input']})", errors)
    _assert(res["cost"] is not None, "cost is present (one event was priced)", errors)
    _assert(abs(res["cost"]["input"] - 1.00) < 1e-9,
            f"cost reflects only the priced haiku event (got: {res['cost']['input']})",
            errors)
    _assert(res["priced_events"] == 1 and res["excluded_events"] == 1,
            f"1 priced + 1 excluded (got: priced={res['priced_events']} "
            f"excluded={res['excluded_events']})", errors)


def case_token_cost_no_token_data(errors: list[str]) -> None:
    """Events with no numeric token fields at all contribute nothing."""
    print("\ncase: token_cost_no_token_data")
    events = [{"meta": {}}, {"meta": None}, {}]
    res = report.token_cost_view(events)
    _assert(sum(res["tokens"].values()) == 0,
            f"no token data → all zero (got: {res['tokens']})", errors)
    _assert(res["cost"] is None, "no token data → cost is None", errors)


def case_token_cost_zero_cost_not_mislabeled_omitted(errors: list[str]) -> None:
    """PR #509 review nit (#510 item 2): a priced event whose cost sums to exactly
    $0.00 must render as a real (zero) cost, never as 'omitted' — `cost is None` is
    the only honest signal for omission, not truthiness of the summed value.

    Needs total_tokens > 0 (else the whole section is skipped) while the priced
    event itself contributes zero cost — so an unpriced event supplies the nonzero
    token volume, and the priced event's own fields are all zero.
    """
    print("\ncase: token_cost_zero_cost_not_mislabeled_omitted")
    events = [
        {**_ev("skill_invoke", 10, name="a"),
         "meta": {"duration_ms": 10, "model": "claude-sonnet-5",
                   "input_tokens": 0, "output_tokens": 0,
                   "cache_creation_tokens": 0, "cache_read_tokens": 0}},
        {**_ev("skill_invoke", 10, name="b"),
         "meta": {"duration_ms": 10, "input_tokens": 500}},  # no model — unpriced
    ]
    res = report.token_cost_view(events)
    _assert(res["cost"] is not None and sum(res["cost"].values()) == 0.0,
            f"cost is a real zero, not None (got: {res['cost']})", errors)

    out = _run_main_with(events, ["report.py", "--since=all", "--format=table"])
    _assert("비용 열 생략" not in out,
            "a real (zero) cost is not mislabeled as omitted", errors)
    _assert("cost=$0.0000" in out,
            f"the zero cost renders explicitly (excerpt not found in: {out!r})", errors)


def case_token_cost_view_end_to_end(errors: list[str]) -> None:
    """main(): json carries token_cost + caveat; table renders both tokens and cost
    side by side, and omits cost with a reason when nothing was priced."""
    print("\ncase: token_cost_view_end_to_end")
    priced = [
        {**_ev("skill_invoke", 10, name="a"),
         "meta": {"duration_ms": 10, "model": "claude-sonnet-5",
                   "input_tokens": 1_000_000, "output_tokens": 100_000}},
    ]
    out = _run_main_with(priced, ["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    _assert(payload.get("token_cost") is not None, "json has non-null token_cost", errors)
    tc = payload["token_cost"]
    _assert(tc["tokens"]["input"] == 1_000_000, f"json tokens.input (got: {tc['tokens']})", errors)
    _assert(tc["cost"] is not None and tc["cost"]["input"] == 3.0,
            f"json cost.input priced at $3/MTok (got: {tc['cost']})", errors)
    _assert(bool(payload.get("token_cost_caveat")), "json carries token_cost_caveat", errors)
    _assert("순위" in (payload.get("token_cost_caveat") or ""),
            "caveat states token-rank != cost-rank", errors)

    tout = _run_main_with(priced, ["report.py", "--since=all", "--format=table"])
    _assert("Token/cost breakdown" in tout, "table renders token/cost section", errors)
    _assert("cost=$3.0000" in tout or "cost=$3.00" in tout or "$3.0000" in tout,
            f"table shows priced cost for input (excerpt not found in output)", errors)

    # No model anywhere → cost omitted with an explicit reason, tokens still shown.
    unpriced = [
        {**_ev("skill_invoke", 10, name="a"),
         "meta": {"duration_ms": 10, "input_tokens": 500}},
    ]
    uout = _run_main_with(unpriced, ["report.py", "--since=all", "--format=json"])
    upayload = json.loads(uout)
    utc = upayload["token_cost"]
    _assert(utc["cost"] is None, "json cost is null when nothing priced", errors)
    _assert(bool(utc.get("cost_omitted_reason")),
            "json carries a cost_omitted_reason when cost is null", errors)
    utout = _run_main_with(unpriced, ["report.py", "--since=all", "--format=table"])
    _assert("비용 열 생략" in utout, "table states cost was omitted, with a reason", errors)


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
    case_lifecycle_never_fired(errors)
    case_lifecycle_stale_note(errors)
    case_lifecycle_caveat_in_output(errors)
    case_lifecycle_caveat_in_json(errors)
    case_lifecycle_fired_bottom_e2e(errors)
    case_rule_fire_per_rule_id(errors)
    case_rule_fire_view_end_to_end(errors)
    case_token_cost_weighted_calculation(errors)
    case_token_cost_ranking_inversion(errors)
    case_token_cost_missing_model_excluded(errors)
    case_token_cost_unregistered_model_excluded(errors)
    case_token_cost_date_suffixed_model_matches_bare_key(errors)
    case_token_cost_mixed_priced_and_unpriced(errors)
    case_token_cost_no_token_data(errors)
    case_token_cost_zero_cost_not_mislabeled_omitted(errors)
    case_token_cost_view_end_to_end(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
