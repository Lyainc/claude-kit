#!/usr/bin/env python3
"""Detect trigger-phrase regressions in thinking-tools agent descriptions.

Sibling to thinking-tools/scripts/test/check-trigger-regression.py, which
already guards `thinking-tools/skills/*/SKILL.md`. #471's face table lists
`thinking-tools/agents/*.md` as a SEPARATE, unguarded row (1 file:
thinking-facilitator.md) — this script fills that gap.

The agent description has no `Trigger when user mentions:` block (the skill
convention) nor a `KR/EN triggers:` label (the vault-bridge/OVM convention).
Its only structured trigger surface is an inline illustrative example —
`For a single strong-signal trigger (e.g., '구체화', '검사해줘', '반증해줘')` —
so that is what this extractor pulls, matching the file's actual shape
instead of forcing an unrelated marker onto it.

Output is a WARNING report, not a hard gate: some removals are intentional
example pruning. The reviewer decides. Exit code 1 signals "removals found".

Usage:
    python3 check-agent-trigger-regression.py <BASE_REF>
    python3 check-agent-trigger-regression.py <BASE_REF> <HEAD_REF>
    python3 check-agent-trigger-regression.py --self-test
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

AGENT_GLOB = "thinking-tools/agents/*.md"

# test/ -> scripts/ -> thinking-tools/ -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]

_EG_RE = re.compile(r"e\.g\.,\s*(.*?)\)")
_QUOTED_RE = re.compile(r"'([^']+)'")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def extract_triggers(agent_text: str, label: str = "") -> set[str]:
    """Pull the `(e.g., '...', '...')` illustrative trigger examples out of an
    agent .md's `description: |` block.

    NOTE: Only handles this file's actual shape (an inline `e.g.,` parenthetical
    of single-quoted phrases). A description with no `e.g.,` clause returns an
    empty set silently.
    """
    fm_match = re.match(r"^---\n(.*?)\n---", agent_text, re.DOTALL)
    if not fm_match:
        return set()
    frontmatter = fm_match.group(1)

    eg_match = _EG_RE.search(frontmatter)
    if not eg_match:
        if label:
            print(
                f"  WARNING: {label}: no `(e.g., '...')` trigger-example clause "
                f"found — triggers not extracted",
                file=sys.stderr,
            )
        return set()

    return set(_QUOTED_RE.findall(eg_match.group(1)))


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
    pat = re.compile(r"^thinking-tools/agents/[^/]+\.md$")
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
            print(f"  [{agent}] {len(removed)} trigger example(s) dropped:")
            for t in sorted(removed):
                print(f"      - {t}")
            total_removed += len(removed)

    print()
    if total_removed:
        print(f"RESULT: {total_removed} trigger example removal(s) found — review whether intentional.")
        return 1
    print("RESULT: no trigger example removals.")
    return 0


def _self_test() -> int:
    before = """---
name: thinking-facilitator
description: |
  Facilitator agent.

  For a single strong-signal trigger (e.g., '구체화', '검사해줘', '반증해줘'),
  invoke the matching skill directly without facilitator routing.
model: sonnet
---
body
"""
    after = """---
name: thinking-facilitator
description: |
  Facilitator agent.

  For a single strong-signal trigger (e.g., '구체화', '반증해줘'),
  invoke the matching skill directly without facilitator routing.
model: sonnet
---
body
"""
    cases = []

    b = extract_triggers(before)
    a = extract_triggers(after)

    cases.append(("example trigger captured", "구체화" in b))
    cases.append(("all three examples captured", len(b) == 3))
    removed = b - a
    cases.append(("detects removal", "검사해줘" in removed))
    cases.append(("retained example not flagged", "구체화" not in removed))

    no_eg = """---
name: other-agent
description: |
  No illustrative examples here at all.
model: sonnet
---
body
"""
    cases.append(("no e.g. clause yields empty set", extract_triggers(no_eg) == set()))

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
