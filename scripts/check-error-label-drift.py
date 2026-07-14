#!/usr/bin/env python3
"""check-error-label-drift.py — E1-EN audit-error-type label drift guard (#385).

RULE: `obsidian-vault-manager/reference/vault-audit-rules.md` is the single source of
truth for the audit skill's error-type taxonomy (`## E<N> — ...` headers). Every other
doc/manifest that states the full range as `E1-E<N>` (en dash or hyphen) must use the
SAME max N as that source file. #250 and #380/PR#383 both landed with the range stale in
several files after a new E-type was added — and PR#383's own fix pass, which named
itself a "recurring bug class", still missed 5 more occurrences. Manual review provably
cannot keep this in sync; this guard makes the check mechanical.

SCOPING for FP=0 (the hard part): not every `E1-E<N>` substring is a "this is the full
taxonomy" claim. Two shapes are legitimate and must NOT be flagged:
  1. `docs/plans/**` narrates past-tense history ("E1-E9 -> E1-E5") — excluded by path.
  2. A PARTIAL range mentioned alongside the max type elsewhere in the same paragraph —
     e.g. "(12 types: E1-E11 v4, E12 v5)" or a `--dod` scope note ("E1-E11 + E12a") or a
     priority-mapping blockquote where "E1-E4 = P0" sits next to "E10-E12 = P1" two lines
     down. None of these are stale: the surrounding text already accounts for the current
     max, it's just split across a versioned/categorized breakdown rather than stated as
     one range. So the unit of judgment is a PARAGRAPH (a run of non-blank lines), not a
     single line or the whole file: an `E1-E<N>` match with N != max is a violation only
     if its own paragraph never mentions `E<max>` (optionally suffixed, e.g. `E12a`)
     anywhere else. This single rule (verified against every real occurrence in this repo,
     not just the two mines #385 names) replaces any per-file/per-line special-casing.

Usage:
    python3 scripts/check-error-label-drift.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = clean (every E1-EN label matches the source-of-truth max, or is
            paragraph-exempted). 1 = stale label(s) found. 2 = usage error / rules file
            unreadable / no `## E<N>` headers found in it.
"""
import argparse
import json
import os
import re
import subprocess
import sys

RULES_REL = os.path.join("obsidian-vault-manager", "reference", "vault-audit-rules.md")
SCAN_EXT = (".md", ".py", ".sh", ".json")
# docs/plans/** and docs/discussions/** are dated historical records (plans-in-progress,
# decision-session transcripts) — an "E1-E9" there is a fact about what was true at
# authoring time, never a live claim about the current taxonomy.
EXCLUDE_PREFIXES = ("docs/plans/", "docs/discussions/")
# This guard's own source discusses the E1-EN pattern in prose (see SCOPING above) —
# exclude it from self-scanning, same rationale as check-banned-words.py's self-exclusion.
_SELF_REL = "scripts/check-error-label-drift.py"

