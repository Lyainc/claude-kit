#!/usr/bin/env python3
"""check-plugin-root-paths.py — SKILL.md executable paths must be plugin-root-anchored.

RULE (narrow, deterministic): inside a SKILL.md fenced code block, a command that EXECUTES
a bundled script (`bash`/`sh`/`python`/`python3` followed by a path containing `scripts/`
or `hooks/`) MUST anchor that path on `${CLAUDE_PLUGIN_ROOT}`.

OBJECTIVE DAMAGE (c6 — policy, not taste): a SKILL.md body is injected and its code blocks
run with CWD = the CONSUMER's project, not the claude-kit checkout. So a repo-relative
invocation like

    python3 feedback-loop/scripts/report.py 2>/dev/null

resolves only when the user happens to be sitting in the claude-kit repo. For every
plugin-INSTALLED consumer the path does not exist — and because these calls are routinely
`2>/dev/null`-suppressed or `|| true`-guarded, they fail SILENTLY: the skill appears to run
while its telemetry/scan step does nothing. This is objective breakage of the plugin's
primary deployment mode (feedback-loop is an explicitly external-distribution unit), not a
style preference. Found live in retro/SKILL.md (4 call sites) during the 2026-07-14 audit,
already shipped in v4.0.0.

WHY EXECUTABLE-ONLY (not every relative path): markdown reference links of the form
`../../reference/foo.md` are resolved relative to the SKILL.md FILE, so they stay correct
wherever the plugin is installed — flagging them would be a false positive. Likewise a
prose mention that merely NAMES a file (`see feedback-loop/README.md`) executes nothing.
We flag only the case where CWD actually decides whether the command works: an interpreter
invoked on a bundled-script path. That keeps FP at 0, which is the bar every other guard in
this repo holds.

Usage:
    python3 scripts/check-plugin-root-paths.py [--root DIR] [--self-test]

Exit codes: 0 = clean, 1 = violation(s) found.
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# A fenced block we treat as executable. Bare ``` is included: retro/SKILL.md's blocks are
# not all language-tagged, and an untagged block of shell is exactly the case we must catch.
FENCE_RE = re.compile(r"^\s*```(\w*)\s*$")
EXEC_LANGS = {"", "bash", "sh", "shell", "console", "python", "python3"}

# An interpreter invoking a path that reaches into a bundled script/hook directory.
# `[^\s;|&]*` keeps the match on ONE argument — a trailing `; echo done` is not swallowed.
INVOKE_RE = re.compile(
    r"\b(?:bash|sh|python3?|uv\s+run)\s+[^\s;|&]*(?:scripts|hooks)/[^\s;|&]*\.(?:sh|py)\b"
)


def scan_skill(path: Path):
    """Yield (lineno, line) for each plugin-root-unanchored script invocation."""
    findings = []
    in_exec_block = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fence = FENCE_RE.match(line)
        if fence:
            # A closing fence carries no language, so toggling on the opener's language is
            # only correct while we are OUTSIDE a block; inside, any fence closes it.
            in_exec_block = (
                False if in_exec_block else fence.group(1).lower() in EXEC_LANGS
            )
            continue
        if not in_exec_block:
            continue
        if INVOKE_RE.search(line) and "CLAUDE_PLUGIN_ROOT" not in line:
            findings.append((lineno, line.strip()))
    return findings


def plugin_roots(root: Path):
    """Source plugins only — a top-level dir carrying a plugin manifest.

    Keyed off the manifest rather than a hardcoded name list so a new plugin is picked up
    for free, and so the vendored `.codex/` plugin caches (someone else's SKILL.md files,
    which we neither own nor may edit) never reach the scanner.
    """
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and (d / ".claude-plugin" / "plugin.json").is_file()
    )


def check(root: Path):
    skills = sorted(f for p in plugin_roots(root) for f in p.glob("skills/*/SKILL.md"))
    violations = [(f, ln, txt) for f in skills for ln, txt in scan_skill(f)]
    return skills, violations


def run_self_test():
    violating = """\
# Retro
Stamp the start:
```bash
bash feedback-loop/scripts/retro-telemetry.sh stamp
```
"""
    untagged_violating = """\
# Retro
```
python3 feedback-loop/scripts/report.py 2>/dev/null
```
"""
    clean_anchored = """\
# Retro
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" stamp
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" 2>/dev/null
```
"""
    clean_prose = """\
# Retro
The helper owns the events-dir rule (shared with `feedback-loop/scripts/event-logger.sh`),
and the schema lives in `../../reference/vault-audit-rules.md`. See feedback-loop/README.md.
"""
    clean_non_exec_block = """\
# Retro
```json
{"path": "feedback-loop/scripts/report.py"}
```
"""
    cases = [
        ("tagged bash, repo-relative", violating, 1),
        ("untagged block, repo-relative", untagged_violating, 1),
        ("anchored on CLAUDE_PLUGIN_ROOT", clean_anchored, 0),
        ("prose mention only (no exec)", clean_prose, 0),
        ("non-executable fence (json)", clean_non_exec_block, 0),
    ]
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, body, expected) in enumerate(cases):
            d = Path(tmp) / f"plug{i}" / "skills" / "s"
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(body, encoding="utf-8")
            got = len(scan_skill(d / "SKILL.md"))
            if got != expected:
                failures.append(f"  {label}: expected {expected} finding(s), got {got}")
    if failures:
        print("FAIL: check-plugin-root-paths self-test", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"OK: all {len(cases)} check-plugin-root-paths self-test cases passed")
    return 0


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true", help="run in-memory fixtures")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = args.root or _git_toplevel()
    skills, violations = check(root)

    if violations:
        print(
            f"FAIL: {len(violations)} unanchored script invocation(s) in SKILL.md "
            f"code blocks — these run with CWD = the consumer's project, not this repo:",
            file=sys.stderr,
        )
        for path, lineno, text in violations:
            rel = path.relative_to(root)
            print(f"  {rel}:{lineno}: {text}", file=sys.stderr)
        print(
            '\nFix: anchor the path — bash "${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh"',
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: plugin-root-paths clean — {len(skills)} SKILL.md checked, "
        f"every bundled-script invocation is ${{CLAUDE_PLUGIN_ROOT}}-anchored"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
