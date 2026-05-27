#!/usr/bin/env python3
"""
Regression test for `vault-bridge/scripts/vault-commit-message.py` —
status-transition-aware commit message generation.

Run: python3 vault-bridge/scripts/test/test-vault-commit-message.py
Exit 0 on pass, 1 on fail.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "vault-bridge" / "scripts" / "vault-commit-message.py"


def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _run_script(vault_root: str, diff_lines: list[str]) -> subprocess.CompletedProcess:
    """Invoke vault-commit-message.py with vault_root and diff on stdin."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), vault_root],
        input="\n".join(diff_lines) + "\n",
        capture_output=True,
        text=True,
    )


def _git(vault_root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", vault_root, *args],
        capture_output=True,
        text=True,
    )


def _init_git_repo(path: Path) -> None:
    """Initialize a minimal git repo suitable for testing."""
    _git(str(path), "init")
    _git(str(path), "config", "user.email", "test@example.com")
    _git(str(path), "config", "user.name", "Test")
    # Create an initial empty commit so HEAD exists
    _git(str(path), "commit", "--allow-empty", "-m", "init")


def _write_note(vault_root: Path, rel_path: str, ftype: str, status: str | None = None, body: str = "# content\n") -> Path:
    """Write a vault note with frontmatter."""
    full = vault_root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---", f"type: {ftype}", f"created: 2026-05-28"]
    if status:
        fm_lines.append(f"status: {status}")
    fm_lines.append("---")
    full.write_text("\n".join(fm_lines) + "\n" + body, encoding="utf-8")
    return full


def _stage_file(vault_root: str, rel_path: str) -> None:
    _git(vault_root, "add", rel_path)


def _commit_file(vault_root: str, rel_path: str, msg: str = "initial") -> None:
    _git(vault_root, "add", rel_path)
    _git(vault_root, "commit", "-m", msg)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def case_new_decision(errors: list[str]) -> None:
    """New decision note → message starts with 'decision(create):'"""
    print("\ncase: new_decision")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        _write_note(vault_root, "notes/decision-2026-05-28-arch.md", "decision")
        diff = ["A\tnotes/decision-2026-05-28-arch.md"]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(out.startswith("decision(create):"), f"starts with decision(create): (got: {out!r})", errors)
        _assert("decision-2026-05-28-arch" in out, f"stem in message (got: {out!r})", errors)


def case_new_raw_note(errors: list[str]) -> None:
    """New raw note → message starts with 'note(draft):'"""
    print("\ncase: new_raw_note")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        _write_note(vault_root, "notes/my-idea.md", "note", "raw")
        diff = ["A\tnotes/my-idea.md"]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(out.startswith("note(draft):"), f"starts with note(draft): (got: {out!r})", errors)


def case_modify_raw_to_draft(errors: list[str]) -> None:
    """Modified file raw→draft → message contains 'note(promote)' and 'raw→draft'"""
    print("\ncase: modify_raw_to_draft")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        rel = "notes/evolving.md"
        # Commit initial version with status=raw
        _write_note(vault_root, rel, "note", "raw")
        _commit_file(str(vault_root), rel, "add evolving")
        # Update to status=draft (unstaged so disk content differs from HEAD)
        _write_note(vault_root, rel, "note", "draft")
        diff = ["M\t" + rel]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert("note(promote)" in out, f"contains note(promote) (got: {out!r})", errors)
        _assert("raw→draft" in out, f"contains raw→draft (got: {out!r})", errors)


def case_modify_draft_to_evergreen(errors: list[str]) -> None:
    """Modified file draft→evergreen → message contains 'note(promote)' and 'draft→evergreen'"""
    print("\ncase: modify_draft_to_evergreen")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        rel = "notes/maturing.md"
        _write_note(vault_root, rel, "note", "draft")
        _commit_file(str(vault_root), rel, "add maturing")
        _write_note(vault_root, rel, "note", "evergreen")
        diff = ["M\t" + rel]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert("note(promote)" in out, f"contains note(promote) (got: {out!r})", errors)
        _assert("draft→evergreen" in out, f"contains draft→evergreen (got: {out!r})", errors)


