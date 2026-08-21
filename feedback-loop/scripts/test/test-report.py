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
import tempfile
from datetime import datetime, timedelta, timezone
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


def _ev(event: str, duration_ms=..., plugin: str = "p", name: str = "n", outcome: str = "ok") -> dict:
    """Build a telemetry event.

    duration_ms sentinel handling:
      - ... (default)  → no meta key at all (meta absent)
      - "__empty__"    → meta = {}
      - "__none__"     → meta = None
      - any other val  → meta = {"duration_ms": val}  (incl. None inside dict)
    """
    e: dict = {"plugin": plugin, "event": event, "name": name, "outcome": outcome}
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
        _ev("skill_invoke", plugin="fake-plugin", name="active-skill", outcome="started"),
        _ev("skill_invoke", plugin="fake-plugin", name="active-skill", outcome="started"),
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


def case_scan_skill_catalog_repo_layout(errors: list[str]) -> None:
    """Repo checkout shape: <root>/{plugin}/skills/{skill}/SKILL.md, unaffected by #522."""
    print("\ncase: scan_skill_catalog_repo_layout")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pluginA" / "skills" / "skillX").mkdir(parents=True)
        (root / "pluginA" / "skills" / "skillX" / "SKILL.md").write_text("x")
        catalog = report.scan_skill_catalog(repo_root=root)
        _assert(catalog == ["pluginA:skillX"],
                f"repo-shape catalog resolves plugin:skill directly (got: {catalog})", errors)


