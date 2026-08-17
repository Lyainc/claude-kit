#!/usr/bin/env python3
"""manifest-summary.py regression (#468, mirrors #460's feedback-loop/scripts/test/test-e8-candidates.py).

audit/SKILL.md never `cat`s .vault-bridge/manifest.json directly — the harness truncates
large Bash output to a 2 KB preview before the model sees it, so a raw `cat` of a real
(100+ KB) manifest silently degrades to whichever ~3 entries survive the cut,
indistinguishable from a legitimately small/clean manifest.

Runs manifest-summary.py via subprocess against real temp fixture files (not a mocked
import), then statically greps the live audit/SKILL.md call site to pin that it never
regresses back to a raw `cat` of the manifest.

#663: audit/SKILL.md sat at the #447 5,000-token budget with no headroom, so the
*rationale* prose (why a raw `cat` is forbidden — the 2 KB harness preview cut — and the
exit-3 branch) moved out of the skill body into `reference/vault-audit-rules.md` ->
"Reading the manifest". The pins followed the text rather than being deleted (#609: an
unpinned region disappears silently). The skill body keeps the executable call plus a
pointer, and both of those are pinned here too, so the pointer cannot rot away and leave
the contract unreachable from the body.

#645: the wiki-side half of this test (manifest-wiki-match.py + wiki/SKILL.md) moved to
vault-bridge/scripts/test/test-manifest-reads.py alongside the skill and script it covers.

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
_AUDIT_SKILL = _HERE.parent.parent / "skills" / "audit" / "SKILL.md"
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


def static_checks(audit_text: str, rules_text: str) -> list:
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
    ("_RULES_CAT_ADVISORY", _RULES_CAT_ADVISORY, _FIX_RULES),
    ("_RULES_CAT_RETRY_OK", _RULES_CAT_RETRY_OK, _FIX_RULES),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"


def _self_test() -> int:
    cases = []

    for ok, desc in static_checks(_FIX_AUDIT, _FIX_RULES):
        cases.append((f"passing: {desc}", ok))

    def _expect_fail(label, audit, rules):
        failed = [d for ok, d in static_checks(audit, rules) if not ok]
        cases.append((f"{label} (expect FAIL): {failed}", bool(failed)))

    _expect_fail("canonical rationale deleted from reference doc",
                 _FIX_AUDIT, _RULES_NO_RATIONALE)
    _expect_fail("canonical exit-3 branch deleted from reference doc",
                 _FIX_AUDIT, _RULES_NO_EXIT3)
    _expect_fail("skill body drops the pointer to the reference doc",
                 _AUDIT_NO_POINTER, _FIX_RULES)
    _expect_fail("skill body regresses to a raw cat",
                 _AUDIT_RAW_CAT, _FIX_RULES)
    _expect_fail("canonical raw-cat prohibition reworded into a recommendation",
                 _FIX_AUDIT, _RULES_CAT_ADVISORY)
    _expect_fail("canonical exit-3 branch made to allow a raw-cat retry",
                 _FIX_AUDIT, _RULES_CAT_RETRY_OK)

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

    # ---- static call-site guard: audit/SKILL.md may not regress to a raw `cat` ----

    for ok, desc in static_checks(
        _AUDIT_SKILL.read_text(encoding="utf-8"),
        _AUDIT_RULES.read_text(encoding="utf-8"),
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
