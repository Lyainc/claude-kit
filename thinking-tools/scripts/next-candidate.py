#!/usr/bin/env python3
"""next-candidate — the comparison set completion-condition's ranking cannot compute for itself.

Why this exists. Phase 1 picks the next session's candidate from "this session's high-ROI
follow-ups". That pool is closed: a session that just finished polishing one module leaves
behind that module's nits, and ranking nits by ROI still yields a nit. The chain therefore
decays the further along it runs — the judgment was never bad, the comparison set was empty.

So this prints what the ranking is missing, deterministically:
  1. chain depth — how many consecutive recent commits stayed in the same top-level area.
     A number, not a vibe. Depth is the decay signal the routine had no way to see.
  2. the open backlog, with labels and staleness.
  3. which open issues reference paths this session actually touched — the "combines with
     what just shipped" axis, where doing it now is cheaper because the context is hot.

**Data only, no verdicts.** Everything here is something the skill cannot derive; what to do
with it (the impact floor, when to re-pick, disclosing the pool) lives in SKILL.md and only
there. Shipping the same rule in both places is duplication, not inheritance.

Read-only, stdlib only, never fails loudly: any missing piece is reported as a labelled blank
section rather than an error, because this runs inside a hook and a crash there would break
skill invocation for no safety gain. A lookup that *failed* never renders as an empty
backlog — the two are different facts and the caller must be able to tell them apart.

Standalone use: python3 scripts/next-candidate.py [--hours N] [--commits N] [--cwd PATH]
"""

import argparse
import json
import os
import subprocess
import sys
import time

DEPTH_ALARM = 3  # consecutive same-area commits at which the pool is presumed exhausted


def run(cmd, cwd=None, timeout=12):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.stdout if p.returncode == 0 else ""
    except Exception:
        return ""


def top_areas(paths):
    """Top-level area of each path. A bare root file is its own area, not a shared one."""
    out = set()
    for p in paths:
        if not p:
            continue
        head = p.split("/")[0]
        out.add(head if "/" in p else f"·{head}")
    return out


def chain_depth(cwd, n_commits):
    """How many of the most recent commits, consecutively, share an area with the newest one.

    The top-level directory is a proxy for "same thread", and it is repo-shaped. It reads true
    where top-level dirs are genuine areas — validated on claude-kit 2026-07-24, which returns
    depth 3 at e9d98ee (three consecutive docs/ commits) and 2 at 91ab783. It reads LOW where
    top-level dirs are layers of one thing: a repo that splits a single thread across
    rules/ + policies/ + skills/ reports depth 1 for three commits of one piece of work.

    So a low depth is never an all-clear. It is an *additional* trigger for widening the pool,
    never a gate on the impact floor — the skill runs the floor test regardless, which is what
    keeps this limitation from mattering.
    """
    raw = run(["git", "log", f"-{n_commits}", "--name-only", "--pretty=format:%x00%h %s"], cwd)
    if not raw:
        return 0, [], []
    commits = []
    for block in raw.split("\x00"):
        block = block.strip("\n")
        if not block:
            continue
        lines = block.split("\n")
        header, files = lines[0], [f for f in lines[1:] if f.strip()]
        commits.append((header, top_areas(files)))
    if not commits:
        return 0, [], []
    head_areas = commits[0][1]
    depth = 0
    for _, areas in commits:
        if areas & head_areas:
            depth += 1
        else:
            break
    return depth, sorted(head_areas), [h for h, _ in commits[:depth]]


def changed_paths(cwd, hours):
    raw = run(["git", "log", f"--since={hours} hours ago", "--name-only", "--pretty=format:"], cwd)
    return sorted({ln.strip() for ln in raw.splitlines() if ln.strip()})


def has_github_remote(cwd):
    return "github.com" in run(["git", "remote", "-v"], cwd)


