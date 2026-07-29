#!/usr/bin/env python3
"""Regression test: add-policy §6 respects an existing index+detail split.

PR #340. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill,
so this is a static-content check — it does not execute LLM logic. It pins the
§6 clause added by #340: when the chosen landfill site already uses a thin
index + per-entry detail-file shape (e.g. a catalogue README.md -> policies/Pn.md),
add-policy must match that shape (one index row + a linked detail file) instead of
appending a new inline block, and must never invent this split on a site that
doesn't already use it. Guards against a future SKILL.md edit silently dropping
either half of that contract.

Scope (#440): the *instruction* is what must stay in §6. Naming the shape
elsewhere is expected — §3 resolves the index's link to place an entry, §8
verifies the written split — so those mentions are not leaks. And because
SKILL.md is hard-wrapped, claims are matched by phrase across whitespace, never
as contiguous substrings; a reflow must not read as a deletion.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-index-detail.py
    python3 feedback-loop/scripts/test/test-add-policy-index-detail.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / "feedback-loop" / "skills" / "add-policy" / "SKILL.md"


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


def _section_6(text: str) -> str:
    """Slice out just §6 (between the '## 6.' and '## 7.' headers)."""
    match = re.search(r"^## 6\.\s.*?(?=^## 7\.\s)", text, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# Checks — each returns (ok, message). Phrase-based on purpose: the claim is
# prose, and the test's job is "is this claim still stated", not exact wording.
#
# Every phrase is matched through `_states()`, which treats any run of
# whitespace as a word gap. A plain `in` test cannot do that job: SKILL.md is
# hard-wrapped, so reflowing a paragraph moves a line break into the middle of
# a phrase and the claim reads as deleted while it is still right there. That
# is what happened to `never invent this split` after 90a20d2.
# ---------------------------------------------------------------------------

def _states(text: str, phrase: str) -> bool:
    """True if `text` states `phrase`, ignoring how the prose happens to wrap."""
    pattern = r"\s+".join(re.escape(word) for word in phrase.split())
    return re.search(pattern, text, re.IGNORECASE) is not None


# The two phrases that carry the *instruction*. These are what must not float
# out of §6 — unlike the shape's mere name, which §3 (placement) and §8
# (post-write verification) both legitimately mention.
_INSTRUCTION_PHRASES = ("match that shape", "never invent this split")


def check_index_detail_shape_named(text: str) -> tuple[bool, str]:
    """The index+detail split shape must be named."""
    section = _section_6(text)
    if not _states(section, "index+detail split") and not _states(section, "index + detail split"):
        return False, "index+detail split shape not named in §6"
    return True, "index+detail split shape named"


def check_match_shape_instruction(text: str) -> tuple[bool, str]:
    """Must instruct matching the shape: an index row + a linked detail file, not a new inline block."""
    section = _section_6(text)
    if not _states(section, "match that shape"):
        return False, "'match that shape' instruction missing"
    if not _states(section, "index row") or not _states(section, "detail file"):
        return False, "index row + detail file pairing not described"
    if not _states(section, "inline block"):
        return False, "the inline-block alternative (what NOT to do) not named"
    return True, "match-shape instruction (index row + detail file, not inline block) present"


def check_never_invent_guard(text: str) -> tuple[bool, str]:
    """Must guard against inventing this split on a site that doesn't already use it."""
    if not _states(_section_6(text), "never invent this split"):
        return False, "'never invent this split' guard missing"
    return True, "never-invent-this-split guard present"


def check_scoped_to_section_6(text: str) -> tuple[bool, str]:
    """The §6 *instruction* must not float elsewhere (e.g. into §7's output contract).

    Naming the shape outside §6 is not a leak: §3 resolves the index's link to
    decide placement, and §8 verifies the written split (link resolves, no new
    `.md` in the loaded directory). Both are halves of the same contract, so
    only the instruction phrases are scoped here.
    """
    section = _section_6(text)
    if not section.strip():
        return False, "§6 section boundary not found (header drift?)"
    # A non-whitespace sentinel, not "": excising §6 butts §5's tail against §7's
    # head, and `_states` spans whitespace, so a section ending in "match that"
    # before one starting with "shape" would read as a leak that isn't there.
    outside_6 = text.replace(section, "\n<<§6 excised>>\n")
    for phrase in _INSTRUCTION_PHRASES:
        if _states(outside_6, phrase):
            return False, f"§6 instruction ('{phrase}') leaked outside §6"
    return True, "§6 instruction correctly scoped to §6"


