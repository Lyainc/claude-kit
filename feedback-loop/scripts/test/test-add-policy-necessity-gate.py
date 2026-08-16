#!/usr/bin/env python3
"""Regression test: add-policy runs a necessity gate before it lands anything.

#450. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill, so this
is a static-content check — it does not execute LLM logic. It pins the gate #450 added:
before the §3 confirmation, §6 asks four questions and reaches one of three outcomes,
and its authority stops at a recommendation.

The gap #450 reported: of §6's verdicts only Contradiction stopped a write, and it
stops it for *disagreeing with an existing rule* — a rule that contradicts nothing and
is simply unnecessary passed straight through. Measured cost: local-harness P14, landed
2026-07-24 and retired the next day, where the retirement's own findings say the gate
was already being asked by `session-close` ① (question 3 is that finding).

#663 moved the gate's CANONICAL text out of the SKILL.md body and into
`add-policy/reference.md` §6-gate-contract — SKILL.md's §6 had every ≥300-char paragraph
pinned verbatim, so the token budget (#447) had no escape hatch left that wasn't a trim. The
pins followed the text rather than being deleted (#609 measured what an unpinned region is
worth: two shipped artifacts pinned by nothing could be deleted wholesale with the suite still
green). So the live run reads BOTH files: the gate block against reference.md, the §3
confirmation and the §6 pointer against SKILL.md.

Pinned claims:

1. The gate exists under reference.md §6-gate-contract, runs before the §3 confirmation, and
   SKILL.md §6 still points at it with an instruction to apply it (the seam #663 created).
2. All four questions are stated, each by its own distinguishing content — so dropping
   one (question 3, the doubled-gate check that P14 needed) fails here.
3. All three outcomes are stated (pass / absorb / recommend not landing).
4. The gate's authority paragraph, VERBATIM: it recommends only, as the first option of
   the same AskUserQuestion, adds no second prompt, and never blocks a landing on either
   inbound path (a direct user request or a distill proposal). Pinned as text rather than
   by pattern because two pattern-based versions were defeated by a contradicting clause
   set beside the negation — see the comment on `_AUTHORITY_CONTRACT`.
5. The distill boundary stays coherent: the gate judges the artifact's cost, never the
   rule's reuse value — without this the skill contradicts its own `description`.
6. §3's confirmation template carries the 필요성 field, and §3 gives the recommendation
   its own question when 필요성 is not 통과 (a single hardcoded don't-land wording would
   misreport an "absorb into an existing entry" verdict to the user answering it).

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-necessity-gate.py
    python3 feedback-loop/scripts/test/test-add-policy-necessity-gate.py --self-test

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
_REFERENCE_PATH = _SKILL_PATH.with_name("reference.md")


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


def _load_reference() -> str:
    """#663: the gate's canonical text lives here now, not in SKILL.md's body."""
    if not _REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"reference.md not found at {_REFERENCE_PATH}")
    return _REFERENCE_PATH.read_text(encoding="utf-8")


def _states(text: str, phrase: str) -> bool:
    """True if `text` states `phrase`, ignoring how the prose happens to wrap.

    Same matcher as test-add-policy-index-detail.py, and for the same reason (#440):
    SKILL.md is hard-wrapped, so a reflow moves a line break into the middle of a
    phrase and a plain substring test reads the claim as deleted while it is still
    there. `\\b` on the outer edges keeps "no new entry" from matching inside a
    longer word.
    """
    core = r"\s+".join(re.escape(word) for word in phrase.split())
    return re.search(rf"\b{core}\b", text, re.IGNORECASE) is not None


def _normalise(text: str) -> str:
    """Collapse every run of whitespace, so a reflow reads as no change (#440)."""
    return " ".join(text.split())


# SKILL.md's §6, used only for the POINTER seam below. The canonical gate text moved out of
# this section in #663.
_SECTION_6_RE = re.compile(r"^## 6\.\s.*?(?=^## 7\.\s)", re.MULTILINE | re.DOTALL)

