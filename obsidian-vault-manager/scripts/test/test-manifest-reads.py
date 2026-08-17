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
skill body keeps the executable call plus a locator, and both of those are pinned here too, so
the locator cannot rot away and leave the contract unreachable from the body.

Both are pinned by WHOLE-SECTION VERBATIM EQUALITY (heading to next heading / step to next step,
whitespace-normalised) plus neighbour-anchor identity, not by scattered substring checks — see
the design note above `_READING_MANIFEST_SECTION`.

Run: python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py
  -> "OK: all N manifest-read checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (in-memory fixtures, no vault, no live files):
  python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py --self-test
"""
import json
import re
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


# ---------------------------------------------------------------------------
# Canonical contract text (#663)
#
# WHY WHOLE-SECTION EQUALITY, not a set of clause pins. Until now this file pinned the contract
# with scattered `in` checks ("2 KB", "Exit 3", the prohibition sentence, the no-retry clause).
# Every partial anchor is a blocklist of the last wording someone tried: it closes the clause it
# names and leaves the next neighbour green after deletion or a premise flip that keeps the
# pinned sentence verbatim and makes it false. So the section's OWN TEXT is the pin and the
# comparison is TOTAL (same shape as `_EXCHANGE_LOOP_SECTION` in
# thinking-tools/scripts/test/test-mode-compose.py). Whitespace is normalised: a reflow is not a
# change, an edit to the words is — and updating these constants is the deliberate act that
# records a contract change, in the same commit as the edit.
#
# Both slices run from their heading (reference.md) / step number (SKILL.md) to the NEXT one, so
# a contradicting clause parked at the bottom is inside the pin, not outside it. They are
# section-SCOPED: a verbatim copy pasted into a neighbouring section is not what gets compared.
#
# The four clause pins that survive are kept for DIAGNOSIS, not coverage — each names a distinct
# polarity/premise flip, so the failure message says which invariant died instead of only "the
# section changed".
# ---------------------------------------------------------------------------

_READING_MANIFEST_SECTION_RE = re.compile(
    r"^### Reading the manifest\b.*?(?=^#{2,4} |\Z)",
    re.MULTILINE | re.DOTALL,
)
# The SKILL.md locator is a numbered step, not a heading, so the step number is its delimiter —
# and a heading counts as one too, so an inserted heading cannot extend the slice past it.
_SKILL_STEP8_RE = re.compile(
    r"^8\. Read manifest summary\b.*?(?=^\d+\. |^#{1,6} |\Z)",
    re.MULTILINE | re.DOTALL,
)

_HEADING_ANCHOR_RE = re.compile(r"^#{1,6} ")
_STEP_OR_HEADING_ANCHOR_RE = re.compile(r"^(?:#{1,6} |\d+\. )")


def _normalise(s: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(s.split())


def _section(pattern: re.Pattern, text: str) -> str:
    """The whole named slice, delimiter to next delimiter, whitespace-normalised ("" if absent)."""
    match = pattern.search(text)
    return _normalise(match.group(0)) if match else ""


_READING_MANIFEST_SECTION = _normalise("""\
### Reading the manifest — never `cat` it (#468, #460)

