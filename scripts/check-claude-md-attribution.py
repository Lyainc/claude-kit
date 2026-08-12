#!/usr/bin/env python3
"""check-claude-md-attribution.py — CLAUDE.md single-plugin script-attribution drift guard (#601).

RULE: when root `CLAUDE.md` names a guard script as belonging to ONE plugin
(`<plugin>는/은/가/이` followed by a backtick-quoted script name — the full topic/subject
particle set: 는/은 mark topic, 가/이 mark subject, and each pairs with a vowel- vs
consonant-final plugin name), that script must
actually be exclusive to that plugin. #250 (E1-EN label drift, guarded by
check-error-label-drift.py) and #380 (hook count miscount) were earlier instances of
the same bug class: CLAUDE.md's descriptive
scope stops tracking reality once a guard/feature spreads from one plugin to several.
#601 is the third recurrence — CLAUDE.md:111 called `check-trigger-regression.py` a
thinking-tools-only guard after all 4 plugins had grown their own copy. This makes that
specific shape of drift mechanical instead of relying on manual review to catch it again.

SCOPING: only root CLAUDE.md is scanned (the always-loaded doc named in #601's own
scope note) — plugin-local READMEs are lower-stakes and out of scope here. A "plugin" is
any top-level dir carrying `.claude-plugin/plugin.json` (same definition
check-plugin-root-paths.py uses). A script's real ownership is every plugin whose
`scripts/` tree (recursive) contains a file with that basename.

Usage:
    python3 scripts/check-claude-md-attribution.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = clean (no single-plugin attribution contradicts actual script ownership).
            1 = stale attribution found. 2 = usage error / CLAUDE.md or no plugin dirs found.
"""
import argparse
import json
import os
import re
import subprocess
import sys

CLAUDE_MD_REL = "CLAUDE.md"
SCRIPT_EXT = (".py", ".sh")


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def plugin_roots(root):
    """Top-level dirs carrying a plugin manifest — keyed off the manifest so a new
    plugin is picked up for free (same approach as check-plugin-root-paths.py)."""
    return sorted(
        d for d in os.listdir(root)
        if os.path.isfile(os.path.join(root, d, ".claude-plugin", "plugin.json"))
    )


def script_ownership(root, plugins):
    """Return {basename: set(plugin names whose scripts/ tree contains that basename)}."""
    ownership = {}
    for plugin in plugins:
        scripts_dir = os.path.join(root, plugin, "scripts")
        if not os.path.isdir(scripts_dir):
            continue
        for dirpath, _dirnames, filenames in os.walk(scripts_dir):
            for name in filenames:
                if name.endswith(SCRIPT_EXT):
                    ownership.setdefault(name, set()).add(plugin)
    return ownership


def find_attributions(text, plugins):
    """Return [(line, plugin, script)] for every `<plugin><particle> `<script>`` mention."""
    plugin_alt = "|".join(re.escape(p) for p in sorted(plugins, key=len, reverse=True))
    pattern = re.compile(
        r"(?P<plugin>" + plugin_alt + r")(?:는|은|가|이)\s*`(?P<script>[\w.\-]+\.(?:py|sh))`"
    )
    hits = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in pattern.finditer(line):
            hits.append((lineno, m.group("plugin"), m.group("script")))
    return hits


def check_attribution(root):
    """Return (ok, report). ok=True means every single-plugin script attribution in
    CLAUDE.md matches that script's actual (exclusive) ownership."""
    report = {"root": root, "plugins": [], "attributions_checked": 0, "violations": []}
    claude_md_path = os.path.join(root, CLAUDE_MD_REL)
    if not os.path.isfile(claude_md_path):
        report["fatal"] = f"{CLAUDE_MD_REL} not found"
        return False, report

    plugins = plugin_roots(root)
    if not plugins:
        report["fatal"] = "no plugin dirs found (no */.claude-plugin/plugin.json)"
        return False, report
    report["plugins"] = plugins

    with open(claude_md_path, encoding="utf-8") as fh:
        text = fh.read()

    ownership = script_ownership(root, plugins)
    hits = find_attributions(text, plugins)
    report["attributions_checked"] = len(hits)

    for lineno, plugin, script in hits:
        actual = ownership.get(script, set())
        if actual != {plugin}:
            report["violations"].append({
                "line": lineno,
                "plugin": plugin,
                "script": script,
                "actual_owners": sorted(actual),
            })

    return (len(report["violations"]) == 0), report


