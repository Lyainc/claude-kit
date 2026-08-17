#!/usr/bin/env python3
"""audit/SKILL.md Phase 4 Step 1 + reference/vault-audit-rules.md Auto-fix eligibility
provenance-pin regression (#673, following #663's manifest-read pin architecture in
test-manifest-reads.py).

f8087d1 folded two pieces of new text into these files with no self-test pin at all
(#625 nit2's sibling — this file covers #591 and the provenance rationale, `#625` nit2's
$VAULT_ROOT snippet is pinned separately in test-audit-vault-root-wiring.py):

- audit/SKILL.md Phase 4 Step 1's AskUserQuestion template — the `provenance 누락` example
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
_AUDIT_RULES = _HERE.parent.parent / "reference" / "vault-audit-rules.md"

_HEADING_ANCHOR_RE = re.compile(r"^#{1,6} ")
_STEP_OR_HEADING_ANCHOR_RE = re.compile(r"^(?:#{1,6} |\d+\. )")

_AUTOFIX_SECTION_RE = re.compile(
    r"^## Auto-fix eligibility\b.*?(?=^#{1,6} |\Z)", re.MULTILINE | re.DOTALL)
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
    "(recompiling/re-verifying a stale wiki page, or reconciling a confirmed E12b "
    "contradiction, is a semantic decision — display-only warning).\n"
)
_AUTOFIX_NEIGHBOURS = (
    "### E12b — cross-page contradiction (`--deep`, skill-only, #336)",
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
_PHASE4_STEP1_NEIGHBOURS = (
    "## Phase 4 — OPTIONAL-FIX",
    "2. If \"건너뜀\": exit without mutation. Mark scanned files clean in audit sidecar.",
)


def static_checks(audit_text: str, rules_text: str) -> list:
    """Static pins for the provenance-autofix contract, as (ok, description) pairs.

    Split out of main() so --self-test can run the identical checks against mutated copies
    of the real files.
    """
    return [
        (_section(_AUTOFIX_SECTION_RE, rules_text) == _AUTOFIX_SECTION,
         "vault-audit-rules.md § Auto-fix eligibility matches VERBATIM (#673)"),
        (_section(_PHASE4_STEP1_RE, audit_text) == _PHASE4_STEP1,
         "audit/SKILL.md Phase 4 Step 1 (AskUserQuestion template) matches VERBATIM (#673)"),
        (_neighbour_anchors(_AUTOFIX_SECTION_RE, rules_text, _HEADING_ANCHOR_RE) == _AUTOFIX_NEIGHBOURS,
         "vault-audit-rules.md § Auto-fix eligibility still sits between its two known anchors "
         "(an inserted sibling would park text outside the pin)"),
        (_neighbour_anchors(_PHASE4_STEP1_RE, audit_text, _STEP_OR_HEADING_ANCHOR_RE) == _PHASE4_STEP1_NEIGHBOURS,
         "audit/SKILL.md Phase 4 Step 1 still sits between its two known anchors "
         "(an inserted sibling would park text outside the pin)"),
    ]


# ---------------------------------------------------------------------------
# #673 mutation fixtures: built by `.replace()` off the REAL files, with the import-time
# no-op guard below — same pattern as test-manifest-reads.py.
# ---------------------------------------------------------------------------

_CLEAN_AUDIT = _AUDIT_SKILL.read_text(encoding="utf-8")
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

_PIN_CASES = [
    ("clean audit/SKILL.md + reference pass every guard",
     _CLEAN_AUDIT, _CLEAN_RULES, True),
    ("reflowed reference doc still passes (whitespace is not the contract)",
     _CLEAN_AUDIT, _RULES_REFLOWED, True),
    ("'provenance NOT auto-fillable' reworded into fillable -> FAIL",
     _CLEAN_AUDIT, _RULES_PROVENANCE_FILLABLE, False),
    ("the per-file surface-and-ask instruction dropped -> FAIL",
     _CLEAN_AUDIT, _RULES_PROVENANCE_SURFACE_DROPPED, False),
    ("a new `#### Addendum` parks a provenance shortcut right after the pinned section -> FAIL "
     "(the whole-section comparison stays byte-identical; only adjacency sees it)",
     _CLEAN_AUDIT, _RULES_ADDENDUM_INSERTED, False),
    ("#591 regression: the provenance example line dropped from the AskUserQuestion template -> FAIL",
     _AUDIT_PROVENANCE_EXAMPLE_DROPPED, _CLEAN_RULES, False),
    ("a heading wedged between Phase 4 Step 1 and Step 2 -> FAIL",
     _AUDIT_HEADING_WEDGED, _CLEAN_RULES, False),
]


def _self_test() -> int:
    cases = []

    for desc, audit, rules, expect_pass in _PIN_CASES:
        results = static_checks(audit, rules)
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
        ("body heading wedged after Step 1", _AUDIT_HEADING_WEDGED,
         _PHASE4_STEP1_RE, _PHASE4_STEP1),
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
        _AUDIT_SKILL.read_text(encoding="utf-8"),
        _AUDIT_RULES.read_text(encoding="utf-8"),
    ):
        if ok:
            print(f"  ok   {desc}")
        else:
            print(f"  FAIL {desc}", file=sys.stderr)
            errors.append(desc)

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print(f"\nOK: all provenance-autofix checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
