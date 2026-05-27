#!/usr/bin/env python3
"""
Regression tests for E8_promotion_candidate finding generation.

Tests that audit-validate.py's classify() correctly surfaces manifest
entries with promotion_candidate=True as E8 findings, and gracefully
handles pre-v3 manifests and below-threshold entries.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Resolve audit-validate module from this script's location
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "audit_validate", _HERE / "audit-validate.py"
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

collect = _mod.collect
classify = _mod.classify


def _make_vault(tmp: Path) -> None:
    """Create a minimal valid vault under tmp."""
    (tmp / "inbox").mkdir()
    (tmp / "notes").mkdir()
    (tmp / "assets").mkdir()


def _write_manifest(vault: Path, files: list, schema_version: int = 3) -> None:
    manifest_dir = vault / ".vault-bridge"
    manifest_dir.mkdir(exist_ok=True)
    manifest = {
        "schema_version": schema_version,
        "file_count": len(files),
        "generated_at": "2026-05-28T00:00:00+00:00",
        "files": files,
    }
    (manifest_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )


def _note(vault: Path, name: str, status: str = "raw") -> None:
    (vault / "notes" / f"{name}.md").write_text(
        f"---\ncreated: 2026-04-01\ntags: [note]\ntype: note\nstatus: {status}\n---\n\n# {name}\n"
    )


# ── Test 1: promotion_candidate=True → E8 finding generated ──────────────────

def test_promotion_candidate_generates_finding() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        _note(vault, "my-evergreen")
        _write_manifest(vault, [
            {
                "path": "notes/my-evergreen.md",
                "type": "note",
                "references_in": 3,
                "access_count": 0,
                "promotion_candidate": True,
            }
        ])
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 1, f"expected 1 E8 finding, got {len(e8)}"
        assert "my-evergreen" in e8[0]["path"], "path should contain note stem"
        assert "refs_in=3" in e8[0]["detail"]
        assert "status→evergreen" in e8[0]["detail"]
        assert e8[0]["priority"] == "P2"
    print("PASS test_promotion_candidate_generates_finding")


# ── Test 2: promotion_candidate=False → no E8 finding ────────────────────────

def test_below_threshold_no_finding() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        _note(vault, "low-ref")
        _write_manifest(vault, [
            {
                "path": "notes/low-ref.md",
                "type": "note",
                "references_in": 1,
                "access_count": 0,
                "promotion_candidate": False,
            }
        ])
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 0, f"expected 0 E8 findings, got {len(e8)}"
    print("PASS test_below_threshold_no_finding")


# ── Test 3: pre-v3 manifest → E8 section skipped (graceful) ──────────────────

def test_pre_v3_manifest_skipped() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        _note(vault, "old-note")
        _write_manifest(vault, [
            {
                "path": "notes/old-note.md",
                "type": "note",
                "promotion_candidate": True,  # present but schema_version=2
            }
        ], schema_version=2)
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 0, f"pre-v3 manifest should yield 0 E8 findings, got {len(e8)}"
    print("PASS test_pre_v3_manifest_skipped")


# ── Test 4: no manifest → no E8 findings, no crash ───────────────────────────

def test_no_manifest_no_crash() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        _note(vault, "standalone")
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 0, f"no manifest should yield 0 E8 findings, got {len(e8)}"
    print("PASS test_no_manifest_no_crash")


# ── Test 5: capture/session type → None in manifest → not surfaced as E8 ─────

def test_non_note_type_not_surfaced() -> None:
    """Manifest carries promotion_candidate=None for capture/session — not True."""
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        (vault / "inbox" / "capture-2026-04-01-topic.md").write_text(
            "---\ncreated: 2026-04-01\ntags: [capture]\ntype: capture\n---\n\n# Capture\n"
        )
        _write_manifest(vault, [
            {
                "path": "inbox/capture-2026-04-01-topic.md",
                "type": "capture",
                "references_in": 10,
                "access_count": 20,
                "promotion_candidate": None,
            }
        ])
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 0, f"capture with promotion_candidate=None should yield 0 E8, got {len(e8)}"
    print("PASS test_non_note_type_not_surfaced")


# ── Test 6: access_count trigger path ────────────────────────────────────────

def test_access_count_trigger() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        _note(vault, "frequent-access")
        _write_manifest(vault, [
            {
                "path": "notes/frequent-access.md",
                "type": "note",
                "references_in": 0,
                "access_count": 5,
                "promotion_candidate": True,
            }
        ])
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 1, f"expected 1 E8 finding via access_count, got {len(e8)}"
        assert "access=5" in e8[0]["detail"]
    print("PASS test_access_count_trigger")


# ── Test 7: multiple True entries → one E8 finding per entry ─────────────────

def test_multiple_candidates_each_become_finding() -> None:
    with tempfile.TemporaryDirectory() as tmp_str:
        vault = Path(tmp_str)
        _make_vault(vault)
        _note(vault, "candidate-a")
        _note(vault, "candidate-b")
        _note(vault, "candidate-c")
        _write_manifest(vault, [
            {"path": "notes/candidate-a.md", "type": "note",
             "references_in": 3, "access_count": 0, "promotion_candidate": True},
            {"path": "notes/candidate-b.md", "type": "note",
             "references_in": 0, "access_count": 5, "promotion_candidate": True},
            {"path": "notes/candidate-c.md", "type": "decision",
             "references_in": 4, "access_count": 8, "promotion_candidate": True},
        ])
        bundle = collect(vault)
        result = classify(bundle)
        e8 = [f for f in result["findings"] if f["type"] == "E8_promotion_candidate"]
        assert len(e8) == 3, f"expected 3 E8 findings, got {len(e8)}"
        paths = {f["path"] for f in e8}
        assert paths == {"notes/candidate-a.md", "notes/candidate-b.md", "notes/candidate-c.md"}
    print("PASS test_multiple_candidates_each_become_finding")


if __name__ == "__main__":
    test_promotion_candidate_generates_finding()
    test_below_threshold_no_finding()
    test_pre_v3_manifest_skipped()
    test_no_manifest_no_crash()
    test_non_note_type_not_surfaced()
    test_access_count_trigger()
    test_multiple_candidates_each_become_finding()
    print("\nOK: all 7 cases passed")
