#!/usr/bin/env python3
"""`verified:`/`provenance:` field-name contract pin, writer↔reader across a plugin boundary
(#645 B3).

Before #645, wiki/SKILL.md (writer of `verified:`/`provenance:`) and audit's E12 wiki
self-audit (reader of the same two fields) both lived in obsidian-vault-manager — a rename on
one side broke the other inside a single plugin's own test suite. #645 moved the writer to
vault-bridge while the reader (audit E12, `obsidian-vault-manager/scripts/test/audit-validate.py`
REQUIRED_FM_FIELDS + `_wiki_pages`/`detect_stale_wiki`/`detect_unverifiable_wiki`) stayed in
obsidian-vault-manager — so the two sides no longer share a test run, a lint pass, or even a
release. If the field name drifts on either side now, nothing fails: `audit-validate.py`'s
`fm.get("verified")` just returns `None` for every page and E12 silently reports 0 stale/
unverified pages instead of erroring — "scan succeeds, only the noise (or its absence) changes"
is exactly the failure mode B3 exists to catch (issue #645 verdict comment §4).

This is a legitimate cross-plugin parity gate, not the `check-trigger-regression.py`-style
independent-instance pattern (#645 verdict comment §7: "그것들은 한 계약을 두 구현이 지키는
parity gate라 crossing이 정당") — `verified:`/`provenance:` are ONE contract kept by two
implementations, which is precisely when a cross-plugin test is warranted.

Pins (substring, not whole-section — neither side treats this as its own canonical prose block):
1. `vault-bridge/skills/wiki/SKILL.md`'s frontmatter template writes `verified:` and
   `provenance:` (Phase 4).
2. `obsidian-vault-manager/scripts/test/audit-validate.py`'s `REQUIRED_FM_FIELDS` names
   `provenance`, and its wiki-staleness reader code calls `fm.get("verified")`.

Run: python3 vault-bridge/scripts/test/test-wiki-frontmatter-contract.py
  -> "OK: all N checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (in-memory fixtures, mutated copies of the real files):
  python3 vault-bridge/scripts/test/test-wiki-frontmatter-contract.py --self-test
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_WIKI_SKILL = _HERE.parent.parent / "skills" / "wiki" / "SKILL.md"
_AUDIT_VALIDATE = _HERE.parent.parent.parent / "obsidian-vault-manager" / "scripts" / "test" / "audit-validate.py"

errors = []


def check(cond: bool, desc: str) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def static_checks(wiki_text: str, audit_validate_text: str) -> list:
    return [
        ("verified: YYYY-MM-DD" in wiki_text,
         "wiki/SKILL.md frontmatter template writes `verified:`"),
        ("provenance: <one line" in wiki_text,
         "wiki/SKILL.md frontmatter template writes `provenance:`"),
        ('REQUIRED_FM_FIELDS = ("created", "tags", "type", "provenance")' in audit_validate_text,
         "audit-validate.py's REQUIRED_FM_FIELDS names `provenance`"),
        ('fm.get("verified")' in audit_validate_text,
         "audit-validate.py's wiki-staleness reader calls fm.get(\"verified\")"),
    ]


_CLEAN_WIKI = _WIKI_SKILL.read_text(encoding="utf-8")
_CLEAN_AUDIT_VALIDATE = _AUDIT_VALIDATE.read_text(encoding="utf-8")

# Writer side renamed the field the reader still expects — the exact drift B3 exists to catch.
_WIKI_FIELD_RENAMED = _CLEAN_WIKI.replace(
    "verified: YYYY-MM-DD", "verified_at: YYYY-MM-DD")
_WIKI_PROVENANCE_DROPPED = _CLEAN_WIKI.replace(
    "provenance: <one line: the query", "notes: <one line: the query")
# Reader side renamed its access — same drift, other direction.
_AUDIT_FIELD_RENAMED = _CLEAN_AUDIT_VALIDATE.replace(
    'fm.get("verified")', 'fm.get("verified_at")')
_AUDIT_REQUIRED_FIELDS_DROPPED = _CLEAN_AUDIT_VALIDATE.replace(
    'REQUIRED_FM_FIELDS = ("created", "tags", "type", "provenance")',
    'REQUIRED_FM_FIELDS = ("created", "tags", "type")')

for _name, _fixture, _base in (
    ("_WIKI_FIELD_RENAMED", _WIKI_FIELD_RENAMED, _CLEAN_WIKI),
    ("_WIKI_PROVENANCE_DROPPED", _WIKI_PROVENANCE_DROPPED, _CLEAN_WIKI),
    ("_AUDIT_FIELD_RENAMED", _AUDIT_FIELD_RENAMED, _CLEAN_AUDIT_VALIDATE),
    ("_AUDIT_REQUIRED_FIELDS_DROPPED", _AUDIT_REQUIRED_FIELDS_DROPPED, _CLEAN_AUDIT_VALIDATE),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

_PIN_CASES = [
    ("clean wiki/SKILL.md + audit-validate.py pass every guard",
     _CLEAN_WIKI, _CLEAN_AUDIT_VALIDATE, True),
    ("writer renames verified: -> verified_at: -> FAIL", _WIKI_FIELD_RENAMED, _CLEAN_AUDIT_VALIDATE, False),
    ("writer drops provenance: from the template -> FAIL",
     _WIKI_PROVENANCE_DROPPED, _CLEAN_AUDIT_VALIDATE, False),
    ("reader renames its fm.get(\"verified\") access -> FAIL", _CLEAN_WIKI, _AUDIT_FIELD_RENAMED, False),
    ("reader drops provenance from REQUIRED_FM_FIELDS -> FAIL",
     _CLEAN_WIKI, _AUDIT_REQUIRED_FIELDS_DROPPED, False),
]


def _self_test() -> int:
    cases = []
    for desc, wiki, audit_validate, expect_pass in _PIN_CASES:
        results = static_checks(wiki, audit_validate)
        got = all(ok for ok, _ in results)
        detail = ""
        if expect_pass and not got:
            detail = f" — unexpectedly failed: {[d for ok, d in results if not ok]}"
        cases.append((f"{desc}{detail}", got == expect_pass))

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


def main() -> int:
    for ok, desc in static_checks(_CLEAN_WIKI, _CLEAN_AUDIT_VALIDATE):
        check(ok, desc)

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print(f"\nOK: all {4} checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
