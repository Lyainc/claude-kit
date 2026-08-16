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

#663: audit/SKILL.md sat at the #447 5,000-token budget with no headroom, so the *rationale*
prose (why a raw `cat` is forbidden — the 2 KB harness preview cut — and the exit-3 branch) moved
out of the skill body into `reference/vault-audit-rules.md` -> "Reading the manifest". The pins
followed the text rather than being deleted (#609: an unpinned region disappears silently). The
skill body keeps the executable call plus a pointer, and both of those are pinned here too, so
the pointer cannot rot away and leave the contract unreachable from the body.

Run: python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py
  -> "OK: all N manifest-read checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (in-memory fixtures, no vault, no live files):
  python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py --self-test
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
_AUDIT_RULES = _HERE.parent.parent / "reference" / "vault-audit-rules.md"

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


def static_checks(audit_text: str, rules_text: str, wiki_text: str) -> list:
    """Static pins for the manifest-read contract, as (ok, description) pairs.

    Split out of main() so --self-test can run the identical checks against in-memory
    fixtures — including a fixture that corrupts the CANONICAL contract text, which since
    #663 lives in reference/vault-audit-rules.md rather than in audit/SKILL.md's body.
    """
    return [
        # audit/SKILL.md keeps the executable call + the pointer to the canonical contract.
        ("scripts/manifest-summary.py" in audit_text,
         "audit/SKILL.md invokes manifest-summary.py"),
        ('cat "$VAULT_ROOT/.vault-bridge/manifest.json"' not in audit_text,
         "audit/SKILL.md no longer `cat`s the manifest directly"),
        ("reference/vault-audit-rules.md" in audit_text and "Reading the manifest" in audit_text,
         "audit/SKILL.md points at reference/vault-audit-rules.md -> Reading the manifest (#663)"),
        # The rationale + exit-code branch themselves are pinned where they now live.
        ("2 KB" in rules_text,
         "vault-audit-rules.md documents the 2 KB truncation rationale (#663 canonical copy)"),
        ("Exit 3" in rules_text or "exit 3" in rules_text,
         "vault-audit-rules.md documents the exit-3 (absent/unparseable) branch"),
        # Pinned by the prohibition's own wording, not by `"cat" in rules_text`: `cat` is a
        # substring of `duplicate`/`location`/`classification`, so a bare containment check
        # stays true even after the sentence is reworded into a recommendation.
        ("**Never `cat` the manifest directly.**" in rules_text,
         "vault-audit-rules.md states the raw-`cat` prohibition"),
        ("never re-attempt with a raw `cat` as a fallback" in rules_text,
         "vault-audit-rules.md forbids a raw `cat` retry after the exit-3 branch"),
        # wiki/SKILL.md is unchanged by #663 — its rationale still lives in its own body.
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

_FIX_AUDIT = """\
8. Read manifest summary through the filter script — never `cat` the manifest directly:
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/..."
   The binding contract is ${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md ->
   **Reading the manifest**.
"""

_FIX_RULES = """\
### Reading the manifest — never `cat` it (#468, #460)

**Never `cat` the manifest directly.**
The harness truncates large Bash output to a 2 KB preview, so a raw `cat` silently degrades.

- Exit 0 -> parse stdout as {file_count, generated_at}.
- Exit 3 -> set manifest_summary to null, and never re-attempt with a raw `cat` as a fallback.
"""

_FIX_WIKI = """\
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-wiki-match.py" ...
2 KB preview cut rationale. Exit 3 -> absent/unparseable/malformed.
"""

# The #663 mutation cases: corrupt the CANONICAL contract (now in the reference doc) and the
# body's pointer to it, and assert the pins still FAIL.
_RULES_NO_RATIONALE = _FIX_RULES.replace("2 KB preview", "preview")
_RULES_NO_EXIT3 = _FIX_RULES.replace("Exit 3 ->", "Otherwise ->")
_AUDIT_NO_POINTER = _FIX_AUDIT.replace(
    "   The binding contract is ${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md ->\n"
    "   **Reading the manifest**.\n", "")
_AUDIT_RAW_CAT = _FIX_AUDIT.replace(
    'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/..."',
    'cat "$VAULT_ROOT/.vault-bridge/manifest.json"')
_WIKI_NO_RATIONALE = _FIX_WIKI.replace("2 KB preview", "preview")
# The prohibition reworded into a recommendation — invisible to a bare `"cat" in rules_text`
# check, since `cat` is a substring of `duplicate`/`location`/`classification`.
_RULES_CAT_ADVISORY = _FIX_RULES.replace(
    "**Never `cat` the manifest directly.**", "Prefer the filter script over a raw `cat`.")
_RULES_CAT_RETRY_OK = _FIX_RULES.replace(
    "and never re-attempt with a raw `cat` as a fallback",
    "then retry with a raw `cat` if needed")

# A fixture built by `.replace()` whose target string has drifted silently becomes a copy of
# its base, and an expect-FAIL case on an unmodified copy would then be testing nothing.
for _name, _fixture, _base in (
    ("_RULES_NO_RATIONALE", _RULES_NO_RATIONALE, _FIX_RULES),
    ("_RULES_NO_EXIT3", _RULES_NO_EXIT3, _FIX_RULES),
    ("_AUDIT_NO_POINTER", _AUDIT_NO_POINTER, _FIX_AUDIT),
    ("_AUDIT_RAW_CAT", _AUDIT_RAW_CAT, _FIX_AUDIT),
    ("_WIKI_NO_RATIONALE", _WIKI_NO_RATIONALE, _FIX_WIKI),
    ("_RULES_CAT_ADVISORY", _RULES_CAT_ADVISORY, _FIX_RULES),
    ("_RULES_CAT_RETRY_OK", _RULES_CAT_RETRY_OK, _FIX_RULES),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"


def _self_test() -> int:
    cases = []

    for ok, desc in static_checks(_FIX_AUDIT, _FIX_RULES, _FIX_WIKI):
        cases.append((f"passing: {desc}", ok))

    def _expect_fail(label, audit, rules, wiki):
        failed = [d for ok, d in static_checks(audit, rules, wiki) if not ok]
        cases.append((f"{label} (expect FAIL): {failed}", bool(failed)))

    _expect_fail("canonical rationale deleted from reference doc",
                 _FIX_AUDIT, _RULES_NO_RATIONALE, _FIX_WIKI)
    _expect_fail("canonical exit-3 branch deleted from reference doc",
                 _FIX_AUDIT, _RULES_NO_EXIT3, _FIX_WIKI)
    _expect_fail("skill body drops the pointer to the reference doc",
                 _AUDIT_NO_POINTER, _FIX_RULES, _FIX_WIKI)
    _expect_fail("skill body regresses to a raw cat",
                 _AUDIT_RAW_CAT, _FIX_RULES, _FIX_WIKI)
    _expect_fail("wiki body loses its own 2 KB rationale",
                 _FIX_AUDIT, _FIX_RULES, _WIKI_NO_RATIONALE)
    _expect_fail("canonical raw-cat prohibition reworded into a recommendation",
                 _FIX_AUDIT, _RULES_CAT_ADVISORY, _FIX_WIKI)
    _expect_fail("canonical exit-3 branch made to allow a raw-cat retry",
                 _FIX_AUDIT, _RULES_CAT_RETRY_OK, _FIX_WIKI)

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

    # ---- static call-site guards: neither SKILL.md may regress to a raw `cat` ----

    for ok, desc in static_checks(
        _AUDIT_SKILL.read_text(encoding="utf-8"),
        _AUDIT_RULES.read_text(encoding="utf-8"),
        _WIKI_SKILL.read_text(encoding="utf-8"),
    ):
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
