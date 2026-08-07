#!/usr/bin/env python3
"""check-agent-tools-usage.py — an agent's `tools:` must match what its body says (#577).

RULE: for every `*/agents/*.md`, the tools declared in frontmatter and the tools the body
actually reaches for must be the same set. Three findings, three different harms:

  UNDECLARED — the body directs the agent to call a tool that `tools:` omits. The call cannot
    happen, so that branch of the agent is dead prose. Found live in vault-searcher.md, whose
    `.vault-link` path-resolution recovery said "use AskUserQuestion" while `tools:` listed only
    Read/Bash/Glob/Grep (#577).

  UNUSED — `tools:` grants a tool the body never reaches for. That is the over-permission #472
    introduced the field to prevent, just re-created one entry at a time. Found live in
    vault-file-organizer.md, which held Write and Grep while its body only moves files and edits
    named frontmatter fields (#577).

  CONTRACT — the body declares itself read-only (the Write Role Contract) yet `tools:` grants a
    write tool. UNUSED cannot catch this on its own: the very sentence stating the prohibition
    ("no access to the Write tool") contains the word `Write`, which satisfies a bare-mention
    check. This is the repo's central write-safety invariant, so it gets its own rule.

`check-agent-tools-field.py` is the sibling guard and deliberately stops at "the key exists and
is non-empty" — its docstring calls this comparison a manual judgment call. This script is that
judgment call, made mechanical.

## How usage is detected, and why the directions read differently

The body is prose, so neither direction can be inferred perfectly. Each is matched by the
narrowest signal its own harm needs, and the asymmetry is deliberate:

  UNDECLARED looks only for an *imperative* mention — `use X`, `call X`, `via X`, `X(` — because
    the harm is a directive that cannot execute. A tool merely named in passing ("the Write Role
    Contract", "vault writes are user-initiated") is not a directive and must not be flagged.
    The verb is matched case-insensitively so a numbered step beginning "Use Glob to…" counts,
    but the tool name itself stays case-exact so the verb `write` never reads as the tool
    `Write`. Negations are excluded within the sentence leading up to the verb:
    code-reviewer.md says "do not use the `Agent` tool", which is a prohibition, not a call.

  UNUSED looks for the tool name appearing *anywhere* in the body, imperative or not. A weaker
    signal is correct here because the direction is inverted: any mention at all shows the grant
    was considered, and demanding an imperative would flag a dozen legitimate grants across this
    repo's agents. The residual cost is that a tool used only through an unnamed shell command
    reads as unused — so a body must name the tools it relies on, which is what CLAUDE.md's
    "Adding a New Agent" §2 already asks for. Where that weak signal is not good enough to
    protect an invariant, CONTRACT above covers the gap.

Neither direction infers usage from a code fence. `mv` in a bash fence is Bash, but `ls` in a
sentence is not, and the guard does not try to tell them apart — the body says `Bash` or the
grant is not evidenced.

Usage:
    python3 scripts/check-agent-tools-usage.py [--root DIR] [--json] [--self-test]

    --root DIR    Repo root to check (default: git toplevel, else CWD). Scans DIR/*/agents/*.md.
    --json        Emit a machine-readable JSON report instead of text.
    --self-test   Validate the matching logic in-memory against fixture strings and exit 0 only
                  if every case is detected as expected.

Exit codes: 0 = every agent's declared tools match its body (or --self-test passed),
            1 = at least one mismatch, 2 = usage error / no agents found.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
# `[ \t]*` and not `\s*`: with re.MULTILINE, `\s*` eats the newline and swallows the first
# entry of a YAML block list, so `tools:\n  - Read` would capture the literal `- Read`.
TOOLS_KEY_RE = re.compile(r"^tools:[ \t]*(.*)$", re.MULTILINE)
TOOLS_BLOCK_ITEM_RE = re.compile(r"^[ \t]*-[ \t]*(\S.*?)[ \t]*$")

# Tool names this guard knows about. A name outside this set is reported as unknown rather than
# silently ignored — a typo'd grant is still a grant that does nothing. `mcp__*` names and the
# scoped `Tool(pattern)` form are normalised before the lookup, not rejected.
KNOWN_TOOLS = [
    "Agent", "Artifact", "AskUserQuestion", "Bash", "BashOutput", "Edit", "ExitPlanMode",
    "Glob", "Grep", "KillShell", "ListAgents", "Monitor", "NotebookEdit", "Read",
    "SendMessage", "Skill", "SlashCommand", "Task", "TodoWrite", "ToolSearch", "WebFetch",
    "WebSearch", "Write",
]

# Tools that can create or modify a file. A body claiming the Write Role Contract may hold none.
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
READONLY_MARKERS = (
    "write role contract",
    "cannot write",
    "no access to the write tool",
    "read-only",
)

_VERBS = r"(?:use|uses|using|call|calls|calling|invoke|invokes|invoking|via|through)"
# Up to two filler words between verb and tool ("use the `X` tool", "call into X").
_FILLER = r"(?:\s+(?:a|an|the|into|to|with|by)){0,2}"
NEGATORS = ("not", "never", "without", "cannot", "no", "neither", "nor")
# How far back to read for a negation, and where that read stops.
_LOOKBACK = 160
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")


def _imperative_re(tool):
    """Match an imperative reach for `tool`.

    The verb and filler are case-insensitive via an inline group so a numbered step starting
    "Use Glob to…" matches; the tool name stays case-exact, which is what keeps the ordinary
    verb `write` from reading as the tool `Write`. The second alternative is call syntax with
    no space before the paren — `Write (v5 §5)` is a prose parenthetical, not a call.
    """
    return re.compile(
        r"(?i:" + _VERBS + _FILLER + r")\s+`?" + re.escape(tool) + r"`?\b"
        r"|\b" + re.escape(tool) + r"\("
    )


def _mention_re(tool):
    return re.compile(r"\b" + re.escape(tool) + r"\b")


def _is_negated(body, start):
    """True when the sentence leading up to `start` negates the reach.

    Read backwards from the match through the whole preceding sentence rather than a fixed
    same-line window: "do not re-invoke yourself, do\\nnot use the `Agent` tool" puts the
    negator on the previous line, and one prose rewrap moves it further still.
    """
    window = body[max(0, start - _LOOKBACK):start]
    ends = list(_SENTENCE_END_RE.finditer(window))
    if ends:
        window = window[ends[-1].end():]
    lowered = window.lower()
    if "n't" in lowered:
        return True
    return any(re.search(r"\b" + n + r"\b", lowered) for n in NEGATORS)


def split_frontmatter(text):
    """Return (frontmatter, body) or (None, None) when there is no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def declared_tools(frontmatter):
    """Read `tools:` in either the inline comma form or a YAML block list."""
    tm = TOOLS_KEY_RE.search(frontmatter or "")
    if not tm:
        return []
    inline = tm.group(1).strip()
    if inline:
        return [t.strip() for t in inline.split(",") if t.strip()]
    tools = []
    for line in frontmatter[tm.end():].lstrip("\r\n").split("\n"):
        item = TOOLS_BLOCK_ITEM_RE.match(line)
        if not item:
            break
        tools.append(item.group(1))
    return tools


