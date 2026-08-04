#!/usr/bin/env python3
"""test-auto-release-trigger.py — pins the #493 fix in auto-release.yml.

Before 2026-08-04 the workflow only watched `pull_request: types: [closed]`, so a
`release` label added AFTER a PR merged fired no event at all — not `pull_request:closed`
(already fired), not `push:main` (no new commit). The fix adds `labeled` to `types:`; the
job-level `if:` (merged == true + labels contains `release`) already handles that event
correctly without further changes, since GitHub's `labeled` payload reflects the label set
AFTER the add.

This is a static-content check on the live workflow YAML (no PyYAML — project policy bans
it, and check-ci-coverage.py's own YAML handling is the same regex-over-text approach):
asserts `labeled` is present in `pull_request.types`, asserts the `if:` still requires
`merged == true` and a `release` label (so a later edit can't silently regress the
condition that makes the new `labeled` event safe to fire on), and asserts the `decide`
step still passes `--labeled` unconditionally for any `pull_request` event.

Usage:
    python3 test-auto-release-trigger.py
    python3 test-auto-release-trigger.py --self-test
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "auto-release.yml"


def check_trigger_types(text: str) -> list[tuple[str, bool]]:
    """Assert `pull_request.types` includes both `closed` and `labeled`."""
    m = re.search(r"pull_request:\s*\n\s*(?:#.*\n\s*)*types:\s*\[([^\]]+)\]", text)
    if not m:
        return [("pull_request.types line found", False)]
    types = {t.strip() for t in m.group(1).split(",")}
    return [
        ("pull_request.types found", True),
        ("`closed` present (merge-time label)", "closed" in types),
        ("`labeled` present (#493 post-merge label)", "labeled" in types),
    ]


def check_if_condition(text: str) -> list[tuple[str, bool]]:
    """Assert the decide job's `if:` still requires merged + the release label.

    Without `merged == true`, a `labeled` event on a still-OPEN PR would also fire and
    release whatever currently sits on main — unrelated to the (unmerged) PR that got
    labeled. Without the `contains(...)` clause, ANY label on ANY merged PR would fire.
    """
    m = re.search(r"jobs:\s*\n\s*decide:.*?if:\s*>-\s*\n(.*?)\n\s*runs-on:", text, re.DOTALL)
    if not m:
        return [("decide job `if:` block found", False)]
    cond = m.group(1)
    return [
        ("decide job `if:` block found", True),
        ("requires `merged == true`",
         "github.event.pull_request.merged == true" in cond),
        ("requires the `release` label",
         "contains(github.event.pull_request.labels.*.name, 'release')" in cond),
    ]


def check_decide_step_unconditional_labeled(text: str) -> list[tuple[str, bool]]:
    """Assert `--labeled` is still passed for ANY pull_request event (closed or labeled),
    not narrowed back down to only `closed` — the job-level `if:` above is what actually
    gates correctness, so this step must stay unconditional on event TYPE."""
    m = re.search(r'if \[ "\$\{\{ github\.event_name \}\}" = "pull_request" \]; then LABELED=\(--labeled\); fi', text)
    return [("decide step passes --labeled for any pull_request event", bool(m))]


def run_checks(text: str) -> list[tuple[str, bool]]:
    return (
        check_trigger_types(text)
        + check_if_condition(text)
        + check_decide_step_unconditional_labeled(text)
    )


def _self_test() -> int:
    good = """
on:
  pull_request:
    types: [closed, labeled]
    branches: [main]
  push:
    branches: [main]

jobs:
  decide:
    if: >-
      github.event_name == 'push' ||
      (github.event.pull_request.merged == true &&
       github.event.pull_request.base.ref == 'main' &&
       contains(github.event.pull_request.labels.*.name, 'release'))
    runs-on: ubuntu-latest
    steps:
      - name: Decide
        run: |
          LABELED=()
          if [ "${{ github.event_name }}" = "pull_request" ]; then LABELED=(--labeled); fi
"""
    regressed_types = good.replace("types: [closed, labeled]", "types: [closed]")
    regressed_if = good.replace(
        "github.event.pull_request.merged == true &&\n       ", ""
    )
    regressed_step = good.replace(
        'if [ "${{ github.event_name }}" = "pull_request" ]; then LABELED=(--labeled); fi',
        'if [ "${{ github.event_name }}" = "closed" ]; then LABELED=(--labeled); fi',
    )

    cases = []

    def add(label, results):
        for name, ok in results:
            cases.append((f"{label}: {name}", ok))

    add("good fixture", run_checks(good))
    labeled_present = dict(check_trigger_types(regressed_types))
    cases.append(("regressed-types fixture: `labeled` absent detected",
                  labeled_present.get("`labeled` present (#493 post-merge label)") is False))
    merged_present = dict(check_if_condition(regressed_if))
    cases.append(("regressed-if fixture: missing merged==true detected",
                  merged_present.get("requires `merged == true`") is False))
    step_present = dict(check_decide_step_unconditional_labeled(regressed_step))
    cases.append(("regressed-step fixture: narrowed condition detected",
                  step_present.get("decide step passes --labeled for any pull_request event") is False))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--self-test":
        return _self_test()

    if not _WORKFLOW_PATH.is_file():
        print(f"ERROR: {_WORKFLOW_PATH} not found", file=sys.stderr)
        return 2

    text = _WORKFLOW_PATH.read_text(encoding="utf-8")
    results = run_checks(text)
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nFAILED: {len(failed)} check(s) — #493's post-merge label fix regressed")
        return 1
    print(f"\nOK: auto-release.yml #493 fix intact ({len(results)} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
