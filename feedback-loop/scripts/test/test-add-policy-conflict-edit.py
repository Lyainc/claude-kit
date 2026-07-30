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

KNOWN GAP (measured, not assumed). Three regions of §6 are pinned verbatim across this suite
and test-add-policy-necessity-gate.py — the preamble, the Supersede verdict, and the gate block
— covering 2,871 of §6's 7,492 characters. The rest is the Duplicate/Edit/Contradiction/Sibling
bullets and the memory-scan subsection, which test-add-policy-routing.py phrase-pins because it
changes. A contradicting clause placed there passes every suite. Closing it means pinning all of
§6, which would put the `awk` snippet under the same paired-commit rule as the contract text and
collide with routing's phrase pins. Two lines that assert the 1-click invariant outside every
pin — SKILL.md's memory-removal bullet and its `## Rules` summary — are unguarded for the same
reason. Recorded so the coverage is a decision, not an assumption.

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


def _bullet_slice(text: str, marker: str) -> str | None:
    """Same slice as `_bullet_scope`, on the ORIGINAL text — the verbatim pin needs the case
    and punctuation intact, which the lower-cased scope throws away."""
    start = text.find(marker)
    if start == -1:
        return None
    nxt = text.find("\n- **", start + 1)
    return text[start:nxt] if nxt != -1 else text[start:]


def _normalise(text: str) -> str:
    """Collapse every run of whitespace, so a reflow reads as no change (#440)."""
    return " ".join(text.split())


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


# §6's PREAMBLE, pinned verbatim. Everything an engine reads before the verdict bullets — and
# therefore the cheapest place for a contradiction to land and the first place it takes effect.
# Review demonstrated it: "A verdict that *removes* an entry is destructive, so it is confirmed
# on its own second question, separately from the §3 addition", three lines above the Supersede
# bullet, passed every suite while granting the second prompt the bullet forbids. A pin only
# covers what it spans, so the span now includes the text above the bullets. The memory-scan
# mechanics further down §6 stay unpinned — test-add-policy-routing.py phrase-pins those.
_PREAMBLE_CONTRACT = """\
## 6. Conflict check (target = the landfill site's current rules + native auto-memory)

**New site**: check the target **exists** first (`[ -f "$TARGET" ]`, the principle §5 uses for
the skill site). Never infer "missing" from a read *error* — that skips the check and
**overwrites existing content**. Absent → **`Write`**, not append; exists but unreadable → stop
and report. ([reference.md](reference.md) §6-new-site)

Otherwise read the **current contents of the chosen site** first (read-only `Bash`/`Grep`):
that channel's own rules, or the existing hook matchers and guard scripts (so a new guard
doesn't fire on an event one already covers), or existing skills.
**If the site is an index+detail split, follow the index's links and read the detail files
too** — they may sit outside the indexed directory (§3), so scanning that directory alone
silently downgrades the check to a title comparison:
"""


# Any top-level bullet, not `- **Duplicate` specifically. What this fixes is FALSE FAILURES on
# benign refactors: renaming the first verdict to something that doesn't start with "Duplicate"
# (`- **Same rule**:`) or reordering the list so Edit comes first both made the old boundary
# miss and red CI. Naming one verdict in the boundary coupled the pin to a label that is free
# to change.
#
# It does NOT close the bullet-shaped decoy: a line beginning `- **` planted right after the
# pinned text ends the slice exactly where the old boundary did, `head` still equals the
# contract, and the check still passes. That case is the documented ceiling — see the KNOWN GAP
# block in the module docstring and the `ponytail:` note on `_PREAMBLE_DECOY_BULLET`. Anything
# below the first top-level bullet is outside this pin, by construction.
_FIRST_BULLET_RE = re.compile(r"^- \*\*", re.MULTILINE)


