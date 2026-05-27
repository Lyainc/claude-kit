#!/usr/bin/env python3
"""
Regression test — generate-manifest.py type opt-in filter (v4 §2.2).

Verifies that files without `type:` frontmatter are excluded from the manifest.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate-manifest.py"


def _make_note(path: Path, frontmatter: str, body: str = "Body text.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")


def case_type_optin_filter(errors: list[str]) -> None:
    """Typed file is included, untyped file is excluded (v4 §2.2)."""
    print("\ncase: type_optin_filter")
    with tempfile.TemporaryDirectory() as vault:
        vault_path = Path(vault)
        _make_note(vault_path / "notes" / "typed.md", "type: note\ntags: [demo]")
        _make_note(vault_path / "notes" / "untyped.md", "tags: [demo]\ncreated: 2026-05-26")
        out = vault_path / ".vault-bridge" / "manifest.json"
        proc = subprocess.run(
            ["python3", str(SCRIPT), "--vault-root", str(vault), "--out", str(out), "--force"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(f"  FAIL generator returned {proc.returncode}: {proc.stderr}", file=sys.stderr)
            errors.append("generator nonzero exit")
            return
        manifest = json.loads(out.read_text(encoding="utf-8"))
        paths = {entry["path"] for entry in manifest.get("files", [])}

        if "notes/typed.md" in paths:
            print("  ok   typed note included")
        else:
            print(f"  FAIL typed note missing (paths={paths})", file=sys.stderr)
            errors.append("typed note missing")

        if "notes/untyped.md" not in paths:
            print("  ok   untyped note excluded (type opt-in)")
        else:
            print("  FAIL untyped note present in manifest (filter did not fire)", file=sys.stderr)
            errors.append("untyped note not filtered")


def case_schema_version_bump_invalidates_v1(errors: list[str]) -> None:
    """A pre-seeded v1 manifest is upgraded in-place to the current schema version.

    v3 behaviour: _load_existing_manifest accepts any schema_version (in-place
    upgrade). Orphan entries (files not on disk) are still dropped because the
    incremental update loop only includes paths present in md_files.
    """
    print("\ncase: schema_version_bump_invalidates_v1")
    with tempfile.TemporaryDirectory() as vault:
        vault_path = Path(vault)
        out = vault_path / ".vault-bridge" / "manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)

        # Seed a v1-style manifest containing a fabricated entry for an orphan file
        # that does not exist on disk. The orphan must be dropped during the
        # incremental update because it's absent from md_files.
        out.write_text(json.dumps({
            "generated_at": "2025-01-01T00:00:00+00:00",
            "vault_root": str(vault),
            "schema_version": 1,
            "file_count": 1,
            "files": [
                {"path": "legacy/orphan.md", "type": "unknown", "title": "orphan",
                 "summary": "", "tags": [], "mtime": 0, "size_bytes": 0}
            ],
        }), encoding="utf-8")

        _make_note(vault_path / "notes" / "real.md", "type: note\ntags: []")

        # No --force: in-place upgrade path (v1 manifest loaded, incremental update).
        proc = subprocess.run(
            ["python3", str(SCRIPT), "--vault-root", str(vault), "--out", str(out)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            print(f"  FAIL generator returned {proc.returncode}: {proc.stderr}", file=sys.stderr)
            errors.append("generator nonzero exit on v1 upgrade")
            return

        manifest = json.loads(out.read_text(encoding="utf-8"))
        current_schema = 3  # SCHEMA_VERSION as of PR 4c
        if manifest.get("schema_version") == current_schema:
            print(f"  ok   manifest upgraded to schema_version={current_schema}")
        else:
            print(f"  FAIL unexpected schema_version (got {manifest.get('schema_version')}, want {current_schema})", file=sys.stderr)
            errors.append("schema_version mismatch after v1 upgrade")

        paths = {entry["path"] for entry in manifest.get("files", [])}
        if "legacy/orphan.md" not in paths:
            print("  ok   v1 orphan entry dropped during full rescan")
        else:
            print(f"  FAIL v1 orphan entry survived v2 rescan", file=sys.stderr)
            errors.append("v1 orphan entry survived")


def main() -> int:
    errors: list[str] = []
    case_type_optin_filter(errors)
    case_schema_version_bump_invalidates_v1(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
