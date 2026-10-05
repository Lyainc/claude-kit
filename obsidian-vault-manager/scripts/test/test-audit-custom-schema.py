#!/usr/bin/env python3
"""
Regression test — audit E13 `custom_schema_violation` end to end (#764).

A vault may declare its own note schema in `<vault>/.vault-schema.json`: notes whose
frontmatter matches a schema's `when` must carry its `required` fields and keep `enum`
fields inside the allowed values. audit/SKILL.md Step 7b hands that file to scan-summary.py
via `--schema`; this test pins the contract through the REAL pipeline (ovm-primitives.sh
scan-frontmatter / scan-filename / extract-wikilinks-batch -> files -> scan-summary.py),
the same Steps 5-7b the skill runs.

Cases:
  a) no schema file: output with `--schema <absent>` is BYTE-IDENTICAL to output without
     `--schema`, and has no E13 key (a vault without a schema sees no behaviour change).
  b) schema present, every matching note conforms: E13 == {"count":0,"records":[]}.
  c) a matching note missing a required field (absent key; separately an empty `track:`)
     is reported under `missing`.
  d) a matching note with an out-of-enum value is reported under `invalid`; a note that does
     not match `when` is never reported.
  e) unusable schema (invalid JSON): E13 == {"computed": false, "reason": ...}, exit 0.
  f) static pin: audit/SKILL.md Step 7b passes `--schema "$VAULT_ROOT/.vault-schema.json"`.
  g) YAML comments and null, from the REAL scanner (not a hand-built record): a trailing
     comment on `tags: [업무지도] # note` still matches `when`; `track: null` / `track: ~` are
     missing; `status: 완료 # done` is not an invalid enum value. The scanner contract is
     pinned directly too: quoted "null" stays a string, and a `#` inside quotes or glued to a
     word (`C#`, a URL fragment) is data, not a comment.

Run: python3 obsidian-vault-manager/scripts/test/test-audit-custom-schema.py
Exit 0 on pass, 1 on fail. Builds a fresh mktemp vault and removes it on the way out.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_SKILL_MD = _SCRIPTS.parent / "skills" / "audit" / "SKILL.md"
_PRIM = _SCRIPTS / "ovm-primitives.sh"
_SUMMARY = _SCRIPTS / "scan-summary.py"

SCHEMA = {"schemas": [{
    "name": "업무 항목",
    "when": {"tags": "업무지도"},
    "required": ["track", "status"],
    "enum": {"status": ["대기", "진행중", "완료"]},
}]}

errors: list = []
count = 0


def check(cond: bool, desc: str) -> None:
    global count
    count += 1
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}", file=sys.stderr)
        errors.append(desc)


def note(path: Path, fm_lines: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(fm_lines) + "\n---\n\n# body\n", encoding="utf-8")


def work_note(path: Path, extra: list) -> None:
    note(path, ["title: t", "type: note", "created: 2026-01-01", "tags: [업무지도]"] + extra)


def build_vault(root: Path, bad: dict) -> Path:
    """Fresh vault: one conforming work note, one non-matching note, plus `bad` extras."""
    vault = root / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    work_note(vault / "notes" / "2026-01-01-work-ok.md", ["track: A", "status: 진행중"])
    note(vault / "notes" / "2026-01-01-other.md",
         ["title: o", "type: note", "created: 2026-01-01", "tags: [etc]", "status: 끝"])
    for name, extra in bad.items():
        work_note(vault / "notes" / f"2026-01-01-{name}.md", extra)
    return vault


def summary(vault: Path, work: Path, schema_arg) -> tuple:
    """Steps 5-7b: scans into files, then scan-summary.py. Returns (rc, stdout bytes)."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH", "VAULT_BRIDGE_DISABLE")}
    env["VAULT_BRIDGE_VAULT_ROOT"] = str(vault)
    for sub, out, arg in (("scan-frontmatter", "fm.json", vault),
                          ("scan-filename", "fn.json", vault),
                          ("extract-wikilinks-batch", "links.json", vault)):
        with open(work / out, "wb") as fh:
            p = subprocess.run(["bash", str(_PRIM), sub, str(arg)], stdout=fh,
                               stderr=subprocess.PIPE, env=env)
        if p.returncode != 0:
            raise SystemExit(f"{sub} failed: {p.stderr.decode()}")
    cmd = [sys.executable, str(_SUMMARY), "--frontmatter", str(work / "fm.json"),
           "--filename", str(work / "fn.json"), "--index", str(work / "links.json"),
           "--max-per-type", "50"]  # default cap is 2; keep every E13 record visible
    if schema_arg is not None:
        cmd += ["--schema", str(schema_arg)]
    p = subprocess.run(cmd, capture_output=True, env=env)
    return p.returncode, p.stdout


