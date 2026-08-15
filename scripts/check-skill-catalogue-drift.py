#!/usr/bin/env python3
"""check-skill-catalogue-drift.py — every skill stays listed where CLAUDE.md requires (#621).

RULE: CLAUDE.md's "Adding a New Skill" step 6 (#173) makes ONE catalogue entry point
MANDATORY for every skill: a row in the root README.md's skill TABLE, plus (by the same
discoverability logic) a mention in the skill's own plugin README.md and in CLAUDE.md's
"Project Overview" plugin bullet, which is what step 6's sibling steps keep current. The
docs/design/4-flow-catalog.md entry is explicitly conditional ("4-흐름에 맞을 때만") and
is NOT enforced here. #621 shipped three drifts of exactly this shape (retired audit
codes still advertised, a stale README skill list, a missing LICENSE) with the same root
cause named in the issue: "카탈로그가 소스보다 늦게 움직이는데 그걸 보는 가드가 없다" — no
guard watches the catalogue, so it silently falls out of sync the next time a skill is
added, renamed, or removed. This guard is that watch.

Two checks, both mechanical:
  1. CATALOGUE: every `*/skills/<name>/SKILL.md` file's skill name (the directory name)
     must appear as a whole word in THREE places, each with its own strictness:
       a. root README.md — inside a markdown TABLE ROW (a line whose first non-blank,
          non-`>` character is `|`) of ITS OWN PLUGIN's section, not merely somewhere in
          the file. Step 6 calls the table entry mandatory, and "anywhere in the file" is
          too weak to enforce it: a deleted table row usually leaves a prose mention
          behind, so the check passes on a catalogue that no longer lists the skill where
          a reader looks for it. Table-row-anywhere is still too weak — 10 of this repo's
          19 skills are named in a second table (the 진입점 table, the second-brain path
          table), which would cover for their own deleted row. Section-scoped, deleting
          any one of the 19 rows is caught. See `root_plugin_sections`.
       b. `<plugin>/README.md` — anywhere in the file. This half stays deliberately loose:
          feedback-loop's README introduces `retro`/`distill`/`add-policy` in prose and a
          file-layout table rather than a discoverability skill table, and step 6 makes
          only the ROOT table mandatory. Tightening this half would flag a legitimate
          layout, which is the false positive #621 asked this guard not to manufacture.
       c. CLAUDE.md — inside its own plugin's `- **<plugin>**` Project Overview bullet.
          Scoping to the plugin's own bullet is what makes the check bite: a name deleted
          from thinking-tools' enumeration is not covered by an unrelated mention
          elsewhere in the file.
     Word boundary treats `-`/`_` as part of the word, so `wiki` doesn't false-positive
     inside `wikilink` but DOES match inside a backticked `/vault-manifest-refresh`-style
     mention (a plain substring check would either miss the latter or match "database" for
     skill name "base" — this guard requires an actual boundary on both sides).
  2. COUNT: a sentence of the exact Korean shape `N개 스킬` / `N개 에이전트` OR its
     reversed twin `스킬 N개` / `에이전트 N개` (CLAUDE.md writes the reversed one, e.g.
     "사고 도구 스킬 9개 + 에이전트 1개"; plugin READMEs write the forward one, e.g. "9개
     스킬과 1개 에이전트") must match the real count of `<plugin>/skills/*/SKILL.md` /
     `<plugin>/agents/*.md` files. Checked in the plugin README (whole file) and in
     CLAUDE.md (scoped to that plugin's own bullet). This is intentionally narrow — only
     these two mechanical phrasings are matched. A prose count that isn't either shape
     (e.g. feedback-loop's "Four pieces ship together", which counts 3 skills PLUS the
     non-skill telemetry component as one more "piece") is left unchecked on purpose:
     checking it against a bare skill/agent count would itself be a false positive, and
     inventing a general natural-language number parser is exactly the fragile matcher
     #621 asked this guard NOT to become.

Usage:
    python3 scripts/check-skill-catalogue-drift.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = every skill is catalogued and every N개 스킬/에이전트 count matches reality
            (or --self-test passed), 1 = at least one drift found, 2 = usage error (no
            root README.md, or no `*/skills/*/SKILL.md` files found).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

# Both orders: "9개 스킬" (plugin READMEs) and "스킬 9개" (CLAUDE.md). Exactly one of the
# two (number, unit) group pairs is populated per match.
COUNT_RE = re.compile(r"(\d+)개\s*(스킬|에이전트)|(스킬|에이전트)\s*(\d+)개")
CLAUDE_MD = "CLAUDE.md"
# A Project Overview plugin bullet: `- **thinking-tools** (\`thinking-tools/\`): ...`,
# continuing until the next blank line or the next such bullet.
CLAUDE_BULLET_RE = re.compile(r"^-\s+\*\*([A-Za-z0-9_-]+)\*\*", re.MULTILINE)


def _iter_counts(text):
    """Yield (claimed, unit) for every `N개 스킬`/`스킬 N개` phrasing in `text`."""
    for m in COUNT_RE.finditer(text):
        if m.group(1):
            yield int(m.group(1)), m.group(2)
        else:
            yield int(m.group(4)), m.group(3)


def table_lines(text):
    """Return the markdown TABLE rows of `text` — lines whose first non-blank, non-`>`
    character is `|` (the `>` strip keeps blockquoted tables, e.g. root README's
    feedback-loop section, in scope)."""
    rows = []
    for line in text.splitlines():
        stripped = line.lstrip("> \t")
        if stripped.startswith("|"):
            rows.append(stripped)
    return "\n".join(rows)


_SECTION_START_RE = re.compile(r"^(?:#{1,6}\s|>\s*\*\*)")


def root_plugin_sections(text, plugins):
    """Return {plugin: section_text} for the root README's per-plugin sections.

    A section opens at the FIRST heading (`### vault-bridge — ...`) or blockquote intro
    (`> **feedback-loop** ...`) naming that plugin, and closes at the next line of either
    shape. Scoping matters: without it, a skill deleted from its own plugin's catalogue
    table still passes on an unrelated table elsewhere in the file (`wiki` is repeated in
    the 진입점 table and the second-brain path table), which is the same
    a-mention-anywhere weakness one level up.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if _SECTION_START_RE.match(line)]
    sections = {}
    for i in starts:
        for p in plugins:
            if p not in sections and _word_re(p).search(lines[i]):
                nxt = next((b for b in starts if b > i), len(lines))
                sections[p] = "\n".join(lines[i:nxt])
                break
    return sections


