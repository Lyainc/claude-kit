#!/usr/bin/env python3
"""Regression test: add-policy §6 conflict-check has a first-class Edit bucket.

#303. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill, so this
is a static-content check — it does not execute LLM logic. It pins the claim that an
explicit "change this existing entry" request is its own conflict-check outcome
(Edit), distinct from Duplicate (strengthen) and Contradiction (refuse) — guarding
against a future edit silently collapsing Edit back into one of those two, which was
the exact gap #303 reported (an explicit edit request risked being misclassified as
Contradiction and refused, or only surfacing as a side effect of Duplicate).

The two pinned claims:

1. §6's conflict-check bullet list names "Edit" as its own outcome, distinct from
   Duplicate and Contradiction, and describes showing a before -> after diff of the
   existing entry rather than just new prose to add.
2. §3's 1-click confirmation template's 충돌 (conflict) field enumerates the edit
   outcome alongside none / sibling / contradiction, so the UX surface reflects it.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py
    python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py --self-test

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


# ---------------------------------------------------------------------------
# Checks — each returns (ok, message). Substring-based on purpose: the claim is
# prose, and the test's job is "is this claim still stated", not exact wording.
# ---------------------------------------------------------------------------

def _bullet_scope(lower: str, marker: str) -> str | None:
    """Slice `lower` from `marker` to the next top-level bullet (`\\n- **`), or
    +600 chars if there is no next bullet. None if `marker` isn't found. Scopes a
    claim check to one bullet's own text instead of the whole document, so an
    unrelated match elsewhere in the skill can't false-positive."""
    marker_pos = lower.find(marker)
    if marker_pos == -1:
        return None
    next_bullet = lower.find("\n- **", marker_pos + 1)
    return lower[marker_pos:next_bullet] if next_bullet != -1 else lower[marker_pos:marker_pos + 600]


def check_edit_bucket_named(text: str) -> tuple[bool, str]:
    """§6 must name Edit as its own conflict-check outcome, not folded into Duplicate."""
    bullet_text = _bullet_scope(text.lower(), "**edit")
    if bullet_text is None:
        return False, "Edit is not named as its own §6 conflict-check outcome"
    if "before" not in bullet_text or "after" not in bullet_text:
        return False, "Edit outcome doesn't describe a before -> after diff"
    return True, "Edit named as a distinct §6 outcome with a before -> after diff"


def check_edit_distinct_from_contradiction(text: str) -> tuple[bool, str]:
    """Contradiction must be scoped to exclude an explicit edit request."""
    bullet_text = _bullet_scope(text.lower(), "**contradiction")
    if bullet_text is None:
        return False, "Contradiction outcome missing entirely"
    if "not target" not in bullet_text and "not an explicit edit" not in bullet_text and "does not target" not in bullet_text:
        return False, (
            "Contradiction isn't scoped to exclude explicit-edit requests — an edit "
            "request could still be misclassified as a refusal"
        )
    return True, "Contradiction explicitly excludes requests that are an edit of that entry"

def check_confirmation_template_lists_edit(text: str) -> tuple[bool, str]:
    """§3's 충돌 confirmation field must enumerate the edit outcome."""
    field_pos = text.find("충돌:")
    if field_pos == -1:
        return False, "충돌 confirmation field missing from the §3 template"
    # Scope to the 충돌 field's own line, not text.split("충돌")[-1] (the whole
    # document tail from the LAST occurrence) — a second unrelated "충돌" mention
    # added anywhere later in the file would otherwise silently validate the wrong text.
    line_end = text.find("\n", field_pos)
    field_line = text[field_pos:line_end if line_end != -1 else len(text)].lower()
    if not re.search(r"\bedit", field_line):
        return False, "충돌 field doesn't enumerate the edit outcome"
    return True, "충돌 field enumerates the edit outcome"


_CHECKS = [
    check_edit_bucket_named,
    check_edit_distinct_from_contradiction,
    check_confirmation_template_lists_edit,
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
- **Duplicate**: if the site already states the same rule, strengthen that entry.
- **Edit (explicit modification of an existing entry)**: if the request clearly targets
  one existing entry and asks to change it, treat it as an in-place edit, not a new
  append. Show the entry's before → after text in the §3 confirmation.
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
- **Sibling**: link them with a one-line note.

## 분류 결과
- 충돌: <none | sibling of an existing rule | edits an existing entry (show before→after) | contradicts an existing rule (explain)>
"""

# Regression of the exact bug #303 reports: only three outcomes, an explicit edit
# request has no first-class path and risks being refused as a Contradiction.
_FAILING = """\
- **Duplicate**: if the site already states the same rule, strengthen that entry
  instead of adding a second (DRY).
- **Contradiction**: if it conflicts with an existing rule, do NOT write — report the
  contradiction to the user and stop.
- **Sibling**: if it is one half of an existing rule's pair, link them with a one-line
  "sibling to <that rule>" rather than duplicating context.

## 분류 결과
- 충돌: <none | sibling of an existing rule | contradicts an existing rule (explain)>
"""

# Regression of a narrower bug: the Edit bucket exists, but its own before -> after
# description was silently dropped, while "before"/"after" still appear elsewhere in
# the document as ordinary English (unrelated to the Edit outcome). The check must
# not be fooled by an unrelated match elsewhere in the file.
_EDIT_WITHOUT_BEFORE_AFTER = """\
Verify before writing to the target. After writing, verify the artifact deterministically.

- **Duplicate**: if the site already states the same rule, strengthen that entry.
- **Edit (explicit modification of an existing entry)**: if the request clearly targets
  one existing entry and asks to change it, treat it as an in-place edit, showing the
  entry's rewritten text in the §3 confirmation.
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
- **Sibling**: link them with a one-line note.
"""

# Regression pin for the word-boundary fix (#320): a 충돌 line containing "expedited"
# has "edit" as a mid-word substring but doesn't name the edit outcome. The old bare
# substring check ("edit" in field_line) would false-positive-pass this.
_CONFIRMATION_FIELD_SUBSTRING_FALSE_POSITIVE = """\
## 분류 결과
- 충돌: <none | sibling of an existing rule | contradicts an existing rule (expedited review)>
"""


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    for check in _CHECKS:
        ok, _ = check(_FAILING)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_edit_bucket_named(_EDIT_WITHOUT_BEFORE_AFTER)
    cases.append(("edit-without-before-after: check_edit_bucket_named (expect FAIL)", not ok))

    ok, _ = check_confirmation_template_lists_edit(_CONFIRMATION_FIELD_SUBSTRING_FALSE_POSITIVE)
    cases.append(("substring-false-positive: check_confirmation_template_lists_edit (expect FAIL)", not ok))

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
    print(f"OK: all {passed} add-policy-conflict-edit checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