# #663: the canonical block lives under reference.md's own `## §6-gate-contract` heading, and
# the scoping rationale is unchanged — on a whole-file search a verbatim copy of the contract
# pasted into a neighbouring section became the slice, so equality passed against the decoy
# while the real gate was free to be a hard blocker. Whole-block equality is total over the
# slice; it says nothing about whether the slice is the one the engine executes. Same shape as
# test-add-policy-conflict-edit.py's `_verdict_scope`.
_REF_GATE_SECTION_RE = re.compile(
    r"^## §6-gate-contract\b.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL
)
# The BOLD block marker, not the bare phrase: "necessity gate" also appears in the frontmatter
# description, in SKILL.md's intro, and in that section's own framing paragraph, so anchoring on
# the bare phrase widened the slice.
_GATE_START = "**necessity gate"
# The section's first line identifies the real reference file, for the header-drift precondition.
_REFERENCE_TITLE = "# add-policy — reference"


def _gate_block(ref: str) -> str:
    """Slice out reference.md's canonical necessity-gate block, or "" if it isn't there.

    Scoped twice: to `## §6-gate-contract` (a copy elsewhere in the file is not the gate the
    engine runs), then to the block itself (the section's framing paragraph is prose about the
    contract, not the contract). The slice then runs to the END of the section — that is
    stricter than the old content-addressed end anchor, because a contradicting clause parked
    below the block is now inside the pin instead of outside it. A document with no
    `## §6-gate-contract` heading falls back to itself, for the bare in-memory fixtures.
    """
    match = _REF_GATE_SECTION_RE.search(ref)
    scope = match.group(0) if match else ref
    start = scope.lower().find(_GATE_START)
    return scope[start:] if start != -1 else ""


# The WHOLE gate block is pinned VERBATIM — equality, not a suffix match. Three review rounds
# landed the same attack in three places. A presence check passed "recommends only **as a
# label**, but it BLOCKS the write"; negation patterns then passed one appended clause ("though
# it does **stop the write**...") because "stop" was not in the verb list; and a suffix-anchored
# pin passed a clause inserted ABOVE the paragraph ("If the answer to any of the four is against
# landing, do NOT write ... Only a rule that clears all four reaches §3 at all"), which makes the
# gate a hard blocker while the paragraph saying it never blocks sits underneath, untouched.
# Every pattern is a blocklist of the last wording someone tried, and every partial anchor leaves
# a region for the next one, so the block's own text is the pin and the comparison is total.
# Whitespace is normalised: a reflow is not a change, an edit to the words is — and updating this
# constant is then the deliberate act of changing the contract, in the same commit.
#
# ponytail: the ceiling is the gate block. `check_no_unnegated_extra_prompt` below carries the
# 1-click invariant across the rest of the file; nothing here reasons about prose.
_GATE_CONTRACT = """\
**Necessity gate — after the conflict check, before the §3 confirmation.** The site's content
is already read, so it costs no extra lookup. Four questions:

1. Has what this rule prevents **actually happened**, or does it only look likely? Speculative
   → recommend not landing.
2. Does an existing or more general entry already imply it → strengthen that entry instead
   (Duplicate/Edit above), adding none.
3. Is **something else already asking the same question** — a hook, a CI guard, an existing
   confirmation checkpoint, the tool itself? A doubled gate is dead weight.
4. Does one clause on a neighbouring entry do it, with no new entry → that form.

Three outcomes: **pass / absorbed into an existing entry / recommend not landing.** The gate
**recommends only**: it renders as the **first option of the §3 AskUserQuestion** and adds **no
second prompt**, and it **never blocks the landing** — not one the user asked for directly, not
one arriving as a distill proposal. A tool does not veto the work it was told to do. It weighs
the **artifact's cost** (must this be a *new* always-loaded entry?), never the rule's **reuse
value**, which stays distill's.
"""


