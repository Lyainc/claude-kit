#!/usr/bin/env python3
"""check-ci-coverage.py — CI test-coverage drift guard (#134).

docs/VALIDATION.md's `## Validation` section is the canonical list of regression tests
for this repo. `.github/workflows/validate.yml` is what CI actually runs on push/PR. When
a test gets added to docs/VALIDATION.md but never wired into validate.yml, it silently
stops being enforced. This guard diffs the two lists and reports tests that are
registered (in docs/VALIDATION.md) but NOT run in CI.

Per G13 trade-off, this is a WARN guard (not a block): it exits 0 by default even when
gaps exist, because coverage is being closed incrementally. Use --strict to make gaps a
hard failure once coverage has stabilized.

Usage:
    python3 scripts/check-ci-coverage.py [--root DIR] [--strict] [--json] [--self-test]

Exit codes (default / warn mode): always 0.
Exit codes (--strict): 0 = full coverage, 1 = gaps found, 2 = inputs unreadable.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

# A "test command" is one of these shapes. Each maps to a stable id so the same logical
# test in docs/VALIDATION.md and validate.yml compares equal regardless of redirects/flags/env prefixes.
_PATTERNS = [
    (re.compile(r"python3\s+-m\s+json\.tool\s+(\S+)"), "json.tool:{}"),
    (re.compile(r"python3\s+(\S+\.py)"), "py:{}"),
    (re.compile(r"bash\s+-n\s+(\S+)"), "bash-n:{}"),
    (re.compile(r"bash\s+(\S+\.sh)"), "sh:{}"),
]


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _join_continuations(text):
    """Join trailing-backslash line continuations into single logical lines."""
    out = []
    buf = ""
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
        else:
            out.append(buf + line)
            buf = ""
    if buf:
        out.append(buf)
    return out


def extract_test_ids(text):
    """Extract the set of test-command ids from a block of shell/yaml text."""
    ids = set()
    for raw in _join_continuations(text):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # drop a trailing inline comment (` # ...`); safe for these command shapes
        comment = re.search(r"\s#\s", line)
        if comment:
            line = line[: comment.start()]
        for pattern, template in _PATTERNS:
            for m in pattern.finditer(line):
                ids.add(template.format(m.group(1)))
    return ids


def extract_validation_section(validation_md_text):
    """Return the text of the `## Validation` section (fenced blocks only)."""
    lines = validation_md_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Validation":
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    section = lines[start:end]
    # Prefer fenced code blocks inside the section; fall back to the whole section.
    fenced, in_fence = [], False
    for line in section:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            fenced.append(line)
    return "\n".join(fenced) if fenced else "\n".join(section)


def _referenced_paths(ids):
    """Strip the id prefix (`py:`, `sh:`, ...) down to a bare path, skipping glob
    patterns (`bash -n hooks/*.sh`) since those have no single file to check."""
    paths = []
    for i in ids:
        _, _, path = i.partition(":")
        if any(c in path for c in "*?["):
            continue
        paths.append(path)
    return paths


def check_coverage(root):
    """Return (ok, report). ok=True means every docs/VALIDATION.md test is also run in
    CI, AND every registered path still exists on disk (#618: a test deleted without
    also deleting its docs/VALIDATION.md line is silent drift — the doc claims a
    regression guard that no longer runs)."""
    report = {"root": root, "registered": [], "ci": [], "missing_in_ci": [], "ci_only": [],
              "stale_paths": []}
    validation_path = os.path.join(root, "docs", "VALIDATION.md")
    yml_path = os.path.join(root, ".github", "workflows", "validate.yml")

    for label, path in (("docs/VALIDATION.md", validation_path), ("validate.yml", yml_path)):
        if not os.path.isfile(path):
            report["violations"] = [f"{label} not found: {path}"]
            report["fatal"] = True
            return False, report

    with open(validation_path, encoding="utf-8") as fh:
        validation_text = fh.read()
    with open(yml_path, encoding="utf-8") as fh:
        yml_text = fh.read()

    section = extract_validation_section(validation_text)
    if section is None:
        report["violations"] = ["docs/VALIDATION.md has no '## Validation' section"]
        report["fatal"] = True
        return False, report

    registered = extract_test_ids(section)
    ci = extract_test_ids(yml_text)
    missing = registered - ci
    ci_only = ci - registered
    stale = sorted(p for p in _referenced_paths(registered) if not os.path.isfile(os.path.join(root, p)))

    report["registered"] = sorted(registered)
    report["ci"] = sorted(ci)
    report["missing_in_ci"] = sorted(missing)
    report["ci_only"] = sorted(ci_only)
    report["stale_paths"] = stale
    return (len(missing) == 0 and len(stale) == 0), report


def run_self_test():
    claude = (
        "# x\n## Validation\n\n```bash\n"
        "python3 -m json.tool a.json > /dev/null\n"
        "python3 dir/test/foo.py\n"
        "OVM=/tmp bash dir/test/bar.sh --with-x\n"
        "bash -n hooks/*.sh\n"
        "python3 dir/test/only-in-claude.py\n"
        "# python3 dir/test/commented-out.py\n"
        "```\n\n## Next\npython3 dir/test/outside-section.py\n"
    )
    yml = (
        "name: v\njobs:\n  validate:\n    steps:\n      - run: |\n"
        "          python3 -m json.tool a.json > /dev/null\n"
        "          python3 dir/test/foo.py\n"
        "          bash dir/test/bar.sh\n"
        "          bash -n hooks/*.sh\n"
    )
    reg = extract_test_ids(extract_validation_section(claude))
    ci = extract_test_ids(yml)
    missing = reg - ci

    failures = []
    expected_reg = {
        "json.tool:a.json", "py:dir/test/foo.py", "sh:dir/test/bar.sh",
        "bash-n:hooks/*.sh", "py:dir/test/only-in-claude.py",
    }
    if reg != expected_reg:
        failures.append(f"  registered: expected {sorted(expected_reg)}, got {sorted(reg)}")
    if missing != {"py:dir/test/only-in-claude.py"}:
        failures.append(f"  missing_in_ci: expected only-in-claude, got {sorted(missing)}")
    if "py:dir/test/commented-out.py" in reg:
        failures.append("  commented-out line was not skipped")
    if "py:dir/test/outside-section.py" in reg:
        failures.append("  line outside ## Validation section leaked in")

    # #618: a registered path that no longer exists on disk is stale drift, and a glob
    # pattern (no single file to check) must not be flagged.
    if _referenced_paths({"py:dir/test/foo.py", "bash-n:hooks/*.sh"}) != ["dir/test/foo.py"]:
        failures.append("  _referenced_paths: glob pattern should be skipped")
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "docs"))
        os.makedirs(os.path.join(tmp, ".github", "workflows"))
        os.makedirs(os.path.join(tmp, "dir", "test"))
        with open(os.path.join(tmp, "dir", "test", "real.py"), "w") as fh:
            fh.write("")
        with open(os.path.join(tmp, "docs", "VALIDATION.md"), "w") as fh:
            fh.write("# x\n## Validation\n\n```bash\npython3 dir/test/real.py\n"
                      "python3 dir/test/deleted.py\n```\n")
        with open(os.path.join(tmp, ".github", "workflows", "validate.yml"), "w") as fh:
            fh.write("name: v\njobs:\n  validate:\n    steps:\n      - run: |\n"
                      "          python3 dir/test/real.py\n"
                      "          python3 dir/test/deleted.py\n")
        ok, report = check_coverage(tmp)
        if ok:
            failures.append("  check_coverage: a stale (deleted) path should fail ok=False")
        if report["stale_paths"] != ["dir/test/deleted.py"]:
            failures.append(f"  check_coverage: expected stale_paths=['dir/test/deleted.py'], "
                             f"got {report['stale_paths']}")

    if failures:
        print("FAIL: check-ci-coverage self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-ci-coverage self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="docs/VALIDATION.md ↔ validate.yml test-coverage guard")
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on coverage gaps")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory parser cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    ok, report = check_coverage(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("fatal"):
        for v in report.get("violations", []):
            print(f"ERROR: {v}")
    else:
        reg, ci = len(report["registered"]), len(report["ci"])
        covered = reg - len(report["missing_in_ci"])
        print(f"CI coverage: {covered}/{reg} docs/VALIDATION.md-registered tests run in validate.yml.")
        if report["missing_in_ci"]:
            tag = "GAP" if args.strict else "WARN"
            print(f"{tag}: {len(report['missing_in_ci'])} registered test(s) NOT run in CI:")
            for t in report["missing_in_ci"]:
                print(f"  - {t}")
            print("Fix: add these to .github/workflows/validate.yml, or remove from "
                  "docs/VALIDATION.md's Validation section if intentionally local-only.")
        else:
            print("OK: every registered test is wired into CI.")
        if report["stale_paths"]:
            tag = "GAP" if args.strict else "WARN"
            print(f"{tag}: {len(report['stale_paths'])} docs/VALIDATION.md-registered path(s) "
                  "do not exist on disk (stale test reference):")
            for p in report["stale_paths"]:
                print(f"  - {p}")
            print("Fix: remove the stale line from docs/VALIDATION.md's Validation section "
                  "(and validate.yml if still wired), or restore the file if this was an "
                  "accidental deletion.")
        if report["ci_only"]:
            print(f"Note: {len(report['ci_only'])} CI step(s) not listed in docs/VALIDATION.md "
                  "(informational): " + ", ".join(report["ci_only"]))

    if report.get("fatal"):
        return 2
    if args.strict and not ok:
        return 1
    return 0  # warn mode: gaps do not fail the build


if __name__ == "__main__":
    sys.exit(main())
