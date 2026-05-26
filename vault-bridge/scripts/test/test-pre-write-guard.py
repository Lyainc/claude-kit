#!/usr/bin/env python3
"""
Regression test for `vault-bridge/hooks/pre-write-guard.sh` —
Write Role Contract enforcement + filename validation.

Policy (2026-05-12): vault writes must be user-initiated (main context,
slash commands). Subagent vault writes are out of policy and are
detected via agent identifier fields in the PreToolUse payload.

Run: python3 vault-bridge/scripts/test/test-pre-write-guard.py
Exit 0 on pass, 1 on fail.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "vault-bridge" / "hooks" / "pre-write-guard.sh"


def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _run(payload: dict, env_overrides: dict | None = None, vault_root: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Always unset the env vars under test so each case is hermetic
    for key in ("VAULT_BRIDGE_DISABLE", "VAULT_BRIDGE_STRICT_NAMING",
                "VAULT_BRIDGE_WRITE_CONTRACT", "VAULT_BRIDGE_VAULT_ROOT",
                "VAULT_BRIDGE_VAULT_PATH"):
        env.pop(key, None)
    if vault_root is not None:
        env["VAULT_BRIDGE_VAULT_ROOT"] = vault_root
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def _make_payload(
    file_path: str,
    tool_name: str = "Write",
    agent_id_field: str | None = None,
    agent_id_value: str | None = None,
) -> dict:
    payload: dict = {
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
    }
    if agent_id_field and agent_id_value:
        payload[agent_id_field] = agent_id_value
    return payload


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def case_main_context_inbox_write(errors: list[str], vault_root: str) -> None:
    """No agent_id + valid path → clean pass (exit 0, stdout empty)."""
    print("\ncase: main_context_inbox_write")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_subagent_enforce_default(errors: list[str], vault_root: str) -> None:
    """subagent_type present + no VAULT_BRIDGE_WRITE_CONTRACT → enforce (actual default at line 86)."""
    # TODO: pre-write-guard.sh:86 default=enforce vs 주석/docs warn 불일치 — 별도 PR로 추적
    print("\ncase: subagent_enforce_default")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="vault-searcher")
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)
    _assert("systemMessage" in proc.stdout and "vault-bridge contract" in proc.stdout,
            f"stdout contains systemMessage with vault-bridge contract (got: {proc.stdout!r})", errors)


def case_subagent_warn_explicit(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_WRITE_CONTRACT=warn → same as default warn."""
    print("\ncase: subagent_warn_explicit")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="vault-searcher")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "warn"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert("CONTRACT WARNING" in proc.stderr,
            f"stderr contains CONTRACT WARNING (got: {proc.stderr!r})", errors)
    _assert("systemMessage" in proc.stdout and "vault-bridge contract" in proc.stdout,
            f"stdout contains systemMessage with vault-bridge contract (got: {proc.stdout!r})", errors)


def case_subagent_enforce(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_WRITE_CONTRACT=enforce → permissionDecision:deny."""
    print("\ncase: subagent_enforce")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)


def case_subagent_off(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_WRITE_CONTRACT=off → contract bypassed; stdout empty."""
    print("\ncase: subagent_off")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "off"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_assets_passthrough(errors: list[str], vault_root: str) -> None:
    """assets/ is passthrough (v4) — exits 0 cleanly; no contract check, no naming check."""
    print("\ncase: assets_passthrough")
    path = f"{vault_root}/assets/image.png"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "",
            f"stdout empty (assets/ passthrough — no contract or naming check; got: {proc.stdout!r})", errors)


def case_notes_valid_filename(errors: list[str], vault_root: str) -> None:
    """notes/ with valid kebab-case filename → clean pass (exit 0, stdout empty)."""
    print("\ncase: notes_valid_filename")
    path = f"{vault_root}/notes/my-thought.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_subfolder_valid(errors: list[str], vault_root: str) -> None:
    """notes/ sub-folder with valid kebab filename → clean pass (top_dir=notes; filename validated)."""
    print("\ncase: notes_subfolder_valid")
    path = f"{vault_root}/notes/diary/my-entry.md"
    payload = _make_payload(path)
    proc = _run(payload, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_notes_violation(errors: list[str], vault_root: str) -> None:
    """notes/ with uppercase filename → naming violation (VAULT_BRIDGE_STRICT_NAMING=1 → exit 2)."""
    print("\ncase: notes_violation")
    path = f"{vault_root}/notes/MyNote.md"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_filename_violation_warn_mode(errors: list[str], vault_root: str) -> None:
    """Subagent + bad filename + warn → both CONTRACT WARNING and NAMING VIOLATION in stderr."""
    print("\ncase: filename_violation_warn_mode")
    path = f"{vault_root}/inbox/badname.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "warn"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert("CONTRACT WARNING" in proc.stderr,
            f"stderr contains CONTRACT WARNING (got: {proc.stderr!r})", errors)
    _assert("NAMING VIOLATION" in proc.stderr,
            f"stderr contains NAMING VIOLATION (got: {proc.stderr!r})", errors)


