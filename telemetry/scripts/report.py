#!/usr/bin/env python3
"""Report top events, outcome distribution, and weekly trend.

Phase 1 W2 deliverable. Skeleton here covers --top counts; the latency/trend
sections expand once we have a week of dogfooding data.

Usage:
    report.py [--since=Nd] [--plugin=NAME|all] [--event=NAME|all]
              [--top=N] [--format=table|json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TELEMETRY_DIR = SCRIPT_DIR.parent
EVENTS_DIR = TELEMETRY_DIR / "events"
REPO_ROOT = TELEMETRY_DIR.parent

# Stale threshold for lifecycle view (days since last use).
_STALE_DAYS = 14
# Bottom-N threshold for lifecycle view.
_BOTTOM_N = 5

# Interpretation guide — hardcoded per DoD.
_LIFECYCLE_CAVEAT = "측정범위: claude-kit 레포 내 세션 기준 (telemetry Option A)"
# NOTE: vault-bridge is deliberately NOT named here — it ships agents/commands/
# hooks but no skills/, so it can never appear in this skills-catalog view
# (isolated-critique LOW finding, 2026-06-10). OVM is the representative class.
_LIFECYCLE_GUIDE = (
    "해석 가이드: thinking-tools류(in-repo 사용 본질)의 never-fired는 죽은 표면 신호로 "
    "우선 해석하세요. OVM류(타 프로젝트 사용 주류)의 never-fired는 "
    "측정범위 밖 사용 가능성을 먼저 의심하세요."
)


def load_events(since_days: int | None = None):
    if not EVENTS_DIR.is_dir():
        return []
    cutoff = None
    if since_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date()
    events = []
    for path in sorted(EVENTS_DIR.glob("events-*.jsonl")):
        try:
            d = datetime.strptime(path.stem[len("events-"):], "%Y-%m-%d").date()
        except ValueError:
            continue
        if cutoff and d < cutoff:
            continue
        with path.open(encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    return events


def parse_since(s: str | None) -> int | None:
    if not s or s == "all":
        return None
    if not s.endswith("d"):
        raise SystemExit("--since must be 'Nd' or 'all'")
    return int(s[:-1])


def collect_durations(events: list[dict]) -> list[float]:
    """Pull numeric meta.duration_ms values across events.

    Only events whose meta carries a non-null numeric duration_ms count. Events
    with empty meta, a null duration_ms (no timing datum), or a non-numeric value
    are skipped — so the latency stats reflect real timing samples only. bool is
    explicitly rejected (it is an int subclass in Python).
    """
    durations: list[float] = []
    for e in events:
        meta = e.get("meta")
        if not isinstance(meta, dict):
            continue
        d = meta.get("duration_ms")
        if isinstance(d, bool) or not isinstance(d, (int, float)):
            continue
        durations.append(float(d))
    return durations


def percentile(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank percentile (q in [0,1]) over a pre-sorted list.

    Nearest-rank avoids interpolation ambiguity and matches the "pick the
    sample at rank ceil(q*N)" definition used for small-N dogfooding data.
    """
    if not sorted_vals:
        raise ValueError("percentile of empty list")
    n = len(sorted_vals)
    rank = max(1, math.ceil(q * n))
    return sorted_vals[rank - 1]


def latency_stats(events: list[dict]) -> dict | None:
    """Return {count, p50, p95} over events carrying meta.duration_ms, or None.

    None signals "no timing samples" so callers can render a skip line rather
    than fabricating zeros.
    """
    durations = collect_durations(events)
    if not durations:
        return None
    durations.sort()
    return {
        "count": len(durations),
        "p50": percentile(durations, 0.50),
        "p95": percentile(durations, 0.95),
    }


def latency_by_event(events: list[dict]) -> dict[str, dict[str, float | int]]:
    """Per-event-type latency p50/p95, keyed by the logical `event` field.

    Buckets events by their `event` value (skill_invoke / agent_spawn / stop /
    ...) and runs latency_stats on each bucket. Only event types that carry at
    least one numeric meta.duration_ms sample appear in the result — a type with
    no timing samples is omitted entirely (latency_stats returns None), mirroring
    the overall-latency "no datum → skip" contract rather than fabricating zeros.

    This composes with the caller's --event filter for free: callers filter the
    events list before passing it in, so a one-type filter yields a single-bucket
    breakdown and the unfiltered list yields the full per-type split.
    """
    buckets: dict[str, list[dict]] = {}
    for e in events:
        buckets.setdefault(e.get("event", "?"), []).append(e)
    out: dict[str, dict] = {}
    for ev_type, bucket in buckets.items():
        stats = latency_stats(bucket)
        if stats is not None:
            out[ev_type] = stats
    return out