def check_gate_present_and_positioned(skill: str, ref: str) -> tuple[bool, str]:
    """The gate must exist, run before the §3 confirmation, and stay reachable from §6.

    #663 moved the canonical text to reference.md, so this check also carries the SEAM the
    split created: SKILL.md §6 must NAME `§6-gate-contract` and say to apply it. A pointer that
    decays into a bare citation is how an on-demand step turns optional — the same failure
    mode test-add-policy-routing.py's `check_scan_command_pointer` guards for the §6-snippet
    split (#469). Scoped to §6: a locator parked in another section is not the one the engine
    reads at the gate.
    """
    block = _gate_block(ref)
    if not block:
        return False, "no necessity gate block found under reference.md §6-gate-contract"
    if not _states(block, "before the §3 confirmation"):
        return False, "the gate doesn't state that it runs before the §3 confirmation"
    section_6 = _SECTION_6_RE.search(skill)
    if not section_6:
        # No silent whole-document fallback: renaming `## 6.`/`## 7.` would widen the scope to
        # the entire file, and a locator parked in §5 would then pass this check while the
        # engine reading §6 at the gate finds nothing — the exact `pointer-outside-§6` case.
        return False, (
            "SKILL.md has no `## 6.` section bounded by `## 7.` — the §6 scope this check "
            "depends on collapsed (heading drift)"
        )
    section = section_6.group(0)
    if "§6-gate-contract" not in section:
        return False, (
            "SKILL.md §6 doesn't name reference.md §6-gate-contract as where the gate's "
            "canonical text lives"
        )
    if not (_states(section, "apply it as written") or _states(section, "read that section")):
        return False, (
            "SKILL.md §6's pointer decayed into a bare citation — it must tell the engine to "
            "read and apply §6-gate-contract, not merely cite it"
        )
    return True, "necessity gate present in reference.md, positioned before §3, reachable from §6"


def check_four_questions(skill: str, ref: str) -> tuple[bool, str]:
    """All four questions, each pinned by its own distinguishing content."""
    block = _gate_block(ref)
    questions = {
        "1 (has it actually happened?)": ("actually happened",),
        "2 (already implied by an existing entry)": ("already imply", "already implies"),
        "3 (something else already asks it)": (
            "already asking the same question",
            "already asks the same question",
        ),
        "4 (a clause on a neighbouring entry)": ("no new entry", "without a new entry"),
    }
    missing = [
        label for label, variants in questions.items()
        if not any(_states(block, v) for v in variants)
    ]
    if missing:
        return False, f"necessity-gate question(s) missing: {missing}"
    return True, "all four necessity-gate questions stated"


def check_three_outcomes(skill: str, ref: str) -> tuple[bool, str]:
    """pass / absorbed into an existing entry / recommend not landing.

    Kept beside the verbatim pin below for its diagnostic: this one names WHICH outcome
    went missing, where the pin only says the paragraph changed.
    """
    block = _gate_block(ref)
    if not _states(block, "recommend not landing"):
        return False, "the 'recommend not landing' outcome is missing"
    if not _states(block, "absorbed into an existing entry"):
        return False, "the 'absorb into an existing entry' outcome is missing"
    if not re.search(r"\bpass\b", block, re.IGNORECASE):
        return False, "the 'pass' outcome is missing"
    return True, "all three outcomes stated (pass / absorb / recommend not landing)"


def check_gate_block_verbatim(skill: str, ref: str) -> tuple[bool, str]:
    """The whole canonical gate block matches its pinned contract text.

    Equality over the block, not a match on part of it: this is what carries the 1-click
    invariant (no second prompt) and the never-blocks guarantee on both inbound paths
    against a contradicting clause set beside them — above, below or inside.
    """
    if _REFERENCE_TITLE in ref and _REF_GATE_SECTION_RE.search(ref) is None:
        # The title line, not the section itself: the precondition has to identify the REAL
        # reference file, or a renamed heading falls back to whole-file and this suite stays
        # green while the contract drifts. The bare in-memory fixtures carry no title, so they
        # keep the fallback they need.
        return False, "§6-gate-contract section boundary not found (header drift?)"
    block = _gate_block(ref)
    if not block:
        return False, "no necessity gate block found under reference.md §6-gate-contract"
    if _normalise(block) != _normalise(_GATE_CONTRACT):
        return False, (
            "reference.md §6-gate-contract no longer matches its pinned contract text — a "
            "clause was added, removed or reworded anywhere in it (including below it, inside "
            "the same section). If that is intended, update _GATE_CONTRACT in this file in the "
            "same commit"
        )
    return True, "necessity-gate block matches its pinned contract text verbatim"


