#!/usr/bin/env python3
"""manifest-wiki-match.py regression (#468, mirrors #460's retired e8-candidates.py pattern).
Moved here from obsidian-vault-manager in #645 alongside manifest-wiki-match.py and
wiki/SKILL.md — the audit-side half of the original combined test (manifest-summary.py +
audit/SKILL.md) stayed in obsidian-vault-manager under the same filename, since those two
files did not move.

wiki/SKILL.md used to `cat` the raw .vault-bridge/manifest.json (100+ KB on a real vault),
silently truncated to a 2 KB harness preview before the model ever saw it. Runs the filter
script against real temp fixtures (missing/unparseable/malformed/valid), asserts its output
stays under the 2 KB cut and serializes `scanned` before `wiki_entries`, then statically
greps the live wiki/SKILL.md call site to pin that it never regresses back to a raw `cat`.

Run: python3 vault-bridge/scripts/test/test-manifest-reads.py
  -> "OK: all N manifest-read checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (in-memory fixtures, no vault, no live files):
  python3 vault-bridge/scripts/test/test-manifest-reads.py --self-test
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_WIKI_SCRIPT = _HERE.parent / "manifest-wiki-match.py"
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


def static_checks(wiki_text: str) -> list:
    """Static pins for the wiki-side manifest-read contract, as (ok, description) pairs.

    Split out of main() so --self-test can run the identical checks against an in-memory
    fixture.
    """
    return [
        ("scripts/manifest-wiki-match.py" in wiki_text,
         "wiki/SKILL.md invokes manifest-wiki-match.py"),
        ("cat ~/vault/.vault-bridge/manifest.json" not in wiki_text,
         "wiki/SKILL.md no longer `cat`s the manifest directly"),
        ("2 KB" in wiki_text, "wiki/SKILL.md documents the 2 KB truncation rationale"),
        ("Exit 3" in wiki_text or "exit 3" in wiki_text,
         "wiki/SKILL.md documents the exit-3 (absent/unparseable/malformed) branch"),
    ]


# ---------------------------------------------------------------------------
# Self-test fixtures (in-memory)
# ---------------------------------------------------------------------------

_FIX_WIKI = """\
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-wiki-match.py" ...
2 KB preview cut rationale. Exit 3 -> absent/unparseable/malformed.
"""

_WIKI_NO_RATIONALE = _FIX_WIKI.replace("2 KB preview", "preview")
_WIKI_NO_EXIT3 = _FIX_WIKI.replace("Exit 3 ->", "Otherwise ->")
_WIKI_RAW_CAT = _FIX_WIKI.replace(
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-wiki-match.py" ...',
    "cat ~/vault/.vault-bridge/manifest.json")

for _name, _fixture, _base in (
    ("_WIKI_NO_RATIONALE", _WIKI_NO_RATIONALE, _FIX_WIKI),
    ("_WIKI_NO_EXIT3", _WIKI_NO_EXIT3, _FIX_WIKI),
    ("_WIKI_RAW_CAT", _WIKI_RAW_CAT, _FIX_WIKI),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"


def _self_test() -> int:
    cases = []

    for ok, desc in static_checks(_FIX_WIKI):
        cases.append((f"passing: {desc}", ok))

    def _expect_fail(label, wiki):
        failed = [d for ok, d in static_checks(wiki) if not ok]
        cases.append((f"{label} (expect FAIL): {failed}", bool(failed)))

    _expect_fail("wiki body loses its 2 KB rationale", _WIKI_NO_RATIONALE)
    _expect_fail("wiki body loses the exit-3 branch", _WIKI_NO_EXIT3)
    _expect_fail("wiki body regresses to a raw cat", _WIKI_RAW_CAT)

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def _note(path: str, type_: str = "note", **extra) -> dict:
    e = {"path": path, "type": type_, "title": path, "tags": ["x"],
         "summary": "s" * 200, "mtime": 0, "size_bytes": 1,
         "references_in": 0, "references_out": 0, "access_count": 0}
    e.update(extra)
    return e


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        missing = tmp / "missing.json"
        r = run(_WIKI_SCRIPT, missing)
        check(r.returncode == 3 and r.stdout == "", "wiki-match: missing manifest -> rc=3, no stdout")

        bad_json = tmp / "bad.json"
        bad_json.write_text("{not json", encoding="utf-8")
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

        # #528: real vault is 182 files / 41 type:wiki as of 2026-08-03 (grew past the 168/3
        # synthetic fixture above) — pin that scale too, so a truncation regression (#523's
        # defect class, different consumer) can't hide behind "only tested at toy size".
        real_scale = [_note("notes/a.md", type_="note")] + \
            [_note(f"wiki/w{i}.md", type_="wiki", title=f"Topic {i}", tags=["t"]) for i in range(41)] + \
            [_note(f"notes/n{i}.md") for i in range(140)]
        real_scale_json = tmp / "real-scale.json"
        real_scale_json.write_text(json.dumps({
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": len(real_scale),
            "schema_version": 3, "files": real_scale,
        }), encoding="utf-8")
        raw_size = len(json.dumps({"files": real_scale}))
        r = run(_WIKI_SCRIPT, real_scale_json)
        out = json.loads(r.stdout) if r.returncode == 0 else {}
        check(out.get("wiki_entries") is not None, "wiki-match: real-scale fixture parses (rc=0)")
        check(len(out.get("wiki_entries") or []) == 41,
              "wiki-match: real-scale (182 files/41 wiki) fixture returns all 41, none dropped (#523 defect class)")
        check(len(r.stdout) < raw_size / 5,
              "wiki-match: real-scale filtered output stays a fraction of the raw manifest size")

        no_wiki = tmp / "no-wiki.json"
        no_wiki.write_text(json.dumps({
            "generated_at": "2026-08-03T00:00:00+00:00", "file_count": 1,
            "schema_version": 3, "files": [_note("notes/a.md")],
        }), encoding="utf-8")
        r = run(_WIKI_SCRIPT, no_wiki)
        check(r.returncode == 0 and json.loads(r.stdout).get("wiki_entries") == [],
              "wiki-match: no wiki/ pages -> rc=0 with an empty list (not a failure)")

    # ---- static call-site guard: wiki/SKILL.md may not regress to a raw `cat` ----

    for ok, desc in static_checks(_WIKI_SKILL.read_text(encoding="utf-8")):
        check(ok, desc)

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print(f"\nOK: all manifest-read checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