def check_conflict_preamble_verbatim(text: str) -> tuple[bool, str]:
    """§6's opening, up to the first verdict bullet, matches its pinned contract text."""
    if _SECTION_6_RE.search(text) is None:
        return False, "§6 section boundary not found (header drift?)"
    section = _verdict_scope(text)
    match = _FIRST_BULLET_RE.search(section)
    if match is None:
        return False, "§6 has no verdict bullets — the outcome list is missing"
    head, contract = _normalise(section[:match.start()]), _normalise(_PREAMBLE_CONTRACT)
    if head != contract:
        # Prefix-vs-equality split so the message says WHICH way it drifted: text inserted
        # between the pinned preamble and the bullets is not the same defect as an edit inside
        # the preamble, and only the second means the constant is out of date.
        # No attempt to say WHICH way it drifted. A clause inserted under the `## 6.` heading
        # and one inserted before the bullets both break contiguity without the contract
        # surviving as a substring, so any such branch guesses — and a wrong guess sends the
        # author to edit the wrong file. The message names both repairs instead.
        return False, (
            "§6's preamble no longer matches its pinned contract text — something above the "
            "first verdict bullet was added, removed or reworded, and that region is what an "
            "engine reads before any verdict. If the wording change is intended, update "
            "_PREAMBLE_CONTRACT in this file; if text was inserted, put it below the pinned "
            "region instead"
        )
    return True, "§6 preamble matches its pinned contract text verbatim"


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


# The retirement clause is pinned VERBATIM, not by pattern. Two review rounds showed why: a
# presence check passed "...ask the user to approve the retirement in a separate prompt of its
# own", and adding a negation pattern then passed "the absorption itself is never a separate
# prompt. The retirement, being destructive, gets its own confirmation question afterwards" —
# #429's rejected design restated, with the negation scoped to the wrong noun. Every pattern is
# a blocklist of the last wording someone tried, and the claim it guards is universal, so the
# contract text itself is the pin. Whitespace is normalised, so a reflow is not a change; an
# added, removed or reworded clause is, and updating this constant is then the deliberate act
# of changing the contract.
#
# ponytail: the ceiling is the bullet boundary — this pins what the verdict says and that
# nothing sits beside it, not what the rest of the skill says about it.
_SUPERSEDE_CONTRACT = """\
- **Supersede (the catalogue's exit path)**: if landing this rule makes an existing entry
  redundant — the new rule states the same obligation at a more general altitude, or the old
  entry's only remaining job is now done by a guard/skill that landed since — do not add a
  second entry. Absorb the old entry's distinguishing content **into the new one** and retire
  the old **in the same write**, so the catalogue never carries both. Show the retirement in the
  §3 confirmation as part of the diff (`Pn retired, absorbed into Pm`) — **never as a separate
  prompt**. **A retired number is never reused.** If the old entry says the same thing at the
  *same* altitude this is a Duplicate instead (strengthen it, add nothing); Supersede needs the
  old entry to have stopped earning its own line.
"""


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


def check_supersede_bullet_verbatim(text: str) -> tuple[bool, str]:
    """#429: the whole Supersede verdict matches its pinned contract text.

    This is what carries the 1-click invariant — the retirement never gets a prompt of its
    own — against a contradicting clause added *beside* the negation, which is how both
    pattern-based versions of this check were defeated.
    """
    bullet = _bullet_slice(_verdict_scope(text), "- **Supersede")
    if bullet is None:
        return False, "Supersede outcome missing entirely"
    if _normalise(bullet) != _normalise(_SUPERSEDE_CONTRACT):
        return False, (
            "the §6 Supersede verdict no longer matches its pinned contract text — a clause was "
            "added, removed or reworded. If that is intended, update _SUPERSEDE_CONTRACT in this "
            "file in the same commit"
        )
    return True, "Supersede verdict matches its pinned contract text verbatim"


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
    check_conflict_preamble_verbatim,
    check_edit_bucket_named,
    check_edit_distinct_from_contradiction,
    check_confirmation_template_lists_edit,
    check_supersede_verdict_named,
    check_supersede_bullet_verbatim,
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
  redundant — the new rule states the same obligation at a more general altitude, or the old
  entry's only remaining job is now done by a guard/skill that landed since — do not add a
  second entry. Absorb the old entry's distinguishing content **into the new one** and retire
  the old **in the same write**, so the catalogue never carries both. Show the retirement in the
  §3 confirmation as part of the diff (`Pn retired, absorbed into Pm`) — **never as a separate
  prompt**. **A retired number is never reused.** If the old entry says the same thing at the
  *same* altitude this is a Duplicate instead (strengthen it, add nothing); Supersede needs the
  old entry to have stopped earning its own line.
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


