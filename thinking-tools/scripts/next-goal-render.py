#!/usr/bin/env python3
"""next-goal-render.py — print next-goal's pick from its structured judgment (#792).

Why this exists: next-goal's pick reached the user as free text, so the path from the named Seed
to the pick could be narrated after the fact, and a second surface (the optional seed-board mod)
would have had to re-derive the choice. Now next-goal writes its judgment once as JSON and this
script renders the NEXT/FROM/SKIPPED lines (plus TRACE for a Seed or uncertainty) from it.
The terminal and the mod read the same JSON, so the UI can never change what was chosen.

What it does not do, on purpose:
  - It never judges. Candidates, decisions and reasons come from next-goal; this only checks the
    judgment's shape, that every Seed path it cites was really walked, and the selected Seed's
    current eligibility. Missing eligibility, required review, or an excluded target refuse a pick.
  - It never trusts a path or a count the judgment states. It re-runs `seed-relations.py walk`
    on the judgment's Seed: FROM's edge path and TRACE's counts come from that walk, and a `via`
    naming a Seed the walk never visited is refused (exit 1) instead of being printed.
    A stale judgment cannot select a Seed or item that became ineligible after its original walk.
  - It never writes anything.

Input (stdin, JSON):
    {
      "seed": "docs/specs/x.yaml" | null,       # the named Seed (repo-root relative or absolute)
      "walk_id": "<id from the WALK line>" | null,   # carries the walk's limits (~dNnM)
      "handoff": "named" | "missing" | "none",  # missing = the session worked from a Seed but
                                                #   no path was handed over (not "no candidate")
      "pick": null | {
        "title": str, "via": "<walked Seed key>" | "session" | "backlog" | "issue:#N",
        "targets": ["constraint-1", "acceptance-2"], "evidence": str,
        "startable": "yes" | "unknown", "startable_reason": str,
        "user_change": str, "note": str (optional, e.g. the maintenance streak)
      },
      "alternatives": [{"title": str, "via": ..., "decision":
                        "held" | "below-floor" | "done" | "external" | "unverified",
                        "reason": str}],
      "unverified": [str],                     # nonempty facts about unevaluated scope
      "walk_stops": [{"from": str, "edge": str, "target": str, "reason": "depth" | "nodes"}]
                                                # optional STOP assertions, checked against walk
    }

`targets` are LOCAL item ids of the `via` Seed (reference/identifiers.md). For a walked Seed
`via` each renders as its full identifier plus the Seed's own description
(`foo/constraint-1 · DB 스키마 생성`, `owner/repo:foo/constraint-1 · ...` across repos); a target the
Seed does not define is refused, as is a legacy `c1`/`ac1` that matches only by canonical form
(the Seed needs `seed-id-migrate.py`, or the target needs the Seed's own spelling). For
`session`, `backlog` and `issue:#N` the targets are free text and print as given.

Usage:
    next-goal-render.py [--cwd <repo>] < judgment.json

Exit codes: 0 rendered, 1 judgment refused (reason on stderr, nothing on stdout), 2 bad usage.
Stdlib only; Python 3.9.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NON_SEED_VIA = ("session", "backlog")
DECISIONS = ("held", "below-floor", "done", "external", "unverified")
DECISION_KO = {"held": "보류", "below-floor": "바닥 미달", "done": "이미 충족",
               "external": "다른 레포 — 링크만", "unverified": "미확인"}
REL_KO = {"start": "출발", "ancestor": "조상", "ancestor-child": "조상의 자식",
          "descendant": "하위", "predecessor": "선행"}


class Refused(Exception):
    pass


def _load_relations():
    spec = importlib.util.spec_from_file_location("seed_relations",
                                                  os.path.join(HERE, "seed-relations.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _one_line(s):
    return " ".join(s.split())


def _need_str(obj, key, where):
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip():
        raise Refused(f"{where}.{key}: 비어 있지 않은 문자열이어야 해요")
    # Normalized in place so every line and REFUSED message stays single-line.
    obj[key] = _one_line(v)
    return obj[key]


def _is_seed_via(via):
    return via not in NON_SEED_VIA and not via.startswith("issue:")


def validate(j):
    if not isinstance(j, dict):
        raise Refused("판단은 JSON 객체여야 해요")
    handoff = j.get("handoff")
    if handoff not in ("named", "missing", "none"):
        raise Refused("handoff: named | missing | none 중 하나여야 해요")
    seed, walk_id = j.get("seed"), j.get("walk_id")
    if handoff == "named" and not (isinstance(seed, str) and seed and isinstance(walk_id, str)):
        raise Refused("handoff=named면 seed와 walk_id(WALK 줄의 id)가 있어야 해요")
    if handoff != "named" and (seed or walk_id):
        raise Refused("Seed를 넘겨받지 않았으면(handoff≠named) seed/walk_id를 비워야 해요")
    pick = j.get("pick")
    if pick is not None:
        if not isinstance(pick, dict):
            raise Refused("pick: 객체 또는 null이어야 해요")
        for k in ("title", "via", "evidence", "startable_reason", "user_change"):
            _need_str(pick, k, "pick")
        if pick.get("startable") not in ("yes", "unknown"):
            raise Refused("pick.startable: yes | unknown — 착수할 수 없는 후보는 pick이 아니라 held예요")
        if not isinstance(pick.get("targets", []), list):
            raise Refused("pick.targets: 목록이어야 해요")
        if _is_seed_via(pick["via"]) and not pick.get("targets"):
            raise Refused("pick.targets: Seed 후보에는 적용할 항목 id가 하나 이상 필요해요")
    alts = j.get("alternatives", [])
    if not isinstance(alts, list):
        raise Refused("alternatives: 목록이어야 해요")
    for i, a in enumerate(alts):
        where = f"alternatives[{i}]"
        if not isinstance(a, dict):
            raise Refused(f"{where}: 객체여야 해요")
        for k in ("title", "via", "reason"):
            _need_str(a, k, where)
        if a.get("decision") not in DECISIONS:
            raise Refused(f"{where}.decision: {' | '.join(DECISIONS)} 중 하나여야 해요")
    if not isinstance(j.get("unverified", []), list):
        raise Refused("unverified: 목록이어야 해요")
    j["unverified"] = [_need_str({"text": u}, "text", f"unverified[{i}]")
                       for i, u in enumerate(j.get("unverified", []))]
    stops = j.get("walk_stops", [])
    if not isinstance(stops, list) or (stops and handoff != "named"):
        raise Refused("walk_stops: named walk의 STOP 목록이어야 해요")
    for i, stop in enumerate(stops):
        if not isinstance(stop, dict):
            raise Refused(f"walk_stops[{i}]: 객체여야 해요")
        for k in ("from", "edge", "target", "reason"):
            _need_str(stop, k, f"walk_stops[{i}]")
    if pick is not None and isinstance(pick.get("note"), str):
        pick["note"] = _one_line(pick["note"])
    if handoff != "named":
        for c in ([pick] if pick else []) + alts:
            if _is_seed_via(c["via"]):
                raise Refused(f"'{c['title']}': Seed를 걷지 않았는데 via가 Seed 경로예요")


def _walk(rel, j, cwd):
    seed = j["seed"]
    path = seed if os.path.isabs(seed) else os.path.join(cwd, seed)
    if not os.path.isfile(path):
        raise Refused(f"seed 파일이 없어요: {seed}")
    m = re.search(r"~d(\d+)n(\d+)$", j["walk_id"])
    if not m:
        raise Refused("walk_id에 탐색 상한(~dNnM)이 없어요 — WALK 줄의 id를 그대로 옮겨 주세요")
    return rel.walk(path, max_depth=int(m.group(1)), max_nodes=int(m.group(2)))


def _edge_path(node):
    """`start →parent p.yaml →children s.yaml`, from the walk itself."""
    parts = ["출발" if node.get("via") else f"출발 {node['key']}"]
    for edge, key in node.get("via") or []:
        parts.append(f"→{edge} {key}")
    return " ".join(parts)


def _check_vias(j, nodes):
    pick = j.get("pick")
    for c in ([pick] if pick else []) + j.get("alternatives", []):
        via = c["via"]
        if not _is_seed_via(via):
            continue
        node = nodes.get(via)
        if node is None:
            raise Refused(f"'{c['title']}': via {via}는 이번 walk가 방문하지 않은 Seed예요 — "
                          f"탐색하지 않은 경로는 적지 않아요")
        external = node.get("status", "").startswith("external")
        if c is pick and external:
            raise Refused(f"'{c['title']}': 다른 레포 Seed는 여기서 판정하지 않아요 (pick 불가)")
        if c is pick:
            eligibility = node.get("eligibility")
            if not isinstance(eligibility, dict):
                raise Refused(f"'{c['title']}': {via} 후보 자격 미확인 — 다시 탐색하고 검토해 주세요")
            excluded = eligibility.get("excluded_items")
            if (eligibility.get("eligible") is not True
                    or eligibility.get("review_required") is not False
                    or not isinstance(excluded, list)
                    or any(not isinstance(i, str) for i in excluded)):
                reason = eligibility.get("reason") or "후보 자격 미확인"
                raise Refused(f"'{c['title']}': {via}는 후보로 고를 수 없어요 — {reason}")
            for target in c.get("targets", []):
                if isinstance(target, str) and target.strip() in excluded:
                    raise Refused(f"target {target}: {via}의 제외된 항목은 후보로 고를 수 없어요")
        if c is not pick and external and c["decision"] != "external":
            raise Refused(f"'{c['title']}': 다른 레포 Seed의 decision은 external이어야 해요")


def _render_targets(rel, via, node, targets):
    """Free text for non-Seed via; for a walked Seed, `<qualified id> · <description>` per target."""
    if not _is_seed_via(via):
        return [str(t) for t in targets]
    defined = node.get("item_desc") or {}
    out = []
    for t in targets:
        if not isinstance(t, str) or not t.strip():
            raise Refused("pick.targets: 비어 있지 않은 문자열 목록이어야 해요")
        t = t.strip()
        if t not in defined:
            twin = next((i for i in defined if rel.canonical_id(i) == rel.canonical_id(t)), None)
            if twin is not None:
                raise Refused(f"target {t}: {via} Seed는 이 항목을 '{twin}'로 정의해요 — 그대로 적어 주세요. "
                              f"옛 id(c<N>/ac<N>) Seed는 scripts/seed-id-migrate.py <seed> --apply로 옮겨요")
            raise Refused(f"target {t}: {via} Seed에 없는 항목이에요 — 정의된 id: "
                          f"{', '.join(defined) or '(없음)'}. 없는 항목은 적지 않아요")
        desc = " ".join(str(defined[t] or "").split())
        out.append(rel.qualified_id(via, t) + (f" · {desc}" if desc else ""))
    return out


def _from_line(j, nodes, rel, incomplete):
    pick = j.get("pick")
    if pick is None:
        if j["handoff"] == "missing":
            return "Seed 경로를 넘겨받지 못해 Seed 후보는 확인 못 함"
        if incomplete:
            return "선택 없음 — 미평가 영역이 남아 후보 부재는 확정 못 함"
        return "없음 — 검토한 범위 안에 가치 있는 후속 후보가 없어요"
    via = pick["via"]
    if via == "session":
        src = "이번 세션 후속"
    elif via == "backlog":
        src = "백로그"
    elif via.startswith("issue:"):
        src = via[len("issue:"):]
    else:
        src = f"Seed edge: {_edge_path(nodes[via])}"
    targets = _render_targets(rel, via, nodes.get(via, {}), pick.get("targets") or [])
    out = src + (f" ({'; '.join(targets)})" if targets else "")
    out += f" — 미충족 근거: {pick['evidence']}"
    out += f" · 착수 {'가능' if pick['startable'] == 'yes' else '미확인'}: {pick['startable_reason']}"
    out += f" · 사용자 변화: {pick['user_change']}"
    if pick.get("note"):
        out += f" · {pick['note']}"
    return out


def _skipped_line(j):
    alts = j.get("alternatives", [])
    if not alts:
        return "없음"
    # A Seed alternative keeps its path or coordinate: for another repo's Seed that is the link.
    return "; ".join(f"{a['title']}{' · ' + a['via'] if _is_seed_via(a['via']) else ''} "
                     f"({DECISION_KO[a['decision']]}: {a['reason']})" for a in alts)


def _trace_line(j, data, current_id):
    unv = j.get("unverified", [])
    suffix = " · 미확인: " + ", ".join(unv) if unv else ""
    if j["handoff"] == "missing":
        return "Seed 경로 인계 누락 — 후보 없음과 달라요. Seed를 지정하면 다시 탐색해요" + suffix
    if data is None:
        return "Seed 탐색 없음" + suffix
    s, w = data["summary"], data["walk"]
    parts = [f"출발 {w['start']}",
             f"방문 {s['visited']}개 (깊이≤{w['max_depth']}, 상한 {w['max_nodes']}개)"]
    parts.append("방문 대상: " + ", ".join(
        f"{n['key']} (깊이 {n['depth']}, {n['status']})" for n in data["nodes"]))
    if s.get("stopped"):
        parts.append(f"상한으로 중단 {s['stopped']}곳")
        parts.extend(f"중단: {r['from']} →{r['edge']} {r['target']} ({r['reason']})"
                     for r in data["stops"])
    if s.get("cycles"):
        parts.append(f"순환 {s['cycles']}곳 끊음")
    if s.get("failed"):
        parts.append(f"조회 실패 {s['failed']}곳")
    if s.get("notfound"):
        parts.append(f"없는 파일 {s['notfound']}곳")
    if unv:
        parts.append("미확인: " + ", ".join(unv))
    stale = "" if current_id == j["walk_id"] else \
        f" · [근거 변경됨: 판단은 {j['walk_id']} 기준, 지금은 {current_id} — 다시 판단 필요]"
    return " · ".join(parts) + f" · 근거 {w['id']} @ {w['at']}" + stale


def render(j, cwd):
    validate(j)
    lines = []
    data, nodes, current_id = None, {}, None
    rel = _load_relations()
    if j["handoff"] == "named":
        data = _walk(rel, j, cwd)
        nodes = {n["key"]: n for n in data["nodes"]}
        current_id = data["walk"]["id"]
        _check_vias(j, nodes)
        for i, stop in enumerate(j.get("walk_stops", [])):
            if not any(all(stop[k] == actual[k] for k in ("from", "edge", "target", "reason"))
                       for actual in data["stops"]):
                raise Refused(f"walk_stops[{i}]: {stop['target']} ({stop['reason']})는 "
                              "이번 walk의 중단 기록과 달라요 — 방문·중단 대상을 다시 확인해 주세요")
    incomplete = bool(j["unverified"] or any(a["decision"] == "unverified"
                      for a in j.get("alternatives", [])) or (data and (
                          any(data["summary"].get(k) for k in
                              ("stopped", "failed", "notfound", "cycles", "external"))
                          or current_id != j["walk_id"])))
    pick = j.get("pick")
    lines.append(f"NEXT     · {pick['title'] if pick else '없음'}")
    lines.append(f"FROM     · {_from_line(j, nodes, rel, incomplete)}")
    lines.append(f"SKIPPED  · {_skipped_line(j)}")
    if j["handoff"] != "none" or j["unverified"]:
        lines.append(f"TRACE    · {_trace_line(j, data, current_id)}")
    return lines


def main(argv):
    cwd = os.getcwd()
    args = argv[1:]
    if args[:1] == ["--cwd"] and len(args) == 2:
        cwd = args[1]
    elif args:
        print("usage: next-goal-render.py [--cwd <repo>] < judgment.json", file=sys.stderr)
        return 2
    try:
        j = json.loads(sys.stdin.read())
    except ValueError as exc:
        print(f"[next-goal-render REFUSED] JSON이 아니에요: {exc}", file=sys.stderr)
        return 1
    try:
        lines = render(j, cwd)
    except Refused as exc:
        print(f"[next-goal-render REFUSED] {exc}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
