#!/usr/bin/env python3
"""Regression test — retro's E8 read is filtered, not truncated (#460).

retro read the vault-bridge manifest with `cat`. The harness persists a large Bash
result to a file and passes the model a 2 KB PREVIEW, so on the live vault (121 KB /
168 files) exactly three `path` entries reached the model — the third cut mid-string —
and retro reported "승격 후보 없음" from a 1.8% scan. The output was character-for-
character indistinguishable from a real full scan: a silent fail-open, the same shape
as the CI guards fixed in #456/#451.

A prose grep alone would not have caught this (the SKILL.md text was correct; the
runtime behaviour was not), so the filter is a real script and this test EXECUTES it
against manifest fixtures:

  1. Missing manifest    -> exit 3 (caller skips PROMOTE), never "0 candidates".
  2. Unparseable / wrong-shape manifest -> exit 3 too. Same branch, same reason.
  2b. A malformed-but-parseable manifest (a `files` entry that is not an object, a
     non-numeric threshold field, a bad env override) takes the SAME exit 3. A traceback
     at exit 1 would be a fourth branch retro's SKILL.md has no instruction for.
  3. Zero candidates     -> exit 0, `e8_candidates: []` WITH `scanned` = file count.
                            "0 of 168 scanned" and "0 of 3 read" must not look alike.
                            `scanned` is serialized FIRST, so a future truncation eats the
                            list rather than the coverage number.
  4. Real candidates     -> only the 5 contract fields, refs OR access threshold.
  5. The leaf `promotion_candidate` flag is IGNORED in both directions: a flagged entry
     under both thresholds is not a candidate, and an unflagged one over a threshold is.
     The flag ignores `status` (#435), so the consumer derives the condition itself.
  5b. `status` is NOT screened, only emitted. It is the one field PROMOTE re-reads from
     the note itself, so screening the manifest's possibly-stale copy could silently drop
     a note that went back to `draft` since the last refresh — the same under-report this
     script exists to close. Over-listing is safe: PROMOTE drops them before the user gate.
  6. Env thresholds (VAULT_AUDIT_PROMOTION_REFS / _ACCESS) are honoured.

Plus static checks on the live retro/SKILL.md, so the call site cannot drift back:
it invokes the script, it does not `cat` the manifest, it does not key off
`promotion_candidate`, and it still distinguishes exit 3 from an empty list.

Run: python3 feedback-loop/scripts/test/test-e8-candidates.py
Exit 0 on pass, 1 on fail.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "feedback-loop" / "scripts" / "e8-candidates.py"
_SKILL = _REPO_ROOT / "feedback-loop" / "skills" / "retro" / "SKILL.md"


def _run(manifest: Path | str, **env_extra) -> tuple[int, str]:
    env = dict(os.environ, **env_extra)
    r = subprocess.run([sys.executable, str(_SCRIPT), str(manifest)],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout.strip()


def _file(files: list[dict]) -> dict:
    return {"generated_at": "2026-07-31", "schema_version": 1,
            "file_count": len(files), "files": files}


def _note(path: str, *, type_="note", status="draft", refs=0, access=0, **extra) -> dict:
    e = {"path": path, "type": type_, "references_in": refs, "access_count": access,
         "title": "t", "summary": "s" * 200, "tags": ["x"], "mtime": 0,
         "size_bytes": 1, "references_out": 0}
    if status is not None:
        e["status"] = status
    e.update(extra)
    return e


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    errors: list[str] = []

    def check(cond: bool, desc: str) -> None:
        if cond:
            print(f"  ok   {desc}")
        else:
            print(f"  FAIL {desc}", file=sys.stderr)
            errors.append(desc)

    if not _SCRIPT.is_file():
        print(f"  FAIL {_SCRIPT} missing — retro still reads the manifest unfiltered",
              file=sys.stderr)
        print("\nRESULT: 1 check(s) FAILED — see above.")
        return 1

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 1. Missing manifest.
        rc, out = _run(tmp / "nope.json")
        check(rc == 3 and out == "", "missing manifest -> exit 3, no stdout verdict")

        # 2. Unparseable, and structurally wrong but valid JSON.
        bad = tmp / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        rc, _ = _run(bad)
        check(rc == 3, "unparseable manifest -> exit 3")
        wrong = tmp / "wrong.json"
        wrong.write_text(json.dumps({"files": "nope"}), encoding="utf-8")
        rc, _ = _run(wrong)
        check(rc == 3, "manifest with non-list `files` -> exit 3")

        # 2b. Malformed but parseable: same branch, never a traceback at exit 1.
        for name, payload in (("entries", {"files": ["notes/a.md", 42]}),
                              ("refs", _file([_note("notes/a.md", refs="many")]))):
            bad2 = tmp / f"malformed-{name}.json"
            bad2.write_text(json.dumps(payload), encoding="utf-8")
            rc, out = _run(bad2)
            check(rc == 3 and out == "",
                  f"malformed manifest ({name}) -> exit 3, not a traceback")

        # 3. Zero candidates out of many scanned — the case that was misreported.
        many = tmp / "many.json"
        many.write_text(json.dumps(_file(
            [_note(f"notes/n{i}.md", status="archived", refs=0, access=0) for i in range(168)]
        )), encoding="utf-8")
        rc, out = _run(many)
        d = json.loads(out)
        check(rc == 0 and d["e8_candidates"] == [] and d["scanned"] == 168,
              "0 candidates over 168 files -> exit 0, empty list, scanned=168")
        check(out.index('"scanned"') < out.index('"e8_candidates"'),
              "`scanned` is serialized before the list (truncation eats the list, not it)")
        check(len(out) < 2000,
              f"output stays under the 2 KB preview cut ({len(out)} B for 168 files)")

        # 4/5. Real candidates + the archived-but-flagged trap.
        mixed = tmp / "mixed.json"
        mixed.write_text(json.dumps(_file([
            _note("notes/by-refs.md", refs=3),                        # refs threshold
            _note("notes/by-access.md", status="raw", access=5),      # access threshold
            _note("notes/decision.md", type_="decision", refs=4),
            _note("notes/below.md", refs=2, access=4),                # under both
            _note("notes/no-status.md", status=None, refs=9),         # status absent, still screened in
            _note("inbox/session.md", type_="session", refs=9, status="draft"),
            _note("notes/flagged-but-cold.md", refs=0, access=0,
                  promotion_candidate=True),                          # #435 trap: flag ignored
        ])), encoding="utf-8")
        rc, out = _run(mixed)
        d = json.loads(out)
        paths = sorted(c["path"] for c in d["e8_candidates"])
        check(rc == 0 and paths == ["notes/by-access.md", "notes/by-refs.md",
                                    "notes/decision.md", "notes/no-status.md"],
              f"refs OR access, note/decision only, status not screened (got {paths})")
        check(all(set(c) == {"path", "references_in", "access_count", "status", "type"}
                  for c in d["e8_candidates"]),
              "each candidate carries exactly the 5 contract fields")
        check("notes/flagged-but-cold.md" not in paths,
              "the leaf promotion_candidate flag is ignored — the condition is re-derived (#435)")
        check("notes/no-status.md" in paths,
              "`status` is emitted, not screened — PROMOTE re-reads it from the note itself")

        # 6. Env thresholds.
        rc, out = _run(mixed, VAULT_AUDIT_PROMOTION_REFS="2",
                       VAULT_AUDIT_PROMOTION_ACCESS="99")
        paths = sorted(c["path"] for c in json.loads(out)["e8_candidates"])
        check(paths == ["notes/below.md", "notes/by-refs.md", "notes/decision.md",
                        "notes/no-status.md"],
              f"env thresholds shift the cut (refs>=2, access>=99 -> {paths})")

    # Static: the retro call site cannot drift back to `cat`.
    text = _SKILL.read_text(encoding="utf-8")
    check("scripts/e8-candidates.py" in text,
          "retro/SKILL.md invokes e8-candidates.py")
    check("cat \"$VAULT_ROOT/.vault-bridge/manifest.json\"" not in text
          and "cat $VAULT_ROOT/.vault-bridge/manifest.json" not in text,
          "retro/SKILL.md no longer `cat`s the manifest")
    check("2 KB" in text or "2KB" in text,
          "the why (2 KB preview truncation) is recorded at the call site")
    check("promotion_candidate: true" not in text,
          "retro/SKILL.md no longer keys off the leaf `promotion_candidate` flag")
    check("Exit 3" in text or "exit 3" in text,
          "exit 3 (absent/unparseable) stays distinct from an empty candidate list")

    print()
    if errors:
        print(f"RESULT: {len(errors)} check(s) FAILED — see above.")
        return 1
    print("OK: all 19 e8-candidates checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