def case_filename_violation_strict_naming(errors: list[str], vault_root: str) -> None:
    """No agent_id + bad filename + VAULT_BRIDGE_STRICT_NAMING=1 → exit 2."""
    print("\ncase: filename_violation_strict_naming")
    path = f"{vault_root}/inbox/badname.md"
    payload = _make_payload(path)
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_STRICT_NAMING": "1"}, vault_root=vault_root)
    _assert(proc.returncode == 2, f"exit 2 (got: {proc.returncode})", errors)


def case_subagent_filename_violation_enforce(errors: list[str], vault_root: str) -> None:
    """Subagent + bad filename + enforce → deny fires first; filename check never reached."""
    print("\ncase: subagent_filename_violation_enforce")
    path = f"{vault_root}/inbox/badname.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"}, vault_root=vault_root)
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert('"permissionDecision":"deny"' in proc.stdout.replace(" ", ""),
            f"stdout contains permissionDecision:deny (got: {proc.stdout!r})", errors)
    # Must NOT also emit a naming violation (contract deny exits before that check)
    _assert("NAMING VIOLATION" not in proc.stderr,
            f"stderr must not contain NAMING VIOLATION (got: {proc.stderr!r})", errors)


def case_kill_switch(errors: list[str], vault_root: str) -> None:
    """VAULT_BRIDGE_DISABLE=1 → exit 0, stdout empty regardless of contract mode."""
    print("\ncase: kill_switch")
    path = f"{vault_root}/inbox/session-2026-05-12.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="vault-searcher")
    proc = _run(
        payload,
        env_overrides={"VAULT_BRIDGE_DISABLE": "1", "VAULT_BRIDGE_WRITE_CONTRACT": "enforce"},
        vault_root=vault_root,
    )
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


def case_non_vault_path(errors: list[str]) -> None:
    """Subagent writing outside vault → exit 0, stdout empty (unchanged behavior)."""
    print("\ncase: non_vault_path")
    path = "/tmp/some-file.md"
    payload = _make_payload(path, agent_id_field="subagent_type", agent_id_value="executor")
    proc = _run(payload, env_overrides={"VAULT_BRIDGE_WRITE_CONTRACT": "enforce"})
    _assert(proc.returncode == 0, "exit 0", errors)
    _assert(proc.stdout.strip() == "", f"stdout empty (got: {proc.stdout!r})", errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"Running pre-write-guard regression tests against: {HOOK}")

    if not HOOK.exists():
        print(f"ERROR: hook not found at {HOOK}", file=sys.stderr)
        return 1

    errors: list[str] = []

    # Provision a temporary fake vault root so tests are hermetic and the real
    # ~/vault is never touched. The hook only requires the directory to exist.
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = tmp
        # Create the top-level dirs the hook navigates (v4: inbox, notes, assets)
        for d in ("inbox", "notes", "assets"):
            Path(vault_root, d).mkdir(parents=True, exist_ok=True)
        # Sub-folder for notes subfolder test
        Path(vault_root, "notes", "diary").mkdir(parents=True, exist_ok=True)

        case_main_context_inbox_write(errors, vault_root)
        case_subagent_enforce_default(errors, vault_root)
        case_subagent_warn_explicit(errors, vault_root)
        case_subagent_enforce(errors, vault_root)
        case_subagent_off(errors, vault_root)
        case_assets_passthrough(errors, vault_root)
        case_notes_valid_filename(errors, vault_root)
        case_notes_subfolder_valid(errors, vault_root)
        case_notes_violation(errors, vault_root)
        case_filename_violation_warn_mode(errors, vault_root)
        case_filename_violation_strict_naming(errors, vault_root)
        case_subagent_filename_violation_enforce(errors, vault_root)
        case_kill_switch(errors, vault_root)

    # Non-vault path test needs no vault_root provisioning
    case_non_vault_path(errors)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
