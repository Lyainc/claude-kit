#!/usr/bin/env python3
"""gen-release-notes.py — build per-plugin release notes from Conventional Commits.

claude-kit ships a single lockstep marketplace version (all plugins share one version,
one tag `vX.Y.Z`). This script turns the commits since the previous tag into the
oh-my-pi-style release body: one section per plugin, each grouped into
Breaking Changes / Added / Changed / Fixed. The GitHub-native "What's Changed" PR list
(`gh release create --generate-notes`) is appended separately by the workflow, so this
script only owns the curated, human-readable top half.

Commit → plugin mapping: a commit's changed file paths decide which plugin section(s)
it lands in (a `thinking-tools/...` path → the thinking-tools section). Commits that
touch only shared infra (scripts/, telemetry/, .github/, docs/, root files) land in a
final "Repository / infrastructure" section. A commit touching several plugins appears
under each.

Conventional-Commit type → category:
    feat                     → Added
    fix                      → Fixed
    perf, refactor           → Changed
    `!` or BREAKING CHANGE:  → Breaking Changes   (overrides type)
    docs, chore, test, ci, build, style → omitted (internal; still in What's Changed)

Usage:
    python3 scripts/gen-release-notes.py --version 3.0.0 [--from v2.0.0] [--to HEAD]
    python3 scripts/gen-release-notes.py --self-test

    --from   previous tag/ref (default: most recent tag reachable from --to, else repo root)
    --to     end ref (default: HEAD)
    --version  the version being released (shown in section headers); required unless --self-test

Exit codes: 0 = notes written to stdout, 2 = usage error.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Plugin source dirs, in display order. Keep in sync with marketplace.json plugins[].source.
PLUGIN_DIRS = [
    "thinking-tools",
    "obsidian-vault-manager",
    "vault-bridge",
    "feedback-loop",
]
INFRA_SECTION = "Repository / infrastructure"

# Category display order within each plugin section (oh-my-pi parity).
CATEGORY_ORDER = ["Breaking Changes", "Added", "Changed", "Fixed"]

# Conventional-commit type → category. Types absent here are omitted from the
# curated notes (they still appear in the GitHub-generated What's Changed list).
TYPE_TO_CATEGORY = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
}

# `type(scope)!: subject` or `type: subject`. scope and `!` optional.
_HEADER_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<subject>.+)$")


def _run_git(args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


def previous_tag(to_ref, cwd=None):
    """Most recent tag strictly before `to_ref`, or None if none exists."""
    try:
        out = _run_git(["describe", "--tags", "--abbrev=0", f"{to_ref}^"], cwd=cwd)
        return out.strip() or None
    except subprocess.CalledProcessError:
        # No tag reachable — fall back to the repo's first commit.
        return None


def collect_commits(from_ref, to_ref, cwd=None):
    """Return a list of {sha, subject, body, files[]} for from_ref..to_ref.

    If from_ref is None, walk from the repository root.

    Records are delimited by NUL (%x00) and fields by Unit Separator (%x1f); a
    trailing %x1f after the body fences off the multi-line body from the
    --name-only file list that follows. Both separators are control chars that
    never occur in commit text, so the split is unambiguous regardless of how many
    newlines the body contains.
    """
    range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref
    fmt = "%x00%H%x1f%s%x1f%b%x1f"
    raw = _run_git(["log", f"--format={fmt}", "--name-only", range_spec], cwd=cwd)
    commits = []
    for chunk in raw.split("\x00"):
        if not chunk.strip():
            continue
        # chunk = "<sha>\x1f<subject>\x1f<body>\x1f\n<file>\n<file>..."
        fields = chunk.split("\x1f")
        sha, subject, body = fields[0].strip(), fields[1], fields[2]
        files_blob = fields[3] if len(fields) > 3 else ""
        files = [ln for ln in files_blob.splitlines() if ln.strip()]
        commits.append({"sha": sha, "subject": subject.strip(), "body": body, "files": files})
    return commits


def plugins_for_files(files):
    """Return the set of plugin dirs (or INFRA_SECTION) touched by these paths."""
    hit = set()
    for f in files:
        top = f.split("/", 1)[0]
        if top in PLUGIN_DIRS:
            hit.add(top)
    if not hit:
        return {INFRA_SECTION}
    return hit


def classify(commit):
    """Parse a commit into (category, subject, scope) or None if it should be omitted.

    category is one of CATEGORY_ORDER; None means the type is not release-note worthy.
    """
    m = _HEADER_RE.match(commit["subject"])
    if not m:
        return None
    ctype = m.group("type")
    bang = m.group("bang")
    scope = m.group("scope")
    subject = m.group("subject").strip()
    breaking = bool(bang) or "BREAKING CHANGE" in (commit.get("body") or "")
    if breaking:
        return ("Breaking Changes", subject, scope)
    category = TYPE_TO_CATEGORY.get(ctype)
    if category is None:
        return None
    return (category, subject, scope)


def build_sections(commits):
    """Return {plugin: {category: [entry,...]}} from classified commits."""
    sections = {}
    for commit in commits:
        result = classify(commit)
        if result is None:
            continue
        category, subject, scope = result
        targets = plugins_for_files(commit["files"])
        for plugin in targets:
            sections.setdefault(plugin, {}).setdefault(category, []).append((subject, scope))
    return sections


def _plugin_version(plugin_dir, version, cwd=None):
    """The version to display for a plugin. Under lockstep this equals `version`;
    read plugin.json so the header stays truthful if a manifest ever diverges."""
    if not cwd:
        cwd = "."
    pj = os.path.join(cwd, plugin_dir, ".claude-plugin", "plugin.json")
    try:
        with open(pj, encoding="utf-8") as fh:
            return json.load(fh).get("version", version)
    except (OSError, json.JSONDecodeError):
        return version


def render(sections, version, cwd=None):
    """Render the {plugin: {category: entries}} map to markdown."""
    lines = []
    ordered = [p for p in PLUGIN_DIRS if p in sections]
    if INFRA_SECTION in sections:
        ordered.append(INFRA_SECTION)
    for plugin in ordered:
        if plugin == INFRA_SECTION:
            lines.append(f"### {INFRA_SECTION}")
        else:
            pv = _plugin_version(plugin, version, cwd=cwd)
            lines.append(f"### {plugin} {pv}")
        lines.append("")
        cats = sections[plugin]
        for category in CATEGORY_ORDER:
            entries = cats.get(category)
            if not entries:
                continue
            lines.append(f"**{category}**")
            lines.append("")
            for subject, scope in entries:
                prefix = f"**{scope}**: " if scope else ""
                lines.append(f"- {prefix}{subject}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate(version, from_ref, to_ref, cwd=None):
    if from_ref is None:
        from_ref = previous_tag(to_ref, cwd=cwd)
    commits = collect_commits(from_ref, to_ref, cwd=cwd)
    sections = build_sections(commits)
    body = render(sections, version, cwd=cwd)
    if not sections:
        body = "_No user-facing changes (feat/fix/refactor/perf) since the previous release._\n"
    return body


# --------------------------------------------------------------------------- #
# Self-test — parsing/classification/grouping, independent of any git repo.
# --------------------------------------------------------------------------- #
def run_self_test():
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"  {label}: got {got!r}, want {want!r}")

    # classify
    check("feat→Added",
          classify({"subject": "feat: add x", "body": ""}),
          ("Added", "add x", None))
    check("fix→Fixed",
          classify({"subject": "fix(scope): bug", "body": ""}),
          ("Fixed", "bug", "scope"))
    check("refactor→Changed",
          classify({"subject": "refactor: tidy", "body": ""}),
          ("Changed", "tidy", None))
    check("perf→Changed",
          classify({"subject": "perf: faster", "body": ""}),
          ("Changed", "faster", None))
    check("bang→Breaking",
          classify({"subject": "feat!: drop api", "body": ""}),
          ("Breaking Changes", "drop api", None))
    check("scope+bang→Breaking",
          classify({"subject": "feat(api)!: drop", "body": ""}),
          ("Breaking Changes", "drop", "api"))
    check("body BREAKING→Breaking",
          classify({"subject": "fix: x", "body": "BREAKING CHANGE: removes y"}),
          ("Breaking Changes", "x", None))
    check("docs omitted", classify({"subject": "docs: update", "body": ""}), None)
    check("chore omitted", classify({"subject": "chore: bump", "body": ""}), None)
    check("non-conventional omitted",
          classify({"subject": "WIP random commit", "body": ""}), None)

    # plugins_for_files
    check("single plugin",
          plugins_for_files(["thinking-tools/skills/x/SKILL.md"]),
          {"thinking-tools"})
    check("multi plugin",
          plugins_for_files(["vault-bridge/a.sh", "feedback-loop/b.py"]),
          {"vault-bridge", "feedback-loop"})
    check("infra only",
          plugins_for_files(["scripts/x.py", "README.md"]),
          {INFRA_SECTION})

    # build_sections + render integration
    commits = [
        {"sha": "1", "subject": "feat(note): add base skill", "body": "",
         "files": ["obsidian-vault-manager/skills/base/SKILL.md"]},
        {"sha": "2", "subject": "fix: stop-hook loop", "body": "",
         "files": ["vault-bridge/hooks/stop-check.sh"]},
        {"sha": "3", "subject": "feat!: drop wrapup", "body": "BREAKING CHANGE: removed",
         "files": ["obsidian-vault-manager/skills/wrapup/SKILL.md"]},
        {"sha": "4", "subject": "docs: readme", "body": "", "files": ["README.md"]},
        {"sha": "5", "subject": "chore: bump dep", "body": "", "files": ["scripts/x.py"]},
        {"sha": "6", "subject": "refactor: tidy report", "body": "",
         "files": ["feedback-loop/scripts/report.py"]},
    ]
    sections = build_sections(commits)
    # ovm has Added(base) + Breaking(drop wrapup)
    check("ovm categories",
          sorted(sections.get("obsidian-vault-manager", {}).keys()),
          ["Added", "Breaking Changes"])
    check("vault-bridge fixed",
          sections.get("vault-bridge", {}).get("Fixed"),
          [("stop-hook loop", None)])
    check("feedback-loop changed",
          sections.get("feedback-loop", {}).get("Changed"),
          [("tidy report", None)])
    # docs/chore omitted → no infra section at all
    check("infra omitted (docs/chore only)",
          INFRA_SECTION in sections, False)

    body = render(sections, "3.0.0", cwd=None)
    check("render has breaking header", "**Breaking Changes**" in body, True)
    check("render orders breaking before added",
          body.index("Breaking Changes") < body.index("Added"), True)

    if failures:
        print("FAIL: gen-release-notes self-test")
        print("\n".join(failures))
        return 1
    print("OK: all gen-release-notes self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="build per-plugin release notes")
    parser.add_argument("--version", help="version being released (header display)")
    parser.add_argument("--from", dest="from_ref", default=None, help="previous tag/ref")
    parser.add_argument("--to", dest="to_ref", default="HEAD", help="end ref (default HEAD)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.version:
        parser.error("--version is required (unless --self-test)")

    sys.stdout.write(generate(args.version, args.from_ref, args.to_ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
