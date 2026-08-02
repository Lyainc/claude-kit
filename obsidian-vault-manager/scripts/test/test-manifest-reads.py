#!/usr/bin/env python3
"""manifest-summary.py + manifest-wiki-match.py regression (#468, mirrors #460's
feedback-loop/scripts/test/test-e8-candidates.py).

Both scripts exist so audit/SKILL.md and wiki/SKILL.md never `cat` .vault-bridge/manifest.json
directly — the harness truncates large Bash output to a 2 KB preview before the model sees it,
so a raw `cat` of a real (100+ KB) manifest silently degrades to whichever ~3 entries survive
the cut, indistinguishable from a legitimately small/clean manifest.

Runs each script via subprocess against real temp fixture files (not a mocked import), then
statically greps the live SKILL.md call sites to pin that neither ever regresses back to a raw
`cat` of the manifest.

Run: python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py
  -> "OK: all N manifest-read checks passed" (exit 0) / "FAILED: ..." (exit 1).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SUMMARY_SCRIPT = _HERE.parent / "manifest-summary.py"
_WIKI_SCRIPT = _HERE.parent / "manifest-wiki-match.py"
_AUDIT_SKILL = _HERE.parent.parent / "skills" / "audit" / "SKILL.md"
_WIKI_SKILL = _HERE.parent.parent / "skills" / "wiki" / "SKILL.md"

errors = []


def check(cond: bool, desc: str) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def run(script: Path, manifest_path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), str(manifest_path)],
        capture_output=True, text=True,
    )


def _note(path: str, type_: str = "note", **extra) -> dict:
    e = {"path": path, "type": type_, "title": path, "tags": ["x"],
         "summary": "s" * 200, "mtime": 0, "size_bytes": 1,
         "references_in": 0, "references_out": 0, "access_count": 0}
    e.update(extra)
    return e


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # ---- manifest-summary.py ----

        missing = tmp / "missing.json"
        r = run(_SUMMARY_SCRIPT, missing)
        check(r.returncode == 3 and r.stdout == "", "summary: missing manifest -> rc=3, no stdout")

        bad_json = tmp / "bad.json"
        bad_json.write_text("{not json", encoding="utf-8")
        r = run(_SUMMARY_SCRIPT, bad_json)
        check(r.returncode == 3, "summary: unparseable JSON -> rc=3")

        no_field = tmp / "no-field.json"
        no_field.write_text(json.dumps({"files": []}), encoding="utf-8")
        r = run(_SUMMARY_SCRIPT, no_field)
        check(r.returncode == 3, "summary: missing file_count/generated_at -> rc=3")

        big_files = [_note(f"notes/n{i}.md") for i in range(168)]
        valid = tmp / "valid.json"
        valid.write_text(json.dumps({
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": 168,
            "schema_version": 3, "files": big_files,
        }), encoding="utf-8")
        r = run(_SUMMARY_SCRIPT, valid)
        check(r.returncode == 0, "summary: valid manifest -> rc=0")
        out = json.loads(r.stdout) if r.returncode == 0 else {}
        check(out.get("file_count") == 168 and out.get("generated_at") == "2026-08-03T00:00:00+00:00",
              "summary: extracts file_count + generated_at only")
        check("files" not in r.stdout and len(r.stdout) < 200,
              "summary: never re-emits the files[] payload (stays tiny regardless of manifest size)")

        # ---- manifest-wiki-match.py ----

        r = run(_WIKI_SCRIPT, missing)
        check(r.returncode == 3 and r.stdout == "", "wiki-match: missing manifest -> rc=3, no stdout")

        r = run(_WIKI_SCRIPT, bad_json)
        check(r.returncode == 3, "wiki-match: unparseable JSON -> rc=3")

        wrong_shape = tmp / "wrong-shape.json"
        wrong_shape.write_text(json.dumps({"files": "nope"}), encoding="utf-8")
        r = run(_WIKI_SCRIPT, wrong_shape)
        check(r.returncode == 3, "wiki-match: files not a list -> rc=3")

        bad_entry = tmp / "bad-entry.json"
        bad_entry.write_text(json.dumps({"files": ["notes/a.md", 42]}), encoding="utf-8")
        r = run(_WIKI_SCRIPT, bad_entry)
        check(r.returncode == 3, "wiki-match: non-dict entry in files[] -> rc=3")

        mixed = [_note("notes/a.md", type_="note")] + \
                [_note(f"wiki/w{i}.md", type_="wiki", title=f"Topic {i}", tags=["t"]) for i in range(3)] + \
                [_note(f"notes/n{i}.md") for i in range(164)]
        big_wiki = tmp / "big-wiki.json"
        big_wiki.write_text(json.dumps({
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": len(mixed),
            "schema_version": 3, "files": mixed,
        }), encoding="utf-8")
        r = run(_WIKI_SCRIPT, big_wiki)
        check(r.returncode == 0, "wiki-match: valid manifest -> rc=0")
        out = json.loads(r.stdout) if r.returncode == 0 else {}
        check(out.get("scanned") == len(mixed), "wiki-match: scanned == total files, not just wiki/ count")
        entries = out.get("wiki_entries") or []
        check(len(entries) == 3 and all(e["path"].startswith("wiki/") for e in entries),
              "wiki-match: only type:wiki entries are returned")
        check(set(entries[0].keys()) == {"path", "title", "tags"},
              "wiki-match: each entry carries only path/title/tags (never summary/mtime/etc.)")
        check(r.stdout.index('"scanned"') < r.stdout.index('"wiki_entries"'),
              "wiki-match: scanned is serialized before wiki_entries (survives truncation first)")
        check(len(r.stdout) < 2000,
              "wiki-match: filtered output for a 168-file manifest stays under the 2 KB preview cut")

        no_wiki = tmp / "no-wiki.json"
        no_wiki.write_text(json.dumps({
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": 1,
            "schema_version": 3, "files": [_note("notes/a.md")],
        }), encoding="utf-8")
        r = run(_WIKI_SCRIPT, no_wiki)
        check(r.returncode == 0 and json.loads(r.stdout).get("wiki_entries") == [],
              "wiki-match: no wiki/ pages -> rc=0 with an empty list (not a failure)")

    # ---- static call-site guards: neither SKILL.md may regress to a raw `cat` ----

    audit_text = _AUDIT_SKILL.read_text(encoding="utf-8")
    check("scripts/manifest-summary.py" in audit_text,
          "audit/SKILL.md invokes manifest-summary.py")
    check('cat "$VAULT_ROOT/.vault-bridge/manifest.json"' not in audit_text,
          "audit/SKILL.md no longer `cat`s the manifest directly")
    check("2 KB" in audit_text, "audit/SKILL.md documents the 2 KB truncation rationale")
    check("Exit 3" in audit_text or "exit 3" in audit_text,
          "audit/SKILL.md documents the exit-3 (absent/unparseable) branch")

    wiki_text = _WIKI_SKILL.read_text(encoding="utf-8")
    check("scripts/manifest-wiki-match.py" in wiki_text,
          "wiki/SKILL.md invokes manifest-wiki-match.py")
    check("cat ~/vault/.vault-bridge/manifest.json" not in wiki_text,
          "wiki/SKILL.md no longer `cat`s the manifest directly")
    check("2 KB" in wiki_text, "wiki/SKILL.md documents the 2 KB truncation rationale")
    check("Exit 3" in wiki_text or "exit 3" in wiki_text,
          "wiki/SKILL.md documents the exit-3 (absent/unparseable/malformed) branch")

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print(f"\nOK: all manifest-read checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