def normalise(tool):
    """Strip the scoped `Bash(git diff:*)` suffix so the base name can be looked up."""
    return tool.split("(", 1)[0].strip()


def is_known(tool):
    base = normalise(tool)
    return base in KNOWN_TOOLS or base.startswith("mcp__")


def strip_noise(body):
    """Drop spans that name tools without reaching for them.

    Fenced code blocks are shell/YAML samples, and an HTML comment is authoring scaffolding —
    a tool name in either is not the body directing itself.
    """
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    return body


def check_agent(text):
    """Return (undeclared, unused, unknown, contract) tool-name lists for one agent .md."""
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        return [], [], [], []
    declared = declared_tools(frontmatter)
    unknown = [t for t in declared if not is_known(t)]
    known_declared = [normalise(t) for t in declared if is_known(t) and not normalise(t).startswith("mcp__")]
    declared_bases = {normalise(t) for t in declared}
    body = strip_noise(body or "")

    undeclared = []
    for tool in KNOWN_TOOLS:
        if tool in declared_bases:
            continue
        for m in _imperative_re(tool).finditer(body):
            if not _is_negated(body, m.start()):
                undeclared.append(tool)
                break

    unused = [t for t in known_declared if not _mention_re(t).search(body)]

    lowered = body.lower()
    contract = []
    if any(marker in lowered for marker in READONLY_MARKERS):
        contract = [t for t in WRITE_TOOLS if t in declared_bases]

    return undeclared, unused, unknown, contract


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_agent_files(root):
    return sorted(glob.glob(os.path.join(root, "*", "agents", "*.md")))


