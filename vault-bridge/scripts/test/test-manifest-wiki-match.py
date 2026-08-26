#!/usr/bin/env python3
"""manifest-wiki-match.py regression (#645 split from OVM's test-manifest-reads.py, #468).

`manifest-wiki-match.py` exists so `wiki/SKILL.md` Phase 3 DEDUP never `cat`s
`.vault-bridge/manifest.json` directly — the harness truncates large Bash output to a 2 KB
preview before the model sees it, so a raw `cat` of a real (100+ KB) manifest silently degrades
to whichever ~3 entries survive the cut, indistinguishable from a legitimately small manifest.

**Why this file is not in obsidian-vault-manager.** It was the wiki half of
`obsidian-vault-manager/scripts/test/test-manifest-reads.py` until `/wiki`'s deployment unit moved
OVM -> vault-bridge (#645); a test follows the script it exercises. The two halves shared only
three helpers (`check`, `run`, `_note`) and the string "2 KB" — a stapled file, not a coupled one,
so the split costs ~60 lines of helper duplication and buys each plugin a self-contained suite.
The name changed from its OVM sibling's on purpose: `check-trigger-regression.py` may exist under
both plugins because those are per-plugin instances of ONE contract, whereas these two files pin
two different contracts and must stay distinguishable in a grep or a CI log.

The audit/manifest-summary half stays in OVM under its original name.

Run: python3 vault-bridge/scripts/test/test-manifest-wiki-match.py
  -> "OK: all N wiki-match checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (in-memory fixtures, no vault, no live files):
  python3 vault-bridge/scripts/test/test-manifest-wiki-match.py --self-test
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_WIKI_SCRIPT = _HERE.parent / "manifest-wiki-match.py"
_WIKI_SKILL = _HERE.parent.parent / "skills" / "wiki" / "SKILL.md"

errors: list[str] = []


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
    """Static call-site pins for wiki/SKILL.md Phase 3, as (ok, description) pairs.

    Substring pins rather than the whole-section equality used on the audit side: wiki/SKILL.md
    keeps its manifest rationale inline in its own body (there was no #663 reference-doc split
    here), so there is no canonical section to compare whole.
    """
    return [
        ("scripts/manifest-wiki-match.py" in wiki_text,
         "wiki/SKILL.md invokes manifest-wiki-match.py"),
        # Path-agnostic on purpose: the manifest path became `$VAULT_ROOT`-relative when /wiki
        # stopped hardcoding `~/vault`, and a pin naming one spelling of the path goes green the
        # moment the path is rewritten — which is exactly when a regression is most likely.
        (not re.search(r"\bcat\b[^\n]*\.vault-bridge/manifest\.json", wiki_text),
         "wiki/SKILL.md never `cat`s the manifest directly, whatever the path spelling"),
        ("2 KB" in wiki_text, "wiki/SKILL.md documents the 2 KB truncation rationale"),
        ("Exit 3" in wiki_text or "exit 3" in wiki_text,
         "wiki/SKILL.md documents the exit-3 (absent/unparseable/malformed) branch"),
    ]


# --- mutation fixtures, built by `.replace()` off the REAL file (no-op guard below) ------
_CLEAN_WIKI = _WIKI_SKILL.read_text(encoding="utf-8")
_WIKI_NO_RATIONALE = _CLEAN_WIKI.replace("2 KB", "small")
_WIKI_RAW_CAT = _CLEAN_WIKI.replace(
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-wiki-match.py" "$VAULT_ROOT/.vault-bridge/manifest.json"',
    'cat "$VAULT_ROOT/.vault-bridge/manifest.json"')

for _name, _fixture in (("_WIKI_NO_RATIONALE", _WIKI_NO_RATIONALE),
                        ("_WIKI_RAW_CAT", _WIKI_RAW_CAT)):
    assert _fixture != _CLEAN_WIKI, f"{_name} is identical to its base — its .replace() no-opped"

_PIN_CASES = [
    ("clean wiki/SKILL.md passes every guard", _CLEAN_WIKI, True),
    ("wiki/SKILL.md loses its own 2 KB rationale -> FAIL", _WIKI_NO_RATIONALE, False),
    ("wiki/SKILL.md regresses to a raw `cat` of the manifest -> FAIL", _WIKI_RAW_CAT, False),
]


def _self_test() -> int:
    cases = []
    for desc, wiki, expect_pass in _PIN_CASES:
        results = static_checks(wiki)
        got = all(ok for ok, _ in results)
        detail = ""
        if expect_pass and not got:
            detail = f" — unexpectedly failed: {[d for ok, d in results if not ok]}"
        cases.append((f"{desc}{detail}", got == expect_pass))

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {n}")
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
    print(f"\nOK: all wiki-match checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
