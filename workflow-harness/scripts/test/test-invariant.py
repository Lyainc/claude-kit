#!/usr/bin/env python3
"""Regression tests for invariant_guard.py — D5 constitutional invariant enforcement (#183 S2).

One negative case per constitutional invariant the harness enforces (the native-
ungoverned gap, `omc-to-native-substrate.md` §4.2): a violating input must be caught,
and a clean input must pass. Single source of truth for the rules: boundary §5.

    INV-4 (CON-4) goal-doc schema      — validate_goal_doc()
    INV-1 (CON-1) new-file-only        — check_new_file_only()
    INV-2/3 (CON-3) isolated critique  — check_isolated_critique()
    INV-5 (CON-5) one-way dependency   — check_one_way_dependency()
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # scripts/test
_SCRIPTS = _HERE.parent                            # scripts
sys.path.insert(0, str(_SCRIPTS))

from invariant_guard import (  # noqa: E402
    check_isolated_critique,
    check_new_file_only,
    check_one_way_dependency,
    parse_goal_doc,
    validate_goal_doc,
)

_VALID = """---
goal_id: G99
title: Sample feature goal
issues: [200, 201]
wave: 3
depends_on: [G1]
recommended_model: opus
status: ready
work_type: feature-full
created: 2026-06-08
---

## 배경 / 목적
why.

## 완료 조건 (Definition of Done)
- [ ] thing

## 쟁점과 트레이드오프
| a | b |

