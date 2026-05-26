#!/usr/bin/env python3
"""
Unit tests for audit-validate.parse_created_date().

Run: python3 obsidian-vault-manager/scripts/test/test-parse-created-date.py
Exit code 0 on pass, 1 on any failure.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from importlib import util as _util  # noqa: E402

_spec = _util.spec_from_file_location("audit_validate", HERE / "audit-validate.py")
_mod = _util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse_created_date = _mod.parse_created_date


def main() -> int:
    cases = [
        # (input, expected, label)
        ("2026-04-15", date(2026, 4, 15), "valid YYYY-MM-DD"),
        ("2024-02-29", date(2024, 2, 29), "valid leap day"),
        ("2020-01-01", date(2020, 1, 1), "valid epoch-ish date"),
        ("2020-13-01", None, "invalid month → None"),
        ("2020-02-30", None, "invalid day → None"),
        ("2020-1-1", None, "non-zero-padded → None"),
        ("2026/04/15", None, "wrong separator → None"),
        ("2026-04-15T00:00:00", None, "iso8601 with time → None (strict YYYY-MM-DD only)"),
        ("not a date", None, "garbage string → None"),
        ("", None, "empty string → None"),
        (None, None, "None input → None"),
        (20260415, None, "int input → None"),
        ([2026, 4, 15], None, "list input → None"),
    ]

    failures = []
    for value, expected, label in cases:
        actual = parse_created_date(value)
        if actual == expected:
            print(f"  ✓ {label}")
        else:
            print(f"  ✗ {label}: expected {expected!r}, got {actual!r}")
            failures.append(label)

    print()
    if failures:
        print(f"FAIL: {len(failures)}/{len(cases)} cases")
        return 1
    print(f"OK: all {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
