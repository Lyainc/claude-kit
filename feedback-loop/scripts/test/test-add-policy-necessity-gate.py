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

Pinned claims:

1. The gate exists in §6, and runs before the §3 confirmation.
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


def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


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


# The BOLD block marker, not the bare phrase: "necessity gate" also appears in the frontmatter
# description and in the intro, so anchoring on it widened the slice to most of the file and the
# scoping this helper claims would have been fiction.
_GATE_START = "**necessity gate"
# The gate block ends where the write-form paragraph begins; if that anchor ever moves,
# the fallback window keeps the slice from silently swallowing the rest of the file.
_GATE_END = "for a new rule the engine appends"


def _gate_block(text: str) -> str:
    """Slice out the §6 necessity-gate block, or "" if it isn't there.

    Scoped, not whole-document: `## Rules` restates the gate in summary form, so a
    whole-document match would pass on the summary alone while the block itself —
    the part the engine actually executes — had been deleted.
    """
    lower = text.lower()
    start = lower.find(_GATE_START)
    if start == -1:
        return ""
    end = lower.find(_GATE_END, start)
    return text[start:end] if end != -1 else text[start:start + 2000]


# The gate's authority paragraph, pinned VERBATIM rather than by pattern. Two review rounds
# showed why. A presence check ("recommends only", "first option", "second prompt" all appear)
# passed "recommends only **as a label**, but it BLOCKS the write and raises its own second
# prompt". Adding negation patterns then passed the correct paragraph with one clause appended —
# "though it does **stop the write** when the answer is clearly no" — because "stop" was not in
# the forbidden-verb list, and "refuses", "halts", "vetoes", "declines" are the same hole. Every
# pattern is a blocklist of the last wording someone tried, while "recommends only" is a
# universal claim, so the contract text itself is the pin. It is matched as the END of the gate
# block, so a clause appended after the paragraph fails too. Whitespace is normalised: a reflow
# is not a change, an edit to the words is — and updating this constant is then the deliberate
# act of changing the contract, in the same commit.
#
# ponytail: the ceiling is the gate block. This pins what the paragraph says and that nothing is
# appended to it, not what the rest of the skill says about the gate.
_AUTHORITY_CONTRACT = """\
Three outcomes: **pass / absorbed into an existing entry / recommend not landing.** The gate
**recommends only**: it renders as the **first option of the §3 AskUserQuestion** and adds **no
second prompt**, and it **never blocks the landing** — not one the user asked for directly, not
one arriving as a distill proposal. A tool does not veto the work it was told to do. It weighs
the **artifact's cost** (must this be a *new* always-loaded entry?), never the rule's **reuse
value**, which stays distill's."""


def check_gate_present_and_positioned(text: str) -> tuple[bool, str]:
    """The gate must exist and run before the §3 confirmation."""
    block = _gate_block(text)
    if not block:
        return False, "no necessity gate block found in the SKILL.md body"
    if not _states(block, "before the §3 confirmation"):
        return False, "the gate doesn't state that it runs before the §3 confirmation"
    return True, "necessity gate present, positioned before the §3 confirmation"


def check_four_questions(text: str) -> tuple[bool, str]:
    """All four questions, each pinned by its own distinguishing content."""
    block = _gate_block(text)
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


def check_three_outcomes(text: str) -> tuple[bool, str]:
    """pass / absorbed into an existing entry / recommend not landing.

    Kept beside the verbatim pin below for its diagnostic: this one names WHICH outcome
    went missing, where the pin only says the paragraph changed.
    """
    block = _gate_block(text)
    if not _states(block, "recommend not landing"):
        return False, "the 'recommend not landing' outcome is missing"
    if not _states(block, "absorbed into an existing entry"):
        return False, "the 'absorb into an existing entry' outcome is missing"
    if not re.search(r"\bpass\b", block, re.IGNORECASE):
        return False, "the 'pass' outcome is missing"
    return True, "all three outcomes stated (pass / absorb / recommend not landing)"


def check_authority_paragraph_verbatim(text: str) -> tuple[bool, str]:
    """The gate's ceiling, matched against the pinned contract text.

    One check rather than a set of patterns: it carries the 1-click invariant (no second
    prompt), the never-blocks guarantee on both inbound paths, and the distill boundary,
    against a contradicting clause set *beside* them — which is how both pattern-based
    versions of this check were defeated. Anchored at the END of the block, so a clause
    appended after the paragraph fails as well.
    """
    block = _gate_block(text)
    if not block:
        return False, "no necessity gate block found in the SKILL.md body"
    if not _normalise(block).endswith(_normalise(_AUTHORITY_CONTRACT)):
        return False, (
            "the gate's authority paragraph no longer matches its pinned contract text, or "
            "something was appended after it — a clause was added, removed or reworded. If "
            "that is intended, update _AUTHORITY_CONTRACT in this file in the same commit"
        )
    return True, "gate authority paragraph matches its pinned contract text verbatim"


def check_distill_boundary(text: str) -> tuple[bool, str]:
    """Artifact cost is the gate's question; reuse value stays distill's.

    Without this the skill contradicts its own `description`, which says add-policy
    never re-judges the rule's reuse value.
    """
    block = _gate_block(text)
    if not _states(block, "reuse value"):
        return False, "the gate doesn't disclaim the reuse-value judgment (distill's)"
    if not (_states(block, "artifact's cost") or _states(block, "artifact cost")):
        return False, "the gate doesn't name the artifact's cost as what it weighs"
    lower = text.lower()
    if "reuse value" not in lower.split("## 1.")[0]:
        return False, "the intro/description doesn't carry the reuse-value vs artifact split"
    return True, "gate judges artifact cost, never reuse value (distill boundary intact)"


