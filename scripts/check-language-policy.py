#!/usr/bin/env python3
"""check-language-policy.py — marketplace-facing metadata English-mandate guard (S2).

RULE (narrow, deterministic): the marketplace-facing metadata that CLAUDE.md's
`## Language Policy` mandates as English MUST contain NO Hangul. Specifically, the
`description` and `keywords` of every plugin's `.claude-plugin/plugin.json` AND the
matching entries in `.claude-plugin/marketplace.json` must contain no Hangul
codepoints (Hangul Syllables U+AC00..U+D7A3, plus the Jamo blocks: U+1100..U+11FF
Hangul Jamo, U+3130..U+318F Compatibility Jamo, U+A960..U+A97F Jamo Extended-A,
U+D7B0..U+D7FF Jamo Extended-B).

OBJECTIVE DAMAGE (claude-kit-work-rules/constraint-6 — policy, not taste): these are the cross-marketplace,
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

BODY CONTRACT (plugin-language-instructions, #835): the bodies (frontmatter excluded) of
`skills/*/SKILL.md` and `agents/*.md` in feedback-loop, thinking-tools, obsidian-vault-manager
and vault-bridge carry the user-facing language instruction exactly once, as the sentence
`Write user-facing output in Korean; if the user writes in English, answer in English.`
This script pins only three narrow, deterministic facts per body: that sentence appears
exactly once, the phrase "English for LLM" is absent, and "MUST be in Korean" is absent.
Sanctioned Korean zones (trigger examples, Korean templates, artifact-language exceptions)
stay unchecked, so this is not a general body-language gate.

Usage:
    python3 scripts/check-language-policy.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = clean (no Hangul in mandated metadata; body contract held), 1 = violations found,
            2 = usage / unreadable input.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys

# Fields on each plugin (in BOTH plugin.json and the marketplace entry) that the
# Language Policy mandates as English. `description` is a string; `keywords` is a list.
MANDATED_FIELDS = ("description", "keywords")

# Plugins whose skill/agent BODIES must carry the language contract exactly once.
BODY_PLUGINS = ("feedback-loop", "thinking-tools", "obsidian-vault-manager", "vault-bridge")

CONTRACT_SENTENCE = (
    "Write user-facing output in Korean; if the user writes in English, answer in English."
)
# literal phrases that must NOT appear in a target body
BODY_FORBIDDEN = ("English for LLM", "MUST be in Korean")

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
                "kind": "metadata",
                "source": source_label,
                "plugin": plugin_name,
                "field": field,
                "hangul": hangul,
            })
    return violations


def _strip_frontmatter(text):
    """Return the body of a markdown file, dropping a leading `---` ... `---` block."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", text, re.S)
    return m.group(2) if m else text


def _iter_body_files(root):
    """Yield (plugin, repo-relative path) for each target skill/agent file that exists."""
    for plugin in BODY_PLUGINS:
        for pattern in ("skills/*/SKILL.md", "agents/*.md"):
            for f in sorted(glob.glob(os.path.join(root, plugin, pattern))):
                if os.path.isfile(f):
                    yield plugin, os.path.relpath(f, root)


def scan_body(text, rel, plugin):
    """Return body-contract violation dicts for one skill/agent file's text."""
    body = _strip_frontmatter(text)
    violations = []
    count = body.count(CONTRACT_SENTENCE)
    if count != 1:
        violations.append({"kind": "body", "source": rel, "plugin": plugin, "body": "contract-sentence",
                           "detail": f"appears {count} time(s), expected exactly 1"})
    lowered = body.lower()
    for phrase in BODY_FORBIDDEN:
        if phrase.lower() in lowered:
            violations.append({"kind": "body", "source": rel, "plugin": plugin,
                               "body": "forbidden-phrase", "detail": f'contains "{phrase}"'})
    return violations


