#!/usr/bin/env python3
"""
Regression test — vault path resolution for non-default vault locations.

Covers VAULT_BRIDGE_VAULT_PATH (userConfig) and VAULT_BRIDGE_VAULT_ROOT (env
override) across hooks and Python helpers.

Priority contract: VAULT_BRIDGE_VAULT_ROOT > VAULT_BRIDGE_VAULT_PATH > ~/vault

Test matrix:
  1. VAULT_BRIDGE_VAULT_PATH → custom vault dir (hook intercepts reads inside it)
  2. VAULT_BRIDGE_VAULT_ROOT overrides VAULT_BRIDGE_VAULT_PATH
  3. Neither env var set → default path ($HOME/vault); dir absent → silent exit
  4. VAULT_BRIDGE_VAULT_PATH with leading tilde → properly expanded
  5. Python _default_vault_root() priority order

Run: python3 vault-bridge/scripts/test/test-vault-path.py
Exit 0 on pass, 1 on fail.
"""

import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCESS_HOOK = ROOT / "hooks" / "pre-access-guard.sh"
WRITE_HOOK  = ROOT / "hooks" / "pre-write-guard.sh"
SCRIPTS     = ROOT / "scripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _run_hook(
    hook: Path,
    payload: dict,
    *,
    vault_root: str | None = None,
    vault_path: str | None = None,
    extra_env: dict | None = None,
) -> tuple[int, str, str]:
    env = os.environ.copy()
    # Hermetic: strip all vault-path vars so developer's shell state can't leak in
    for k in ("VAULT_BRIDGE_DISABLE", "VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH"):
        env.pop(k, None)
    if vault_root is not None:
        env["VAULT_BRIDGE_VAULT_ROOT"] = vault_root
    if vault_path is not None:
        env["VAULT_BRIDGE_VAULT_PATH"] = vault_path
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["bash", str(hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _read_payload(file_path: str) -> dict:
    return {"tool_name": "Read", "tool_input": {"file_path": file_path}}


def _write_payload(file_path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path}}


# ---------------------------------------------------------------------------
# Case 1: VAULT_BRIDGE_VAULT_PATH → hook intercepts reads inside custom vault
# ---------------------------------------------------------------------------

def case_vault_path_intercepts_reads(errors: list[str]) -> None:
    """Hook must warn when reading inside VAULT_BRIDGE_VAULT_PATH directory."""
    print("\ncase: vault_path_intercepts_reads")
    with tempfile.TemporaryDirectory() as custom_vault:
        target = f"{custom_vault}/30_Notes/my-note.md"
        rc, out, _ = _run_hook(ACCESS_HOOK, _read_payload(target), vault_path=custom_vault)
        _assert(rc == 0, "exit 0 (never blocks)", errors)
        _assert(
            "VAULT_BRIDGE POLICY" in out or "vault-searcher" in out,
            "systemMessage emitted for read inside custom vault",
            errors,
        )


# ---------------------------------------------------------------------------
# Case 2: VAULT_BRIDGE_VAULT_ROOT overrides VAULT_BRIDGE_VAULT_PATH
# ---------------------------------------------------------------------------

def case_vault_root_overrides_vault_path(errors: list[str]) -> None:
    """VAULT_BRIDGE_VAULT_ROOT must take priority over VAULT_BRIDGE_VAULT_PATH."""
    print("\ncase: vault_root_overrides_vault_path")
    with (
        tempfile.TemporaryDirectory() as root_vault,   # explicit override
        tempfile.TemporaryDirectory() as path_vault,   # userConfig value
    ):
        # Read targets the root_vault (override); path_vault is ignored
        target_in_root = f"{root_vault}/30_Notes/note.md"
        rc, out, _ = _run_hook(
            ACCESS_HOOK,
            _read_payload(target_in_root),
            vault_root=root_vault,
            vault_path=path_vault,
        )
        _assert(rc == 0, "exit 0", errors)
        _assert("VAULT_BRIDGE POLICY" in out or "vault-searcher" in out,
                "intercept fires for VAULT_ROOT path (not PATH path)", errors)

        # Read targets the path_vault; should NOT intercept (root_vault wins)
        target_in_path = f"{path_vault}/30_Notes/note.md"
        rc2, out2, _ = _run_hook(
            ACCESS_HOOK,
            _read_payload(target_in_path),
            vault_root=root_vault,
            vault_path=path_vault,
        )
        _assert(rc2 == 0, "exit 0 for path-vault read", errors)
        _assert("VAULT_BRIDGE POLICY" not in out2,
                "no intercept when reading path_vault (root_vault wins)", errors)


# ---------------------------------------------------------------------------
# Case 3: Vault dir absent → silent exit
# ---------------------------------------------------------------------------

def case_absent_vault_exits_silently(errors: list[str]) -> None:
    """Hooks must exit silently (exit 0, empty stdout) when the resolved vault
    root directory does not exist.  Tested via VAULT_BRIDGE_VAULT_ROOT pointing
    at a nonexistent path — the same fast-exit guard applies regardless of
    which priority level supplies the path."""
    print("\ncase: absent_vault_exits_silently")
    nonexistent = "/tmp/__vault_bridge_nonexistent_vault_test__"
    rc, out, _ = _run_hook(
        ACCESS_HOOK,
        _read_payload(f"{nonexistent}/note.md"),
        vault_root=nonexistent,  # explicit nonexistent → triggers vault-absent guard
    )
    _assert(rc == 0, "exit 0 when vault dir absent", errors)
    _assert(out.strip() == "", "empty stdout (silent pass-through)", errors)


# ---------------------------------------------------------------------------
# Case 4: Tilde expansion in VAULT_BRIDGE_VAULT_PATH
# ---------------------------------------------------------------------------

def case_tilde_expansion(errors: list[str]) -> None:
    """VAULT_BRIDGE_VAULT_PATH with ~/… prefix must expand to $HOME/…."""
    print("\ncase: tilde_expansion_in_vault_path")
    home = str(Path.home())
    # Use a stable path under HOME that we can create temporarily
    with tempfile.TemporaryDirectory(dir=home, prefix=".vb-test-") as tmp:
        rel = Path(tmp).relative_to(home)
        tilde_path = f"~/{rel}"
        target = f"{tmp}/30_Notes/note.md"
        rc, out, _ = _run_hook(
            ACCESS_HOOK,
            _read_payload(target),
            vault_path=tilde_path,
        )
        _assert(rc == 0, "exit 0 with tilde vault_path", errors)
        _assert("VAULT_BRIDGE POLICY" in out or "vault-searcher" in out,
                "intercept fires after tilde expansion", errors)


# ---------------------------------------------------------------------------
# Case 5: pre-write-guard also respects VAULT_BRIDGE_VAULT_PATH
# ---------------------------------------------------------------------------

def case_write_guard_vault_path(errors: list[str]) -> None:
    """pre-write-guard must enforce naming rules inside custom VAULT_BRIDGE_VAULT_PATH."""
    print("\ncase: write_guard_vault_path")
    with tempfile.TemporaryDirectory() as custom_vault:
        # Valid name → no naming violation
        today = datetime.date.today().isoformat()
        valid_path = f"{custom_vault}/00_Inbox/session-{today}.md"
        rc, out, _ = _run_hook(
            WRITE_HOOK,
            _write_payload(valid_path),
            vault_path=custom_vault,
        )
        _assert(rc == 0, "exit 0 for valid filename in custom vault", errors)
        # The write guard will enforce the write contract (no agent_id = main context)
        # so stdout should be empty for a clean write
        _assert("NAMING VIOLATION" not in out,
                "no naming violation for valid session filename", errors)

        # Invalid name → naming warning emitted
        bad_path = f"{custom_vault}/00_Inbox/random-name.md"
        rc2, out2, _ = _run_hook(
            WRITE_HOOK,
            _write_payload(bad_path),
            vault_path=custom_vault,
        )
        _assert(rc2 == 0, "exit 0 (log-only mode)", errors)
        _assert("naming warning" in out2 or "NAMING VIOLATION" in out2,
                "naming warning emitted for bad filename in custom vault", errors)


# ---------------------------------------------------------------------------
# Case 6: Python _default_vault_root() priority order
# ---------------------------------------------------------------------------

def case_python_default_vault_root(errors: list[str]) -> None:
    """_default_vault_root() must respect VAULT_BRIDGE_VAULT_ROOT > VAULT_BRIDGE_VAULT_PATH > ~/vault."""
    print("\ncase: python_default_vault_root_priority")

    script = str(SCRIPTS / "generate-manifest.py")

    def _get_default(env_overrides: dict) -> str:
        env = os.environ.copy()
        for k in ("VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH"):
            env.pop(k, None)
        env.update(env_overrides)
        # Run the module just to evaluate _default_vault_root() via --help (dry)
        # We invoke python directly to call the function without side effects.
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]);"
            "import importlib.util, os; "
            "spec = importlib.util.spec_from_file_location('m', sys.argv[2]); "
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
            "print(m._default_vault_root())"
        )
        proc = subprocess.run(
            ["python3", "-c", code, str(SCRIPTS), script],
            capture_output=True, text=True, env=env,
        )
        return proc.stdout.strip()

    home = str(Path.home())

    # Priority 3 (default): ~/vault
    result = _get_default({})
    _assert(result == f"{home}/vault",
            f"default returns ~/vault (got: {result!r})", errors)

    # Priority 2: VAULT_BRIDGE_VAULT_PATH
    result = _get_default({"VAULT_BRIDGE_VAULT_PATH": "/custom/path/vault"})
    _assert(result == "/custom/path/vault",
            f"VAULT_BRIDGE_VAULT_PATH used (got: {result!r})", errors)

    # Priority 1: VAULT_BRIDGE_VAULT_ROOT wins over VAULT_BRIDGE_VAULT_PATH
    result = _get_default({
        "VAULT_BRIDGE_VAULT_PATH": "/custom/path/vault",
        "VAULT_BRIDGE_VAULT_ROOT": "/override/vault",
    })
    _assert(result == "/override/vault",
            f"VAULT_BRIDGE_VAULT_ROOT wins (got: {result!r})", errors)

    # Tilde expansion
    result = _get_default({"VAULT_BRIDGE_VAULT_PATH": "~/my-vault"})
    _assert(result == f"{home}/my-vault",
            f"tilde expanded in VAULT_BRIDGE_VAULT_PATH (got: {result!r})", errors)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    errors: list[str] = []

    case_vault_path_intercepts_reads(errors)
    case_vault_root_overrides_vault_path(errors)
    case_absent_vault_exits_silently(errors)
    case_tilde_expansion(errors)
    case_write_guard_vault_path(errors)
    case_python_default_vault_root(errors)

    print()
    if errors:
        print(f"FAIL: {len(errors)} case(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: all {6} vault-path cases passed")


if __name__ == "__main__":
    main()
