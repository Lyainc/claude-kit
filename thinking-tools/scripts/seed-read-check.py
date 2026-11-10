#!/usr/bin/env python3
"""Seed read check — decision logic for hooks/seed-read-guard.sh (PreToolUse Read|Bash) and
hooks/seed-read-output-guard.sh (PostToolUse Bash, `--post`).

Denies (once per Seed per transcript) a Read/cat of a build-spec Seed body when
`seed-relations.py metadata` has not run for that Seed in the same transcript
(reference/seed-lifecycle.md §발견과 소비). Reads the hook JSON payload on stdin and prints a
one-line deny reason or nothing. Always exits 0: any exception, unparseable input or unreadable
file fails open. Bash detection is a heuristic and never claims to block every read.

The `--post` mode covers what the static PreToolUse check cannot see (a read built by command
substitution such as `cat $(git ls-files docs)`): it inspects the Bash tool OUTPUT for a Seed body
signature and, when the transcript shows no metadata for the Seed(s) (or the Seed cannot be
identified), prints feedback telling the model not to apply the body. Still a heuristic.

    echo '<payload json>' | seed-read-check.py
    echo '<PostToolUse payload json>' | seed-read-check.py --post
    seed-read-check.py --self-test
"""
from __future__ import annotations

import glob
import importlib.util
import itertools
import json
import os
import re
import shlex
import shutil
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
POST_HEAD = "Seed 본문이 metadata 없이 출력됐어요"
TEMPLATE_HEAD = "Seed Spec — output template"  # first line of templates/SEED_SPEC.yaml (emitted Seeds keep it)
TEMPLATE_PATH = "templates/SEED_SPEC.yaml"
# Output lines may carry a `cat -n` / `grep -n` / `grep <file>` prefix before the YAML key.
_PREFIX = r"(?:[ \t]*\d+\t|(?:[^\s:]+[:-])?(?:\d+[:-])?)"
SEED_KEYS = tuple(re.compile(r"(?m)^" + _PREFIX + k) for k in ("lifecycle:", "success_criteria:"))
GLOB_CHARS = "*?["
GLOB_CAP = 500
GENERIC_HEAD = POST_HEAD + ": 출력에 Seed 본문이 있는데 어느 Seed인지"  # the post guard's unidentified block opens like this
PATTERN_CMDS = {"grep", "egrep", "fgrep", "rg", "sed", "awk"}  # first non-option argument is a pattern/script
PATTERN_OPT = re.compile(r"-[A-Za-z]*[ef]$")  # short option cluster ending in -e/-f takes a value
VAR_REF = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
# A plain template read may print it with these programs; anything else is not a template read.
# None of them can run a command from its arguments (awk `system()`, sed `e`, rg `--pre` can).
TEMPLATE_READERS = {"cat", "head", "tail", "sed", "nl", "grep", "egrep", "fgrep"}
SAFE_SED = re.compile(r"[\d,;$pq ]+")  # `1,40p`: line addresses and print only, no `e`/`r`/`w`
FD_REDIRECT = re.compile(r"^(?:\d*>&\d+|\d*>&-|&?>>?/dev/null|\d+>>?/dev/null)$")  # `2>&1`, `2>/dev/null`
COUNT = re.compile(r"^\+?\d+$")  # `head -n 5`, `tail -n +3`: a count value, not a path


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
    env: dict[str, str] = {}
    for seg in segs:
        seg = seg.strip()
        subst = seg.endswith("$")  # `S=$(…)` was cut at `(`: the value is a substitution
        seg = seg.removesuffix("$").strip()
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        # `S=…/seed-relations.py; python3 "$S" metadata …` (observed live, 2026-11-09): a plain
        # assignment-only segment defines a variable that later segments expand, so a tool named
        # through it is still recognised. Anything else ($(…), loop variables) stays literal.
        assigns = words[1:] if words[:1] == ["export"] else words
        if assigns and all(ASSIGN.match(w) for w in assigns):
            for name, value in (w.split("=", 1) for w in assigns):
                if subst or "$" in value or "`" in value:
                    env.pop(name, None)
                else:
                    env[name] = value
            continue
        if env:
            words = [VAR_REF.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)), w) for w in words]
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


