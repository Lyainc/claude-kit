#!/usr/bin/env python3
"""Detect trigger-phrase regressions in vault-bridge SKILL.md descriptions.

Sibling to vault-bridge/scripts/test/check-trigger-regression.py, which
guards `vault-bridge/agents/*.md`. #471's face table lists
`vault-bridge/skills/*/SKILL.md` (3 items) as a SEPARATE, unguarded row —
this script fills that gap, named check-SKILL-trigger-regression.py to avoid
colliding with the sibling agent-checking script in the same directory.

Of the 4 vault-bridge skills, 3 (`vault-commit`, `vault-link`,
`vault-manifest-refresh`) carry `disable-model-invocation: true` — they are
explicit slash-command-only, so there is no natural-language trigger surface
to regress, and this script structurally skips them rather than inventing
one. `vault-save` has no such flag and carries the same inline
`KR triggers: '...'. EN triggers: '...'.` label the sibling agent script
already parses, so it reuses that exact extractor.

Output is a WARNING report, not a hard gate: some removals are intentional
synonym cleanup. The reviewer decides. Exit code 1 signals "removals found".

Usage:
    python3 check-skill-trigger-regression.py <BASE_REF>
    python3 check-skill-trigger-regression.py <BASE_REF> <HEAD_REF>
    python3 check-skill-trigger-regression.py --self-test
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILL_GLOB = "vault-bridge/skills/*/SKILL.md"

# test/ -> scripts/ -> vault-bridge/ -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]

_DESC_RE = re.compile(r'^description:\s*"(.*)"\s*$', re.MULTILINE)
_KR_RE = re.compile(r"KR triggers:\s*(.*?)(?:\s*EN triggers:|$)")
_EN_RE = re.compile(r"EN triggers:\s*(['\"].*['\"])")
_DISABLE_INVOCATION_RE = re.compile(r"^disable-model-invocation:\s*true\s*$", re.MULTILINE)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _frontmatter(text: str) -> str | None:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    return m.group(1) if m else None


def is_explicit_invoke_only(skill_text: str) -> bool:
    """True when `disable-model-invocation: true` is set — no auto-trigger surface exists."""
    fm = _frontmatter(skill_text)
    return bool(fm and _DISABLE_INVOCATION_RE.search(fm))


def extract_triggers(skill_text: str, label: str = "") -> set[str]:
    """Pull KR/EN trigger phrases out of a vault-bridge SKILL.md description.

    NOTE: Only handles the single-line quoted `description: "..."` style with
    an inline `KR triggers: ...`/`EN triggers: ...` label (the shape
    `vault-save/SKILL.md` uses). A description with no such label returns an
    empty set silently — this is the expected, non-error case for the 3
    explicit-invoke-only skills, which `compare()` filters out before ever
    calling this.
    """
    fm = _frontmatter(skill_text)
    if fm is None:
        return set()

    desc_match = _DESC_RE.search(fm)
    if not desc_match:
        if label:
            print(
                f"  WARNING: {label}: no single-line quoted `description: \"...\"` "
                f"found — triggers not extracted (multi-line/folded style?)",
                file=sys.stderr,
            )
        return set()
    description = desc_match.group(1)

    triggers = set()
    for lang_re in (_KR_RE, _EN_RE):
        m = lang_re.search(description)
        if not m:
            continue
        for raw in m.group(1).split(","):
            token = raw.strip("'\". \t")
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
    pat = re.compile(r"^vault-bridge/skills/[^/]+/SKILL\.md$")
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
    skipped = []
    print(f"Trigger regression check: {base_ref} -> {head_ref or 'working tree'}\n")
    for path in paths:
        base_text = _git_show(base_ref, path)
        if base_text is None:
            continue  # skill did not exist at base — nothing to regress
        if is_explicit_invoke_only(base_text):
            skipped.append(path)
            continue
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

    if skipped:
        print(f"  (skipped {len(skipped)} explicit-invoke-only skill(s), no trigger surface: "
              f"{', '.join(p.split('/')[-2] for p in skipped)})")

    print()
    if total_removed:
        print(f"RESULT: {total_removed} trigger removal(s) found — review whether intentional.")
        return 1
    print("RESULT: no trigger removals.")
    return 0


def _self_test() -> int:
    before = """---
name: vault-save
description: "Save reference material. KR triggers: '볼트에 저장', '메모해줘', '자료 저장'. EN triggers: 'save to vault', 'vault save'."
allowed-tools: Read Write Bash Glob
---
body
"""
    after = """---
name: vault-save
description: "Save reference material. KR triggers: '볼트에 저장', '자료 저장'. EN triggers: 'save to vault'."
allowed-tools: Read Write Bash Glob
---
body
"""
    cases = []

    b = extract_triggers(before)
    a = extract_triggers(after)

    cases.append(("KR trigger captured", "볼트에 저장" in b))
    cases.append(("EN trigger captured", "save to vault" in b))
    removed = b - a
    cases.append(("detects KR removal", "메모해줘" in removed))
    cases.append(("detects EN removal", "vault save" in removed))
    cases.append(("retained trigger not flagged", "볼트에 저장" not in removed))

    explicit_invoke = """---
name: vault-commit
description: "Commit uncommitted vault changes to git. Invoke via /vault-commit."
allowed-tools: Bash AskUserQuestion
disable-model-invocation: true
---
body
"""
    cases.append(("explicit-invoke-only skill detected", is_explicit_invoke_only(explicit_invoke)))
    cases.append(("vault-save not flagged as explicit-invoke-only", not is_explicit_invoke_only(before)))

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
