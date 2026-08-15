#!/usr/bin/env python3
"""check-agent-nonresponse-clause.py — Agent-delegating skills must state the no-response
fallback (#647).

RULE: every file in FILES below spawns a subagent via `Agent` and then WAITS on its report,
so each one must carry the no-response clause verbatim:

    only idle notifications and no final text after one re-request

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

FILES = [
    "thinking-tools/skills/build-spec/SKILL.md",
    "thinking-tools/skills/build-spec/reference.md",
    "thinking-tools/skills/doc-concretize/SKILL.md",
    "thinking-tools/skills/unknown-discovery/SKILL.md",
    "thinking-tools/skills/adversarial-review/SKILL.md",
    "thinking-tools/skills/expert-panel/SKILL.md",
]


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def has_clause(text):
    """True if the file states the no-response fallback.

    Newline-insensitive: the clause is prose and gets re-wrapped by editors, so the
    comparison runs over whitespace-collapsed text.
    """
    return CLAUSE in " ".join(text.split())


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
            if not has_clause(fh.read()):
                missing.append(rel)

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
