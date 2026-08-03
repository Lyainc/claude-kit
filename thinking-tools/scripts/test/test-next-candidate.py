#!/usr/bin/env python3
"""Unit tests for next-candidate.py's chain_depth()/top_areas() edge cases (#521).

test-completion-condition-hook.sh only exercises these through single-commit e2e fixtures
routed via the hook, so three edges chain_depth's own docstring documents as load-bearing
were never directly asserted: zero commits, a bare root file's `·` prefix, and multi-area
branching (including a commit whose changed files span more than one area).

Usage: python3 thinking-tools/scripts/test/test-next-candidate.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_PATH = _REPO_ROOT / "thinking-tools" / "scripts" / "next-candidate.py"

_spec = importlib.util.spec_from_file_location("next_candidate", _SCRIPT_PATH)
nc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nc)


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )


def _commit(cwd, paths, msg):
    """Write each path with placeholder content and commit them together."""
    for rel in paths:
        p = Path(cwd) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel)
    _git(cwd, "add", "-A")
    _git(cwd, "commit", "-q", "-m", msg)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _repo():
    d = tempfile.mkdtemp(prefix="test-next-candidate-")
    _git(d, "init", "-q")
    return d


def check_top_areas() -> list[str]:
    """A bare root file is its own `·`-prefixed area, never merged with a same-name dir."""
    failures = []
    cases = [
        (["README.md"], {"·README.md"}),
        (["thinking-tools/scripts/x.py"], {"thinking-tools"}),
        (["README.md", "thinking-tools/scripts/x.py"], {"·README.md", "thinking-tools"}),
        (["a/b.py", "a/c.py"], {"a"}),
        ([""], set()),
    ]
    for paths, expected in cases:
        got = nc.top_areas(paths)
        if got != expected:
            failures.append(f"top_areas({paths!r}): expected {expected}, got {got}")
    return failures


def check_zero_commits() -> list[str]:
    """A repo with no commits at all must not be mistaken for a broken-but-populated one."""
    failures = []
    cwd = _repo()
    depth, areas, shas = nc.chain_depth(cwd, 5)
    if (depth, areas, shas) != (0, [], []):
        failures.append(f"zero commits: expected (0, [], []), got {(depth, areas, shas)}")
    return failures


def check_multi_area_branching() -> list[str]:
    """Consecutive same-area commits count; the first non-overlapping commit stops the chain."""
    failures = []
    cwd = _repo()
    c1 = _commit(cwd, ["docs/a.md"], "c1")
    c2 = _commit(cwd, ["thinking-tools/x.py"], "c2")
    c3 = _commit(cwd, ["thinking-tools/y.py"], "c3")
    depth, areas, shas = nc.chain_depth(cwd, 3)
    if depth != 2:
        failures.append(f"multi-area branching: expected depth 2, got {depth}")
    if areas != ["thinking-tools"]:
        failures.append(f"multi-area branching: expected head areas ['thinking-tools'], got {areas}")
    # Each entry is "abbrev-sha subject" (chain_depth returns git log's raw header line).
    # The abbreviation's length follows core.abbrev (not always 7), so compare the sha token
    # as a prefix of the full sha rather than assuming a fixed width.
    expected_full = [c3, c2]
    got_shas = [s.split(" ", 1)[0] for s in shas]
    if len(got_shas) != 2 or not all(f.startswith(s) for f, s in zip(expected_full, got_shas)):
        failures.append(f"multi-area branching: expected shas prefixing {expected_full}, got {got_shas}")
    return failures


def check_partial_overlap() -> list[str]:
    """A commit touching two areas still counts if only one of them matches the head area."""
    failures = []
    cwd = _repo()
    _commit(cwd, ["docs/old.md"], "d1")
    _commit(cwd, ["thinking-tools/p.py", "docs/q.md"], "d2")
    _commit(cwd, ["thinking-tools/r.py"], "d3")
    depth, areas, _ = nc.chain_depth(cwd, 3)
    if depth != 2:
        failures.append(f"partial overlap: expected depth 2 (d3, d2 share 'thinking-tools'), got {depth}")
    if areas != ["thinking-tools"]:
        failures.append(f"partial overlap: expected head areas ['thinking-tools'], got {areas}")
    return failures


def check_root_file_prefix_breaks_chain() -> list[str]:
    """A root file's `·`-prefixed area must not accidentally intersect a real top-level dir."""
    failures = []
    cwd = _repo()
    _commit(cwd, ["nested/thing.py"], "e1")
    _commit(cwd, ["README.md"], "e2")
    depth, areas, _ = nc.chain_depth(cwd, 2)
    if depth != 1:
        failures.append(f"root-file prefix: expected depth 1 (breaks at 'nested'), got {depth}")
    if areas != ["·README.md"]:
        failures.append(f"root-file prefix: expected head areas ['·README.md'], got {areas}")
    return failures


def main() -> int:
    checks = [
        check_top_areas,
        check_zero_commits,
        check_multi_area_branching,
        check_partial_overlap,
        check_root_file_prefix_breaks_chain,
    ]
    failures = []
    for check in checks:
        failures += check()

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: all {len(checks)} test-next-candidate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
