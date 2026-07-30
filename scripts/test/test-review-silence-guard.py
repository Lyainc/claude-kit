#!/usr/bin/env python3
"""Regression test: the CI review job cannot pass while having said nothing (#451).

`.github/workflows/claude-code-review.yml` only ever ASKED for a review comment. A run
that posted none finished green, so from the Checks tab "reviewed, found nothing" and
"never actually reviewed" were the same tick — the silent-guard-off failure class of
#447/#454/#456. The fix is a verify step that counts this round's comments and fails at
zero; this file pins it, because a deleted step leaves no other trace.

Two halves, matching what can actually break:

1. EXECUTED. The counting is a jq filter, and its subtle part is `select(.createdAt >
   env.SINCE)`. Drop that clause and the guard still looks right while passing every
   `synchronize` re-run as soon as round 1 left a comment behind — silence goes
   undetected exactly where it is hardest to notice. So the filter is EXTRACTED from the
   workflow and RUN through real `jq` over fixtures, including a prior-round comment that
   must NOT satisfy the current round.
2. STATIC. The step exists, runs `if: always()` (a review that died mid-run is the case
   that must not be laundered into a pass), and exits nonzero at zero comments. Plus the
   paired prompt clause — the prompt must REQUIRE a comment even on a clean review, or
   the workflow half turns every clean PR red — and the `paths:` filter must stay out
   (a required check skipped by a path filter reports no status and pends forever).
   Two more conditions the round-scoping rests on, both found by review of this file's
   first version: an EMPTY `SINCE` must fail rather than widen the filter to "any claude
   comment ever" (jq's `>` holds against "" for every timestamp, and the `echo "at=$(date
   ...)"` that produces it exits 0 even when date does not), and the workflow must hold a
   `concurrency:` group — two overlapping runs on one PR give the later one a window that
   predates the earlier one's comment, so it can pass on a sibling's review.

jq is a hard dependency here, not an optional nicety: no jq means the executed half
cannot run, and a check that skips itself is the very thing this file exists to catch,
so that exits 2 rather than reporting a pass.

Usage:
    python3 scripts/test/test-review-silence-guard.py
    python3 scripts/test/test-review-silence-guard.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
    2  jq unavailable, or the workflow/filter could not be read (no verdict reported)
"""
import json
import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_WORKFLOW = os.path.join(_ROOT, ".github", "workflows", "claude-code-review.yml")

# The verify step's own `--jq '...'`. Anchored on `gh pr view` + `--json comments` so it
# cannot latch onto some other gh call the workflow may grow later.
_JQ_RE = re.compile(r"gh pr view[^\n]*--json comments[^\n]*--jq\s+'([^']+)'")

_SINCE = "2026-07-31T00:00:00Z"


def extract_jq_filter(text):
    """Return the comment-counting jq filter from the workflow, or None."""
    m = _JQ_RE.search(text)
    return m.group(1) if m else None


def count_with_jq(jq_filter, comments, since=_SINCE):
    """Run the workflow's own filter over a fixture comment list; return its number."""
    payload = json.dumps({"comments": comments})
    out = subprocess.run(
        ["jq", jq_filter],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "SINCE": since},
    )
    if out.returncode != 0:
        raise RuntimeError(f"jq failed on the extracted filter: {out.stderr.strip()}")
    return int(out.stdout.strip())


def _comment(login, created_at):
    return {"author": {"login": login}, "createdAt": created_at}


# (label, comments, expected count). The pass cases and the silent cases both matter:
# a filter that counts everything never fails, one that counts nothing always does.
_FIXTURES = [
    ("this round's claude comment counts", [_comment("claude", "2026-07-31T00:05:00Z")], 1),
    ("no comments at all is silence", [], 0),
    (
        "a PRIOR round's comment does not satisfy this round",
        [_comment("claude", "2026-07-30T23:00:00Z")],
        0,
    ),
    (
        "a prior comment plus a fresh one still counts the fresh one",
        [_comment("claude", "2026-07-30T23:00:00Z"), _comment("claude", "2026-07-31T00:05:00Z")],
        1,
    ),
    (
        "a human comment in the window is not a review comment",
        [_comment("Lyainc", "2026-07-31T00:05:00Z")],
        0,
    ),
    (
        "the login match is case-insensitive (claude[bot], Claude)",
        [_comment("Claude[bot]", "2026-07-31T00:05:00Z")],
        1,
    ),
]


