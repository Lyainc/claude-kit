#!/usr/bin/env python3
"""check-agent-tools-usage.py — an agent's `tools:` must match what its body says (#577).

RULE: for every `*/agents/*.md`, the tools declared in frontmatter and the tools the body
actually reaches for must be the same set. Two directions, two different harms:

  UNDECLARED — the body directs the agent to call a tool that `tools:` omits. The call cannot
    happen, so that branch of the agent is dead prose. Found live in vault-searcher.md, whose
    `.vault-link` path-resolution recovery said "use AskUserQuestion" while `tools:` listed only
    Read/Bash/Glob/Grep (#577).

  UNUSED — `tools:` grants a tool the body never reaches for. That is the over-permission #472
    introduced the field to prevent, just re-created one entry at a time. Found live in
    vault-file-organizer.md, which held Write and Grep while its body only moves files and edits
    named frontmatter fields (#577).

`check-agent-tools-field.py` is the sibling guard and deliberately stops at "the key exists and
is non-empty" — its docstring calls this comparison a manual judgment call. This script is that
judgment call, made mechanical.

## How usage is detected, and why the two directions read differently

The body is prose, so neither direction can be inferred perfectly. Each is therefore matched by
the narrowest signal that its own harm needs, and the asymmetry is deliberate:

  UNDECLARED looks only for an *imperative* mention — `use X`, `call X`, `via X`, `X(` — because
    the harm is a directive that cannot execute. A tool merely named in passing ("the Write Role
    Contract", "vault writes are user-initiated") is not a directive and must not be flagged.
    Negations are excluded too: code-reviewer.md says "do not use the `Agent` tool", which is a
    prohibition, not a call.

  UNUSED looks for the tool name appearing *anywhere* in the body, imperative or not. A weaker
    signal is correct here because the direction is inverted: any mention at all is enough to
    show the grant was considered, and demanding an imperative would flag every tool a body
    references indirectly. The residual cost is that a tool used only through an unnamed shell
    command reads as unused — so a body must name the tools it relies on, which is what
    CLAUDE.md's "Adding a New Agent" §2 already asks for.

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
TOOLS_KEY_RE = re.compile(r"^tools:\s*(.*)$", re.MULTILINE)

# Tool names this guard knows about. A name outside this set in `tools:` is reported as
# unknown rather than silently ignored — a typo'd grant is still a grant that does nothing.
KNOWN_TOOLS = [
    "Agent", "AskUserQuestion", "Bash", "BashOutput", "Edit", "Glob", "Grep",
    "KillShell", "NotebookEdit", "Read", "Skill", "SlashCommand", "Task",
    "TodoWrite", "WebFetch", "WebSearch", "Write",
]

# An imperative reach for a tool: `use X` / `call X` / `invoke X` / `via X` / `through X`,
# optionally with the name in backticks, or a call-shaped `X(`. Case-insensitive on the verb
# only — the tool name itself stays exact so `write` the verb never reads as `Write` the tool.
_VERBS = r"(?:use|uses|using|call|calls|calling|invoke|invokes|invoking|via|through)"
# Up to two filler words between verb and tool ("use the `X` tool", "call into X").
_FILLER = r"(?:\s+(?:a|an|the|into|to|with|by)){0,2}"
NEGATORS = ("not", "never", "n't", "without", "cannot", "no")


def _imperative_re(tool):
    return re.compile(
        r"(?:(?P<lead>[^.\n]{0,60}?)\b" + _VERBS + _FILLER + r"\s+`?" + re.escape(tool) + r"`?\b)"
        r"|(?:\b" + re.escape(tool) + r"\s*\()",
        re.IGNORECASE if False else 0,
    )


def _mention_re(tool):
    return re.compile(r"\b" + re.escape(tool) + r"\b")


def _is_negated(lead):
    """True when the clause leading up to the verb negates it."""
    if lead is None:
        return False
    tail = lead.lower()[-40:]
    return any(re.search(r"\b" + re.escape(n) + r"\b", tail) for n in NEGATORS) or "n't" in tail


def split_frontmatter(text):
    """Return (frontmatter, body) or (None, None) when there is no frontmatter."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def declared_tools(frontmatter):
    tm = TOOLS_KEY_RE.search(frontmatter or "")
    if not tm:
        return []
    return [t.strip() for t in tm.group(1).split(",") if t.strip()]


def strip_noise(body):
    """Drop spans that name tools without reaching for them.

    Fenced code blocks are shell/YAML samples, and an HTML comment is authoring scaffolding —
    a tool name in either is not the body directing itself.
    """
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    return body


def check_agent(text):
    """Return (undeclared, unused, unknown) tool-name lists for one agent .md."""
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        return [], [], []
    declared = declared_tools(frontmatter)
    known_declared = [t for t in declared if t in KNOWN_TOOLS]
    unknown = [t for t in declared if t not in KNOWN_TOOLS]
    body = strip_noise(body or "")

    undeclared = []
    for tool in KNOWN_TOOLS:
        if tool in declared:
            continue
        for m in _imperative_re(tool).finditer(body):
            if not _is_negated(m.groupdict().get("lead")):
                undeclared.append(tool)
                break

    unused = [t for t in known_declared if not _mention_re(t).search(body)]
    return undeclared, unused, unknown


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


def run_self_test():
    cases = [
        # (label, text, expected_undeclared, expected_unused)
        (
            "imperative mention of an undeclared tool",
            "---\nname: a\ntools: Read\n---\nuse AskUserQuestion to confirm the path.\nRead it.",
            ["AskUserQuestion"], [],
        ),
        (
            "backticked imperative, filler words",
            "---\nname: a\ntools: Read\n---\nThen call the `Skill` tool. Read the file.",
            ["Skill"], [],
        ),
        (
            "negated mention is not a call",
            "---\nname: a\ntools: Read\n---\nDo not use the `Agent` tool here. Read the diff.",
            [], [],
        ),
        (
            "passing mention is not a call",
            "---\nname: a\ntools: Read\n---\nThe Write Role Contract forbids that. Read only.",
            [], [],
        ),
        (
            "declared but never mentioned",
            "---\nname: a\ntools: Read, Write, Grep\n---\nRead the frontmatter and report.",
            [], ["Write", "Grep"],
        ),
        (
            "tool named only inside a fence does not count as used",
            "---\nname: a\ntools: Bash\n---\nRun it:\n```\nBash\n```\n",
            [], ["Bash"],
        ),
        (
            "clean agent",
            "---\nname: a\ntools: Read, Bash\n---\nRead the file, then use Bash to move it.",
            [], [],
        ),
        (
            "no frontmatter is not this guard's problem",
            "just a reference doc",
            [], [],
        ),
    ]
    failures = []
    for label, text, want_undeclared, want_unused in cases:
        got_undeclared, got_unused, _ = check_agent(text)
        if sorted(got_undeclared) != sorted(want_undeclared) or sorted(got_unused) != sorted(want_unused):
            failures.append((label, (got_undeclared, got_unused), (want_undeclared, want_unused)))
    if failures:
        print("FAIL: check-agent-tools-usage self-test")
        for label, got, want in failures:
            print(f"  {label}: got {got}, want {want}")
        return 1
    print(f"OK: all {len(cases)} check-agent-tools-usage self-test cases passed")
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
            undeclared, unused, unknown = check_agent(fh.read())
        if undeclared or unused or unknown:
            findings.append({
                "file": os.path.relpath(path, root),
                "undeclared": undeclared,
                "unused": unused,
                "unknown": unknown,
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
    else:
        print(f"OK: all {len(agent_files)} agent(s) declare exactly the tools their body uses")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
