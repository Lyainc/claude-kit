#!/usr/bin/env python3
"""
audit-state `stats`/`status` op + `list-dirty-since` untracked-file regression (#619).

Before this fix:
  - `audit-state status` (and `stats`) did not exist — any call errored with
    "unknown audit-state op", so the audit skill's documented `status` flag had
    nothing to invoke.
  - `list-dirty-since` only ever iterated the sidecar's own `paths` dict, so a file
    the sidecar has NEVER heard of (no prior audit run touched it) could not appear
    in the output under any reason — "untracked" was structurally unreachable even
    though SKILL.md documented it.

Both ops now walk the live vault (`list_md_files`) instead of only the sidecar.

Run: python3 obsidian-vault-manager/scripts/test/test-audit-state-stats-and-untracked.py
  -> "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def run_prim(vault: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "VAULT_ROOT": str(vault)}
    for k in ("VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH", "AUDIT_STATE_PATH"):
        env.pop(k, None)
    return subprocess.run(
        ["bash", str(_PRIM_SH), *args],
        capture_output=True, text=True, env=env,
    )


def audit_state(vault: Path, *args: str) -> subprocess.CompletedProcess:
    return run_prim(vault, "audit-state", *args)


def write_note(vault: Path, relpath: str) -> Path:
    p = vault / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntype: note\ntags: [x]\ncreated: 2026-01-01\nprovenance: t\n---\nbody\n",
                  encoding="utf-8")
    return p


def case_stats_alias_on_fresh_vault(errors: list) -> None:
    """No sidecar at all -> every file is untracked; `stats` and `status` agree."""
    print("\ncase: stats_alias_on_fresh_vault")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        write_note(vault, "notes/a.md")
        write_note(vault, "notes/b.md")

        for op in ("stats", "status"):
            proc = audit_state(vault, op)
            _assert(proc.returncode == 0, f"[{op}] exits 0 (stderr: {proc.stderr!r})", errors)
            data = json.loads(proc.stdout) if proc.returncode == 0 else {}
            _assert(data.get("total") == 2, f"[{op}] total == 2 (got {data.get('total')})", errors)
            _assert(data.get("untracked") == 2,
                    f"[{op}] untracked == 2 (got {data.get('untracked')})", errors)
            _assert(data.get("clean") == 0, f"[{op}] clean == 0 (got {data.get('clean')})", errors)
            _assert(data.get("dirty") == 0, f"[{op}] dirty == 0 (got {data.get('dirty')})", errors)


def case_stats_after_mark_clean(errors: list) -> None:
    print("\ncase: stats_after_mark_clean")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        write_note(vault, "notes/a.md")
        write_note(vault, "notes/b.md")
        mc = audit_state(vault, "mark-clean", "notes/a.md")
        _assert(mc.returncode == 0, f"mark-clean exits 0 (stderr: {mc.stderr!r})", errors)

        proc = audit_state(vault, "stats")
        data = json.loads(proc.stdout)
        _assert(data.get("clean") == 1, f"clean == 1 after marking one file (got {data.get('clean')})", errors)
        _assert(data.get("untracked") == 1, f"untracked == 1 (got {data.get('untracked')})", errors)
        _assert(data.get("total") == 2, f"total unchanged at 2 (got {data.get('total')})", errors)


def case_stats_tracked_missing(errors: list) -> None:
    """A sidecar record for a file that no longer exists is reported separately,
    not folded into `total` (which counts files that currently exist on disk)."""
    print("\ncase: stats_tracked_missing")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        write_note(vault, "notes/a.md")
        audit_state(vault, "mark-clean", "notes/a.md")
        os.remove(vault / "notes" / "a.md")

        proc = audit_state(vault, "stats")
        data = json.loads(proc.stdout)
        _assert(data.get("total") == 0, f"total == 0, deleted file not counted (got {data.get('total')})", errors)
        _assert(data.get("tracked_missing") == 1,
                f"tracked_missing == 1 (got {data.get('tracked_missing')})", errors)


def case_list_dirty_since_untracked(errors: list) -> None:
    """The #619 repro: fresh vault, no state file -> every file surfaces as untracked
    instead of the old `[]` (which the skill read as "nothing to audit")."""
    print("\ncase: list_dirty_since_untracked")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        write_note(vault, "notes/a.md")
        write_note(vault, "notes/b.md")

        proc = audit_state(vault, "list-dirty-since")
        _assert(proc.returncode == 0, f"exits 0 (stderr: {proc.stderr!r})", errors)
        records = json.loads(proc.stdout) if proc.returncode == 0 else []
        _assert(len(records) == 2, f"both untracked files listed (got {len(records)})", errors)
        by_path = {r["path"]: r for r in records}
        for rel in ("notes/a.md", "notes/b.md"):
            _assert(rel in by_path, f"{rel} present in output", errors)
            _assert(by_path.get(rel, {}).get("reason") == "untracked",
                    f"{rel} reason == 'untracked' (got {by_path.get(rel, {}).get('reason')!r})", errors)


def case_list_dirty_since_mixed_reasons(errors: list) -> None:
    """clean/untracked/mtime_changed/explicitly_invalidated/file_missing all coexist and
    each keeps its own reason — the untracked fix must not regress the pre-existing ones."""
    print("\ncase: list_dirty_since_mixed_reasons")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        write_note(vault, "notes/clean.md")
        write_note(vault, "notes/new.md")            # untracked
        write_note(vault, "notes/touched.md")         # mark clean, then touch -> mtime_changed
        write_note(vault, "notes/invalidated.md")     # mark clean, then invalidate

        audit_state(vault, "mark-clean", "notes/clean.md")
        audit_state(vault, "mark-clean", "notes/touched.md")
        audit_state(vault, "mark-clean", "notes/invalidated.md")
        audit_state(vault, "invalidate", "notes/invalidated.md")

        # Ensure a real mtime bump (integer-second resolution).
        time.sleep(1.1)
        (vault / "notes" / "touched.md").write_text(
            "---\ntype: note\ntags: [x]\ncreated: 2026-01-01\nprovenance: t\n---\nedited\n",
            encoding="utf-8")

        proc = audit_state(vault, "list-dirty-since")
        records = json.loads(proc.stdout)
        by_path = {r["path"]: r["reason"] for r in records}

        _assert("notes/clean.md" not in by_path, "clean file is absent from dirty list", errors)
        _assert(by_path.get("notes/new.md") == "untracked", "new file: untracked", errors)
        _assert(by_path.get("notes/touched.md") == "mtime_changed", "touched file: mtime_changed", errors)
        _assert(by_path.get("notes/invalidated.md") == "explicitly_invalidated",
                "invalidated file: explicitly_invalidated", errors)


def case_list_dirty_since_file_missing_still_works(errors: list) -> None:
    """Pre-existing behavior: a tracked file whose bytes vanished from disk still
    surfaces (`file_missing`) even though the new code walks the live vault first."""
    print("\ncase: list_dirty_since_file_missing_still_works")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        write_note(vault, "notes/gone.md")
        audit_state(vault, "mark-clean", "notes/gone.md")
        os.remove(vault / "notes" / "gone.md")

        proc = audit_state(vault, "list-dirty-since")
        records = json.loads(proc.stdout)
        by_path = {r["path"]: r["reason"] for r in records}
        _assert(by_path.get("notes/gone.md") == "file_missing",
                f"deleted tracked file reported as file_missing (got {by_path.get('notes/gone.md')!r})",
                errors)


def main() -> int:
    errors: list = []
    for case in (
        case_stats_alias_on_fresh_vault,
        case_stats_after_mark_clean,
        case_stats_tracked_missing,
        case_list_dirty_since_untracked,
        case_list_dirty_since_mixed_reasons,
        case_list_dirty_since_file_missing_still_works,
    ):
        case(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed")
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