def claude_md_bullets(text):
    """Return {plugin: bullet_text} for CLAUDE.md's Project Overview plugin bullets."""
    if text is None:
        return {}
    bullets, matches = {}, list(CLAUDE_BULLET_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end]
        # A bullet ends at the first blank line — later prose is a different section.
        bullets[m.group(1)] = body.split("\n\n", 1)[0]
    return bullets


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _word_re(word):
    """Whole-word match treating `-`/`_` as word characters, so `wiki` doesn't match
    inside `wikilink` but does match a backticked `/vault-manifest-refresh` mention."""
    return re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(word) + r"(?![A-Za-z0-9_-])")


def find_skills(root):
    """Return sorted [{plugin, name, path}] for every */skills/<name>/SKILL.md."""
    skills = []
    for path in sorted(glob.glob(os.path.join(root, "*", "skills", "*", "SKILL.md"))):
        rel = os.path.relpath(path, root)
        parts = rel.split(os.sep)
        skills.append({"plugin": parts[0], "name": parts[2], "path": rel})
    return skills


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def check_catalogue_presence(root, skills, root_readme_text, plugin_readme_cache,
                             claude_bullets=None):
    """Return a list of {kind, plugin, skill, detail} violations for missing entries."""
    violations = []
    claude_bullets = {} if claude_bullets is None else claude_bullets
    plugins = sorted({s["plugin"] for s in skills})
    sections = root_plugin_sections(root_readme_text, plugins) if root_readme_text else {}
    for s in skills:
        plugin, name = s["plugin"], s["name"]
        if plugin not in sections:
            violations.append({
                "kind": "missing_in_root_readme", "plugin": plugin, "skill": name,
                "detail": f"root README.md has no `{plugin}` section (heading or `> **{plugin}**` intro)",
            })
        elif not _word_re(name).search(table_lines(sections[plugin])):
            violations.append({
                "kind": "missing_in_root_readme", "plugin": plugin, "skill": name,
                "detail": (f"`{name}` not found (as a whole word) in a table row of root "
                           f"README.md's `{plugin}` section"),
            })

        bullet = claude_bullets.get(plugin)
        if bullet is None:
            violations.append({
                "kind": "missing_in_claude_md", "plugin": plugin, "skill": name,
                "detail": f"{CLAUDE_MD} has no `- **{plugin}**` Project Overview bullet",
            })
        elif not _word_re(name).search(bullet):
            violations.append({
                "kind": "missing_in_claude_md", "plugin": plugin, "skill": name,
                "detail": f"`{name}` not found (as a whole word) in {CLAUDE_MD}'s `{plugin}` bullet",
            })

        plugin_readme_path = os.path.join(plugin, "README.md")
        if plugin_readme_path not in plugin_readme_cache:
            plugin_readme_cache[plugin_readme_path] = _read(os.path.join(root, plugin_readme_path))
        text = plugin_readme_cache[plugin_readme_path]
        if text is None:
            violations.append({
                "kind": "missing_plugin_readme", "plugin": plugin, "skill": name,
                "detail": f"{plugin_readme_path} does not exist or is unreadable",
            })
        elif not _word_re(name).search(text):
            violations.append({
                "kind": "missing_in_plugin_readme", "plugin": plugin, "skill": name,
                "detail": f"`{name}` not found (as a whole word) in {plugin_readme_path}",
            })
    return violations