# The mutation that defeated the negation pattern: the negation is scoped to the absorption,
# and the retirement gets its own confirmation anyway. Every keyword and a real negation are
# present; only the verbatim pin sees it.
_SUPERSEDE_NEGATION_MISPLACED = _SUPERSEDE_CONTRACT.replace(
    "— **never as a separate\n  prompt**.",
    """— the absorption itself is
  never a separate prompt. The retirement, being destructive, gets its own confirmation
  question afterwards, and the engine waits for that second answer before deleting anything.""",
)

# The same contract with every line break moved. Whitespace is not the contract (#440), so this
# must still read as unchanged — the case that keeps the pin from failing on a pure reflow.
_SUPERSEDE_REFLOWED = " ".join(_SUPERSEDE_CONTRACT.split())


# Every fixture above is a bare bullet fragment, so all of them take `_verdict_scope`'s
# fallback branch and the SCOPED branch — the round-2 fix for §8's own `- **Supersede**:`
# bullet — was exercised only in real mode, where it always succeeds. These two carry the
# headers, so the slice itself is tested here rather than by a sibling file's heading check.
_SECTION_HEADERS = """\
## 6. Conflict check

%s
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit, do NOT write — report and stop.

## 7. Output contract

## 8. Post-write self-check

- **Supersede**: the retired entry is gone from the index and no inbound link points at it.

## 분류 결과
- 충돌: <none | edits an existing entry (before→after)>
- 은퇴: <none | Pn이 이 규칙에 흡수돼요>
"""

# §6 holds the real verdict; §8's decoy sits after it. The scoped slice must read §6's.
_SCOPED_OK = _SECTION_HEADERS % (_SUPERSEDE_CONTRACT + "\n")

# §6's verdict deleted, §8's decoy left in place. Without scoping the marker search retargets
# to §8 and the suite reports the wrong defect (or, worse, a near-miss it can rationalise).
_SCOPED_VERDICT_DELETED = _SECTION_HEADERS % ""

assert _SCOPED_OK != _SCOPED_VERDICT_DELETED, "scoped fixtures collapsed to the same text"


