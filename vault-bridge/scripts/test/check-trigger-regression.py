#!/usr/bin/env python3
"""Detect trigger-phrase regressions in vault-bridge agent frontmatter descriptions.

Sibling to thinking-tools/scripts/test/check-trigger-regression.py, adapted for
vault-bridge's agent format: a single-line quoted `description: "..."` (not a
`description: |` block scalar) whose trigger phrases are labeled inline as
"KR triggers: '...', ... EN triggers: '...', ...". When that description is
edited, an individual trigger phrase can be silently dropped — this script
extracts the KR/EN trigger sets and diffs a base git ref against the working
tree (or a head ref), reporting anything that disappeared.

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

AGENT_GLOB = "vault-bridge/agents/*.md"

# test/ -> scripts/ -> vault-bridge/ -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]

_DESC_RE = re.compile(r'^description:\s*"(.*)"\s*$', re.MULTILINE)
_KR_RE = re.compile(r"KR triggers:\s*(.*?)(?:\s*EN triggers:|$)")
# Anchored to the quoted, comma-separated trigger list itself (not `.*$`) so trailing
# prose after the list (e.g. a future "Notes: ..." clause) is never silently absorbed.
_EN_RE = re.compile(r"EN triggers:\s*((?:'[^']*'|\"[^\"]*\")(?:,\s*(?:'[^']*'|\"[^\"]*\"))*)")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def extract_triggers(agent_text: str, label: str = "") -> set[str]:
    """Pull KR/EN trigger phrases out of an agent .md's frontmatter description.

    NOTE: Only handles the single-line `description: "..."` quoted-scalar style
    (the only style vault-bridge agents currently use). A block-scalar (`|`) or
    multi-line description returns an empty set silently.
    """
    fm_match = re.match(r"^---\n(.*?)\n---", agent_text, re.DOTALL)
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
    return sorted(str(p.relative_to(_REPO_ROOT)) for p in _REPO_ROOT.glob(AGENT_GLOB))


def _list_agent_paths(ref: str | None) -> list[str]:
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
    pat = re.compile(r"^vault-bridge/agents/[^/]+\.md$")
    return sorted(line for line in result.stdout.splitlines() if pat.match(line))


def compare(base_ref: str, head_ref: str | None) -> int:
    if not _ref_exists(base_ref):
        print(f"ERROR: base ref '{base_ref}' not found in this repo.", file=sys.stderr)
        return 2
    if head_ref is not None and not _ref_exists(head_ref):
        print(f"ERROR: head ref '{head_ref}' not found in this repo.", file=sys.stderr)
        return 2
    paths = _list_agent_paths(base_ref) or _list_agent_paths(None)
    total_removed = 0
    print(f"Trigger regression check: {base_ref} -> {head_ref or 'working tree'}\n")
    for path in paths:
        base_text = _git_show(base_ref, path)
        if base_text is None:
            continue  # agent did not exist at base — nothing to regress
        head_text = _git_show(head_ref, path) if head_ref else _read_working_tree(path)
        if head_text is None:
            print(f"  {path}: REMOVED FILE (agent deleted)")
            total_removed += 1
            continue
        removed = extract_triggers(base_text, path) - extract_triggers(head_text, path)
        if removed:
            agent = path.split("/")[-1]
            print(f"  [{agent}] {len(removed)} trigger(s) dropped:")
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
description: "Some purpose line about ('what do we know about X'). KR triggers: '노트 찾아줘', '관련 자료', '검색해줘'. EN triggers: 'vault search', 'find in vault', 'domain context'."
model: haiku
---
body
"""
    after = """---
name: demo
description: "Some purpose line about ('what do we know about X'). KR triggers: '노트 찾아줘', '검색해줘'. EN triggers: 'vault search', 'domain context'."
model: haiku
---
body
"""
    cases = []

    b = extract_triggers(before)
    a = extract_triggers(after)

    cases.append(("KR trigger captured", "노트 찾아줘" in b))
    cases.append(("EN trigger captured", "vault search" in b))
    cases.append(("prose example quote excluded", "what do we know about X" not in b))
    removed = b - a
    cases.append(("detects KR removal", "관련 자료" in removed))
    cases.append(("detects EN removal", "find in vault" in removed))
    cases.append(("retained KR trigger not flagged", "노트 찾아줘" not in removed))
    cases.append(("retained EN trigger not flagged", "vault search" not in removed))

    # #373: a trailing clause after the EN trigger list must not be absorbed as noise.
    trailing_clause = """---
name: demo
description: "Purpose line. KR triggers: '노트 찾아줘'. EN triggers: 'vault search', 'domain context'. Notes: internal caveat."
model: haiku
---
body
"""
    trailing = extract_triggers(trailing_clause)
    cases.append(("EN capture stops at trigger list", "vault search" in trailing))
    cases.append(("trailing clause not absorbed as a trigger",
                  not any("Notes" in t for t in trailing)))

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
