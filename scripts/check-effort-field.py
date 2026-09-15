#!/usr/bin/env python3
"""check-effort-field.py — every agents/*.md must declare `effort:` (#648, narrowed by #751).

RULE: every `*/agents/*.md` file's YAML frontmatter must have an explicit, non-empty
`effort:` key. Without it, the agent inherits the whole session's effort dial instead of
a value tuned to what it actually does — #448 established that an effort override is
preferred over a `model:` tier downgrade. This is a BLOCK guard so a new or edited agent
can't silently land without one.

#648 originally mandated the same key on `*/skills/*/SKILL.md` too. #751 found the
opposite is true there: a SKILL.md `effort:` that differs from the session's ambient
effort regenerates the WHOLE main-context messages cache on every call the skill is
invoked (measured: 83% collapse rate when the value transitions, 1-hour-TTL cache
writes billed at 20x a read) — so a skill should OMIT `effort:` and inherit ambient
unless it deliberately matches it. A subagent has no such cost: it runs in its own
context, never touching the main cache, so #648's original mandate stands for agents.

This only checks that the key EXISTS and is non-empty — it does not judge whether the
value (low/medium/high/xhigh/max) is the right one for what the agent does. That
judgment call is manual (see #648's issue body for the reasoning behind each site's
chosen value). Same shape as check-agent-tools-field.py (#472).

Usage:
    python3 scripts/check-effort-field.py [--root DIR] [--json] [--self-test]

    --root DIR    Repo root to check (default: git toplevel, else CWD). Scans
                  DIR/*/agents/*.md only — */skills/*/SKILL.md is #751's opposite case,
                  checked (as a warning, not a block) by check-skill-token-budget.py.
    --json        Emit a machine-readable JSON report instead of text.
    --self-test   Validate the frontmatter-parsing logic in-memory against fixture
                  strings (missing effort:, empty effort:, present effort:) and exit 0
                  only if every case is detected as expected.

Exit codes: 0 = every agent has a non-empty effort: field (or --self-test passed),
            1 = at least one is missing it, 2 = usage error / no files found.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
# `[ \t]*`, not `\s*` — `\s*` crosses the newline, so a bare `effort:` followed by another
# frontmatter key would capture THAT line as the value and report non-empty (the #472 harm,
# same bug class, see check-agent-tools-field.py's note).
EFFORT_KEY_RE = re.compile(r"^effort:[ \t]*(.*)$", re.MULTILINE)


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_target_files(root):
    # #751: SKILL.md is deliberately NOT scanned here — see module docstring.
    return sorted(glob.glob(os.path.join(root, "*", "agents", "*.md")))


def check_effort_field(text):
    """Return (has_field, is_nonempty) for a SKILL.md/agent .md file's contents."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False, False
    frontmatter = m.group(1)
    em = EFFORT_KEY_RE.search(frontmatter)
    if not em:
        return False, False
    value = em.group(1).split("#", 1)[0].strip()
    return True, bool(value)


def run_self_test():
    cases = [
        ("---\nname: foo\nmodel: sonnet\n---\nbody", False, False),  # missing key
        ("---\nname: foo\neffort:\n---\nbody", True, False),          # empty value
        ("---\nname: foo\neffort: low\n---\nbody", True, True),       # present
        ("no frontmatter at all", False, False),
        # An empty value followed by another key: `\s*` used to capture `model: x` here.
        ("---\nname: foo\neffort:\nmodel: x\n---\nbody", True, False),
        ("---\nname: foo\neffort: medium  # some comment\n---\nbody", True, True),
        ("---\nname: foo\neffort:  # none yet\nmodel: x\n---\nbody", True, False),
    ]
    failures = []
    for text, expect_has, expect_nonempty in cases:
        has, nonempty = check_effort_field(text)
        if (has, nonempty) != (expect_has, expect_nonempty):
            failures.append((text[:30], (has, nonempty), (expect_has, expect_nonempty)))
    # #751: find_target_files must scan agents/*.md only — a SKILL.md with or without
    # effort: must never appear, or this guard re-imposes the mandate #751 just lifted.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        plugin = os.path.join(tmp, "fixture-plugin")
        os.makedirs(os.path.join(plugin, "skills", "x"))
        os.makedirs(os.path.join(plugin, "agents"))
        with open(os.path.join(plugin, "skills", "x", "SKILL.md"), "w") as fh:
            fh.write("---\nname: x\n---\nbody")
        with open(os.path.join(plugin, "agents", "y.md"), "w") as fh:
            fh.write("---\nname: y\neffort: low\n---\nbody")
        found = find_target_files(tmp)
        expected = [os.path.join(plugin, "agents", "y.md")]
        if found != expected:
            failures.append(("find_target_files scope", found, expected))

    if failures:
        print("FAIL: check-effort-field self-test")
        for snippet, got, want in failures:
            print(f"  {snippet!r}: got {got}, want {want}")
        return 1
    print("OK: all check-effort-field self-test cases passed")
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
    target_files = find_target_files(root)
    if not target_files:
        print(f"ERROR: no */agents/*.md files found under {root}", file=sys.stderr)
        return 2

    missing = []
    for path in target_files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        has, nonempty = check_effort_field(text)
        if not (has and nonempty):
            missing.append(os.path.relpath(path, root))

    if args.json:
        print(json.dumps({"checked": len(target_files), "missing_effort_field": missing}, indent=2))
    else:
        if missing:
            print("FAIL: agent(s) missing a non-empty `effort:` frontmatter field:")
            for rel in missing:
                print(f"  {rel}")
        else:
            print(f"OK: all {len(target_files)} agent(s) declare `effort:`")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
