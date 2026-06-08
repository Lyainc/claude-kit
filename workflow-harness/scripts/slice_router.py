#!/usr/bin/env python3
"""slice_router.py — 4-way slice→skill binding router (#183 S1, Gap-ROUTE §4.1).

native `/goal` evaluates a *freeform* completion condition; it does NOT bind a
structured goal-doc to "this work_type → this slice sequence → each slice runs this
skill". That declarative routing is the one thin gap the harness owns
(`omc-to-native-substrate.md` §4.1). This module is exactly the *binding decision
logic* — it does not run the slices (native `/goal` + Workflow do that), it decides
what the sequence and bindings are.

Routing is driven by the goal-doc `work_type` (goal-doc-spec §3.6), with the fourth
work-type — bug-light — signalled by goal-doc ABSENCE, not a field value (§4.4):

    feature-full  → spec → impl → critique   (each a SEPARATE skill — CON-3)
    decision-only → decision                  (산출만, no implementation)
    doc-only      → doc                        (output only)
    (no goal-doc) → bug-light                  → debug direct, no slice

INV-4 is enforced as a precondition: route() validates the goal-doc with
invariant_guard.validate_goal_doc() before reading work_type, so a malformed goal-doc
never routes. This is the S1→S2 dependency made concrete (the router sits on top of
the invariant layer).

Native-delegation boundary (what this module does NOT do): it does not spawn the
bound skills, does not run the slice loop, does not summon reviewers. The active
agent under native `/goal` reads this plan and delegates each slice to native
agents / leaf skills. The harness only decides the binding.

Stdlib only. Imports the sibling invariant_guard (intra-harness, allowed — the
one-way rule constrains leaf→harness, not harness-internal modules; CON-5/§3).

CLI:
    python3 slice_router.py <goal-doc.md>   # JSON route plan for a goal-doc
    python3 slice_router.py                  # no goal-doc → bug-light (debug-direct) plan
    python3 slice_router.py --self-test      # in-memory 4-way cases
"""
from __future__ import annotations

import argparse
import json
import sys

from invariant_guard import parse_goal_doc, validate_goal_doc

# ── §3.6 work_type → default slice sequence + binding ────────────────────────
# impl/critique concrete attribution is #133's inventory (native-delegation first);
# the binding is written as candidate-or (`executor|native(#133)`) per goal-doc-spec
# §3.2 — the router carries the candidate set forward, #133 resolves it at runtime.
_SLICE_SEQUENCES = {
    "feature-full": {
        "route": "spec→impl→critique",
        "execution": "full",
        "slices": [
            {"name": "spec", "binding": "spec-first"},
            {"name": "impl", "binding": "executor|native(#133)"},
            {"name": "critique", "binding": "adversarial-review|code-reviewer(#133)"},
        ],
    },
    "decision-only": {
        "route": "decide-only",
        "execution": "none",  # 실행 없음, 산출만 (§3.6)
        "slices": [
            {"name": "decision", "binding": "expert-panel|adversarial-review"},
        ],
    },
    "doc-only": {
        "route": "output-only",
        "execution": "output-only",  # 출력 전용 (§3.6)
        "slices": [
            {"name": "doc", "binding": "doc-concretize|doc-polish|spec-first"},
        ],
    },
}

# §4.4 — bug-light: goal-doc is omitted entirely, router routes straight to debug.
_BUG_LIGHT_PLAN = {
    "work_type": "bug-light",
    "route": "debug-direct",
    "execution": "debug",
    "slices": [],
    "binding": "debug(#133)",
    "note": "goal-doc absent → debug direct, no slice (goal-doc-spec §4.4)",
}