def check_counts(root, skills, plugin_readme_cache, claude_bullets=None):
    """Return a list of {kind, plugin, detail} violations for stale `N개 스킬`/`스킬 N개`."""
    violations = []
    claude_bullets = {} if claude_bullets is None else claude_bullets
    plugins = sorted({s["plugin"] for s in skills})
    for plugin in plugins:
        actual_skills = sum(1 for s in skills if s["plugin"] == plugin)
        actual_agents = len(glob.glob(os.path.join(root, plugin, "agents", "*.md")))

        plugin_readme_path = os.path.join(plugin, "README.md")
        if plugin_readme_path not in plugin_readme_cache:
            plugin_readme_cache[plugin_readme_path] = _read(os.path.join(root, plugin_readme_path))

        sources = [(plugin_readme_path, plugin_readme_cache[plugin_readme_path])]
        if plugin in claude_bullets:
            sources.append((f"{CLAUDE_MD} (`{plugin}` bullet)", claude_bullets[plugin]))

        for where, text in sources:
            if text is None:
                continue  # already reported by check_catalogue_presence
            for claimed, unit in _iter_counts(text):
                actual = actual_skills if unit == "스킬" else actual_agents
                if claimed != actual:
                    violations.append({
                        "kind": "count_drift", "plugin": plugin,
                        "detail": (f"{where} claims `{claimed}개 {unit}` but "
                                   f"{plugin}/{'skills' if unit == '스킬' else 'agents'} has {actual}"),
                    })
    return violations


def check_all(root):
    root_readme_text = _read(os.path.join(root, "README.md"))
    claude_bullets = claude_md_bullets(_read(os.path.join(root, CLAUDE_MD)))
    skills = find_skills(root)
    plugin_readme_cache = {}
    violations = []
    violations += check_catalogue_presence(root, skills, root_readme_text,
                                           plugin_readme_cache, claude_bullets)
    violations += check_counts(root, skills, plugin_readme_cache, claude_bullets)
    return skills, root_readme_text, violations


