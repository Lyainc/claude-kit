#!/usr/bin/env python3
"""Regression test — sequence.py collapses the started/success lifecycle pair (#458).

The event stream writes TWO rows per call: `outcome:"started"` and then
`outcome:"success"` (or `"error"`), same call. sequence.py used to feed both into the
in-session n-gram window, so every single call produced an `X -> X` self-transition.
retro reads that output as "repeated n-grams (review-round churn)" — a waste signal —
so the counter was reporting its own instrumentation as waste, and the phantom
self-transitions took the `--top=N` slots away from real repeats. Measured on a 7d
window: `retro -> retro` = 19 for a skill that ran once per session.

Pinned here:

  1. A started/success pair for one call yields NO 2-gram at all.
  2. Two genuinely consecutive calls still yield exactly one 2-gram (the fix must not
     erase real repetition — the failure mode in the other direction).
  3. `error` outcomes still count: a failed call happened, and a retry loop after it is
     exactly the repetition retro is looking for.
  3b. `command_run` survives. It emits a SINGLE `started` row with an empty tool_use_id and
     no terminal row, so an outcome-based filter erases the whole type — and worse, fuses
     the calls on either side of it into a repeat that never happened. Same trap for a call
     that starts and never completes (167 agent_spawn `started` vs 164 `success` in the
     repo's own 7d events). This is why the collapse keys on tool_use_id, not on outcome.
  4. n-grams never span a session boundary.
  5. 3-gram windows hold after the filter (`--n=3` is a supported CLI shape).
  6. Non-sequence event types (tool_use, rule_fire) and unnamed events are excluded.

Run: python3 feedback-loop/scripts/test/test-sequence.py
Exit 0 on pass, 1 on fail.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import sequence  # noqa: E402


_ids = iter(range(1, 10_000))


def _ev(name: str, outcome: str = "success", session: str = "s1",
        event: str = "skill_invoke", tool_use_id: str = "") -> dict:
    return {"session_id": session, "event": event, "name": name, "outcome": outcome,
            "tool_use_id": tool_use_id}


def _call(name: str, **kw) -> list[dict]:
    """One real invocation as the stream records it: started, then success, same id."""
    tid = f"tu_{next(_ids)}"
    return [_ev(name, outcome="started", tool_use_id=tid, **kw),
            _ev(name, outcome="success", tool_use_id=tid, **kw)]


def _command(name: str, **kw) -> list[dict]:
    """A slash command: ONE `started` row, empty tool_use_id, no terminal row."""
    return [_ev(name, outcome="started", event="command_run", **kw)]


def _grams(events: list[dict], n: int = 2) -> dict:
    return dict(sequence.count_ngrams(sequence.session_sequences(events), n))


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    errors: list[str] = []

    def check(cond: bool, desc: str) -> None:
        if cond:
            print(f"  ok   {desc}")
        else:
            print(f"  FAIL {desc}", file=sys.stderr)
            errors.append(desc)

    if not hasattr(sequence, "session_sequences") or not hasattr(sequence, "count_ngrams"):
        print("  FAIL sequence.py exposes no lifecycle-filtered n-gram path "
              "(session_sequences/count_ngrams) — started rows still reach the window",
              file=sys.stderr)
        print("\nRESULT: 1 check(s) FAILED — see above.")
        return 1

    # 1. One call = one event. Its lifecycle pair must not become a self-transition.
    check(_grams(_call("retro")) == {},
          "single call (started+success) produces no 2-gram")

    # 2. Real repetition survives.
    check(_grams(_call("retro") + _call("retro")) ==
          {("skill_invoke:retro", "skill_invoke:retro"): 1},
          "two consecutive calls still count as one repeat")

    # 3. A failed call is a real call; the retry after it is real repetition.
    failed = _call("retro")
    failed[1]["outcome"] = "error"
    check(_grams(failed + _call("retro")) ==
          {("skill_invoke:retro", "skill_invoke:retro"): 1},
          "error outcome counts (failed call + retry = one repeat)")

    # 3b. command_run has no terminal row and no id — it must survive intact, and it must
    #     still SEPARATE its neighbours. Dropping it would report a phantom a -> a repeat.
    check(_grams(_command("goal")) == {}, "a lone command_run yields no 2-gram")
    check(_grams(_call("a") + _command("goal") + _call("a")) == {
        ("skill_invoke:a", "command_run:goal"): 1,
        ("command_run:goal", "skill_invoke:a"): 1,
    }, "command_run survives and keeps its neighbours apart (no phantom a -> a)")
    check(_grams(_command("goal") + _command("goal")) ==
          {("command_run:goal", "command_run:goal"): 1},
          "two command_run rows with the same empty id are not deduped into one")

    # 3c. A call that started and never completed is still a call.
    check(_grams(_call("a") + [_ev("b", "started", tool_use_id="tu_orphan")] + _call("a")) == {
        ("skill_invoke:a", "skill_invoke:b"): 1,
        ("skill_invoke:b", "skill_invoke:a"): 1,
    }, "an unterminated call keeps its slot (no phantom a -> a)")

    # 4. Sessions do not bleed into each other.
    check(_grams(_call("retro", session="s1") + _call("retro", session="s2")) == {},
          "no n-gram spans a session boundary")

    # 5. 3-gram window, post-filter.
    three = _call("a") + _call("b") + _call("c") + _call("d")
    check(_grams(three, 3) == {
        ("skill_invoke:a", "skill_invoke:b", "skill_invoke:c"): 1,
        ("skill_invoke:b", "skill_invoke:c", "skill_invoke:d"): 1,
    }, "3-gram window slides correctly after the filter")

    # 6. Only sequence-bearing event types with a name enter the window.
    noise = (_call("a") + [_ev("x", event="tool_use"), _ev("y", event="rule_fire"),
                           _ev("", event="skill_invoke")] + _call("a"))
    check(_grams(noise) == {("skill_invoke:a", "skill_invoke:a"): 1},
          "tool_use / rule_fire / unnamed events stay out of the window")

    print()
    if errors:
        print(f"RESULT: {len(errors)} check(s) FAILED — see above.")
        return 1
    print("OK: all 10 sequence lifecycle-pair checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