def run_checks(text):
    """Return (passed, failed) over the extracted filter + the static contract."""
    cases = []

    jq_filter = extract_jq_filter(text)
    cases.append(("verify step counts comments via `gh pr view --json comments --jq`", jq_filter is not None))
    if jq_filter:
        for label, comments, expected in _FIXTURES:
            try:
                got = count_with_jq(jq_filter, comments)
                ok = got == expected
                label = f"{label} (expected {expected}, got {got})"
            except RuntimeError as exc:
                ok, label = False, f"{label} — {exc}"
            cases.append((label, ok))

    cases.extend([
        ("the verify step exists by name",
         "Verify a review comment was posted (no silent pass)" in text),
        # `if: always()` — without it a failed review step skips the check that would have
        # reported WHY the job is red, and a cancelled one skips it silently.
        ("the verify step runs `if: always()`",
         bool(re.search(r"Verify a review comment was posted[^\n]*\n\s*if:\s*always\(\)", text))),
        ("zero comments exits nonzero", bool(re.search(r'\[ "\$count" -lt 1 \]', text))
         and "exit 1" in text.split("Verify a review comment was posted")[-1]),
        ("the failure is annotated for the Checks tab", "::error::" in text),
        # The window the count is measured against must be captured BEFORE the review,
        # or `env.SINCE` in the filter resolves to nothing and every re-run passes.
        ("the review-start timestamp is recorded before the review runs",
         text.index("id: review_start") < text.index("id: claude-review")),
        ("the verify step reads that timestamp", "SINCE: ${{ steps.review_start.outputs.at }}" in text),
        # An empty SINCE widens the filter to "any claude comment ever" instead of failing:
        # jq's `>` holds against "" for every timestamp, and the `echo "at=$(date ...)"` that
        # produces it exits 0 even when date does not.
        ("an empty timestamp fails instead of widening the window",
         bool(re.search(r'if \[ -z "\$SINCE" \]; then', text))),
        # Round-scoping assumes rounds are sequential. Two overlapping runs break that: the
        # later one's window predates the earlier one's comment, so it can count a sibling's.
        ("only one review run per PR at a time",
         bool(re.search(r"^concurrency:\n\s+group: claude-review-", text, re.MULTILINE))),
        # The workflow half is only enforceable because the prompt half requires a comment
        # on a clean review too. Ship one without the other and every clean PR goes red.
        ("the prompt forbids silence", "Silence is not a review" in text),
        ("the prompt requires a comment even when nothing was found",
         "P0/P1 없음 — LGTM" in text),
        # A required check skipped by a path filter never reports, so the PR pends forever.
        # `paths-ignore:` skips it the same way, so both spellings are rejected.
        ("no active `paths:`/`paths-ignore:` filter on the trigger",
         not re.search(r"^\s{4}paths(-ignore)?:", text, re.MULTILINE)),
    ])

    for label, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    failed = sum(1 for _, ok in cases if not ok)
    return len(cases) - failed, failed


_GOOD_SNIPPET = """
      - name: Verify a review comment was posted (no silent pass)
        if: always()
        run: |
          count=$(gh pr view "$PR" --json comments --jq '[.comments[] | select(.author.login | test("claude"; "i")) | select(.createdAt > env.SINCE)] | length')
"""


def _self_test():
    """In-memory: the extractor finds the filter, misses when it is gone, and the
    fixtures actually discriminate — a filter without the time clause must FAIL them."""
    cases = []

    cases.append(("extractor finds the filter", extract_jq_filter(_GOOD_SNIPPET) is not None))
    cases.append(("extractor returns None when the step is absent",
                  extract_jq_filter("- name: something else\n") is None))
    cases.append(("extractor ignores an unrelated gh call",
                  extract_jq_filter("gh pr view 1 --json title --jq '.title'\n") is None))

    good = extract_jq_filter(_GOOD_SNIPPET)
    cases.append(("the good filter passes every fixture",
                  all(count_with_jq(good, c) == e for _, c, e in _FIXTURES)))

    # The point of the fixtures: a filter that dropped the createdAt clause must be caught.
    no_time = '[.comments[] | select(.author.login | test("claude"; "i"))] | length'
    cases.append(("a filter without the createdAt clause FAILS the prior-round fixture",
                  any(count_with_jq(no_time, c) != e for _, c, e in _FIXTURES)))
    # ...and one that ignores the author must be caught too.
    no_author = "[.comments[] | select(.createdAt > env.SINCE)] | length"
    cases.append(("a filter without the author clause FAILS the human-comment fixture",
                  any(count_with_jq(no_author, c) != e for _, c, e in _FIXTURES)))

    for label, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    failed = [label for label, ok in cases if not ok]
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s): {failed}")
        return 1
    print(f"\nOK: all {len(cases)} review-silence-guard self-test cases passed")
    return 0


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if shutil.which("jq") is None:
        print(
            "FATAL: jq is unavailable, so the extracted filter cannot be executed and this\n"
            "  check will not report a verdict. Install jq (it is preinstalled on GitHub's\n"
            "  ubuntu runners) and re-run — skipping is the failure this file guards against.",
            file=sys.stderr,
        )
        return 2

    if argv and argv[0] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        return _self_test()

    print(f"Checking: {_WORKFLOW}\n")
    try:
        with open(_WORKFLOW, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"FATAL: cannot read the review workflow: {exc}", file=sys.stderr)
        return 2

    passed, failed = run_checks(text)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} review-silence-guard checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