SELF_TEST_CASES = [
    # (label, text, undeclared, unused, unknown, contract)
    (
        "imperative mention of an undeclared tool",
        "---\nname: a\ntools: Read\n---\nuse AskUserQuestion to confirm the path.\nRead it.",
        ["AskUserQuestion"], [], [], [],
    ),
    (
        "a numbered step starting with a capitalised verb still counts",
        "---\nname: a\ntools: Read\n---\n1. Use Glob to find session files.\n2. Read them.",
        ["Glob"], [], [], [],
    ),
    (
        "backticked imperative, filler words",
        "---\nname: a\ntools: Read\n---\nThen call the `Skill` tool. Read the file.",
        ["Skill"], [], [], [],
    ),
    (
        "negation on the previous line still suppresses",
        "---\nname: a\ntools: Read\n---\nDo not re-invoke yourself, do\nnot use the `Agent` tool. Read the diff.",
        [], [], [], [],
    ),
    (
        "a negator further back in the same sentence suppresses",
        "---\nname: a\ntools: Read\n---\nThis agent must never, under any circumstance whatsoever in any mode, use the `Agent` tool. Read on.",
        [], [], [], [],
    ),
    (
        "a negator in the PREVIOUS sentence does not suppress",
        "---\nname: a\ntools: Read\n---\nThis is not a review tool. Use Grep for the scan. Read on.",
        ["Grep"], [], [], [],
    ),
    (
        "passing mention is not a call",
        "---\nname: a\ntools: Read\n---\nThe Write Role Contract forbids that. Read only.",
        [], [], [], [],
    ),
    (
        "a prose parenthetical is not call syntax",
        "---\nname: a\ntools: Read\n---\nThe Write (v5) contract forbids it. Read only.",
        [], [], [], [],
    ),
    (
        "call syntax with no space is a call",
        "---\nname: a\ntools: Read\n---\nEmit Artifact(path) at the end. Read first.",
        ["Artifact"], [], [], [],
    ),
    (
        "declared but never mentioned",
        "---\nname: a\ntools: Read, Write, Grep\n---\nRead the frontmatter and report.",
        [], ["Write", "Grep"], [], [],
    ),
    (
        "tool named only inside a fence does not count as used",
        "---\nname: a\ntools: Bash\n---\nRun it:\n```\nBash\n```\n",
        [], ["Bash"], [], [],
    ),
    (
        "a YAML block list is read like the inline form",
        "---\nname: a\ntools:\n  - Read\n  - Bash\nmodel: haiku\n---\nRead the file, then use Bash to move it.",
        [], [], [], [],
    ),
    (
        "an unknown tool name is reported, mcp__ and scoped forms are not",
        "---\nname: a\ntools: Read, Bash(git diff:*), mcp__foo__bar, Reed\n---\nRead it, then use Bash.",
        [], [], ["Reed"], [],
    ),
    (
        "a read-only body may not hold a write tool",
        "---\nname: a\ntools: Read, Write\n---\nThis agent is read-only by the Write Role Contract. Read and report.",
        [], [], [], ["Write"],
    ),
    (
        "clean agent",
        "---\nname: a\ntools: Read, Bash\n---\nRead the file, then use Bash to move it.",
        [], [], [], [],
    ),
    (
        "no frontmatter is not this guard's problem",
        "just a reference doc",
        [], [], [], [],
    ),
]


def run_self_test():
    failures = []
    for label, text, *want in SELF_TEST_CASES:
        got = check_agent(text)
        if [sorted(g) for g in got] != [sorted(w) for w in want]:
            failures.append((label, got, tuple(want)))
    if failures:
        print("FAIL: check-agent-tools-usage self-test")
        for label, got, want in failures:
            print(f"  {label}: got {got}, want {want}")
        return 1
    print(f"OK: all {len(SELF_TEST_CASES)} check-agent-tools-usage self-test cases passed")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    root = args.root or _git_toplevel() or os.getcwd()
    agent_files = find_agent_files(root)
    if not agent_files:
        print(f"ERROR: no */agents/*.md files found under {root}", file=sys.stderr)
        return 2

    findings = []
    for path in agent_files:
        with open(path, encoding="utf-8") as fh:
            undeclared, unused, unknown, contract = check_agent(fh.read())
        if undeclared or unused or unknown or contract:
            findings.append({
                "file": os.path.relpath(path, root),
                "undeclared": undeclared,
                "unused": unused,
                "unknown": unknown,
                "contract": contract,
            })

    if args.json:
        print(json.dumps({"checked": len(agent_files), "findings": findings}, indent=2))
    elif findings:
        print("FAIL: agent `tools:` does not match body usage:")
        for f in findings:
            print(f"  {f['file']}")
            if f["undeclared"]:
                print(f"    body calls but tools: omits — {', '.join(f['undeclared'])}")
            if f["unused"]:
                print(f"    tools: grants but body never names — {', '.join(f['unused'])}")
            if f["unknown"]:
                print(f"    unknown tool name — {', '.join(f['unknown'])}")
            if f["contract"]:
                print(f"    body claims read-only but grants — {', '.join(f['contract'])}")
    else:
        print(f"OK: all {len(agent_files)} agent(s) declare exactly the tools their body uses")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
