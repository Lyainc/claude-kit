#!/usr/bin/env python3
"""
test-manifest-promotion.py — Unit tests for generate-manifest.py PR 4c fields.

Tests references_in, references_out, access_count, and promotion_candidate
using an in-memory fixture vault (no real ~/vault reads).

Usage: python3 vault-bridge/scripts/test/test-manifest-promotion.py
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
_build_wikilink_index = _mod._build_wikilink_index
_compute_promotion_candidate = _mod._compute_promotion_candidate
PROMOTION_REFS_THRESHOLD = _mod.PROMOTION_REFS_THRESHOLD
PROMOTION_ACCESS_THRESHOLD = _mod.PROMOTION_ACCESS_THRESHOLD

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

print("=== test-manifest-promotion.py ===")
print()

# ── Case 1: references_in >= 3 → promotion_candidate = True ──────────────
print("Case 1: references_in >= 3 → promotion_candidate = True")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    # Target note
    make_note(vault, "notes/target-note.md", FRONTMATTER_NOTE.format(
        title="Target Note", body="This note gets linked."
    ))
    # 3 notes link to target-note
    for i in range(1, 4):
        make_note(vault, f"notes/linker-{i}.md", FRONTMATTER_NOTE.format(
            title=f"Linker {i}",
            body=f"See [[target-note]] for details.",
        ))

    out = vault / ".vault-bridge" / "manifest.json"
    # Set non-git so access_count = 0
    manifest, stats = generate(vault, out, force=True)

    target = next((f for f in manifest["files"] if "target-note" in f["path"]), None)
    ok("target-note found in manifest", target is not None)
    if target:
        ok("references_in >= 3", target["references_in"] >= 3,
           f"got {target['references_in']}")
        ok("promotion_candidate = True", target["promotion_candidate"] is True,
           f"got {target['promotion_candidate']}")
        ok("references_out = 0", target["references_out"] == 0,
           f"got {target['references_out']}")

print()

# ── Case 2: references_in = 2 → promotion_candidate = False ─────────────
print("Case 2: references_in = 2 → promotion_candidate = False")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    make_note(vault, "notes/target-note.md", FRONTMATTER_NOTE.format(
        title="Target Note", body="This note gets linked."
    ))
    for i in range(1, 3):  # only 2 linkers
        make_note(vault, f"notes/linker-{i}.md", FRONTMATTER_NOTE.format(
            title=f"Linker {i}",
            body=f"See [[target-note]] for details.",
        ))

    out = vault / ".vault-bridge" / "manifest.json"
    manifest, _ = generate(vault, out, force=True)

    target = next((f for f in manifest["files"] if "target-note" in f["path"]), None)
    ok("target-note found in manifest", target is not None)
    if target:
        ok("references_in = 2", target["references_in"] == 2,
           f"got {target['references_in']}")
        ok("promotion_candidate = False (refs < threshold)",
           target["promotion_candidate"] is False,
           f"got {target['promotion_candidate']}")

print()

# ── Case 3: access_count >= 5 → promotion_candidate = True ──────────────
print("Case 3: access_count >= 5 (mocked) → promotion_candidate = True")

# Test _compute_promotion_candidate directly since access_count needs git
ok("access_count 5 + type:note → True",
   _compute_promotion_candidate("note", 0, 5) is True)
ok("access_count 4 + type:note → False",
   _compute_promotion_candidate("note", 0, 4) is False)
ok("access_count 5 + refs 0 → True",
   _compute_promotion_candidate("note", 0, 5) is True)
ok("refs 3 + access 0 → True",
   _compute_promotion_candidate("note", 3, 0) is True)
ok("refs 2 + access 4 → False",
   _compute_promotion_candidate("note", 2, 4) is False)

print()

# ── Case 4: inbox/ file → promotion_candidate = None ────────────────────
print("Case 4: inbox/ file (type:capture) → promotion_candidate = None")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    make_note(vault, "inbox/capture-2026-01-01-topic.md", """\
---
created: 2026-01-01
tags: [capture]
type: capture
---

# Capture note

[[some-note]] [[other-note]] [[third-note]]
""")
    # Ensure there's at least one note-type file for the manifest to process
    make_note(vault, "notes/some-note.md", FRONTMATTER_NOTE.format(
        title="Some Note", body="Content."
    ))

    out = vault / ".vault-bridge" / "manifest.json"
    manifest, _ = generate(vault, out, force=True)

    capture = next((f for f in manifest["files"] if "capture" in f["path"]), None)
    ok("capture found in manifest", capture is not None)
    if capture:
        ok("capture promotion_candidate is None (not eligible)",
           capture["promotion_candidate"] is None,
           f"got {capture['promotion_candidate']}")
        ok("capture references_out = 3",
           capture["references_out"] == 3,
           f"got {capture['references_out']}")

print()

# ── Case 5: no type field → type=unknown → excluded from manifest ─────────
print("Case 5: no type field → file excluded from manifest (type opt-in)")

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
        ok("typed-note has promotion_candidate field",
           "promotion_candidate" in typed)

print()

# ── Case 6: non-git vault → access_count = 0 (not null) ─────────────────
print("Case 6: non-git vault → access_count = 0 (not null)")

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

# ── Case 7: decision type is promotion-eligible ──────────────────────────
print("Case 7: type:decision eligible for promotion (like type:note)")

ok("decision + refs 3 → True",
   _compute_promotion_candidate("decision", 3, 0) is True)
ok("decision + access 5 → True",
   _compute_promotion_candidate("decision", 0, 5) is True)
ok("session type → None (not eligible)",
   _compute_promotion_candidate("session", 10, 10) is None)
ok("plan type → None (not eligible)",
   _compute_promotion_candidate("plan", 10, 10) is None)

print()

# ── Case 8: in-place upgrade — old manifest (no PR-4c fields) ────────────
print("Case 8: in-place upgrade — old v2 manifest gets new fields patched")

with tempfile.TemporaryDirectory() as tmp:
    vault = Path(tmp)
    make_note(vault, "notes/existing-note.md", FRONTMATTER_NOTE.format(
        title="Existing Note", body="Already in manifest."
    ))

    out = vault / ".vault-bridge" / "manifest.json"
    # Simulate an old v2 manifest (no PR-4c fields)
    old_manifest = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "vault_root": str(vault),
        "schema_version": 2,
        "file_count": 1,
        "files": [
            {
                "path": "notes/existing-note.md",
                "type": "note",
                "tags": ["note"],
                "title": "Existing Note",
                "summary": "Already in manifest.",
                "mtime": 0,  # force old mtime so file appears unchanged
                "size_bytes": 100,
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
        ok("promotion_candidate field patched in", "promotion_candidate" in note,
           f"fields: {list(note.keys())}")
    ok("schema_version updated to 3",
       manifest.get("schema_version") == 3,
       f"got {manifest.get('schema_version')}")

print()

# ── Summary ───────────────────────────────────────────────────────────────
print(f"=== Results: {PASS} passed, {FAIL} failed ===")
if FAIL == 0:
    print("OK: all cases passed")
    sys.exit(0)
else:
    sys.exit(1)
