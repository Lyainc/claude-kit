#!/usr/bin/env python3
"""
Regression tests for audit-validate._git_activity_summary().

Run: python3 obsidian-vault-manager/scripts/test/test-git-activity.py
Exit code 0 on pass, 1 on any failure.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("av", str(ROOT / "audit-validate.py"))
av = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(av)  # type: ignore[union-attr]

_git_activity_summary = av._git_activity_summary


def _git(args: list, cwd: str) -> None:
    """Run a git command; raise on failure."""
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   capture_output=True, text=True)


def _setup_git_repo(tmp: str) -> None:
    """Initialise a minimal git repo with identity config."""
    _git(["init"], tmp)
    _git(["config", "user.email", "test@example.com"], tmp)
    _git(["config", "user.name", "Test"], tmp)


def main() -> int:
    errors: list[str] = []

    def check(label: str, got, want) -> None:
        if got == want:
            print(f"  ok   {label}")
        else:
            print(f"  FAIL {label}: got {got!r}, want {want!r}", file=sys.stderr)
            errors.append(label)

    # ── case 1: non-git directory → None ─────────────────────────────────────
    print("case 1: non-git directory")
    with tempfile.TemporaryDirectory() as tmp:
        result = _git_activity_summary(Path(tmp))
        check("non-git vault → None", result, None)

    # ── case 2: git repo with 0 commits in window → all-zero counts ──────────
    print("case 2: git repo, no commits in window")
    with tempfile.TemporaryDirectory() as tmp:
        _setup_git_repo(tmp)
        # Create a commit far in the past via GIT_COMMITTER_DATE / GIT_AUTHOR_DATE
        p = Path(tmp) / "old.md"
        p.write_text("old content")
        _git(["add", "old.md"], tmp)
        old_date = "2000-01-01T00:00:00"
        env = {**os.environ,
               "GIT_AUTHOR_DATE": old_date,
               "GIT_COMMITTER_DATE": old_date}
        subprocess.run(
            ["git", "commit", "-m", "old commit"],
            cwd=tmp, check=True, capture_output=True, text=True, env=env,
        )
        result = _git_activity_summary(Path(tmp), days=7)
        check("0 commits in window → result is dict", isinstance(result, dict), True)
        check("0 commits in window → commits=0", result["commits"], 0)
        check("0 commits in window → added=0", result["added"], 0)
        check("0 commits in window → modified=0", result["modified"], 0)
        check("0 commits in window → deleted=0", result["deleted"], 0)

    # ── case 3: git repo with commits → correct counts ───────────────────────
    print("case 3: git repo with recent commits")
    with tempfile.TemporaryDirectory() as tmp:
        _setup_git_repo(tmp)

        # Commit 1: add two files
        (Path(tmp) / "a.md").write_text("alpha")
        (Path(tmp) / "b.md").write_text("beta")
        _git(["add", "a.md", "b.md"], tmp)
        _git(["commit", "-m", "add a and b"], tmp)

        # Commit 2: modify a.md, delete b.md
        (Path(tmp) / "a.md").write_text("alpha modified")
        _git(["add", "a.md"], tmp)
        _git(["rm", "b.md"], tmp)
        _git(["commit", "-m", "modify a, delete b"], tmp)

        result = _git_activity_summary(Path(tmp), days=7)
        check("recent commits → result is dict", isinstance(result, dict), True)
        check("recent commits → commits=2", result["commits"], 2)
        check("recent commits → added=2", result["added"], 2)
        check("recent commits → modified=1", result["modified"], 1)
        check("recent commits → deleted=1", result["deleted"], 1)
        check("recent commits → days=7", result["days"], 7)

    # ── case 4: git not in PATH → None ───────────────────────────────────────
    print("case 4: git not in PATH")
    with tempfile.TemporaryDirectory() as tmp:
        orig_path = os.environ.get("PATH", "")
        os.environ["PATH"] = ""
        try:
            result = _git_activity_summary(Path(tmp))
            check("git not in PATH → None", result, None)
        finally:
            os.environ["PATH"] = orig_path

    print()
    n_cases = 4 + 5 + 5 + 1  # labels above
    n_checks = len(errors) + sum(
        1 for line in open(__file__) if line.strip().startswith("check(")
    )
    # Just count the check() calls in this file for the summary line
    total = sum(1 for line in open(__file__) if line.strip().startswith("check("))
    if errors:
        print(f"FAIL: {len(errors)}/{total} cases failed")
        return 1
    print(f"OK: all {total} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
