#!/usr/bin/env python3
"""
test-manifest-meta.py — Unit tests for generate-manifest.py global meta fields
(references_in/out, access_count, type opt-in, schema upgrade).

Uses an in-memory fixture vault (no real ~/vault reads).

Usage: python3 vault-bridge/scripts/test/test-manifest-meta.py
Expected exit code: 0 (all cases pass)
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add the scripts dir to path so we can import generate-manifest functions
SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

# generate-manifest.py has a hyphen, so import via importlib
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "generate_manifest",
    SCRIPT_DIR / "generate-manifest.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

generate = _mod.generate

PASS = 0
FAIL = 0


def ok(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1


def make_note(vault: Path, rel: str, content: str) -> Path:
    p = vault / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


FRONTMATTER_NOTE = """\
---
created: 2026-01-01
tags: [note]
type: note
status: evergreen
---

# {title}

{body}
"""

print("=== test-manifest-meta.py ===")
print()

# ── Case 1: no type field → type=unknown → excluded from manifest ─────────
print("Case 1: no type field → file excluded from manifest (type opt-in)")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    make_note(vault, "notes/no-type.md", """\
---
created: 2026-01-01
tags: [note]
---

# No type field

This file has no type: in frontmatter — invisible to claude-kit.
""")
    # Also a typed note so manifest isn't empty
    make_note(vault, "notes/typed-note.md", FRONTMATTER_NOTE.format(
        title="Typed", body="Has type field."
    ))

    out = vault / ".vault-bridge" / "manifest.json"
    manifest, _ = generate(vault, out, force=True)

    untyped = next((f for f in manifest["files"] if "no-type" in f["path"]), None)
    ok("untyped file not in manifest (type opt-in §2.2)", untyped is None)

    typed = next((f for f in manifest["files"] if "typed-note" in f["path"]), None)
    ok("typed-note IS in manifest", typed is not None)
    if typed:
        ok("typed-note has no stale promotion_candidate field (#480)",
           "promotion_candidate" not in typed)

print()

# ── Case 2: non-git vault → access_count = 0 (not null) ─────────────────
print("Case 2: non-git vault → access_count = 0 (not null)")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    make_note(vault, "notes/regular-note.md", FRONTMATTER_NOTE.format(
        title="Regular Note", body="Content here."
    ))

    out = vault / ".vault-bridge" / "manifest.json"
    # No .git dir → _is_git_repo returns False → access_count = 0
    manifest, _ = generate(vault, out, force=True)

    note = next((f for f in manifest["files"] if "regular-note" in f["path"]), None)
    ok("note found in manifest", note is not None)
    if note:
        ok("access_count = 0 for non-git vault (not null)",
           note["access_count"] == 0,
           f"got {note['access_count']}")
        ok("access_count is int (not None)",
           isinstance(note["access_count"], int),
           f"type: {type(note['access_count'])}")

print()

# ── Case 3: in-place upgrade — pre-v3 manifest (no global meta fields) ───
print("Case 3: in-place upgrade — old v2 manifest gets new fields patched, "
      "stale promotion_candidate dropped")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    make_note(vault, "notes/existing-note.md", FRONTMATTER_NOTE.format(
        title="Existing Note", body="Already in manifest."
    ))

    out = vault / ".vault-bridge" / "manifest.json"
    # Simulate a pre-#480 v3 manifest carrying a stale promotion_candidate field.
    old_manifest = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "vault_root": str(vault),
        "schema_version": 3,
        "file_count": 1,
        "files": [
            {
                "path": "notes/existing-note.md",
                "type": "note",
                "tags": ["note"],
                "title": "Existing Note",
                "summary": "Already in manifest.",
                "mtime": 0,  # entry mtime is informational; incremental check uses filesystem stat (see os.utime below)
                "size_bytes": 100,
                "references_in": 0,
                "references_out": 0,
                "access_count": 0,
                "promotion_candidate": True,
            }
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(old_manifest), encoding="utf-8")

    # Touch the manifest to appear newer than the file
    import time
    time.sleep(0.05)
    os.utime(out, None)  # set manifest mtime to now

    # Run incremental update (not force) — should upgrade in-place
    manifest, stats = generate(vault, out, force=False)

    note = next((f for f in manifest["files"] if "existing-note" in f["path"]), None)
    ok("existing note still in manifest after upgrade", note is not None)
    if note:
        ok("references_in field patched in", "references_in" in note,
           f"fields: {list(note.keys())}")
        ok("access_count field patched in", "access_count" in note,
           f"fields: {list(note.keys())}")
        ok("stale promotion_candidate field dropped (#480)",
           "promotion_candidate" not in note,
           f"fields: {list(note.keys())}")

print()

# ── Case 4: wikilink dedup — self-link excluded, repeats count once ─────
print("Case 4: wikilink dedup (self-link excluded, repeated mentions count once)")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    # Target gets three mentions from a single linker plus one self-link.
    make_note(vault, "notes/target.md", FRONTMATTER_NOTE.format(
        title="Target",
        body="Self-link should not count: [[target]].",
    ))
    make_note(vault, "notes/spammy-linker.md", FRONTMATTER_NOTE.format(
        title="Spammy Linker",
        body="See [[target]] and again [[target]] and [[target]] once more.",
    ))

    out = vault / ".vault-bridge" / "manifest.json"
    manifest, _ = generate(vault, out, force=True)

    target = next((f for f in manifest["files"] if f["path"] == "notes/target.md"), None)
    ok("target found in manifest", target is not None)
    if target:
        ok("references_in = 1 (3 mentions in 1 file collapse, self-link excluded)",
           target["references_in"] == 1,
           f"got {target['references_in']}")

    linker = next((f for f in manifest["files"] if "spammy-linker" in f["path"]), None)
    if linker:
        ok("references_out counts every occurrence (3)",
           linker["references_out"] == 3,
           f"got {linker['references_out']}")

print()

# ── Summary ───────────────────────────────────────────────────────────────
print(f"=== Results: {PASS} passed, {FAIL} failed ===")
if FAIL == 0:
    print("OK: all cases passed")
    sys.exit(0)
else:
    sys.exit(1)
