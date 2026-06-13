#!/usr/bin/env python3
"""check-type-optin.py — vault-note `type:` opt-in regression guard (work-rules S1).

RULE (vault second-brain v4 §2.2): a committed Markdown file whose YAML frontmatter
carries the *vault signal* — it declares BOTH `created:` AND `tags:` at the top level,
i.e. it represents a vault note — MUST also declare a top-level `type:` field.

OBJECTIVE DAMAGE (c6 — policy, not taste): v4 §2.2 makes `type:` the opt-in marker for
claude-kit management. A vault file WITHOUT `type:` is INVISIBLE to claude-kit — it is
silently dropped from the manifest and from audit (never surfaced, never managed). So a
template, fixture, or doc that emits vault-style frontmatter but forgets `type:` is a real
regression that *loses notes* with no error. That is objective damage, not a style
preference — the missing field changes program behavior (note disappears), it isn't taste.

SCOPING for FP=0: only files carrying the FULL vault signal (`created:` AND `tags:`) are
treated as vault notes. Ordinary repo docs — READMEs, design docs, specs that happen to
have only `created:` (or only `tags:`, or neither) — are NOT vault notes and are ignored.
Frontmatter is read only from the leading `---`…`---` fenced block; a `created:`/`tags:`
appearing in body prose or inside a fenced code block never trips the check.

Usage:
    python3 scripts/check-type-optin.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = clean (no vault-note missing `type:`), 1 = violations found,
            2 = usage / unreadable input.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Top-level frontmatter key: `key:` at column 0 (no leading whitespace), optional value.
# Indented keys (nested mappings) and keys inside code fences are deliberately excluded —
# only the document's own top-level frontmatter mapping counts as the vault signal.
_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:")

# The two keys whose joint presence marks a file as a vault note (v4 §2.2 strong signal).
SIGNAL_KEYS = ("created", "tags")
# The opt-in marker that joint-signal files must additionally declare.
REQUIRED_KEY = "type"


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _tracked_md_files(root):
    """Return tracked *.md paths (relative to root). Falls back to a filesystem walk
    if `git ls-files` is unavailable (e.g. root is not a git work tree)."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "*.md"],
            capture_output=True, text=True, check=True,
        )
        files = [ln for ln in out.stdout.splitlines() if ln]
        if files:
            return files
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    walked = []
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            if name.endswith(".md"):
                walked.append(
                    os.path.relpath(os.path.join(dirpath, name), root)
                )
    return sorted(walked)


