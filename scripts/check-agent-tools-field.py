#!/usr/bin/env python3
"""check-agent-tools-field.py — agent frontmatter must declare `tools:` (#472).

RULE: every `*/agents/*.md` file's YAML frontmatter must have an explicit `tools:` key.
With no `tools:` field, an agent inherits every tool available in the harness (Write,
Edit, Agent, every connected MCP server) regardless of what its own body says it is
allowed to do — the Write Role Contract two agents declared in prose (vault-knowledge-manager,
thinking-facilitator) was unenforced until #472 scoped their frontmatter. This is a BLOCK
guard so a new or edited agent can't silently regress back to "no tools: field = inherits
everything".

This only checks that the key EXISTS (and is non-empty) — it does not judge whether the
listed tools match what the agent body actually uses. That judgment call is manual (see
#472's issue body for the reasoning behind each agent's chosen list).

Usage:
    python3 scripts/check-agent-tools-field.py [--root DIR] [--json] [--self-test]

    --root DIR    Repo root to check (default: git toplevel, else CWD). Scans
                  DIR/*/agents/*.md.
    --json        Emit a machine-readable JSON report instead of text.
    --self-test   Validate the frontmatter-parsing logic in-memory against fixture
                  strings (missing tools:, empty tools:, present tools:) and exit 0
                  only if every case is detected as expected.

Exit codes: 0 = every agent has a non-empty tools: field (or --self-test passed),
            1 = at least one agent is missing it, 2 = usage error / no agents found.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
# `[ \t]*` and not `\s*`: `\s*` crosses the newline, so a bare `tools:` followed by any other
# frontmatter key captured THAT line as the value and reported the agent as non-empty — the
# #472 harm passing silently. Caught by #611's review; the sibling usage guard already carried
# this note. The block-list form has to keep working, so an empty inline value falls through to
# the item check below rather than being rejected outright.
TOOLS_KEY_RE = re.compile(r"^tools:[ \t]*(.*)$", re.MULTILINE)
TOOLS_BLOCK_ITEM_RE = re.compile(r"^[ \t]*-[ \t]*(\S.*?)[ \t]*$")


def _block_items(rest):
    """Yield the YAML block-list items following the key, skipping blanks and comments.

    A comment or blank line between `tools:` and its first `- Read` is valid YAML, so stopping
    at the first non-item line would reject a correct declaration. The scan still stops at the
    next real key, which is what keeps an empty `tools:` from borrowing the line below it.
    """
    for line in rest.lstrip("\r\n").split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = TOOLS_BLOCK_ITEM_RE.match(line)
        if not item:
            return
        yield item.group(1)


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


def check_tools_field(text):
    """Return (has_field, is_nonempty) for an agent .md file's contents."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False, False
    frontmatter = m.group(1)
    tm = TOOLS_KEY_RE.search(frontmatter)
    if not tm:
        return False, False
    value = tm.group(1).split("#", 1)[0].strip()
    if value:
        return True, True
    return True, any(_block_items(frontmatter[tm.end():]))


def run_self_test():
    cases = [
        ("---\nname: foo\nmodel: sonnet\n---\nbody", False, False),  # missing key
        ("---\nname: foo\ntools:\n---\nbody", True, False),          # empty value
        ("---\nname: foo\ntools: Read, Grep\n---\nbody", True, True),  # present
        ("no frontmatter at all", False, False),
        # An empty value followed by another key: `\s*` used to capture `model: x` here.
        ("---\nname: foo\ntools:\nmodel: x\n---\nbody", True, False),
        ("---\nname: foo\ntools:\n  - Read\n  - Bash\n---\nbody", True, True),  # block list
        ("---\nname: foo\ntools:  # none yet\nmodel: x\n---\nbody", True, False),
        # A comment or blank line before the first item is valid YAML.
        ("---\nname: foo\ntools:\n  # the list\n  - Read\n---\nbody", True, True),
    ]
    failures = []
    for text, expect_has, expect_nonempty in cases:
        has, nonempty = check_tools_field(text)
        if (has, nonempty) != (expect_has, expect_nonempty):
            failures.append((text[:30], (has, nonempty), (expect_has, expect_nonempty)))
    if failures:
        print("FAIL: check-agent-tools-field self-test")
        for snippet, got, want in failures:
            print(f"  {snippet!r}: got {got}, want {want}")
        return 1
    print("OK: all check-agent-tools-field self-test cases passed")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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

    missing = []
    for path in agent_files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        has, nonempty = check_tools_field(text)
        if not (has and nonempty):
            missing.append(os.path.relpath(path, root))

    if args.json:
        print(json.dumps({"checked": len(agent_files), "missing_tools_field": missing}, indent=2))
    else:
        if missing:
            print("FAIL: agents missing a non-empty `tools:` frontmatter field:")
            for rel in missing:
                print(f"  {rel}")
        else:
            print(f"OK: all {len(agent_files)} agent(s) declare `tools:`")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
