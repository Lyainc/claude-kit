#!/usr/bin/env python3
"""audit/fix.md Phase 4 Step 1 + audit/SKILL.md Phase 4 fail-closed gate +
reference/vault-audit-rules.md Auto-fix eligibility provenance-pin regression (#673, following
#663's manifest-read pin architecture in test-manifest-reads.py).

#750: the Phase 4 procedure (including the Step 1 AskUserQuestion template) moved out of
audit/SKILL.md into the sibling audit/fix.md so SKILL.md fits Codex's 8,000-byte invoked-skill
limit. SKILL.md keeps a short gate that is fail-closed: it must stay binding even if fix.md is
never read (Read fix.md before ANY write; STOP and apply no fix if it is unreadable; never write a
vault file without the Step 1 approval; E2 only, provenance gate; E9/E13 display-only). Both
halves are pinned here: the template whole-section verbatim in fix.md (same strictness as before),
and the SKILL.md gate whole-section verbatim plus one named clause pin per invariant, so deleting
the fail-closed gate fails loud instead of leaving a template nobody is told to read.

f8087d1 folded two pieces of new text into these files with no self-test pin at all
(#625 nit2's sibling — this file covers #591 and the provenance rationale, `#625` nit2's
$VAULT_ROOT snippet is pinned separately in test-audit-vault-root-wiring.py):

- audit/fix.md Phase 4 Step 1's AskUserQuestion template (was audit/SKILL.md) — the `provenance 누락` example
  line added by #591.
- reference/vault-audit-rules.md's "Auto-fix eligibility" table — the `provenance` is-not-
  auto-fillable rationale sentence.

Both encode the SAME invariant (provenance has no safe deterministic inference, unlike
`tags`, so it must be surfaced to the user rather than guessed) from two directions — the
binding rule in the reference doc, and the always-loaded template that must not silently
drift from it. A loose `"provenance" in text` substring check stays green even if that
sentence is reworded into "infer it like tags"; only a whole-section verbatim comparison
catches a reword, and only a neighbour-identity pin catches a sibling heading/step wedged
just outside the pinned slice.

Run: python3 obsidian-vault-manager/scripts/test/test-audit-provenance-autofix-pin.py
  -> "OK: all N provenance-autofix checks passed" (exit 0) / "FAILED: ..." (exit 1).
Self-test (in-memory fixtures, no vault, no live files):
  python3 obsidian-vault-manager/scripts/test/test-audit-provenance-autofix-pin.py --self-test
"""
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_SKILL = _HERE.parent.parent / "skills" / "audit" / "SKILL.md"
_AUDIT_FIX = _HERE.parent.parent / "skills" / "audit" / "fix.md"
_AUDIT_RULES = _HERE.parent.parent / "reference" / "vault-audit-rules.md"

_HEADING_ANCHOR_RE = re.compile(r"^#{1,6} ")
_STEP_OR_HEADING_ANCHOR_RE = re.compile(r"^(?:#{1,6} |\d+\. )")

_AUTOFIX_SECTION_RE = re.compile(
    r"^## Auto-fix eligibility\b.*?(?=^#{1,6} |\Z)", re.MULTILINE | re.DOTALL)
_SKILL_PHASE4_RE = re.compile(
    r"^## Phase 4 — OPTIONAL-FIX\b.*?(?=^#{1,6} |\Z)", re.MULTILINE | re.DOTALL)
_PHASE4_STEP1_RE = re.compile(
    r"^1\. If `auto_fix_eligible`.*?(?=^\d+\. |^#{1,6} |\Z)", re.MULTILINE | re.DOTALL)


