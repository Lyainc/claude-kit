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
  3. two operations in a row → the sidecar is NOT overwritten (the `.bak` single-slot
                               regression guard); distinct corruption still gets its
                               own sidecar, and an existing good `.bak` survives

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


def case_two_ops_keep_the_sidecar(errors: list) -> None:
    """The `.bak` single-slot regression: a second operation must not erase the first
    run's evidence. Identical bytes reuse the one sidecar (a `--reset-state` loop calls
    this once per vault file, and N identical copies is litter, not evidence)."""
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
        _assert(after_first == after_second,
                f"two ops: same sidecar reused, none added or renamed "
                f"(before={[p.name for p in after_first]}, after={[p.name for p in after_second]})",
                errors)
        _assert(
            all(p.read_text(encoding="utf-8") == original for p in after_second),
            "two ops: the sidecar still holds the original bytes",
            errors,
        )
        _assert(state_path.read_text(encoding="utf-8") == original,
                "two ops: audit-state.json never overwritten", errors)


def case_different_corruption_gets_its_own_sidecar(errors: list) -> None:
    """Dedup must not hide NEW evidence: different bytes → an additional sidecar."""
    first_bytes = "{ this is not json"
    second_bytes = '{"version": 1, "paths": "not a dict"}'
    with tempfile.TemporaryDirectory() as td:
        vault, state_path = seed(Path(td), first_bytes)
        run_audit_state(vault, state_path, "mark-clean", "notes/a.md")
        state_path.write_text(second_bytes, encoding="utf-8")
        run_audit_state(vault, state_path, "mark-clean", "notes/a.md")

        found = sidecars(state_path)
        _assert(len(found) == 2,
                f"distinct corruption: two sidecars kept (got {len(found)})", errors)
        _assert(
            {p.read_text(encoding="utf-8") for p in found} == {first_bytes, second_bytes},
            "distinct corruption: both originals preserved verbatim",
            errors,
        )


def case_existing_good_bak_survives(errors: list) -> None:
    """The actual #443 data-loss mechanism: the old code rotated `.bak` on the write
    that followed the empty-state fallback, so the last good state was destroyed. The
    corrupt path must never touch an existing `.bak`."""
    good_bak = json.dumps({"version": 1, "paths": {"notes/a.md": {"status": "clean"}}})
    original = "{ truncated"
    with tempfile.TemporaryDirectory() as td:
        vault, state_path = seed(Path(td), original)
        bak = state_path.parent / (state_path.name + ".bak")
        bak.write_text(good_bak, encoding="utf-8")

        for op in ("mark-clean", "invalidate"):
            run_audit_state(vault, state_path, op, "notes/a.md")

        _assert(bak.read_text(encoding="utf-8") == good_bak,
                "good .bak: last good state survives both ops untouched", errors)


def case_bad_record_shape(errors: list) -> None:
    """A record that is not an object reaches every op's indexing, so it must take the
    same exit-3 path as whole-file corruption rather than an uncaught traceback."""
    for label, rec in [("string record", "oops"), ("null record", None), ("list record", [1, 2])]:
        original = json.dumps({"version": 1, "paths": {"notes/a.md": rec}})
        for op in ("is-clean", "invalidate", "list-dirty-since"):
            with tempfile.TemporaryDirectory() as td:
                vault, state_path = seed(Path(td), original)
                arg = "notes/a.md" if op != "list-dirty-since" else ""
                proc = run_audit_state(vault, state_path, op, *( [arg] if arg else [] ))
                _assert(proc.returncode == 3,
                        f"bad record [{label}/{op}]: exit 3 (got {proc.returncode})", errors)
                _assert("traceback" not in proc.stderr.lower(),
                        f"bad record [{label}/{op}]: message, not a traceback", errors)
                _assert(state_path.read_text(encoding="utf-8") == original,
                        f"bad record [{label}/{op}]: state file untouched", errors)


def case_bad_mtime_type(errors: list) -> None:
    """A wrong-typed `mtime_at_audit` must not raise on the comparison. The record cannot
    claim freshness, so the file reads as dirty and re-audits."""
    original = json.dumps(
        {"version": 1, "paths": {"notes/a.md": {"mtime_at_audit": "nope", "status": "clean"}}})
    for op, args in [("is-clean", ["notes/a.md"]), ("list-dirty-since", [])]:
        with tempfile.TemporaryDirectory() as td:
            vault, state_path = seed(Path(td), original)
            proc = run_audit_state(vault, state_path, op, *args)
            _assert(proc.returncode == 0,
                    f"bad mtime [{op}]: exits 0 (got {proc.returncode}: {proc.stderr})", errors)
            _assert("traceback" not in proc.stderr.lower(),
                    f"bad mtime [{op}]: no traceback", errors)
            if proc.returncode == 0 and op == "is-clean":
                _assert(json.loads(proc.stdout).get("clean") is False,
                        "bad mtime [is-clean]: reads as dirty, not clean", errors)


def case_unpreservable_still_exits_3(errors: list) -> None:
    """A read-only directory means no sidecar can be written. That is still exit 3 with an
    honest message — never a traceback that reads as corruption when it is permissions."""
    original = "{ truncated"
    with tempfile.TemporaryDirectory() as td:
        vault, state_path = seed(Path(td), original)
        state_path.parent.chmod(0o555)
        try:
            proc = run_audit_state(vault, state_path, "mark-clean", "notes/a.md")
        finally:
            state_path.parent.chmod(0o755)
        _assert(proc.returncode == 3,
                f"unwritable dir: exit 3 (got {proc.returncode})", errors)
        _assert("traceback" not in proc.stderr.lower(),
                "unwritable dir: message, not a traceback", errors)
        _assert("COULD NOT preserve" in proc.stderr,
                f"unwritable dir: says the copy failed (stderr: {proc.stderr.strip()[:120]})",
                errors)
        _assert(state_path.read_text(encoding="utf-8") == original,
                "unwritable dir: original still intact", errors)


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
    for case in (case_unparseable, case_wrong_shape, case_two_ops_keep_the_sidecar,
                 case_different_corruption_gets_its_own_sidecar,
                 case_existing_good_bak_survives, case_bad_record_shape,
                 case_bad_mtime_type, case_unpreservable_still_exits_3,
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
