#!/usr/bin/env python3
"""check-banned-words.py — repo-owned banned-term guard (work-rules minimal core, slice S3).

RULE: a small, repo-owned list of banned terms (rules/banned-terms.txt, one
"term  ::  reason" entry per line) must NEVER reappear in the repo's code/config text. The
script READS that data file and flags any occurrence in scanned files. This is
config-injection policy, NOT hardcoded taste: the term list is data the repo owns and curates,
and each term is justified by OBJECTIVE DAMAGE in its `reason`.

OBJECTIVE-DAMAGE rationale (why a violation is damage, not taste): the curated terms are
identifiers/markers of *removed* subsystems (e.g. the release-please auto-versioning that was
replaced by the manual lockstep release). If such an identifier silently reappears in a workflow
or config, the dead subsystem comes back to life and races the live one — for release-please that
means auto-versioning fighting the manual lockstep release and producing divergent / double
version bumps across the 4 plugin.json + marketplace.json manifests (the exact drift
check-version-sync.py exists to block). That breakage is silent: nothing else flags it. A
banned-term gate makes the resurrection a loud CI failure instead of a latent foot-gun. No
subjective-style constant (line length, quotes, indent) is encoded here — those belong to
external linters; this gate enforces claude-kit-specific policy only.

SCOPE (kept narrow so FP=0 on a clean repo):
  - File types: only code/config text where a banned identifier would be a LIVE reference —
    .py .sh .json .yaml .yml. Markdown / prose is NOT scanned, so historical mentions
    ("the <X> alias was removed") in CLAUDE.md and docs/ never false-positive.
  - File set: git-tracked files PLUS untracked-but-not-gitignored files (the "committed repo",
    robust to staged-yet-uncommitted new files). Gitignored and local-only machine config (e.g.
    an untracked .claude/settings.local.json holding stale permission strings) are excluded.
  - The banned-terms data file itself is never scanned (its lines legitimately contain the
    terms), so terms are never self-flagged.

Usage:
    python3 scripts/check-banned-words.py [--root DIR] [--terms FILE] [--json] [--self-test]

    --root DIR    Repo root to scan (default: git toplevel, else CWD).
    --terms FILE  Banned-terms data file (default: <root>/rules/banned-terms.txt).
    --json        Emit a machine-readable JSON report.
    --self-test   Run in-memory fixtures (>=1 violation + >=1 clean + self-flag exclusion).

Exit codes: 0 = clean (no banned terms), 1 = banned term(s) found, 2 = usage / unreadable input.
"""
import argparse
import json
import os
import subprocess
import sys

# Only scan code/config types where a banned identifier would be a live reference.
SCAN_EXT = (".py", ".sh", ".json", ".yaml", ".yml")
# Default location of the repo-owned banned-terms data file (relative to root).
DEFAULT_TERMS_REL = os.path.join("rules", "banned-terms.txt")


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def parse_terms(text):
    """Parse banned-terms data text into a list of (term, reason).

    Format: "term  ::  reason". '#' comment lines and blank lines are skipped. A line with
    no '::' uses the whole (stripped) line as the term and an empty reason. Empty terms are
    ignored. Returns a list preserving file order.
    """
    terms = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "::" in line:
            term, reason = line.split("::", 1)
            term, reason = term.strip(), reason.strip()
        else:
            term, reason = line, ""
        if term:
            terms.append((term, reason))
    return terms


def _list_scan_files(root):
    """Return repo-relative scanned files: git-tracked + untracked-not-ignored, code/config exts.

    Falls back to an os.walk (excluding .git) if `root` is not a git repo.
    """
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
                files.append(rel)
    return sorted(
        {f for f in files if os.path.splitext(f)[1] in SCAN_EXT}
    )


