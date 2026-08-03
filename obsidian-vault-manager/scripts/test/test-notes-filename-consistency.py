#!/usr/bin/env python3
"""
#531 — notes/ filename convention must agree between the two enforcement points:
audit-validate.py's filename_conforms() (report-time, E3) and
vault-bridge/hooks/pre-write-guard.sh's notes/ pattern (write-time).

Before the fix, a bare YYYY-MM- prefixed filename under notes/ (e.g.
notes/2026-08-03.md) passed the write-time guard but was flagged P0 by audit —
allowed in, then reported as a violation on every subsequent run. This drives
both implementations over the same filename set and asserts identical verdicts.

Run: python3 obsidian-vault-manager/scripts/test/test-notes-filename-consistency.py
  -> "OK: all cases passed" (exit 0) / "FAILED: N case(s) failed" (exit 1).
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parents[2]
AUDIT_PY = _HERE / "audit-validate.py"
HOOK = ROOT / "vault-bridge" / "hooks" / "pre-write-guard.sh"

_spec = importlib.util.spec_from_file_location("audit_validate", AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
filename_conforms = _mod.filename_conforms

CASES = [
    # (filename under notes/, expect_conforms)
    ("my-thought.md", True),
    ("decision-2026-04-12-x.md", True),
    ("plan-2026-05-26-pr1-rollout.md", True),
    ("2026-08-03.md", False),  # #531 repro: bare ISO date, notes/ reserves this shape for sources/
    ("diary/2026-08-03.md", False),  # #531's actual repro path: same rule, one subfolder deep
]


def guard_conforms(vault_root: str, rel_path: str) -> bool:
    """True if pre-write-guard (strict mode) allows the write; False if it blocks it."""
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": f"{vault_root}/{rel_path}"},
    }
    env = os.environ.copy()
    for key in ("VAULT_BRIDGE_DISABLE", "VAULT_BRIDGE_WRITE_CONTRACT",
                "VAULT_BRIDGE_VAULT_PATH"):
        env.pop(key, None)
    env["VAULT_BRIDGE_VAULT_ROOT"] = vault_root
    env["VAULT_BRIDGE_STRICT_NAMING"] = "1"
    result = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                             capture_output=True, text=True, env=env)
    return result.returncode == 0


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as vault_root:
        os.makedirs(f"{vault_root}/notes", exist_ok=True)
        for filename, expect in CASES:
            rel = f"notes/{filename}"
            audit_says = filename_conforms(Path(rel))
            guard_says = guard_conforms(vault_root, rel)
            if audit_says != expect:
                print(f"FAIL {rel}: filename_conforms()={audit_says}, expected {expect}", file=sys.stderr)
                failures += 1
                continue
            if guard_says != expect:
                print(f"FAIL {rel}: pre-write-guard.sh allows={guard_says}, expected {expect}", file=sys.stderr)
                failures += 1
                continue
            if audit_says != guard_says:
                print(f"FAIL {rel}: audit={audit_says} vs guard={guard_says} DISAGREE", file=sys.stderr)
                failures += 1
                continue
            print(f"  ok   {rel}: both agree (conforms={expect})")

    if failures:
        print(f"FAILED: {failures} case(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