def check_bodies(root, report):
    """Scan every target body under `root`; append to `report` and return this scan's violations."""
    found = []
    present = [p for p in BODY_PLUGINS if os.path.isdir(os.path.join(root, p))]
    if present:  # a plugin repo: every target plugin must exist and yield bodies, or the gate scans nothing
        seen = {p for p, _ in _iter_body_files(root)}
        for plugin in BODY_PLUGINS:
            if plugin not in seen:
                found.append({"fatal": f"[{plugin}] no skills/*/SKILL.md or agents/*.md bodies found"})
                report["fatal"] = True
    for plugin, rel in _iter_body_files(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            found.append({"fatal": f"[{plugin}] {rel} unreadable: {exc}"})
            report["fatal"] = True
            continue
        report.setdefault("bodies_checked", []).append(rel)
        found.extend(scan_body(text, rel, plugin))
    report["violations"].extend(found)
    return found


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

    if check_bodies(root, report):
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

    # BODY CONTRACT fixtures: a target body must carry the contract sentence exactly once.
    fm = "---\nname: x\n---\n\n"
    ok_skill = ("---\nname: s\ndescription: \"English for LLM MUST be in Korean (frontmatter ignored)\"\n---\n\n"
                + CONTRACT_SENTENCE + " Artifacts keep their own language.\n")
    body_cases = (
        # (name, {relpath: text}, expected violation "body" kind or None for clean)
        ("clean bodies (frontmatter phrases ignored)",
         {"thinking-tools/skills/s/SKILL.md": ok_skill,
          "vault-bridge/agents/a.md": fm + CONTRACT_SENTENCE + "\n"}, None),
        ("out-of-scope files",
         {"other-plugin/skills/s/SKILL.md": "no contract here\n",
          "thinking-tools/skills/s/reference.md": "no contract here\n"}, None),
        ("missing contract",
         {"feedback-loop/skills/s/SKILL.md": fm + "No language rule.\n"}, "contract-sentence"),
        ("duplicated contract",
         {"obsidian-vault-manager/agents/a.md": fm + CONTRACT_SENTENCE + "\n\n" + CONTRACT_SENTENCE + "\n"},
         "contract-sentence"),
        ("'English for LLM'",
         {"thinking-tools/agents/a.md": fm + CONTRACT_SENTENCE + "\nInstructions are English for LLM parsing.\n"},
         "forbidden-phrase"),
        ("'MUST be in Korean'",
         {"vault-bridge/skills/s/SKILL.md": fm + CONTRACT_SENTENCE + "\nReplies MUST be in Korean.\n"},
         "forbidden-phrase"),
        ("forbidden phrase in other case",
         {"vault-bridge/skills/s/SKILL.md": fm + CONTRACT_SENTENCE + "\nReplies must be in korean.\n"},
         "forbidden-phrase"),
    )
    for name, files, expected in body_cases:
        with tempfile.TemporaryDirectory() as tmp:
            _build(tmp, "Plugin", ["skills"], "Plugin", ["skills"])
            files = dict(files)
            for plugin in BODY_PLUGINS:  # every target plugin needs at least one body
                if not any(fnmatch.fnmatch(rel, f"{plugin}/{pat}") for rel in files
                           for pat in ("skills/*/SKILL.md", "agents/*.md")):
                    files[f"{plugin}/agents/base.md"] = fm + CONTRACT_SENTENCE + "\n"
            for rel, text in files.items():
                path = os.path.join(tmp, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            ok, report = check_language_policy(tmp)
        kinds = {v.get("body") for v in report["violations"] if v.get("kind") == "body"}
        if expected is None:
            if not ok or report["violations"]:
                failures.append(f"  {name}: expected ok=True, got {report['violations']}")
        elif ok or expected not in kinds:
            failures.append(f"  {name}: expected flagged {expected}, got ok={ok} {report['violations']}")
    # A target plugin that yields no bodies (renamed/moved layout) must not pass as clean.
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp, "Plugin", ["skills"], "Plugin", ["skills"])
        os.makedirs(os.path.join(tmp, "thinking-tools", "agents"))
        with open(os.path.join(tmp, "thinking-tools", "agents", "a.md"), "w", encoding="utf-8") as fh:
            fh.write(fm + CONTRACT_SENTENCE + "\n")
        ok, report = check_language_policy(tmp)
    if ok or not any("no skills/*/SKILL.md" in v.get("fatal", "") for v in report["violations"]):
        failures.append(f"  empty target plugin: expected fatal, got ok={ok} {report['violations']}")
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
        b = len(report.get("bodies_checked", []))
        meta_v = [v for v in report["violations"] if v.get("kind") == "metadata"]
        body_v = [v for v in report["violations"] if v.get("kind") == "body"]
        if ok:
            print(f"OK: language-policy clean — {n} metadata source(s) checked, "
                  "no Hangul in marketplace-facing description/keywords; "
                  f"{b} skill/agent body(ies) carry the language contract once")
        else:
            if meta_v:
                print("VIOLATION: Hangul found in English-mandated marketplace metadata:")
                for v in meta_v:
                    chars = " ".join(v["hangul"])
                    print(f"  - {v['source']} [{v['plugin']}] {v['field']}: contains Hangul ({chars})")
                print("Fix: keep description/keywords ASCII-English in BOTH "
                      ".claude-plugin/plugin.json and .claude-plugin/marketplace.json "
                      "(CLAUDE.md 'Language Policy' — README descriptions: English by default). "
                      "Typographic symbols (–, →, ⑤) are allowed; Hangul is not.")
            if body_v:
                print("VIOLATION: skill/agent body breaks the language contract:")
                for v in body_v:
                    print(f"  - {v['source']} [{v['plugin']}] {v['detail']}")
                print(f'Fix: state "{CONTRACT_SENTENCE}" exactly once in the body, '
                      'and drop "English for LLM" / "MUST be in Korean" wording.')

    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