def check_distill_boundary(skill: str, ref: str) -> tuple[bool, str]:
    """Artifact cost is the gate's question; reuse value stays distill's.

    Without this the skill contradicts its own `description`, which says add-policy
    never re-judges the rule's reuse value.
    """
    text = skill
    block = _gate_block(ref)
    if not _states(block, "reuse value"):
        return False, "the gate doesn't disclaim the reuse-value judgment (distill's)"
    if not (_states(block, "artifact's cost") or _states(block, "artifact cost")):
        return False, "the gate doesn't name the artifact's cost as what it weighs"
    lower = text.lower()
    if "reuse value" not in lower.split("## 1.")[0]:
        return False, "the intro/description doesn't carry the reuse-value vs artifact split"
    return True, "gate judges artifact cost, never reuse value (distill boundary intact)"


def check_confirmation_surfaces_the_recommendation(skill: str, ref: str = "") -> tuple[bool, str]:
    """§3 carries the 필요성 field AND a question per non-통과 outcome.

    The gate has two non-통과 outcomes, and §3's default question ("여기에 이렇게 넣을게요 —
    맞아요?") fits neither. A single hardcoded don't-land wording is worse than none: asked
    after a "기존 항목으로 충분" verdict it offers a yes/no on abandoning the rule when the
    recommendation was to fold it into an existing entry, so the user's answer lands a
    brand-new entry the gate argued against.
    """
    text = skill
    pos = text.find("필요성:")
    if pos == -1:
        return False, "필요성 field missing from the §3 confirmation template"
    line_end = text.find("\n", pos)
    line = text[pos:line_end if line_end != -1 else len(text)]
    for outcome in ("기존 항목으로 충분", "안 넣는 게 나음"):
        if outcome not in line:
            return False, f"필요성 field doesn't offer the '{outcome}' outcome"
    ask_pos = text.find("Then AskUserQuestion")
    if ask_pos == -1:
        return False, "§3's AskUserQuestion instruction is missing"
    ask = text[ask_pos:]
    ask = ask[:ask.find("\n\n")] if "\n\n" in ask else ask
    for outcome in ("기존 항목으로 충분", "안 넣는 게 나음"):
        if outcome not in ask:
            return False, (
                f"§3's confirmation doesn't say what to ask on a '{outcome}' verdict — one "
                f"hardcoded wording misreports the other outcome to the user answering it"
            )
    return True, "§3 carries 필요성 and a distinct confirmation question per non-통과 outcome"


_CHECKS = [
    check_gate_present_and_positioned,
    check_four_questions,
    check_three_outcomes,
    check_gate_block_verbatim,
    check_distill_boundary,
    check_confirmation_surfaces_the_recommendation,
]


