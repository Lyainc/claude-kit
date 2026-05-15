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

    if args.format == "json":
        payload = {
            "total": len(events),
            "since": args.since,
            "outcomes": dict(outcomes),
            "plugin_unknown_ratio": round(unknown_ratio, 4),
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
    print(f"Top {args.top}:")
    for (plg, ev, nm), c in counts.most_common(args.top):
        label = f"{plg}:{ev}" + (f" ({nm})" if nm else "")
        print(f"  {c:>5}  {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