_HEADER_RE = re.compile(r"^##\s+E(\d+)\b", re.MULTILINE)
_RANGE_RE = re.compile(r"E1[–-]E(\d+)")


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _list_scan_files(root):
    """Return repo-relative scanned files: git-tracked + untracked-not-ignored, matching
    SCAN_EXT, minus EXCLUDE_PREFIXES. Falls back to os.walk if `root` is not a git repo."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        ).stdout
        files = [f for f in out.splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                files.append(rel.replace(os.sep, "/"))
    return sorted(
        f for f in set(files)
        if os.path.splitext(f)[1] in SCAN_EXT
        and not f.startswith(EXCLUDE_PREFIXES)
        and f != _SELF_REL
    )


def extract_max_e(rules_text):
    """Return the highest N from top-level `## E<N> —` headers, or None if none found."""
    nums = [int(m.group(1)) for m in _HEADER_RE.finditer(rules_text)]
    return max(nums) if nums else None


def iter_paragraphs(text):
    """Yield (start_line, paragraph_text) for each run of non-blank lines (1-indexed)."""
    lines = text.splitlines()
    block, start = [], None
    for i, line in enumerate(lines, start=1):
        if line.strip() == "":
            if block:
                yield start, "\n".join(block)
                block, start = [], None
        else:
            if start is None:
                start = i
            block.append(line)
    if block:
        yield start, "\n".join(block)


def find_violations_in_text(text, max_e):
    """Return a list of {line, label, expected} for stale E1-EN labels in `text`."""
    violations = []
    exempt_re = re.compile(r"E" + str(max_e) + r"[a-z]?\b")
    for start_line, para in iter_paragraphs(text):
        for m in _RANGE_RE.finditer(para):
            n = int(m.group(1))
            if n == max_e:
                continue
            if exempt_re.search(para):
                continue  # paragraph already accounts for the current max elsewhere
            line_no = start_line + para.count("\n", 0, m.start())
            violations.append({"line": line_no, "label": m.group(0), "expected": f"E1-E{max_e}"})
    return violations


def check_labels(root):
    """Return (ok, report). ok=True means no stale E1-EN label was found."""
    report = {"root": root, "files_scanned": 0, "max_e": None, "violations": []}
    rules_path = os.path.join(root, RULES_REL)
    if not os.path.isfile(rules_path):
        report["fatal"] = f"rules file not found: {RULES_REL}"
        return False, report
    with open(rules_path, encoding="utf-8") as fh:
        rules_text = fh.read()

    max_e = extract_max_e(rules_text)
    if max_e is None:
        report["fatal"] = f"no `## E<N>` headers found in {RULES_REL}"
        return False, report
    report["max_e"] = max_e

    files = _list_scan_files(root)
    report["files_scanned"] = len(files)
    for rel in files:
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        for v in find_violations_in_text(text, max_e):
            report["violations"].append({"file": rel, **v})

    return (len(report["violations"]) == 0), report


def run_self_test():
    failures = []

    rules_text = (
        "# vault-audit\n\n"
        "## E1 — a\n## E2 — b\n## E9 — c\n## E10 — d\n## E11 — e\n## E12 — f\n"
    )
    if extract_max_e(rules_text) != 12:
        failures.append(f"  extract_max_e: expected 12, got {extract_max_e(rules_text)}")
    if extract_max_e(rules_text + "\n## E13 — g\n") != 13:
        failures.append("  extract_max_e: did not pick up a newly-added E13 header")
    if extract_max_e("no headers here") is not None:
        failures.append("  extract_max_e: expected None for a rules file with no headers")

    max_e = 12
    cases = [
        ("clean-total", "audit detects E1–E12 errors.", []),
        ("stale-total", "audit detects E1–E11 errors.",
         [{"label": "E1–E11", "expected": "E1-E12"}]),
        ("versioned-breakdown-same-line",
         "Error types (12 types: E1–E11 v4, E12 v5).", []),
        ("dod-scope-note",
         "that gate stays scoped to E1–E11 + E12a exactly as it was before.", []),
        ("multiline-priority-mapping",
         "P0 = integrity: All four E1–E4 types are in Step 1.\n"
         "P1 = structure: E6 and E7 surface inputs; E10 and E11 surface drift; E12 surfaces staleness.",
         []),
        ("hyphen-variant-stale", "v4, E1-E11 fixtures only, nothing past that here.",
         [{"label": "E1-E11", "expected": "E1-E12"}]),
    ]
    for name, text, expected in cases:
        got = [{"label": v["label"], "expected": v["expected"]} for v in find_violations_in_text(text, max_e)]
        if got != expected:
            failures.append(f"  case {name!r}: expected {expected}, got {got}")

    # Filesystem-level check: docs/plans/** path exclusion + real violation surfacing.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "obsidian-vault-manager", "reference"))
        with open(os.path.join(td, RULES_REL), "w", encoding="utf-8") as fh:
            fh.write(rules_text)
        os.makedirs(os.path.join(td, "docs", "plans"))
        with open(os.path.join(td, "docs", "plans", "old.md"), "w", encoding="utf-8") as fh:
            fh.write("Historical note: E1-E9 -> E1-E5 in this migration.\n")
        with open(os.path.join(td, "clean.md"), "w", encoding="utf-8") as fh:
            fh.write("The audit skill covers E1–E12.\n")
        with open(os.path.join(td, "stale.md"), "w", encoding="utf-8") as fh:
            fh.write("The audit skill covers E1–E11.\n")

        ok, report = check_labels(td)
        if ok:
            failures.append("  filesystem: expected ok=False (stale.md present), got True")
        if report.get("max_e") != 12:
            failures.append(f"  filesystem: expected max_e=12, got {report.get('max_e')}")
        viol_files = sorted({v["file"] for v in report["violations"]})
        if viol_files != ["stale.md"]:
            failures.append(f"  filesystem: expected only stale.md flagged, got {viol_files}")

        # Now fix stale.md and remove it; clean tree must report ok=True (fp_on_clean == 0).
        os.remove(os.path.join(td, "stale.md"))
        ok2, report2 = check_labels(td)
        if not ok2 or report2["violations"]:
            failures.append(f"  filesystem: expected clean tree ok=True, got {report2['violations']}")

    if failures:
        print("FAIL: check-error-label-drift self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-error-label-drift self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="E1-EN audit-error-type label drift guard")
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory + fixture cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    ok, report = check_labels(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("fatal"):
        print(f"ERROR: {report['fatal']}")
    elif ok:
        print(f"OK: error-label-drift clean — {report['files_scanned']} file(s) checked, "
              f"every E1-EN label matches source-of-truth max E{report['max_e']} "
              f"({RULES_REL})")
    else:
        print(f"FAIL: {len(report['violations'])} stale E1-EN label(s) found "
              f"(source-of-truth max: E{report['max_e']}, from {RULES_REL}):")
        for v in report["violations"]:
            print(f"  - {v['file']}:{v['line']}: `{v['label']}` should be `{v['expected']}`")
        print("Fix: update the stale label, or (if it's an intentionally partial range) "
              "mention the current max E-type elsewhere in the same paragraph.")

    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