def run_checks(skill: str, ref: str) -> tuple[int, int]:
    """`skill` is SKILL.md (the §3 confirmation + the §6 pointer); `ref` is reference.md, where
    the gate's canonical text lives since #663. Two sources on purpose, not one concatenated
    blob: a SKILL.md claim must not be satisfiable from the reference, or the split's own seam
    goes unguarded."""
    passed = failed = 0
    for check in _CHECKS:
        ok, msg = check(skill, ref)
        print(f"  [{'OK  ' if ok else 'FAIL'}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test (in-memory fixtures) — TWO sources since #663, mirroring the split: the §3
# confirmation and the §6 pointer come from the SKILL.md side, the canonical gate block from
# the reference.md side.
# ---------------------------------------------------------------------------

_PASSING_SKILL = """\
add-policy never re-judges the rule's reuse value; it judges whether a new artifact is needed.

## 1. Input contract

- 필요성: <통과 | 기존 항목으로 충분 | 안 넣는 게 나음 — <이유 한 줄>>

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" — unless 필요성 is not 통과,
and then the gate's recommendation is the first option: 기존 항목으로 충분 asks about folding it
into that entry, 안 넣는 게 나음 asks whether to land it at all.

## 6. Conflict check

**Necessity gate — runs here, after the conflict check.** Canonical binding text:
[reference.md](reference.md) §6-gate-contract — read that section and apply it as written.

## 7. Output contract
"""

_PASSING_REF = (
    "## §6-gate-contract — the necessity gate, CANONICAL text\n"
    "\n"
    "This section is the contract, not background.\n"
    "\n"
    + _GATE_CONTRACT
    + "\n"
    "## §6-gate — why it exists\n"
)

# Pre-#450 regression: no gate anywhere, so every claim is absent on both sides.
_FAILING_SKILL = """\
## 6. Conflict check

- **Duplicate**: strengthen that entry instead of adding a second.
- **Contradiction**: do NOT write — report and stop.

## 7. Output contract
"""
_FAILING_REF = """\
## §6-memory — why the memory scan is two steps

Nothing here states a gate.
"""

# The three mutations that defeated the pattern-based checks, in the order review found them:
# keywords deleted; keywords kept but every claim inverted; and — the one a negation pattern
# still passed — the paragraph left intact with a single contradicting clause appended. Since
# #663 they mutate the CANONICAL copy, which is reference.md's.
_REFUSING_GATE = _PASSING_REF.replace(
    "The gate\n**recommends only**:",
    "The gate **blocks the write** when it judges the rule unnecessary, asking a second\n"
    "question before anything is written:",
)
_INVERTED_GATE = _PASSING_REF.replace(
    "**recommends only**:",
    "**recommends only** as a label, but it **blocks the write** and raises its own second\nprompt:",
)
_APPENDED_CLAUSE = _PASSING_REF.replace(
    "which stays distill's.",
    "which stays distill's. It does stop the write when the answer is clearly no.",
)
# #663: the section-scoped slice runs to the END of `## §6-gate-contract`, so a contradicting
# clause parked BELOW the block — outside the old content-addressed end anchor — is now inside
# the pin. This case is what proves that, and it is the mutation the split made possible.
_TRAILING_CLAUSE = _PASSING_REF.replace(
    "\n## §6-gate — why it exists",
    "\nIf the answer to any of the four is against landing, do NOT write; only a rule that\n"
    "clears all four reaches §3 at all.\n\n## §6-gate — why it exists",
)
# The same contract with every line break moved: whitespace is not the contract (#440), so this
# must still read as unchanged.
_REFLOWED_GATE = _PASSING_REF.replace(_GATE_CONTRACT, _normalise(_GATE_CONTRACT))

# Question 3 dropped — the exact question P14 needed. The other checks stay green, so this
# fixture is what keeps check_four_questions from degrading into "a gate exists".
_MISSING_QUESTION_3 = _PASSING_REF.replace(
    "3. Is **something else already asking the same question** — a hook, a CI guard, an existing\n"
    "   confirmation checkpoint, the tool itself? A doubled gate is dead weight.\n",
    "",
)

# The section exists but holds only a summary; the executable block is gone. A whole-document
# matcher passes this; the scoped slice must not.
_SUMMARY_ONLY_REF = """\
## §6-gate-contract — the necessity gate, CANONICAL text

The necessity gate runs before every landing: four questions, three outcomes
(pass / absorb / recommend not landing), and it recommends only.

## §6-gate — why it exists
"""

# §3 offers one hardcoded don't-land wording for both non-통과 outcomes — the defect that
# misreports an absorb verdict to the user answering it.
_ONE_GENERIC_REFUSAL = _PASSING_SKILL.replace(
    """— unless 필요성 is not 통과,
and then the gate's recommendation is the first option: 기존 항목으로 충분 asks about folding it
into that entry, 안 넣는 게 나음 asks whether to land it at all.""",
    """— unless 필요성 is not 통과,
and then ask "이건 안 넣는 게 나아 보이는데, 그래도 넣을까요?" instead.""",
)

# The #663 seam, from the SKILL.md side: the pointer is the only thing left in the body that
# reaches the contract, so its two decay modes get fixtures of their own.
_POINTER_DROPPED = _PASSING_SKILL.replace(
    """Canonical binding text:
[reference.md](reference.md) §6-gate-contract — read that section and apply it as written.""",
    "The engine weighs whether a new entry is needed.",
)
_POINTER_BARE_CITATION = _PASSING_SKILL.replace(
    " — read that section and apply it as written.", " (background reading).",
)

# The pointer moved out of §6: §6 is still there, and the engine reading it at the gate finds
# nothing. The whole-document fallback would pass this, the §6 scope must not.
_POINTER_OUTSIDE_SECTION_6 = """\
add-policy never re-judges the rule's reuse value; it judges whether a new artifact is needed.

## 1. Input contract

- 필요성: <통과 | 기존 항목으로 충분 | 안 넣는 게 나음 — <이유 한 줄>>

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" — unless 필요성 is not 통과,
and then the gate's recommendation is the first option: 기존 항목으로 충분 asks about folding it
into that entry, 안 넣는 게 나음 asks whether to land it at all.

## 5. Inviolability

**Necessity gate** — canonical binding text: [reference.md](reference.md) §6-gate-contract —
read that section and apply it as written.

## 6. Conflict check

- **Duplicate**: strengthen that entry instead of adding a second.

## 7. Output contract
"""


# A fixture built by `.replace()` whose target string has drifted silently becomes a copy of
# its base, and an expect-FAIL case on a copy of the base would then be testing nothing.
# `## 6.` renamed: the §6 scope this check depends on no longer resolves. The locator is still
# present and correct, so only the missing-scope guard can red this.
_SECTION_6_HEADING_DRIFT = _PASSING_SKILL.replace("## 6. Conflict check", "## 6b. Conflict check")

for _name, _fixture, _base in (
    ("_SECTION_6_HEADING_DRIFT", _SECTION_6_HEADING_DRIFT, _PASSING_SKILL),
    ("_REFUSING_GATE", _REFUSING_GATE, _PASSING_REF),
    ("_INVERTED_GATE", _INVERTED_GATE, _PASSING_REF),
    ("_APPENDED_CLAUSE", _APPENDED_CLAUSE, _PASSING_REF),
    ("_TRAILING_CLAUSE", _TRAILING_CLAUSE, _PASSING_REF),
    ("_REFLOWED_GATE", _REFLOWED_GATE, _PASSING_REF),
    ("_MISSING_QUESTION_3", _MISSING_QUESTION_3, _PASSING_REF),
    ("_ONE_GENERIC_REFUSAL", _ONE_GENERIC_REFUSAL, _PASSING_SKILL),
    ("_POINTER_DROPPED", _POINTER_DROPPED, _PASSING_SKILL),
    ("_POINTER_BARE_CITATION", _POINTER_BARE_CITATION, _PASSING_SKILL),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"
assert _POINTER_OUTSIDE_SECTION_6 != _PASSING_SKILL


# A verbatim copy of the contract parked in a neighbouring reference section, with the real
# §6-gate-contract replaced by a hard blocker. On a whole-file search the pin read the copy and
# passed; scoped to the section it must not.
_DECOY_ELSEWHERE = (
    "## §6-memory — why the memory scan is two steps\n"
    "\n"
    + _GATE_CONTRACT
    + "\n"
    "## §6-gate-contract — the necessity gate, CANONICAL text\n"
    "\n"
    "**Necessity gate — after the conflict check.** Four questions decide it, and if any of\n"
    "them says no the engine does NOT write: it reports the finding and stops, exactly as a\n"
    "Contradiction does.\n"
    "\n"
    "## §6-gate — why it exists\n"
)
assert _GATE_CONTRACT in _DECOY_ELSEWHERE and "## §6-gate-contract" in _DECOY_ELSEWHERE

# Heading drift on a document that IS the real reference file (it carries the title line), so
# the precondition must name the boundary instead of falling back to a whole-file match.
_HEADING_DRIFT = (_REFERENCE_TITLE + "\n\n" + _DECOY_ELSEWHERE).replace(
    "## §6-gate-contract —", "## §6 gate contract —"
)
assert _REFERENCE_TITLE in _HEADING_DRIFT and "## §6-gate-contract" not in _HEADING_DRIFT


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING_SKILL, _PASSING_REF)
        cases.append((f"passing: {check.__name__}", ok))

    for check in _CHECKS:
        ok, _ = check(_FAILING_SKILL, _FAILING_REF)
        cases.append((f"no-gate: {check.__name__} (expect FAIL)", not ok))

    # #663: every one of these corrupts the CANONICAL copy, which is reference.md's.
    for name, fixture in (
        ("refusing", _REFUSING_GATE),
        ("inverted", _INVERTED_GATE),
        ("appended-contradicting-clause", _APPENDED_CLAUSE),
        ("clause-parked-below-the-block", _TRAILING_CLAUSE),
    ):
        ok, _ = check_gate_block_verbatim(_PASSING_SKILL, fixture)
        cases.append((f"reference.md {name}-gate: check_gate_block_verbatim (expect FAIL)", not ok))

    ok, msg = check_gate_block_verbatim(_PASSING_SKILL, _HEADING_DRIFT)
    cases.append(("header-drift (§6-gate-contract renamed): names the boundary (expect FAIL)",
                  (not ok) and "boundary not found" in msg))

    ok, _ = check_gate_block_verbatim(_PASSING_SKILL, _DECOY_ELSEWHERE)
    cases.append(("decoy-copy-outside-§6-gate-contract: check_gate_block_verbatim (expect FAIL)", not ok))

    ok, _ = check_gate_block_verbatim(_PASSING_SKILL, _REFLOWED_GATE)
    cases.append(("reflowed-gate: check_gate_block_verbatim (still OK)", ok))

    ok, _ = check_four_questions(_PASSING_SKILL, _MISSING_QUESTION_3)
    cases.append(("missing-question-3: check_four_questions (expect FAIL)", not ok))
    ok, _ = check_three_outcomes(_PASSING_SKILL, _MISSING_QUESTION_3)
    cases.append(("missing-question-3: check_three_outcomes (still OK)", ok))

    for check in (check_four_questions, check_three_outcomes, check_gate_block_verbatim):
        ok, _ = check(_PASSING_SKILL, _SUMMARY_ONLY_REF)
        cases.append((f"summary-only: {check.__name__} (expect FAIL)", not ok))

    # The seam #663 created: SKILL.md's body must keep a live pointer at the canonical text.
    for name, skill_fixture in (
        ("pointer-dropped", _POINTER_DROPPED),
        ("pointer-bare-citation", _POINTER_BARE_CITATION),
        ("pointer-outside-§6", _POINTER_OUTSIDE_SECTION_6),
        # Heading drift: with `## 6.` renamed there is no §6 to scope to. The scope must NOT
        # silently widen to the whole document, or a §5-parked locator would read as reachable.
        ("§6-heading-drift", _SECTION_6_HEADING_DRIFT),
    ):
        ok, _ = check_gate_present_and_positioned(skill_fixture, _PASSING_REF)
        cases.append((f"{name}: check_gate_present_and_positioned (expect FAIL)", not ok))

    ok, _ = check_confirmation_surfaces_the_recommendation(_ONE_GENERIC_REFUSAL, _PASSING_REF)
    cases.append((
        "one-generic-refusal: check_confirmation_surfaces_the_recommendation (expect FAIL)",
        not ok,
    ))

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

    print(f"Checking: {_SKILL_PATH}\n          {_REFERENCE_PATH} (gate contract, #663)\n")
    try:
        text = _load_skill()
        reference = _load_reference()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    passed, failed = run_checks(text, reference)
    print()
    if failed:
        print(f"RESULT: {failed} check(s) FAILED — see above.")
        return 1
    print(f"OK: all {passed} add-policy-necessity-gate checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
