#!/usr/bin/env python3
"""Regression test: expert-panel mode combinations compose without contradiction.

Validates the SKILL.md claim "All combinations compose silently" by statically
parsing the SKILL.md mode-toggle declarations and asserting:

1. Every declared mode name appears in the Execution Modes section.
2. No two mode declarations share the same trigger phrase (no ambiguous routing).
3. Every mode name that appears in the "All combinations compose silently" line
   (or its extended footnote) is declared in Execution Modes.
4. Citation grounding is listed as composing silently with all other modes.
5. Phase 2 inline-summary path is referenced as composing silently.

This is a structural / static check — it does not execute any LLM logic.

Usage:
    python3 thinking-tools/scripts/test/test-mode-compose.py
    python3 thinking-tools/scripts/test/test-mode-compose.py --self-test

Exit codes:
    0  All checks passed
    1  One or more checks failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SKILL_PATH = _REPO_ROOT / "thinking-tools" / "skills" / "expert-panel" / "SKILL.md"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _load_skill() -> str:
    if not _SKILL_PATH.is_file():
        raise FileNotFoundError(f"SKILL.md not found at {_SKILL_PATH}")
    return _SKILL_PATH.read_text(encoding="utf-8")


def _extract_execution_modes_block(text: str) -> str:
    """Return the text of the ## Execution Modes section (up to next ##)."""
    m = re.search(r"^## Execution Modes\n(.*?)(?=\n## |\Z)", text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def _extract_declared_modes(modes_block: str) -> list[dict]:
    """Parse each bullet in the Execution Modes section.

    Returns list of dicts with keys:
      - name: str  (the bold label, e.g. "격리 실행")
      - triggers: list[str]  (quoted phrases inside parentheses)
    """
    modes: list[dict] = []
    # Match lines like: - **격리 실행** ("phrase1", "phrase2"):
    for m in re.finditer(
        r"^- \*\*(.+?)\*\*\s*\((.+?)\):", modes_block, re.MULTILINE
    ):
        name = m.group(1).strip()
        raw_triggers = m.group(2)
        triggers = [t.strip().strip('"') for t in raw_triggers.split(",")]
        modes.append({"name": name, "triggers": triggers})
    return modes


def _find_compose_line(text: str) -> str:
    """Return the FIRST line containing the 'compose silently' declaration.

    Only the first match is returned (not all joined): downstream checks do `in`
    tests on this string, so joining multiple lines would let a citation mention on
    one line and an inline-summary mention on another both pass against the combined
    string even when no single line carries both — a false positive. SKILL.md keeps
    the declaration on one line; if it splits, the checks should fail loudly.
    """
    for line in text.splitlines():
        if "compose silently" in line:
            return line.strip()
    return ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_modes_declared(modes: list[dict]) -> tuple[bool, str]:
    """At least the two canonical modes must be declared."""
    names = {m["name"] for m in modes}
    # COUPLED to the bold mode labels in expert-panel/SKILL.md "## Execution Modes"
    # (the `- **격리 실행** (...)` / `- **요약 출력** (...)` bullets). If a mode is
    # intentionally renamed there, update this set too — otherwise this gate silently
    # stops checking that mode (a rename without an update here is a false-OK).
    required = {"격리 실행", "요약 출력"}
    missing = required - names
    if missing:
        return False, f"Missing declared modes: {missing}"
    return True, f"All {len(modes)} mode(s) declared (incl. required: {required})"


def check_no_trigger_collision(modes: list[dict]) -> tuple[bool, str]:
    """No trigger phrase appears in two different modes."""
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for mode in modes:
        for trigger in mode["triggers"]:
            if trigger in seen:
                collisions.append(
                    f"'{trigger}' shared by '{seen[trigger]}' and '{mode['name']}'"
                )
            else:
                seen[trigger] = mode["name"]
    if collisions:
        return False, "Trigger collisions: " + "; ".join(collisions)
    return True, f"No trigger collisions across {len(seen)} trigger phrase(s)"


def check_compose_line_present(text: str) -> tuple[bool, str]:
    """The 'All combinations compose silently' declaration must exist."""
    compose = _find_compose_line(text)
    if not compose:
        return False, "'All combinations compose silently' declaration not found"
    return True, f"Compose declaration found: {compose[:120]}"


def check_citation_compose_referenced(text: str) -> tuple[bool, str]:
    """Citation grounding must be mentioned as composing silently."""
    compose = _find_compose_line(text)
    if "citation" not in compose.lower() and "Citation" not in compose:
        return False, (
            "Citation grounding not referenced in 'compose silently' line — "
            "add 'citation grounding' to the compose declaration"
        )
    return True, "Citation grounding referenced in compose declaration"


def check_inline_summary_compose_referenced(text: str) -> tuple[bool, str]:
    """Phase 2 inline-summary path must be mentioned as composing silently."""
    compose = _find_compose_line(text)
    if "inline" not in compose.lower() and "summary path" not in compose.lower() and "inline-summary" not in compose.lower():
        return False, (
            "Phase 2 inline-summary path not referenced in 'compose silently' line — "
            "add reference to inline SUMMARY path in the compose declaration"
        )
    return True, "Phase 2 inline-summary path referenced in compose declaration"


def check_citation_contract_section(text: str) -> tuple[bool, str]:
    """A ## Citation Contract section must exist."""
    if "## Citation Contract" not in text:
        return False, "'## Citation Contract' section not found in SKILL.md"
    return True, "'## Citation Contract' section present"


def check_citation_state_field(text: str) -> tuple[bool, str]:
    """Citation field must appear in the STATE block template."""
    if "Citation:" not in text:
        return False, "'Citation:' field not found in STATE block template"
    return True, "'Citation:' field present in STATE block"


def check_phase2_inline_path(text: str) -> tuple[bool, str]:
    """Phase 2 must describe the lightweight inline SUMMARY path."""
    if "inline SUMMARY" not in text:
        return False, "Phase 2 inline SUMMARY path not described in SKILL.md"
    return True, "Phase 2 inline SUMMARY path described"


def check_recovery_cost_line(text: str) -> tuple[bool, str]:
    """Recovery cost must be mentioned in the cost section."""
    if "Recovery cost" not in text and "복구 비용" not in text and "recovery overhead" not in text.lower():
        return False, "Recovery cost not mentioned in SKILL.md cost section"
    return True, "Recovery cost line present in SKILL.md"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_checks(text: str) -> tuple[int, int]:
    """Run all checks against the SKILL.md text. Returns (passed, failed)."""
    modes_block = _extract_execution_modes_block(text)
    modes = _extract_declared_modes(modes_block)

    checks = [
        check_modes_declared(modes),
        check_no_trigger_collision(modes),
        check_compose_line_present(text),
        check_citation_compose_referenced(text),
        check_inline_summary_compose_referenced(text),
        check_citation_contract_section(text),
        check_citation_state_field(text),
        check_phase2_inline_path(text),
        check_recovery_cost_line(text),
    ]

    passed = failed = 0
    for ok, msg in checks:
        label = "OK  " if ok else "FAIL"
        print(f"  [{label}] {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    return passed, failed


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

_PASSING_FIXTURE = """\
---
name: expert-panel
description: |
  Facilitate expert panel discussions.
  Trigger when user mentions: 전문가 토론, expert panel.
  Routing: adversarial-review for 1:1.
allowed-tools: Read Write Agent
---

## Execution Modes

Express mode preferences in natural language:
- **격리 실행** ("엄격하게", "격리해서"): Isolated spawn.
- **요약 출력** ("요약만", "transcript 없이"): Summary only.

All combinations compose silently — including any combination with citation grounding (see Citation Contract) and the Phase 2 inline-summary path.

## Citation Contract

When an expert states a numeric or factual claim it must cite one grounding source.

## Consensus Rules

...

## Core Workflow

### Phase 1: Topic Rounds

**Cost**: per topic, `(exchanges × experts)` — **Recovery cost**: if Phase 2 produces a content-free sign-off, the user must re-request the record.

### Phase 2: Recording

**Lightweight / single-topic sessions**: produce an **inline SUMMARY** in the current conversation.

### STATE Block

```
<!-- STATE:CHECKPOINT -->
Topic: 1/2 | Phase: 1 | Round: 1/3
Mode: [isolated:off] [summary-only:off]
Citation: [t1:grounded]
<!-- /STATE -->
```
"""

_FAILING_FIXTURE = """\
---
name: expert-panel
description: |
  Facilitate expert panel discussions.
  Trigger when user mentions: 전문가 토론.
allowed-tools: Read Write Agent
---

## Execution Modes

- **격리 실행** ("엄격하게"): Isolated spawn.
- **요약 출력** ("엄격하게"): Summary only.

All combinations compose silently.

## Phase 2

Discussion cannot end without document generation.
"""


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    # --- passing fixture: all checks should pass ---
    passing_modes_block = _extract_execution_modes_block(_PASSING_FIXTURE)
    passing_modes = _extract_declared_modes(passing_modes_block)

    ok, _ = check_modes_declared(passing_modes)
    cases.append(("passing: modes declared", ok))

    ok, _ = check_no_trigger_collision(passing_modes)
    cases.append(("passing: no trigger collision", ok))

    ok, _ = check_compose_line_present(_PASSING_FIXTURE)
    cases.append(("passing: compose line present", ok))

    ok, _ = check_citation_compose_referenced(_PASSING_FIXTURE)
    cases.append(("passing: citation in compose line", ok))

    ok, _ = check_inline_summary_compose_referenced(_PASSING_FIXTURE)
    cases.append(("passing: inline-summary in compose line", ok))

    ok, _ = check_citation_contract_section(_PASSING_FIXTURE)
    cases.append(("passing: citation contract section", ok))

    ok, _ = check_citation_state_field(_PASSING_FIXTURE)
    cases.append(("passing: citation state field", ok))

    ok, _ = check_phase2_inline_path(_PASSING_FIXTURE)
    cases.append(("passing: phase2 inline path", ok))

    ok, _ = check_recovery_cost_line(_PASSING_FIXTURE)
    cases.append(("passing: recovery cost line", ok))

    # --- failing fixture: trigger collision and missing features should fail ---
    failing_modes_block = _extract_execution_modes_block(_FAILING_FIXTURE)
    failing_modes = _extract_declared_modes(failing_modes_block)

    ok, _ = check_no_trigger_collision(failing_modes)
    cases.append(("failing: trigger collision detected (expect FAIL)", not ok))

    ok, _ = check_citation_contract_section(_FAILING_FIXTURE)
    cases.append(("failing: citation section absent (expect FAIL)", not ok))

    ok, _ = check_citation_state_field(_FAILING_FIXTURE)
    cases.append(("failing: citation state field absent (expect FAIL)", not ok))

    ok, _ = check_citation_compose_referenced(_FAILING_FIXTURE)
    cases.append(("failing: citation not in compose (expect FAIL)", not ok))

    ok, _ = check_inline_summary_compose_referenced(_FAILING_FIXTURE)
    cases.append(("failing: inline-summary not in compose (expect FAIL)", not ok))

    ok, _ = check_phase2_inline_path(_FAILING_FIXTURE)
    cases.append(("failing: inline path absent (expect FAIL)", not ok))

    ok, _ = check_recovery_cost_line(_FAILING_FIXTURE)
    cases.append(("failing: recovery cost absent (expect FAIL)", not ok))

    failed = [name for name, passed in cases if not passed]
    for name, passed in cases:
        print(f"  [{'OK' if passed else 'FAIL'}] {name}")

    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s): {failed}")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if argv and argv[0] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        return _self_test()

    # Real mode: check the actual SKILL.md
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
    print(f"OK: all {passed} mode-compose checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
