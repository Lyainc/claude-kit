#!/usr/bin/env python3
"""Regression tests for slice_router.py — 4-way slice→skill binding router (#183 S1).

Covers the four work-type routes (goal-doc-spec §3.6 + §4.4) plus the native-
delegation boundary: an invalid goal-doc is blocked by INV-4 before routing, and the
router emits *bindings*, never a running loop (native `/goal`+Workflow run the loop).

    feature-full  → spec → impl → critique  (each a SEPARATE skill — CON-3)
    decision-only → decision (no implementation)
    doc-only      → doc (output only)
    (no goal-doc) → bug-light → debug direct (§4.4)
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent          # scripts/test
_SCRIPTS = _HERE.parent                            # scripts
sys.path.insert(0, str(_SCRIPTS))

from invariant_guard import check_isolated_critique  # noqa: E402
from slice_router import route  # noqa: E402


def _doc(work_type: str, *, single_slice: bool = True) -> str:
    if single_slice:
        slices = "1. **only** → 바인딩: spec-first | 대상 파일: x | 산출: y | 검증: z\n"
    else:
        slices = (
            "1. **spec** → 바인딩: spec-first | 대상 파일: x | 산출: y | 검증: z\n"
            "2. **impl** → 바인딩: executor|native(#133) | 대상 파일: x | 산출: y | 검증: z\n"
            "3. **critique** → 바인딩: adversarial-review|code-reviewer(#133) | 대상 파일: x | 산출: y | 검증: z\n"
        )
    return f"""---
goal_id: G50
title: Sample
issues: [300]
wave: 2
depends_on: [G1]
recommended_model: sonnet
status: ready
work_type: {work_type}
created: 2026-06-08
---

## 배경 / 목적
why.

## 완료 조건 (Definition of Done)
- [ ] thing

## 쟁점과 트레이드오프
| a | b |

## 슬라이스 순서
{slices}
## E2E 자가검증
```bash
echo ok
```
"""


# ── the four routes (§3.6 + §4.4) ────────────────────────────────────────────

def test_feature_full_route() -> None:
    p = route(_doc("feature-full", single_slice=False))
    assert p["route"] == "spec→impl→critique", f"route: {p['route']}"
    assert p["execution"] == "full"
    names = [s["name"] for s in p["slices"]]
    assert names == ["spec", "impl", "critique"], f"slices: {names}"
    print("PASS test_feature_full_route")


def test_feature_full_each_separate_skill() -> None:
    # §3.6 / 2026-06-03 decision: spec/impl/critique are each a SEPARATE skill,
    # not a single "spec-impl-critique" binding.
    p = route(_doc("feature-full", single_slice=False))
    bindings = [s["binding"] for s in p["slices"]]
    assert len(set(bindings)) == 3, f"spec/impl/critique must be 3 distinct bindings: {bindings}"
    print("PASS test_feature_full_each_separate_skill")


def test_feature_full_critique_isolated() -> None:
    # the router's default binding must already satisfy CON-3 (critique ≠ author)
    p = route(_doc("feature-full", single_slice=False))
    assert check_isolated_critique(p) is None, "default feature-full binding violates isolated critique"
    print("PASS test_feature_full_critique_isolated")


def test_decision_only_route() -> None:
    p = route(_doc("decision-only"))
    assert p["route"] == "decide-only"
    assert p["execution"] == "none", "decision-only must have no implementation (§3.6)"
    assert [s["name"] for s in p["slices"]] == ["decision"]
    print("PASS test_decision_only_route")


def test_doc_only_route() -> None:
    p = route(_doc("doc-only"))
    assert p["route"] == "output-only"
    assert p["execution"] == "output-only", "doc-only is output-only (§3.6)"
    print("PASS test_doc_only_route")


def test_bug_light_goal_doc_absence() -> None:
    # §4.4: bug-light is goal-doc ABSENCE → route(None), debug direct, no slice
    p = route(None)
    assert p["work_type"] == "bug-light"
    assert p["route"] == "debug-direct"
    assert p["execution"] == "debug"
    assert p["slices"] == [], "bug-light routes straight to debug, no slice"
    print("PASS test_bug_light_goal_doc_absence")


# ── INV-4 precondition: an invalid goal-doc never routes ─────────────────────

def test_invalid_goal_doc_blocked() -> None:
    bad = _doc("feature-full").replace("work_type: feature-full", "work_type: nonsense")
    p = route(bad)
    assert p["route"] == "invalid", f"invalid goal-doc should block, got {p['route']}"
    assert p.get("violations"), "blocked plan must carry the schema violations"
    assert p["slices"] == []
    print("PASS test_invalid_goal_doc_blocked")


def test_malformed_no_frontmatter_blocked() -> None:
    p = route("just some markdown, no frontmatter at all")
    assert p["route"] == "invalid", "a doc with no frontmatter must not route"
    print("PASS test_malformed_no_frontmatter_blocked")


# ── native-delegation boundary ───────────────────────────────────────────────

def test_router_emits_bindings_not_execution() -> None:
    # the router decides bindings; it must not claim to RUN anything. Every slice is a
    # (name, binding) pair — no spawned agent, no loop state — native runs the loop.
    p = route(_doc("feature-full", single_slice=False))
    for s in p["slices"]:
        assert set(s.keys()) == {"name", "binding"}, f"slice carries non-binding state: {s}"
    print("PASS test_router_emits_bindings_not_execution")


def test_real_g16_routes_feature_full() -> None:
    # dogfooding: the actual G16 goal-doc routes to feature-full with isolated critique
    g16 = (_SCRIPTS.parents[1] / "docs" / "plans" / "goal-docs" / "G16-harness-router-invariant.md")
    if g16.is_file():
        p = route(g16.read_text(encoding="utf-8"))
        assert p["work_type"] == "feature-full", f"G16 should be feature-full, got {p['work_type']}"
        assert p["goal_id"] == "G16"
        assert check_isolated_critique(p) is None
    print("PASS test_real_g16_routes_feature_full")


if __name__ == "__main__":
    test_feature_full_route()
    test_feature_full_each_separate_skill()
    test_feature_full_critique_isolated()
    test_decision_only_route()
    test_doc_only_route()
    test_bug_light_goal_doc_absence()
    test_invalid_goal_doc_blocked()
    test_malformed_no_frontmatter_blocked()
    test_router_emits_bindings_not_execution()
    test_real_g16_routes_feature_full()
    print("\nOK: all 10 cases passed")