def check_banned_words(root, terms_path=None):
    """Scan `root` for any banned term. Returns (ok, report).

    ok=True means no scanned file contains any banned term. The banned-terms data file itself is
    excluded from the scan so its own lines are never self-flagged.
    """
    report = {
        "root": root, "terms_file": terms_path, "term_count": 0,
        "files_scanned": 0, "violations": [],
    }
    if terms_path is None:
        terms_path = os.path.join(root, DEFAULT_TERMS_REL)
        report["terms_file"] = terms_path

    if not os.path.isfile(terms_path):
        report["violations"].append(f"banned-terms file not found: {terms_path}")
        report["fatal"] = True
        return False, report
    try:
        with open(terms_path, encoding="utf-8") as fh:
            terms = parse_terms(fh.read())
    except OSError as exc:
        report["violations"].append(f"banned-terms file unreadable: {terms_path} ({exc})")
        report["fatal"] = True
        return False, report

    report["term_count"] = len(terms)
    if not terms:
        # An empty policy list is vacuously clean — nothing to enforce, no damage.
        return True, report

    terms_abs = os.path.abspath(terms_path)
    files = _list_scan_files(root)
    scanned = 0
    for rel in files:
        abspath = os.path.join(root, rel)
        if os.path.abspath(abspath) == terms_abs:
            continue  # never scan the data file itself
        if not os.path.isfile(abspath):
            continue
        try:
            with open(abspath, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        scanned += 1
        for lineno, content in enumerate(lines, start=1):
            for term, reason in terms:
                if term in content:
                    report["violations"].append({
                        "file": rel, "line": lineno, "term": term,
                        "reason": reason, "text": content.rstrip("\n"),
                    })

    report["files_scanned"] = scanned
    return (len(report["violations"]) == 0), report


def run_self_test():
    """In-memory fixtures: a VIOLATION case, a CLEAN case, and data-file self-exclusion."""
    import tempfile
    failures = []

    # --- parse_terms unit checks ---
    parsed = parse_terms(
        "# comment\n\nfoo-bar  ::  reason text\nbare-term\n  ::  reason-without-term\n"
    )
    if parsed != [("foo-bar", "reason text"), ("bare-term", "")]:
        failures.append(f"  parse_terms: unexpected result {parsed}")

    # --- VIOLATION fixture: a scanned-type file containing a banned term must be flagged. ---
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "rules"))
        with open(os.path.join(tmp, DEFAULT_TERMS_REL), "w", encoding="utf-8") as fh:
            fh.write("# terms\nforbidden-token  ::  must never reappear\n")
        # A .py file (scanned) that references the banned token -> violation.
        with open(os.path.join(tmp, "live.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 'forbidden-token'\n")
        # A .md file (NOT scanned) mentioning the token as prose -> must NOT flag.
        with open(os.path.join(tmp, "history.md"), "w", encoding="utf-8") as fh:
            fh.write("The forbidden-token alias was removed.\n")
        ok, report = check_banned_words(tmp)
        if ok:
            failures.append("  violation fixture: expected ok=False, got ok=True")
        v = report["violations"]
        if not (len(v) == 1 and isinstance(v[0], dict)
                and v[0]["file"] == "live.py" and v[0]["term"] == "forbidden-token"
                and v[0]["line"] == 1):
            failures.append(f"  violation fixture: expected single live.py hit, got {v}")
        # The .md prose mention must NOT be flagged (scope excludes markdown).
        if any(isinstance(item, dict) and item.get("file") == "history.md" for item in v):
            failures.append("  violation fixture: markdown prose was wrongly scanned")

    # --- CLEAN fixture: no scanned file contains a banned term -> pass, FP=0. ---
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "rules"))
        with open(os.path.join(tmp, DEFAULT_TERMS_REL), "w", encoding="utf-8") as fh:
            fh.write("# terms\nforbidden-token  ::  must never reappear\n")
        with open(os.path.join(tmp, "clean.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 'totally fine'\n")
        with open(os.path.join(tmp, "conf.json"), "w", encoding="utf-8") as fh:
            fh.write('{"ok": true}\n')
        ok, report = check_banned_words(tmp)
        if not ok:
            failures.append(f"  clean fixture: expected ok=True, got violations {report['violations']}")
        if report["violations"]:
            failures.append(f"  clean fixture: expected FP=0, got {report['violations']}")

    # --- SELF-EXCLUSION: the banned-terms data file's own lines are never self-flagged. ---
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "rules"))
        # The data file legitimately contains the term in its own line — must be skipped.
        with open(os.path.join(tmp, DEFAULT_TERMS_REL), "w", encoding="utf-8") as fh:
            fh.write("# terms\nself-referential-term  ::  appears here legitimately\n")
        with open(os.path.join(tmp, "harmless.sh"), "w", encoding="utf-8") as fh:
            fh.write("echo hi\n")
        ok, report = check_banned_words(tmp)
        if not ok:
            failures.append(
                f"  self-exclusion: data file flagged itself, violations={report['violations']}"
            )

    # --- missing terms file -> fatal (exit 2 path). ---
    with tempfile.TemporaryDirectory() as tmp:
        ok, report = check_banned_words(tmp)
        if ok or not report.get("fatal"):
            failures.append("  missing-terms fixture: expected fatal=True, ok=False")

    if failures:
        print("FAIL: check-banned-words self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-banned-words self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Repo-owned banned-term guard (reads rules/banned-terms.txt)"
    )
    parser.add_argument("--root", default=None, help="repo root to scan")
    parser.add_argument("--terms", default=None, help="banned-terms data file path")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory fixtures")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    terms_path = args.terms or os.path.join(root, DEFAULT_TERMS_REL)
    ok, report = check_banned_words(root, terms_path)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("fatal"):
        for v in report["violations"]:
            print(f"ERROR: {v}")
    elif ok:
        print(
            f"OK: banned-words clean — {report['files_scanned']} file(s) checked, "
            f"no violations ({report['term_count']} banned term(s) enforced)"
        )
    else:
        print(f"BANNED-WORD: {len(report['violations'])} occurrence(s) of banned term(s) found:")
        for v in report["violations"]:
            print(f"  - {v['file']}:{v['line']}  term={v['term']!r}")
            if v["reason"]:
                print(f"      reason: {v['reason']}")
        print(
            "Fix: remove the banned identifier (it marks a removed subsystem — its reappearance "
            "is silent breakage). If a term is now legitimate, delete its line from "
            "rules/banned-terms.txt with justification."
        )

    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
