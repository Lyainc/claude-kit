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
    return 0


if __name__ == "__main__":
    sys.exit(main())