def _expand(pattern: str, wd: str) -> list[str]:
    """Seed-candidate YAML files a glob matches: filtered to YAML, capped lazily, then sorted. A pattern
    whose fixed prefix is exactly `/` or the home directory itself is skipped (too broad)."""
    fixed = re.split(r"[*?\[]", pattern, maxsplit=1)[0]
    prefix = os.path.normpath(os.path.expanduser(fixed)) if fixed else ""
    if prefix in ("/", os.path.normpath(os.path.expanduser("~"))):
        return []
    return sorted(itertools.islice((m for m in glob.iglob(pattern, recursive=True)
                                    if m.endswith((".yaml", ".yml"))), GLOB_CAP))


def _command_str(command) -> str:
    """A hook payload's command as one string; a Codex argv list is unwrapped or shell-joined."""
    if isinstance(command, list) and all(isinstance(a, str) for a in command):
        return command[2] if len(command) == 3 and command[1] in ("-lc", "-c") else shlex.join(command)
    return command if isinstance(command, str) else ""


def _reads_only_template(command: str, out: str) -> bool:
    """True only for a plain read of the template alone: one reader program, no substitution, no
    comment, no second command, one body. Option flags, a count value (`head -n 5`), the sed/grep/awk
    script word and fd redirects (`2>&1`) are not paths (#934); a yaml word in any of them is."""
    if TEMPLATE_PATH not in command or any(t in command for t in ("$(", "`", "#", ";", "|", "\n", "<")) \
            or re.search(r"(?<!>)&(?!>)", command):
        return False
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return False
    prog = os.path.basename(words[0]) if words else ""
    if prog not in TEMPLATE_READERS:
        return False
    need_script, skip_next, paths = prog in PATTERN_CMDS, False, []
    for w in words[1:]:
        is_template = w.endswith(TEMPLATE_PATH)
        if not is_template and (".yaml" in w or ".yml" in w):  # may be a read (`sed 'r x.yaml'`, --file=)
            return False
        if skip_next:  # the value of -e/-f/--regexp
            skip_next = False
            if prog == "sed" and not SAFE_SED.fullmatch(w):
                return False
            continue
        if is_template:
            paths.append(w)
            continue
        if FD_REDIRECT.match(w) or COUNT.match(w):
            continue
        if w.startswith("-") and w != "-":
            if prog == "sed" and (w.startswith(("--expression", "--file")) or re.match(r"-[A-Za-z]*f", w)):
                return False  # a sed script we do not inspect (file or `--expression=` form)
            if prog in PATTERN_CMDS and (w in ("--regexp", "--file") or PATTERN_OPT.match(w)):
                skip_next, need_script = True, False
            elif w.startswith(("--regexp=", "--file=")):
                need_script = False
            continue
        if need_script:  # grep's pattern is inert; sed's script may run or read (`e`, `r`)
            need_script = False
            if prog == "sed" and not SAFE_SED.fullmatch(w):
                return False
            continue
        return False  # another path (or `-` for stdin)
    return bool(paths) and len(SEED_KEYS[1].findall(out)) <= 1


