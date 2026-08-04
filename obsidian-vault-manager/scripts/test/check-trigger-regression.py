#!/usr/bin/env python3
"""Detect trigger-phrase regressions in obsidian-vault-manager descriptions.

Sibling to thinking-tools/scripts/test/check-trigger-regression.py and
vault-bridge/scripts/test/check-trigger-regression.py (#471 — routing-SSOT
drift guard extended to the faces that had none). Covers BOTH
`obsidian-vault-manager/skills/*/SKILL.md` and `obsidian-vault-manager/agents/*.md`
in one script, matching the issue's face table which lists them as one
5+2-item row.

The plugin's descriptions are not uniform: `wiki/SKILL.md` carries an inline
`KR triggers: '...'. EN triggers: '...'.` label (the same shape
vault-bridge/agents uses), but `audit`/`base`/`vault-file-organizer` carry no
structured trigger list at all — only prose + `Example: ...` usage lines.
Reusing vault-bridge's KR/EN-triggers regex is correct for files that HAVE
that label and silently (with a stderr WARNING) extracts an empty set for
files that don't, exactly like the sibling scripts already do for their own
non-matching styles — never a false trigger removal, never a crash.

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

GLOBS = ("obsidian-vault-manager/skills/*/SKILL.md", "obsidian-vault-manager/agents/*.md")

# test/ -> scripts/ -> obsidian-vault-manager/ -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]

_DESC_RE = re.compile(r'^description:\s*"(.*)"\s*$', re.MULTILINE)
_KR_RE = re.compile(r"KR triggers:\s*(.*?)(?:\s*EN triggers:|$)")
_EN_RE = re.compile(r"EN triggers:\s*(['\"].*['\"])")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def extract_triggers(text: str, label: str = "") -> set[str]:
    """Pull KR/EN trigger phrases out of a SKILL.md/agent .md description.

    NOTE: Only handles the single-line quoted `description: "..."` style
    with an inline `KR triggers: ...`/`EN triggers: ...` label. Files with no
    such label (audit, base, vault-file-organizer as of #471) return an
    empty set silently — there is no structured trigger list to regress.
    """
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
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
    paths = []
    for glob in GLOBS:
        paths.extend(str(p.relative_to(_REPO_ROOT)) for p in _REPO_ROOT.glob(glob))
    return sorted(paths)


def _list_paths(ref: str | None) -> list[str]:
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
    pats = [
        re.compile(r"^obsidian-vault-manager/skills/[^/]+/SKILL\.md$"),
        re.compile(r"^obsidian-vault-manager/agents/[^/]+\.md$"),
    ]
    return sorted(
        line for line in result.stdout.splitlines() if any(p.match(line) for p in pats)
    )


def compare(base_ref: str, head_ref: str | None) -> int:
    if not _ref_exists(base_ref):
        print(f"ERROR: base ref '{base_ref}' not found in this repo.", file=sys.stderr)
        return 2
    if head_ref is not None and not _ref_exists(head_ref):
        print(f"ERROR: head ref '{head_ref}' not found in this repo.", file=sys.stderr)
        return 2
    paths = _list_paths(base_ref) or _list_paths(None)
    total_removed = 0
    print(f"Trigger regression check: {base_ref} -> {head_ref or 'working tree'}\n")
    for path in paths:
        base_text = _git_show(base_ref, path)
        if base_text is None:
            continue  # file did not exist at base — nothing to regress
        head_text = _git_show(head_ref, path) if head_ref else _read_working_tree(path)
        if head_text is None:
            print(f"  {path}: REMOVED FILE")
            total_removed += 1
            continue
        removed = extract_triggers(base_text, path) - extract_triggers(head_text, path)
        if removed:
            name = path.split("/")[-2] if path.endswith("SKILL.md") else path.split("/")[-1]
            print(f"  [{name}] {len(removed)} trigger(s) dropped:")
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
name: wiki
description: "Compile domain knowledge. Examples: '/wiki foo'. KR triggers: 'wiki에 정리', '위키 페이지로', '알아낸 거 저장'. EN triggers: 'compile to wiki', 'save to wiki'."
allowed-tools: Read Write Bash Glob
---
body
"""
    after = """---
name: wiki
description: "Compile domain knowledge. Examples: '/wiki foo'. KR triggers: 'wiki에 정리', '알아낸 거 저장'. EN triggers: 'compile to wiki'."
allowed-tools: Read Write Bash Glob
---
body
"""
    cases = []

    b = extract_triggers(before)
    a = extract_triggers(after)

    cases.append(("KR trigger captured", "wiki에 정리" in b))
    cases.append(("EN trigger captured", "compile to wiki" in b))
    cases.append(("Example prose excluded", "/wiki foo" not in b))
    removed = b - a
    cases.append(("detects KR removal", "위키 페이지로" in removed))
    cases.append(("detects EN removal", "save to wiki" in removed))
    cases.append(("retained trigger not flagged", "wiki에 정리" not in removed))

    # No structured trigger label at all (audit/base/vault-file-organizer shape) —
    # must return empty, not crash, and never register a false regression.
    no_label = """---
name: audit
description: "Scan the vault for structural defects. Example: '/audit' or '/audit --deep'"
allowed-tools: Read
---
body
"""
    cases.append(("no-trigger-label file yields empty set", extract_triggers(no_label) == set()))

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
