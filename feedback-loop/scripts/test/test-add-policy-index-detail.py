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
# Checks — each returns (ok, message). Substring-based on purpose: the claim is
# prose, and the test's job is "is this claim still stated", not exact wording.
# ---------------------------------------------------------------------------

def check_index_detail_shape_named(text: str) -> tuple[bool, str]:
    """The index+detail split shape must be named."""
    lower = _section_6(text).lower()
    if "index+detail split" not in lower and "index + detail split" not in lower:
        return False, "index+detail split shape not named in §6"
    return True, "index+detail split shape named"


def check_match_shape_instruction(text: str) -> tuple[bool, str]:
    """Must instruct matching the shape: an index row + a linked detail file, not a new inline block."""
    lower = _section_6(text).lower()
    if "match that shape" not in lower:
        return False, "'match that shape' instruction missing"
    if "index row" not in lower or "detail file" not in lower:
        return False, "index row + detail file pairing not described"
    if "inline block" not in lower:
        return False, "the inline-block alternative (what NOT to do) not named"
    return True, "match-shape instruction (index row + detail file, not inline block) present"

def check_never_invent_guard(text: str) -> tuple[bool, str]:
    """Must guard against inventing this split on a site that doesn't already use it."""
    lower = _section_6(text).lower()
    if "never invent this split" not in lower:
        return False, "'never invent this split' guard missing"
    return True, "never-invent-this-split guard present"


def check_scoped_to_section_6(text: str) -> tuple[bool, str]:
    """The whole clause must live inside §6, not floated elsewhere (e.g. §7 output contract)."""
    if not _section_6(text).strip():
        return False, "§6 section boundary not found (header drift?)"
    outside_6 = text.replace(_section_6(text), "")
    if "index+detail split" in outside_6.lower() or "never invent this split" in outside_6.lower():
        return False, "index+detail clause leaked outside §6"
    return True, "index+detail clause correctly scoped to §6"


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
