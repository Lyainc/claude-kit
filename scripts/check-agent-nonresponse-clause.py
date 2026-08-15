#!/usr/bin/env python3
"""check-agent-nonresponse-clause.py — Agent-delegating skills must state the no-response
fallback (#647).

RULE: every file in FILES below spawns a subagent via `Agent` and then WAITS on its report,
so each such site must carry the no-response clause verbatim:

    only idle notifications and no final text after one re-request

FILES maps each file to how many of those sites it has, and the clause is COUNTED, not merely
looked for — build-spec waits at two sites and adversarial-review at three, so a file-level
check would stay green after one of them quietly lost its fallback.

Why a content assertion and not detection code: on 2026-08-15 three spawned subagents stayed
alive, emitted only `idle_notification` events, and never returned a final report — no error,
no timeout, no policy denial. Every documented fallback in these skills keyed on "the call
fails" or "policy blocks it", so a live-but-silent agent matched no condition and a human had
to notice. That is a SINGLE observation (#647), which is why nothing here tries to *detect*
the mode: the fix is one documented rule (one re-request, then treat as unavailable and take
the existing inline fallback), and this guard only keeps that rule from being edited away.

The file list is deliberately explicit and hand-maintained — there is no discovery heuristic.
A skill that starts delegating to `Agent` and waiting on the reply gets added here by hand,
the same way its fallback paragraph is written by hand.

Usage:
    python3 scripts/check-agent-nonresponse-clause.py [--root DIR] [--json] [--self-test]

    --root DIR    Repo root to check (default: git toplevel, else CWD).
    --json        Emit a machine-readable JSON report instead of text.
    --self-test   Validate the clause matcher in-memory and exit 0 only if every case
                  is detected as expected.

Exit codes: 0 = every listed file carries the clause (or --self-test passed),
            1 = at least one file is missing it, 2 = a listed file does not exist.
"""
import argparse
import json
import os
import subprocess
import sys

CLAUSE = "only idle notifications and no final text after one re-request"

# rel path -> how many Agent-wait sites in that file carry the clause. Counted, not just
# looked for once: build-spec waits twice (Phase 2 gate, Phase 2.5 blind-spot) and
# adversarial-review three times (vault grounding, Judge, 자동 방어 Defender), so a
# file-level "is it in here somewhere" check passes while one site loses its fallback.
FILES = {
    "thinking-tools/skills/build-spec/SKILL.md": 2,
    "thinking-tools/skills/build-spec/reference.md": 1,
    "thinking-tools/skills/doc-concretize/SKILL.md": 1,
    "thinking-tools/skills/unknown-discovery/SKILL.md": 1,
    "thinking-tools/skills/adversarial-review/SKILL.md": 3,
    "thinking-tools/skills/expert-panel/SKILL.md": 1,
    "thinking-tools/skills/expert-panel/reference.md": 1,
}


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def count_clause(text):
    """How many times the file states the no-response fallback.

    Newline-insensitive: the clause is prose and gets re-wrapped by editors, so the
    comparison runs over whitespace-collapsed text.
    """
    return " ".join(text.split()).count(CLAUSE)


def has_clause(text):
    return count_clause(text) > 0


def run_self_test():
    cases = [
        ("A subagent that returns only idle notifications and no final text after one "
         "re-request counts as unavailable.", True),
        # Re-wrapped across lines — still the same sentence.
        ("...returns only idle notifications and no final\ntext after one re-request...", True),
        # The pre-#647 wording: failure only, no no-response condition.
        ("**Agent call fails / unavailable** -> score inline against the same checklist.", False),
        ("The agent sent idle notifications.", False),
        ("", False),
    ]
    failures = [(t[:40], has_clause(t), want) for t, want in cases if has_clause(t) != want]
    # Per-site counting: a file whose two delegation sites each carry the clause must read
    # as 2, so deleting one drops it below its FILES entry instead of still passing.
    two_sites = cases[0][0] + " ...unrelated prose... " + cases[0][0]
    if count_clause(two_sites) != 2:
        failures.append(("two-site count", count_clause(two_sites), 2))
    if failures:
        print("FAIL: check-agent-nonresponse-clause self-test")
        for snippet, got, want in failures:
            print(f"  {snippet!r}: got {got}, want {want}")
        return 1
    print("OK: all check-agent-nonresponse-clause self-test cases passed")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    root = args.root or _git_toplevel() or os.getcwd()
    missing, absent = [], []
    for rel in FILES:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            absent.append(rel)
            continue
        with open(path, encoding="utf-8") as fh:
            found = count_clause(fh.read())
        if found < FILES[rel]:
            missing.append(f"{rel} ({found} of {FILES[rel]} site(s))")

    if args.json:
        print(json.dumps(
            {"checked": len(FILES), "missing_clause": missing, "not_found": absent}, indent=2))
    else:
        if absent:
            print("ERROR: listed file(s) not found — update FILES in this script:",
                  file=sys.stderr)
            for rel in absent:
                print(f"  {rel}", file=sys.stderr)
        if missing:
            print(f"FAIL: file(s) missing the #647 no-response fallback clause ({CLAUSE!r}):")
            for rel in missing:
                print(f"  {rel}")
        if not absent and not missing:
            print(f"OK: all {len(FILES)} Agent-delegating file(s) state the no-response fallback")

    if absent:
        return 2
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
