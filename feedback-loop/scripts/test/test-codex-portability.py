#!/usr/bin/env python3
"""Regression checks for feedback-loop's supported Codex contracts."""

from __future__ import annotations

import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[3]
_SKILLS = _ROOT / "feedback-loop" / "skills"

_REQUIRED = {
    "retro": (
        "Claude hook telemetry is unavailable in Codex.",
        "current conversation's observable waste",
        "Do not run `stamp`, `report.py`,\n`sequence.py`, or `emit`",
        "normal user confirmation before `gh issue create`",
    ),
    "distill": (
        "never `~/.claude`",
        "continue with `add-policy`'s Codex storage branch",
        "separate one-click confirmation",
    ),
    "add-policy": (
        'CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"',
        "$CODEX_ROOT/AGENTS.md",
        "existing shared catalogue entry",
        "declared managed source",
        "same exact-diff approval",
        "$HOME/.agents/skills/<name>/SKILL.md",
        "$CODEX_ROOT/hooks.json",
        "never silently grant trust.",
    ),
}

_FORBIDDEN = {
    "retro": ("Unsupported in Codex:",),
    "distill": ("Persistence unavailable in Codex:",),
    "add-policy": ("Unsupported in Codex:",),
}


def _portability_section(text: str) -> str:
    start = text.find("## Codex Portability")
    if start < 0:
        return ""
    end = text.find("\n# ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def check(skill: str, text: str) -> list[str]:
    section = _portability_section(text)
    section = " ".join(section.split())
    errors = [
        f"{skill}: missing {phrase!r}"
        for phrase in _REQUIRED[skill]
        if " ".join(phrase.split()) not in section
    ]
    errors.extend(
        f"{skill}: retains {phrase!r}"
        for phrase in _FORBIDDEN[skill]
        if " ".join(phrase.split()) in section
    )
    return errors


def _live_texts() -> dict[str, str]:
    return {skill: (_SKILLS / skill / "SKILL.md").read_text(encoding="utf-8") for skill in _REQUIRED}


def _self_test() -> int:
    texts = {
        skill: "## Codex Portability\n" + "\n".join(required) + "\n# body\n"
        for skill, required in _REQUIRED.items()
    }
    cases = [("complete contracts pass", not any(check(skill, text) for skill, text in texts.items()))]
    for skill, phrase in (("retro", _REQUIRED["retro"][1]), ("distill", _REQUIRED["distill"][1]),
                          ("add-policy", _REQUIRED["add-policy"][1])):
        cases.append((f"{skill} contract loss fails", bool(check(skill, texts[skill].replace(phrase, "")))))
    for label, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}")
    if not all(ok for _, ok in cases):
        return 1
    print(f"OK: all {len(cases)} Codex feedback-loop portability self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        return _self_test()
    if argv:
        print("usage: test-codex-portability.py [--self-test]", file=sys.stderr)
        return 2
    errors = [error for skill, text in _live_texts().items() for error in check(skill, text)]
    if errors:
        print("FAIL: Codex feedback-loop portability")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("OK: all 3 Codex feedback-loop portability contracts passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
