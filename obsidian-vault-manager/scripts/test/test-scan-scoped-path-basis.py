#!/usr/bin/env python3
"""
`--path`-scoped scan-frontmatter/scan-filename path-basis regression (#619 follow-up, #631).

Before this fix: `cmd_scan_frontmatter`/`cmd_scan_filename` computed each record's `path`
via `os.path.relpath(fpath, target_dir)`, where `target_dir` is the `<dir>` argument they
were called with. Unscoped `/audit` passes `$VAULT_ROOT` as that argument, so `path` came
out `$VAULT_ROOT`-relative by coincidence. But SKILL.md Step 5–6 pass `$scan_dir` under
`--path <subdir>` (e.g. `$VAULT_ROOT/notes`), so a scoped call emitted `notes/x.md` as bare
`x.md` instead — a different basis than `e5-candidates`, which #619 already fixed to always
be `$VAULT_ROOT`-relative regardless of which subdirectory it walks (audit/SKILL.md Step 10
calls it unscoped on `$VAULT_ROOT/notes` unconditionally). CLASSIFY's E5 step joins an
orphan's `frontmatter_records` entry against `e5_candidates` by `path` — under `--path
notes`, the mismatched basis (`x.md` vs `notes/x.md`) meant the join always missed, so a
real orphan with a real shared-tag candidate reported "연결 후보 없음" instead.

This test pins the reproduction case named in #631: a vault scoped via `--path notes`
where an orphan and a candidate share a real tag — the orphan's `scan-frontmatter` path
must key-match its `e5-candidates` entry, and that entry's candidate list must contain the
other file.

Run: python3 obsidian-vault-manager/scripts/test/test-scan-scoped-path-basis.py
  -> "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
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


def _env(vault_root: Path) -> dict:
    env = {**os.environ, "VAULT_ROOT": str(vault_root)}
    for k in ("VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH", "AUDIT_STATE_PATH"):
        env.pop(k, None)
    return env


def write_note(vault: Path, relpath: str, tags: list) -> None:
    p = vault / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    tags_str = ", ".join(tags)
    p.write_text(
        f"---\ntype: note\ntags: [{tags_str}]\ncreated: 2026-01-01\nprovenance: t\n---\nbody\n",
        encoding="utf-8",
    )


def run_prim(vault: Path, *args: str) -> list:
    proc = subprocess.run(
        ["bash", str(_PRIM_SH), *args],
        capture_output=True, text=True, env=_env(vault),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{args}: {proc.stderr}")
    return json.loads(proc.stdout)


def case_scoped_scan_frontmatter_matches_e5_candidates(errors: list) -> None:
    """The #631 repro: --path notes scope, orphan + candidate sharing a real tag."""
    print("\ncase: scoped_scan_frontmatter_matches_e5_candidates")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        write_note(vault, "notes/orphan.md", ["rare-tag"])
        write_note(vault, "notes/candidate.md", ["rare-tag"])

        scan_dir = vault / "notes"  # what SKILL.md passes under `--path notes`
        fm_records = run_prim(vault, "scan-frontmatter", str(scan_dir))
        e5_records = run_prim(vault, "e5-candidates", str(vault / "notes"))

        fm_paths = {r["path"] for r in fm_records}
        e5_paths = {r["path"] for r in e5_records}
        _assert(fm_paths == {"notes/orphan.md", "notes/candidate.md"},
                f"scoped scan-frontmatter is $VAULT_ROOT-relative, not scan_dir-relative "
                f"(got {sorted(fm_paths)})", errors)
        _assert(fm_paths == e5_paths,
                f"scoped scan-frontmatter and e5-candidates share the same key basis "
                f"(fm={sorted(fm_paths)}, e5={sorted(e5_paths)})", errors)

        # Simulate CLASSIFY's actual join: look up e5-candidates by the KEY scan-frontmatter
        # produced, not by a hardcoded literal — this is what fails pre-fix, since the
        # fm_record's path ("orphan.md") never matches any e5_records key ("notes/orphan.md").
        e5_by_path = {r["path"]: r for r in e5_records}
        orphan_fm_path = next(r["path"] for r in fm_records if "orphan" in r["path"])
        orphan_entry = e5_by_path.get(orphan_fm_path)
        _assert(orphan_entry is not None,
                f"orphan's e5-candidates entry is reachable via its scan-frontmatter key "
                f"({orphan_fm_path!r} in {sorted(e5_by_path)})", errors)
        if orphan_entry is not None:
            cand_paths = {c["path"] for c in orphan_entry["candidates"]}
            _assert("notes/candidate.md" in cand_paths,
                    f"orphan finds the real shared-tag candidate under --path scope "
                    f"(got {sorted(cand_paths)})", errors)


def case_scoped_scan_filename_matches_vault_root_basis(errors: list) -> None:
    """scan-filename must use the same $VAULT_ROOT-relative basis as scan-frontmatter."""
    print("\ncase: scoped_scan_filename_matches_vault_root_basis")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        write_note(vault, "notes/sub/deep.md", ["x"])

        scan_dir = vault / "notes"
        records = run_prim(vault, "scan-filename", str(scan_dir))
        paths = {r["path"] for r in records}
        _assert(paths == {"notes/sub/deep.md"},
                f"scoped scan-filename is $VAULT_ROOT-relative (got {sorted(paths)})", errors)


def case_unscoped_call_unchanged(errors: list) -> None:
    """Unscoped (target_dir == VAULT_ROOT) behavior is unaffected by the fix."""
    print("\ncase: unscoped_call_unchanged")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        write_note(vault, "notes/a.md", ["x"])

        fm_records = run_prim(vault, "scan-frontmatter", str(vault))
        fn_records = run_prim(vault, "scan-filename", str(vault))
        _assert({r["path"] for r in fm_records} == {"notes/a.md"},
                "unscoped scan-frontmatter still $VAULT_ROOT-relative", errors)
        _assert({r["path"] for r in fn_records} == {"notes/a.md"},
                "unscoped scan-filename still $VAULT_ROOT-relative", errors)


def main() -> int:
    errors: list = []
    for case in (
        case_scoped_scan_frontmatter_matches_e5_candidates,
        case_scoped_scan_filename_matches_vault_root_basis,
        case_unscoped_call_unchanged,
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
