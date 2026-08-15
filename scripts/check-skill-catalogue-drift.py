#!/usr/bin/env python3
"""check-skill-catalogue-drift.py — every skill stays listed where CLAUDE.md requires (#621).

RULE: CLAUDE.md's "Adding a New Skill" step 6 (#173) makes ONE catalogue entry point
MANDATORY for every skill: the root README.md's skill table, plus (by the same
discoverability logic) the skill's own plugin README.md. The
docs/design/4-flow-catalog.md entry is explicitly conditional ("4-흐름에 맞을 때만") and
is NOT enforced here. #621 shipped three drifts of exactly this shape (retired audit
codes still advertised, a stale README skill list, a missing LICENSE) with the same root
cause named in the issue: "카탈로그가 소스보다 늦게 움직이는데 그걸 보는 가드가 없다" — no
guard watches the catalogue, so it silently falls out of sync the next time a skill is
added, renamed, or removed. This guard is that watch.

Two checks, both mechanical:
  1. CATALOGUE: every `*/skills/<name>/SKILL.md` file's skill name (the directory name)
     must appear as a whole word somewhere in root README.md AND in `<plugin>/README.md`.
     Word boundary treats `-`/`_` as part of the word, so `wiki` doesn't false-positive
     inside `wikilink` but DOES match inside a backticked `/vault-manifest-refresh`-style
     mention (a plain substring check would either miss the latter or match "database" for
     skill name "base" — this guard requires an actual boundary on both sides). This
     deliberately does NOT parse markdown table structure — a name can appear in the
     plugin's skill table, a slash-command table, or explanatory prose right after the
     table, and all three are legitimate discoverability entries per the skills observed
     in this repo (e.g. `/vault-manifest-refresh` sits in prose below vault-bridge's skill
     table in the root README, not inside the table itself).
  2. COUNT: a plugin README.md sentence of the exact Korean shape `N개 스킬` / `N개
     에이전트` (e.g. "9개 스킬과 1개 에이전트") must match the real count of
     `<plugin>/skills/*/SKILL.md` / `<plugin>/agents/*.md` files. This is intentionally
     narrow — only this one mechanical phrasing is matched. A prose count that isn't this
     exact shape (e.g. feedback-loop's "Four pieces ship together", which counts 3 skills
     PLUS the non-skill telemetry component as one more "piece") is left unchecked on
     purpose: checking it against a bare skill/agent count would itself be a false
     positive, and inventing a general natural-language number parser is exactly the
     fragile matcher #621 asked this guard NOT to become.

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

COUNT_RE = re.compile(r"(\d+)개\s*(스킬|에이전트)")


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


def check_catalogue_presence(root, skills, root_readme_text, plugin_readme_cache):
    """Return a list of {kind, plugin, skill, detail} violations for missing entries."""
    violations = []
    for s in skills:
        plugin, name = s["plugin"], s["name"]
        if root_readme_text is None or not _word_re(name).search(root_readme_text):
            violations.append({
                "kind": "missing_in_root_readme", "plugin": plugin, "skill": name,
                "detail": f"`{name}` not found (as a whole word) in root README.md",
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


def check_counts(root, skills, plugin_readme_cache):
    """Return a list of {kind, plugin, detail} violations for stale `N개 스킬`/`N개 에이전트`."""
    violations = []
    plugins = sorted({s["plugin"] for s in skills})
    for plugin in plugins:
        actual_skills = sum(1 for s in skills if s["plugin"] == plugin)
        actual_agents = len(glob.glob(os.path.join(root, plugin, "agents", "*.md")))

        plugin_readme_path = os.path.join(plugin, "README.md")
        if plugin_readme_path not in plugin_readme_cache:
            plugin_readme_cache[plugin_readme_path] = _read(os.path.join(root, plugin_readme_path))
        text = plugin_readme_cache[plugin_readme_path]
        if text is None:
            continue  # already reported by check_catalogue_presence

        for m in COUNT_RE.finditer(text):
            claimed, unit = int(m.group(1)), m.group(2)
            actual = actual_skills if unit == "스킬" else actual_agents
            if claimed != actual:
                violations.append({
                    "kind": "count_drift", "plugin": plugin,
                    "detail": (f"{plugin_readme_path} claims `{claimed}개 {unit}` but "
                               f"{plugin}/{'skills' if unit == '스킬' else 'agents'} has {actual}"),
                })
    return violations


def check_all(root):
    root_readme_text = _read(os.path.join(root, "README.md"))
    skills = find_skills(root)
    plugin_readme_cache = {}
    violations = []
    violations += check_catalogue_presence(root, skills, root_readme_text, plugin_readme_cache)
    violations += check_counts(root, skills, plugin_readme_cache)
    return skills, root_readme_text, violations


def run_self_test():
    import tempfile
    failures = []

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "demo-plugin", "skills", "wiki"))
        os.makedirs(os.path.join(td, "demo-plugin", "skills", "audit"))
        os.makedirs(os.path.join(td, "demo-plugin", "agents"))
        for name in ("wiki", "audit"):
            with open(os.path.join(td, "demo-plugin", "skills", name, "SKILL.md"), "w") as fh:
                fh.write(f"---\nname: {name}\n---\nbody")
        with open(os.path.join(td, "demo-plugin", "agents", "a.md"), "w") as fh:
            fh.write("agent")

        # Case 1: clean — both skills mentioned everywhere, counts correct.
        with open(os.path.join(td, "README.md"), "w") as fh:
            fh.write("root catalogue: `wiki`, `audit`\n")
        with open(os.path.join(td, "demo-plugin", "README.md"), "w") as fh:
            fh.write("2개 스킬과 1개 에이전트: `wiki` `audit`\n")
        skills, _, violations = check_all(td)
        if len(skills) != 2:
            failures.append(f"find_skills: expected 2, got {len(skills)}")
        if violations:
            failures.append(f"clean case: expected no violations, got {violations}")

        # Case 2: root README missing `audit`.
        with open(os.path.join(td, "README.md"), "w") as fh:
            fh.write("root catalogue: `wiki` only\n")
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        if ("missing_in_root_readme", "audit") not in kinds:
            failures.append(f"missing-in-root case: expected missing_in_root_readme/audit, got {violations}")
        with open(os.path.join(td, "README.md"), "w") as fh:
            fh.write("root catalogue: `wiki`, `audit`\n")

        # Case 3: word-boundary — `base` as a skill name must not match inside `database`.
        os.makedirs(os.path.join(td, "demo-plugin", "skills", "base"))
        with open(os.path.join(td, "demo-plugin", "skills", "base", "SKILL.md"), "w") as fh:
            fh.write("---\nname: base\n---\nbody")
        with open(os.path.join(td, "README.md"), "w") as fh:
            fh.write("root catalogue: `wiki`, `audit`. Uses a database internally.\n")
        with open(os.path.join(td, "demo-plugin", "README.md"), "w") as fh:
            fh.write("3개 스킬과 1개 에이전트: `wiki` `audit` `base`\n")
        _, _, violations = check_all(td)
        kinds = {(v["kind"], v.get("skill")) for v in violations}
        if ("missing_in_root_readme", "base") not in kinds:
            failures.append(f"word-boundary case: expected `base` flagged despite `database` substring, got {violations}")
        with open(os.path.join(td, "README.md"), "w") as fh:
            fh.write("root catalogue: `wiki`, `audit`, `base`. Uses a database internally.\n")
        _, _, violations = check_all(td)
        if any(v.get("skill") == "base" for v in violations):
            failures.append(f"word-boundary case: `base` still flagged after adding a real mention, got {violations}")
        os.remove(os.path.join(td, "demo-plugin", "skills", "base", "SKILL.md"))
        os.rmdir(os.path.join(td, "demo-plugin", "skills", "base"))
        with open(os.path.join(td, "demo-plugin", "README.md"), "w") as fh:
            fh.write("2개 스킬과 1개 에이전트: `wiki` `audit`\n")

        # Case 4: count drift — README claims 3 skills but only 2 exist.
        with open(os.path.join(td, "demo-plugin", "README.md"), "w") as fh:
            fh.write("3개 스킬과 1개 에이전트: `wiki` `audit`\n")
        _, _, violations = check_all(td)
        drift = [v for v in violations if v["kind"] == "count_drift"]
        if not drift or "3개 스킬" not in drift[0]["detail"]:
            failures.append(f"count-drift case: expected a count_drift violation, got {violations}")

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
        print(f"OK: skill-catalogue clean — {len(skills)} skill(s) checked, all listed in root "
              f"README.md + their own plugin README.md, no `N개 스킬`/`N개 에이전트` count drift")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