def open_issues(cwd):
    """Return (issues, failure_reason). A failure is never reported as an empty backlog.

    "No open issues" and "could not look" lead to opposite decisions — the first says the
    backlog is genuinely exhausted, the second says nothing at all — so collapsing them into
    one blank section is how a lookup failure gets read as a clean result.
    """
    if not has_github_remote(cwd):
        return [], "no-remote"
    if not _which("gh"):
        return [], "gh-missing"

    try:
        p = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--limit", "100",
             "--json", "number,title,body,labels,updatedAt"],
            cwd=cwd, capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return [], "gh-failed"

    if p.returncode != 0:
        return [], "gh-failed"
    try:
        return (json.loads(p.stdout) if p.stdout.strip() else []), None
    except Exception:
        return [], "gh-failed"


def _which(binary):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(d, binary)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


BACKLOG_UNAVAILABLE = {
    "no-remote": "열린 이슈: 조회 안 함 — GitHub 리모트가 없어요.",
    "gh-missing": "열린 이슈: 조회 못 함 — gh CLI가 설치돼 있지 않아요. (백로그가 비었다는 뜻이 아니에요)",
    "gh-failed": "열린 이슈: 조회 실패 — gh 인증 만료나 권한 문제일 수 있어요. (백로그가 비었다는 뜻이 아니에요)",
}


def age_days(iso):
    try:
        t = time.mktime(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        return max(0, int((time.time() - t) // 86400))
    except Exception:
        return -1


def link_terms(paths):
    """Search terms specific enough that a hit means something.

    Bare filename stems are NOT usable here: README, SKILL, CLAUDE, plugin match every issue
    in a repo like this one, and a link signal that fires on everything discriminates never.
    Measured on claude-kit 2026-07-24: stem matching linked 5 of 5 open issues; requiring a
    path separator linked 3, all genuine. So: full paths, and directory prefixes with at
    least two segments. Every term contains a '/'.
    """
    terms = set()
    for p in paths:
        if "/" not in p:
            continue
        terms.add(p)
        parts = p.split("/")
        for cut in range(2, len(parts)):
            terms.add("/".join(parts[:cut]))
    return terms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=12, help="window for 'this session changed'")
    ap.add_argument("--commits", type=int, default=12, help="commits inspected for chain depth")
    ap.add_argument("--cwd", default=os.getcwd())
    args = ap.parse_args()

    cwd = args.cwd
    if not run(["git", "rev-parse", "--is-inside-work-tree"], cwd).strip():
        return 0

    out = []
    depth, areas, shas = chain_depth(cwd, args.commits)
    if depth:
        out.append(f"체인 깊이 {depth} — 최근 커밋 {depth}개가 연속으로 같은 영역({', '.join(areas)})")
        if depth >= DEPTH_ALARM:
            out.append(f"  깊이 {DEPTH_ALARM} 이상 — 같은 영역이 연속으로 이어진 구간이에요.")

    paths = changed_paths(cwd, args.hours)
    issues, reason = open_issues(cwd)

    if issues:
        out.append(f"\n열린 이슈 {len(issues)}개 (백로그 전체):")
        for it in sorted(issues, key=lambda x: -x["number"]):
            labels = ",".join(l["name"] for l in it.get("labels", []))
            d = age_days(it.get("updatedAt", ""))
            out.append(
                f"  #{it['number']:<5} [{labels or '-'}] {d}d전 {it['title'][:64]}"
            )
    elif reason:
        out.append("\n" + BACKLOG_UNAVAILABLE[reason])
    else:
        out.append("\n열린 이슈: 0개 — 백로그가 실제로 비어 있어요.")

    if paths and issues:
        terms = link_terms(paths)
        hits = []
        for it in issues:
            text = f"{it.get('title','')}\n{it.get('body','') or ''}"
            matched = sorted({t for t in terms if t and t in text})[:3]
            if matched:
                hits.append((it["number"], it["title"], matched))
        if hits:
            out.append("\n직전 작업과 연계되는 이슈 (본문이 이번에 바꾼 경로를 언급):")
            for num, title, matched in hits:
                out.append(f"  #{num:<5} {title[:56]}  ← {', '.join(matched)}")

    if out:
        print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
