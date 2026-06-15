#!/usr/bin/env python3
"""check-language-policy.py — marketplace-facing metadata English-mandate guard (S2).

RULE (narrow, deterministic): the marketplace-facing metadata that CLAUDE.md's
`## Language Policy` mandates as English MUST contain NO Hangul. Specifically, the
`description` and `keywords` of every plugin's `.claude-plugin/plugin.json` AND the
matching entries in `.claude-plugin/marketplace.json` must contain no Hangul
codepoints (Hangul Syllables U+AC00..U+D7A3, plus the Jamo blocks: U+1100..U+11FF
Hangul Jamo, U+3130..U+318F Compatibility Jamo, U+A960..U+A97F Jamo Extended-A,
U+D7B0..U+D7FF Jamo Extended-B).

OBJECTIVE DAMAGE (c6 — policy, not taste): these are the cross-marketplace,
English-mandated descriptions. CLAUDE.md's Language Policy states "README descriptions:
English by default" and the Version Sync Rule treats `description`/`keywords` as synced
fields enforced across plugin.json ↔ marketplace.json. Korean leaking into this public
marketplace surface breaks the English-consistency contract that every downstream
consumer (the marketplace listing, version-sync, README parity) relies on. This is an
OBJECTIVE breakage of a stated contract on a public surface — not a style preference.

WHY HANGUL-ONLY (not ASCII-only): Korean is LEGITIMATELY present throughout the repo —
SKILL.md descriptions embed Korean trigger phrases, reference/ docs and I/O directives
are Korean by policy. And even these marketplace descriptions legitimately use non-ASCII
TYPOGRAPHY (en-dash `–`, em-dash `—`, arrows `↔` `→`, circled digits `⑤`). An
"ASCII-only" rule would be FP-laden and would flag sanctioned typography. We therefore
flag ONLY Hangul codepoints, which is the precise signal the policy mandates against.

SOFT REMAINDER (deferred to RULES.md, NOT enforced here): body-language — the policy's
"Skill instructions / Agent instructions: English for LLM-optimized parsing" for
SKILL.md and agents/*.md BODIES — is a GRAY ZONE. Those bodies contain sanctioned Korean
zones (Korean I/O directives, trigger examples, Korean template content). Per c6, a check
there would be either FP-laden or require taste-laden zone carve-outs, so body-language
stays a SOFT rule documented in RULES.md, not a hard gate in this script.

Usage:
    python3 scripts/check-language-policy.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = clean (no Hangul in mandated metadata), 1 = violations found,
            2 = usage / unreadable input.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Fields on each plugin (in BOTH plugin.json and the marketplace entry) that the
# Language Policy mandates as English. `description` is a string; `keywords` is a list.
MANDATED_FIELDS = ("description", "keywords")

# Hangul codepoint ranges (syllables + all Jamo blocks). A single regex character class.
_HANGUL = re.compile(
    "["
    "가-힣"   # Hangul Syllables
    "ᄀ-ᇿ"   # Hangul Jamo
    "㄰-㆏"   # Hangul Compatibility Jamo
    "ꥠ-꥿"   # Hangul Jamo Extended-A
    "ힰ-퟿"   # Hangul Jamo Extended-B
    "]"
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


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _hangul_in(value):
    """Return the sorted set of distinct Hangul chars found in a string-or-list field."""
    found = set()
    if isinstance(value, str):
        found.update(_HANGUL.findall(value))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                found.update(_HANGUL.findall(item))
    return sorted(found)


def scan_fields(obj, source_label, plugin_name):
    """Return a list of violation dicts for any Hangul in the mandated fields of `obj`."""
    violations = []
    for field in MANDATED_FIELDS:
        if field not in obj:
            continue
        hangul = _hangul_in(obj[field])
        if hangul:
            violations.append({
                "source": source_label,
                "plugin": plugin_name,
                "field": field,
                "hangul": hangul,
            })
    return violations


def check_language_policy(root):
    """Return (ok, report). ok=True means no Hangul in the mandated marketplace metadata.

    Scans BOTH each plugin's `.claude-plugin/plugin.json` (description/keywords) AND the
    matching entry in `.claude-plugin/marketplace.json`. A missing/unreadable
    marketplace.json is fatal (the surface can't be checked).
    """
    report = {"root": root, "checked": [], "violations": []}
    mp_path = os.path.join(root, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(mp_path):
        report["violations"].append({"fatal": f"marketplace.json not found: {mp_path}"})
        report["fatal"] = True
        return False, report

    try:
        marketplace = _load_json(mp_path)
    except (json.JSONDecodeError, OSError) as exc:
        report["violations"].append({"fatal": f"marketplace.json unreadable: {mp_path} ({exc})"})
        report["fatal"] = True
        return False, report

    plugins = marketplace.get("plugins", [])
    if not plugins:
        report["violations"].append({"fatal": "marketplace.json has no plugins[]"})
        report["fatal"] = True
        return False, report

    ok = True
    for entry in plugins:
        name = entry.get("name", "<unnamed>")
        source = entry.get("source", "")

        # 1) the marketplace.json entry itself
        report["checked"].append(f"marketplace.json[{name}]")
        ev = scan_fields(entry, "marketplace.json", name)
        if ev:
            report["violations"].extend(ev)
            ok = False

        # 2) the plugin's own plugin.json
        pj_path = os.path.normpath(
            os.path.join(root, source, ".claude-plugin", "plugin.json")
        )
        if not os.path.isfile(pj_path):
            # Missing plugin.json is version-sync's concern (exit-coded there), not this
            # guard's — we only assert the language of files that exist. Skip silently.
            continue
        try:
            plugin_json = _load_json(pj_path)
        except (json.JSONDecodeError, OSError) as exc:
            report["violations"].append({"fatal": f"[{name}] plugin.json unreadable: {exc}"})
            report["fatal"] = True
            ok = False
            continue
        report["checked"].append(os.path.join(source, ".claude-plugin", "plugin.json"))
        pv = scan_fields(plugin_json, "plugin.json", name)
        if pv:
            report["violations"].extend(pv)
            ok = False

    return ok, report


def run_self_test():
    """In-memory fixtures: >=1 VIOLATION case (flagged) + >=1 CLEAN case (FP=0).

    The clean case deliberately includes sanctioned non-ASCII typography (en-dash,
    arrow, circled digit) to prove the Hangul-only rule does NOT flag it.
    """
    import tempfile

    def _build(tmp, plugin_desc, plugin_keywords, mp_desc, mp_keywords):
        os.makedirs(os.path.join(tmp, "demo", ".claude-plugin"))
        os.makedirs(os.path.join(tmp, ".claude-plugin"))
        with open(os.path.join(tmp, "demo", ".claude-plugin", "plugin.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"name": "demo", "version": "1.0.0",
                       "description": plugin_desc, "keywords": plugin_keywords}, fh,
                      ensure_ascii=False)
        with open(os.path.join(tmp, ".claude-plugin", "marketplace.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"name": "mp", "version": "1.0.0", "plugins": [
                {"name": "demo", "version": "1.0.0", "description": mp_desc,
                 "keywords": mp_keywords, "source": "./demo/"}]}, fh, ensure_ascii=False)

    failures = []

    # CLEAN: ASCII English + sanctioned typography (–, →, ⑤). Must pass with FP=0.
    with tempfile.TemporaryDirectory() as tmp:
        clean_desc = "Claude Code thinking-tools – layer ⑤ orchestration → done"
        _build(tmp, clean_desc, ["skills", "thinking"], clean_desc, ["skills", "thinking"])
        ok, report = check_language_policy(tmp)
        if not ok:
            failures.append(f"  clean case: expected ok=True, got violations {report['violations']}")
        if report.get("violations"):
            failures.append(f"  clean case: expected zero violations (FP), got {report['violations']}")

    # VIOLATION (plugin.json description has Hangul). Must be flagged ok=False.
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp, "사고 도구 플러그인", ["skills"], "Thinking-tools plugin", ["skills"])
        ok, report = check_language_policy(tmp)
        if ok:
            failures.append("  plugin.json Hangul desc: expected ok=False, got ok=True")
        if not any(v.get("source") == "plugin.json" and v.get("field") == "description"
                   for v in report["violations"]):
            failures.append(f"  plugin.json Hangul desc: not flagged, got {report['violations']}")

    # VIOLATION (marketplace.json keyword has Hangul). Must be flagged.
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp, "Plugin", ["skills"], "Plugin", ["skills", "사고도구"])
        ok, report = check_language_policy(tmp)
        if ok:
            failures.append("  marketplace Hangul keyword: expected ok=False, got ok=True")
        if not any(v.get("source") == "marketplace.json" and v.get("field") == "keywords"
                   for v in report["violations"]):
            failures.append(f"  marketplace Hangul keyword: not flagged, got {report['violations']}")

    # Jamo-only (compatibility jamo ㄱ) must also be caught, not just full syllables.
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp, "Plugin ㄱ", ["skills"], "Plugin", ["skills"])
        ok, report = check_language_policy(tmp)
        if ok:
            failures.append("  jamo desc: expected ok=False (compatibility jamo), got ok=True")

    # Missing marketplace.json is fatal (exit 2).
    with tempfile.TemporaryDirectory() as tmp:
        ok, report = check_language_policy(tmp)
        if not report.get("fatal"):
            failures.append("  missing marketplace.json: expected fatal=True")

    if failures:
        print("FAIL: check-language-policy self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-language-policy self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="marketplace-facing metadata English-mandate (no-Hangul) guard")
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory fixtures")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    ok, report = check_language_policy(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("fatal"):
        for v in report["violations"]:
            if "fatal" in v:
                print(f"ERROR: {v['fatal']}")
    else:
        n = len(report["checked"])
        if ok:
            print(f"OK: language-policy clean — {n} metadata source(s) checked, "
                  "no Hangul in marketplace-facing description/keywords")
        else:
            print("VIOLATION: Hangul found in English-mandated marketplace metadata:")
            for v in report["violations"]:
                if "fatal" in v:
                    continue
                chars = " ".join(v["hangul"])
                print(f"  - {v['source']} [{v['plugin']}] {v['field']}: contains Hangul ({chars})")
            print("Fix: keep description/keywords ASCII-English in BOTH "
                  ".claude-plugin/plugin.json and .claude-plugin/marketplace.json "
                  "(CLAUDE.md 'Language Policy' — README descriptions: English by default). "
                  "Typographic symbols (–, →, ⑤) are allowed; Hangul is not.")

    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
