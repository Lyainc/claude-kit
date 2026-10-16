#!/usr/bin/env python3
"""Seed read check — decision logic for hooks/seed-read-guard.sh (PreToolUse Read|Bash).

Denies (once per Seed per transcript) a Read/cat of a build-spec Seed body when
`seed-relations.py metadata` has not run for that Seed in the same transcript
(reference/seed-lifecycle.md §발견과 소비). Reads the hook JSON payload on stdin and prints a
one-line deny reason or nothing. Always exits 0: any exception, unparseable input or unreadable
file fails open. Bash detection is a heuristic and never claims to block every read.

    echo '<payload json>' | seed-read-check.py
    seed-read-check.py --self-test
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("seed_append_check", HERE / "seed-append-check.py")
_sac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sac)

TOOLS = ("seed-relations.py", "seed-lifecycle.py", "seed-id-migrate.py",
         "seed-append-check.py", "seed-read-check.py")
READERS = {"cat", "head", "tail", "sed", "less", "more", "grep", "egrep", "rg", "awk",
           "nl", "bat", "view", "yq", "for", "do", "while", "until", "xargs"}
SPLIT = re.compile(r"&&|\|\||;|\||\n")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MARKER = "Seed 본문을 읽기 전에"
META_PATH = re.compile(r'"path":\s*"([^"]+)"')


def is_seed_file(path: str) -> bool:
    try:
        if not path.endswith((".yaml", ".yml")) or _sac.is_template_path(path):
            return False
        if not os.path.isfile(path):
            return False
        with open(path, encoding="utf-8", errors="replace") as f:
            return _sac.reads_as_seed(f.read())
    except Exception:
        return False


def _words(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def bash_candidates(command: str, cwd: str) -> list[str]:
    if ".yaml" not in command and ".yml" not in command:
        return []
    if any(t in command for t in TOOLS):
        return []
    wd = cwd or os.getcwd()
    found: list[str] = []
    for seg in SPLIT.split(command):
        words = _words(seg.strip())
        while words and ASSIGN.match(words[0]):
            words.pop(0)
        if not words:
            continue
        first = words[0]
        if first == "cd":
            if len(words) != 2 or words[1].startswith("-") or "$" in words[1] or words[1].startswith("~"):
                return []
            wd = os.path.normpath(os.path.join(wd, words[1]))
            if not os.path.isdir(wd):
                return []
            continue
        if first not in READERS or (first == "sed" and any(w.startswith("-i") for w in words)):
            continue
        for w in words[1:]:
            if not w.endswith((".yaml", ".yml")):
                continue
            p = w if os.path.isabs(w) else os.path.join(wd, w)
            if any(c in p for c in "*?["):
                found.extend(sorted(glob.glob(p)))
            else:
                found.append(p)
    return found


def transcript_path(payload: dict) -> str:
    tp = payload.get("transcript_path") or ""
    agent = payload.get("agent_id") or ""
    if tp and agent:
        base = os.path.basename(tp)
        stem = base[:-6] if base.endswith(".jsonl") else base
        return os.path.join(os.path.dirname(tp), stem, "subagents", f"agent-{agent}.jsonl")
    return tp


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def scan_transcript(tp: str):
    """Return (metadata_commands, metadata_paths, denial_strings), or None when unreadable.

    metadata_paths are the `"path"` values a `seed-relations.py metadata` call printed, so a
    loop like `for s in a b; do ... metadata docs/specs/$s.yaml; done` still counts.
    """
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        return None
    commands: list[str] = []
    meta_ids: set[str] = set()
    paths: list[str] = []
    results: list[str] = []
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        content = (e.get("message") or {}).get("content") if isinstance(e.get("message"), dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if e.get("type") == "assistant" and b.get("type") == "tool_use" and b.get("name") == "Bash":
                cmd = (b.get("input") or {}).get("command")
                if isinstance(cmd, str):
                    commands.append(cmd)
                    if "seed-relations.py" in cmd and "metadata" in cmd and b.get("id"):
                        meta_ids.add(b["id"])
            elif b.get("type") == "tool_result":
                texts = list(_strings(b.get("content")))
                results.extend(t for t in texts if MARKER in t)
                if b.get("tool_use_id") in meta_ids:
                    paths.extend(m for t in texts for m in META_PATH.findall(t))
    return commands, paths, results


def decide(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    tool = payload.get("tool_name")
    if tool == "Read":
        cands = [ti.get("file_path") or ""]
    elif tool == "Bash":
        cands = bash_candidates(ti.get("command") or "", payload.get("cwd") or "")
    else:
        return ""
    seeds: list[str] = []
    for c in cands:
        c = os.path.abspath(c) if c else ""
        if c and c not in seeds and is_seed_file(c):
            seeds.append(c)
    if not seeds:
        return ""
    scanned = scan_transcript(transcript_path(payload))
    if scanned is None:
        return ""
    commands, paths, results = scanned
    unseen = []
    for s in seeds:
        base = os.path.basename(s)
        # ponytail: path-suffix and basename match; ceiling: two Seeds whose relative paths (or
        # basenames, for the command check) coincide in different repos share one metadata call;
        # upgrade: resolve each metadata call's cwd.
        if any(s == p or s.endswith("/" + p.lstrip("./")) for p in paths):
            continue
        if any("seed-relations.py" in c and "metadata" in c and base in c for c in commands):
            continue
        if any(s in r for r in results):  # already denied once for this Seed in this transcript
            continue
        unseen.append(s)
    if not unseen:
        return ""
    script = f"{PLUGIN_ROOT}/scripts/seed-relations.py"
    cmds = " ; ".join(f'python3 "{script}" metadata {shlex.quote(s)} --json' for s in unseen)
    return f"{MARKER} metadata를 먼저 실행해요: {cmds} (seed-lifecycle.md §발견과 소비)"


def _self_test() -> int:
    total = failed = 0

    def check(name, got, want_deny):
        nonlocal total, failed
        total += 1
        if bool(got) != want_deny:
            failed += 1
            print(f"FAIL: {name}: got {got!r}", file=sys.stderr)

    def tr(path, commands=(), results=(), outputs=()):
        rows = []
        for i, c in enumerate(commands):
            rows.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": c}}]}})
            if i < len(outputs):
                rows.append({"type": "user", "message": {"content": [
                    {"type": "tool_result", "tool_use_id": f"t{i}", "content": outputs[i]}]}})
        for r in results:
            rows.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "content": r}]}})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        specs = f"{d}/docs/specs"
        os.makedirs(specs)
        seed, plain = f"{specs}/x.yaml", f"{specs}/plain.yaml"
        Path(seed).write_text('skill: build-spec\ngoal: g\n')
        Path(plain).write_text("a: 1\n")
        tmpl = f"{d}/skills/build-spec/templates/SEED_SPEC.yaml"
        os.makedirs(os.path.dirname(tmpl))
        Path(tmpl).write_text('skill: build-spec\n')
        t_none, t_meta = f"{d}/t/none.jsonl", f"{d}/t/meta.jsonl"
        tr(t_none, commands=["ls"])
        tr(t_meta, commands=[f'python3 /p/seed-relations.py metadata {seed} --json'])
        # build-spec's real loop shape (#814 S2): the basename never appears in the command.
        t_loop = f"{d}/t/loop.jsonl"
        tr(t_loop, commands=['for s in x; do python3 /p/seed-relations.py metadata docs/specs/$s.yaml --json; done'],
           outputs=['{"path": "docs/specs/x.yaml", "title": "t", "lifecycle": {}}'])
        t_walk = f"{d}/t/walk.jsonl"
        tr(t_walk, commands=['python3 /p/seed-relations.py walk docs/specs/$s.yaml --json'],
           outputs=['{"path": "docs/specs/x.yaml"}'])
        t_denied = f"{d}/t/denied.jsonl"
        tr(t_denied, results=[f"{MARKER} metadata를 먼저 실행해요: ... {seed} ..."])
        # subagent layout: parent transcript t/main.jsonl, subagent at t/main/subagents/agent-a1.jsonl
        t_main = f"{d}/t/main.jsonl"
        tr(t_main, commands=[f'python3 /p/seed-relations.py metadata {seed} --json'])
        tr(f"{d}/t/main/subagents/agent-a1.jsonl", commands=["ls"])
        tr(f"{d}/t/main/subagents/agent-a2.jsonl", commands=[f'python3 /p/seed-relations.py metadata {seed} --json'])

        def read(p, t):
            return {"tool_name": "Read", "tool_input": {"file_path": p}, "transcript_path": t}

        def bash(c, t, **kw):
            return {"tool_name": "Bash", "tool_input": {"command": c}, "transcript_path": t, "cwd": d, **kw}

        check("read seed unseen", decide(read(seed, t_none)), True)
        check("read seed seen", decide(read(seed, t_meta)), False)
        check("read seed already denied once", decide(read(seed, t_denied)), False)
        check("read seed, loop metadata output", decide(read(seed, t_loop)), False)
        check("read seed, walk output is not metadata", decide(read(seed, t_walk)), True)
        check("bash sed -i is an edit", decide(bash("sed -i '' s/a/b/ docs/specs/x.yaml", t_none)), False)
        check("bash sed -n still reads", decide(bash("sed -n 1,5p docs/specs/x.yaml", t_none)), True)
        check("read non-seed yaml", decide(read(plain, t_none)), False)
        check("read template", decide(read(tmpl, t_none)), False)
        check("read non-yaml", decide(read(f"{d}/nope.txt", t_none)), False)
        check("bash cd && cat", decide(bash("cd docs/specs && cat x.yaml", t_none, cwd=d)), True)
        check("bash cd abs", decide(bash(f"cd {specs} && head -5 x.yaml", t_none)), True)
        r = decide(bash("for f in docs/specs/*.yaml; do cat $f; done", t_none))
        check("bash for-glob", r, True)
        check("bash for-glob lists only seeds", "plain.yaml" in r or seed not in r, False)
        check("bash seed-relations metadata", decide(bash(f"python3 /p/seed-relations.py metadata {seed} --json", t_none)), False)
        check("bash git diff", decide(bash("git diff docs/specs/x.yaml", t_none)), False)
        check("bash unresolvable cd", decide(bash("cd $HOME/zz && cat x.yaml", t_none)), False)
        check("bash cd missing dir", decide(bash("cd nowhere && cat docs/specs/x.yaml", t_none)), False)
        check("bash cat seen", decide(bash("cat docs/specs/x.yaml", t_meta)), False)
        check("bash no yaml", decide(bash("cat README.md", t_none)), False)
        check("subagent, metadata only in parent", decide({**read(seed, t_main), "agent_id": "a1"}), True)
        check("subagent, metadata in subagent", decide({**read(seed, t_main), "agent_id": "a2"}), False)
        check("main, metadata in main", decide(read(seed, t_main)), False)
        check("missing transcript", decide(read(seed, f"{d}/t/missing.jsonl")), False)
        check("no transcript_path", decide({"tool_name": "Read", "tool_input": {"file_path": seed}}), False)
        check("other tool", decide({"tool_name": "Grep", "tool_input": {}}), False)
        check("reason has command", "seed-relations.py" in decide(read(seed, t_none)), True)

    total += 1
    import subprocess
    p = subprocess.run([sys.executable, str(Path(__file__).resolve())], input="not json{",
                       capture_output=True, text=True)
    if p.stdout or p.returncode != 0:
        failed += 1
        print("FAIL: garbage stdin", file=sys.stderr)

    if failed:
        print(f"FAIL: {failed}/{total} seed-read-check case(s) failed", file=sys.stderr)
        return 1
    print(f"OK: all {total} seed-read-check self-test cases passed")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict):
            reason = decide(payload)
            if reason:
                print(reason)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
