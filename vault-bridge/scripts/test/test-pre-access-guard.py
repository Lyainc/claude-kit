#!/usr/bin/env python3
"""
Regression test for `vault-bridge/hooks/pre-access-guard.sh` subagent
self-exemption.

The hook fires on every Read/Grep/Glob to ~/vault/ and emits a systemMessage
suggesting vault-searcher. Without the self-exemption, the hook fires even
when vault-searcher IS the caller — the haiku model interprets its own
warning as a denial and aborts. A regression here would silently re-introduce
the self-confusion loop with no error: vault-searcher reads would still work
but the model would abort after each one.

Run: python3 vault-bridge/scripts/test/test-pre-access-guard.py
Exit 0 on pass, 1 on fail.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "pre-access-guard.sh"


def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def _run_hook(
    payload_dict: dict,
    env: dict | None = None,
    vault_root: str | None = None,
) -> tuple[int, str, str]:
    """
    Pipe payload_dict as JSON to the hook via stdin.
    Returns (returncode, stdout, stderr).
    vault_root defaults to a temp directory that exists (so the hook reaches
    the path-check logic). Pass an empty/nonexistent path to test vault-absent
    fast-exit.
    """
    merged_env = os.environ.copy()
    if vault_root is not None:
        merged_env["VAULT_BRIDGE_VAULT_ROOT"] = vault_root
    if env:
        merged_env.update(env)

    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload_dict),
        capture_output=True,
        text=True,
        env=merged_env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _vault_read_payload(
    path: str,
    extra: dict | None = None,
) -> dict:
    """Minimal Read payload targeting path."""
    base: dict = {
        "tool_name": "Read",
        "tool_input": {"file_path": path},
    }
    if extra:
        base.update(extra)
    return base


def _cleanup_session(session_id: str) -> None:
    d = f"/tmp/vault-bridge-session-{session_id}"
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def case_vault_searcher_subagent_type(errors: list[str], vault_dir: str) -> None:
    """subagent_type: vault-searcher → exit 0, no stdout."""
    print("\ncase: vault_searcher_subagent_type")
    sid = "test-pre-access-subagent_type"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"subagent_type": "vault-searcher"},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty (got: {out!r})", errors)
    _cleanup_session(sid)


def case_vault_searcher_namespaced(errors: list[str], vault_dir: str) -> None:
    """subagent_type: vault-bridge:vault-searcher → exit 0, no stdout."""
    print("\ncase: vault_searcher_namespaced")
    sid = "test-pre-access-namespaced"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"subagent_type": "vault-bridge:vault-searcher"},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty (got: {out!r})", errors)
    _cleanup_session(sid)


def case_vault_searcher_agent_name(errors: list[str], vault_dir: str) -> None:
    """agent_name: vault-searcher → exit 0, no stdout."""
    print("\ncase: vault_searcher_agent_name")
    sid = "test-pre-access-agent_name"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"agent_name": "vault-searcher"},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty (got: {out!r})", errors)
    _cleanup_session(sid)


def case_vault_searcher_agent_dot_name(errors: list[str], vault_dir: str) -> None:
    """agent.name: vault-searcher → exit 0, no stdout."""
    print("\ncase: vault_searcher_agent_dot_name")
    sid = "test-pre-access-agent_dot_name"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"agent": {"name": "vault-searcher"}},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty (got: {out!r})", errors)
    _cleanup_session(sid)


def case_vault_searcher_attribution(errors: list[str], vault_dir: str) -> None:
    """attributionAgent: vault-bridge:vault-searcher → exit 0, no stdout."""
    print("\ncase: vault_searcher_attribution")
    sid = "test-pre-access-attribution"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"attributionAgent": "vault-bridge:vault-searcher"},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty (got: {out!r})", errors)
    _cleanup_session(sid)


def case_main_context_first_access(errors: list[str], vault_dir: str) -> None:
    """No agent identifier + vault Read → exit 0, stdout contains warning, counter=1."""
    print("\ncase: main_context_first_access")
    sid = "test-pre-access-main-first"
    _cleanup_session(sid)
    payload = _vault_read_payload(os.path.join(vault_dir, "note.md"))
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert("Direct vault access detected" in out, f"systemMessage emitted (got: {out!r})", errors)
    # Counter file should contain 1
    counter_file = f"/tmp/vault-bridge-session-{sid}/direct-access-count"
    count_val = ""
    if os.path.isfile(counter_file):
        count_val = open(counter_file).read().strip()
    _assert(count_val == "1", f"counter=1 after first access (got: {count_val!r})", errors)
    _cleanup_session(sid)


def case_other_subagent(errors: list[str], vault_dir: str) -> None:
    """subagent_type: executor (non-vault-searcher) → warning still emitted."""
    print("\ncase: other_subagent")
    sid = "test-pre-access-executor"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"subagent_type": "executor"},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert("Direct vault access detected" in out, f"systemMessage emitted for non-exempt agent (got: {out!r})", errors)
    _cleanup_session(sid)


def case_kill_switch(errors: list[str], vault_dir: str) -> None:
    """VAULT_BRIDGE_DISABLE=1 → exit 0, stdout empty even with vault-searcher identifier."""
    print("\ncase: kill_switch")
    sid = "test-pre-access-kill-switch"
    _cleanup_session(sid)
    payload = _vault_read_payload(
        os.path.join(vault_dir, "note.md"),
        {"subagent_type": "vault-searcher"},
    )
    rc, out, _ = _run_hook(
        payload,
        env={"CLAUDE_SESSION_ID": sid, "VAULT_BRIDGE_DISABLE": "1"},
        vault_root=vault_dir,
    )
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty under kill switch (got: {out!r})", errors)
    _cleanup_session(sid)


def case_non_vault_path(errors: list[str], vault_dir: str) -> None:
    """vault-searcher identifier + non-vault path → exit 0, stdout empty (path filter)."""
    print("\ncase: non_vault_path")
    sid = "test-pre-access-non-vault"
    _cleanup_session(sid)
    # Even without exemption logic, /tmp/somefile.md is outside vault — no warning.
    # With vault-searcher: exemption fires first, but end result is the same.
    payload = _vault_read_payload(
        "/tmp/not-in-vault/file.md",
        {"subagent_type": "vault-searcher"},
    )
    rc, out, _ = _run_hook(payload, env={"CLAUDE_SESSION_ID": sid}, vault_root=vault_dir)
    _assert(rc == 0, "exit 0", errors)
    _assert(out.strip() == "", f"stdout empty for non-vault path (got: {out!r})", errors)
    _cleanup_session(sid)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print(f"Running pre-access-guard regression tests against: {HOOK}")

    if not HOOK.exists():
        print(f"ERROR: hook not found at {HOOK}", file=sys.stderr)
        return 1

    errors: list[str] = []

    # Create a real temp directory to stand in for ~/vault so the hook's
    # `[ ! -d "$VAULT_ROOT" ]` guard doesn't short-circuit the path check.
    with tempfile.TemporaryDirectory() as vault_dir:
        # Create a file inside so Read payloads point to something under vault_dir.
        Path(vault_dir, "note.md").write_text("# stub\n", encoding="utf-8")

        case_vault_searcher_subagent_type(errors, vault_dir)
        case_vault_searcher_namespaced(errors, vault_dir)
        case_vault_searcher_agent_name(errors, vault_dir)
        case_vault_searcher_agent_dot_name(errors, vault_dir)
        case_vault_searcher_attribution(errors, vault_dir)
        case_main_context_first_access(errors, vault_dir)
        case_other_subagent(errors, vault_dir)
        case_kill_switch(errors, vault_dir)
        case_non_vault_path(errors, vault_dir)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