def e13(stdout: bytes):
    return json.loads(stdout)["errors"].get("E13", "<absent>")


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="audit-custom-schema-"))
    try:
        # a) no schema file
        vault = build_vault(root / "a", {})
        work = root / "a-work"; work.mkdir()
        schema_path = vault / ".vault-schema.json"
        rc0, plain = summary(vault, work, None)
        rc1, with_arg = summary(vault, work, schema_path)
        check(rc0 == 0 and rc1 == 0, "a) no schema file: both runs exit 0")
        check(plain == with_arg, "a) --schema <absent> output is byte-identical to no --schema")
        check("E13" not in json.loads(plain)["errors"], "a) no E13 key without a schema file")

        # b) schema present, all conform
        schema_path.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding="utf-8")
        rc, out = summary(vault, work, schema_path)
        check(rc == 0 and e13(out) == {"count": 0, "records": []},
              "b) conforming notes: E13 == {count:0, records:[]}")

        # c) required missing (absent key; empty value) and d) enum violation
        vault = build_vault(root / "c", {
            "no-track": ["status: 완료"],
            "empty-track": ["track:", "status: 완료"],
            "bad-enum": ["track: B", "status: 끝"],
        })
        work = root / "c-work"; work.mkdir()
        schema_path = vault / ".vault-schema.json"
        schema_path.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding="utf-8")
        rc, out = summary(vault, work, schema_path)
        recs = {Path(r["path"]).name: r for r in e13(out)["records"]}
        check(rc == 0 and e13(out)["count"] == 3, "c/d) exactly the three bad notes are reported")
        check(recs.get("2026-01-01-no-track.md", {}).get("missing") == ["track"],
              "c) absent required key -> missing")
        check(recs.get("2026-01-01-empty-track.md", {}).get("missing") == ["track"],
              "c) empty `track:` -> missing")
        check(recs.get("2026-01-01-bad-enum.md", {}).get("invalid") == {"status": ["끝"]},
              "d) out-of-enum value -> invalid")
        check("2026-01-01-other.md" not in recs and "2026-01-01-work-ok.md" not in recs,
              "d) non-matching and conforming notes are never reported")

        # e) unusable schema
        schema_path.write_text("{not json", encoding="utf-8")
        rc, out = summary(vault, work, schema_path)
        v = e13(out)
        check(rc == 0 and isinstance(v, dict) and v.get("computed") is False and v.get("reason"),
              "e) invalid JSON schema -> computed:false with reason, exit 0")

        # g) comments and null through the real scanner
        vault = root / "g" / "vault"
        (vault / ".obsidian").mkdir(parents=True)
        base = ["type: note", "created: 2026-01-01"]
        note(vault / "notes" / "2026-01-01-comment-tags.md",
             base + ["tags: [업무지도] # domain tag", "status: 완료"])
        note(vault / "notes" / "2026-01-01-null-track.md",
             base + ["tags: [업무지도]", "track: null", "status: 완료"])
        note(vault / "notes" / "2026-01-01-tilde-track.md",
             base + ["tags: [업무지도]", "track: ~", "status: 완료"])
        note(vault / "notes" / "2026-01-01-comment-track.md",
             base + ["tags: [업무지도]", "track: # to fill", "status: 완료"])
        note(vault / "notes" / "2026-01-01-comment-enum.md",
             base + ["tags: [업무지도]", "track: A", "status: 완료 # finished"])
        note(vault / "notes" / "2026-01-01-block-tags.md",
             base + ["tags:", "  # a whole-line comment", "  - 업무지도 # domain", "track: A",
                     "status: 완료"])
        note(vault / "notes" / "2026-01-01-quoted-null.md",
             base + ["tags: [업무지도]", 'track: "null"', "status: '완료' # q"])
        note(vault / "notes" / "2026-01-01-hash-data.md",
             base + ["tags: [업무지도]", 'track: "A # B"', "status: 완료",
                     "lang: C#", "url: http://example.com/#frag"])
        note(vault / "notes" / "2026-01-01-real-bad.md",
             base + ["tags: [업무지도] # c", "track: A", "status: 끝 # bad"])
        work = root / "g-work"; work.mkdir()
        schema_path = vault / ".vault-schema.json"
        schema_path.write_text(json.dumps(SCHEMA, ensure_ascii=False), encoding="utf-8")
        rc, out = summary(vault, work, schema_path)
        recs = {Path(r["path"]).name: r for r in e13(out)["records"]}
        fm = {Path(r["path"]).name: r["frontmatter"]
              for r in json.loads((work / "fm.json").read_text(encoding="utf-8"))}
        check(rc == 0 and fm["2026-01-01-comment-tags.md"]["tags"] == ["업무지도"],
              "g) scanner: `tags: [x] # c` is the list [x], not a string")
        check(fm["2026-01-01-block-tags.md"]["tags"] == ["업무지도"],
              "g) scanner: a whole-line comment and a trailing comment do not break a block list")
        check(fm["2026-01-01-null-track.md"]["track"] is None
              and fm["2026-01-01-tilde-track.md"]["track"] is None,
              "g) scanner: unquoted null and ~ are JSON null")
        check(fm["2026-01-01-comment-track.md"]["track"] == [],
              "g) scanner: `track: # note` stays empty ([]), as `track:` always did")
        check(fm["2026-01-01-quoted-null.md"]["track"] == "null"
              and fm["2026-01-01-quoted-null.md"]["status"] == "완료",
              "g) scanner: quoted \"null\" is the string; a comment after a quoted value is cut")
        check(fm["2026-01-01-hash-data.md"]["track"] == "A # B"
              and fm["2026-01-01-hash-data.md"]["lang"] == "C#"
              and fm["2026-01-01-hash-data.md"]["url"] == "http://example.com/#frag",
              "g) scanner: `#` inside quotes or glued to a word is data, not a comment")
        check(recs.get("2026-01-01-comment-tags.md", {}).get("missing") == ["track"],
              "g) E13: a commented `tags:` still matches `when` (violation not missed)")
        check(recs.get("2026-01-01-null-track.md", {}).get("missing") == ["track"]
              and recs.get("2026-01-01-tilde-track.md", {}).get("missing") == ["track"]
              and recs.get("2026-01-01-comment-track.md", {}).get("missing") == ["track"],
              "g) E13: `track: null`, `track: ~` and `track: # note` are missing")
        check("2026-01-01-comment-enum.md" not in recs and "2026-01-01-block-tags.md" not in recs,
              "g) E13: a trailing comment is not part of an enum value (no false invalid)")
        check("2026-01-01-quoted-null.md" not in recs and "2026-01-01-hash-data.md" not in recs,
              "g) E13: quoted \"null\" and a quoted `#` are real values, so not reported")
        check(recs.get("2026-01-01-real-bad.md", {}).get("invalid") == {"status": ["끝"]}
              and e13(out)["count"] == 5,
              "g) E13: a real violation behind a comment is still reported (exactly 5 records)")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # f) static pin on SKILL.md Step 7b
    text = _SKILL_MD.read_text(encoding="utf-8")
    step = text[text.index("7b."):]
    step = step[:step.index("\n8. ")]
    check('--schema "$VAULT_ROOT/.vault-schema.json"' in step and "scan-summary.py" in step,
          'f) SKILL.md Step 7b passes --schema "$VAULT_ROOT/.vault-schema.json"')

    if errors:
        print(f"FAIL: {len(errors)} of {count} custom-schema checks failed", file=sys.stderr)
        sys.exit(1)
    print(f"OK: all {count} custom-schema cases passed")


if __name__ == "__main__":
    main()
