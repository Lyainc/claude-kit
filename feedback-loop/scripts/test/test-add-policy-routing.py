#!/usr/bin/env python3
"""Regression test: add-policy SOFT reminder channel is layer-routed with a vanilla fallback.

G28 ① + ③. The engine (feedback-loop/skills/add-policy/SKILL.md) is a prose skill,
so this is a static-content check — it does not execute LLM logic. It pins the four
claims G28 added to §3, guarding against a future edit silently dropping the machine
work-rule catalogue routing or the vanilla fallback:

1. The SOFT reminder channel is routed by LAYER (both branches described):
   - stance/voice (judgment/expression) -> ~/.claude/CLAUDE.md
   - work-rule -> ~/.claude/rules
2. Vanilla fallback: ~/.claude/rules ABSENT -> CLAUDE.md fallback (both states covered).
3. No-hardcode clause: the machine rules/ structure is DETECTED, never hardcoded.
4. Thin pointer + backing detail when the catalogue channel is used.

Usage:
    python3 feedback-loop/scripts/test/test-add-policy-routing.py
    python3 feedback-loop/scripts/test/test-add-policy-routing.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

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

def check_stance_voice_to_claude_md(text: str) -> tuple[bool, str]:
    """stance/voice must be routed to ~/.claude/CLAUDE.md."""
    lower = text.lower()
    if "stance" not in lower and "judgment" not in lower:
        return False, "stance/voice (judgment) layer not mentioned in routing"
    if "~/.claude/claude.md" not in lower:
        return False, "~/.claude/CLAUDE.md not named as the stance/voice channel"
    return True, "stance/voice -> ~/.claude/CLAUDE.md routing present"


def check_workrule_to_rules(text: str) -> tuple[bool, str]:
    """work-rule must be routed to the ~/.claude/rules catalogue."""
    lower = text.lower()
    if "~/.claude/rules" not in lower:
        return False, "~/.claude/rules catalogue not named as the work-rule channel"
    if "work-rule" not in lower:
        return False, "work-rule layer not mentioned in routing"
    return True, "work-rule -> ~/.claude/rules routing present"


def check_vanilla_fallback(text: str) -> tuple[bool, str]:
    """Absent rules/ must fall back to CLAUDE.md (vanilla portability)."""
    lower = text.lower()
    has_fallback = "fall back" in lower or "fallback" in lower
    has_absent = "absent" in lower or "if it exists" in lower or "vanilla" in lower
    if not (has_fallback and has_absent):
        return False, (
            "vanilla fallback not described — need both a fallback and the "
            "rules-absent / vanilla condition"
        )
    return True, "vanilla fallback (rules absent -> CLAUDE.md) described"


def check_no_hardcode(text: str) -> tuple[bool, str]:
    """The machine rules/ structure must be detected, never hardcoded."""
    lower = text.lower()
    if "never hardcode" not in lower and "not hardcode" not in lower and "no hardcode" not in lower:
        return False, "no-hardcode clause ('never hardcode the machine's rules/ structure') missing"
    if "[ -d" not in text and "detect" not in lower:
        return False, "detection mechanism ([ -d \"$HOME/.claude/rules\" ] / detect) not described"
    return True, "no-hardcode + detect-the-catalogue clause present"


def check_thin_pointer(text: str) -> tuple[bool, str]:
    """Thin pointer + backing detail must be described for the catalogue channel."""
    lower = text.lower()
    if "thin pointer" not in lower and "one-line pointer" not in lower:
        return False, "thin-pointer routing not described"
    if "detail" not in lower:
        return False, "backing detail (catalogue holds the detail) not described"
    return True, "thin pointer + backing detail described"


def check_not_fourth_site(text: str) -> tuple[bool, str]:
    """The routing must be framed as a channel mapping, NOT a fourth landfill site."""
    lower = text.lower()
    if "not a fourth site" not in lower and "no new site" not in lower:
        return False, (
            "routing not framed as 'not a fourth site' — a future reader may mistake "
            "the rules channel for a new landfill site"
        )
    return True, "routing framed as a channel mapping, not a fourth site"


_CHECKS = [
    check_stance_voice_to_claude_md,
    check_workrule_to_rules,
    check_vanilla_fallback,
    check_no_hardcode,
    check_thin_pointer,
    check_not_fourth_site,
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
**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):**
- judgment / expression (stance·voice) -> the top-level ~/.claude/CLAUDE.md persona block.
- work-rule (how you do the work) -> the machine work-rule catalogue ~/.claude/rules
  if it exists; otherwise fall back to ~/.claude/CLAUDE.md.

The fallback is non-negotiable: never hardcode the machine's rules/ structure. Detect it
([ -d "$HOME/.claude/rules" ]) and degrade to CLAUDE.md on a vanilla machine where
~/.claude/rules is absent.

Thin pointer + backing detail: put the detail in the catalogue and keep ~/.claude/CLAUDE.md
to at most a one-line pointer / thin pointer.
"""

# Regression of the exact bug G28 fixes: SOFT always -> CLAUDE.md, no rules routing,
# no fallback, no no-hardcode clause.
_FAILING = """\
Tier folds into the site: HARD => hook, SOFT => CLAUDE.md. A SOFT rule is always a
CLAUDE.md reminder appended as one prose line.
"""


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    for check in _CHECKS:
        ok, _ = check(_PASSING)
        cases.append((f"passing: {check.__name__}", ok))

    # On the pre-G28 fixture, every rules/fallback/hardcode claim must be absent.
    for check in (
        check_workrule_to_rules,
        check_vanilla_fallback,
        check_no_hardcode,
        check_thin_pointer,
        check_not_fourth_site,
    ):
        ok, _ = check(_FAILING)
        cases.append((f"failing: {check.__name__} (expect FAIL)", not ok))

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
    print(f"OK: all {passed} add-policy-routing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
