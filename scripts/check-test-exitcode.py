#!/usr/bin/env python3
"""check-test-exitcode.py — CLAUDE.md-registered test exit-code runner (slice S4).

RULE: CLAUDE.md's `## Validation` section is the canonical list of regression-guard
commands for this repo. This tool extracts the actual runnable command strings from that
section's fenced code blocks (skipping comments / pure-comment lines / inline-comment
tails) and provides a runner that executes each command and asserts it exits 0, reporting
every command whose exit code is nonzero.

OBJECTIVE DAMAGE (c6): a test that is *registered* in CLAUDE.md but has silently broken
(nonzero exit) is a dead regression guard — the protection it documents no longer holds,
yet the docs still claim it does. That divergence is objective damage, not taste: the
claimed safety net is a lie. CI already runs these tests directly; this script is a LOCAL
pre-push convenience that runs the *documented* list as a single batch and fails if any
documented command does not exit 0. It does not encode any style/format preference — it
only runs what CLAUDE.md already declares runnable and checks the OS exit code.

Note (scope): the extractor returns command strings verbatim so the runner executes the
exact thing CLAUDE.md documents. It joins trailing-backslash continuations, strips inline
comment tails, and skips blank / pure-comment lines. It does NOT try to model shell
semantics (env-var prefixes, pipes, redirects are passed straight to `bash -c`).

Usage:
    python3 scripts/check-test-exitcode.py [--root DIR] [--list] [--json]
                                           [--timeout SEC] [--self-test]

    --root DIR    Repo root (default: git toplevel, else CWD). Reads DIR/CLAUDE.md and
                  runs each extracted command with cwd=DIR.
    --list        Print the extracted commands (one per line) and exit WITHOUT running
                  them. Fast, side-effect-free — use to inspect what would run.
    --timeout SEC Per-command timeout in seconds (default: 300). A timeout counts as a
                  failure for that command.
    --json        Emit a machine-readable JSON report.
    --self-test   Validate the RUNNER logic in-memory with fake commands (one exits 0,
                  one exits 1) and assert the runner reports exactly the failing one.

Exit codes:
    0 = all extracted commands exited 0 (or --list / --self-test succeeded)
    1 = at least one command failed (nonzero exit / timeout), or self-test mismatch
    2 = usage error / CLAUDE.md unreadable / no '## Validation' section
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Reuse the section locator from the CI-coverage guard (it already pins the exact
# `## Validation` block + fenced-only text). We need the RAW command strings (not the
# normalized ids), so the command extractor below is our own.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from importlib import import_module

_ci = import_module("check-ci-coverage")
extract_validation_section = _ci.extract_validation_section
_join_continuations = _ci._join_continuations

# Lines that are runnable commands begin with one of these tokens (optionally after an
# env-var assignment prefix like `FOO=bar `). Anything else inside the fenced block
# (prose, stray words) is ignored — we only run what looks like an actual command.
_CMD_HEAD = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"      # zero+ ENV=val prefixes
    r"(python3|bash|find|rm|claude)\b"          # a known command head
)


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def extract_commands(section_text):
    """Extract the ordered list of raw runnable command strings from section text.

    Joins trailing-backslash continuations, skips blank and pure-comment lines, strips a
    trailing inline-comment tail (` # ...`), and keeps only lines whose head is a known
    runnable command. Returns command strings verbatim (de-duplicated by first
    occurrence so the runner does not run the same command twice).
    """
    commands = []
    seen = set()
    for raw in _join_continuations(section_text):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # drop a trailing inline comment (` # ...`); safe for these command shapes
        comment = re.search(r"\s#\s", line)
        if comment:
            line = line[: comment.start()].rstrip()
        if not line or not _CMD_HEAD.match(line):
            continue
        if line not in seen:
            seen.add(line)
            commands.append(line)
    return commands


def get_commands(root):
    """Read root/CLAUDE.md, locate ## Validation, return (commands, error_or_None)."""
    claude_path = os.path.join(root, "CLAUDE.md")
    if not os.path.isfile(claude_path):
        return None, f"CLAUDE.md not found: {claude_path}"
    try:
        with open(claude_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return None, f"CLAUDE.md unreadable: {exc}"
    section = extract_validation_section(text)
    if section is None:
        return None, "CLAUDE.md has no '## Validation' section"
    return extract_commands(section), None


def run_commands(commands, cwd, timeout):
    """Run each command via `bash -c` with the given cwd. Returns a report dict.

    A command is a failure if it exits nonzero or times out. Each result records the
    command, its exit code (None on timeout), and whether it passed.
    """
    results = []
    for cmd in commands:
        entry = {"command": cmd, "exit": None, "passed": False, "timed_out": False}
        try:
            proc = subprocess.run(
                ["bash", "-c", cmd],
                cwd=cwd, capture_output=True, text=True, timeout=timeout,
            )
            entry["exit"] = proc.returncode
            entry["passed"] = proc.returncode == 0
            if not entry["passed"]:
                entry["stderr_tail"] = (proc.stderr or "").strip()[-500:]
        except subprocess.TimeoutExpired:
            entry["timed_out"] = True
            entry["passed"] = False
        results.append(entry)
    failures = [r for r in results if not r["passed"]]
    return {
        "cwd": cwd,
        "total": len(results),
        "results": results,
        "failures": failures,
        "ok": len(failures) == 0,
    }


def run_self_test():
    """Validate the RUNNER logic in-memory with fake commands (no CLAUDE.md needed).

    One command exits 0, one exits 1; assert the runner reports exactly the failing one.
    Also exercise the command extractor on a synthetic section.
    """
    failures = []

    # 1) Runner: exactly the exit-1 command must be reported as a failure.
    ok_cmd = 'python3 -c "pass"'
    bad_cmd = 'python3 -c "import sys;sys.exit(1)"'
    report = run_commands([ok_cmd, bad_cmd], cwd=os.getcwd(), timeout=30)
    if report["ok"]:
        failures.append("  runner: expected overall failure, got ok=True")
    failed_cmds = [r["command"] for r in report["failures"]]
    if failed_cmds != [bad_cmd]:
        failures.append(
            f"  runner: expected exactly [{bad_cmd!r}] to fail, got {failed_cmds}"
        )
    ok_entry = next((r for r in report["results"] if r["command"] == ok_cmd), None)
    if not ok_entry or ok_entry["exit"] != 0 or not ok_entry["passed"]:
        failures.append("  runner: the exit-0 command was not reported as passed")

    # 2) Timeout counts as a failure.
    to_report = run_commands(['python3 -c "import time;time.sleep(5)"'],
                             cwd=os.getcwd(), timeout=1)
    if to_report["ok"] or not to_report["results"][0]["timed_out"]:
        failures.append("  runner: a timed-out command was not reported as a failure")

    # 3) Extractor: pull only runnable commands, skip comments/prose/inline-tails,
    #    join continuations, keep env-prefixed lines, de-dup.
    section = "\n".join([
        'python3 scripts/foo.py --self-test',
        '# python3 scripts/commented-out.py',
        'OVM_FIXTURE_DIR=/tmp/x \\',
        '  bash scripts/test/gen.sh --with-audit-errors',
        'python3 scripts/bar.py  # Expected: OK',
        'just some prose that is not a command',
        'find a/b -name "SKILL.md" | sort',
        'python3 scripts/foo.py --self-test',   # duplicate of line 1
    ])
    cmds = extract_commands(section)
    expected = [
        'python3 scripts/foo.py --self-test',
        'OVM_FIXTURE_DIR=/tmp/x    bash scripts/test/gen.sh --with-audit-errors',
        'python3 scripts/bar.py',
        'find a/b -name "SKILL.md" | sort',
    ]
    if cmds != expected:
        failures.append(f"  extractor: expected {expected}, got {cmds}")

    # 4) Extractor: a section with no commands yields [].
    if extract_commands("# only comments\n\nplain prose\n") != []:
        failures.append("  extractor: comment/prose-only section should yield no commands")

    if failures:
        print("FAIL: check-test-exitcode self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-test-exitcode self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run CLAUDE.md-registered Validation commands and assert exit 0"
    )
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--list", action="store_true",
                        help="print extracted commands without running them")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--timeout", type=int, default=300,
                        help="per-command timeout in seconds (default: 300)")
    parser.add_argument("--self-test", action="store_true",
                        help="validate the runner logic in-memory")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    commands, err = get_commands(root)
    if err is not None:
        if args.json:
            print(json.dumps({"root": root, "error": err, "ok": False}, ensure_ascii=False))
        else:
            print(f"ERROR: {err}")
        return 2

    if args.list:
        if args.json:
            print(json.dumps({"root": root, "commands": commands}, ensure_ascii=False, indent=2))
        else:
            for cmd in commands:
                print(cmd)
            print(f"# {len(commands)} command(s) extracted from CLAUDE.md ## Validation "
                  "(not run)", file=sys.stderr)
        return 0

    report = run_commands(commands, cwd=root, timeout=args.timeout)
    report["root"] = root

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        passed = report["total"] - len(report["failures"])
        if report["ok"]:
            print(f"OK: check-test-exitcode clean — {report['total']} registered "
                  f"command(s) ran, all exited 0")
        else:
            print(f"FAIL: {len(report['failures'])}/{report['total']} registered "
                  f"command(s) did NOT exit 0 ({passed} passed):")
            for r in report["failures"]:
                why = "timeout" if r["timed_out"] else f"exit {r['exit']}"
                print(f"  - [{why}] {r['command']}")
            print("Fix: repair the broken test or remove it from CLAUDE.md's Validation "
                  "section if it is intentionally retired.")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