def run_self_test():
    failures = []
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        for plugin in ("plugin-a", "plugin-b"):
            os.makedirs(os.path.join(td, plugin, ".claude-plugin"))
            with open(os.path.join(td, plugin, ".claude-plugin", "plugin.json"), "w") as fh:
                fh.write("{}")
            os.makedirs(os.path.join(td, plugin, "scripts", "test"))

        # shared.py exists in BOTH plugins; only-a.py exists in plugin-a alone.
        with open(os.path.join(td, "plugin-a", "scripts", "test", "shared.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(td, "plugin-b", "scripts", "test", "shared.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(td, "plugin-a", "scripts", "test", "only-a.py"), "w") as fh:
            fh.write("")

        # violating: CLAUDE.md claims shared.py is plugin-a-only.
        with open(os.path.join(td, CLAUDE_MD_REL), "w", encoding="utf-8") as fh:
            fh.write("guard doc(plugin-a는 `shared.py`가 드롭을 감지), rest of sentence.\n")
        ok, report = check_attribution(td)
        if ok or [v["script"] for v in report["violations"]] != ["shared.py"]:
            failures.append(f"  violating case: expected shared.py flagged, got {report['violations']}")
        if report["violations"] and report["violations"][0]["actual_owners"] != ["plugin-a", "plugin-b"]:
            failures.append(f"  violating case: wrong actual_owners {report['violations']}")

        # violating, via the 이 particle (subject case, consonant-final pair of 가) instead of
        # 는 (topic case) — locks in that 이-particle matching is intentional Korean grammar
        # coverage, not accidental overmatching (#603). 은/가 are not separately exercised here;
        # this case plus the pre-existing 는 case above are the two particles #603 was about.
        with open(os.path.join(td, CLAUDE_MD_REL), "w", encoding="utf-8") as fh:
            fh.write("guard doc(plugin-a이 `shared.py`를 검사), rest of sentence.\n")
        ok1b, report1b = check_attribution(td)
        if ok1b or [v["script"] for v in report1b["violations"]] != ["shared.py"]:
            failures.append(f"  이-particle case: expected shared.py flagged, got {report1b['violations']}")

        # clean: correctly attributed to the plugin that exclusively owns it.
        with open(os.path.join(td, CLAUDE_MD_REL), "w", encoding="utf-8") as fh:
            fh.write("guard doc(plugin-a는 `only-a.py`가 드롭을 감지), rest of sentence.\n")
        ok2, report2 = check_attribution(td)
        if not ok2 or report2["violations"]:
            failures.append(f"  exclusive-owner case: expected clean, got {report2['violations']}")

        # clean: generalized phrasing names no single plugin, so no attribution is parsed.
        with open(os.path.join(td, CLAUDE_MD_REL), "w", encoding="utf-8") as fh:
            fh.write("guard doc(각 플러그인의 `shared.py`가 드롭을 감지), rest of sentence.\n")
        ok3, report3 = check_attribution(td)
        if not ok3 or report3["attributions_checked"] != 0:
            failures.append(f"  generalized-phrasing case: expected 0 attributions parsed, got {report3}")

        # fatal: no plugin dirs.
        with tempfile.TemporaryDirectory() as td_empty:
            with open(os.path.join(td_empty, CLAUDE_MD_REL), "w") as fh:
                fh.write("no plugins here\n")
            ok4, report4 = check_attribution(td_empty)
            if ok4 or not report4.get("fatal"):
                failures.append(f"  no-plugins case: expected fatal, got {report4}")

    if failures:
        print("FAIL: check-claude-md-attribution self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-claude-md-attribution self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="CLAUDE.md single-plugin script-attribution drift guard")
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory + fixture cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    ok, report = check_attribution(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("fatal"):
        print(f"ERROR: {report['fatal']}")
    elif ok:
        print(f"OK: claude-md-attribution clean — {report['attributions_checked']} "
              f"single-plugin script attribution(s) checked against {len(report['plugins'])} "
              f"plugin(s), all exclusive as claimed")
    else:
        print(f"FAIL: {len(report['violations'])} stale attribution(s) found in {CLAUDE_MD_REL}:")
        for v in report["violations"]:
            print(f"  - line {v['line']}: `{v['script']}` attributed to {v['plugin']} only, "
                  f"but actually owned by {v['actual_owners']}")
        print("Fix: generalize the phrasing (e.g. '각 플러그인의') or name every owning plugin.")

    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