## 슬라이스 순서
1. **spec** → 바인딩: spec-first | 대상 파일: x | 산출: y | 검증: z
2. **impl** → 바인딩: executor|native(#133) | 대상 파일: x | 산출: y | 검증: z

## E2E 자가검증
```bash
echo ok
```
"""


# ── INV-4 (CON-4): goal-doc schema ───────────────────────────────────────────

def test_inv4_valid_passes() -> None:
    assert validate_goal_doc(_VALID) == [], "a conformant goal-doc must pass clean"
    print("PASS test_inv4_valid_passes")


def test_inv4_missing_required_field() -> None:
    bad = _VALID.replace("work_type: feature-full\n", "")
    v = validate_goal_doc(bad)
    assert any("work_type" in x for x in v), f"missing work_type not caught: {v}"
    print("PASS test_inv4_missing_required_field")


def test_inv4_empty_issues_rejected() -> None:
    # issues: [] is present-but-empty → still "missing": a goal must close ≥1 issue (#190 N1)
    bad = _VALID.replace("issues: [200, 201]", "issues: []")
    v = validate_goal_doc(bad)
    assert any("at least one GitHub issue" in x for x in v), f"empty issues not rejected: {v}"
    print("PASS test_inv4_empty_issues_rejected")


def test_inv4_empty_depends_on_allowed() -> None:
    # depends_on: [] is legitimate (foundation goals like G1 have no predecessors) — the
    # empty-issues rule must NOT generalize into a blanket empty-list-is-missing rule (#190 N1)
    doc = _VALID.replace("depends_on: [G1]", "depends_on: []")
    assert validate_goal_doc(doc) == [], "empty depends_on wrongly rejected"
    print("PASS test_inv4_empty_depends_on_allowed")


def test_inv4_bad_model_enum() -> None:
    bad = _VALID.replace("recommended_model: opus", "recommended_model: gpt4")
    v = validate_goal_doc(bad)
    assert any("recommended_model must be one of" in x for x in v), f"bad model enum not caught: {v}"
    print("PASS test_inv4_bad_model_enum")


def test_inv4_bad_status_enum() -> None:
    bad = _VALID.replace("status: ready", "status: in-progress")
    v = validate_goal_doc(bad)
    assert any("status must be one of" in x for x in v), f"bad status enum not caught: {v}"
    print("PASS test_inv4_bad_status_enum")


def test_inv4_bug_light_worktype_rejected() -> None:
    # bug-light is signalled by goal-doc ABSENCE, never as a work_type value (§4.4)
    bad = _VALID.replace("work_type: feature-full", "work_type: bug-light")
    v = validate_goal_doc(bad)
    assert any("work_type must be one of" in x for x in v), f"bug-light value not rejected: {v}"
    print("PASS test_inv4_bug_light_worktype_rejected")


def test_inv4_depends_on_namespace() -> None:
    # depends_on is the goal_id space (G\d+), not GitHub issue numbers (§1.4)
    bad = _VALID.replace("depends_on: [G1]", "depends_on: [183]")
    v = validate_goal_doc(bad)
    assert any("not a goal_id" in x for x in v), f"depends_on namespace violation not caught: {v}"
    print("PASS test_inv4_depends_on_namespace")


def test_inv4_issues_namespace() -> None:
    # issues is the GitHub-number space; a goal_id there is a namespace violation (§1.4)
    bad = _VALID.replace("issues: [200, 201]", "issues: [G1]")
    v = validate_goal_doc(bad)
    assert any("not a GitHub issue number" in x for x in v), f"issues namespace violation not caught: {v}"
    print("PASS test_inv4_issues_namespace")


def test_inv4_missing_section() -> None:
    bad = _VALID.replace("## E2E 자가검증\n", "## Appendix\n")
    v = validate_goal_doc(bad)
    assert any("e2e" in x.lower() for x in v), f"missing E2E section not caught: {v}"
    print("PASS test_inv4_missing_section")


def test_inv4_section_out_of_order() -> None:
    # move DoD after the slice section → out-of-order, not merely missing
    reordered = """---
goal_id: G99
title: t
issues: [1]
wave: 1
depends_on: [G1]
recommended_model: haiku
status: ready
work_type: doc-only
created: 2026-06-08
---

## 배경 / 목적
b

## 쟁점과 트레이드오프
t

## 슬라이스 순서
1. **a** → 바인딩: doc-concretize | 대상 파일: x | 산출: y | 검증: z

## 완료 조건 (Definition of Done)
- [ ] late

## E2E 자가검증
```bash
echo ok
```
"""
    v = validate_goal_doc(reordered)
    assert any("out of order" in x for x in v), f"out-of-order DoD not caught: {v}"
    print("PASS test_inv4_section_out_of_order")


def test_inv4_no_binding_structure() -> None:
    # slice section present but no slice line carries a binding marker
    bad = _VALID.replace(
        "1. **spec** → 바인딩: spec-first | 대상 파일: x | 산출: y | 검증: z\n"
        "2. **impl** → 바인딩: executor|native(#133) | 대상 파일: x | 산출: y | 검증: z\n",
        "Just prose, no slice lines here.\n",
    )
    v = validate_goal_doc(bad)
    assert any("no slice with a binding expression" in x for x in v), f"missing binding structure not caught: {v}"
    print("PASS test_inv4_no_binding_structure")


def test_inv4_wave_value_not_checked() -> None:
    # wave value space is NOT validated (§1.5) — a label like 독립 must still pass
    doc = _VALID.replace("wave: 3", "wave: 독립·게이트")
    assert validate_goal_doc(doc) == [], "wave label wrongly rejected (should be value-unchecked, §1.5)"
    print("PASS test_inv4_wave_value_not_checked")


def test_inv4_inline_comment_in_enum_allowed() -> None:
    # legal YAML inline comment must NOT be rejected as a bad enum (review MEDIUM #1)
    doc = _VALID.replace("status: ready", "status: ready  # gate cleared")
    v = validate_goal_doc(doc)
    assert v == [], f"inline-comment enum wrongly rejected: {v}"
    print("PASS test_inv4_inline_comment_in_enum_allowed")


def test_inv4_quoted_hash_preserved() -> None:
    # a '#' inside a quoted scalar is literal, not a comment — must survive
    doc = _VALID.replace('title: Sample feature goal', 'title: "weights #42 tuning"')
    assert validate_goal_doc(doc) == [], "quoted '#' wrongly stripped/rejected"
    print("PASS test_inv4_quoted_hash_preserved")


def test_inv4_h3_section_recognized() -> None:
    # a required section nested at ### is still recognized (§2 keyword+order; review LOW)
    doc = _VALID.replace("## E2E 자가검증", "### E2E 자가검증")
    v = validate_goal_doc(doc)
    assert v == [], f"### section wrongly reported missing: {v}"
    print("PASS test_inv4_h3_section_recognized")


def test_inv4_real_g16_doc_passes() -> None:
    # dogfooding: the actual G16 goal-doc this code closes must validate clean
    g16 = (_SCRIPTS.parents[1] / "docs" / "plans" / "goal-docs" / "G16-harness-router-invariant.md")
    if g16.is_file():
        v = validate_goal_doc(g16.read_text(encoding="utf-8"))
        assert v == [], f"real G16 goal-doc failed INV-4: {v}"
    print("PASS test_inv4_real_g16_doc_passes")


# ── INV-1 (CON-1): new-file-only ─────────────────────────────────────────────

def test_inv1_clobber_caught() -> None:
    assert check_new_file_only("notes/a.md", ["notes/a.md", "notes/b.md"]) is not None
    print("PASS test_inv1_clobber_caught")


def test_inv1_new_path_allowed() -> None:
    assert check_new_file_only("notes/new.md", ["notes/a.md"]) is None
    print("PASS test_inv1_new_path_allowed")


def test_inv1_status_carveout_allowed() -> None:
    # frontmatter-only status-machine transition is within CON-1 (boundary §5 note)
    assert check_new_file_only("notes/a.md", ["notes/a.md"], frontmatter_only_status_patch=True) is None
    print("PASS test_inv1_status_carveout_allowed")


# ── INV-2/3 (CON-3): isolated critique / no self-approval ────────────────────

def test_inv23_self_approval_caught() -> None:
    plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor"},
        {"name": "critique", "binding": "executor"},  # same as impl → self-approval
    ]}
    assert check_isolated_critique(plan) is not None, "critique==author not caught"
    print("PASS test_inv23_self_approval_caught")


def test_inv23_candidate_or_overlap_caught() -> None:
    # candidate-or overlap: code-reviewer appears in both impl and critique candidates
    plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor|code-reviewer(#133)"},
        {"name": "critique", "binding": "adversarial-review|code-reviewer(#133)"},
    ]}
    assert check_isolated_critique(plan) is not None, "candidate-or overlap not caught"
    print("PASS test_inv23_candidate_or_overlap_caught")


def test_inv23_isolated_passes() -> None:
    plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor|native(#133)"},
        {"name": "critique", "binding": "adversarial-review|code-reviewer(#133)"},
    ]}
    assert check_isolated_critique(plan) is None, "properly isolated critique wrongly flagged"
    print("PASS test_inv23_isolated_passes")


def test_inv23_no_critique_slice_noop() -> None:
    # decision-only / doc-only have no critique slice → nothing to isolate
    plan = {"work_type": "doc-only", "slices": [{"name": "doc", "binding": "doc-concretize"}]}
    assert check_isolated_critique(plan) is None
    print("PASS test_inv23_no_critique_slice_noop")


def test_inv23_empty_critique_binding_caught() -> None:
    plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor"},
        {"name": "critique", "binding": ""},
    ]}
    assert check_isolated_critique(plan) is not None, "empty critique binding not caught"
    print("PASS test_inv23_empty_critique_binding_caught")


def test_inv23_self_approval_in_qualifier_caught() -> None:
    # an author skill-id smuggled inside a 직접(...) qualifier — candidate extraction
    # would drop it, so scan the raw binding (review MEDIUM #2 — directly CON-3)
    plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor"},
        {"name": "critique", "binding": "직접(executor가 self-review)"},
    ]}
    assert check_isolated_critique(plan) is not None, "self-approval hidden in qualifier not caught"
    print("PASS test_inv23_self_approval_in_qualifier_caught")


def test_inv23_legit_direct_qualifier_allowed() -> None:
    # 직접(<context>) that names NO author skill is legitimate (§3.3) — must pass
    plan = {"work_type": "feature-full", "slices": [
        {"name": "spec", "binding": "spec-first"},
        {"name": "impl", "binding": "executor|native(#133)"},
        {"name": "critique", "binding": "code-reviewer(별도 컨텍스트)"},
    ]}
    assert check_isolated_critique(plan) is None, "legit critique context qualifier wrongly flagged"
    print("PASS test_inv23_legit_direct_qualifier_allowed")


# ── INV-5 (CON-5): one-way dependency ────────────────────────────────────────

def test_inv5_leaf_import_caught() -> None:
    v = check_one_way_dependency("vault-bridge/scripts/x.py", "from invariant_guard import validate_goal_doc")
    assert v is not None, "leaf importing harness module not caught"
    print("PASS test_inv5_leaf_import_caught")


def test_inv5_leaf_plugin_import_caught() -> None:
    v = check_one_way_dependency("thinking-tools/scripts/y.py", "import workflow_harness.slice_router")
    assert v is not None, "leaf importing workflow_harness package not caught"
    print("PASS test_inv5_leaf_plugin_import_caught")


def test_inv5_leaf_shellout_caught() -> None:
    v = check_one_way_dependency(
        "obsidian-vault-manager/scripts/z.sh",
        "python3 workflow-harness/scripts/slice_router.py $doc",
    )
    assert v is not None, "leaf shelling out to harness script not caught"
    print("PASS test_inv5_leaf_shellout_caught")


def test_inv5_dynamic_import_caught() -> None:
    # __import__ / importlib.import_module evasions (review MEDIUM #3)
    a = check_one_way_dependency("vault-bridge/scripts/x.py", "m = __import__('slice_router')")
    b = check_one_way_dependency("thinking-tools/scripts/y.py", "importlib.import_module('invariant_guard')")
    assert a is not None, "__import__ evasion not caught"
    assert b is not None, "importlib.import_module evasion not caught"
    print("PASS test_inv5_dynamic_import_caught")


def test_inv5_variable_path_shellout_caught() -> None:
    # shellout where the harness path is assembled from a variable (review MEDIUM #3)
    v = check_one_way_dependency(
        "obsidian-vault-manager/scripts/z.py",
        "subprocess.run([py, H + '/slice_router.py'])",
    )
    assert v is not None, "variable-path shellout to harness not caught"
    print("PASS test_inv5_variable_path_shellout_caught")


def test_inv5_commented_out_import_not_flagged() -> None:
    # a commented-out import / "never do this" note must NOT trip INV-5 (#189 nit 2)
    v = check_one_way_dependency(
        "vault-bridge/scripts/x.py",
        "# from invariant_guard import validate_goal_doc  # NEVER do this",
    )
    assert v is None, "commented-out import wrongly flagged as INV-5 violation"
    # but a real (uncommented) import on the same kind of line is still caught
    live = check_one_way_dependency("vault-bridge/scripts/x.py", "from invariant_guard import validate_goal_doc")
    assert live is not None, "uncommented import wrongly skipped"
    print("PASS test_inv5_commented_out_import_not_flagged")


def test_inv5_harness_self_import_allowed() -> None:
    # harness importing its own sibling module is fine — one-way constrains leaf→harness
    v = check_one_way_dependency("workflow-harness/scripts/slice_router.py", "import invariant_guard")
    assert v is None, "harness self-import wrongly flagged as INV-5"
    print("PASS test_inv5_harness_self_import_allowed")


def test_inv5_leaf_prose_citation_allowed() -> None:
    # prose that merely NAMES the harness (boundary citation) is not a reverse dependency
    v = check_one_way_dependency("vault-bridge/README.md", "Bound by CON-5 (see workflow-harness boundary §5).")
    assert v is None, "leaf prose citing the harness wrongly flagged"
    print("PASS test_inv5_leaf_prose_citation_allowed")


def test_inv5_non_leaf_path_ignored() -> None:
    # a non-leaf file (e.g. telemetry, docs) is not constrained by INV-5
    v = check_one_way_dependency("telemetry/scripts/report.py", "from slice_router import route")
    assert v is None, "non-leaf path wrongly constrained by INV-5"
    print("PASS test_inv5_non_leaf_path_ignored")


# ── shared parser sanity ─────────────────────────────────────────────────────

def test_parser_extracts_slices_and_sections() -> None:
    parsed = parse_goal_doc(_VALID)
    assert parsed["frontmatter"]["work_type"] == "feature-full"
    assert len(parsed["slice_lines"]) == 2, f"expected 2 slice lines, got {parsed['slice_lines']}"
    assert len(parsed["section_headers"]) == 5
    print("PASS test_parser_extracts_slices_and_sections")


if __name__ == "__main__":
    test_inv4_valid_passes()
    test_inv4_missing_required_field()
    test_inv4_empty_issues_rejected()
    test_inv4_empty_depends_on_allowed()
    test_inv4_bad_model_enum()
    test_inv4_bad_status_enum()
    test_inv4_bug_light_worktype_rejected()
    test_inv4_depends_on_namespace()
    test_inv4_issues_namespace()
    test_inv4_missing_section()
    test_inv4_section_out_of_order()
    test_inv4_no_binding_structure()
    test_inv4_wave_value_not_checked()
    test_inv4_inline_comment_in_enum_allowed()
    test_inv4_quoted_hash_preserved()
    test_inv4_h3_section_recognized()
    test_inv4_real_g16_doc_passes()
    test_inv1_clobber_caught()
    test_inv1_new_path_allowed()
    test_inv1_status_carveout_allowed()
    test_inv23_self_approval_caught()
    test_inv23_candidate_or_overlap_caught()
    test_inv23_isolated_passes()
    test_inv23_no_critique_slice_noop()
    test_inv23_empty_critique_binding_caught()
    test_inv23_self_approval_in_qualifier_caught()
    test_inv23_legit_direct_qualifier_allowed()
    test_inv5_leaf_import_caught()
    test_inv5_leaf_plugin_import_caught()
    test_inv5_leaf_shellout_caught()
    test_inv5_dynamic_import_caught()
    test_inv5_variable_path_shellout_caught()
    test_inv5_commented_out_import_not_flagged()
    test_inv5_harness_self_import_allowed()
    test_inv5_leaf_prose_citation_allowed()
    test_inv5_non_leaf_path_ignored()
    test_parser_extracts_slices_and_sections()
    print("\nOK: all 37 cases passed")