def run_self_test():
    import tempfile
    failures = []

    def write(rel, text):
        path = os.path.join(td, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def root_table(*names, trailer=""):
        rows = "".join(f"| when | `{n}` — does a thing |\n" for n in names)
        return ("# kit\n\n### demo-plugin — demo\n\n| 이럴 때 | 스킬 |\n|---|---|\n"
                + rows + trailer
                + "\n### 무엇부터 써볼까\n\n| 하려는 일 | 진입점 |\n|---|---|\n"
                  "| everything | `wiki` · `audit` · `base` |\n")

    def claude_md(count, *names):
        return ("## Project Overview\n\n"
                f"- **demo-plugin** (`demo-plugin/`): 스킬 {count}개 + 에이전트 1개 "
                f"({', '.join(names)})\n\n## Git Conventions\n")

    with tempfile.TemporaryDirectory() as td:
        for name in ("wiki", "audit"):
            write(f"demo-plugin/skills/{name}/SKILL.md", f"---\nname: {name}\n---\nbody")
        write("demo-plugin/agents/a.md", "agent")

        # Case 1: clean — both skills in a root table row, plugin README, CLAUDE.md bullet.
        write("README.md", root_table("wiki", "audit"))
        write("demo-plugin/README.md", "2개 스킬과 1개 에이전트: `wiki` `audit`\n")
        write("CLAUDE.md", claude_md(2, "wiki", "audit"))
        skills, _, violations = check_all(td)
        if len(skills) != 2:
            failures.append(f"find_skills: expected 2, got {len(skills)}")
        if violations:
            failures.append(f"clean case: expected no violations, got {violations}")

        # Case 2: root README table row for `audit` deleted.
        write("README.md", root_table("wiki"))
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        if ("missing_in_root_readme", "audit") not in kinds:
            failures.append(f"missing-in-root case: expected missing_in_root_readme/audit, got {violations}")

        # Case 2b: the deleted row leaves a PROSE mention behind — still a violation.
        # This is the mutation the "anywhere in the file" rule used to pass (#621).
        write("README.md", root_table("wiki", trailer="\n`audit` is documented in the plugin README.\n"))
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        if ("missing_in_root_readme", "audit") not in kinds:
            failures.append(f"prose-only case: prose mention must NOT satisfy the table rule, got {violations}")

        # Case 2c: a blockquoted table row (root README's feedback-loop section) counts.
        write("README.md", root_table("wiki", trailer="\n> | `audit` | quoted table row |\n"))
        _, _, violations = check_all(td)
        if any(v.get("skill") == "audit" and v["kind"] == "missing_in_root_readme" for v in violations):
            failures.append(f"blockquoted-table case: expected `audit` satisfied, got {violations}")
        write("README.md", root_table("wiki", "audit"))

        # Case 2d: the 진입점 table (outside demo-plugin's section) repeats every name —
        # it must NOT stand in for the plugin's own catalogue row.
        write("README.md", root_table("wiki"))
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        if ("missing_in_root_readme", "audit") not in kinds:
            failures.append(f"section-scope case: an out-of-section table row must not satisfy the rule, got {violations}")
        write("README.md", root_table("wiki", "audit"))

        # Case 2e: root README has no section for the plugin at all.
        write("README.md", "# kit\n\n| 이럴 때 | 스킬 |\n|---|---|\n| when | `wiki` `audit` |\n")
        _, _, violations = check_all(td)
        if not any("has no `demo-plugin` section" in v["detail"] for v in violations):
            failures.append(f"missing-section case: expected a missing-section violation, got {violations}")
        write("README.md", root_table("wiki", "audit"))

        # Case 3: word-boundary — `base` as a skill name must not match inside `database`.
        write("demo-plugin/skills/base/SKILL.md", "---\nname: base\n---\nbody")
        write("README.md", root_table("wiki", "audit", trailer="| x | Uses a database internally |\n"))
        write("demo-plugin/README.md", "3개 스킬과 1개 에이전트: `wiki` `audit` `base`\n")
        write("CLAUDE.md", claude_md(3, "wiki", "audit", "base"))
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        if ("missing_in_root_readme", "base") not in kinds:
            failures.append(f"word-boundary case: expected `base` flagged despite `database` substring, got {violations}")
        write("README.md", root_table("wiki", "audit", "base", trailer="| x | Uses a database internally |\n"))
        _, _, violations = check_all(td)
        if any(v.get("skill") == "base" for v in violations):
            failures.append(f"word-boundary case: `base` still flagged after adding a real row, got {violations}")
        os.remove(os.path.join(td, "demo-plugin", "skills", "base", "SKILL.md"))
        os.rmdir(os.path.join(td, "demo-plugin", "skills", "base"))
        write("README.md", root_table("wiki", "audit"))
        write("demo-plugin/README.md", "2개 스킬과 1개 에이전트: `wiki` `audit`\n")
        write("CLAUDE.md", claude_md(2, "wiki", "audit"))

        # Case 4: count drift — plugin README claims 3 skills but only 2 exist.
        write("demo-plugin/README.md", "3개 스킬과 1개 에이전트: `wiki` `audit`\n")
        _, _, violations = check_all(td)
        drift = [v for v in violations if v["kind"] == "count_drift"]
        if not drift or "3개 스킬" not in drift[0]["detail"]:
            failures.append(f"count-drift case: expected a count_drift violation, got {violations}")
        write("demo-plugin/README.md", "2개 스킬과 1개 에이전트: `wiki` `audit`\n")

        # Case 4b: CLAUDE.md's REVERSED `스킬 N개` shape drifts (the #621 mutation:
        # revert the count AND drop a name from the enumeration).
        write("CLAUDE.md", claude_md(1, "wiki"))
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        details = " ".join(v["detail"] for v in violations)
        if ("missing_in_claude_md", "audit") not in kinds:
            failures.append(f"claude-md-enumeration case: expected missing_in_claude_md/audit, got {violations}")
        if "1개 스킬" not in details:
            failures.append(f"claude-md-count case: expected a reversed `스킬 1개` count_drift, got {violations}")

        # Case 4c: CLAUDE.md missing the plugin bullet entirely.
        write("CLAUDE.md", "## Project Overview\n\nnothing here\n")
        _, _, violations = check_all(td)
        if not any(v["kind"] == "missing_in_claude_md" for v in violations):
            failures.append(f"missing-claude-bullet case: expected a violation, got {violations}")
        write("CLAUDE.md", claude_md(2, "wiki", "audit"))

        # Case 5: missing plugin README entirely.
        os.remove(os.path.join(td, "demo-plugin", "README.md"))
        _, _, violations = check_all(td)
        if not any(v["kind"] == "missing_plugin_readme" for v in violations):
            failures.append(f"missing-plugin-readme case: expected a violation, got {violations}")

    if failures:
        print("FAIL: check-skill-catalogue-drift self-test")
        for f in failures:
            print(f"  {f}")
        return 1
    print("OK: all check-skill-catalogue-drift self-test cases passed")
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
    if not os.path.isfile(os.path.join(root, "README.md")):
        print(f"ERROR: no README.md found at {root}", file=sys.stderr)
        return 2

    skills, _, violations = check_all(root)
    if not skills:
        print(f"ERROR: no */skills/*/SKILL.md files found under {root}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"checked": len(skills), "violations": violations}, ensure_ascii=False, indent=2))
    elif violations:
        print(f"FAIL: {len(violations)} skill-catalogue drift violation(s) found:")
        for v in violations:
            print(f"  - [{v['kind']}] {v['detail']}")
    else:
        print(f"OK: skill-catalogue clean — {len(skills)} skill(s) checked, all listed in a root "
              f"README.md table row + their own plugin README.md + their {CLAUDE_MD} bullet, "
              f"no `N개 스킬`/`스킬 N개` count drift")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
