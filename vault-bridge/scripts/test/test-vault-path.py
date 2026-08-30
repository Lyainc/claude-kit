#!/usr/bin/env python3
"""
Regression test — vault path resolution for non-default vault locations.

Covers VAULT_BRIDGE_VAULT_PATH (userConfig) and VAULT_BRIDGE_VAULT_ROOT (env
override) across hooks, Python helpers, and obsidian-vault-manager's
ovm-primitives.sh (#613/#616 — ovm-primitives.sh was the one place in the repo
that fell straight to $HOME/vault, ignoring both env vars).

Priority contract: VAULT_BRIDGE_VAULT_ROOT > VAULT_BRIDGE_VAULT_PATH > ~/vault
(ovm-primitives.sh additionally honors a direct VAULT_ROOT override, on top of
that chain, for test/caller back-compat.)

Test matrix:
  1. pre-write-guard also respects VAULT_BRIDGE_VAULT_PATH
  2. Python _default_vault_root() priority order
  3. ovm-primitives.sh resolves VAULT_BRIDGE_VAULT_PATH (#613 repro: scan-frontmatter
     against a non-default vault used to die in validate_vault_path)
  4. ovm-primitives.sh: VAULT_BRIDGE_VAULT_ROOT wins over VAULT_BRIDGE_VAULT_PATH
  5. ovm-primitives.sh: AUDIT_STATE_PATH derives from the resolved VAULT_ROOT, not a
     hardcoded $HOME/vault (#613's second bug — audit state written to the wrong vault)

Run: python3 vault-bridge/scripts/test/test-vault-path.py
Exit 0 on pass, 1 on fail.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRITE_HOOK  = ROOT / "hooks" / "pre-write-guard.sh"
SCRIPTS     = ROOT / "scripts"
OVM_PRIM    = ROOT.parent / "obsidian-vault-manager" / "scripts" / "ovm-primitives.sh"


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


def _write_payload(file_path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path}}


def _run_ovm(*args: str, env_overrides: dict) -> tuple[int, str, str]:
    env = os.environ.copy()
    for k in ("VAULT_ROOT", "VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH",
              "AUDIT_STATE_PATH", "VAULT_BRIDGE_DISABLE"):
        env.pop(k, None)
    env.update(env_overrides)
    proc = subprocess.run(
        ["bash", str(OVM_PRIM), *args],
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Case 1: pre-write-guard also respects VAULT_BRIDGE_VAULT_PATH
# ---------------------------------------------------------------------------

def case_write_guard_vault_path(errors: list[str]) -> None:
    """pre-write-guard must enforce naming rules inside custom VAULT_BRIDGE_VAULT_PATH."""
    print("\ncase: write_guard_vault_path")
    with tempfile.TemporaryDirectory() as custom_vault:
        # Valid name → no naming violation (v4: sources/ pattern)
        today = datetime.date.today().isoformat()
        valid_path = f"{custom_vault}/sources/session-{today}.md"
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

        # Invalid name → naming warning emitted (sources/ pattern mismatch)
        bad_path = f"{custom_vault}/sources/random-name.md"
        rc2, out2, _ = _run_hook(
            WRITE_HOOK,
            _write_payload(bad_path),
            vault_path=custom_vault,
        )
        _assert(rc2 == 0, "exit 0 (log-only mode)", errors)
        _assert("naming warning" in out2 or "NAMING VIOLATION" in out2,
                "naming warning emitted for bad filename in custom vault", errors)


# ---------------------------------------------------------------------------
# Case 2: Python _default_vault_root() priority order
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
# Case 3: ovm-primitives.sh resolves VAULT_BRIDGE_VAULT_PATH (#613 repro)
# ---------------------------------------------------------------------------

def case_ovm_primitives_vault_path(errors: list[str]) -> None:
    """scan-frontmatter against a non-default vault must not die in validate_vault_path."""
    print("\ncase: ovm_primitives_vault_path")
    with tempfile.TemporaryDirectory() as custom_vault:
        rc, out, err = _run_ovm(
            "scan-frontmatter", custom_vault,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": custom_vault},
        )
        _assert(rc == 0, f"scan-frontmatter succeeds under VAULT_BRIDGE_VAULT_PATH (stderr: {err!r})", errors)
        _assert(out.strip() == "[]", "empty vault scans to an empty JSON array", errors)


# ---------------------------------------------------------------------------
# Case 4: ovm-primitives.sh — VAULT_BRIDGE_VAULT_ROOT wins over VAULT_BRIDGE_VAULT_PATH
# ---------------------------------------------------------------------------

def case_ovm_primitives_priority(errors: list[str]) -> None:
    """VAULT_BRIDGE_VAULT_ROOT must win when both env vars are set (mirrors the Python case)."""
    print("\ncase: ovm_primitives_priority")
    with tempfile.TemporaryDirectory() as root_vault, tempfile.TemporaryDirectory() as path_vault:
        # Scanning root_vault must succeed (it is the resolved VAULT_ROOT)...
        rc, _, err = _run_ovm(
            "scan-frontmatter", root_vault,
            env_overrides={
                "VAULT_BRIDGE_VAULT_ROOT": root_vault,
                "VAULT_BRIDGE_VAULT_PATH": path_vault,
            },
        )
        _assert(rc == 0, f"VAULT_BRIDGE_VAULT_ROOT dir accepted (stderr: {err!r})", errors)
        # ...while scanning path_vault must fail (it lost to VAULT_BRIDGE_VAULT_ROOT).
        rc2, _, err2 = _run_ovm(
            "scan-frontmatter", path_vault,
            env_overrides={
                "VAULT_BRIDGE_VAULT_ROOT": root_vault,
                "VAULT_BRIDGE_VAULT_PATH": path_vault,
            },
        )
        _assert(rc2 != 0, "VAULT_BRIDGE_VAULT_PATH dir rejected once VAULT_BRIDGE_VAULT_ROOT is set", errors)
        _assert("not under VAULT_ROOT" in err2, f"rejection names the reason (stderr: {err2!r})", errors)


# ---------------------------------------------------------------------------
# Case 5: ovm-primitives.sh — AUDIT_STATE_PATH derives from VAULT_ROOT (#613 second bug)
# ---------------------------------------------------------------------------

def case_ovm_audit_state_path(errors: list[str]) -> None:
    """AUDIT_STATE_PATH must default under the resolved VAULT_ROOT, never a hardcoded ~/vault."""
    print("\ncase: ovm_audit_state_path")
    with tempfile.TemporaryDirectory() as custom_vault:
        notes_dir = Path(custom_vault) / "notes"
        notes_dir.mkdir()
        (notes_dir / "foo.md").touch()
        rc, out, err = _run_ovm(
            "audit-state", "mark-clean", "notes/foo.md",
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": custom_vault},
        )
        _assert(rc == 0, f"audit-state mark-clean succeeds (stderr: {err!r})", errors)
        expected_state = Path(custom_vault) / ".ovm" / "audit-state.json"
        _assert(expected_state.is_file(),
                f"audit state written under VAULT_ROOT, not $HOME/vault (expected {expected_state})",
                errors)


# ---------------------------------------------------------------------------
# Case 6: vault-link/SKILL.md Step 2 resolves the vault root, not hardcoded (#700)
# ---------------------------------------------------------------------------

def case_vault_link_no_hardcoded_vault(errors: list[str]) -> None:
    """vault-link/SKILL.md must resolve {vault_root} before scanning, never hardcode ~/vault."""
    print("\ncase: vault_link_no_hardcoded_vault")
    text = (ROOT / "skills" / "vault-link" / "SKILL.md").read_text()

    fences = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
    _assert(len(fences) >= 1, "vault-link SKILL.md has at least one bash fence", errors)
    hardcoded = [f for f in fences if "~/vault" in f]
    _assert(not hardcoded, f"no bash fence hardcodes ~/vault (found: {hardcoded!r})", errors)

    scan_fence = next((f for f in fences if "notes/" in f), "")
    _assert(
        "VAULT_BRIDGE_VAULT_ROOT" in scan_fence and "VAULT_BRIDGE_VAULT_PATH" in scan_fence,
        "Step 2 scan fence resolves via the VAULT_BRIDGE_VAULT_ROOT/VAULT_BRIDGE_VAULT_PATH chain",
        errors,
    )
    _assert(
        '"$VAULT_ROOT/notes/"' in scan_fence,
        "Step 2 ls command scans $VAULT_ROOT, not a hardcoded path",
        errors,
    )
    # Resolving $VAULT_ROOT into a shell variable is useless to the calling agent unless the
    # fence also echoes it — Bash tool calls don't preserve shell state across turns, so the
    # resolved value must appear in this call's stdout for later steps to fill in `${VAULT_ROOT}`.
    _assert(
        'echo "$VAULT_ROOT"' in scan_fence,
        "Step 2 fence echoes the resolved $VAULT_ROOT for the caller to read back",
        errors,
    )
    # Prose shown to the user during Step 2 must reference the resolved path too, or a
    # custom-vault user gets scanned correctly but told the wrong location (#700 follow-on).
    # (The frontmatter `description` and intro sentence describe the default location in
    # general terms and are exempt — only actionable Step 2 / Rules prose matters here.)
    stale_prose = [
        "`~/vault/notes/` 하위 프로젝트 목록입니다",
        "mkdir -p ~/vault/notes/{name}/",
        "`~/vault/notes/` 디렉토리가 없거나 비어 있습니다",
        "mkdir -p ~/vault/notes/{project-name}",
        "vault root가 `~/vault/`가 아닌 경우",
        "inside `~/vault/`",
    ]
    found_stale = [s for s in stale_prose if s in text]
    _assert(not found_stale, f"no stale ~/vault/notes/ prose left in Step 2 / Rules (found: {found_stale!r})", errors)


# ---------------------------------------------------------------------------
# Case 7: vault-save/SKILL.md step 3 aborts instead of mkdir when vault_root is
# missing (#697)
# ---------------------------------------------------------------------------

def case_vault_save_aborts_without_vault_root(errors: list[str]) -> None:
    """vault-save/SKILL.md must stop, not mkdir -p, when {vault_root} does not exist."""
    print("\ncase: vault_save_aborts_without_vault_root")
    text = (ROOT / "skills" / "vault-save" / "SKILL.md").read_text()

    _assert(
        "mkdir -p` the target directory before writing" not in text,
        "old unconditional 'mkdir -p the target directory' step is gone",
        errors,
    )

    step3_match = re.search(r"\n3\.\s.*?(?=\n4\.\s)", text, re.DOTALL)
    _assert(step3_match is not None, "step 3 is present and followed by step 4", errors)
    step3 = step3_match.group(0) if step3_match else ""

    _assert("not** exist" in step3 or "not exist" in step3,
            "step 3 checks whether {vault_root} does not exist", errors)
    _assert("stop" in step3.lower(),
            "step 3 stops instead of writing when {vault_root} is missing", errors)
    _assert("never" in step3.lower() and "mkdir -p" in step3.lower(),
            "step 3 explicitly forbids mkdir -p on {vault_root} itself", errors)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    errors: list[str] = []

    case_write_guard_vault_path(errors)
    case_python_default_vault_root(errors)
    case_ovm_primitives_vault_path(errors)
    case_ovm_primitives_priority(errors)
    case_ovm_audit_state_path(errors)
    case_vault_link_no_hardcoded_vault(errors)
    case_vault_save_aborts_without_vault_root(errors)

    print()
    if errors:
        print(f"FAIL: {len(errors)} case(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: all {7} vault-path cases passed")


if __name__ == "__main__":
    main()
