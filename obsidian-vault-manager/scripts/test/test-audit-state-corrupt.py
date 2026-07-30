#!/usr/bin/env python3
"""
audit-state corrupt-input regression (#443).

Before this gate, `load_state` swallowed BOTH failure modes and returned an empty
state with exit 0, so the next `save_state` wrote the empty state to disk and rotated
the single `.bak` slot — two operations and the original was gone, silently.

Three cases, all driving the real `ovm-primitives.sh audit-state` subprocess:
  1. unparseable JSON        → exit != 0, sidecar holds the original, state file untouched
  2. valid JSON, wrong shape → same path (not a traceback): no `paths` key, and `paths`
                               present but not a dict, and a top-level JSON array
  3. two operations in a row → the first sidecar is NOT overwritten (the `.bak`
                               single-slot regression guard)

Run: python3 obsidian-vault-manager/scripts/test/test-audit-state-corrupt.py
  → "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def run_audit_state(vault: Path, state_path: Path, *args) -> subprocess.CompletedProcess:
    env = {**os.environ, "VAULT_ROOT": str(vault), "AUDIT_STATE_PATH": str(state_path)}
    return subprocess.run(
        ["bash", str(_PRIM_SH), "audit-state", *args],
        capture_output=True, text=True, env=env,
    )


def sidecars(state_path: Path) -> list:
    return sorted(state_path.parent.glob(state_path.name + ".corrupt-*"))


def seed(tmp: Path, content: str) -> tuple:
    """Vault with one note + a state file holding `content`. Returns (vault, state_path)."""
    vault = tmp / "vault"
    (vault / "notes").mkdir(parents=True)
    (vault / "notes" / "a.md").write_text("---\ntype: note\n---\nbody\n", encoding="utf-8")
    state_path = vault / ".ovm" / "audit-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(content, encoding="utf-8")
    return vault, state_path


def assert_preserved(proc, state_path: Path, original: str, label: str, errors: list) -> None:
    """Shared expectation: loud non-zero exit, original in a sidecar, state file as-is."""
    _assert(proc.returncode != 0, f"{label}: exits non-zero (got {proc.returncode})", errors)
    _assert(
        "traceback" not in proc.stderr.lower(),
        f"{label}: fails with a message, not a traceback",
        errors,
    )
    found = sidecars(state_path)
    _assert(len(found) == 1, f"{label}: exactly one sidecar written (got {len(found)})", errors)
    if found:
        _assert(
            found[0].read_text(encoding="utf-8") == original,
            f"{label}: sidecar holds the original bytes",
            errors,
        )
        _assert(
            str(found[0]) in proc.stderr,
            f"{label}: stderr names the sidecar path",
            errors,
        )
    _assert(
        state_path.read_text(encoding="utf-8") == original,
        f"{label}: audit-state.json itself is NOT overwritten",
        errors,
    )
    _assert(
        not (state_path.parent / (state_path.name + ".bak")).exists(),
        f"{label}: no .bak rotation happened",
        errors,
    )


def case_unparseable(errors: list) -> None:
    original = '{"version": 1, "paths": {"notes/a.md": '  # truncated mid-object
    with tempfile.TemporaryDirectory() as td:
        vault, state_path = seed(Path(td), original)
        proc = run_audit_state(vault, state_path, "mark-clean", "notes/a.md")
        assert_preserved(proc, state_path, original, "unparseable JSON", errors)


def case_wrong_shape(errors: list) -> None:
    for label, original in [
        ("no paths key", '{"version": 1}'),
        ("paths not a dict", '{"version": 1, "paths": []}'),
        ("top-level array", '[{"version": 1}]'),
        ("top-level null", "null"),
    ]:
        with tempfile.TemporaryDirectory() as td:
            vault, state_path = seed(Path(td), original)
            proc = run_audit_state(vault, state_path, "mark-clean", "notes/a.md")
            assert_preserved(proc, state_path, original, f"wrong shape [{label}]", errors)


def case_two_ops_keep_both_sidecars(errors: list) -> None:
    """The `.bak` single-slot regression: a second operation must not erase the first
    run's evidence. Two ops → two distinct sidecars, both holding the original."""
    original = "{ this is not json"
    with tempfile.TemporaryDirectory() as td:
        vault, state_path = seed(Path(td), original)
        first = run_audit_state(vault, state_path, "mark-clean", "notes/a.md")
        after_first = sidecars(state_path)
        second = run_audit_state(vault, state_path, "invalidate", "notes/a.md")
        after_second = sidecars(state_path)

        _assert(first.returncode != 0 and second.returncode != 0,
                "two ops: both exit non-zero", errors)
        _assert(len(after_first) == 1, "two ops: first op wrote one sidecar", errors)
        _assert(len(after_second) == 2,
                f"two ops: second sidecar added, first kept (got {len(after_second)})", errors)
        _assert(after_first and after_first[0] in after_second,
                "two ops: the first sidecar still exists after the second op", errors)
        _assert(
            all(p.read_text(encoding="utf-8") == original for p in after_second),
            "two ops: every sidecar still holds the original bytes",
            errors,
        )
        _assert(state_path.read_text(encoding="utf-8") == original,
                "two ops: audit-state.json never overwritten", errors)


def case_healthy_state_unaffected(errors: list) -> None:
    """FP guard: a well-formed state file still works, and no sidecar is created."""
    original = json.dumps({"version": 1, "paths": {}, "last_full_scan": None})
    with tempfile.TemporaryDirectory() as td:
        vault, state_path = seed(Path(td), original)
        proc = run_audit_state(vault, state_path, "mark-clean", "notes/a.md")
        _assert(proc.returncode == 0, f"healthy: exits 0 (got {proc.returncode}: {proc.stderr})",
                errors)
        _assert(not sidecars(state_path), "healthy: no corrupt sidecar written", errors)
        if proc.returncode == 0:
            written = json.loads(state_path.read_text(encoding="utf-8"))
            _assert("notes/a.md" in written.get("paths", {}),
                    "healthy: mark-clean recorded the path", errors)


def main() -> int:
    errors: list = []
    for case in (case_unparseable, case_wrong_shape, case_two_ops_keep_both_sidecars,
                 case_healthy_state_unaffected):
        print(f"\n{case.__name__}:")
        case(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed")
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
