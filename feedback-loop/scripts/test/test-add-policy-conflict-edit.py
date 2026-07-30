#!/usr/bin/env python3
"""Regression test: add-policy §6 conflict-check has an Edit bucket and a Supersede exit.

#303. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill, so this
is a static-content check — it does not execute LLM logic. It pins the claim that an
explicit "change this existing entry" request is its own conflict-check outcome
(Edit), distinct from Duplicate (strengthen) and Contradiction (refuse) — guarding
against a future edit silently collapsing Edit back into one of those two, which was
the exact gap #303 reported (an explicit edit request risked being misclassified as
Contradiction and refused, or only surfacing as a side effect of Duplicate).

#429 adds the other half. Every §6 verdict left the entry count flat — Contradiction
included, since it refuses the write rather than clearing anything — so the catalogue
was monotonically increasing (local-harness: 12 policies in 39 days, 1 removed, and
that one a by-product of a manual audit). Supersede is the exit path: a new rule that
makes an existing entry redundant absorbs and retires it in the SAME write, on the same
confirmation. Pinned here because it is a §6 verdict + a §3 confirmation field, exactly
what this suite already guards.

The pinned claims:

1. §6's conflict-check bullet list names "Edit" as its own outcome, distinct from
   Duplicate and Contradiction, and describes showing a before -> after diff of the
   existing entry rather than just new prose to add.
2. §3's 1-click confirmation template's 충돌 (conflict) field enumerates the edit
   outcome alongside none / sibling / contradiction, so the UX surface reflects it.
3. §6 names "Supersede" as its own outcome, retiring the redundant entry in the same
   write, and forbids reusing a retired number.
4. That retirement rides on the same single confirmation — never a second prompt.
5. §3's confirmation template carries the 은퇴 (retirement) field.

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

# The §6 verdict bullets, and nothing else. §8's post-write self-check now carries its own
# `- **Supersede**:` bullet, so a marker search over the whole document would silently retarget
# there if §6's bullet were deleted — reporting "doesn't retire in the same write" for a verdict
# that is missing outright. Fixtures are bare bullet fragments with no headers, so a document
# without the header pair falls back to itself.
_SECTION_6_RE = re.compile(r"^## 6\.\s.*?(?=^## 7\.\s)", re.MULTILINE | re.DOTALL)


def _verdict_scope(text: str) -> str:
    match = _SECTION_6_RE.search(text)
    return match.group(0) if match else text


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
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**edit")
    if bullet_text is None:
        return False, "Edit is not named as its own §6 conflict-check outcome"
    if "before" not in bullet_text or "after" not in bullet_text:
        return False, "Edit outcome doesn't describe a before -> after diff"
    return True, "Edit named as a distinct §6 outcome with a before -> after diff"


def check_edit_distinct_from_contradiction(text: str) -> tuple[bool, str]:
    """Contradiction must be scoped to exclude an explicit edit request."""
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**contradiction")
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


# NEGATED polarity, not mere presence of the words. A bullet reading "ask the user to approve
# the retirement in a separate prompt of its own" contains "separate prompt" and states the exact
# design #429 rejects; a presence check passes it. `\s+` between the words because SKILL.md is
# hard-wrapped — "never as a separate\n  prompt" is one phrase, not a deletion.
_NO_EXTRA_PROMPT_RE = re.compile(
    r"\b(?:never|no|without)\s+(?:as\s+)?(?:a\s+)?(?:separate|second)\s+prompt\b",
    re.IGNORECASE,
)


def check_supersede_verdict_named(text: str) -> tuple[bool, str]:
    """#429: §6 must name Supersede as its own outcome, retiring the entry in the same write."""
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**supersede")
    if bullet_text is None:
        return False, "Supersede is not named as its own §6 conflict-check outcome"
    if "retire" not in bullet_text:
        return False, "Supersede outcome doesn't retire the superseded entry"
    if "same write" not in bullet_text:
        return False, (
            "Supersede doesn't retire in the SAME write — a deferred retirement is how the "
            "catalogue ends up carrying both entries"
        )
    if "never reused" not in bullet_text and "never be reused" not in bullet_text:
        return False, "the retired-number-is-never-reused rule is missing"
    return True, "Supersede named as a distinct §6 outcome, retiring in the same write"