def case_scan_skill_catalog_cache_layout(errors: list[str]) -> None:
    """Plugin-cache shape inserts a semver version dir: {plugin}/{version}/skills/{skill}/SKILL.md.

    #522: PLUGIN_DIR.parent (== this function's repo_root arg) lands ON the
    single-plugin cache dir, one level too deep — the naive repo-shape glob
    then reads the version directory as the plugin name (`4.0.1:retro`) and
    every real qualified_name match fails, so the lifecycle view reports 100%
    never_fired. The fix must detect the version-looking path component,
    escalate to the marketplace root (repo_root.parent) so sibling plugins are
    found too, and dedup repeats across every cached version of the same skill.

    Also covers a gap found in fresh-context review of the first cut of this
    fix: the plugin cache keeps EVERY version it ever installed (only the live
    one lacks a `.orphaned_at` marker, confirmed against the real cache on
    this machine — every plugin has exactly one non-orphaned version). A skill
    retired in the live version but still present in an old orphaned version's
    SKILL.md must NOT resurrect as a permanently never-fired catalog entry —
    that is the exact false signal #522 was written to kill, just relocated
    from "misread as a version" to "read from a dead version".
    """
    print("\ncase: scan_skill_catalog_cache_layout")
    with tempfile.TemporaryDirectory() as td:
        cache_root = Path(td) / "cache" / "some-marketplace"
        for version in ("4.0.1", "4.5.0"):
            skill_dir = cache_root / "feedback-loop" / version / "skills" / "retro"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("x")
        (cache_root / "feedback-loop" / "4.5.0" / "skills" / "add-policy").mkdir(parents=True)
        (cache_root / "feedback-loop" / "4.5.0" / "skills" / "add-policy" / "SKILL.md").write_text("x")
        (cache_root / "thinking-tools" / "4.5.0" / "skills" / "expert-panel").mkdir(parents=True)
        (cache_root / "thinking-tools" / "4.5.0" / "skills" / "expert-panel" / "SKILL.md").write_text("x")
        # A skill retired by 4.5.0 but still on disk in the orphaned 4.0.1 dir.
        retired_dir = cache_root / "feedback-loop" / "4.0.1" / "skills" / "retired-skill"
        retired_dir.mkdir(parents=True)
        (retired_dir / "SKILL.md").write_text("x")
        (cache_root / "feedback-loop" / "4.0.1" / ".orphaned_at").write_text("2026-01-01")
        # 4.5.0 is the live version: no .orphaned_at marker.

        # Simulates REPO_ROOT = PLUGIN_DIR.parent when report.py runs from
        # .../feedback-loop/4.5.0/scripts/report.py in the real cache.
        catalog = report.scan_skill_catalog(repo_root=cache_root / "feedback-loop")

        _assert(not any(c.split(":", 1)[0][0].isdigit() for c in catalog),
                f"no version string ever appears as a plugin name (got: {catalog})", errors)
        _assert("feedback-loop:retro" in catalog,
                "feedback-loop:retro resolved despite two cached versions", errors)
        _assert(catalog.count("feedback-loop:retro") == 1,
                "the two cached versions of retro dedup to one catalog entry", errors)
        _assert("feedback-loop:add-policy" in catalog,
                "feedback-loop:add-policy resolved", errors)
        _assert("thinking-tools:expert-panel" in catalog,
                "sibling plugin (thinking-tools) is found via the marketplace root, not just feedback-loop's own cache dir",
                errors)
        _assert("feedback-loop:retired-skill" not in catalog,
                "a skill retired in the live version does not resurrect from an orphaned old-version cache dir",
                errors)


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
        lc.get("caveat") == report._LIFECYCLE_CAVEAT,
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
        {**_ev("skill_invoke", name="hot", outcome="started"), "qualified_name": "fx:hot",
         "ts": "2099-01-01T00:00:00Z"},
        {**_ev("skill_invoke", name="hot", outcome="started"), "qualified_name": "fx:hot",
         "ts": "2099-01-01T00:00:00Z"},
        {**_ev("skill_invoke", name="hot", outcome="started"), "qualified_name": "fx:hot",
         "ts": "2099-01-01T00:00:00Z"},
        {**_ev("skill_invoke", name="cold", outcome="started"), "qualified_name": "fx:cold",
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


def case_lifecycle_counts_calls_not_events(errors: list[str]) -> None:
    """#696: one call must count as 1 regardless of how many skill_invoke lines
    it logs. Reproduces the real retro pattern — harness started+success PLUS a
    Phase-3 emit (retro-telemetry.sh: a THIRD skill_invoke line, outcome=success,
    tool_use_id="") — against a plain skill that only ever logs started+success.
    Before the fix both were counted by raw skill_invoke event count (retro=3,
    plain=2), making the two incomparable; after the fix only outcome=started
    counts, so both are 1.
    """
    print("\ncase: lifecycle_counts_calls_not_events")
    catalog = ["feedback-loop:retro", "thinking-tools:expert-panel"]
    events = [
        # retro: harness started+success + one extra Phase-3 emit (success, no tool_use_id)
        {**_ev("skill_invoke", name="retro", outcome="started"),
         "qualified_name": "feedback-loop:retro", "tool_use_id": "t1"},
        {**_ev("skill_invoke", name="retro", outcome="success"),
         "qualified_name": "feedback-loop:retro", "tool_use_id": "t1"},
        {**_ev("skill_invoke", name="retro", outcome="success"),
         "qualified_name": "feedback-loop:retro", "tool_use_id": ""},
        # expert-panel: harness started+success only, one real call.
        {**_ev("skill_invoke", name="expert-panel", outcome="started"),
         "qualified_name": "thinking-tools:expert-panel", "tool_use_id": "t2"},
        {**_ev("skill_invoke", name="expert-panel", outcome="success"),
         "qualified_name": "thinking-tools:expert-panel", "tool_use_id": "t2"},
    ]
    result = report.skill_lifecycle_view(events, catalog=catalog)
    bottom = {s: c for s, c in result["bottom"]}
    _assert(bottom.get("feedback-loop:retro") == 1,
            f"retro's Phase-3 emit does not inflate its call count (got: {bottom})", errors)
    _assert(bottom.get("thinking-tools:expert-panel") == 1,
            f"expert-panel counts its one real call (got: {bottom})", errors)
    _assert(bottom.get("feedback-loop:retro") == bottom.get("thinking-tools:expert-panel"),
            "1 call each is comparable across skills regardless of extra emits", errors)


def case_lifecycle_stale_tracks_any_outcome(errors: list[str]) -> None:
    """Fresh-context review finding on #696: gating last_seen on outcome=='started'
    (same as the count filter) would make a call whose 'started' line falls
    outside this window while its 'success'/'error' line doesn't (a call
    straddling the UTC day-file boundary --since slices on — real for a
    long-running skill like retro, which the issue's own data shows running
    10+ minutes) read as staler than it really is. last_seen must track ANY
    skill_invoke event, not just started ones, so a recent completion-only
    line still refreshes recency even on a window where it can't register a
    full call count.

    Fixture: one OLD started event (>14d ago) establishes counts>0, plus one
    RECENT success-only event (no started sibling in this event list, as if
    its started line landed outside the window). If last_seen only tracked
    started events, last_seen would stay pinned to the old timestamp and the
    skill would wrongly show as stale.
    """
    print("\ncase: lifecycle_stale_tracks_any_outcome")
    catalog = ["feedback-loop:retro"]
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent_ts = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = [
        {**_ev("skill_invoke", name="retro", outcome="started"),
         "qualified_name": "feedback-loop:retro", "ts": old_ts},
        {**_ev("skill_invoke", name="retro", outcome="success"),
         "qualified_name": "feedback-loop:retro", "ts": recent_ts},
    ]
    result = report.skill_lifecycle_view(events, catalog=catalog)
    _assert("feedback-loop:retro" not in result["stale"],
            "a recent success-only event refreshes last_seen and keeps the "
            "skill out of stale, even though only the old started event counts",
            errors)


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
# Liveness aggregation cases (#491)
# ---------------------------------------------------------------------------

def case_liveness_excluded_from_outcomes(errors: list[str]) -> None:
    """rule_fire (outcome=fired) never appears in the outcome mix; it gets its
    own liveness total/by_event instead, in both json and table."""
    print("\ncase: liveness_excluded_from_outcomes")
    fixture = [
        {**_ev("rule_fire", name="no-pyyaml"), "outcome": "fired"},
        {**_ev("rule_fire", name="no-pyyaml"), "outcome": "fired"},
        {**_ev("rule_fire", name="trash-not-rm"), "outcome": "fired"},
        _ev("skill_invoke", 10, name="note"),
        _ev("skill_invoke", 10, name="note"),
    ]
    out = _run_main_with(fixture, ["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    _assert("fired" not in payload["outcomes"],
            f"'fired' absent from outcomes (got: {payload['outcomes']})", errors)
    _assert(payload["outcomes"] == {"ok": 2},
            f"outcomes reflects only non-liveness events (got: {payload['outcomes']})",
            errors)
    _assert(payload["liveness"] == {"total": 3, "by_event": {"rule_fire": 3}},
            f"liveness total/by_event correct (got: {payload.get('liveness')})", errors)

    tout = _run_main_with(fixture, ["report.py", "--since=all", "--format=table"])
    outcomes_line = next((ln for ln in tout.splitlines() if ln.startswith("Outcomes:")), "")
    _assert("fired" not in outcomes_line,
            f"table Outcomes line excludes fired (got: {outcomes_line!r})", errors)
    _assert("Liveness (enforcement heartbeat" in tout,
            "table renders a dedicated liveness line", errors)


def case_liveness_no_fires_no_line(errors: list[str]) -> None:
    """No rule_fire events → liveness.total is 0 and the table prints no liveness line."""
    print("\ncase: liveness_no_fires_no_line")
    fixture = [_ev("skill_invoke", 10, name="note")]
    out = _run_main_with(fixture, ["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    _assert(payload["liveness"] == {"total": 0, "by_event": {}},
            f"liveness is zeroed, not omitted (got: {payload.get('liveness')})", errors)
    tout = _run_main_with(fixture, ["report.py", "--since=all", "--format=table"])
    _assert("Liveness (" not in tout, "no liveness line when nothing fired", errors)


def case_liveness_excluded_from_top_by_default(errors: list[str]) -> None:
    """Top N excludes liveness events by default, even when they'd dominate by count."""
    print("\ncase: liveness_excluded_from_top_by_default")
    fixture = (
        [{**_ev("rule_fire", name="noisy-rule"), "outcome": "fired"} for _ in range(5)]
        + [_ev("skill_invoke", 10, name="note")]
    )
    out = _run_main_with(fixture, ["report.py", "--since=all", "--format=json"])
    payload = json.loads(out)
    top_events = {row["event"] for row in payload["top"]}
    _assert("rule_fire" not in top_events,
            f"rule_fire absent from Top N by default (got: {payload['top']})", errors)
    _assert("skill_invoke" in top_events, "skill_invoke present in Top N", errors)
    _assert(payload["top_includes_liveness"] is False,
            "top_includes_liveness reflects the default (False)", errors)

    tout = _run_main_with(fixture, ["report.py", "--since=all", "--format=table"])
    _assert("liveness events excluded" in tout,
            "table Top N header states the default exclusion", errors)
    # The dedicated "Rule-fire liveness" section legitimately names noisy-rule —
    # only the Top N block itself must exclude it.
    top_block = tout.split("Top 10")[1].split("Skill lifecycle")[0]
    _assert("noisy-rule" not in top_block,
            f"excluded rule_fire name absent from the Top N block (got: {top_block!r})",
            errors)


def case_liveness_included_with_flag(errors: list[str]) -> None:
    """--top-include-liveness folds liveness events back into Top N (opt-in)."""
    print("\ncase: liveness_included_with_flag")
    fixture = (
        [{**_ev("rule_fire", name="noisy-rule"), "outcome": "fired"} for _ in range(5)]
        + [_ev("skill_invoke", 10, name="note")]
    )
    out = _run_main_with(
        fixture, ["report.py", "--since=all", "--format=json", "--top-include-liveness"]
    )
    payload = json.loads(out)
    top_events = {row["event"]: row["count"] for row in payload["top"]}
    _assert(top_events.get("rule_fire") == 5,
            f"rule_fire folded back into Top N with the flag (got: {payload['top']})", errors)
    _assert(payload["top_includes_liveness"] is True,
            "top_includes_liveness reflects the flag (True)", errors)
    # outcome mix stays excluded regardless — the flag only affects Top N.
    _assert("fired" not in payload["outcomes"],
            "outcome mix still excludes liveness even with the flag", errors)

    tout = _run_main_with(
        fixture, ["report.py", "--since=all", "--format=table", "--top-include-liveness"]
    )
    _assert("liveness events included" in tout,
            "table Top N header states liveness is included with the flag", errors)


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


def case_token_cost_bracket_variant_matches_bare_key(errors: list[str]) -> None:
    """#650: a bracketed context-window variant (e.g. 'claude-opus-5[1m]') prices
    identically to its registered bare key — the bracket carries no hyphen, so
    the #510 hyphen-suffix rule alone must not be the only path that works."""
    print("\ncase: token_cost_bracket_variant_matches_bare_key")
    events = [_meta_ev(model="claude-opus-5[1m]", input_tokens=1_000_000)]
    res = report.token_cost_view(events)
    _assert(res["cost"] is not None, "bracket-variant opus id still prices", errors)
    _assert(abs(res["cost"]["input"] - 5.00) < 1e-9,
            f"bracket variant uses the bare opus rate (got: {res['cost']})", errors)
    _assert(res["priced_events"] == 1 and res["excluded_events"] == 0,
            "bracket-variant id counts as priced, not excluded/unpriced", errors)


def case_token_cost_excluded_line_visible_in_table(errors: list[str]) -> None:
    """#650: excluded-event count renders as its own breakdown line (not only
    buried in the cost caveat footnote) whenever some event was excluded."""
    print("\ncase: token_cost_excluded_line_visible_in_table")
    events = [
        {**_ev("skill_invoke", 10, name="a"),
         "meta": {"duration_ms": 10, "model": "claude-sonnet-5", "input_tokens": 1000}},
        {**_ev("skill_invoke", 10, name="b"),
         "meta": {"duration_ms": 10, "model": "claude-made-up-9", "input_tokens": 500}},
    ]
    out = _run_main_with(events, ["report.py", "--since=all", "--format=table"])
    _assert("excluded" in out and "events=" in out,
            f"table shows an explicit excluded-events line (got: {out!r})", errors)
    _assert("claude-made-up-9" in out,
            "excluded line names the unregistered model", errors)


def case_token_cost_all_unpriced_excluded_line_absent(errors: list[str]) -> None:
    """#657: when every event is unpriced (cost is None), the excluded-events
    breakdown row must not also print — only the '비용 열 생략' block should,
    so the same excluded count isn't restated twice."""
    print("\ncase: token_cost_all_unpriced_excluded_line_absent")
    events = [
        {**_ev("skill_invoke", 10, name="a"),
         "meta": {"duration_ms": 10, "model": "claude-made-up-9", "input_tokens": 500}},
    ]
    out = _run_main_with(events, ["report.py", "--since=all", "--format=table"])
    _assert("비용 열 생략" in out, "cost-is-None caveat block prints", errors)
    _assert("events=" not in out,
            f"excluded-events breakdown row does not also print (got: {out!r})", errors)


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


def case_plugin_unknown_split(errors: list[str]) -> None:
    """#664: plugin=unknown splits into attribution_failure vs no_target."""
    print("\ncase: plugin_unknown_split")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pluginA" / "skills" / "skillX").mkdir(parents=True)
        (root / "pluginA" / "skills" / "skillX" / "SKILL.md").write_text("x")
        (root / "pluginA" / "agents").mkdir(parents=True)
        (root / "pluginA" / "agents" / "agentY.md").write_text("y")

        owned = report.claude_kit_owned_names(repo_root=root)
        _assert(owned == {"skillX", "agentY"},
                f"owned names = skill + agent bare names (got: {owned})", errors)

        events = [
            # a. name IS ours (skill) -> attribution_failure
            {"plugin": "unknown", "event": "skill_invoke", "name": "skillX"},
            # a. name IS ours (agent) -> attribution_failure
            {"plugin": "unknown", "event": "agent_spawn", "name": "agentY"},
            # b. native command -> no_target
            {"plugin": "unknown", "event": "command_run", "name": "/goal"},
            # c. built-in agent -> no_target
            {"plugin": "unknown", "event": "agent_spawn", "name": "general-purpose"},
            # d. plugin outside claude-kit -> no_target
            {"plugin": "unknown", "event": "skill_invoke", "name": "ponytail"},
            # not unknown at all -> excluded entirely
            {"plugin": "pluginA", "event": "skill_invoke", "name": "skillX"},
        ]
        split = report.classify_unknown(events, repo_root=root)
        _assert(split == {"total_unknown": 5, "attribution_failure": 2, "no_target": 3},
                f"split counts (got: {split})", errors)


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
    case_scan_skill_catalog_repo_layout(errors)
    case_scan_skill_catalog_cache_layout(errors)
    case_lifecycle_stale_note(errors)
    case_lifecycle_caveat_in_output(errors)
    case_lifecycle_caveat_in_json(errors)
    case_lifecycle_fired_bottom_e2e(errors)
    case_lifecycle_counts_calls_not_events(errors)
    case_lifecycle_stale_tracks_any_outcome(errors)
    case_rule_fire_per_rule_id(errors)
    case_rule_fire_view_end_to_end(errors)
    case_liveness_excluded_from_outcomes(errors)
    case_liveness_no_fires_no_line(errors)
    case_liveness_excluded_from_top_by_default(errors)
    case_liveness_included_with_flag(errors)
    case_token_cost_weighted_calculation(errors)
    case_token_cost_ranking_inversion(errors)
    case_token_cost_missing_model_excluded(errors)
    case_token_cost_unregistered_model_excluded(errors)
    case_token_cost_date_suffixed_model_matches_bare_key(errors)
    case_token_cost_bracket_variant_matches_bare_key(errors)
    case_token_cost_excluded_line_visible_in_table(errors)
    case_token_cost_all_unpriced_excluded_line_absent(errors)
    case_token_cost_mixed_priced_and_unpriced(errors)
    case_token_cost_no_token_data(errors)
    case_token_cost_zero_cost_not_mislabeled_omitted(errors)
    case_token_cost_view_end_to_end(errors)
    case_plugin_unknown_split(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
