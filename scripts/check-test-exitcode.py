#!/usr/bin/env python3
"""check-test-exitcode.py — docs/VALIDATION.md-registered test exit-code runner (slice S4).

RULE: docs/VALIDATION.md's `## Validation` section is the canonical list of regression-guard
commands for this repo. This tool extracts the actual runnable command strings from that
section's fenced code blocks (skipping comments / pure-comment lines / inline-comment
tails) and provides a runner that executes each command, asserts it exits 0, and — when the
command is immediately followed by a `# Expected: ...` comment — asserts its stdout matches
that text too. Reports every command whose exit code is nonzero or whose stdout diverges.

OBJECTIVE DAMAGE (c6): a test that is *registered* in docs/VALIDATION.md but has silently
broken (nonzero exit) is a dead regression guard — the protection it documents no longer
holds, yet the docs still claim it does. That divergence is objective damage, not taste:
the claimed safety net is a lie. CI already runs these tests directly; this script is a
LOCAL pre-push convenience that runs the *documented* list as a single batch and fails if
any documented command does not exit 0. It does not encode any style/format preference —
it only runs what docs/VALIDATION.md already declares runnable and checks the OS exit code.

OBJECTIVE DAMAGE, part 2 (#578): the exit-code check above says nothing about the
`# Expected: ...` comment that follows most commands — nothing ever compared it to real
stdout, so it silently rots. #577 needed its self-test count comment hand-fixed 3 times as
the count grew; a reviewer catching every one was luck, not enforcement. This adds that
comparison, with three buckets so a mismatch caused by inherent per-run variance (a file
count, a case count, a filesystem path) isn't confused with a mismatch caused by the doc
just being wrong:
  1. The `# Expected:` text contains no placeholder (no standalone `N`, no `...`) → the
     command's stdout must match it EXACTLY (after whitespace normalization), anchored to
     the END of stdout (most commands print several progress lines before their final
     summary; only the summary is documented, so matching is tail-anchored, not full-string).
  2. It contains a placeholder → `N` becomes `\\d+` and `...` becomes `.*` before matching,
     so a self-test case count or a checked-file count or a machine-specific path doesn't
     make the guard flap.
  3. The command has NO `# Expected:` comment at all → skipped, and the skip count is
     always printed (never silently), because a silent skip is exactly the "looks enforced,
     isn't" gap this guard exists to close.
A multi-line `# Expected:` (a `#   `-indented, 3+-space continuation right after it) is
joined with spaces into one logical expected string — that's wrapping for readability in
the .md, not multiple stdout lines.

Note (scope): the extractor returns command strings verbatim so the runner executes the
exact thing docs/VALIDATION.md documents. It joins trailing-backslash continuations, strips
inline comment tails, and skips blank / pure-comment lines. It does NOT try to model shell
semantics (env-var prefixes, pipes, redirects are passed straight to `bash -c`).

Usage:
    python3 scripts/check-test-exitcode.py [--root DIR] [--list] [--json]
                                           [--timeout SEC] [--self-test]

    --root DIR    Repo root (default: git toplevel, else CWD). Reads DIR/docs/VALIDATION.md
                  and runs each extracted command with cwd=DIR.
    --list        Print the extracted commands (one per line) and exit WITHOUT running
                  them. Fast, side-effect-free — use to inspect what would run.
    --timeout SEC Per-command timeout in seconds (default: 300). A timeout counts as a
                  failure for that command.
    --json        Emit a machine-readable JSON report.
    --self-test   Validate the RUNNER + Expected-text matcher logic in-memory with fake
                  commands/fixtures.

Exit codes:
    0 = all extracted commands exited 0 and every `# Expected:` text matched (or --list /
        --self-test succeeded)
    1 = at least one command failed (nonzero exit / timeout / stdout mismatch), or
        self-test mismatch
    2 = usage error / docs/VALIDATION.md unreadable / no '## Validation' section
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
import importlib.util

# Canonical pattern for loading a script whose filename isn't a valid module
# identifier (hyphenated): spec_from_file_location, not import_module("check-ci-coverage").
_ci_spec = importlib.util.spec_from_file_location(
    "check_ci_coverage", os.path.join(_HERE, "check-ci-coverage.py")
)
_ci = importlib.util.module_from_spec(_ci_spec)
_ci_spec.loader.exec_module(_ci)
extract_validation_section = _ci.extract_validation_section
_join_continuations = _ci._join_continuations

# Lines that are runnable commands begin with one of these tokens (optionally after an
# env-var assignment prefix like `FOO=bar `). Anything else inside the fenced block
# (prose, stray words) is ignored — we only run what looks like an actual command.
_CMD_HEAD = re.compile(
    r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"      # zero+ ENV=val prefixes
    r"(python3|bash|find|rm|claude|uv)\b"       # a known command head
    # `uv` earns its place: check-skill-token-budget is registered as
    # `uv run --with tiktoken python3 ...` so CI and local run the identical command. Without
    # it here the line is not a command, so the suite silently stopped running that guard
    # while still reporting "all exited 0" — the same silent-skip failure #447 is about.
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


# The comment immediately after a command, if it starts with this, documents that
# command's expected stdout. A 3+-space-indented `#` line right after it is a wrapped
# continuation of the same text (word-wrap for .md readability, not a second stdout line);
# a single-space `# ...` comment, a blank line, or the next command all end the block.
_EXPECTED_RE = re.compile(r"^#\s*Expected:\s*(.*)$")
_CONTINUATION_RE = re.compile(r"^#\s{3,}(\S.*)$")


def extract_command_expected_pairs(section_text):
    """Pair each extracted command with its immediately-following `# Expected:` text.

    Same extraction rules as extract_commands (continuations joined, comment/blank lines
    skipped, inline-comment tails stripped, de-duplicated by first occurrence). Returns an
    ordered list of (command, expected_or_None); `expected` is whitespace-normalized and
    has any 3+-space continuation lines folded in.
    """
    lines = _join_continuations(section_text)
    n = len(lines)
    pairs = []
    seen = set()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        comment = re.search(r"\s#\s", line)
        if comment:
            line = line[: comment.start()].rstrip()
        if not line or not _CMD_HEAD.match(line) or line in seen:
            continue
        seen.add(line)
        expected = None
        j = i + 1
        if j < n:
            m = _EXPECTED_RE.match(lines[j].strip())
            if m:
                parts = [m.group(1)]
                j += 1
                while j < n:
                    cm = _CONTINUATION_RE.match(lines[j])
                    if not cm:
                        break
                    parts.append(cm.group(1))
                    j += 1
                expected = " ".join(" ".join(parts).split())
        pairs.append((line, expected))
    return pairs


def extract_commands(section_text):
    """Extract the ordered list of raw runnable command strings from section text.

    Joins trailing-backslash continuations, skips blank and pure-comment lines, strips a
    trailing inline-comment tail (` # ...`), and keeps only lines whose head is a known
    runnable command. Returns command strings verbatim (de-duplicated by first
    occurrence so the runner does not run the same command twice).
    """
    return [cmd for cmd, _ in extract_command_expected_pairs(section_text)]


def _expected_pattern(expected):
    """Compile `# Expected:` text into a tail-anchored regex honoring N/... placeholders.

    A standalone `N` becomes `\\d+` (a variable count); `...` becomes `.*` (elided/variable
    text — a path, a file list). Everything else is matched literally. Anchored to the END
    of the (whitespace-collapsed) stdout, not the start: most commands print progress lines
    before their final summary, and only the summary is documented here.
    """
    out = []
    for part in re.split(r"(\.\.\.|\bN\b)", expected):
        if part == "...":
            out.append(".*")
        elif part == "N":
            out.append(r"\d+")
        else:
            out.append(re.escape(part))
    return re.compile("".join(out) + r"\s*\Z")


def expected_matches(stdout, expected):
    """True if stdout's tail matches the (placeholder-aware) `# Expected:` text."""
    normalized = " ".join((stdout or "").split())
    return _expected_pattern(expected).search(normalized) is not None


