#!/usr/bin/env python3
"""Extract 2-gram and 3-gram event sequences within sessions.

Phase 1 W3 deliverable. Skeleton here exposes the CLI shape and a minimal
2-gram count so the surface is locked in before full impl.

retro invokes this as a best-effort waste signal with `2>/dev/null` (SKILL.md
Phase 1 §3), so a missing-events / empty-output run is a tolerated no-op rather
than a failure. The n-gram counting itself IS gated — test-sequence.py (#458).

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


def session_sequences(events: list[dict]) -> dict[str, list[str]]:
    """Bucket events by session_id, in order, as `event:name` labels.

    Collapsed to ONE row per call first. The stream logs `started` and then
    `success`/`error` for the same call, so an in-session n-gram reads that
    lifecycle pair as an `X -> X` self-transition and reports a single call as
    repetition (#458) — which retro then reads as a waste signal. report.py's
    outcome mix legitimately counts both rows (calls vs completions), so the
    collapse belongs here, not in load_events.

    Dedup by `tool_use_id`, NOT by dropping `outcome == "started"`. The paired
    types carry an id and always emit `started` first, so keeping the first row
    holds their position in the sequence — but `command_run` emits a SINGLE
    `started` row with an empty id and no terminal row at all, so an
    outcome-based filter erases that type outright and fuses its neighbours into
    a repeat that never happened. A call that starts and never completes is the
    same trap. An empty id is therefore never deduped: it marks a row that is
    already one-per-call.
    """
    sessions: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for e in events:
        tid = e.get("tool_use_id") or ""
        if tid:
            key = (e.get("event") or "", tid)
            if key in seen:
                continue
            seen.add(key)
        ev = e.get("event") or ""
        nm = e.get("name") or ""
        if ev in {"skill_invoke", "agent_spawn", "command_run"} and nm:
            sessions[e.get("session_id") or ""].append(f"{ev}:{nm}")
    return sessions


def count_ngrams(sessions: dict[str, list[str]], n: int) -> Counter:
    ngrams: Counter = Counter()
    for seq in sessions.values():
        for i in range(len(seq) - n + 1):
            ngrams[tuple(seq[i:i + n])] += 1
    return ngrams


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

    sessions = session_sequences(events)
    ngrams = count_ngrams(sessions, args.n)

    if not ngrams:
        print(f"No {args.n}-grams found")
        return 0

    print(f"Top {args.top} {args.n}-grams (across {len(sessions)} sessions):")
    for gram, c in ngrams.most_common(args.top):
        print(f"  {c:>4}  {' -> '.join(gram)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
