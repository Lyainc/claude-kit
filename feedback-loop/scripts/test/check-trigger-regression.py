#!/usr/bin/env python3
"""Detect trigger-phrase regressions in feedback-loop SKILL.md descriptions.

Sibling to thinking-tools/scripts/test/check-trigger-regression.py and
vault-bridge/scripts/test/check-trigger-regression.py (#471 — routing-SSOT
drift guard extended to the faces that had none). feedback-loop's skills use
a THIRD description shape: a single-line quoted `description: "..."` (like
vault-bridge) but with an inline `Trigger: <phrase>, <phrase>, ...` label
(mixed KR/EN, unquoted, comma-separated — like thinking-tools) that runs up
to the next `. Routing:` clause or end of string. Neither existing script's
regex matches this shape, so it gets its own extractor rather than a forced
reuse.

Output is a WARNING report, not a hard gate: some removals are intentional
synonym cleanup. The reviewer decides. Exit code 1 signals "removals found".

Usage:
    python3 check-trigger-regression.py <BASE_REF>
    python3 check-trigger-regression.py <BASE_REF> <HEAD_REF>
    python3 check-trigger-regression.py --self-test
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILL_GLOB = "feedback-loop/skills/*/SKILL.md"

# test/ -> scripts/ -> feedback-loop/ -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]

_DESC_RE = re.compile(r'^description:\s*"(.*)"\s*$', re.MULTILINE)
_TRIGGER_RE = re.compile(r"Trigger:\s*(.*?)(?:\.\s*Routing:|\Z)")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def extract_triggers(skill_text: str, label: str = "") -> set[str]:
    """Pull the `Trigger: ...` phrase list out of a feedback-loop SKILL.md's description.

    NOTE: Only handles the single-line quoted `description: "..."` style with
    an inline `Trigger: ...` label (the only style feedback-loop skills
    currently use). A block-scalar (`|`) description, or one with no
    `Trigger:` label at all, returns an empty set silently.
    """
    fm_match = re.match(r"^---\n(.*?)\n---", skill_text, re.DOTALL)
    if not fm_match:
        return set()

    desc_match = _DESC_RE.search(fm_match.group(1))
    if not desc_match:
        if label:
            print(
                f"  WARNING: {label}: no single-line quoted `description: \"...\"` "
                f"found — triggers not extracted (multi-line/folded style?)",
                file=sys.stderr,
            )
        return set()
    description = desc_match.group(1)

    trig_match = _TRIGGER_RE.search(description)
    if not trig_match:
        return set()

    triggers = set()
    for raw in trig_match.group(1).split(","):
        token = raw.strip('". \t')
        if len(token) >= 2:
            triggers.add(token)
    return triggers


def _ref_exists(ref: str) -> bool:
    return _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0


def _git_show(ref: str, path: str) -> str | None:
    result = _git("show", f"{ref}:{path}")
    return result.stdout if result.returncode == 0 else None


def _read_working_tree(path: str) -> str | None:
    p = _REPO_ROOT / path
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _disk_glob() -> list[str]:
    return sorted(str(p.relative_to(_REPO_ROOT)) for p in _REPO_ROOT.glob(SKILL_GLOB))


def _list_skill_paths(ref: str | None) -> list[str]:
    if ref is None:
        return _disk_glob()
    result = _git("ls-tree", "-r", "--name-only", ref)
    if result.returncode != 0:
        print(
            f"WARNING: `git ls-tree {ref}` failed; falling back to disk glob. "
            f"stderr: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return _disk_glob()
    pat = re.compile(r"^feedback-loop/skills/[^/]+/SKILL\.md$")
    return sorted(line for line in result.stdout.splitlines() if pat.match(line))


def compare(base_ref: str, head_ref: str | None) -> int:
    if not _ref_exists(base_ref):
        print(f"ERROR: base ref '{base_ref}' not found in this repo.", file=sys.stderr)
        return 2
    if head_ref is not None and not _ref_exists(head_ref):
        print(f"ERROR: head ref '{head_ref}' not found in this repo.", file=sys.stderr)
        return 2
    paths = _list_skill_paths(base_ref) or _list_skill_paths(None)
    total_removed = 0
    print(f"Trigger regression check: {base_ref} -> {head_ref or 'working tree'}\n")
    for path in paths:
        base_text = _git_show(base_ref, path)
        if base_text is None:
            continue  # skill did not exist at base — nothing to regress
        head_text = _git_show(head_ref, path) if head_ref else _read_working_tree(path)
        if head_text is None:
            print(f"  {path}: REMOVED FILE (skill deleted)")
            total_removed += 1
            continue
        removed = extract_triggers(base_text, path) - extract_triggers(head_text, path)
        if removed:
            skill = path.split("/")[-2]
            print(f"  [{skill}] {len(removed)} trigger(s) dropped:")
            for t in sorted(removed):
                print(f"      - {t}")
            total_removed += len(removed)

    print()
    if total_removed:
        print(f"RESULT: {total_removed} trigger removal(s) found — review whether intentional.")
        return 1
    print("RESULT: no trigger removals.")
    return 0


def _self_test() -> int:
    before = """---
name: demo
description: "Purpose line about the engine. Trigger: 이 규칙 추가, 정책 분류, add policy, /add-policy. Routing: distill discovers, add-policy lands."
model: inherit
---
body
"""
    after = """---
name: demo
description: "Purpose line about the engine. Trigger: 이 규칙 추가, add policy, /add-policy. Routing: distill discovers, add-policy lands."
model: inherit
---
body
"""
    cases = []

    b = extract_triggers(before)
    a = extract_triggers(after)

    cases.append(("KR trigger captured", "이 규칙 추가" in b))
    cases.append(("EN trigger captured", "add policy" in b))
    cases.append(("slash trigger captured", "/add-policy" in b))
    cases.append(("Routing clause excluded", not any("distill" in t for t in b)))
    removed = b - a
    cases.append(("detects removal", "정책 분류" in removed))
    cases.append(("retained trigger not flagged", "add policy" not in removed))

    # No trailing "Routing:" clause — trigger list runs to end of description.
    no_routing = """---
name: demo
description: "Purpose line. Trigger: 회고, 회고해줘, retro, session retrospective."
model: inherit
---
body
"""
    nr = extract_triggers(no_routing)
    cases.append(("no-Routing-clause trigger list fully captured", "session retrospective" in nr))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return _self_test()
    base_ref = argv[0]
    head_ref = argv[1] if len(argv) > 1 else None
    return compare(base_ref, head_ref)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