def failure_reason(entry):
    """Classify why a run_commands() result entry failed, root cause first.

    A crash (nonzero exit) is the root cause even when its partial/garbage stdout also
    happens to fail the Expected match — report it as the crash, not a "stdout mismatch"
    that reads like nothing more than a stale doc comment.
    """
    if entry["timed_out"]:
        return "timeout"
    if entry["exit"] != 0:
        return f"exit {entry['exit']}"
    if entry["expected_ok"] is False:
        return "stdout mismatch"
    return f"exit {entry['exit']}"


def get_commands(root):
    """Read root/docs/VALIDATION.md, locate ## Validation, return (pairs, error_or_None).

    Each pair is (command, expected_or_None) — see extract_command_expected_pairs.
    """
    validation_path = os.path.join(root, "docs", "VALIDATION.md")
    if not os.path.isfile(validation_path):
        return None, f"docs/VALIDATION.md not found: {validation_path}"
    try:
        with open(validation_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return None, f"docs/VALIDATION.md unreadable: {exc}"
    section = extract_validation_section(text)
    if section is None:
        return None, "docs/VALIDATION.md has no '## Validation' section"
    return extract_command_expected_pairs(section), None


def run_commands(commands, cwd, timeout):
    """Run each command via `bash -c` with the given cwd. Returns a report dict.

    `commands` is a list of either plain command strings or (command, expected_or_None)
    pairs. A command is a failure if it exits nonzero, times out, OR (when it carries a
    `# Expected:` text) its stdout doesn't match. `skipped_no_expected` counts commands
    with no `# Expected:` text at all — always reported, never silent (#578).
    """
    results = []
    skipped_no_expected = 0
    for item in commands:
        cmd, expected = item if isinstance(item, tuple) else (item, None)
        entry = {
            "command": cmd, "exit": None, "passed": False, "timed_out": False,
            "expected": expected, "expected_ok": None,
        }
        if expected is None:
            skipped_no_expected += 1
        try:
            proc = subprocess.run(
                ["bash", "-c", cmd],
                cwd=cwd, capture_output=True, text=True, timeout=timeout,
            )
            entry["exit"] = proc.returncode
            exit_ok = proc.returncode == 0
            if expected is not None:
                entry["expected_ok"] = expected_matches(proc.stdout, expected)
            entry["passed"] = exit_ok and entry["expected_ok"] is not False
            if not exit_ok:
                entry["stderr_tail"] = (proc.stderr or "").strip()[-500:]
            if entry["expected_ok"] is False:
                entry["stdout_tail"] = (proc.stdout or "").strip()[-500:]
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
        "skipped_no_expected": skipped_no_expected,
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

    # 5) Pair extractor: single-line Expected, multi-line (continuation) Expected, a
    #    single-space comment ending the continuation, and no-Expected-at-all.
    pair_section = "\n".join([
        'python3 scripts/foo.py',
        '# Expected: OK: foo clean',
        'python3 scripts/bar.py',
        '# Expected: OK: bar clean — N file(s)',
        '#   checked, no violations',
        '# a regular single-space comment does not extend the block',
        'python3 scripts/baz.py',
    ])
    pairs = extract_command_expected_pairs(pair_section)
    expected_pairs = [
        ('python3 scripts/foo.py', 'OK: foo clean'),
        ('python3 scripts/bar.py', 'OK: bar clean — N file(s) checked, no violations'),
        ('python3 scripts/baz.py', None),
    ]
    if pairs != expected_pairs:
        failures.append(f"  pair extractor: expected {expected_pairs}, got {pairs}")

    # 6) Matcher: fixed text needs an exact tail match; N/... are wildcards; a prefix of
    #    progress lines before the documented summary is fine (tail-anchored, not full-string).
    match_cases = [
        ("OK: clean", "OK: clean", True),
        ("OK: clean", "noise\nOK: clean", True),          # tail-anchored past a prefix line
        ("OK: clean", "OK: clean\nextra", False),          # but not past a SUFFIX line
        ("OK: all N cases passed", "OK: all 42 cases passed", True),
        ("OK: N file(s), ...", "OK: 3 file(s), no violations (1 term)", True),
        ("OK: version clean (root: ...)", "OK: version clean (root: /tmp/x)", True),
        ("OK: all 7 cases passed", "OK: all 8 cases passed", False),  # stale literal count
    ]
    for expected_text, stdout, want in match_cases:
        got = expected_matches(stdout, expected_text)
        if got != want:
            failures.append(
                f"  matcher: expected_matches({stdout!r}, {expected_text!r}) "
                f"= {got}, want {want}"
            )

    # 7) Runner: a documented command whose stdout doesn't match its Expected text fails,
    #    even with exit 0 — and a command with no Expected text is counted as skipped, not
    #    silently treated as passing evidence of anything.
    mismatch_cmd = 'python3 -c "print(\'OK: wrong text\')"'
    match_cmd = 'python3 -c "print(\'OK: right text\')"'
    no_expected_cmd = 'python3 -c "pass"'
    exp_report = run_commands(
        [(mismatch_cmd, "OK: right text"), (match_cmd, "OK: right text"), no_expected_cmd],
        cwd=os.getcwd(), timeout=30,
    )
    if exp_report["ok"]:
        failures.append("  runner: a stdout/Expected mismatch should fail the batch")
    if exp_report["skipped_no_expected"] != 1:
        failures.append(
            f"  runner: expected skipped_no_expected=1, got {exp_report['skipped_no_expected']}"
        )
    mismatch_entry = next(r for r in exp_report["results"] if r["command"] == mismatch_cmd)
    if mismatch_entry["passed"] or mismatch_entry["expected_ok"] is not False:
        failures.append("  runner: the mismatching command was not reported as a failure")
    match_entry = next(r for r in exp_report["results"] if r["command"] == match_cmd)
    if not match_entry["passed"] or match_entry["expected_ok"] is not True:
        failures.append("  runner: the matching command was not reported as passed")

    # 8) failure_reason: a crash (nonzero exit) outranks a coincidental stdout mismatch —
    #    a command that both exits nonzero AND fails its Expected match is a crash, not a
    #    "stdout mismatch" (a crash's garbage output will almost never match the doc anyway).
    reason_cases = [
        ({"timed_out": True, "exit": None, "expected_ok": None}, "timeout"),
        ({"timed_out": False, "exit": 1, "expected_ok": False}, "exit 1"),
        ({"timed_out": False, "exit": 1, "expected_ok": None}, "exit 1"),
        ({"timed_out": False, "exit": 0, "expected_ok": False}, "stdout mismatch"),
    ]
    for entry, want in reason_cases:
        got = failure_reason(entry)
        if got != want:
            failures.append(f"  failure_reason({entry}): expected {want!r}, got {got!r}")

    if failures:
        print("FAIL: check-test-exitcode self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-test-exitcode self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run docs/VALIDATION.md-registered Validation commands and assert exit 0"
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
        cmds = [cmd for cmd, _ in commands]
        if args.json:
            print(json.dumps({"root": root, "commands": cmds}, ensure_ascii=False, indent=2))
        else:
            for cmd in cmds:
                print(cmd)
            print(f"# {len(cmds)} command(s) extracted from docs/VALIDATION.md ## Validation "
                  "(not run)", file=sys.stderr)
        return 0

    report = run_commands(commands, cwd=root, timeout=args.timeout)
    report["root"] = root

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        passed = report["total"] - len(report["failures"])
        skipped = report["skipped_no_expected"]
        # #578: skip count is always printed, success or failure — a silent skip is the gap
        # this guard exists to close, not a detail to bury behind a failure branch.
        skip_note = (f" ({skipped} command(s) have no `# Expected:` text, stdout unchecked)"
                     if skipped else "")
        if report["ok"]:
            print(f"OK: check-test-exitcode clean — {report['total']} registered "
                  f"command(s) ran, all exited 0 and all documented stdout matched"
                  f"{skip_note}")
        else:
            print(f"FAIL: {len(report['failures'])}/{report['total']} registered "
                  f"command(s) did NOT pass ({passed} passed){skip_note}:")
            for r in report["failures"]:
                why = failure_reason(r)
                print(f"  - [{why}] {r['command']}")
                # Show WHY it failed here, not only under --json: the CI review job quotes
                # this output, and a bare exit code costs it a second run to diagnose.
                if r["expected_ok"] is False:
                    print(f"      expected (tail): {r['expected']}")
                    print(f"      got (tail):      {r.get('stdout_tail', '')}")
                for line in (r.get("stderr_tail") or "").splitlines():
                    print(f"      {line}")
            print("Fix: repair the broken test/stale `# Expected:` text, or remove it from "
                  "docs/VALIDATION.md's Validation section if it is intentionally retired.")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