def bash_candidates(command: str, cwd: str) -> list[str]:
    # Pre-filter: a yaml name, `specs`, or a glob character (a glob can expand to Seed YAML files
    # without naming one). Candidates are still filtered by is_seed_file() in decide().
    if not any(t in command for t in (".yaml", ".yml", "specs") + tuple(GLOB_CHARS)):
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
        if first == "rg" and "--files" in words:  # lists file names only; reads no body (#934)
            continue
        prev = ""
        need_pattern, skip_next = first in PATTERN_CMDS, False
        for w in words[1:]:
            target, prev = prev in (">", ">>") or w.startswith(">"), w
            if target:  # a redirect target is written, not read
                continue
            if skip_next:  # the value of -e/-f/--regexp is a pattern or script file, not a read path
                skip_next = False
                continue
            if need_pattern or first in PATTERN_CMDS:
                if w.startswith("-") and w != "-":
                    if w in ("--regexp", "--file") or PATTERN_OPT.match(w):
                        skip_next, need_pattern = True, False
                    elif w.startswith(("--regexp=", "--file=")):
                        need_pattern = False
                    continue
                if need_pattern:  # the first non-option argument is the pattern/script
                    need_pattern = False
                    continue
            has_glob = any(c in w for c in GLOB_CHARS)
            if not has_glob and not w.endswith((".yaml", ".yml")):
                continue
            w = os.path.expanduser(w)
            p = w if os.path.isabs(w) else os.path.join(wd, w)
            if has_glob:
                # A non-yaml glob (`docs/specs/*`, `h*`) can expand to Seed YAML files too.
                found.extend(_expand(p, wd))
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
        if moved or any(c in target for c in "$`~" + GLOB_CHARS) or not (cwd or os.path.isabs(target)):
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
        results.extend(t for t in _strings(e) if GENERIC_HEAD in t[:300])
        p = e.get("payload")
        if isinstance(p, dict):
            # shortcut: only code-mode `exec` → exec_command records were observed (codex-cli 0.163.0);
            # parse other Codex tool shapes if a rollout shows them.
            it = p.get("item") if p.get("type") == "item_completed" else None
            if isinstance(it, dict) and it.get("type") == "CommandExecution":
                argv = it.get("command")
                cmd = argv[2] if isinstance(argv, list) and len(argv) == 3 and argv[1] in ("-lc", "-c") \
                    else shlex.join(argv) if isinstance(argv, list) else argv
                raw_cwd = it.get("cwd") or ""
                call = _metadata_call(cmd, unquote(urlparse(raw_cwd).path)) \
                    if isinstance(cmd, str) and isinstance(raw_cwd, str) else None
                if call:
                    literal, cwd = call
                    calls.extend((m, literal, cwd) for m in META_PATH.findall(str(it.get("aggregated_output") or "")))
            elif p.get("type") in ("custom_tool_call_output", "function_call_output"):
                results.extend(t for t in _strings(p.get("output")) if DENY_HEAD in t[:300])
            continue
        content = (e.get("message") or {}).get("content") if isinstance(e.get("message"), dict) else None
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


def _seed_files(cands: list[str]) -> list[str]:
    seeds: list[str] = []
    for c in cands:
        c = os.path.abspath(c) if c else ""
        if c and c not in seeds and c.endswith((".yaml", ".yml")) and is_seed_file(c):
            seeds.append(c)
    return seeds


def unseen_seeds(seeds: list[str], payload: dict, extra_calls=(), skip_denied: bool = True):
    """Seeds with no metadata call in the transcript (or already denied once, when skip_denied).
    None when the transcript is unreadable (fail open)."""
    scanned = scan_transcript(transcript_path(payload))
    if scanned is None:
        return None
    calls, results = scanned
    calls = list(calls) + list(extra_calls)
    return [s for s in seeds if not any(_seen(os.path.realpath(s), c) for c in calls)
            and not (skip_denied and any(s in r for r in results))]


def _generic_blocked(payload: dict) -> bool:
    """The unidentified-Seed block was already given once in this transcript."""
    scanned = scan_transcript(transcript_path(payload))
    return bool(scanned) and any(GENERIC_HEAD in r[:300] for r in scanned[1])


def _metadata_cmds(seeds: list[str]) -> str:
    script = f"{PLUGIN_ROOT}/scripts/seed-relations.py"
    return " ; ".join(f'python3 "{script}" metadata {shlex.quote(s)} --json' for s in seeds)


