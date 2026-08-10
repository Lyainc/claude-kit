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

RULE 2, agents/*.md (#579): the OPPOSITE markdown-link judgment applies here, on purpose.
A SKILL.md body is read as a FILE, so `../../reference/foo.md` resolves relative to it and
stays correct wherever installed. An agent .md body is instead injected as a subagent's
SYSTEM PROMPT — there is no file on disk it is "read relative to" at runtime, and CWD is the
CONSUMER's project, not this checkout. So the same relative path that SKILL.md's own
docstring calls safe is exactly what breaks in an agent body: `../reference/foo.md` or a
bare `foo.md` (same directory) resolves nowhere once installed. Do not fold this into the
SKILL.md rule above or "fix" it back to matching SKILL.md's judgment — the two are
deliberately inverted, and reverting one to match the other reintroduces the #566 bug.

SCOPE, agents/*.md: only a backtick-quoted path anchored at `reference/`, `scripts/`, or
`hooks/` (optionally behind one or more `../`), or a bare `name.ext` immediately annotated
`(same directory)` / `(this directory)` — the two shapes #566 actually shipped. This deliberately
excludes what would otherwise flood this narrow, prose-scanning guard with false positives:
human-facing doc links (`docs/design/...`), vault paths (`~/vault/...`), another plugin's own
path (`obsidian-vault-manager/reference/...` — no `${CLAUDE_PLUGIN_ROOT}` spans plugins, so
that is a separate, harder problem this guard does not attempt), and fake paths inside a
fenced code example (stripped, along with HTML comments, before scanning — the SKILL.md rule
above scans fenced blocks because THEY are the executable surface there; here prose IS the
executable surface, so fenced/commented text is the non-executable illustration to exclude).
Further scoped to agents whose `tools:` frontmatter grants Read or Bash: without either, the
agent has no way to act on the pointer at runtime, so a broken one is inert prose — the same
"prose mention executes nothing" exemption SKILL.md already gets, just gated on capability
instead of on markdown-link syntax. `${CLAUDE_PLUGIN_ROOT}`-anchored paths are never flagged.

Usage:
    python3 scripts/check-plugin-root-paths.py [--root DIR] [--self-test]

Exit codes: 0 = clean, 1 = violation(s) found.
"""

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Reuse the agent frontmatter/`tools:` parser (declared_tools, normalise, split_frontmatter,
# strip_noise) from the sibling guard instead of re-implementing YAML-ish parsing here.
_HERE = os.path.dirname(os.path.abspath(__file__))
_usage_spec = importlib.util.spec_from_file_location(
    "check_agent_tools_usage", os.path.join(_HERE, "check-agent-tools-usage.py")
)
_usage = importlib.util.module_from_spec(_usage_spec)
_usage_spec.loader.exec_module(_usage)

# A fenced block we treat as executable. Bare ``` is included: retro/SKILL.md's blocks are
# not all language-tagged, and an untagged block of shell is exactly the case we must catch.
FENCE_RE = re.compile(r"^\s*```(\w*)\s*$")
EXEC_LANGS = {"", "bash", "sh", "shell", "console", "python", "python3"}

# An interpreter invoking a path that reaches into a bundled script/hook directory.
# `(?:-\S+\s+)*` skips interpreter flags — `python3 -u scripts/x.py`, `bash -x scripts/x.sh`
# are the same defect and must not slip through on the flag alone.
# `[^\s;|&]*` keeps the match on ONE argument — a trailing `; echo done` is not swallowed.
INVOKE_RE = re.compile(
    r"\b(?:bash|sh|python3?|uv\s+run)\s+(?:-\S+\s+)*[^\s;|&]*(?:scripts|hooks)/[^\s;|&]*\.(?:sh|py)\b"
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


# The two shapes #566 actually shipped: a backtick path anchored at reference/scripts/hooks
# (optionally behind one or more `../`), or a bare `name.ext` annotated "(same directory)"/
# "(this directory)". Anchored on the backtick so a match can only start the code span —
# `${CLAUDE_PLUGIN_ROOT}/reference/x.md` never matches (the span starts with `${...}`, not
# `reference/`), so no separate CLAUDE_PLUGIN_ROOT exclusion is needed here.
AGENT_REL_PATH_RE = re.compile(r"`((?:\.\./)*(?:reference|scripts|hooks)/[^`\s]+\.[A-Za-z0-9]+)`")
AGENT_SAME_DIR_RE = re.compile(
    r"`([\w.-]+\.[A-Za-z0-9]+)`\s*\((?:same|this)\s+directory\)", re.IGNORECASE
)


def scan_agent(path: Path):
    """Yield (lineno, line) for each unanchored plugin-internal file pointer in an agent body.

    Scoped to agents whose `tools:` frontmatter grants Read or Bash (see module docstring —
    without either the agent cannot act on the pointer, so a broken one is inert prose, the
    same exemption scan_skill gives a bare mention). Fenced code blocks and HTML comments are
    stripped before scanning — illustrative examples, not the executable surface here.
    """
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _usage.split_frontmatter(text)
    if frontmatter is None:
        return []
    declared = {_usage.normalise(t) for t in _usage.declared_tools(frontmatter)}
    if not (declared & {"Read", "Bash"}):
        return []

    # `body` is the exact tail of `text` (FRONTMATTER_RE's second group runs to `\Z`), so the
    # frontmatter's line count — and therefore body's real starting line — is just the newline
    # count in everything before it. Without this offset every reported lineno undercounts by
    # the frontmatter's length, pointing at unrelated frontmatter/body text instead of the hit.
    line_offset = text[: len(text) - len(body or "")].count("\n")

    findings = []
    in_fence = False
    in_comment = False
    for body_lineno, line in enumerate((body or "").splitlines(), 1):
        lineno = body_lineno + line_offset
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue
        line = re.sub(r"<!--.*?-->", "", line)
        if AGENT_REL_PATH_RE.search(line) or AGENT_SAME_DIR_RE.search(line):
            findings.append((lineno, line.strip()))
    return findings


def plugin_roots(root: Path):
    """Source plugins only — a top-level dir carrying a plugin manifest.

    Keyed off the manifest rather than a hardcoded name list so a new plugin is picked up
    for free, and so any vendored third-party plugin cache (someone else's SKILL.md files,
    which we neither own nor may edit) never reaches the scanner.
    """
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and (d / ".claude-plugin" / "plugin.json").is_file()
    )


def check(root: Path):
    skills = sorted(f for p in plugin_roots(root) for f in p.glob("skills/*/SKILL.md"))
    agents = sorted(f for p in plugin_roots(root) for f in p.glob("agents/*.md"))
    violations = [(f, ln, txt) for f in skills for ln, txt in scan_skill(f)]
    violations += [(f, ln, txt) for f in agents for ln, txt in scan_agent(f)]
    return skills, agents, violations


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
    flagged_violating = """\
# Retro
```bash
python3 -u feedback-loop/scripts/report.py
bash -x feedback-loop/scripts/retro-telemetry.sh stamp
```
"""
    cases = [
        ("tagged bash, repo-relative", violating, 1),
        ("untagged block, repo-relative", untagged_violating, 1),
        ("interpreter flag before the path", flagged_violating, 2),
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

    # agents/*.md fixtures (#579) — every one carries `tools: Read` unless the case is
    # specifically about the no-Read/Bash exemption, so that exemption is exercised too.
    agent_bare_rel = """\
---
name: x
tools: Read
---
Detail lives in `../reference/foo.md`.
"""
    agent_same_dir = """\
---
name: x
tools: Bash
---
Seven worked examples live in `foo-examples.md` (same directory).
"""
    agent_anchored = """\
---
name: x
tools: Read
---
Detail lives in `${CLAUDE_PLUGIN_ROOT}/reference/foo.md`.
"""
    agent_no_read_or_bash = """\
---
name: x
tools: Skill, AskUserQuestion
---
Detail lives in `../reference/foo.md`. (No Read/Bash to act on it — inert prose.)
"""
    agent_cross_plugin = """\
---
name: x
tools: Read
---
Run the availability gate from `obsidian-vault-manager/reference/obsidian-cli.md`.
"""
    agent_doc_and_vault_paths = """\
---
name: x
tools: Read
---
See `docs/design/claude-kit-boundary.md` for the boundary. Vault notes live under
`~/vault/notes/`. (Same contract as `some-other-agent.md`.)
"""
    agent_fenced_example = """\
---
name: x
tools: Read
---
Wrong pattern (do not do this):
```
Detail lives in `../reference/foo.md`.
```
"""
    agent_html_comment = """\
---
name: x
tools: Read
---
<!-- old note: detail lives in `../reference/foo.md` -->
Detail lives in `${CLAUDE_PLUGIN_ROOT}/reference/foo.md`.
"""
    agent_cases = [
        ("agent: bare ../reference/ path", agent_bare_rel, 1),
        ("agent: bare filename (same directory)", agent_same_dir, 1),
        ("agent: anchored on CLAUDE_PLUGIN_ROOT", agent_anchored, 0),
        ("agent: no Read/Bash tool — inert prose", agent_no_read_or_bash, 0),
        ("agent: cross-plugin path (not this plugin's own dir)", agent_cross_plugin, 0),
        ("agent: human doc link + vault path + bare filename mention", agent_doc_and_vault_paths, 0),
        ("agent: bad pattern shown inside a fenced example", agent_fenced_example, 0),
        ("agent: stale pointer inside an HTML comment", agent_html_comment, 0),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, body, expected) in enumerate(agent_cases):
            d = Path(tmp) / f"aplug{i}" / "agents"
            d.mkdir(parents=True)
            (d / "x.md").write_text(body, encoding="utf-8")
            got = len(scan_agent(d / "x.md"))
            if got != expected:
                failures.append(f"  {label}: expected {expected} finding(s), got {got}")

        # A finding's lineno must be the REAL file line, not a frontmatter-stripped-body
        # offset — `agent_bare_rel`'s violation is physically line 5 (4-line frontmatter).
        d = Path(tmp) / "alineno" / "agents"
        d.mkdir(parents=True)
        (d / "x.md").write_text(agent_bare_rel, encoding="utf-8")
        got_lines = [ln for ln, _ in scan_agent(d / "x.md")]
        if got_lines != [5]:
            failures.append(f"  agent lineno: expected [5], got {got_lines}")

    if failures:
        print("FAIL: check-plugin-root-paths self-test", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"OK: all {len(cases) + len(agent_cases)} check-plugin-root-paths self-test cases passed")
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
    skills, agents, violations = check(root)

    if violations:
        print(
            f"FAIL: {len(violations)} unanchored script invocation(s) / plugin-internal file "
            f"pointer(s) — these resolve against the CONSUMER's project/CWD, not this repo:",
            file=sys.stderr,
        )
        for path, lineno, text in violations:
            rel = path.relative_to(root)
            print(f"  {rel}:{lineno}: {text}", file=sys.stderr)
        print(
            '\nFix: anchor the path — bash "${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh" '
            'or `${CLAUDE_PLUGIN_ROOT}/reference/foo.md` in an agent body',
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: plugin-root-paths clean — {len(skills)} SKILL.md + {len(agents)} agents/*.md "
        f"checked, every bundled-script invocation / plugin-internal pointer is "
        f"${{CLAUDE_PLUGIN_ROOT}}-anchored"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