def scan_skill_catalog(repo_root: Path | None = None) -> list[str]:
    """Return sorted list of '{plugin}:{skill}' identifiers from SKILL.md files.

    Glob pattern: <repo_root>/*/skills/*/SKILL.md (depth-2 only, no hidden dirs).
    plugin = first path component (e.g. 'thinking-tools').
    skill  = third path component (e.g. 'expert-panel').
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    catalog: list[str] = []
    for skill_md in root.glob("*/skills/*/SKILL.md"):
        parts = skill_md.relative_to(root).parts
        # Expected: (plugin, 'skills', skill_name, 'SKILL.md') → 4 parts
        if len(parts) != 4:
            continue
        plugin, _, skill_name, _ = parts
        # Skip hidden directories
        if plugin.startswith("."):
            continue
        catalog.append(f"{plugin}:{skill_name}")
    return sorted(catalog)


def skill_lifecycle_view(
    events: list[dict],
    catalog: list[str] | None = None,
    stale_days: int = _STALE_DAYS,
    bottom_n: int = _BOTTOM_N,
    since_days: int | None = None,
) -> dict:
    """Derive per-skill lifecycle signals from events vs. catalog.

    Returns a dict with keys:
      catalog        - full catalog list
      never_fired    - skills with 0 events in the window
      stale          - skills whose last event is > stale_days ago (excluding never-fired)
      stale_note     - non-None when the --since window is too short to ever
                       contain a stale event (the section would be inert)
      bottom         - bottom_n skills by count (excluding never-fired), sorted ascending
      caveat         - measurement-scope caveat string
      guide          - interpretation guide string

    Matching: event['qualified_name'] == '{plugin}:{skill}' (catalog format).
    Only skill_invoke events (event == 'skill_invoke') with a non-empty
    qualified_name are counted — other event types don't carry skill identity.
    """
    if catalog is None:
        catalog = scan_skill_catalog()

    catalog_set = set(catalog)
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=stale_days)

    # Collect last-seen timestamp and counts per qualified_name from skill_invoke events.
    last_seen: dict[str, datetime] = {}
    counts: Counter[str] = Counter()
    for e in events:
        if e.get("event") != "skill_invoke":
            continue
        qn = e.get("qualified_name", "")
        if not qn or qn not in catalog_set:
            continue
        counts[qn] += 1
        ts_raw = e.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if qn not in last_seen or ts > last_seen[qn]:
            last_seen[qn] = ts

    # 1. never-fired: in catalog but count == 0
    never_fired = sorted(s for s in catalog if counts[s] == 0)

    # 2. stale: has events but last seen > stale_days ago
    stale = sorted(
        s for s in catalog
        if counts[s] > 0 and s in last_seen and last_seen[s] < stale_cutoff
    )

    # A bounded --since window <= the stale threshold filters out every event old
    # enough to be stale BEFORE this view runs, so the section would render "(none)"
    # unconditionally. Surface that instead of silently hiding the one signal the
    # stale view exists for (isolated-critique MEDIUM finding, 2026-06-10).
    stale_note = None
    if since_days is not None and since_days <= stale_days:
        stale_note = (
            f"--since={since_days}d window cannot contain >{stale_days}d-old events; "
            "use --since=all or a window above the stale threshold"
        )

    # 3. bottom-N: skills with events, sorted by count ascending, top bottom_n
    fired = [(s, counts[s]) for s in catalog if counts[s] > 0]
    fired.sort(key=lambda x: (x[1], x[0]))
    bottom = fired[:bottom_n]

    return {
        "catalog": catalog,
        "never_fired": never_fired,
        "stale": stale,
        "stale_note": stale_note,
        "bottom": bottom,
        "caveat": _LIFECYCLE_CAVEAT,
        "guide": _LIFECYCLE_GUIDE,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", default="7d", help="time window (e.g. '7d', 'all')")
    p.add_argument("--plugin", default="all")
    p.add_argument("--event", default="all")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--format", choices=("table", "json"), default="table")
    args = p.parse_args()

    since_days = parse_since(args.since)
    events = load_events(since_days)

    if args.plugin != "all":
        events = [e for e in events if e.get("plugin") == args.plugin]
    if args.event != "all":
        events = [e for e in events if e.get("event") == args.event]

    if not events:
        print(f"No events matched (since={args.since}, plugin={args.plugin}, event={args.event})")
        return 0

    counts = Counter(
        (e.get("plugin", "?"), e.get("event", "?"), e.get("name", ""))
        for e in events
    )
    outcomes = Counter(e.get("outcome", "?") for e in events)
    plugin_unknown = sum(1 for e in events if e.get("plugin") == "unknown")
    unknown_ratio = plugin_unknown / len(events)

    latency = latency_stats(events)
    latency_per_event = latency_by_event(events)

    lifecycle = skill_lifecycle_view(events, since_days=since_days)

    if args.format == "json":
        payload = {
            "total": len(events),
            "since": args.since,
            "outcomes": dict(outcomes),
            "plugin_unknown_ratio": round(unknown_ratio, 4),
            "latency": (
                {
                    "count": latency["count"],
                    "p50_ms": round(latency["p50"], 1),
                    "p95_ms": round(latency["p95"], 1),
                }
                if latency is not None
                else None
            ),
            "latency_by_event": {
                ev_type: {
                    "count": s["count"],
                    "p50_ms": round(s["p50"], 1),
                    "p95_ms": round(s["p95"], 1),
                }
                for ev_type, s in sorted(latency_per_event.items())
            },
            "top": [
                {"plugin": plg, "event": ev, "name": nm, "count": c}
                for (plg, ev, nm), c in counts.most_common(args.top)
            ],
            "lifecycle": {
                "caveat": lifecycle["caveat"],
                "never_fired": lifecycle["never_fired"],
                "stale": lifecycle["stale"],
                "stale_note": lifecycle["stale_note"],
                "bottom": [
                    {"skill": s, "count": c} for s, c in lifecycle["bottom"]
                ],
                "guide": lifecycle["guide"],
            },
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Total events: {len(events)} (since={args.since})")
    print(f"Outcomes: {dict(outcomes)}")
    print(f"plugin=unknown ratio: {unknown_ratio:.1%}")
    print()
    print("Latency p50/p95 (events with duration_ms only):")
    if latency is None:
        print("  (no events carry meta.duration_ms — nothing to report)")
    else:
        print(
            f"  n={latency['count']}  "
            f"p50={latency['p50']:.0f}ms  p95={latency['p95']:.0f}ms"
        )
        print("  by event type:")
        max_width = max((len(k) for k in latency_per_event), default=14)
        for ev_type, s in sorted(latency_per_event.items()):
            print(
                f"    {ev_type:<{max_width}} "
                f"n={s['count']:<4} "
                f"p50={s['p50']:.0f}ms  p95={s['p95']:.0f}ms"
            )
    print()
    print(f"Top {args.top}:")
    for (plg, ev, nm), c in counts.most_common(args.top):
        label = f"{plg}:{ev}" + (f" ({nm})" if nm else "")
        print(f"  {c:>5}  {label}")
    print()
    print(f"Skill lifecycle ({lifecycle['caveat']}):")
    if lifecycle["never_fired"]:
        print(f"  never-fired ({len(lifecycle['never_fired'])}):")
        for s in lifecycle["never_fired"]:
            print(f"    {s}")
    else:
        print("  never-fired: (none)")
    if lifecycle["stale"]:
        print(f"  last-used > {_STALE_DAYS}d ({len(lifecycle['stale'])}):")
        for s in lifecycle["stale"]:
            print(f"    {s}")
    else:
        print(f"  last-used > {_STALE_DAYS}d: (none)")
    if lifecycle["stale_note"]:
        print(f"    ({lifecycle['stale_note']})")
    if lifecycle["bottom"]:
        print(f"  bottom-{_BOTTOM_N} (by count):")
        for s, c in lifecycle["bottom"]:
            print(f"    {c:>5}  {s}")
    else:
        print(f"  bottom-{_BOTTOM_N}: (none)")
    print(f"  {lifecycle['guide']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
