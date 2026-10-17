#!/usr/bin/env python3
"""Tests for next-goal-render.py (#792) — the pick rendered from next-goal's judgment JSON.

Covers: pick targets render as `<seed slug>/<id> · description` from the via Seed's own items
(an unknown or canonical-only target is refused; the same id in two walked Seeds is told apart by
affiliation; a cross-repo key keeps its `owner/repo:` prefix; a legacy Seed still renders); FROM's edge path and TRACE's counts come from a fresh walk, never from the JSON; a `via`
the walk never visited is refused; another repo's Seed cannot be the pick; a Seed or HEAD change
after the walk marks the judgment stale; a missing Seed handoff reads differently from "no
candidate"; no Seed/no gaps keeps three lines; no pick retains uncertainty, and STOP assertions
are checked against actual visited/stopped records (#826); the same JSON renders identically twice.

Usage: python3 thinking-tools/scripts/test/test-next-goal-render.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import atexit
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "next-goal-render.py"
_RELATIONS = Path(__file__).resolve().parents[1] / "seed-relations.py"


def _repo(ac="acceptance-1"):
    d = tempfile.mkdtemp(prefix="test-next-goal-render-")
    atexit.register(shutil.rmtree, d, ignore_errors=True)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    specs = Path(d) / "docs" / "specs"
    specs.mkdir(parents=True)
    (specs / "p.yaml").write_text(
        "skill: build-spec\ntarget: parent\nlifecycle:\n  state: active\n  outcome: null\n  reason: requested\n  approved_by: fixture user request\n  evidence:\n    commit: null\n    items: []\n  withdrawn: []\nrelations:\n  parent: null\n  refines: []\n"
        "  depends_on: []\n  children: [docs/specs/c.yaml, other/repo:docs/specs/x.yaml]\n"
        "success_criteria:\n  - id: %s\n    description: parent outcome\n" % ac, encoding="utf-8")
    (specs / "c.yaml").write_text(
        "skill: build-spec\ntarget: child\nlifecycle:\n  state: active\n  outcome: null\n  reason: requested\n  approved_by: fixture user request\n  evidence:\n    commit: null\n    items: []\n  withdrawn: []\nrelations:\n  parent: docs/specs/p.yaml\n"
        "  refines: [%s]\n  link_reason: settles %s\n  depends_on: []\n  children: []\n"
        "success_criteria:\n  - id: %s\n    description: child outcome\n" % (ac, ac, ac), encoding="utf-8")
    return d


def _walk_id(repo):
    p = subprocess.run([sys.executable, str(_RELATIONS), "walk", "docs/specs/c.yaml"], cwd=repo,
                       capture_output=True, encoding="utf-8", env=_env())
    first = p.stdout.splitlines()[0].split("\t")
    return next(f[3:] for f in first if f.startswith("id="))


def _env():
    return {**os.environ, "GH_BIN": "/nonexistent/gh"}


def _render(repo, judgment, *args):
    p = subprocess.run([sys.executable, str(_SCRIPT), "--cwd", repo, *args], input=json.dumps(judgment),
                       capture_output=True, encoding="utf-8", env=_env())
    return p.returncode, p.stdout, p.stderr


def _judgment(walk_id, pick_via="docs/specs/p.yaml", **over):
    j = {
        "seed": "docs/specs/c.yaml", "walk_id": walk_id, "handoff": "named",
        "pick": {"title": "부모 acceptance-1 마무리", "via": pick_via, "targets": ["acceptance-1"],
                 "evidence": "acceptance-1 검사 스크립트가 아직 없음", "startable": "yes",
                 "startable_reason": "선행 없음", "user_change": "부모 목표를 끝까지 확인할 수 있음"},
        "alternatives": [{"title": "x Seed", "via": "other/repo:docs/specs/x.yaml",
                          "decision": "external", "reason": "다른 레포"}],
        "unverified": [],
    }
    j.update(over)
    return j


failures = []


def check(name, cond, detail=""):
    if not cond:
        failures.append(f"{name}: {detail}")


def main():
    repo = _repo()
    wid = _walk_id(repo)

    code, out, err = _render(repo, _judgment(wid))
    lines = out.splitlines()
    check("named renders four lines", code == 0 and [ln[:8] for ln in lines] ==
          ["NEXT    ", "FROM    ", "SKIPPED ", "TRACE   "], f"{code} {out!r} {err!r}")
    check("FROM path comes from the walk", "Seed edge: 출발 →parent docs/specs/p.yaml (p/acceptance-1 · parent outcome)" in out, out)
    check("TRACE counts come from the walk", "출발 docs/specs/c.yaml" in out and "방문 " in out
          and "조회 실패 1곳" in out, out)
    check("not stale on a fresh walk", "근거 변경됨" not in out, out)

    # Live consumer proof text can contain line endings; each rendered field stays one line.
    multiline = _judgment(wid)
    for key in ("title", "evidence", "startable_reason", "user_change", "note"):
        multiline["pick"][key] = "첫 줄\n\n  둘째 줄"
    multiline["alternatives"][0]["title"] = "외부\r\n선행"
    multiline["alternatives"][0]["reason"] = "ready\n과 실제 증거"
    multiline["unverified"] = ["미확인\n외부"]
    code, multiline_out, err = _render(repo, multiline)
    check("multiline judgment keeps four output fields", code == 0
          and [line[:8] for line in multiline_out.splitlines()] ==
          ["NEXT    ", "FROM    ", "SKIPPED ", "TRACE   "]
          and "ready 과 실제 증거" in multiline_out
          and "첫 줄 둘째 줄" in multiline_out and "  둘째" not in multiline_out
          and "외부 선행" in multiline_out and "\r" not in multiline_out
          and "미확인: 미확인 외부" in multiline_out, f"{code} {multiline_out!r} {err!r}")
    code2, out2, _ = _render(repo, _judgment(wid))
    # TRACE ends with the walk's own clock (`@ <UTC second>`), taken afresh on every render, so a
    # second boundary between the two runs is not a rendering difference.
    def no_clock(text):
        return re.sub(r" @ \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", " @ <at>", text, flags=re.M)
    check("same JSON renders identically", (code2, no_clock(out2)) == (code, no_clock(out)))

    p1 = subprocess.run([sys.executable, str(_RELATIONS), "walk", "docs/specs/c.yaml", "--max-depth",
                         "1", "--max-nodes", "2"], cwd=repo, capture_output=True, encoding="utf-8",
                        env=_env())
    wid1 = next(f[3:] for f in p1.stdout.splitlines()[0].split("\t") if f.startswith("id="))
    code, out, err = _render(repo, _judgment(wid1, alternatives=[]))
    check("re-walk uses the limits carried in the walk id", code == 0 and "근거 변경됨" not in out
          and "깊이≤1, 상한 2개" in out, f"{code} {out!r} {err!r}")
    code, _, err = _render(repo, _judgment(wid.rsplit("~", 1)[0]))
    check("walk id without limits refused cleanly", code == 1 and "Traceback" not in err, err)

    code, out, err = _render(repo, _judgment(wid, pick_via="docs/specs/never.yaml"))
    check("unwalked via refused", code == 1 and out == "" and "방문하지 않은" in err, f"{code} {err!r}")

    code, out, err = _render(repo, _judgment(wid, pick_via="other/repo:docs/specs/x.yaml"))
    check("external pick refused", code == 1 and "다른 레포" in err, f"{code} {err!r}")

    bad = _judgment(wid)
    bad["alternatives"][0]["decision"] = "held"
    code, _, err = _render(repo, bad)
    check("external alternative must be decision external", code == 1, err)

    bad = _judgment(wid)
    bad["pick"]["startable"] = "no"
    code, _, err = _render(repo, bad)
    check("unstartable pick refused", code == 1, err)

    code, out, err = _render(repo, {"seed": None, "walk_id": None, "handoff": "missing",
                                    "pick": None, "alternatives": [], "unverified": []})
    check("missing handoff differs from no candidate", code == 0 and "NEXT     · 없음" in out
          and "인계 누락" in out and "넘겨받지 못해" in out, f"{code} {out!r} {err!r}")

    code, out, err = _render(repo, {"handoff": "none", "pick": None, "alternatives": []})
    check("no Seed keeps three lines", code == 0 and len(out.splitlines()) == 3
          and "TRACE" not in out and "검토한 범위 안" in out, f"{code} {out!r} {err!r}")

    # #826: no pick is not proof that an unavailable pool has no candidates.
    gap = "열린 이슈 비교: GitHub 리모트가 없어 조회 못 함"
    no_seed = {"seed": None, "walk_id": None, "handoff": "none", "pick": None,
               "alternatives": [], "unverified": [gap]}
    for handoff in ("none", "missing"):
        code, out, err = _render(repo, {**no_seed, "handoff": handoff})
        check(handoff + " retains unavailable backlog without a pick", code == 0
              and gap in out and "TRACE" in out and "가치 있는 후속 후보가 없어요" not in out
              and ("인계 누락" in out if handoff == "missing" else "미평가" in out),
              f"{code} {out!r} {err!r}")
    for unverified in ([None], [42], [" \n "]):
        code, out, err = _render(repo, {**no_seed, "unverified": unverified})
        check("malformed uncertainty cannot disappear", code == 1 and out == ""
              and "unverified" in err, f"{code} {out!r} {err!r}")

    code, out, err = _render(repo, {**no_seed, "unverified": [], "alternatives": [
        {"title": "확인 못 한 후보", "via": "backlog", "decision": "unverified", "reason": gap}]})
    check("unverified alternative prevents an exhaustive no-pick claim", code == 0
          and "미평가" in out and gap in out, f"{code} {out!r} {err!r}")

    # The parent was visited at depth 1; the external child is the actual depth-2 STOP.
    stop = {"from": "docs/specs/p.yaml", "edge": "children",
            "target": "other/repo:docs/specs/x.yaml", "reason": "depth"}
    bounded = _judgment(wid1, pick=None, alternatives=[], walk_stops=[stop])
    code, out, err = _render(repo, bounded)
    check("bounded no-pick names visited and actual stopped targets", code == 0
          and "미평가" in out and "docs/specs/p.yaml (깊이 1, ok)" in out
          and "docs/specs/p.yaml →children other/repo:docs/specs/x.yaml (depth)" in out,
          f"{code} {out!r} {err!r}")
    for field, wrong in (("target", "docs/specs/p.yaml"), ("reason", "nodes"),
                         ("from", "docs/specs/c.yaml"), ("edge", "parent")):
        code, out, err = _render(repo, {**bounded, "walk_stops": [{**stop, field: wrong}]})
        check("stop assertion rejects wrong " + field, code == 1 and out == ""
              and "walk_stops[0]" in err and "walk" in err, f"{code} {out!r} {err!r}")
    code, out, err = _render(repo, _judgment(wid1, pick=None, alternatives=[]))
    check("walker gaps survive omitted stop assertions and unverified", code == 0
          and "미평가" in out and "other/repo:docs/specs/x.yaml (depth)" in out,
          f"{code} {out!r} {err!r}")
    code, out, err = _render(repo, _judgment(wid, pick=None, alternatives=[]))
    check("failed walk lookup prevents exhaustive no-pick claim", code == 0
          and "미평가" in out and "조회 실패 1곳" in out, f"{code} {out!r} {err!r}")

    # All local visited candidates may be below the floor; absence is valid within that scope.
    parent = Path(repo) / "docs/specs/p.yaml"
    full_parent = parent.read_text(encoding="utf-8")
    parent.write_text(full_parent.replace(', other/repo:docs/specs/x.yaml', ''), encoding="utf-8")
    clear_id = _walk_id(repo)
    code, out, err = _render(repo, _judgment(clear_id, pick=None, alternatives=[]))
    check("complete named no-pick stays a valid scoped conclusion", code == 0
          and "검토한 범위 안" in out and "미평가" not in out, f"{code} {out!r} {err!r}")
    # A CYCLE is an edge cut to an already visited node: it leaves no unevaluated scope.
    parent.write_text(parent.read_text(encoding="utf-8").replace(
        "relations:\n  parent: null", "relations:\n  parent: docs/specs/c.yaml"), encoding="utf-8")
    cycle_id = _walk_id(repo)
    code, out, err = _render(repo, _judgment(cycle_id, pick=None, alternatives=[]))
    check("cycle-only no-pick stays a valid scoped conclusion", code == 0 and "순환" in out
          and "검토한 범위 안" in out and "미평가" not in out, f"{code} {out!r} {err!r}")
    parent.write_text(parent.read_text(encoding="utf-8").replace(
        "parent: docs/specs/c.yaml", "parent: null", 1), encoding="utf-8")
    parent.write_text(parent.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    code, out, err = _render(repo, _judgment(clear_id, pick=None, alternatives=[]))
    check("stale no-pick retains uncertainty", code == 0 and "미평가" in out
          and "근거 변경됨" in out, f"{code} {out!r} {err!r}")
    parent.write_text(full_parent, encoding="utf-8")

    pn = subprocess.run([sys.executable, str(_RELATIONS), "walk", "docs/specs/c.yaml",
                         "--max-depth", "3", "--max-nodes", "2"], cwd=repo,
                        capture_output=True, encoding="utf-8", env=_env())
    nwid = next(f[3:] for f in pn.stdout.splitlines()[0].split("\t") if f.startswith("id="))
    node_stop = {k: " \n " + v + " " for k, v in {**stop, "reason": "nodes"}.items()}
    code, out, err = _render(repo, _judgment(nwid, pick=None, alternatives=[], walk_stops=[node_stop]))
    check("node cap and normalized STOP assertion retain the actual target", code == 0
          and "미평가" in out and "other/repo:docs/specs/x.yaml (nodes)" in out,
          f"{code} {out!r} {err!r}")
    code, out, err = _render(repo, {**no_seed, "walk_stops": [stop]})
    check("STOP requires a named walk", code == 1 and out == "" and "walk_stops" in err, err)

    code, _, err = _render(repo, {"handoff": "none", "pick": {"title": "외부\r\n선행", "via": "docs/specs/c.yaml",
                                  "targets": ["acceptance-1"], "evidence": "e", "startable": "yes", "startable_reason": "r",
                                  "user_change": "u"}, "alternatives": []})
    check("Seed via without a walk refused", code == 1, err)
    check("refusal names a multiline title on one line", "'외부 선행'" in err
          and len(err.strip().splitlines()) == 1, err)

    p = Path(repo) / "docs" / "specs" / "p.yaml"
    original = p.read_text(encoding="utf-8")
    p.write_text(original + "\n# edited\n", encoding="utf-8")
    code, out, err = _render(repo, _judgment(wid))
    check("a visited non-start Seed change marks stale", code == 0 and "근거 변경됨" in out,
          f"{out!r} {err!r}")
    p.write_text(original, encoding="utf-8")

    c = Path(repo) / "docs" / "specs" / "c.yaml"
    c.write_text(c.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    code, out, err = _render(repo, _judgment(wid))
    check("Seed change after the walk marks stale", code == 0 and "근거 변경됨" in out, f"{out!r} {err!r}")

    # targets: affiliation disambiguates the same local id in two walked Seeds.
    code, out, err = _render(repo, _judgment(wid, pick_via="docs/specs/c.yaml"))
    check("same id in another walked Seed shows its own affiliation and description",
          code == 0 and "(c/acceptance-1 · child outcome)" in out and "p/acceptance-1" not in out,
          f"{code} {out!r} {err!r}")
    code, out, err = _render(repo, _judgment(wid, pick_via="session"))
    check("session via keeps targets as free text", code == 0 and "이번 세션 후속 (acceptance-1)" in out,
          f"{code} {out!r} {err!r}")
    bad = _judgment(wid)
    bad["pick"]["targets"] = ["acceptance-9"]
    code, out, err = _render(repo, bad)
    check("target the via Seed does not define is refused", code == 1 and out == ""
          and "acceptance-9" in err and "docs/specs/p.yaml" in err, f"{code} {out!r} {err!r}")
    bad["pick"]["targets"] = ["acceptance-1", "constraint-4"]
    code, out, err = _render(repo, bad)
    check("one unknown target refuses the whole pick", code == 1 and out == "" and "constraint-4" in err, err)
    bad["pick"]["targets"] = ["ac1"]
    code, out, err = _render(repo, bad)
    check("legacy spelling of a migrated item is refused with a hint", code == 1
          and "acceptance-1" in err and "seed-id-migrate.py" in err, f"{code} {err!r}")
    for missing in (False, True):
        bad = _judgment(wid)
        if missing:
            del bad["pick"]["targets"]
        else:
            bad["pick"]["targets"] = []
        code, out, err = _render(repo, bad)
        check("Seed pick must name its item scope", code == 1 and out == ""
              and "pick.targets" in err, f"{code} {out!r} {err!r}")

    # cross-repo key keeps its coordinate prefix (an external Seed cannot be a pick, so call directly).
    spec = importlib.util.spec_from_file_location("ngr", str(_SCRIPT))
    ngr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ngr)
    rel = ngr._load_relations()
    got = ngr._render_targets(rel, "other/repo:docs/specs/x.yaml",
                              {"item_desc": {"constraint-1": "DB 스키마\n생성"}}, ["constraint-1"])
    check("cross-repo key shows owner/repo: prefix", got == ["other/repo:x/constraint-1 · DB 스키마 생성"], str(got))

    # #854: a target description is cut to its first sentence and a fixed cap, '…' marks what was dropped.
    cap = ngr._TARGET_DESC_MAX
    desc_of = lambda d: ngr._render_targets(rel, "docs/specs/x.yaml", {"item_desc": {"constraint-1": d}},
                                            ["constraint-1"])[0].split(" · ", 1)[1]
    got = desc_of("첫 문장이에요. 둘째 문장이에요. 셋째 문장이에요.")
    check("multi-sentence description keeps the first sentence + marker", got == "첫 문장이에요.…", got)
    got = desc_of("word " * 60)
    check("over-long sentence is capped with a marker", got.endswith("…") and len(got) <= cap + 1, got)
    got = desc_of("DB 스키마 생성")
    check("short description is unchanged without a marker", got == "DB 스키마 생성", got)
    got = desc_of("Short one.")
    check("short sentence with a final period gets no marker", got == "Short one.", got)
    got = ngr._render_targets(rel, "docs/specs/x.yaml", {"item_desc": {"constraint-1": ""}}, ["constraint-1"])
    check("no description renders the bare id", got == ["x/constraint-1"], str(got))

    # #854 end to end: 8 targets with long multi-sentence descriptions keep FROM bounded.
    big = _repo()
    long_desc = " ".join("이 항목은 충분히 길게 쓰인 문장이라서 설명 전체를 그대로 찍으면 한 줄이 아주 길어져요." for _ in range(4))
    items = [("constraints", "constraint-%d" % i) for i in range(1, 4)] + \
            [("success_criteria", "acceptance-%d" % i) for i in range(1, 6)]
    body = "".join("%s:\n" % k + "".join("  - id: %s\n    description: %s\n" % (i, long_desc)
                                        for kk, i in items if kk == k)
                   for k in ("constraints", "success_criteria"))
    pyaml = Path(big) / "docs" / "specs" / "p.yaml"
    head = pyaml.read_text(encoding="utf-8").split("success_criteria:")[0]
    pyaml.write_text(head + body, encoding="utf-8")
    bj = _judgment(_walk_id(big))
    bj["pick"]["targets"] = [i for _, i in items]
    code, out, err = _render(big, bj)
    from_line = next((ln for ln in out.splitlines() if ln.startswith("FROM")), "")
    check("8-target pick renders", code == 0 and from_line != "", f"{code} {out!r} {err!r}")
    paren = from_line[from_line.find(" ("):from_line.find(") — 미충족")]
    check("every qualified id still appears", all("p/" + i in paren for _, i in items), paren)
    check("FROM target list is bounded", 0 < len(paren) <= 8 * (len("p/constraint-1") + cap + 6), str(len(paren)))
    check("whole FROM line stays short", 0 < len(from_line) < 1500, str(len(from_line)))

    # Missing eligibility from an older walker never authorizes a pick.
    for name, eligibility in [
        ("missing eligibility", None),
        ("paused Seed", {"eligible": False, "reason": "paused", "excluded_items": [], "review_required": False}),
        ("unknown lifecycle", {"eligible": False, "reason": "unknown", "excluded_items": [], "review_required": True}),
        ("review required", {"eligible": True, "reason": "review", "excluded_items": [], "review_required": True}),
        ("malformed exclusions", {"eligible": True, "reason": "active", "excluded_items": "acceptance-1", "review_required": False}),
        ("excluded target", {"eligible": True, "reason": "active", "excluded_items": ["acceptance-1"], "review_required": False}),
    ]:
        node = {"key": "docs/specs/p.yaml", "status": "ok"}
        if eligibility is not None:
            node["eligibility"] = eligibility
        refused = False
        try:
            ngr._check_vias(_judgment(wid, alternatives=[]), {node["key"]: node})
        except ngr.Refused:
            refused = True
        check(name + " refuses pick", refused)
        held = _judgment(wid, pick=None, alternatives=[
            {"title": "held", "via": node["key"], "decision": "held", "reason": "review"}])
        ngr._check_vias(held, {node["key"]: node})
    padded = _judgment(wid, alternatives=[])
    padded["pick"]["targets"] = [" acceptance-1 "]
    try:
        ngr._check_vias(padded, {node["key"]: node})
        check("whitespace cannot bypass excluded target", False)
    except ngr.Refused:
        pass

    # Stale judgments recheck current on-disk lifecycle and withdrawn items.
    for label, lifecycle in [
        ("paused", "  state: paused\n  outcome: null\n  reason: waiting\n"),
        ("closed", "  state: closed\n  outcome: discontinued\n  reason: stopped\n"),
        ("withdrawn", "  state: active\n  outcome: null\n  reason: no longer needed\n  withdrawn:\n    - id: acceptance-1\n      reason: no longer needed\n"),
    ]:
        replacement = lifecycle + "  approved_by: fixture transition request\n  evidence:\n    commit: null\n    items: []\n"
        if label != "withdrawn":
            replacement += "  withdrawn: []\n"
        p.write_text(original.replace("  state: active\n  outcome: null\n  reason: requested\n  approved_by: fixture user request\n  evidence:\n    commit: null\n    items: []\n  withdrawn: []\n", replacement), encoding="utf-8")
        code, out, err = _render(repo, _judgment(wid))
        check(label + " after judgment refuses pick before printing", code == 1 and out == "", f"{code} {out!r} {err!r}")
        for runtime in ("claude", "codex"):
            check(label + " refusal is unchanged in " + runtime,
                  _render(repo, _judgment(wid), "--runtime", runtime) == (code, out, err))
    p.write_text(original.replace("lifecycle:\n  state: active\n  outcome: null\n  reason: requested\n  approved_by: fixture user request\n  evidence:\n    commit: null\n    items: []\n  withdrawn: []\n", ""), encoding="utf-8")
    code, out, err = _render(repo, _judgment(wid))
    check("absent lifecycle refuses legacy pick", code == 1 and out == "", f"{code} {out!r} {err!r}")
    p.write_text(original, encoding="utf-8")

    # a legacy Seed still renders; a canonical-only match is refused.
    legacy = _repo(ac="ac1")
    lwid = _walk_id(legacy)
    j = _judgment(lwid)
    j["pick"]["targets"] = ["ac1"]
    code, out, err = _render(legacy, j)
    check("legacy Seed still renders", code == 0 and "(p/ac1 · parent outcome)" in out, f"{code} {out!r} {err!r}")
    j["pick"]["targets"] = ["acceptance-1"]
    code, out, err = _render(legacy, j)
    check("new-form target on a legacy Seed is refused with a hint", code == 1 and "'ac1'" in err
          and "seed-id-migrate.py" in err, f"{code} {err!r}")

    # #861: runtime selection changes presentation only, including refusals and diagnostics.
    panel_repo = _repo()
    panel_parent = Path(panel_repo) / "docs/specs/p.yaml"
    panel_parent.write_text(panel_parent.read_text().replace(', other/repo:docs/specs/x.yaml', ''))
    panel_id = _walk_id(panel_repo)
    panel_j = _judgment(panel_id, alternatives=[])
    plain = _render(panel_repo, panel_j)
    codex = _render(panel_repo, panel_j, "--runtime", "codex")
    check("explicit Codex preserves plain output", (plain[0], no_clock(plain[1]), plain[2]) ==
          (codex[0], no_clock(codex[1]), codex[2]), str(codex))

    def panel(judgment, repo=panel_repo):
        code, text, err = _render(repo, judgment, "--runtime", "claude")
        # Measure the complete panel, not the wrapper's private helpers.
        widths = [sum(0 if unicodedata.combining(c) or unicodedata.category(c) in ("Mn", "Me")
                      else 2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in line)
                  for line in text.splitlines()]
        check("Claude panel uses exactly 80 display cells", code == 0 and widths and
              all(width == 80 for width in widths), f"{code} {widths} {text!r} {err}")
        content = " ".join(" ".join(line[2:-2] for line in text.splitlines() if line.startswith("| ")).split())
        return text, content

    boxed, content = panel(panel_j)
    check("Claude box has one closed frame and content labels", boxed.splitlines()[0] == "+" + "-" * 78 + "+"
          and all("| " + label + " " in boxed for label in ("NEXT", "FROM", "SKIPPED", "TRACE"))
          and boxed.splitlines()[-1] == "+" + "-" * 78 + "+"
          and "├" not in boxed and all(line[2:-2].strip() for line in boxed.splitlines()[1:-1]), boxed)
    check("healthy TRACE keeps the actual edge and compact evidence", "c →parent p" in content and
          "2/25 방문 · 깊이 ≤ 3 · 근거 #" in content and re.search(r"근거 #[0-9a-f]{8}\b", content)
          and "방문 대상:" not in content and " @ " not in content and panel_id not in content, content)
    check("FROM names the source and keeps scope plus why/readiness/benefit", "FROM Seed p acceptance-1 · parent outcome" in content
          and all(value in content for value in (panel_j["pick"]["evidence"], panel_j["pick"]["startable_reason"],
                                                panel_j["pick"]["user_change"]))
          and all(label in content for label in ("근거", "착수", "변화"))
          and "p/acceptance-1" not in content, content)

    sibling_repo = _repo()
    sibling_parent = Path(sibling_repo) / "docs/specs/p.yaml"
    sibling_parent.write_text(sibling_parent.read_text().replace(
        "other/repo:docs/specs/x.yaml", "docs/specs/sibling.yaml"))
    (Path(sibling_repo) / "docs/specs/sibling.yaml").write_text(
        (Path(sibling_repo) / "docs/specs/c.yaml").read_text().replace("target: child", "target: sibling"))
    _, content = panel(_judgment(_walk_id(sibling_repo), pick_via="docs/specs/sibling.yaml", alternatives=[]), sibling_repo)
    check("healthy TRACE preserves parent and child edges", "c →parent p →children sibling" in content
          and "FROM Seed sibling acceptance-1 · child outcome" in content, content)

    long_path = "docs/" + "한글Ａé" * 70 + "/target.yaml"
    wide = {"handoff": "none", "pick": {"title": "한글·●✓…→ Ａ é " * 30, "via": "session",
            "targets": [long_path], "evidence": "긴 근거 " * 65, "startable": "unknown",
            "startable_reason": "확인 대기", "user_change": "변경 확인", "note": "유지보수 기록 보존"}, "alternatives": []}
    boxed, content = panel(wide)
    check("unbroken paths and combining marks survive wrapping", long_path in content.replace(" ", "")
          and "é" in content and not any(line.startswith("| ́") for line in boxed.splitlines()), boxed)
    check("long labeled paragraphs use hanging indentation", any(line.startswith("|       ") and "긴 근거" in line
          for line in boxed.splitlines()) and "미확인: 확인 대기" in content and "유지보수 기록 보존" in content, boxed)
    for tone in ("〮", "〯"):
        wide["pick"]["title"] = "a" * 72 + "한" + tone
        boxed, _ = panel(wide)
        check("Hangul combining tone stays with its base at the wrap boundary",
              any("한" + tone in line for line in boxed.splitlines()), boxed)

    # Every selected requirement keeps its own meaning, even with more than two targets.
    descriptions = {2: "선행 승인 없이 파일을 덮어쓰지 않아요", 3: "선택하지 않은 요구사항",
                    4: "검사 실패 시 기존 파일과 오류 근거를 보존해요", 5: "사용자가 결과를 다시 검증할 수 있어요"}
    panel_parent.write_text(panel_parent.read_text() + "\n" + "".join(
        "  - id: acceptance-%d\n    description: %s\n" % (i, desc) for i, desc in descriptions.items()))
    many = _judgment(_walk_id(panel_repo), alternatives=[])
    many["pick"]["targets"] = ["acceptance-1", "acceptance-2", "acceptance-4", "acceptance-5"]
    _, content = panel(many)
    check("many targets keep every literal id and meaningful description", all(
        "acceptance-%d · %s" % (i, desc) in content
        for i, desc in {1: "parent outcome", **descriptions}.items() if i != 3)
          and "acceptance-3" not in content and descriptions[3] not in content and " … " not in content, content)
    check("selected affiliation is stated once in FROM", content.count("Seed p") == 1
          and "p/acceptance-" not in content, content)

    long_meaning = "요구사항의 중요한 의미를 잘라내지 않고 보존하는 동작을 확인해요 " * 4
    panel_parent.write_text(panel_parent.read_text().replace(descriptions[2], long_meaning))
    many["walk_id"] = _walk_id(panel_repo)
    _, content = panel(many)
    expected_desc = ngr._shorten_desc(long_meaning.strip())
    check("many targets retain the existing 80-character description budget", expected_desc in content
          and expected_desc.endswith("…") and len(expected_desc) > 60, content)

    for handoff, gaps in (("none", []), ("none", [gap]), ("missing", [gap])):
        _, content = panel({"handoff": handoff, "pick": None, "alternatives": [], "unverified": gaps})
        check("Claude no-pick preserves the scope conclusion", ("검토한 범위 안" in content if not gaps else
              gap in content and "가치 있는 후속 후보가 없어요" not in content), content)
    _, content = panel(bounded, repo)
    check("Claude retains actual depth-stop diagnostics", "상한으로 중단" in content and "중단:" in content
          and "other/repo:docs/specs/x.yaml (depth)" in content, content)
    _, content = panel(_judgment(wid, pick=None, alternatives=[], unverified=[gap]), repo)
    check("Claude retains failed/external lookup, stale and uncertainty", "조회 실패 1곳" in content
          and "other/repo:docs/specs/x.yaml" in content and "실패:" in content
          and "근거 변경됨" in content and gap in content, content)
    panel_parent.write_text(panel_parent.read_text().replace("parent: null", "parent: docs/specs/c.yaml", 1))
    _, content = panel(_judgment(_walk_id(panel_repo), pick=None, alternatives=[]))
    check("Claude retains cycle diagnostics", "순환 1곳" in content and "순환:" in content, content)
    panel_parent.write_text(panel_parent.read_text().replace("parent: docs/specs/c.yaml", "parent: null", 1)
                            .replace("children: [docs/specs/c.yaml]", "children: [docs/specs/c.yaml, docs/specs/missing.yaml]"))
    _, content = panel(_judgment(_walk_id(panel_repo), pick=None, alternatives=[]))
    check("Claude retains missing-file diagnostic", "없는 파일 1곳" in content and "docs/specs/missing.yaml" in content, content)

    for invalid in (_judgment(wid, pick_via="docs/specs/never.yaml"),
                    _judgment(wid, pick_via="other/repo:docs/specs/x.yaml"),
                    {**no_seed, "unverified": [None]},
                    {**bounded, "walk_stops": [{**stop, "target": "wrong.yaml"}]}):
        baseline = _render(repo, invalid)
        for runtime in ("claude", "codex"):
            result = _render(repo, invalid, "--runtime", runtime)
            check("refusal is identical for " + runtime, result == baseline and result[0] == 1 and result[1] == "", str(result))
    for args in (("--runtime", "invalid"), ("--runtime",), ("--runtime", "claude", "extra"),
                 ("--unknown",), ("--cwd",)):
        result = _render(panel_repo, no_seed, *args)
        check("bad CLI arguments exit 2 without output", result[0] == 2 and result[1] == "", str(result))
    reversed_args = subprocess.run([sys.executable, str(_SCRIPT), "--runtime", "claude", "--cwd", panel_repo],
                                  input=json.dumps(no_seed), capture_output=True, encoding="utf-8", env=_env())
    check("runtime and cwd flags accept either order", reversed_args.returncode == 0
          and reversed_args.stdout.startswith("+" + "-" * 78 + "+\n| NEXT"), str(reversed_args))
    default_args = subprocess.run([sys.executable, str(_SCRIPT)], cwd=panel_repo,
                                 input=json.dumps(no_seed), capture_output=True, encoding="utf-8", env=_env())
    check("CLI defaults to cwd and plain output", (default_args.returncode, default_args.stdout, default_args.stderr)
          == _render(panel_repo, no_seed, "--runtime", "codex"), str(default_args))

    if failures:
        print("\n".join("FAIL " + f for f in failures))
        return 1
    print("OK: all test-next-goal-render checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