def check_supersede_rides_one_confirmation(text: str) -> tuple[bool, str]:
    """#429: the retirement must ride on the existing confirmation, never a second prompt."""
    bullet_text = _bullet_scope(_verdict_scope(text).lower(), "**supersede")
    if bullet_text is None:
        return False, "Supersede outcome missing entirely"
    if not _NO_EXTRA_PROMPT_RE.search(bullet_text):
        return False, (
            "Supersede doesn't state that the retirement rides on the same confirmation — "
            "the 1-click invariant the rest of the skill holds"
        )
    return True, "Supersede retirement rides on the same 1-click confirmation"


def check_confirmation_template_lists_retirement(text: str) -> tuple[bool, str]:
    """#429: §3's confirmation template must carry the 은퇴 field."""
    field_pos = text.find("은퇴:")
    if field_pos == -1:
        return False, "은퇴 confirmation field missing from the §3 template"
    # Same line-scoping as the 충돌 check: a later unrelated 은퇴 mention must not
    # validate the wrong text.
    line_end = text.find("\n", field_pos)
    field_line = text[field_pos:line_end if line_end != -1 else len(text)]
    if "none" not in field_line.lower():
        return False, "은퇴 field doesn't offer the no-retirement case"
    return True, "은퇴 field present in the §3 confirmation template"


_CHECKS = [
    check_edit_bucket_named,
    check_edit_distinct_from_contradiction,
    check_confirmation_template_lists_edit,
    check_supersede_verdict_named,
    check_supersede_rides_one_confirmation,
    check_confirmation_template_lists_retirement,
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
- **Supersede (the catalogue's exit path)**: if landing this rule makes an existing entry
  redundant, do not add a second entry. Absorb the old entry's distinguishing content into
  the new one and retire it **in the same write**, shown in the §3 confirmation as part of
  the diff, never as a separate prompt. **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
- **Sibling**: link them with a one-line note.

## 분류 결과
- 충돌: <none | sibling of an existing rule | edits an existing entry (show before→after) | contradicts an existing rule (explain)>
- 은퇴: <none | Pn이 이 규칙에 흡수돼요 — 같은 쓰기에서 은퇴시킬게요>
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


# Supersede exists but defers the retirement to its own confirmation — the design #429
# explicitly rejects, because a second prompt is where a retirement gets skipped.
_SUPERSEDE_SECOND_PROMPT = """\
- **Supersede**: if landing this rule makes an existing entry redundant, absorb it and retire
  the old entry **in the same write**. Ask the user to confirm the retirement separately.
  **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""

# Supersede that only marks the old entry for later removal. The catalogue carries both
# until someone comes back, which is the monotonic growth #429 measured.
_SUPERSEDE_DEFERRED_WRITE = """\
- **Supersede**: if landing this rule makes an existing entry redundant, note that the old
  entry should be retired, never as a separate prompt. **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""


# The keywords are all present, but the claim is inverted: the retirement gets its own prompt.
# This is the mutation a presence-only check passes, which is what made the check vacuous.
_SUPERSEDE_INVERTED = """\
- **Supersede**: if landing this rule makes an existing entry redundant, absorb it and retire
  the old entry **in the same write**, shown in the §3 confirmation as part of the diff, and
  then ask the user to approve the retirement in a separate prompt of its own.
  **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
"""

# The phrase straddles a line break, exactly as it does in the hard-wrapped SKILL.md. A plain
# substring check reads this as deleted (#440); it must read as stated.
_SUPERSEDE_WRAPPED = """\
- **Supersede**: if landing this rule makes an existing entry redundant, absorb it and retire
  the old entry **in the same write** — never as a separate
  prompt. **A retired number is never reused.**
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.
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

    ok, _ = check_supersede_rides_one_confirmation(_SUPERSEDE_SECOND_PROMPT)
    cases.append(("supersede-second-prompt: check_supersede_rides_one_confirmation (expect FAIL)", not ok))
    ok, _ = check_supersede_verdict_named(_SUPERSEDE_SECOND_PROMPT)
    cases.append(("supersede-second-prompt: check_supersede_verdict_named (still OK)", ok))

    ok, _ = check_supersede_verdict_named(_SUPERSEDE_DEFERRED_WRITE)
    cases.append(("supersede-deferred-write: check_supersede_verdict_named (expect FAIL)", not ok))

    ok, _ = check_supersede_rides_one_confirmation(_SUPERSEDE_INVERTED)
    cases.append(("supersede-inverted: check_supersede_rides_one_confirmation (expect FAIL)", not ok))
    ok, _ = check_supersede_rides_one_confirmation(_SUPERSEDE_WRAPPED)
    cases.append(("supersede-wrapped: check_supersede_rides_one_confirmation (still OK)", ok))

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