def extract_frontmatter_keys(text):
    """Return the set of top-level keys in the leading `---`…`---` frontmatter block.

    Returns an empty set if the file has no frontmatter (does not start with `---`)
    or the block is never closed. Only column-0 `key:` lines inside the block count;
    fenced code blocks within the frontmatter are skipped so an example `created:` in a
    YAML sample cannot fabricate the signal.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    keys = set()
    in_fence = False
    fence_marker = None
    for line in lines[1:]:
        stripped = line.strip()
        # Inside the frontmatter, track code fences (``` or ~~~) so example keys are ignored.
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            fence_marker = stripped[:3]
            continue
        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = None
            continue
        if stripped == "---" or stripped == "...":
            break  # end of frontmatter block
        m = _KEY_RE.match(line)
        if m:
            keys.add(m.group(1))
    return keys


def check_type_optin(root):
    """Return (ok, report). A vault-note (created+tags) lacking `type:` is a violation."""
    report = {"root": root, "checked": 0, "vault_notes": [], "violations": [], "unreadable": []}
    for rel in _tracked_md_files(root):
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            report["unreadable"].append(f"{rel} ({exc})")
            continue
        report["checked"] += 1
        keys = extract_frontmatter_keys(text)
        has_signal = all(k in keys for k in SIGNAL_KEYS)
        if not has_signal:
            continue  # not a vault note — ignored (ordinary repo doc)
        report["vault_notes"].append(rel)
        if REQUIRED_KEY not in keys:
            report["violations"].append(rel)
    ok = not report["violations"] and not report["unreadable"]
    return ok, report


def _fm(created=False, tags=False, type_=False, extra="", fenced_fake=False):
    """Build a tiny markdown doc with a chosen frontmatter shape (test helper)."""
    body = ["---"]
    if created:
        body.append("created: 2026-06-13")
    if tags:
        body.append("tags: [demo, work-rules]")
    if type_:
        body.append("type: note")
    if extra:
        body.append(extra)
    if fenced_fake:
        # An example `created:`/`tags:` inside a fence must NOT count as the signal.
        body += ["```yaml", "created: 1999-01-01", "tags: [fake]", "```"]
    body += ["---", "", "# body", "Some text with created: and tags: in prose."]
    return "\n".join(body) + "\n"


def run_self_test():
    failures = []

    # --- extractor / signal-detection cases (in-memory) -----------------------
    # (label, text, expect_signal, expect_violation)
    cases = [
        ("violation: created+tags, no type",
         _fm(created=True, tags=True), True, True),
        ("clean: created+tags+type",
         _fm(created=True, tags=True, type_=True), True, False),
        ("clean: type before tags (order independent)",
         "---\ntype: plan\ncreated: 2026-06-13\ntags: [a]\n---\n# x\n", True, False),
        ("ignored: created only (not a vault note)",
         _fm(created=True), False, False),
        ("ignored: tags only (not a vault note)",
         _fm(tags=True), False, False),
        ("ignored: neither (ordinary doc)",
         "# Just a README\n\nNo frontmatter here.\ncreated: in prose\n", False, False),
        ("ignored: no frontmatter but body mentions created/tags",
         "# Doc\n\ncreated: 2026-06-13\ntags: [x]\n", False, False),
        ("ignored: fenced YAML sample fakes the signal",
         _fm(fenced_fake=True), False, False),
        ("ignored: indented (nested) created/tags are not top-level",
         "---\nmeta:\n  created: 2026-06-13\n  tags: [a]\n---\n# x\n", False, False),
    ]
    for label, text, want_signal, want_violation in cases:
        keys = extract_frontmatter_keys(text)
        got_signal = all(k in keys for k in SIGNAL_KEYS)
        got_violation = got_signal and (REQUIRED_KEY not in keys)
        if got_signal != want_signal:
            failures.append(f"  {label}: signal expected={want_signal} got={got_signal}")
        if got_violation != want_violation:
            failures.append(f"  {label}: violation expected={want_violation} got={got_violation}")

    # --- end-to-end check_type_optin over a temp repo -------------------------
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # 1 violation, 2 clean vault notes, 2 ignored non-vault docs.
        files = {
            "templates/bad.md": _fm(created=True, tags=True),                 # VIOLATION
            "notes/good.md": _fm(created=True, tags=True, type_=True),        # clean vault note
            "notes/good2.md": "---\ntype: decision\ncreated: 2026-06-13\ntags: [x]\n---\n# y\n",
            "README.md": "# Readme\n\nNo vault frontmatter.\n",               # ignored
            "docs/design.md": _fm(created=True),                             # ignored (created only)
        }
        for rel, content in files.items():
            full = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(content)
        ok, report = check_type_optin(tmp)
        if ok:
            failures.append("  e2e: expected ok=False (one violation present)")
        if report["violations"] != ["templates/bad.md"]:
            failures.append(f"  e2e: violations expected ['templates/bad.md'], got {report['violations']}")
        if sorted(report["vault_notes"]) != ["notes/good.md", "notes/good2.md", "templates/bad.md"]:
            failures.append(f"  e2e: vault_notes mismatch, got {sorted(report['vault_notes'])}")
        if report["checked"] != len(files):
            failures.append(f"  e2e: checked expected {len(files)}, got {report['checked']}")

        # Fix the violation -> the same tree must be clean (FP=0 proof).
        with open(os.path.join(tmp, "templates", "bad.md"), "w", encoding="utf-8") as fh:
            fh.write(_fm(created=True, tags=True, type_=True))
        ok2, report2 = check_type_optin(tmp)
        if not ok2:
            failures.append(f"  e2e: expected clean after fix, violations={report2['violations']}")

    if failures:
        print("FAIL: check-type-optin self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-type-optin self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="vault-note `type:` opt-in regression guard (v4 §2.2)"
    )
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    if not os.path.isdir(root):
        print(f"ERROR: root is not a directory: {root}", file=sys.stderr)
        return 2

    ok, report = check_type_optin(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        checked = report["checked"]
        n_notes = len(report["vault_notes"])
        if report["unreadable"]:
            for u in report["unreadable"]:
                print(f"ERROR: unreadable markdown file: {u}", file=sys.stderr)
        if report["violations"]:
            print(f"FAIL: {len(report['violations'])} vault note(s) missing `type:` "
                  f"(invisible to claude-kit — v4 §2.2 opt-in):")
            for v in report["violations"]:
                print(f"  - {v}")
            print("Fix: add a top-level `type:` field (note|decision|session|plan|capture). "
                  "A vault note (created+tags) without `type:` is silently dropped from the "
                  "manifest and audit.")
        else:
            print(f"OK: check-type-optin clean — {checked} markdown file(s) checked, "
                  f"{n_notes} vault note(s), no missing `type:`")

    if report["unreadable"] and not args.json:
        # unreadable input is a non-clean condition; surface as exit 2 only when it is the
        # sole problem, else 1 takes precedence below.
        if not report["violations"]:
            return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
