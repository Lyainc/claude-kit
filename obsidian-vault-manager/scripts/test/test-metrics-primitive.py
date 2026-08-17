#!/usr/bin/env python3
"""
`ovm-primitives.sh metrics` concurrency + error-contract regression (#670).

Before #670, the metrics sidecar was keyed only by a hash of the vault path, so two
concurrent `/audit` runs against the same vault clobbered each other's start/stop/report
data. The fix threads an explicit per-run token through start -> stop -> report and keys
the sidecar file by `<vault_tag>-<token>`. This test drives the primitive via subprocess
(never traces the Python inline) and pins three things the PR review found untested:
same-vault concurrent starts get distinct tokens and non-clobbering files, `stop`/`report`
without a token is a clear exit-1 error (not a silent no-op), and an unknown token is
reported as "no session", not misread as an empty one.

Run: python3 obsidian-vault-manager/scripts/test/test-metrics-primitive.py
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


def _run(args: list, vault: Path, tmpdir: Path):
    env = {**os.environ, "VAULT_ROOT": str(vault), "TMPDIR": str(tmpdir)}
    return subprocess.run(
        ["bash", str(_PRIM_SH), "metrics", *args],
        capture_output=True, text=True, env=env,
    )


def case_stop_missing_token_errors(errors: list) -> None:
    print("\ncase: stop_missing_token_errors")
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as tmpdir:
        proc = _run(["stop"], Path(vault), Path(tmpdir))
        _assert(proc.returncode == 1, f"exit 1 with no token (got {proc.returncode})", errors)
        _assert("token" in proc.stderr.lower(), f"error names the missing token (got {proc.stderr!r})", errors)


def case_report_missing_token_errors(errors: list) -> None:
    print("\ncase: report_missing_token_errors")
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as tmpdir:
        proc = _run(["report"], Path(vault), Path(tmpdir))
        _assert(proc.returncode == 1, f"exit 1 with no token (got {proc.returncode})", errors)
        _assert("token" in proc.stderr.lower(), f"error names the missing token (got {proc.stderr!r})", errors)


def case_unknown_token_is_no_session_not_empty(errors: list) -> None:
    print("\ncase: unknown_token_is_no_session_not_empty")
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as tmpdir:
        proc = _run(["stop", "deadbeef"], Path(vault), Path(tmpdir))
        _assert(proc.returncode == 1, f"exit 1 on an unknown token (got {proc.returncode})", errors)
        _assert("no metrics session" in proc.stderr.lower(),
                f"error distinguishes 'no session' from an empty one (got {proc.stderr!r})", errors)


def case_concurrent_same_vault_distinct_tokens_isolated(errors: list) -> None:
    """Two `start` calls against the SAME vault (same vault_tag) must not share a file —
    the exact collision #670 fixes."""
    print("\ncase: concurrent_same_vault_distinct_tokens_isolated")
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as tmpdir:
        start_a = _run(["start", "run-a"], Path(vault), Path(tmpdir))
        start_b = _run(["start", "run-b"], Path(vault), Path(tmpdir))
        _assert(start_a.returncode == 0 and start_b.returncode == 0,
                f"both starts exit 0 (got {start_a.returncode}, {start_b.returncode})", errors)

        token_a = json.loads(start_a.stdout)["token"]
        token_b = json.loads(start_b.stdout)["token"]
        _assert(token_a != token_b, f"distinct tokens for concurrent starts (got {token_a!r}, {token_b!r})", errors)

        stop_a = _run(["stop", token_a], Path(vault), Path(tmpdir))
        stop_b = _run(["stop", token_b], Path(vault), Path(tmpdir))
        _assert(stop_a.returncode == 0 and stop_b.returncode == 0,
                f"both stops exit 0 (got {stop_a.returncode}, {stop_b.returncode})", errors)

        report_a = json.loads(_run(["report", token_a], Path(vault), Path(tmpdir)).stdout)
        report_b = json.loads(_run(["report", token_b], Path(vault), Path(tmpdir)).stdout)
        _assert(report_a["label"] == "run-a", f"report(token_a) is run-a's own data (got {report_a.get('label')!r})", errors)
        _assert(report_b["label"] == "run-b", f"report(token_b) is run-b's own data (got {report_b.get('label')!r})", errors)


def case_start_stop_report_roundtrip(errors: list) -> None:
    print("\ncase: start_stop_report_roundtrip")
    with tempfile.TemporaryDirectory() as vault, tempfile.TemporaryDirectory() as tmpdir:
        start = _run(["start", "roundtrip"], Path(vault), Path(tmpdir))
        _assert(start.returncode == 0, f"start exits 0 (got {start.returncode})", errors)
        token = json.loads(start.stdout)["token"]

        stop = _run(["stop", token], Path(vault), Path(tmpdir))
        _assert(stop.returncode == 0, f"stop exits 0 (got {stop.returncode})", errors)
        _assert(json.loads(stop.stdout)["elapsed_ms"] >= 0, "stop reports a non-negative elapsed_ms", errors)

        report = json.loads(_run(["report", token], Path(vault), Path(tmpdir)).stdout)
        _assert(report["elapsed_ms"] is not None, "report shows elapsed_ms set after stop", errors)


def main() -> int:
    errors: list = []
    for case in (
        case_stop_missing_token_errors,
        case_report_missing_token_errors,
        case_unknown_token_is_no_session_not_empty,
        case_concurrent_same_vault_distinct_tokens_isolated,
        case_start_stop_report_roundtrip,
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
