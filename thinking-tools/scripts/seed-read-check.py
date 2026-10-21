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
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("seed_append_check", HERE / "seed-append-check.py")
_sac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sac)

TOOLS = ("seed-relations.py", "seed-lifecycle.py", "seed-id-migrate.py",
         "seed-append-check.py", "seed-read-check.py")
READERS = {"cat", "head", "tail", "sed", "less", "more", "grep", "egrep", "rg", "awk",
           "nl", "bat", "view", "yq", "for", "do", "while", "until", "xargs"}
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
SED_INPLACE = re.compile(r"-[A-Za-z]*i")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MARKER = "Seed 본문을 읽기 전에"
LAUNCHERS = {"uv", "run", "bun", "env", "exec", "sh", "bash", "do", "then", "else", "if", "while", "until", "time", "nohup"}
DENY_HEAD = MARKER + " metadata를 먼저 실행해요: python3 "  # the guard's own deny output opens like this
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


def _strip_heredocs(command: str) -> str:
    """Drop heredoc bodies: their lines are data, not commands."""
    out: list[str] = []
    pending: list[str] = []
    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending = [m.group(2) for m in HEREDOC.finditer(line)]
    return "\n".join(out)


def _segments(command: str) -> list[list[str]]:
    """Split a command into simple-command word lists at unquoted `&&`, `||`, `;`, `|`, `&`,
    newline, parentheses, `$(` and backticks; quotes keep `|`/`;` literal and `#` starts a comment."""
    segs: list[str] = []
    cur: list[str] = []
    quote = ""
    i, n = 0, len(command)
    while i < n:
        c = command[i]
        if quote:
            cur.append(c)
            if c == "\\" and quote == '"' and i + 1 < n:
                cur.append(command[i + 1])
                i += 1
            elif c == quote:
                quote = ""
        elif c == "\\" and i + 1 < n:
            cur.append(command[i:i + 2])
            i += 1
        elif c in "'\"":
            quote = c
            cur.append(c)
        elif c == "#" and (not cur or cur[-1].isspace()):
            while i < n and command[i] != "\n":
                i += 1
            continue
        elif c in ";|&()`\n":
            if c == "&" and command[i - 1:i] in (">", "<"):  # `2>&1`, `&>` are redirects
                cur.append(c)
            else:
                segs.append("".join(cur))
                cur = []
        else:
            cur.append(c)
        i += 1
    segs.append("".join(cur))
    out = []
    for seg in segs:
        seg = seg.strip().removesuffix("$").strip()
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        while words and ASSIGN.match(words[0]):
            words.pop(0)
        if words:
            out.append(words)
    return out


def _tool_call(words: list[str]) -> int:
    """Index of a Seed tool script named as the program or the interpreter's script, else -1."""
    i = 0  # skip launchers and their flags; a tool name later in the arguments is just an argument
    while i < len(words) and (words[i].startswith("-") or os.path.basename(words[i]) in LAUNCHERS
                              or os.path.basename(words[i]).startswith("python")):
        i += 1
    return i if i < len(words) and os.path.basename(words[i]) in TOOLS else -1


def bash_candidates(command: str, cwd: str) -> list[str]:
    if ".yaml" not in command and ".yml" not in command:
        return []
    segments = _segments(_strip_heredocs(command))
    has_tool = any(_tool_call(w) >= 0 for w in segments)
    wd = cwd or os.getcwd()
    found: list[str] = []
    for words in segments:
        first = os.path.basename(words[0])
        if first == "cd":
            if len(words) != 2 or words[1].startswith("-") or "$" in words[1] or words[1].startswith("~"):
                return []
            wd = os.path.normpath(os.path.join(wd, words[1]))
            if not os.path.isdir(wd):
                return []
            continue
        # A segment running a Seed tool is that tool's own read. A loop header is skipped when the
        # command runs one, since its body is usually the tool.
        # ponytail: `walk a.yaml; for f in x.yaml; do cat $f; done` still passes; upgrade: parse loops.
        if _tool_call(words) >= 0 or (has_tool and first in ("for", "while", "until")):
            continue
        if first not in READERS or (first == "sed" and any(
                w.startswith("--in-place") or SED_INPLACE.match(w) for w in words[1:])):
            continue
        prev = ""
        for w in words[1:]:
            target, prev = prev in (">", ">>") or w.startswith(">"), w
            if target or not w.endswith((".yaml", ".yml")):  # a redirect target is written, not read
                continue
            w = os.path.expanduser(w)
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


