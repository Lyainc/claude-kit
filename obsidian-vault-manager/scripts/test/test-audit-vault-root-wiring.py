#!/usr/bin/env python3
"""
Regression test — audit/SKILL.md's Phase 1 SCAN resolves $VAULT_ROOT and honors --path,
instead of hardcoding ~/vault (#619, following #613/#616's vault-root-chain fix).

Before this fix, audit/SKILL.md Steps 4-6 passed a literal `~/vault` to
scan-frontmatter/scan-filename/find regardless of VAULT_BRIDGE_VAULT_ROOT/VAULT_BRIDGE_VAULT_PATH,
so a non-default vault died in ovm-primitives.sh's validate_vault_path (the same #613 symptom,
still reachable end-to-end through the skill even after ovm-primitives.sh itself was fixed) and
the documented `--path <dir>` flag was inert (nothing consumed it).

Test matrix:
  1. SKILL.md structural wiring: Step 1 resolves $VAULT_ROOT via the shared chain; Steps
     scanning the vault use $scan_dir/$VAULT_ROOT, never a literal ~/vault; the link index
     and E9 vocabulary check stay unscoped by --path (by design — see SKILL.md Step 7/9).
  2. Functional: ovm-primitives.sh scan-frontmatter, invoked exactly as SKILL.md's Step 5
     would invoke it, against a non-default VAULT_BRIDGE_VAULT_PATH vault — succeeds (the
     #613/#619 repro).
  3. Functional: --path scoping actually narrows results — scanning $VAULT_ROOT/notes only
     returns files under notes/, scanning $VAULT_ROOT (unscoped) returns both.

Run: python3 obsidian-vault-manager/scripts/test/test-audit-vault-root-wiring.py
Exit 0 on pass, 1 on fail.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SKILL_MD = _HERE.parent.parent / "skills" / "audit" / "SKILL.md"
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"


def _assert(cond: bool, desc: str, errors: list) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


# ---------------------------------------------------------------------------
# Case 1: SKILL.md structural wiring
# ---------------------------------------------------------------------------

def case_skill_md_wiring(errors: list) -> None:
    print("\ncase: skill_md_wiring")
    text = _SKILL_MD.read_text(encoding="utf-8")
    # Isolate Phase 1 SCAN so a hardcoded ~/vault elsewhere in the file (there is none, but
    # future edits could add one) doesn't get conflated with this phase's own contract.
    m = re.search(r"## Phase 1 — SCAN(.*?)## Phase 2", text, re.DOTALL)
    _assert(m is not None, "Phase 1 SCAN section found", errors)
    phase1 = m.group(1) if m else ""

    # Step 1 resolves the shared chain, same as ovm-primitives.sh/pre-write-guard.sh.
    _assert("VAULT_BRIDGE_VAULT_ROOT" in phase1 and "VAULT_BRIDGE_VAULT_PATH" in phase1,
            "Step 1 names both VAULT_BRIDGE_VAULT_ROOT and VAULT_BRIDGE_VAULT_PATH", errors)

    # No exec call takes a literal ~/vault as its scan target anymore.
    literal_vault_calls = re.findall(
        r"(?:scan-frontmatter|scan-filename|find)\s+~/vault\b", phase1)
    _assert(not literal_vault_calls,
            f"no scan-frontmatter/scan-filename/find call hardcodes ~/vault (found: {literal_vault_calls})",
            errors)

    # Steps 5-6 (frontmatter/filename scan) use the --path-aware $scan_dir.
    _assert('scan-frontmatter "$scan_dir"' in phase1,
            "scan-frontmatter is called with \"$scan_dir\"", errors)
    _assert('scan-filename "$scan_dir"' in phase1,
            "scan-filename is called with \"$scan_dir\"", errors)

    # Step 7 (link index) and Step 9 (E9 vocabulary) stay vault-wide by design — they use
    # $VAULT_ROOT, not the --path-scoped $scan_dir, so a scoped run can't manufacture a
    # false E5 orphan or a false E9 vocabulary split.
    _assert('find "$VAULT_ROOT"' in phase1,
            "the wikilink-index find call uses the unscoped $VAULT_ROOT", errors)
    _assert('detect-vocabulary "$VAULT_ROOT"' in phase1,
            "detect-vocabulary is called with the unscoped $VAULT_ROOT", errors)


# ---------------------------------------------------------------------------
# Helpers for the functional cases
# ---------------------------------------------------------------------------

def _run_ovm(*args: str, env_overrides: dict) -> tuple:
    import os
    env = os.environ.copy()
    for k in ("VAULT_ROOT", "VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH",
              "AUDIT_STATE_PATH", "VAULT_BRIDGE_DISABLE"):
        env.pop(k, None)
    env.update(env_overrides)
    proc = subprocess.run(
        ["bash", str(_PRIM_SH), *args],
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write_note(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ncreated: 2026-08-14\ntype: note\ntags: [x]\nprovenance: test\n---\n# {title}\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Case 2: scan-frontmatter succeeds under VAULT_BRIDGE_VAULT_PATH, invoked as Step 5 would
# ---------------------------------------------------------------------------

def case_scan_frontmatter_non_default_vault(errors: list) -> None:
    print("\ncase: scan_frontmatter_non_default_vault")
    with tempfile.TemporaryDirectory() as vault:
        _write_note(Path(vault) / "notes" / "one.md", "One")
        # scan_dir with no --path == $VAULT_ROOT unscoped, exactly Step 1's construction.
        rc, out, err = _run_ovm(
            "scan-frontmatter", vault,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": vault},
        )
        _assert(rc == 0, f"scan-frontmatter succeeds under a non-default vault (stderr: {err!r})", errors)
        try:
            records = json.loads(out)
        except json.JSONDecodeError:
            records = None
        _assert(isinstance(records, list) and len(records) == 1,
                f"one frontmatter record returned (got: {out!r})", errors)


# ---------------------------------------------------------------------------
# Case 3: --path scoping actually narrows the scan target
# ---------------------------------------------------------------------------

def case_path_flag_scopes_scan(errors: list) -> None:
    print("\ncase: path_flag_scopes_scan")
    with tempfile.TemporaryDirectory() as vault:
        _write_note(Path(vault) / "notes" / "in-scope.md", "In scope")
        _write_note(Path(vault) / "sources" / "out-of-scope.md", "Out of scope")

        # Unscoped ($VAULT_ROOT, --path not given): both files.
        rc_all, out_all, err_all = _run_ovm(
            "scan-frontmatter", vault,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": vault},
        )
        _assert(rc_all == 0, f"unscoped scan succeeds (stderr: {err_all!r})", errors)
        all_records = json.loads(out_all) if rc_all == 0 else []
        _assert(len(all_records) == 2,
                f"unscoped scan sees both files (got {len(all_records)})", errors)

        # Scoped ($VAULT_ROOT/notes, --path notes): only the in-scope file — the exact
        # scan_dir construction Step 1 documents ("$VAULT_ROOT/<subdir>" under --path).
        scan_dir = str(Path(vault) / "notes")
        rc_scoped, out_scoped, err_scoped = _run_ovm(
            "scan-frontmatter", scan_dir,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": vault},
        )
        _assert(rc_scoped == 0, f"--path-scoped scan succeeds (stderr: {err_scoped!r})", errors)
        scoped_records = json.loads(out_scoped) if rc_scoped == 0 else []
        _assert(len(scoped_records) == 1 and "in-scope.md" in scoped_records[0].get("path", ""),
                f"--path notes scan sees only the in-scope file (got: {out_scoped!r})", errors)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    errors: list = []

    case_skill_md_wiring(errors)
    case_scan_frontmatter_non_default_vault(errors)
    case_path_flag_scopes_scan(errors)

    print()
    if errors:
        print(f"FAIL: {len(errors)} case(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("OK: all 3 audit-vault-root-wiring cases passed")


if __name__ == "__main__":
    main()