def case_modify_body_only(errors: list[str]) -> None:
    """Modified file with no status change → message starts with 'note(update):'"""
    print("\ncase: modify_body_only")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        rel = "notes/stable.md"
        _write_note(vault_root, rel, "note", "evergreen", body="# old content\n")
        _commit_file(str(vault_root), rel, "add stable")
        _write_note(vault_root, rel, "note", "evergreen", body="# updated content\n")
        diff = ["M\t" + rel]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(out.startswith("note(update):"), f"starts with note(update): (got: {out!r})", errors)


def case_modify_decision_body(errors: list[str]) -> None:
    """Modified decision file with no status change → message starts with 'decision(update):'"""
    print("\ncase: modify_decision_body")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        rel = "notes/arch-choice.md"
        _write_note(vault_root, rel, "decision", "draft", body="# old rationale\n")
        _commit_file(str(vault_root), rel, "add arch-choice")
        _write_note(vault_root, rel, "decision", "draft", body="# updated rationale\n")
        diff = ["M\t" + rel]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(out.startswith("decision(update):"), f"starts with decision(update): (got: {out!r})", errors)


def case_multi_file_decision_plus_note(errors: list[str]) -> None:
    """Multi-file (decision + note update) → title is decision line, body has bullet"""
    print("\ncase: multi_file_decision_plus_note")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        # Decision (added)
        _write_note(vault_root, "notes/decision-2026-05-28-pick.md", "decision")
        # Note (modified — commit then update)
        rel_note = "notes/background.md"
        _write_note(vault_root, rel_note, "note", "draft", body="# old\n")
        _commit_file(str(vault_root), rel_note, "add background")
        _write_note(vault_root, rel_note, "note", "draft", body="# new\n")
        diff = [
            "A\tnotes/decision-2026-05-28-pick.md",
            "M\t" + rel_note,
        ]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        lines = out.splitlines()
        _assert(lines[0].startswith("decision(create):"), f"title is decision(create): (got: {lines[0]!r})", errors)
        _assert(any(ln.startswith("- ") for ln in lines), f"body contains bullet (got: {out!r})", errors)
        _assert("note(update)" in out, f"body contains note(update) (got: {out!r})", errors)


def case_no_staged_files(errors: list[str]) -> None:
    """No staged files → fallback 'vault: update notes'"""
    print("\ncase: no_staged_files")
    with tempfile.TemporaryDirectory() as tmp:
        proc = _run_script(str(tmp), [])
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(out == "vault: update notes", f"fallback message (got: {out!r})", errors)


def case_untyped_file(errors: list[str]) -> None:
    """Added file with no type field → 'vault: add {filename}'"""
    print("\ncase: untyped_file")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        _init_git_repo(vault_root)
        f = vault_root / "notes" / "diary.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# No frontmatter here\n", encoding="utf-8")
        diff = ["A\tnotes/diary.md"]
        proc = _run_script(str(vault_root), diff)
        out = proc.stdout.strip()
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(out.startswith("vault: add"), f"starts with vault: add (got: {out!r})", errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"Running vault-commit-message regression tests against: {SCRIPT}")

    if not SCRIPT.exists():
        print(f"ERROR: script not found at {SCRIPT}", file=sys.stderr)
        return 1

    errors: list[str] = []

    case_new_decision(errors)
    case_new_raw_note(errors)
    case_modify_raw_to_draft(errors)
    case_modify_draft_to_evergreen(errors)
    case_modify_body_only(errors)
    case_modify_decision_body(errors)
    case_multi_file_decision_plus_note(errors)
    case_no_staged_files(errors)
    case_untyped_file(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