_CHECKS = [
    check_index_detail_shape_named,
    check_match_shape_instruction,
    check_never_invent_guard,
    check_scoped_to_section_6,
]


def run_checks(text: str) -> tuple[int, int]:
    passed = failed = 0
    for check in _CHECKS:
        ok, msg = check(text)
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test (in-memory fixtures)
# ---------------------------------------------------------------------------

_PASSING = """\
## 6. Conflict check (target = the landfill site's current rules)

The engine does not maintain a numbered catalogue; for a new rule it appends in each
site's native form, and for an Edit-classified rule it rewrites the targeted entry in
place instead. If the chosen site's current content is already an index+detail split
(a thin summary table/list of one-liners each linking to a per-entry file, e.g. a
catalogue README.md -> policies/Pn.md), match that shape — add one terse index row
plus its linked detail file, not a new inline block — so the always-loaded index
doesn't grow unbounded as entries accumulate. Never invent this split on a site that
doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# Regression of the pre-#340 SKILL.md: §6 says nothing about index+detail sites at all.
_FAILING = """\
## 6. Conflict check (target = the landfill site's current rules)

The engine does not maintain a numbered catalogue; for a new rule it appends in each
site's native form, and for an Edit-classified rule it rewrites the targeted entry in
place instead — always conflict-checked against that site's present content.

## 7. Output contract

Some unrelated §7 content.
"""

# A clause present but leaked into §7 instead of §6 — must fail the scoping check.
_LEAKED = """\
## 6. Conflict check (target = the landfill site's current rules)

The engine does not maintain a numbered catalogue.

## 7. Output contract

If the chosen site's current content is already an index+detail split, match that
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent this split on a site that doesn't already use it.
"""

# Same claims as _PASSING, but every phrase straddles a line break. Hard-wrapped
# prose must still read as stating them — a plain substring test fails here, which
# is how 90a20d2's reflow made `never invent this split` look deleted.
_WRAPPED = """\
## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail
split, match that
shape — add one terse index
row plus its linked detail
file, not a new inline
block. Never invent
this split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# One word off in each instruction phrase ("the"/"that", "that"/"this"). The
# claims are absent, but only just — this bounds how far `_states` may be
# loosened. Widen it to `.*` or drop a word from a phrase and this fixture is
# the case that goes red; every other fixture stays green.
_NEAR_MISS = """\
## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail split, match the
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent that split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.
"""

# §3 resolves the index link for placement and §8 verifies the written split.
# Both name the shape outside §6 without carrying the instruction — not a leak.
_NAMED_OUTSIDE_6 = """\
## 3. The three landfill sites

If the site is an index+detail split, follow the index's links and read the detail
files before deciding where the new entry goes.

## 6. Conflict check (target = the landfill site's current rules)

If the chosen site's current content is already an index+detail split, match that
shape — add one terse index row plus its linked detail file, not a new inline block.
Never invent this split on a site that doesn't already use it.

## 7. Output contract

Some unrelated §7 content.

## 8. Post-write self-check

On an index+detail split, also verify the link resolves and that the loaded
directory gained no new `.md`.
"""


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    for check in (
        check_index_detail_shape_named,
        check_match_shape_instruction,
        check_never_invent_guard,
    ):
        ok, _ = check(_FAILING)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_scoped_to_section_6(_LEAKED)
    cases.append(("leaked: check_scoped_to_section_6 (expect FAIL)", not ok))

    # Regression of the two ways this suite went red on a correct SKILL.md (#440).
    for check in _CHECKS:
        ok, _ = check(_WRAPPED)
        cases.append((f"hard-wrapped: {check.__name__}", ok))

    ok, _ = check_scoped_to_section_6(_NAMED_OUTSIDE_6)
    cases.append(("shape named in §3/§8 is not a leak: check_scoped_to_section_6", ok))

    # The other edge of the same fix: `_states` spans whitespace, and nothing
    # more. A one-word-off phrase must still read as absent.
    for check in (check_match_shape_instruction, check_never_invent_guard):
        ok, _ = check(_NEAR_MISS)
        cases.append((f"near-miss: {check.__name__} (expect FAIL)", not ok))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s): {failed}")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        return _self_test()

    print(f"Checking: {_SKILL_PATH}\n")
    try:
        text = _load_skill()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    passed, failed = run_checks(text)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} add-policy-index-detail checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
