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
4. The gate **recommends only**: first option of the same AskUserQuestion, no second
   prompt. This is the 1-click invariant the whole skill repeats.
5. An explicit user request is never blocked by the gate.
6. The distill boundary stays coherent: the gate judges the artifact's cost, never the
   rule's reuse value — without this the skill contradicts its own `description`.
7. §3's 1-click confirmation template carries the 필요성 field.

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


_GATE_START = "necessity gate"
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
    """pass / absorbed into an existing entry / recommend not landing."""
    block = _gate_block(text)
    if not _states(block, "recommend not landing"):
        return False, "the 'recommend not landing' outcome is missing"
    if not _states(block, "absorbed into an existing entry"):
        return False, "the 'absorb into an existing entry' outcome is missing"
    if not re.search(r"\bpass\b", block, re.IGNORECASE):
        return False, "the 'pass' outcome is missing"
    return True, "all three outcomes stated (pass / absorb / recommend not landing)"


def check_recommends_only_one_click(text: str) -> tuple[bool, str]:
    """Authority stops at a recommendation, inside the existing single confirmation."""
    block = _gate_block(text)
    if not _states(block, "recommends only"):
        return False, "the gate doesn't limit itself to a recommendation"
    if not _states(block, "first option"):
        return False, "the recommendation isn't rendered as the first option of the confirmation"
    if not _states(block, "second prompt"):
        return False, "the no-second-prompt (1-click) invariant is missing from the gate"
    return True, "gate recommends only, as the first option of the same 1-click confirmation"


def check_explicit_request_wins(text: str) -> tuple[bool, str]:
    """A landing the user asked for explicitly is never blocked by the gate."""
    block = _gate_block(text)
    stated = any(_states(block, p) for p in (
        "never blocks a landing the user asked for explicitly",
        "does not veto an explicit request",
        "never blocks an explicit request",
    ))
    if not stated:
        return False, "the gate doesn't say an explicit user request is still landed"
    return True, "an explicitly requested landing is never blocked by the gate"


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


def check_confirmation_template_has_necessity_field(text: str) -> tuple[bool, str]:
    """§3's 1-click confirmation template must carry the 필요성 line."""
    pos = text.find("필요성:")
    if pos == -1:
        return False, "필요성 field missing from the §3 confirmation template"
    line_end = text.find("\n", pos)
    line = text[pos:line_end if line_end != -1 else len(text)]
    if "안 넣는" not in line:
        return False, "필요성 field doesn't offer the 'don't land it' outcome"
    return True, "§3 confirmation template carries the 필요성 field"


_CHECKS = [
    check_gate_present_and_positioned,
    check_four_questions,
    check_three_outcomes,
    check_recommends_only_one_click,
    check_explicit_request_wins,
    check_distill_boundary,
    check_confirmation_template_has_necessity_field,
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

**Necessity gate — after the conflict check, before the §3 confirmation.** Four questions:

1. Has what this rule prevents **actually happened**, or does it only look likely?
2. Does an existing or more general entry already imply it → absorb it above.
3. Is **something else already asking the same question** — a hook, a CI guard?
4. Does one clause on a neighbouring entry do the job, with no new entry → that form.

Three outcomes: **pass / absorbed into an existing entry / recommend not landing.** The gate
**recommends only**: it renders as the **first option of the §3 AskUserQuestion**, adds no
second prompt, and never blocks a landing the user asked for explicitly. It weighs the
**artifact's cost**, never the rule's **reuse value**, which stays distill's.

For a new rule the engine appends in each site's native form.

- 필요성: <통과 | 기존 항목으로 충분 | 안 넣는 게 나음 — <이유 한 줄>>
"""

# Pre-#450 regression: no gate at all, so every claim is absent.
_FAILING = """\
## 6. Conflict check

- **Duplicate**: strengthen that entry instead of adding a second.
- **Contradiction**: do NOT write — report and stop.

For a new rule the engine appends in each site's native form.
"""

# The gate exists but can refuse — the rejected design. 1-click and the explicit-request
# guarantee are both gone, and those two checks must be the ones that go red.
_REFUSING_GATE = _PASSING.replace(
    """**recommends only**: it renders as the **first option of the §3 AskUserQuestion**, adds no
second prompt, and never blocks a landing the user asked for explicitly.""",
    """**blocks the write** when it judges the rule unnecessary, asking the user a second
question before anything is written.""",
)

# Question 3 dropped — the exact question P14 needed. The other checks stay green, so
# this fixture is what keeps check_four_questions from degrading into "a gate exists".
_MISSING_QUESTION_3 = _PASSING.replace(
    "3. Is **something else already asking the same question** — a hook, a CI guard?\n", ""
)

# The gate is summarised in `## Rules` but the executable block is gone. A
# whole-document matcher passes this; the scoped slice must not.
_SUMMARY_ONLY = """\
## 6. Conflict check

- **Duplicate**: strengthen that entry instead of adding a second.

For a new rule the engine appends in each site's native form.

## Rules

- The necessity gate runs before every landing: four questions, three outcomes
  (pass / absorb / recommend not landing), and it recommends only.
"""


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    for check in _CHECKS:
        ok, _ = check(_FAILING)
        cases.append((f"no-gate: {check.__name__} (expect FAIL)", not ok))

    for check in (check_recommends_only_one_click, check_explicit_request_wins):
        ok, _ = check(_REFUSING_GATE)
        cases.append((f"refusing-gate: {check.__name__} (expect FAIL)", not ok))

    ok, _ = check_four_questions(_MISSING_QUESTION_3)
    cases.append(("missing-question-3: check_four_questions (expect FAIL)", not ok))
    ok, _ = check_three_outcomes(_MISSING_QUESTION_3)
    cases.append(("missing-question-3: check_three_outcomes (still OK)", ok))

    for check in (check_four_questions, check_three_outcomes, check_recommends_only_one_click):
        ok, _ = check(_SUMMARY_ONLY)
        cases.append((f"summary-only: {check.__name__} (expect FAIL)", not ok))

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