def check_confirmation_surfaces_the_recommendation(text: str) -> tuple[bool, str]:
    """§3 carries the 필요성 field AND a question per non-통과 outcome.

    The gate has two non-통과 outcomes, and §3's default question ("여기에 이렇게 넣을게요 —
    맞아요?") fits neither. A single hardcoded don't-land wording is worse than none: asked
    after a "기존 항목으로 충분" verdict it offers a yes/no on abandoning the rule when the
    recommendation was to fold it into an existing entry, so the user's answer lands a
    brand-new entry the gate argued against.
    """
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
    check_authority_paragraph_verbatim,
    check_distill_boundary,
    check_confirmation_surfaces_the_recommendation,
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
add-policy never re-judges the rule's reuse value; it judges whether a new artifact is needed.

## 1. Input contract

- 필요성: <통과 | 기존 항목으로 충분 | 안 넣는 게 나음 — <이유 한 줄>>

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" — unless 필요성 is not 통과,
and then the gate's recommendation is the first option: 기존 항목으로 충분 asks about folding it
into that entry, 안 넣는 게 나음 asks whether to land it at all.

**Necessity gate — after the conflict check, before the §3 confirmation.** Four questions:

1. Has what this rule prevents **actually happened**, or does it only look likely?
2. Does an existing or more general entry already imply it → strengthen that entry instead.
3. Is **something else already asking the same question** — a hook, a CI guard?
4. Does one clause on a neighbouring entry do it, with no new entry → that form.

%s

For a new rule the engine appends in each site's native form.
""" % _AUTHORITY_CONTRACT

# Pre-#450 regression: no gate at all, so every claim is absent.
_FAILING = """\
## 6. Conflict check

- **Duplicate**: strengthen that entry instead of adding a second.
- **Contradiction**: do NOT write — report and stop.

For a new rule the engine appends in each site's native form.
"""

# The three mutations that defeated the pattern-based checks, in the order review found them:
# keywords deleted; keywords kept but every claim inverted; and — the one a negation pattern
# still passed — the paragraph left intact with a single contradicting clause appended.
_REFUSING_GATE = _PASSING.replace(
    "The gate\n**recommends only**:",
    "The gate **blocks the write** when it judges the rule unnecessary, asking a second\n"
    "question before anything is written:",
)
_INVERTED_GATE = _PASSING.replace(
    "**recommends only**:",
    "**recommends only** as a label, but it **blocks the write** and raises its own second\nprompt:",
)
_APPENDED_CLAUSE = _PASSING.replace(
    "which stays distill's.",
    "which stays distill's. It does stop the write when the answer is clearly no.",
)
# The same contract with every line break moved: whitespace is not the contract (#440), so this
# must still read as unchanged.
_REFLOWED_GATE = _PASSING.replace(_AUTHORITY_CONTRACT, _normalise(_AUTHORITY_CONTRACT))

# Question 3 dropped — the exact question P14 needed. The other checks stay green, so this
# fixture is what keeps check_four_questions from degrading into "a gate exists".
_MISSING_QUESTION_3 = _PASSING.replace(
    "3. Is **something else already asking the same question** — a hook, a CI guard?\n", ""
)

# The gate is summarised in `## Rules` but the executable block is gone. A whole-document
# matcher passes this; the scoped slice must not.
_SUMMARY_ONLY = """\
## 6. Conflict check

- **Duplicate**: strengthen that entry instead of adding a second.

For a new rule the engine appends in each site's native form.

## Rules

- The necessity gate runs before every landing: four questions, three outcomes
  (pass / absorb / recommend not landing), and it recommends only.
"""

# §3 offers one hardcoded don't-land wording for both non-통과 outcomes — the defect that
# misreports an absorb verdict to the user answering it.
_ONE_GENERIC_REFUSAL = _PASSING.replace(
    """— unless 필요성 is not 통과,
and then the gate's recommendation is the first option: 기존 항목으로 충분 asks about folding it
into that entry, 안 넣는 게 나음 asks whether to land it at all.""",
    """— unless 필요성 is not 통과,
and then ask "이건 안 넣는 게 나아 보이는데, 그래도 넣을까요?" instead.""",
)


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    for check in _CHECKS:
        ok, _ = check(_FAILING)
        cases.append((f"no-gate: {check.__name__} (expect FAIL)", not ok))

    for name, fixture in (
        ("refusing", _REFUSING_GATE),
        ("inverted", _INVERTED_GATE),
        ("appended-contradicting-clause", _APPENDED_CLAUSE),
    ):
        ok, _ = check_authority_paragraph_verbatim(fixture)
        cases.append((f"{name}-gate: check_authority_paragraph_verbatim (expect FAIL)", not ok))

    ok, _ = check_authority_paragraph_verbatim(_REFLOWED_GATE)
    cases.append(("reflowed-gate: check_authority_paragraph_verbatim (still OK)", ok))

    ok, _ = check_four_questions(_MISSING_QUESTION_3)
    cases.append(("missing-question-3: check_four_questions (expect FAIL)", not ok))
    ok, _ = check_three_outcomes(_MISSING_QUESTION_3)
    cases.append(("missing-question-3: check_three_outcomes (still OK)", ok))

    for check in (check_four_questions, check_three_outcomes, check_authority_paragraph_verbatim):
        ok, _ = check(_SUMMARY_ONLY)
        cases.append((f"summary-only: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_confirmation_surfaces_the_recommendation(_ONE_GENERIC_REFUSAL)
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
    print(f"OK: all {passed} add-policy-necessity-gate checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