def _metadata_call(command: str, cwd: str):
    """(literal Seed path or None, cwd) when a command runs `seed-relations.py metadata|read`."""
    segments = _segments(_strip_heredocs(command))
    moved = any(os.path.basename(w[0]) == "cd" for w in segments)
    for words in segments:
        i = _tool_call(words)
        if i < 0 or os.path.basename(words[i]) != "seed-relations.py":
            continue
        args = [w for w in words[i + 1:] if not w.startswith("-")]
        if len(args) < 2 or args[0] not in ("metadata", "read"):
            continue
        target = args[1]
        if moved or any(c in target for c in "$*?[`~") or not (cwd or os.path.isabs(target)):
            return None, cwd  # the file name is not literal here; match by the printed path
        return os.path.realpath(os.path.join(cwd, target)), cwd
    return None


def scan_transcript(tp: str):
    """Return (metadata calls, denial strings), or None when unreadable.

    A metadata call is (printed path, literal Seed path or None, cwd) for a Bash call whose
    command ran `seed-relations.py metadata|read` and whose output printed a `"path"`, so a loop
    like `for s in a b; do ... metadata docs/specs/$s.yaml; done` still counts and a failed call
    (no JSON printed) does not. A denial is a tool_result opening with the guard's own deny text.
    A Codex rollout carries the same facts under `payload`: each shell command it ran is a
    `CommandExecution` item (command, file:// cwd, aggregated_output), and a denied command
    leaves only the tool output `Command blocked by PreToolUse hook: <reason>`.
    """
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        return None
    meta_calls: dict[str, tuple] = {}
    calls: list[tuple] = []
    results: list[str] = []
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        p = e.get("payload")
        if isinstance(p, dict):
            # shortcut: only code-mode `exec` → exec_command records were observed (codex-cli 0.163.0);
            # parse other Codex tool shapes if a rollout shows them.
            it = p.get("item") if p.get("type") == "item_completed" else None
            if isinstance(it, dict) and it.get("type") == "CommandExecution":
                argv = it.get("command")
                cmd = argv[2] if isinstance(argv, list) and len(argv) == 3 and argv[1] in ("-lc", "-c") \
                    else shlex.join(argv) if isinstance(argv, list) else argv
                cwd = unquote(urlparse(it.get("cwd") or "").path)
                call = _metadata_call(cmd, cwd) if isinstance(cmd, str) else None
                if call:
                    literal, cwd = call
                    calls.extend((m, literal, cwd) for m in META_PATH.findall(str(it.get("aggregated_output") or "")))
            elif p.get("type") in ("custom_tool_call_output", "function_call_output"):
                results.extend(t for t in _strings(p.get("output")) if DENY_HEAD in t[:300])
            continue
        content =(e.get("message") or {}).get("content") if isinstance(e.get("message"), dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if e.get("type") == "assistant" and b.get("type") == "tool_use" and b.get("name") == "Bash":
                cmd = (b.get("input") or {}).get("command")
                if isinstance(cmd, str) and b.get("id"):
                    call = _metadata_call(cmd, e.get("cwd") or "")
                    if call:
                        meta_calls[b["id"]] = call
            elif b.get("type") == "tool_result":
                texts = list(_strings(b.get("content")))
                results.extend(t for t in texts if DENY_HEAD in t[:300])
                if b.get("tool_use_id") in meta_calls:
                    literal, cwd = meta_calls[b["tool_use_id"]]
                    calls.extend((m, literal, cwd) for t in texts for m in META_PATH.findall(t))
    return calls, results


def _seen(seed: str, call: tuple) -> bool:
    printed, literal, cwd = call
    if literal:  # the metadata call named this exact file
        return seed == literal
    printed = printed.removeprefix("./")
    if not seed.endswith("/" + printed):
        return False
    if not cwd:
        return True
    # The loop variable hides the file name; the printed path is relative to the Seed's repo root,
    # so that root must contain, or be contained in, the directory the call ran in.
    root = seed[:-len(printed) - 1]
    cwd = os.path.realpath(cwd)
    return cwd == root or cwd.startswith(root + "/") or root.startswith(cwd.rstrip("/") + "/")


def decide(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    tool = payload.get("tool_name")
    if tool == "Read":
        fp = ti.get("file_path") or ""
        cands = [fp if os.path.isabs(fp) or not fp else os.path.join(payload.get("cwd") or os.getcwd(), fp)]
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
    calls, results = scanned
    unseen = []
    for s in seeds:
        if any(_seen(os.path.realpath(s), c) for c in calls):
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

    def tr(path, commands=(), results=(), outputs=(), cwd=None):
        rows = []
        for i, c in enumerate(commands):
            rows.append({"type": "assistant", **({"cwd": cwd} if cwd else {}), "message": {"content": [
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
        tr(t_meta, commands=[f'python3 /p/seed-relations.py metadata {seed} --json'], outputs=[f'{{"path": "{seed}"}}'])
        # build-spec's real loop shape (#814 S2): the basename never appears in the command.
        t_loop = f"{d}/t/loop.jsonl"
        tr(t_loop, commands=['for s in x; do python3 /p/seed-relations.py metadata docs/specs/$s.yaml --json; done'],
           outputs=['{"path": "docs/specs/x.yaml", "title": "t", "lifecycle": {}}'])
        t_walk = f"{d}/t/walk.jsonl"
        tr(t_walk, commands=['python3 /p/seed-relations.py walk docs/specs/$s.yaml --json'],
           outputs=['{"path": "docs/specs/x.yaml"}'])
        # #895 review: a failed metadata call (no JSON) or another Seed's call does not count.
        t_failed = f"{d}/t/failed.jsonl"
        tr(t_failed, commands=[f'python3 /p/seed-relations.py metadata {seed} --json'],
           outputs=["seed-relations: not a file: x.yaml"])
        t_other = f"{d}/t/other.jsonl"
        tr(t_other, commands=['python3 /p/seed-relations.py metadata docs/specs/old-x.yaml --json'],
           outputs=['{"path": "docs/specs/old-x.yaml"}'])
        t_denied = f"{d}/t/denied.jsonl"
        tr(t_denied, results=[f'PreToolUse:Read hook error: {DENY_HEAD}"/p/seed-relations.py" metadata {seed} --json (seed-lifecycle.md)'])
        # #895 review: a file that merely quotes the marker and the path (a Read of this script or a doc)
        # is not a deny.
        t_quoted = f"{d}/t/quoted.jsonl"
        tr(t_quoted, results=["1\t#!/usr/bin/env python3\n" + "x\n" * 200 + f"{MARKER} metadata를 먼저 실행해요: {seed}"])
        # #895 review: a loop's metadata call run in another repo does not cover this repo's Seed.
        t_foreign = f"{d}/t/foreign.jsonl"
        tr(t_foreign, commands=['for s in x; do python3 /p/seed-relations.py metadata docs/specs/$s.yaml --json; done'],
           outputs=['{"path": "docs/specs/x.yaml"}'], cwd="/elsewhere/other-repo")
        t_here = f"{d}/t/here.jsonl"
        tr(t_here, commands=['for s in x; do python3 /p/seed-relations.py metadata docs/specs/$s.yaml --json; done'],
           outputs=['{"path": "docs/specs/x.yaml"}'], cwd=d)
        # #895 review: `metadata` in a walk's file name must not turn walk output into a metadata call.
        t_walkmeta = f"{d}/t/walkmeta.jsonl"
        tr(t_walkmeta, commands=['python3 /p/seed-relations.py walk docs/specs/metadata-y.yaml --json'],
           outputs=['{"nodes": [{"path": "docs/specs/x.yaml"}]}'])
        # subagent layout: parent transcript t/main.jsonl, subagent at t/main/subagents/agent-a1.jsonl
        t_main = f"{d}/t/main.jsonl"
        tr(t_main, commands=[f'python3 /p/seed-relations.py metadata {seed} --json'], outputs=[f'{{"path": "{seed}"}}'])
        tr(f"{d}/t/main/subagents/agent-a1.jsonl", commands=["ls"])
        tr(f"{d}/t/main/subagents/agent-a2.jsonl", commands=[f'python3 /p/seed-relations.py metadata {seed} --json'], outputs=[f'{{"path": "{seed}"}}'])

        # Codex rollout (#814 acceptance-2): codex-cli 0.163.0 records shapes, observed live.
        def cx(path, runs=(), outputs=()):
            rows = [{"type": "item_completed", "item": {"type": "CommandExecution", "command": argv,
                     "cwd": "file://" + cwd, "aggregated_output": out, "exit_code": 0}} for argv, cwd, out in runs]
            rows += [{"type": "custom_tool_call_output", "call_id": "c", "output": [
                {"type": "input_text", "text": "Script failed\n"}, {"type": "input_text", "text": o}]} for o in outputs]
            Path(path).write_text("\n".join(json.dumps({"type": "event_msg" if "item" in r else "response_item",
                                                        "payload": r}) for r in rows) + "\n")
        meta_rel = 'python3 /p/seed-relations.py metadata docs/specs/x.yaml --json'
        c_meta, c_none, c_failed, c_denied, c_foreign, c_argv = (f"{d}/t/c-{n}.jsonl" for n in
                                                                  ("meta", "none", "failed", "denied", "foreign", "argv"))
        cx(c_meta, runs=[(["/bin/zsh", "-lc", meta_rel], d, '{"path": "docs/specs/x.yaml"}')])
        cx(c_none, runs=[(["/bin/zsh", "-lc", "ls"], d, "docs")])
        cx(c_failed, runs=[(["/bin/zsh", "-lc", meta_rel], d, "seed-relations: not a file")])
        cx(c_denied, outputs=[f'Script error:\nCommand blocked by PreToolUse hook: {DENY_HEAD}"/p/seed-relations.py" metadata {seed} --json'])
        cx(c_foreign, runs=[(["/bin/zsh", "-lc", 'for s in x; do python3 /p/seed-relations.py metadata docs/specs/$s.yaml; done'],
                             "/elsewhere/other-repo", '{"path": "docs/specs/x.yaml"}')])
        cx(c_argv, runs=[(["python3", "/p/seed-relations.py", "metadata", seed, "--json"], "/", f'{{"path": "{seed}"}}')])

        def read(p, t):
            return {"tool_name": "Read", "tool_input": {"file_path": p}, "transcript_path": t}

        def bash(c, t, **kw):
            return {"tool_name": "Bash", "tool_input": {"command": c}, "transcript_path": t, "cwd": d, **kw}

        check("read seed unseen", decide(read(seed, t_none)), True)
        check("read seed seen", decide(read(seed, t_meta)), False)
        check("read seed already denied once", decide(read(seed, t_denied)), False)
        check("read seed, loop metadata output", decide(read(seed, t_loop)), False)
        check("read seed, walk output is not metadata", decide(read(seed, t_walk)), True)
        check("bash tool name only as an argument still reads", decide(bash("cat docs/specs/x.yaml seed-relations.py", t_none)), True)
        check("bash launcher-run tool is its own read", decide(bash("uv run python3 -I scripts/seed-relations.py walk docs/specs/x.yaml", t_none)), False)
        check("bash sed -i is an edit", decide(bash("sed -i '' s/a/b/ docs/specs/x.yaml", t_none)), False)
        check("bash sed -n still reads", decide(bash("sed -n 1,5p docs/specs/x.yaml", t_none)), True)
        check("read seed, metadata failed", decide(read(seed, t_failed)), True)
        check("read seed, metadata for old-x only", decide(read(seed, t_other)), True)
        check("bash tool prefix is no bypass", decide(bash("python3 /p/seed-relations.py walk a.yaml; cat docs/specs/x.yaml", t_none)), True)
        check("bash metadata loop over glob", decide(bash("for f in docs/specs/*.yaml; do python3 /p/seed-relations.py metadata $f; done", t_none)), False)
        check("bash heredoc write is no read", decide(bash("cat > docs/specs/x.yaml <<'EOF'\nskill: build-spec\nEOF", t_none)), False)
        check("bash append write is no read", decide(bash("cat a.txt >> docs/specs/x.yaml", t_none)), False)
        check("bash sed --in-place is an edit", decide(bash("sed --in-place s/a/b/ docs/specs/x.yaml", t_none)), False)
        home = os.environ.get("HOME")
        os.environ["HOME"] = d
        try:
            check("bash ~ path expands", decide(bash("cat ~/docs/specs/x.yaml", t_none)), True)
        finally:
            if home is None:
                os.environ.pop("HOME")
            else:
                os.environ["HOME"] = home
        check("read relative path uses payload cwd", decide({**read("docs/specs/x.yaml", t_none), "cwd": d}), True)
        check("read quoting the marker is no prior deny", decide(read(seed, t_quoted)), True)
        check("read, metadata ran in another repo", decide(read(seed, t_foreign)), True)
        check("read, metadata ran in this repo", decide(read(seed, t_here)), False)
        check("read, walk output with metadata in a file name", decide(read(seed, t_walkmeta)), True)
        check("bash grep pattern keeps its pipe", decide(bash("grep -n 'goal|ambiguity' docs/specs/x.yaml", t_none)), True)
        check("bash sed script keeps its semicolon", decide(bash("sed -n '1p;3p' docs/specs/x.yaml", t_none)), True)
        check("bash tool name in a comment is no bypass", decide(bash("cat docs/specs/x.yaml  # seed-relations.py", t_none)), True)
        check("bash tool name as an argument is no bypass", decide(bash("cat docs/specs/x.yaml | grep seed-relations.py", t_none)), True)
        check("bash absolute reader path", decide(bash("/bin/cat docs/specs/x.yaml", t_none)), True)
        check("bash command substitution", decide(bash("echo $(cat docs/specs/x.yaml)", t_none)), True)
        check("bash sed -Ei is an edit", decide(bash("sed -Ei s/a/b/ docs/specs/x.yaml", t_none)), False)
        check("bash heredoc body is no command", decide(bash("python3 - <<'EOF'\ncat docs/specs/x.yaml\nEOF", t_none)), False)
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
        # Before #814's Codex branch, a Codex rollout never showed the metadata call: always denied.
        check("codex, metadata ran before cat", decide(bash("head -3 docs/specs/x.yaml", c_meta)), False)
        check("codex, no metadata", decide(bash("cat docs/specs/x.yaml", c_none)), True)
        check("codex, metadata failed", decide(bash("cat docs/specs/x.yaml", c_failed)), True)
        check("codex, already denied once", decide(bash("cat docs/specs/x.yaml", c_denied)), False)
        check("codex, metadata ran in another repo", decide(bash("cat docs/specs/x.yaml", c_foreign)), True)
        check("codex, argv command", decide(bash("cat docs/specs/x.yaml", c_argv)), False)

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
