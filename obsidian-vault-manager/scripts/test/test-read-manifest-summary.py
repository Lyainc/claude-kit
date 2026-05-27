#!/usr/bin/env python3
"""
Regression test — audit-validate.read_manifest_summary().

Locks the schema_version gate semantics: pre-v3 manifests return None for
promotion_candidate_count (field unavailable), while v3+ manifests always
return an int (possibly 0) so callers can distinguish "field unavailable"
from "no candidates".
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "av", str(ROOT / "audit-validate.py")
)
av = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(av)  # type: ignore[union-attr]


def _write_manifest(vault: Path, payload: dict) -> Path:
    out = vault / ".vault-bridge" / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def main() -> int:
    errors: list[str] = []

    def check(label: str, got, want) -> None:
        if got == want:
            print(f"  ok   {label}")
        else:
            print(f"  FAIL {label}: got {got!r}, want {want!r}", file=sys.stderr)
            errors.append(label)

    print("case: read_manifest_summary schema_version gate")

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)

        # No manifest file → None summary
        check("missing manifest returns None",
              av.read_manifest_summary(vault), None)

        # Pre-v3 manifest with non-empty files → promotion_candidate_count = None
        _write_manifest(vault, {
            "schema_version": 2,
            "files": [{"path": "a.md", "promotion_candidate": True}],
        })
        r = av.read_manifest_summary(vault)
        check("v2 manifest → promotion_candidate_count is None",
              r["promotion_candidate_count"], None)

        # v3 manifest with empty files → promotion_candidate_count = 0 (not None)
        _write_manifest(vault, {"schema_version": 3, "files": []})
        r = av.read_manifest_summary(vault)
        check("v3 empty manifest → promotion_candidate_count = 0",
              r["promotion_candidate_count"], 0)

        # v3 manifest with mixed candidates → exact integer count
        _write_manifest(vault, {
            "schema_version": 3,
            "files": [
                {"path": "a.md", "promotion_candidate": True},
                {"path": "b.md", "promotion_candidate": False},
                {"path": "c.md", "promotion_candidate": True},
                {"path": "d.md", "promotion_candidate": None},
            ],
        })
        r = av.read_manifest_summary(vault)
        check("v3 with 2 true + 1 false + 1 null → 2",
              r["promotion_candidate_count"], 2)

        # v4+ manifest (future schema) is still gated as v3+
        _write_manifest(vault, {
            "schema_version": 99,
            "files": [{"path": "a.md", "promotion_candidate": True}],
        })
        r = av.read_manifest_summary(vault)
        check("future schema (v99) → promotion_candidate_count = 1",
              r["promotion_candidate_count"], 1)

        # Missing schema_version → defaults to v1 → None
        _write_manifest(vault, {
            "files": [{"path": "a.md", "promotion_candidate": True}],
        })
        r = av.read_manifest_summary(vault)
        check("missing schema_version (defaults to v1) → None",
              r["promotion_candidate_count"], None)

        # Corrupt JSON → None summary
        (vault / ".vault-bridge" / "manifest.json").write_text(
            "not-json", encoding="utf-8"
        )
        check("corrupt JSON returns None",
              av.read_manifest_summary(vault), None)

    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
