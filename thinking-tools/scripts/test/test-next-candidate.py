#!/usr/bin/env python3
"""Unit tests for next-candidate.py's chain_depth()/top_areas() edge cases (#521).

test-next-goal-hook.sh only exercises these through single-commit e2e fixtures
routed via the hook, so three edges chain_depth's own docstring documents as load-bearing
were never directly asserted: zero commits, a bare root file's `·` prefix, and multi-area
branching (including a commit whose changed files span more than one area).

Usage: python3 thinking-tools/scripts/test/test-next-candidate.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import atexit
import calendar
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
    atexit.register(shutil.rmtree, d, ignore_errors=True)
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


def check_age_days_dst() -> list[str]:
    """age_days() must use calendar.timegm (UTC-exact), not local mktime — DST fix regression guard (#542).

    Picks an input 30 minutes shy of a day boundary under a DST-observing local zone: the old
    `time.mktime(...) - time.timezone` form could be off by up to an hour, which is enough to
    flip the floored day count across that boundary. That error only occurs when the target,
    interpreted as America/New_York local wall-clock time, actually falls inside DST (roughly
    Mar-Nov) — anchoring the fixture to the real `now` made the guard's power to catch a
    reintroduced bug depend on which season CI happened to run in (#553). Anchoring `now` to a
    fixed mid-July instant (deep inside DST, no transition nearby) via a `time.time()`
    monkeypatch keeps the guard effective year-round regardless of when this test runs.
    """
    failures = []
    orig_tz = os.environ.get("TZ")
    orig_time = time.time
    try:
        os.environ["TZ"] = "America/New_York"
        time.tzset()
        now = calendar.timegm(time.strptime("2026-07-15T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
        time.time = lambda: now
        target = now - (3 * 86400 - 1800)
        iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(target))
        got = nc.age_days(iso)
        if got != 2:
            failures.append(f"age_days DST check: expected 2, got {got} (TZ={os.environ.get('TZ')})")
    finally:
        time.time = orig_time
        if orig_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = orig_tz
        time.tzset()
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


def check_maintenance_ratio() -> list[str]:
    """Streak counts consecutive non-body commits from HEAD backward, stopping at the first
    commit that touched a SKILL.md/agents/*.md body (#755)."""
    failures = []
    cwd = _repo()
    _commit(cwd, ["thinking-tools/skills/foo/SKILL.md"], "c1 touches a body")
    _commit(cwd, ["rules/rm-guard.sh"], "c2 maintenance")
    _commit(cwd, ["rules/other.sh"], "c3 maintenance")
    streak, touched, total = nc.maintenance_ratio(cwd, 3)
    if (streak, touched, total) != (2, 1, 3):
        failures.append(f"maintenance_ratio: expected (streak=2, touched=1, total=3), got {(streak, touched, total)}")
    return failures


def check_maintenance_ratio_near_misses() -> list[str]:
    """Near-miss paths must not count as a body touch: `agents.py` (not .md), `SKILL.md.bak`
    (not exactly SKILL.md) — only a nested `agents/*.md` still counts."""
    failures = []
    cwd = _repo()
    _commit(cwd, ["thinking-tools/skills/foo/SKILL.md"], "d1 real body")
    _commit(cwd, ["thinking-tools/agents/agents.py"], "d2 near-miss: agents.py not .md")
    _commit(cwd, ["thinking-tools/skills/foo/SKILL.md.bak"], "d3 near-miss: not exactly SKILL.md")
    _commit(cwd, ["docs/nested/agents/reviewer.md"], "d4 real: nested agents/*.md")
    streak, touched, total = nc.maintenance_ratio(cwd, 4)
    # HEAD is d4, a real body touch, so the trailing streak is immediately 0.
    if (streak, touched, total) != (0, 2, 4):
        failures.append(
            f"maintenance_ratio near-misses: expected (streak=0, touched=2, total=4), got "
            f"{(streak, touched, total)}"
        )
    return failures


def check_open_issues_body_requested_only_when_needed() -> list[str]:
    """`gh issue list` must request `body` only when the caller says it needs it (#757 —
    fetching body for the whole open backlog was the dominant cost of the hook's default
    fetch; the hook had been fixed by skipping the fetch outright instead of lightening it).

    Asserts on the actual `gh` invocation args, not on rendered prose, so a future change that
    keeps the words right but re-widens the fetch still fails this.
    """
    failures = []
    cwd = _repo()
    _commit(cwd, ["f.txt"], "init")
    _git(cwd, "remote", "add", "origin", "https://github.com/example/example.git")

    stub_dir = tempfile.mkdtemp(prefix="test-next-candidate-stub-")
    atexit.register(shutil.rmtree, stub_dir, ignore_errors=True)
    calls_log = Path(stub_dir) / "calls.log"
    stub = Path(stub_dir) / "gh"
    stub.write_text(f'#!/usr/bin/env bash\necho "$@" >> "{calls_log}"\necho "[]"\n')
    stub.chmod(0o755)

    orig_path = os.environ.get("PATH", "")
    try:
        os.environ["PATH"] = f"{stub_dir}:{orig_path}"
        nc.open_issues(cwd, want_body=False)
        nc.open_issues(cwd, want_body=True)
    finally:
        os.environ["PATH"] = orig_path

    calls = calls_log.read_text().splitlines() if calls_log.exists() else []
    if len(calls) != 2:
        failures.append(f"open_issues body gating: expected 2 gh calls, got {len(calls)}: {calls}")
        return failures
    if "body" in calls[0]:
        failures.append(f"open_issues(want_body=False) requested body: {calls[0]}")
    if "body" not in calls[1]:
        failures.append(f"open_issues(want_body=True) did not request body: {calls[1]}")
    return failures


def main() -> int:
    checks = [
        check_top_areas,
        check_zero_commits,
        check_multi_area_branching,
        check_partial_overlap,
        check_root_file_prefix_breaks_chain,
        check_age_days_dst,
        check_maintenance_ratio,
        check_maintenance_ratio_near_misses,
        check_open_issues_body_requested_only_when_needed,
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