def route(goal_doc_text) -> dict:
    """Return the slice routing plan for a goal-doc (or bug-light when it is absent).

    `goal_doc_text` is the goal-doc content, or None to signal goal-doc ABSENCE
    (bug-light, §4.4). When text is given, INV-4 runs first — an invalid goal-doc
    returns an `invalid` plan with the schema violations, never a routed sequence.
    """
    if goal_doc_text is None:
        plan = dict(_BUG_LIGHT_PLAN)
        plan["slices"] = list(_BUG_LIGHT_PLAN["slices"])  # don't alias the module constant
        return plan

    violations = validate_goal_doc(goal_doc_text)
    if violations:
        return {
            "work_type": None,
            "route": "invalid",
            "execution": "blocked",
            "slices": [],
            "violations": violations,
            "note": "goal-doc fails INV-4 schema validation — fix before routing (§4.3)",
        }

    fm = parse_goal_doc(goal_doc_text)["frontmatter"]
    work_type = fm.get("work_type")
    seq = _SLICE_SEQUENCES.get(work_type)
    if seq is None:
        # validate_goal_doc already constrains work_type to the enum, so this is a
        # defensive belt — only reachable if the enum set and this table drift apart.
        return {
            "work_type": work_type,
            "route": "unroutable",
            "execution": "blocked",
            "slices": [],
            "note": f"work_type {work_type!r} has no slice sequence binding (§3.6)",
        }

    plan = {"work_type": work_type}
    plan.update(seq)
    # Deep-copy the slice dicts so a caller mutating the returned plan can NEVER corrupt
    # the module-level routing table (_SLICE_SEQUENCES) via aliasing — the router's whole
    # job is to hand this plan to a caller that acts on it (#189 nit 1).
    plan["slices"] = [dict(s) for s in seq["slices"]]
    # carry goal identity through so the active agent can label the loop
    plan["goal_id"] = fm.get("goal_id")
    plan["recommended_model"] = fm.get("recommended_model")
    return plan


# ── self-test ────────────────────────────────────────────────────────────────

def _doc(work_type: str) -> str:
    return f"""---
goal_id: G99
title: Sample
issues: [200]
wave: 3
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
1. **only** → 바인딩: spec-first | 대상 파일: x | 산출: y | 검증: z

## E2E 자가검증
```bash
echo ok
```
"""


def run_self_test() -> int:
    failures = []

    # 1. feature-full → spec→impl→critique, each a separate skill
    p = route(_doc("feature-full"))
    if p["route"] != "spec→impl→critique":
        failures.append(f"  feature-full route wrong: {p['route']}")
    names = [s["name"] for s in p["slices"]]
    if names != ["spec", "impl", "critique"]:
        failures.append(f"  feature-full slices wrong: {names}")
    # critique binding must be disjoint from authoring bindings (CON-3 carried in §3.6)
    spec_impl = {p["slices"][0]["binding"], p["slices"][1]["binding"]}
    if p["slices"][2]["binding"] in spec_impl:
        failures.append("  feature-full critique binding not separate from author")

    # 2. decision-only → no implementation
    p = route(_doc("decision-only"))
    if p["execution"] != "none" or p["route"] != "decide-only":
        failures.append(f"  decision-only route/exec wrong: {p['route']}/{p['execution']}")

    # 3. doc-only → output only
    p = route(_doc("doc-only"))
    if p["execution"] != "output-only":
        failures.append(f"  doc-only execution wrong: {p['execution']}")

    # 4. bug-light → goal-doc absence → debug direct, no slice
    p = route(None)
    if p["work_type"] != "bug-light" or p["route"] != "debug-direct" or p["slices"]:
        failures.append(f"  bug-light routing wrong: {p}")

    # 5. invalid goal-doc never routes
    bad = _doc("feature-full").replace("work_type: feature-full", "work_type: nonsense")
    p = route(bad)
    if p["route"] != "invalid" or not p.get("violations"):
        failures.append(f"  invalid goal-doc routed instead of blocked: {p['route']}")

    if failures:
        print("FAIL: slice_router self-test")
        print("\n".join(failures))
        return 1
    print("OK: all slice_router self-test cases passed")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="4-way slice→skill binding router (#183)")
    parser.add_argument("path", nargs="?", help="goal-doc path; omit to signal bug-light (goal-doc absence)")
    parser.add_argument("--self-test", action="store_true", help="run in-memory 4-way cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if args.path is None:
        # no goal-doc → bug-light (§4.4)
        print(json.dumps(_BUG_LIGHT_PLAN, ensure_ascii=False, indent=2))
        return 0

    try:
        with open(args.path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print(f"ERROR: cannot read {args.path}: {e}", file=sys.stderr)
        return 2

    plan = route(text)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 1 if plan["route"] in ("invalid", "unroutable") else 0


if __name__ == "__main__":
    sys.exit(main())