def _normalise(s: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(s.split())


def _section(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    return _normalise(match.group(0)) if match else ""


def _neighbour_anchors(pattern: re.Pattern, text: str, anchor: re.Pattern) -> tuple:
    match = pattern.search(text)
    if not match:
        return ("", "")
    before = [ln for ln in text[:match.start()].splitlines() if anchor.match(ln)]
    after = [ln for ln in text[match.end():].splitlines() if anchor.match(ln)]
    return (before[-1] if before else "", after[0] if after else "")


# ---------------------------------------------------------------------------
# Canonical contract text (#673)
# ---------------------------------------------------------------------------

_AUTOFIX_SECTION = _normalise(
    "## Auto-fix eligibility\n\n"
    "Only the following are mutated by Phase 4 OPTIONAL-FIX (frontmatter-only edits):\n\n"
    "| Type | Auto-fix action |\n"
    "|------|-----------------|\n"
    "| `missing_required_fields` (E2) | Add missing `tags`, `type`, `created` fields. "
    "For `tags:`, propose a deterministic 3-tier inference (type → filename slug → first "
    "segment under `notes/`; see the E2 **Tag inference** section above) — never an empty "
    "`tags: []` — and preview it in the confirmation gate before applying. `provenance` "
    "(#477 item 4) is required but NOT auto-fillable — unlike `tags`, there is no safe "
    "deterministic inference for \"where did this come from.\" When it's among the missing "
    "fields, surface it in the confirmation gate per-file and ask the user for the actual "
    "origin instead of writing a placeholder. |\n\n"
    "Never auto-fixed: E1 (body structure unknown), E3 (rename affects inbound links — "
    "suggestion only), E5 (content value judgment — connection candidates are suggestions "
    "only), E6 (stagnation requires semantic decision: process / archive), E9 (canonical-form "
    "choice + multi-file rewrite is the user's decision — display-only), E10/E11 (moving a "
    "file affects inbound links — display-only warning, user decides the destination), E12 "
    "(recompiling/re-verifying a stale wiki page, reconciling a confirmed E12b "
    "contradiction, or merging a confirmed E12c near-duplicate pair, is a semantic decision "
    "— display-only warning), E13 (a custom property's value cannot be inferred — "
    "display-only).\n"
)
_AUTOFIX_NEIGHBOURS = (
    "## E13 — `custom_schema_violation` [Warning]",
    "## Manifest Summary (display-only)",
)

_PHASE4_STEP1 = _normalise(
    "1. If `auto_fix_eligible` count > 0, first compute the tag proposals for every\n"
    "   E2 finding whose missing fields include `tags` in ONE batched call (pass all\n"
    "   such relpaths as arguments — see **Tag inference** above):\n"
    "   ```bash\n"
    "   bash \"${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh\" infer-tags <relpath1> <relpath2> ...\n"
    "   # >~200 paths (ARG_MAX headroom)? Pipe one per line into `infer-tags -` instead.\n"
    "   ```\n"
    "   Match each element's `path` back to its finding. A per-file failure surfaces as\n"
    "   `error` + `inferred_tags: []` on that element and the batch still succeeds (exit\n"
    "   is non-zero only when EVERY path failed). Then ask (single AskUserQuestion),\n"
    "   showing each inferred proposal on its own line as `추론된 태그: [X, Y, Z]`:\n"
    "   ```\n"
    "   AskUserQuestion:\n"
    "     question: \"다음 F건의 frontmatter 이슈를 자동으로 수정할까요?\"\n"
    "     context: |\n"
    "       수정 대상:\n"
    "       • missing_required_fields: X건 (tags/type/created 추가)\n\n"
    "       추론된 태그 (제안):\n"
    "       • notes/llm/decision-2026-04-12-context-window.md → [decision, context, window, llm]\n"
    "       • sources/capture-2026-05-01-obsidian-api.md → [capture, obsidian, api]\n\n"
    "       provenance 누락 (자동 추론 불가, 개별 확인 필요):\n"
    "       • sources/capture-2026-05-03-untitled-clip.md → 출처를 알려주시면 채워 넣을게요\n\n"
    "       태그는 type·파일명·폴더에서 추론한 제안입니다. frontmatter만 수정하며\n"
    "       파일 이름 · 내용 · 위치는 변경하지 않습니다.\n"
    "     options:\n"
    "       - \"수정 실행\"\n"
    "       - \"건너뜀\"\n"
    "   ```\n"
)
# SKILL.md's always-loaded Phase 4 gate (#750). Whole section pinned verbatim, plus its two
# neighbouring headings by identity, plus one named clause per invariant below.
_SKILL_PHASE4 = _normalise(
    "## Phase 4 — OPTIONAL-FIX\n\n"
    "OFF by default: only after REPORT, on the user's explicit opt-in, never under `--dry-run`. "
    "**On entering Phase 4, before asking anything or any write, Read\n`fix.md` in full and follow it**; if unreadable, STOP, apply no fix "
    "and tell the user in Korean. Never use Edit on, or\notherwise write, a vault file without the "
    "user's approval through the AskUserQuestion gate in `fix.md` Step 1\n(\"수정 실행\"). Only E2 "
    "is auto-fixable (frontmatter-only), and it requires the provenance gate: ask for the real\n"
    "origin, never a placeholder. E9, E13 and every other type are display-only, never mutated.\n\n"
)
_SKILL_PHASE4_NEIGHBOURS = ("## Phase 3 — REPORT", "## Flags")
_SKILL_GATE_CLAUSES = {
    "read fix.md in full on entering Phase 4, before asking or writing":
        "**On entering Phase 4, before asking anything or any write, Read `fix.md` in full and follow it**",
    "the no-fix path never marks clean under --dry-run":
        "otherwise, unless `--dry-run`, Read `fix.md` and run only its Steps 4–5 (mark-clean, metrics)",
    "stop with no fix when fix.md is unreadable":
        "if unreadable, STOP, apply no fix",
    "no vault write without the Step 1 AskUserQuestion approval":
        "Never use Edit on, or otherwise write, a vault file without the user's approval "
        "through the AskUserQuestion gate in `fix.md` Step 1",
    "E2 auto-fix requires the provenance gate, never a placeholder":
        "it requires the provenance gate: ask for the real origin, never a placeholder",
    "E9/E13 (and every other type) are display-only, never mutated":
        "E9, E13 and every other type are display-only, never mutated",
}

_PHASE4_STEP1_NEIGHBOURS = (
    "## Phase 4 — OPTIONAL-FIX",
    "2. If \"건너뜀\": exit without mutation. Mark scanned files clean in audit sidecar.",
)


def static_checks(fix_text: str, rules_text: str, skill_text: str) -> list:
    """Static pins for the provenance-autofix contract, as (ok, description) pairs.

    Split out of main() so --self-test can run the identical checks against mutated copies
    of the real files.
    """
    return [
        (_section(_AUTOFIX_SECTION_RE, rules_text) == _AUTOFIX_SECTION,
         "vault-audit-rules.md § Auto-fix eligibility matches VERBATIM (#673)"),
        (_section(_PHASE4_STEP1_RE, fix_text) == _PHASE4_STEP1,
         "audit/fix.md Phase 4 Step 1 (AskUserQuestion template) matches VERBATIM (#673, #750)"),
        (_neighbour_anchors(_AUTOFIX_SECTION_RE, rules_text, _HEADING_ANCHOR_RE) == _AUTOFIX_NEIGHBOURS,
         "vault-audit-rules.md § Auto-fix eligibility still sits between its two known anchors "
         "(an inserted sibling would park text outside the pin)"),
        (_neighbour_anchors(_PHASE4_STEP1_RE, fix_text, _STEP_OR_HEADING_ANCHOR_RE) == _PHASE4_STEP1_NEIGHBOURS,
         "audit/fix.md Phase 4 Step 1 still sits between its two known anchors "
         "(an inserted sibling would park text outside the pin)"),
        (_section(_SKILL_PHASE4_RE, skill_text) == _SKILL_PHASE4,
         "audit/SKILL.md Phase 4 fail-closed gate matches VERBATIM (#750)"),
        (_neighbour_anchors(_SKILL_PHASE4_RE, skill_text, _HEADING_ANCHOR_RE) == _SKILL_PHASE4_NEIGHBOURS,
         "audit/SKILL.md Phase 4 gate still sits between its two known headings "
         "(an inserted sibling would park text outside the pin)"),
    ] + [
        (_normalise(clause) in _normalise(skill_text),
         f"audit/SKILL.md gate clause: {name}")
        for name, clause in _SKILL_GATE_CLAUSES.items()
    ]


# ---------------------------------------------------------------------------
# #673 mutation fixtures: built by `.replace()` off the REAL files, with the import-time
# no-op guard below — same pattern as test-manifest-reads.py.
# ---------------------------------------------------------------------------

_CLEAN_AUDIT = _AUDIT_FIX.read_text(encoding="utf-8")   # the Phase 4 template's owner (fix.md)
_CLEAN_SKILL = _AUDIT_SKILL.read_text(encoding="utf-8")
_CLEAN_RULES = _AUDIT_RULES.read_text(encoding="utf-8")

# The "not auto-fillable" claim reworded so provenance reads as inferrable, same class as
# #663's raw-`cat` prohibition reworded into a recommendation.
_RULES_PROVENANCE_FILLABLE = _CLEAN_RULES.replace(
    "`provenance` (#477 item 4) is required but NOT auto-fillable — unlike `tags`, there is "
    "no safe deterministic inference for \"where did this come from.\"",
    "`provenance` (#477 item 4) can be inferred the same way as `tags`.")

# The instruction to surface provenance per-file and ask for the real origin, deleted —
# the placeholder-fabrication risk #591 exists to prevent.
_RULES_PROVENANCE_SURFACE_DROPPED = _CLEAN_RULES.replace(
    " When it's among the missing fields, surface it in the confirmation gate per-file and "
    "ask the user for the actual origin instead of writing a placeholder.",
    "")

# ADJACENT-CLAUSE CORRUPTION: a new sibling heading right after the pinned section, parking
# contradicting text where the whole-section comparison stays byte-identical.
_RULES_ADDENDUM_INSERTED = _CLEAN_RULES.replace(
    "\n## Manifest Summary (display-only)",
    "\n#### Addendum: provenance shortcuts\n\nIf the file came from an obvious source, infer "
    "provenance automatically without asking.\n\n## Manifest Summary (display-only)")

# The #591 regression itself: the provenance example line dropped back out of the
# AskUserQuestion template.
_AUDIT_PROVENANCE_EXAMPLE_DROPPED = _CLEAN_AUDIT.replace(
    "\n\n       provenance 누락 (자동 추론 불가, 개별 확인 필요):\n"
    "       • sources/capture-2026-05-03-untitled-clip.md → 출처를 알려주시면 채워 넣을게요",
    "")

# ADJACENT-CLAUSE CORRUPTION, body side: a heading wedged between Step 1 and Step 2.
_AUDIT_HEADING_WEDGED = _CLEAN_AUDIT.replace(
    "\n\n2. If \"건너뜀\": exit without mutation.",
    "\n\n#### Fast-path note\n\nWhen every finding is missing only `tags`, skip the "
    "confirmation gate and apply directly.\n"
    "\n2. If \"건너뜀\": exit without mutation.")

# #750 fail-closed gate mutations on SKILL.md (each deletes or inverts one invariant).
_SKILL_GATE_READ_DROPPED = _CLEAN_SKILL.replace(
    "**On entering Phase 4, before asking anything or any write, Read\n`fix.md` in full and follow it**; ", "")
_SKILL_DRYRUN_NOFIX_DROPPED = _CLEAN_SKILL.replace("otherwise, unless `--dry-run`, Read", "otherwise Read")
_SKILL_GATE_UNREADABLE_DROPPED = _CLEAN_SKILL.replace(
    "if unreadable, STOP, apply no fix and tell the user in Korean. ", "")
_SKILL_GATE_APPROVAL_DROPPED = _CLEAN_SKILL.replace(
    "Never use Edit on, or\notherwise write, a vault file without the user's approval through the "
    "AskUserQuestion gate in `fix.md` Step 1\n(\"수정 실행\"). ", "")
_SKILL_GATE_PROVENANCE_DROPPED = _CLEAN_SKILL.replace(
    ", and it requires the provenance gate: ask for the real\norigin, never a placeholder", "")
_SKILL_GATE_E13_MUTABLE = _CLEAN_SKILL.replace(
    "E9, E13 and every other type are display-only, never mutated.",
    "E9 and E13 may be auto-fixed when the value is obvious.")
_SKILL_GATE_WHOLE_SECTION_DELETED = _CLEAN_SKILL.replace(
    _CLEAN_SKILL[_CLEAN_SKILL.index("## Phase 4 — OPTIONAL-FIX"):_CLEAN_SKILL.index("## Flags")],
    "## Phase 4 — OPTIONAL-FIX\n\nSee fix.md.\n\n")
_SKILL_HEADING_WEDGED = _CLEAN_SKILL.replace(
    "\n## Flags", "\n#### Fast path\n\nWhen only `tags` are missing, apply directly without asking.\n\n## Flags")

# These SKILL.md fixtures are checked for no-ops inside _self_test(), NOT at import: when the live
# gate sentence is deleted, the .replace() legitimately no-ops, and an import-time assert would
# crash before main() could report which gate clause went missing.
_SKILL_GATE_FIXTURES = (
    ("_SKILL_GATE_READ_DROPPED", _SKILL_GATE_READ_DROPPED, _CLEAN_SKILL),
    ("_SKILL_DRYRUN_NOFIX_DROPPED", _SKILL_DRYRUN_NOFIX_DROPPED, _CLEAN_SKILL),
    ("_SKILL_GATE_UNREADABLE_DROPPED", _SKILL_GATE_UNREADABLE_DROPPED, _CLEAN_SKILL),
    ("_SKILL_GATE_APPROVAL_DROPPED", _SKILL_GATE_APPROVAL_DROPPED, _CLEAN_SKILL),
    ("_SKILL_GATE_PROVENANCE_DROPPED", _SKILL_GATE_PROVENANCE_DROPPED, _CLEAN_SKILL),
    ("_SKILL_GATE_E13_MUTABLE", _SKILL_GATE_E13_MUTABLE, _CLEAN_SKILL),
    ("_SKILL_GATE_WHOLE_SECTION_DELETED", _SKILL_GATE_WHOLE_SECTION_DELETED, _CLEAN_SKILL),
    ("_SKILL_HEADING_WEDGED", _SKILL_HEADING_WEDGED, _CLEAN_SKILL),
)

for _name, _fixture, _base in (
    ("_RULES_PROVENANCE_FILLABLE", _RULES_PROVENANCE_FILLABLE, _CLEAN_RULES),
    ("_RULES_PROVENANCE_SURFACE_DROPPED", _RULES_PROVENANCE_SURFACE_DROPPED, _CLEAN_RULES),
    ("_RULES_ADDENDUM_INSERTED", _RULES_ADDENDUM_INSERTED, _CLEAN_RULES),
    ("_AUDIT_PROVENANCE_EXAMPLE_DROPPED", _AUDIT_PROVENANCE_EXAMPLE_DROPPED, _CLEAN_AUDIT),
    ("_AUDIT_HEADING_WEDGED", _AUDIT_HEADING_WEDGED, _CLEAN_AUDIT),
):
    assert _fixture != _base, f"{_name} is identical to its base — its .replace() no-opped"

# A realistic reflow of the reference doc: every prose paragraph rewrapped onto one line,
# headings/fences/lists/tables left alone. Must still PASS — whitespace is not the contract.
_RULES_REFLOWED = "\n\n".join(
    block if block.startswith(("#", "```", "-", "|")) else " ".join(block.split())
    for block in _CLEAN_RULES.split("\n\n")
)

# (fix.md text, rules text, SKILL.md text, expect_pass)
_PIN_CASES = [
    ("clean audit/fix.md + SKILL.md gate + reference pass every guard",
     _CLEAN_AUDIT, _CLEAN_RULES, _CLEAN_SKILL, True),
    ("reflowed reference doc still passes (whitespace is not the contract)",
     _CLEAN_AUDIT, _RULES_REFLOWED, _CLEAN_SKILL, True),
    ("'provenance NOT auto-fillable' reworded into fillable -> FAIL",
     _CLEAN_AUDIT, _RULES_PROVENANCE_FILLABLE, _CLEAN_SKILL, False),
    ("the per-file surface-and-ask instruction dropped -> FAIL",
     _CLEAN_AUDIT, _RULES_PROVENANCE_SURFACE_DROPPED, _CLEAN_SKILL, False),
    ("a new `#### Addendum` parks a provenance shortcut right after the pinned section -> FAIL "
     "(the whole-section comparison stays byte-identical; only adjacency sees it)",
     _CLEAN_AUDIT, _RULES_ADDENDUM_INSERTED, _CLEAN_SKILL, False),
    ("#591 regression: the provenance example line dropped from the AskUserQuestion template -> FAIL",
     _AUDIT_PROVENANCE_EXAMPLE_DROPPED, _CLEAN_RULES, _CLEAN_SKILL, False),
    ("a heading wedged between Phase 4 Step 1 and Step 2 in fix.md -> FAIL",
     _AUDIT_HEADING_WEDGED, _CLEAN_RULES, _CLEAN_SKILL, False),
    ("#750: SKILL.md gate's 'Read fix.md in full before ANY write' removed -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_GATE_READ_DROPPED, False),
    ("#750: the no-fix path's `--dry-run` exception removed (dry-run would mark clean) -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_DRYRUN_NOFIX_DROPPED, False),
    ("#750: SKILL.md gate's 'STOP and apply no fix if fix.md is unreadable' removed -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_GATE_UNREADABLE_DROPPED, False),
    ("#750: SKILL.md gate's 'no vault write without the Step 1 approval' removed -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_GATE_APPROVAL_DROPPED, False),
    ("#750: SKILL.md gate's provenance requirement removed -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_GATE_PROVENANCE_DROPPED, False),
    ("#750: SKILL.md gate lets E9/E13 be auto-fixed -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_GATE_E13_MUTABLE, False),
    ("#750: SKILL.md Phase 4 gate replaced by a bare 'See fix.md.' -> FAIL",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_GATE_WHOLE_SECTION_DELETED, False),
    ("#750: a `#### Fast path` heading wedged after the SKILL.md gate -> FAIL "
     "(only adjacency sees it)",
     _CLEAN_AUDIT, _CLEAN_RULES, _SKILL_HEADING_WEDGED, False),
]


def _self_test() -> int:
    cases = []

    for name, fixture, base in _SKILL_GATE_FIXTURES:
        assert fixture != base, f"{name} is identical to its base — its .replace() no-opped"

    for desc, fix, rules, skill, expect_pass in _PIN_CASES:
        results = static_checks(fix, rules, skill)
        got = all(ok for ok, _ in results)
        detail = ""
        if expect_pass and not got:
            detail = f" — unexpectedly failed: {[d for ok, d in results if not ok]}"
        cases.append((f"{desc}{detail}", got == expect_pass))

    # The two adjacent-clause cases claim the whole-section comparisons stay byte-identical
    # and only the neighbour-identity pin catches them. Assert that, or the claim rots into a
    # comment that says one thing while the test passes for a different reason.
    for label, mutated, pattern, pinned in (
        ("reference `#### Addendum`", _RULES_ADDENDUM_INSERTED,
         _AUTOFIX_SECTION_RE, _AUTOFIX_SECTION),
        ("fix.md heading wedged after Step 1", _AUDIT_HEADING_WEDGED,
         _PHASE4_STEP1_RE, _PHASE4_STEP1),
        ("SKILL.md heading wedged after the Phase 4 gate", _SKILL_HEADING_WEDGED,
         _SKILL_PHASE4_RE, _SKILL_PHASE4),
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


def main() -> int:
    errors = []
    for ok, desc in static_checks(
        _AUDIT_FIX.read_text(encoding="utf-8"),
        _AUDIT_RULES.read_text(encoding="utf-8"),
        _AUDIT_SKILL.read_text(encoding="utf-8"),
    ):
        if ok:
            print(f"  ok   {desc}")
        else:
            print(f"  FAIL {desc}", file=sys.stderr)
            errors.append(desc)

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print("\nOK: all provenance-autofix checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