**Canonical text (#663).** `audit/SKILL.md` Phase 1 Step 8 points here; this section is the
binding contract, not background, and must be applied as written (the body keeps the call plus a
locator). Its whole text — heading to the next heading, so nothing unpinned may be parked at the
bottom — is pinned VERBATIM by `_READING_MANIFEST_SECTION` in
`obsidian-vault-manager/scripts/test/test-manifest-reads.py`, and the headings on either side are
pinned by identity so an inserted sibling cannot park contradicting text just outside it. Editing
anything below is a deliberate contract change and updates that constant in the same commit; a
reflow is free (the comparison is whitespace-normalised).

**Never `cat` the manifest directly.** It can run past 100 KB, and the harness truncates large
Bash output to a 2 KB preview, so a raw `cat` silently degrades to whichever entries survive the
cut — indistinguishable from a legitimately small manifest. Use the filter script instead, which
reads the full file on disk and returns only the two fields the REPORT header needs:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/.vault-bridge/manifest.json"
```

- **Exit 0** → parse stdout as `{file_count, generated_at}` and use it as `manifest_summary`.
- **Exit 3** (manifest absent, unparseable, or missing a required field) → set `manifest_summary`
  to null, and **never re-attempt with a raw `cat` as a fallback**. A truncated read is worse than
  no read: the header would print a confident wrong count instead of `없음`.

---
""")

# The ALWAYS-LOADED body, pinned the same way: at runtime the loaded SKILL.md outranks an
# on-demand reference doc, so a body step saying "exit 3 → retry with cat" defeats a perfectly
# pinned canonical section. Comparing the step WHOLE is what catches that.
_SKILL_STEP8 = _normalise("""\
8. Read manifest summary (used for REPORT header) through the filter script — **never `cat` the
   manifest directly** (#468, #460). Uses the `$VAULT_ROOT` from Step 1:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/.vault-bridge/manifest.json"
   ```
   Exit 0 → `manifest_summary` = parsed `{file_count, generated_at}`; exit 3 → null.
   **Apply `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → Reading the manifest as
   written — that section is the binding contract** for why a raw `cat` is forbidden and the full
   exit-code branch; the line above is a locator, not a summary you may act from alone. This whole
   step is pinned VERBATIM by `_SKILL_STEP8` in
   `obsidian-vault-manager/scripts/test/test-manifest-reads.py`.
""")


# --- adjacency: a heading is otherwise the escape hatch ---------------------------------
#
# "Nothing unpinned may be parked at the bottom of a section" holds only up to the NEXT
# delimiter, so one inserted `#### Addendum` moves arbitrary contradicting text outside every
# pin while leaving both whole-section comparisons byte-identical. Neither file is wholly
# contract, so a whole-file heading-SET assertion would be wrong (every unrelated section edit
# would red); instead each pinned slice's two NEIGHBOURING anchors are pinned BY IDENTITY, so an
# inserted sibling on either side reds.
#
# WHAT THIS DOES NOT COVER: contradicting text parked elsewhere in either file — under a
# non-adjacent heading, or appended at the end. Nothing routes the skill to those (the SKILL.md
# locator names this one section, and the locator is itself pinned whole), so reaching them takes
# a second edit to the pinned regions.
_NEIGHBOURS = {
    "vault-audit-rules.md § Reading the manifest": (
        "rules", _READING_MANIFEST_SECTION_RE, _HEADING_ANCHOR_RE,
        ("## Manifest Summary (display-only)", "## REPORT output example"),
    ),
    "audit/SKILL.md Phase 1 Step 8": (
        "audit", _SKILL_STEP8_RE, _STEP_OR_HEADING_ANCHOR_RE,
        ("7. Build a global link index (`{target_stem → [source_paths]}`) from wikilinks vault-wide —",
         "9. Detect E9 vocabulary inconsistency pairs (vault-wide, deterministic — never aggregate tags/keys in the LLM):"),
    ),
}


def _neighbour_anchors(pattern: re.Pattern, text: str, anchor: re.Pattern) -> tuple:
    """The anchor line immediately before and immediately after the pinned slice."""
    match = pattern.search(text)
    if not match:
        return ("", "")
    before = [ln for ln in text[:match.start()].splitlines() if anchor.match(ln)]
    after = [ln for ln in text[match.end():].splitlines() if anchor.match(ln)]
    return (before[-1] if before else "", after[0] if after else "")


# --- clause pins kept for a readable diagnosis of one specific flip each ---------------
# `cat` is a substring of `duplicate`/`location`/`classification`, so these pin the
# prohibition's own wording, never a bare `"cat" in rules_text`.
_CAT_PROHIBITION = "**Never `cat` the manifest directly.**"
_NO_CAT_RETRY = "**never re-attempt with a raw `cat` as a fallback**"
_TRUNCATION_RATIONALE = "2 KB preview"
_EXIT3_BRANCH = "**Exit 3** (manifest absent, unparseable, or missing a required field)"


def static_checks(audit_text: str, rules_text: str, wiki_text: str) -> list:
    """Static pins for the manifest-read contract, as (ok, description) pairs.

    Split out of main() so --self-test can run the identical checks against mutated copies of
    the REAL files — including copies that corrupt the CANONICAL contract text, which since
    #663 lives in reference/vault-audit-rules.md rather than in audit/SKILL.md's body.
    """
    rules = _normalise(rules_text)
    texts = {"rules": rules_text, "audit": audit_text}
    return [
        # --- total: the whole slice, verbatim ---
        (_section(_READING_MANIFEST_SECTION_RE, rules_text) == _READING_MANIFEST_SECTION,
         "vault-audit-rules.md § Reading the manifest matches VERBATIM (#663 canonical copy)"),
        (_section(_SKILL_STEP8_RE, audit_text) == _SKILL_STEP8,
         "audit/SKILL.md Phase 1 Step 8 (loaded body) matches VERBATIM"),
    ] + [
        # --- adjacency: no sibling inserted on either side of a pinned slice ---
        (_neighbour_anchors(pattern, texts[key], anchor) == expected,
         f"{label} still sits between its two known anchors "
         f"(an inserted sibling would park text outside the pin)")
        for label, (key, pattern, anchor, expected) in _NEIGHBOURS.items()
    ] + [
        # --- diagnostic: one named invariant each, so a failure says which one died ---
        (_CAT_PROHIBITION in rules,
         "vault-audit-rules.md states the raw-`cat` prohibition (not a recommendation)"),
        (_NO_CAT_RETRY in rules,
         "vault-audit-rules.md forbids a raw `cat` retry after the exit-3 branch"),
        (_TRUNCATION_RATIONALE in rules,
         "vault-audit-rules.md documents the 2 KB truncation rationale"),
        (_EXIT3_BRANCH in rules,
         "vault-audit-rules.md documents the exit-3 (absent/unparseable) branch"),
        ('cat "$VAULT_ROOT/.vault-bridge/manifest.json"' not in audit_text,
         "audit/SKILL.md never `cat`s the manifest directly, anywhere in the body"),
        # wiki/SKILL.md is unchanged by #663 — its rationale still lives in its own body, so it
        # keeps the substring pins (no reference-doc split, nothing to pin whole).
        ("scripts/manifest-wiki-match.py" in wiki_text,
         "wiki/SKILL.md invokes manifest-wiki-match.py"),
        ("cat ~/vault/.vault-bridge/manifest.json" not in wiki_text,
         "wiki/SKILL.md no longer `cat`s the manifest directly"),
        ("2 KB" in wiki_text, "wiki/SKILL.md documents the 2 KB truncation rationale"),
        ("Exit 3" in wiki_text or "exit 3" in wiki_text,
         "wiki/SKILL.md documents the exit-3 (absent/unparseable/malformed) branch"),
    ]


# ---------------------------------------------------------------------------
# #663 mutation fixtures: built by `.replace()` off the REAL files, with the import-time guard
# below — a fixture whose target string has drifted silently becomes a copy of its base, and an
# expect-FAIL case on an unmodified copy would be testing nothing.
# ---------------------------------------------------------------------------

_CLEAN_AUDIT = _AUDIT_SKILL.read_text(encoding="utf-8")
_CLEAN_RULES = _AUDIT_RULES.read_text(encoding="utf-8")
_CLEAN_WIKI = _WIKI_SKILL.read_text(encoding="utf-8")

# --- the canonical section corrupted ---
# The prohibition reworded into a recommendation.
_RULES_CAT_ADVISORY = _CLEAN_RULES.replace(
    "**Never `cat` the manifest directly.**", "Prefer the filter script over a raw `cat`.")
# The truncation rationale — the whole reason the prohibition exists — deleted.
_RULES_NO_RATIONALE = _CLEAN_RULES.replace(
    "the harness truncates large\nBash output to a 2 KB preview, so a raw `cat` silently degrades to whichever entries survive the\ncut — indistinguishable from a legitimately small manifest.",
    "a raw `cat` is usually fine.")
# The exit-3 branch relabelled, so an absent manifest has no defined handling.
_RULES_NO_EXIT3 = _CLEAN_RULES.replace(
    "- **Exit 3** (manifest absent, unparseable, or missing a required field) →",
    "- **Any other exit** →")
# The no-retry clause inverted: the exact fallback that reintroduces the truncated read.
_RULES_CAT_RETRY_OK = _CLEAN_RULES.replace(
    "and **never re-attempt with a raw `cat` as a fallback**",
    "then retry with a raw `cat` if needed")
# PREMISE FLIP — "a truncated read is worse than no read" inverted, leaving the pinned
# prohibition sentence verbatim above it and false. No clause pin on that sentence sees this.
_RULES_TRUNCATION_HARMLESS = _CLEAN_RULES.replace(
    "A truncated read is worse than\n  no read: the header would print a confident wrong count instead of `없음`.",
    "A truncated read is close enough: print whatever count survived.")
# Exit 0 loosened from the two-field parse into "show whatever came back".
_RULES_EXIT0_LOOSENED = _CLEAN_RULES.replace(
    "→ parse stdout as `{file_count, generated_at}` and use it as `manifest_summary`.",
    "→ show stdout in the header as-is.")
# The self-declaration that tells the next editor this section is pinned, deleted.
_RULES_SELF_DECL_DELETED = _CLEAN_RULES.replace(
    " Its whole text — heading to the next heading, so nothing unpinned may be parked at the\nbottom — is pinned VERBATIM by `_READING_MANIFEST_SECTION` in\n`obsidian-vault-manager/scripts/test/test-manifest-reads.py`, and the headings on either side are\npinned by identity so an inserted sibling cannot park contradicting text just outside it.", "")

# --- ADJACENT-CLAUSE CORRUPTION: a new sibling heading immediately after the pinned section,
# parking contradicting text where every whole-section comparison stays byte-identical and every
# old substring check still passed. Only the neighbour-identity pin can see this.
_RULES_ADDENDUM_INSERTED = _CLEAN_RULES.replace(
    "\n## REPORT output example",
    "\n#### Addendum: small vaults\n\nWhen the vault looks small, a raw `cat` of the manifest is\nfine and the filter script may be skipped.\n\n## REPORT output example")

# --- the ALWAYS-LOADED body corrupted to contradict the canonical section it points at ---
_AUDIT_RAW_CAT = _CLEAN_AUDIT.replace(
    '   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/.vault-bridge/manifest.json"',
    '   cat "$VAULT_ROOT/.vault-bridge/manifest.json"')
# The body's exit-3 branch flipped into the fallback the canonical section forbids.
_AUDIT_EXIT3_RETRIES = _CLEAN_AUDIT.replace(
    "exit 3 → null.", "exit 3 → retry with a raw `cat`.")
# The binding locator decayed into a bare rationale citation: the contract still exists, nothing
# routes the skill to it as binding. A path-only check ("vault-audit-rules.md" in text) is blind
# to this — the path is cited half a dozen times elsewhere in the body.
_AUDIT_POINTER_DECAYED = _CLEAN_AUDIT.replace(
    "   **Apply `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → Reading the manifest as\n   written — that section is the binding contract** for why",
    "   For background, see `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → Reading the\n   manifest, which covers why")
# The caveat that stops the model acting from the two-line summary alone, deleted.
_AUDIT_LOCATOR_CAVEAT_DELETED = _CLEAN_AUDIT.replace(
    "; the line above is a locator, not a summary you may act from alone", "")
# ADJACENT-CLAUSE CORRUPTION, body side: a heading wedged between step 8 and step 9.
_AUDIT_HEADING_WEDGED = _CLEAN_AUDIT.replace(
    "\n9. Detect E9 vocabulary",
    "\n#### Manifest note\n\nSkipping the filter script is acceptable under time pressure.\n\n9. Detect E9 vocabulary")

# --- wiki/SKILL.md (unchanged by #663, still substring-pinned) ---
_WIKI_NO_RATIONALE = _CLEAN_WIKI.replace("2 KB", "small")

# --- a realistic reflow: every prose paragraph rewrapped onto one line, headings and fenced
# blocks left alone. Must still PASS — whitespace is not the contract.
_RULES_REFLOWED = "\n\n".join(
    block if block.startswith(("#", "```", "-", "|")) else " ".join(block.split())
    for block in _CLEAN_RULES.split("\n\n")
)

for _name, _fixture, _base in (
    ("_RULES_REFLOWED", _RULES_REFLOWED, _CLEAN_RULES),
    ("_RULES_CAT_ADVISORY", _RULES_CAT_ADVISORY, _CLEAN_RULES),
    ("_RULES_NO_RATIONALE", _RULES_NO_RATIONALE, _CLEAN_RULES),
    ("_RULES_NO_EXIT3", _RULES_NO_EXIT3, _CLEAN_RULES),
    ("_RULES_CAT_RETRY_OK", _RULES_CAT_RETRY_OK, _CLEAN_RULES),
    ("_RULES_TRUNCATION_HARMLESS", _RULES_TRUNCATION_HARMLESS, _CLEAN_RULES),
    ("_RULES_EXIT0_LOOSENED", _RULES_EXIT0_LOOSENED, _CLEAN_RULES),
    ("_RULES_SELF_DECL_DELETED", _RULES_SELF_DECL_DELETED, _CLEAN_RULES),
    ("_RULES_ADDENDUM_INSERTED", _RULES_ADDENDUM_INSERTED, _CLEAN_RULES),
    ("_AUDIT_RAW_CAT", _AUDIT_RAW_CAT, _CLEAN_AUDIT),
    ("_AUDIT_EXIT3_RETRIES", _AUDIT_EXIT3_RETRIES, _CLEAN_AUDIT),
    ("_AUDIT_POINTER_DECAYED", _AUDIT_POINTER_DECAYED, _CLEAN_AUDIT),
    ("_AUDIT_LOCATOR_CAVEAT_DELETED", _AUDIT_LOCATOR_CAVEAT_DELETED, _CLEAN_AUDIT),
    ("_AUDIT_HEADING_WEDGED", _AUDIT_HEADING_WEDGED, _CLEAN_AUDIT),
    ("_WIKI_NO_RATIONALE", _WIKI_NO_RATIONALE, _CLEAN_WIKI),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

# (audit, rules, wiki, expect_pass)
_PIN_CASES = [
    ("clean audit/SKILL.md + reference + wiki pass every guard",
     _CLEAN_AUDIT, _CLEAN_RULES, _CLEAN_WIKI, True),
    ("reflowed reference doc still passes (whitespace is not the contract)",
     _CLEAN_AUDIT, _RULES_REFLOWED, _CLEAN_WIKI, True),
    ("canonical raw-`cat` prohibition reworded into a recommendation -> FAIL",
     _CLEAN_AUDIT, _RULES_CAT_ADVISORY, _CLEAN_WIKI, False),
    ("canonical 2 KB truncation rationale deleted -> FAIL",
     _CLEAN_AUDIT, _RULES_NO_RATIONALE, _CLEAN_WIKI, False),
    ("canonical exit-3 branch relabelled away -> FAIL",
     _CLEAN_AUDIT, _RULES_NO_EXIT3, _CLEAN_WIKI, False),
    ("canonical no-retry clause inverted into a raw-`cat` fallback -> FAIL",
     _CLEAN_AUDIT, _RULES_CAT_RETRY_OK, _CLEAN_WIKI, False),
    ("'a truncated read is worse than no read' inverted -> FAIL "
     "(premise flip: the prohibition sentence stays verbatim and becomes false)",
     _CLEAN_AUDIT, _RULES_TRUNCATION_HARMLESS, _CLEAN_WIKI, False),
    ("canonical exit-0 two-field parse loosened -> FAIL",
     _CLEAN_AUDIT, _RULES_EXIT0_LOOSENED, _CLEAN_WIKI, False),
    ("canonical section's 'this is pinned' self-declaration deleted -> FAIL",
     _CLEAN_AUDIT, _RULES_SELF_DECL_DELETED, _CLEAN_WIKI, False),
    ("a new `#### Addendum` parks contradicting text right after the pinned section -> FAIL "
     "(every substring check and both section comparisons still pass; only adjacency sees it)",
     _CLEAN_AUDIT, _RULES_ADDENDUM_INSERTED, _CLEAN_WIKI, False),
    ("loaded body regresses to a raw `cat` -> FAIL",
     _AUDIT_RAW_CAT, _CLEAN_RULES, _CLEAN_WIKI, False),
    ("loaded body's exit-3 branch retries with a raw `cat` -> FAIL",
     _AUDIT_EXIT3_RETRIES, _CLEAN_RULES, _CLEAN_WIKI, False),
    ("loaded body's binding locator decayed into a citation -> FAIL",
     _AUDIT_POINTER_DECAYED, _CLEAN_RULES, _CLEAN_WIKI, False),
    ("loaded body drops the 'locator, not a summary you may act from alone' caveat -> FAIL",
     _AUDIT_LOCATOR_CAVEAT_DELETED, _CLEAN_RULES, _CLEAN_WIKI, False),
    ("a heading wedged between Step 8 and Step 9 parks contradicting text -> FAIL",
     _AUDIT_HEADING_WEDGED, _CLEAN_RULES, _CLEAN_WIKI, False),
    ("wiki/SKILL.md loses its own 2 KB rationale -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _WIKI_NO_RATIONALE, False),
]


def _self_test() -> int:
    cases = []

    for desc, audit, rules, wiki, expect_pass in _PIN_CASES:
        results = static_checks(audit, rules, wiki)
        got = all(ok for ok, _ in results)
        detail = ""
        if expect_pass and not got:
            detail = f" — unexpectedly failed: {[d for ok, d in results if not ok]}"
        cases.append((f"{desc}{detail}", got == expect_pass))

    # The two adjacent-clause cases claim the whole-section comparisons stay byte-identical and
    # only the neighbour-identity pin catches them. Assert that, or the claim rots into a
    # comment that says one thing while the test passes for a different reason.
    for label, mutated, pattern, pinned in (
        ("reference `#### Addendum`", _RULES_ADDENDUM_INSERTED,
         _READING_MANIFEST_SECTION_RE, _READING_MANIFEST_SECTION),
        ("body heading wedged after Step 8", _AUDIT_HEADING_WEDGED,
         _SKILL_STEP8_RE, _SKILL_STEP8),
    ):
        cases.append((
            f"adjacency-only: {label} leaves the pinned slice itself unchanged",
            _section(pattern, mutated) == pinned,
        ))

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
