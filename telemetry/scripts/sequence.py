#!/usr/bin/env python3
"""Extract 2-gram and 3-gram event sequences within sessions.

Phase 1 W3 deliverable. Skeleton here exposes the CLI shape and a minimal
2-gram count so the surface is locked in before full impl.

Usage:
    sequence.py [--since=Nd] [--n=2|3] [--top=N]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from report import load_events, parse_since  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", default="7d")
    p.add_argument("--n", type=int, choices=(2, 3), default=2)
    p.add_argument("--top", type=int, default=20)
    args = p.parse_args()

    since_days = parse_since(args.since)
    events = load_events(since_days)
    if not events:
        print("No events to analyze")
        return 0

    # Bucket events by session_id, preserving order.
    sessions: dict[str, list[str]] = defaultdict(list)
    for e in events:
        sid = e.get("session_id") or ""
        ev = e.get("event") or ""
        nm = e.get("name") or ""
        if ev in {"skill_invoke", "agent_spawn", "command_run"} and nm:
            sessions[sid].append(f"{ev}:{nm}")

    ngrams: Counter = Counter()
    for seq in sessions.values():
        for i in range(len(seq) - args.n + 1):
            ngrams[tuple(seq[i:i + args.n])] += 1

    if not ngrams:
        print(f"No {args.n}-grams found")
        return 0

    print(f"Top {args.top} {args.n}-grams (across {len(sessions)} sessions):")
    for gram, c in ngrams.most_common(args.top):
        print(f"  {c:>4}  {' -> '.join(gram)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
