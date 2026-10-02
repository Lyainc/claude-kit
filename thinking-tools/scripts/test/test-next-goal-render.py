#!/usr/bin/env python3
"""Tests for next-goal-render.py (#792) — the pick rendered from next-goal's judgment JSON.

Covers: FROM's edge path and TRACE's counts come from a fresh walk, never from the JSON; a `via`
the walk never visited is refused; another repo's Seed cannot be the pick; a Seed or HEAD change
after the walk marks the judgment stale; a missing Seed handoff reads differently from "no
candidate"; no Seed in play keeps the three-line shape; the same JSON renders identically twice.

Usage: python3 thinking-tools/scripts/test/test-next-goal-render.py
Exit codes: 0 all passed, 1 one or more failed
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "next-goal-render.py"
_RELATIONS = Path(__file__).resolve().parents[1] / "seed-relations.py"


def _repo():
    d = tempfile.mkdtemp(prefix="test-next-goal-render-")
    atexit.register(shutil.rmtree, d, ignore_errors=True)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    specs = Path(d) / "docs" / "specs"
    specs.mkdir(parents=True)
    (specs / "p.yaml").write_text(
        "skill: build-spec\ntarget: parent\nrelations:\n  parent: null\n  refines: []\n"
        "  depends_on: []\n  children: [docs/specs/c.yaml, other/repo:docs/specs/x.yaml]\n"
        "success_criteria:\n  - id: ac1\n    description: parent outcome\n", encoding="utf-8")
    (specs / "c.yaml").write_text(
        "skill: build-spec\ntarget: child\nrelations:\n  parent: docs/specs/p.yaml\n"
        "  refines: [ac1]\n  link_reason: settles ac1\n  depends_on: []\n  children: []\n"
        "success_criteria:\n  - id: ac1\n    description: child outcome\n", encoding="utf-8")
    return d


def _walk_id(repo):
    p = subprocess.run([sys.executable, str(_RELATIONS), "walk", "docs/specs/c.yaml"], cwd=repo,
                       capture_output=True, encoding="utf-8", env=_env())
    first = p.stdout.splitlines()[0].split("\t")
    return next(f[3:] for f in first if f.startswith("id="))


def _env():
    return {**os.environ, "GH_BIN": "/nonexistent/gh"}


def _render(repo, judgment):
    p = subprocess.run([sys.executable, str(_SCRIPT), "--cwd", repo], input=json.dumps(judgment),
                       capture_output=True, encoding="utf-8", env=_env())
    return p.returncode, p.stdout, p.stderr


def _judgment(walk_id, pick_via="docs/specs/p.yaml", **over):
    j = {
        "seed": "docs/specs/c.yaml", "walk_id": walk_id, "handoff": "named",
        "pick": {"title": "부모 ac1 마무리", "via": pick_via, "targets": ["ac1"],
                 "evidence": "ac1 검사 스크립트가 아직 없음", "startable": "yes",
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
    check("FROM path comes from the walk", "Seed edge: 출발 →parent docs/specs/p.yaml (ac1)" in out, out)
    check("TRACE counts come from the walk", "출발 docs/specs/c.yaml" in out and "방문 " in out
          and "조회 실패 1곳" in out, out)
    check("not stale on a fresh walk", "근거 변경됨" not in out, out)
    code2, out2, _ = _render(repo, _judgment(wid))
    check("same JSON renders identically", (code2, out2) == (code, out))

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
          and "TRACE" not in out and "가치 있는 후속 후보가 없어요" in out, f"{code} {out!r} {err!r}")

    code, _, err = _render(repo, {"handoff": "none", "pick": {"title": "t", "via": "docs/specs/c.yaml",
                                  "evidence": "e", "startable": "yes", "startable_reason": "r",
                                  "user_change": "u"}, "alternatives": []})
    check("Seed via without a walk refused", code == 1, err)

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

    if failures:
        print("\n".join("FAIL " + f for f in failures))
        return 1
    print("OK: all test-next-goal-render checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