def decide(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    tool = payload.get("tool_name")
    if tool == "Read":
        fp = ti.get("file_path") or ""
        cands = [fp if os.path.isabs(fp) or not fp else os.path.join(payload.get("cwd") or os.getcwd(), fp)]
    elif tool == "Bash":
        cands = bash_candidates(_command_str(ti.get("command")), payload.get("cwd") or "")
    else:
        return ""
    seeds = _seed_files(cands)
    if not seeds:
        return ""
    unseen = unseen_seeds(seeds, payload)
    if not unseen:  # None (unreadable transcript) or empty
        return ""
    return f"{MARKER} metadata를 먼저 실행해요: {_metadata_cmds(unseen)} (seed-lifecycle.md §발견과 소비)"


def has_seed_body(out: str) -> bool:
    """Output carries a Seed body: the template's amendment-contract header, both top-level
    `lifecycle:` and `success_criteria:` keys (every Seed the template emits has them), or a Seed
    marker (`_sac.SEED_MARKERS`, the single definition) beside one of those keys. Heuristic."""
    if "AMENDMENT CONTRACT" in out and "Read metadata first" in out:
        return True
    has = [k.search(out) for k in SEED_KEYS]
    return all(has) or (any(m in out for m in _sac.SEED_MARKERS) and any(has))


def _identify_seeds(command: str, out: str, cwd: str) -> list[str]:
    """Seeds the output most likely printed: files the command names (globs expanded) plus Seed
    files whose path prefixes an output line. Anything else stays unidentified."""
    cands = bash_candidates(command, cwd)
    for m in re.finditer(r"(?m)^(?:==> )?([^\s:=]+\.ya?ml)(?:[:\- ]|$)", out):
        cands.append(m.group(1) if os.path.isabs(m.group(1)) else os.path.join(cwd, m.group(1)))
    return _seed_files(cands)


def decide_post(payload: dict) -> str:
    """Feedback text when a Bash call's OUTPUT holds a Seed body with no metadata on record."""
    if payload.get("tool_name") != "Bash":
        return ""
    out = "\n".join(_strings(payload.get("tool_response")))
    if not has_seed_body(out):
        return ""  # fast path: no signature
    command = _command_str((payload.get("tool_input") or {}).get("command"))
    cwd = payload.get("cwd") or os.getcwd()
    seeds = _identify_seeds(command, out, cwd)
    if not seeds and _reads_only_template(command, out):
        # Emitted Seeds keep the template's header lines, so the output text alone cannot tell the
        # template from a Seed; only a command that reads nothing but the template is exempt.
        return ""
    cur = _metadata_call(command, cwd)  # this call's own metadata/read output may not be in the transcript yet
    extra = [(m, cur[0], cur[1]) for m in META_PATH.findall(out)] if cur else []
    unseen = unseen_seeds(seeds, payload, extra, skip_denied=False)
    if unseen is None:
        return ""
    # More Seed bodies than identified Seeds: some body is unidentified. Block that generically, but once
    # per transcript, so non-Seed YAML that merely has these keys (fixtures, diffs) cannot loop forever.
    bodies = len(SEED_KEYS[1].findall(out))
    if (not seeds or bodies > len(seeds)) and not _generic_blocked(payload):
        return (f"{GENERIC_HEAD} 확인하지 못했어요. 그 본문의 항목을 하나도 적용하지 말고, "
                f'출력에 나온 Seed마다 python3 "{PLUGIN_ROOT}/scripts/seed-relations.py" metadata <seed> --json 을 먼저 실행해요 (seed-lifecycle.md §발견과 소비)')
    if not unseen:
        return ""
    return (f"{POST_HEAD}: 그 본문의 항목을 하나도 적용하지 말고, 먼저 실행해요: {_metadata_cmds(unseen)} "
            "(unknown/paused/closed 상태나 철회·보류 항목은 자동 적용 대상이 아니에요, seed-lifecycle.md §발견과 소비)")


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
        Path(f"{specs}/hello.yaml").write_text('skill: build-spec\ngoal: h\n')
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
        # #934 live shape (2026-11-09 cd1): the tool and the Seed directory come through variables.
        t_var = f"{d}/t/var.jsonl"
        tr(t_var, commands=['S=/p/seed-relations.py; D=docs/specs; for f in x; do echo "=== $f"; '
                            'python3 "$S" metadata "$D/$f.yaml" --json; done'],
           outputs=['=== x\n{"path": "docs/specs/x.yaml", "title": "t"}'], cwd=d)
        t_varsub = f"{d}/t/varsub.jsonl"  # a substituted value is not literal: no metadata call
        tr(t_varsub, commands=['S=$(command -v seed-relations.py); python3 "$S" metadata docs/specs/x.yaml'],
           outputs=['{"path": "docs/specs/x.yaml"}'], cwd=d)
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
        c_badcwd, c_badcmd = f"{d}/t/c-badcwd.jsonl", f"{d}/t/c-badcmd.jsonl"
        for path, over in ((c_badcwd, {"cwd": 5}), (c_badcmd, {"command": {"x": 1}})):
            item = {"type": "CommandExecution", "command": ["/bin/zsh", "-lc", meta_rel], "cwd": "file://" + d,
                    "aggregated_output": '{"path": "docs/specs/x.yaml"}', "exit_code": 0, **over}
            Path(path).write_text(json.dumps({"type": "event_msg", "payload": {"type": "item_completed", "item": item}}) + "\n")
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
        # Glob/directory-wide reads that name no yaml (#814 live repro).
        check("bash cat dir glob", decide(bash("cat docs/specs/*", t_none)), True)
        check("bash for over dir glob", decide(bash('for f in docs/specs/*; do cat "$f"; done', t_none)), True)
        check("bash cat partial-name glob", decide(bash("cat docs/specs/h*", t_none)), True)
        check("bash cat ? glob", decide(bash("cat docs/specs/?.yaml", t_none)), True)
        check("bash ? glob with no yaml/specs text", decide(bash("cat docs/spec?/x.y?ml", t_none)), True)
        check("bash [] glob with no yaml/specs text", decide(bash("cat docs/spec[s]/x.yam[l]", t_none)), True)
        check("bash dir glob, metadata seen", decide(bash("cat docs/specs/x*", t_meta)), False)
        check("bash dir glob loop running the tool", decide(bash('for f in docs/specs/*; do python3 /p/seed-relations.py metadata "$f"; done', t_none)), False)
        check("bash echo dir glob is no read", decide(bash("echo docs/specs/*", t_none)), False)
        check("bash ls dir glob is no read", decide(bash("ls docs/specs/*", t_none)), False)
        check("bash git dir glob is no read", decide(bash("git add docs/specs/*", t_none)), False)
        check("bash glob redirect target is no read", decide(bash("echo hi > docs/specs/*", t_none)), False)
        check("bash glob matching only non-seed", decide(bash("cat docs/specs/p*", t_none)), False)
        check("bash glob matching nothing", decide(bash("cat docs/nothing/*", t_none)), False)
        check("bash glob with a quoted pattern arg", decide(bash("grep 'specs/*' README.md", t_none)), False)
        sib = os.path.realpath(tempfile.mkdtemp(dir=os.path.dirname(d)))
        try:
            os.makedirs(f"{sib}/docs/specs")
            Path(f"{sib}/docs/specs/s.yaml").write_text("skill: build-spec\ngoal: s\n")
            check("bash glob outside the working directory", decide(bash(f"cat {sib}/docs/specs/*", t_none)), True)
            check("bash ** recursive glob", decide(bash(f"cat {sib}/**/s.yaml", t_none)), True)
            check("bash glob of the root is skipped", decide(bash("cat /*", t_none)), False)
            check("bash glob of the home dir is skipped", decide(bash("cat ~/*", t_none)), False)
        finally:
            shutil.rmtree(sib, ignore_errors=True)
        many = f"{d}/many"
        os.makedirs(many)
        for i in range(GLOB_CAP + 5):
            Path(f"{many}/n{i:04d}.txt").write_text("x\n")
        Path(f"{many}/zz.yaml").write_text("skill: build-spec\ngoal: z\n")
        check("bash glob cap counts only yaml files", decide(bash("cat many/*", t_none)), True)
        check("bash grep -rn pattern is not expanded", decide(bash("grep -rn 'specs/*' .", t_none)), False)
        check("bash rg pattern with a class is not expanded", decide(bash("rg '[a-z]+' docs/nothing", t_none)), False)
        check("bash grep -e pattern is not expanded, file read", decide(bash("grep -e 'specs/*' docs/specs/x.yaml", t_none)), True)
        check("bash grep -e pattern alone is no read", decide(bash("grep -e 'docs/specs/*' README.md", t_none)), False)
        check("bash grep file arg after pattern still reads", decide(bash("grep goal docs/specs/*.yaml", t_none)), True)
        # #934: a listing reads no body (live Codex shape), but a content search still does.
        check("bash rg --files with spec globs is no read", decide(bash(
            "pwd; rg --files -g 'AGENTS.md' -g 'docs/specs/**' -g 'pnpm-lock.yaml'", t_none)), False)
        check("bash rg --files over the spec dir is no read", decide(bash("rg --files docs/specs", t_none)), False)
        check("bash ls of the spec dir is no read", decide(bash("ls -la docs/specs; ls docs/specs/*.yaml", t_none)), False)
        check("bash rg content search still reads", decide(bash("rg goal -g '*.yaml' docs/specs/x.yaml", t_none)), True)
        check("bash rg --files beside a cat still reads", decide(bash("rg --files docs; cat docs/specs/x.yaml", t_none)), True)
        # #934: metadata through a variable (live cd1/CDS/CB shape) is metadata, before and after.
        check("bash metadata loop through $S is not denied", decide(bash(
            'S=/p/seed-relations.py; for f in docs/specs/x.yaml; do python3 "$S" metadata "$f" --json; done', t_none)), False)
        check("bash exported tool variable", decide(bash(
            "export S=/p/seed-relations.py; python3 ${S} metadata docs/specs/x.yaml", t_none)), False)
        check("read seed after metadata through variables", decide(bash("cat README.md docs/specs/x.yaml", t_var)), False)
        check("bash variable naming a reader still reads", decide(bash("R=cat; $R docs/specs/x.yaml", t_none)), True)
        check("bash variable tool beside a cat still reads", decide(bash(
            "S=/p/seed-relations.py; python3 $S walk a.yaml; cat docs/specs/x.yaml", t_none)), True)
        check("read seed, substituted tool variable is no metadata", decide(bash("cat docs/specs/x.yaml", t_varsub)), True)
        check("codex argv command", decide({"tool_name": "Bash", "tool_input": {"command": ["bash", "-lc", "cat docs/specs/x.yaml"]},
                                           "transcript_path": t_none, "cwd": d}), True)
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
        check("codex, non-str cwd is no metadata call", decide(bash("cat docs/specs/x.yaml", c_badcwd)), True)
        check("codex, non-str non-list command is no metadata call", decide(bash("cat docs/specs/x.yaml", c_badcmd)), True)
        check("codex, argv command", decide(bash("cat docs/specs/x.yaml", c_argv)), False)

        # PostToolUse: the output carries a Seed body that no static read check could predict.
        body = ("# AMENDMENT CONTRACT\nskill: build-spec\nlifecycle:\n  state: paused\n"
                "success_criteria:\n  - id: acceptance-1\n")
        stranger = body
        # a `grep -rn`-style read names its Seed in each line prefix
        pref = "docs/specs/x.yaml:2:lifecycle:\ndocs/specs/x.yaml:9:success_criteria:\n"

        def post(c, out, t, **kw):
            return {"tool_name": "Bash", "tool_input": {"command": c}, "tool_response": {"stdout": out, "stderr": ""},
                    "transcript_path": t, "cwd": d, **kw}

        subst = 'for f in $(git ls-files docs AGENTS.md); do cat "$f"; done'
        r = decide_post(post(subst, pref, t_none))
        check("post, seed body without metadata", r, True)
        check("post, block names the identified seed", seed in r and "metadata" in r, True)
        check("post, same body after metadata", decide_post(post(subst, pref, t_meta)), False)
        check("post, output without a seed body", decide_post(post(subst, "docs\nAGENTS.md\n", t_none)), False)
        check("post, only one signature key is no seed body", decide_post(post(subst, "lifecycle:\n  state: x\n", t_none)), False)
        r = decide_post(post("cat $(ls)", stranger, t_none))
        check("post, unidentifiable seed body", r, True)
        check("post, unidentifiable block is generic", "<seed>" in r and seed not in r, True)
        check("post, unidentifiable body even after metadata", decide_post(post("cat $(ls)", stranger, t_meta)), True)
        check("post, command names the seed", decide_post(post("cat docs/specs/x.yaml", stranger, t_none)), True)
        check("post, command names the seed, metadata seen", decide_post(post("cat docs/specs/x.yaml", stranger, t_meta)), False)
        check("post, grep -n prefix keeps the signature", decide_post(post(subst, "docs/specs/x.yaml:1:skill: build-spec\ndocs/specs/x.yaml:2:lifecycle:\ndocs/specs/x.yaml:9:success_criteria:\n", t_none)), True)
        check("post, cat -n prefix keeps the signature", decide_post(post(subst, "     1\tskill: build-spec\n     2\tlifecycle:\n     9\tsuccess_criteria:\n", t_none)), True)
        check("post, path-prefixed lines identify the seed", seed in decide_post(post(
            "grep -rn . docs", "docs/specs/x.yaml:2:lifecycle:\ndocs/specs/x.yaml:9:success_criteria:\n", t_none)), True)
        check("post, a command naming the template is no seed", decide_post(post(
            "cat thinking-tools/skills/build-spec/templates/SEED_SPEC.yaml", f"# {TEMPLATE_HEAD}\n" + stranger, t_none)), False)
        check("post, a Seed keeping the template header still blocks", decide_post(post(
            subst, f"# {TEMPLATE_HEAD}\n" + stranger, t_none)), True)
        check("post, template plus substituted Seeds still blocks", decide_post(post(
            "cat skills/build-spec/templates/SEED_SPEC.yaml $(ls docs/specs/*.yaml)", f"# {TEMPLATE_HEAD}\n" + stranger, t_none)), True)
        check("post, a template path in a comment still blocks", decide_post(post(
            "cat $(git ls-files docs) # templates/SEED_SPEC.yaml", f"# {TEMPLATE_HEAD}\n" + stranger, t_none)), True)
        # #934: a plain template read with a count, a sed script or an fd redirect is not a Seed body.
        tp = "thinking-tools/skills/build-spec/templates/SEED_SPEC.yaml"
        tout = f"# {TEMPLATE_HEAD}\n" + stranger
        for c in (f"head -n 5 {tp}", f"sed -n '1,40p' {tp}", f"cat {tp} 2>&1", f"cat {tp} 2>/dev/null",
                  f"tail -n +3 {tp}", f"grep -n 'success_criteria' {tp}"):
            check(f"post, template-only read: {c[:18]}", decide_post(post(c, tout, t_none)), False)
        for c in (f"sed 'r docs/specs/x.yaml' {tp}", f"cat {tp} -", f"grep -f {tp} README.md",
                  f"cat {tp} README.md", f"cat {tp} & cat README.md", f"cat {tp} < README.md",
                  f"python3 x.py {tp}", f"head -n 5 {tp}\ncat README.md",
                  # review round 1: a script word that runs or reads a file is no template read
                  f"awk 'BEGIN{{system(\"cat docs/specs/x*\")}}' {tp}", f"sed -n '1e cat docs/specs/x*' {tp}",
                  f"sed -n -e '1r README.md' {tp}", f"sed -f s.sed {tp}", f"rg --pre ./p . {tp}"):
            check(f"post, template plus another read still blocks: {c[-22:]}", decide_post(post(c, tout, t_none)), True)
        # #934: the live cd1 re-read after a variable-driven metadata loop.
        check("post, re-read after metadata through variables", decide_post(post(
            "cat README.md docs/specs/x.yaml", stranger, t_var)), False)
        check("post, re-read after substituted-variable metadata still blocks", decide_post(post(
            "cat README.md docs/specs/x.yaml", stranger, t_varsub)), True)
        check("post, a metadata call's own output counts", decide_post(post(
            'python3 /p/seed-relations.py read docs/specs/x.yaml', f'{{"path": "docs/specs/x.yaml"}}\n{pref}', t_none)), False)
        check("post, walk output is no metadata", decide_post(post(
            'python3 /p/seed-relations.py walk docs/specs/x.yaml', body, t_walk)), True)
        check("post, metadata ran in another repo", decide_post(post("cat docs/specs/x.yaml", body, t_foreign)), True)
        check("post, string tool_response", decide_post({**post(subst, "", t_none), "tool_response": body}), True)
        check("post, subagent transcript without metadata", decide_post({**post(subst, body, t_main), "agent_id": "a1"}), True)
        check("post, subagent transcript with metadata", decide_post({**post(subst, pref, t_main), "agent_id": "a2"}), False)
        check("post, missing transcript fails open", decide_post(post(subst, body, f"{d}/t/missing.jsonl")), False)
        check("post, other tool", decide_post({**post(subst, body, t_none), "tool_name": "Read"}), False)
        check("post, codex rollout with metadata", decide_post(post(subst, pref, c_meta)), False)
        check("post, codex rollout without metadata", decide_post(post(subst, body, c_none)), True)
        t_gen = f"{d}/t/generic.jsonl"
        tr(t_gen, results=[f"{POST_HEAD}: 출력에 Seed 본문이 있는데 어느 Seed인지 확인하지 못했어요. 그 본문의"])
        check("post, unidentified block only once per transcript", decide_post(post("cat $(ls)", stranger, t_gen)), False)
        two = pref + "other.yaml:3:success_criteria:\n"
        check("post, more bodies than identified seeds blocks despite metadata", decide_post(post(subst, two, t_meta)), True)
        t_genmeta = f"{d}/t/genmeta.jsonl"
        tr(t_genmeta, commands=[f'python3 /p/seed-relations.py metadata {seed} --json'], outputs=[f'{{"path": "{seed}"}}'],
           results=[f"{POST_HEAD}: 출력에 Seed 본문이 있는데 어느 Seed인지 확인하지 못했어요. 그 본문의"])
        check("post, partial identification blocks only once", decide_post(post(subst, two, t_genmeta)), False)
        r = decide_post(post(subst, two, t_gen))
        check("post, generic given once, identified unseen still gets the specific block", "<seed>" not in r and seed in r, True)
        check("post, one body per identified seed is not generic", "<seed>" in decide_post(post(subst, pref, t_none)), False)
        check("post, no tool_response", decide_post({"tool_name": "Bash", "tool_input": {"command": "ls"}}), False)

    import subprocess
    for args, stdin, want_out in (([], "not json{", False), (["--post"], "not json{", False), (["--post"], "[]", False)):
        total += 1
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), *args], input=stdin,
                           capture_output=True, text=True)
        if bool(p.stdout) != want_out or p.returncode != 0:
            failed += 1
            print(f"FAIL: garbage stdin {args}", file=sys.stderr)
    with tempfile.TemporaryDirectory() as d2:
        total += 1
        pl = {"tool_name": "Bash", "tool_input": {"command": "cat $(ls)"}, "cwd": d2, "transcript_path": f"{d2}/t.jsonl",
              "tool_response": {"stdout": "target: zz\nlifecycle:\nsuccess_criteria:\n"}}
        Path(f"{d2}/t.jsonl").write_text("{}\n")
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--post"], input=json.dumps(pl),
                           capture_output=True, text=True)
        if POST_HEAD not in p.stdout or p.returncode != 0:
            failed += 1
            print("FAIL: --post end to end", file=sys.stderr)

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
            reason = (decide_post if "--post" in sys.argv else decide)(payload)
            if reason:
                print(reason)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