_PREAMBLE_OK = (
    _PREAMBLE_CONTRACT
    + "\n- **Duplicate**: if the site already states the same rule, strengthen that entry.\n"
    + _SUPERSEDE_CONTRACT
    + "\n\n## 7. Output contract\n"
)
# Review's round-3 mutation, verbatim: a second question granted above the bullets.
_PREAMBLE_CONTRADICTED = _PREAMBLE_OK.replace(
    "Otherwise read the",
    "A verdict that *removes* an entry is destructive, so it is confirmed on its own second\n"
    "question, separately from the §3 addition.\n\nOtherwise read the",
)
_PREAMBLE_REFLOWED = _PREAMBLE_OK.replace(
    _PREAMBLE_CONTRACT, " ".join(_PREAMBLE_CONTRACT.split())
)
# A clause slipped between the pinned preamble and the first bullet — the region a
# content-addressed end boundary used to surrender whenever anything bullet-shaped appeared
# above the real list. The contract-derived boundary must red it, and say WHERE it drifted.
#
# ponytail: a decoy that is itself a top-level bullet lands BELOW this boundary, in the
# unpinned verdict-list region, and passes. That is the documented ceiling (see the module
# docstring), not something this boundary can close — pinning it means pinning all of §6.
_PREAMBLE_DECOY_BULLET = _PREAMBLE_OK.replace(
    "- **Duplicate**:",
    "A verdict that *removes* an entry is confirmed on its own second question.\n\n"
    "- **Duplicate**:",
)
# The benign refactor with the same effect: the first bullet is renamed, not moved.
_PREAMBLE_SPLIT_BULLET = _PREAMBLE_OK.replace(
    "- **Duplicate**:", "- **Duplicate (same rule)**:"
)
# The other insertion point: directly under the `## 6.` heading, above the contract's first
# paragraph. Also an insertion, and it must not be reported as a stale constant.
_PREAMBLE_PREPENDED = _PREAMBLE_OK.replace(
    "**New site**:",
    "A verdict that *removes* an entry is confirmed on its own second question.\n\n"
    "**New site**:",
)
assert _PREAMBLE_PREPENDED != _PREAMBLE_OK, "_PREAMBLE_PREPENDED no-opped"
assert _PREAMBLE_DECOY_BULLET != _PREAMBLE_OK, "_PREAMBLE_DECOY_BULLET no-opped"
assert _PREAMBLE_SPLIT_BULLET != _PREAMBLE_OK, "_PREAMBLE_SPLIT_BULLET no-opped"
assert _PREAMBLE_CONTRADICTED != _PREAMBLE_OK, "_PREAMBLE_CONTRADICTED no-opped"
assert _PREAMBLE_REFLOWED != _PREAMBLE_OK, "_PREAMBLE_REFLOWED no-opped"


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    # _PASSING/_FAILING are bare bullet fragments with no `## 6.`/`## 7.` headers, so the
    # §6-scoped preamble pin cannot run against them; it has its own headered fixtures below.
    bullet_checks = [c for c in _CHECKS if c is not check_conflict_preamble_verbatim]

    for check in bullet_checks:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    for check in bullet_checks:
        ok, _ = check(_FAILING)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_edit_bucket_named(_EDIT_WITHOUT_BEFORE_AFTER)
    cases.append(("edit-without-before-after: check_edit_bucket_named (expect FAIL)", not ok))

    ok, _ = check_confirmation_template_lists_edit(_CONFIRMATION_FIELD_SUBSTRING_FALSE_POSITIVE)
    cases.append(("substring-false-positive: check_confirmation_template_lists_edit (expect FAIL)", not ok))

    ok, _ = check_supersede_verdict_named(_SUPERSEDE_SECOND_PROMPT)
    cases.append(("supersede-second-prompt: check_supersede_verdict_named (still OK)", ok))

    ok, _ = check_supersede_verdict_named(_SUPERSEDE_DEFERRED_WRITE)
    cases.append(("supersede-deferred-write: check_supersede_verdict_named (expect FAIL)", not ok))

    for name, fixture in (
        ("inverted", _SUPERSEDE_INVERTED),
        ("second-prompt", _SUPERSEDE_SECOND_PROMPT),
        ("deferred-write", _SUPERSEDE_DEFERRED_WRITE),
        ("negation-on-the-wrong-noun", _SUPERSEDE_NEGATION_MISPLACED),
    ):
        ok, _ = check_supersede_bullet_verbatim(fixture)
        cases.append((f"supersede-{name}: check_supersede_bullet_verbatim (expect FAIL)", not ok))

    ok, _ = check_supersede_bullet_verbatim(_SUPERSEDE_REFLOWED)
    cases.append(("supersede-reflowed: check_supersede_bullet_verbatim (still OK)", ok))

    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_OK)
    cases.append(("preamble: check_conflict_preamble_verbatim (still OK)", ok))
    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_CONTRADICTED)
    cases.append(("preamble-grants-a-second-question: check_conflict_preamble_verbatim (expect FAIL)", not ok))
    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_DECOY_BULLET)
    cases.append(("preamble-clause-before-the-bullets (expect FAIL)", not ok))
    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_PREPENDED)
    cases.append(("preamble-clause-above-the-contract (expect FAIL)", not ok))

    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_SPLIT_BULLET)
    cases.append((
        "preamble-renamed-first-bullet: span must not shrink (still OK)", ok,
    ))

    ok, _ = check_conflict_preamble_verbatim(_PREAMBLE_REFLOWED)
    cases.append(("preamble-reflowed: check_conflict_preamble_verbatim (still OK)", ok))
    ok, _ = check_conflict_preamble_verbatim(_PASSING)
    cases.append(("preamble: headerless fixture reports the boundary (expect FAIL)", not ok))

    ok, _ = check_supersede_bullet_verbatim(_SCOPED_OK)
    cases.append(("scoped: check_supersede_bullet_verbatim reads §6's verdict (still OK)", ok))
    ok, msg = check_supersede_bullet_verbatim(_SCOPED_VERDICT_DELETED)
    cases.append(("scoped: §6 verdict deleted must not retarget to §8's bullet (expect FAIL)",
                  (not ok) and "missing entirely" in msg))

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
