#!/usr/bin/env python3
"""Extract 2-gram and 3-gram event sequences within sessions.

Phase 1 W3 deliverable. Skeleton here exposes the CLI shape and a minimal
2-gram count so the surface is locked in before full impl.

retro invokes this as a best-effort waste signal with `2>/dev/null` (SKILL.md
Phase 1 §3), so a missing-events / empty-output run is a tolerated no-op rather
than a failure. The n-gram counting itself IS gated — test-sequence.py (#458).

`count_ngrams` never reports a same-label window (#598) — a run of N
consecutive identical labels used to inflate into N-1 adjacent-pair matches,
so a single 9-call isolated-subagent fan-out (expert-panel's E1/E2/E3 rounds,
each a distinct persona) outscored every genuine A->B repeat in `--top=N` and
read as the #1 waste pattern despite being zero-waste orchestration. Same-label
runs are reported separately by `count_self_transition_runs`, keyed by run
length — a length-2 run (real re-delegation candidate) and a length-9 run
(fan-out) land in different buckets instead of one inflated count.

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


# Event types whose calls emit a started row and a terminal row sharing one
# tool_use_id. `command_run` is deliberately absent: it emits a SINGLE id-less
# started row, which is why the id-less guard below is scoped to this set.
_PAIRED_LIFECYCLE = {"skill_invoke", "agent_spawn"}


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
        # A paired type carries an id on BOTH its rows, so an id-less TERMINAL row is
        # not a lifecycle row at all — it is a supplementary emit riding the same event
        # type (retro's Phase-3 counter line, retro-telemetry.sh:71, hardcoded
        # outcome="success" tool_use_id=""). The dedup above never dedups an empty id,
        # so without this guard that line lands as a second `skill_invoke:retro` and ONE
        # retro call reads as a self-transition run of 2 — which retro/SKILL.md calls
        # "review-round churn worth an item", making every retro run manufacture a
        # phantom waste item about itself. Same root cause as #696 (the emit reusing
        # skill_invoke); report.py fixed its half by counting only outcome=='started',
        # which this function cannot do — command_run emits a single id-less 'started'
        # row, so an outcome filter would erase that type outright. Keyed on
        # terminal-outcome AND empty id instead: command_run ('started') and every real
        # lifecycle row (has an id) both escape it.
        if ev in _PAIRED_LIFECYCLE and not tid and (e.get("outcome") or "") != "started":
            continue
        nm = e.get("name") or ""
        if ev in {"skill_invoke", "agent_spawn", "command_run"} and nm:
            sessions[e.get("session_id") or ""].append(f"{ev}:{nm}")
    return sessions


def count_ngrams(sessions: dict[str, list[str]], n: int) -> Counter:
    """Count n-gram transitions, excluding windows where every item is the same label.

    A same-label window is a fan-out/repeat RUN, not a transition — see
    count_self_transition_runs. Counting it here too would double-report it under two
    different units (window count vs. run length) and let a long run still dominate the
    mixed-transition ranking via sheer window count (#598).
    """
    ngrams: Counter = Counter()
    for seq in sessions.values():
        for i in range(len(seq) - n + 1):
            gram = tuple(seq[i:i + n])
            if len(set(gram)) == 1:
                continue
            ngrams[gram] += 1
    return ngrams


def count_self_transition_runs(sessions: dict[str, list[str]]) -> Counter:
    """Count consecutive same-label runs (length >= 2), keyed by (label, run length).

    Where the old adjacent-pair count turned one N-call run into N-1 matches, this turns
    it into ONE entry at its actual length. A length-2 run (one immediate re-delegation)
    and a length-9 run (a 9-persona panel round) never merge into the same bucket, so
    length — not count — is what tells a real repeat apart from designed fan-out (#598).
    """
    runs: Counter = Counter()
    for seq in sessions.values():
        i = 0
        while i < len(seq):
            j = i
            while j + 1 < len(seq) and seq[j + 1] == seq[i]:
                j += 1
            length = j - i + 1
            if length >= 2:
                runs[(seq[i], length)] += 1
            i = j + 1
    return runs


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
    runs = count_self_transition_runs(sessions)

    if not ngrams and not runs:
        print(f"No {args.n}-grams found")
        return 0

    if ngrams:
        print(f"Top {args.top} {args.n}-grams (across {len(sessions)} sessions):")
        for gram, c in ngrams.most_common(args.top):
            print(f"  {c:>4}  {' -> '.join(gram)}")

    if runs:
        if ngrams:
            print()
        print(f"Top {args.top} self-transition runs (across {len(sessions)} sessions) "
              "— same label repeated consecutively, by run length:")
        for (label, length), c in runs.most_common(args.top):
            print(f"  {c:>4}x  {label}  (run length {length})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
