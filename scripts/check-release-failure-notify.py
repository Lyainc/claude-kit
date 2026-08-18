#!/usr/bin/env python3
"""check-release-failure-notify.py — auto-release failure-surfacing guard (#642).

RULE: `.github/workflows/auto-release.yml` is push-triggered, so a failure there never
shows up as a PR check — every PR stays green while releases silently fail (this happened
for 12 days / 40 runs, caught only because a human noticed main had drifted ahead of the
last tag). The workflow must therefore carry its own failure surfacing: a job gated on
`if: failure()` that opens/comments a GitHub issue via `gh issue`, with `issues: write`
permission to do it. This guard fails if that job, its `failure()` gate, its `issues:
write` permission, or its `gh issue create` call ever disappears from the workflow.

Usage:
    python3 scripts/check-release-failure-notify.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = the failure-notify job is present and correctly wired. 1 = missing/broken.
            2 = usage error / auto-release.yml unreadable.
"""
import argparse
import json
import os
import re
import subprocess
import sys

WORKFLOW_REL = os.path.join(".github", "workflows", "auto-release.yml")

_JOB_HEADER_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$", re.MULTILINE)

# The jobs whose failure must reach the notify job. `failure()` only sees needs-graph
# ancestors, so this list IS the wiring — not a stylistic preference.
REQUIRED_NEEDS = ("decide", "release")


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def iter_job_blocks(yml_text):
    """Yield (job_name, block_text) for each top-level job under `jobs:`."""
    headers = list(_JOB_HEADER_RE.finditer(yml_text))
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(yml_text)
        yield m.group(1), yml_text[start:end]


def find_notify_job(yml_text):
    """Return the name of a job whose `if:` gates on failure(), or None."""
    for name, block in iter_job_blocks(yml_text):
        if re.search(r"^\s*if:.*failure\(\)", block, re.MULTILINE):
            return name, block
    return None, None


def check_workflow(root):
    """Return (ok, report). ok=True means a properly-wired failure-notify job exists."""
    report = {"root": root, "job": None, "violations": []}
    path = os.path.join(root, WORKFLOW_REL)
    if not os.path.isfile(path):
        report["fatal"] = f"{WORKFLOW_REL} not found"
        return False, report
    with open(path, encoding="utf-8") as fh:
        yml_text = fh.read()

    name, block = find_notify_job(yml_text)
    if name is None:
        report["violations"].append(
            "no job gated on `if: failure()` found — a release failure has no surface"
        )
        return False, report
    report["job"] = name

    if not re.search(r"issues:\s*write", block):
        report["violations"].append(f"job `{name}` lacks `issues: write` permission")
    if not re.search(r"\bgh\s+issue\s+create\b", block):
        report["violations"].append(f"job `{name}` never calls `gh issue create`")

    # `failure()` at job level evaluates over the needs-graph ancestors, so a notify job that
    # does not need the release jobs never fires no matter how it is gated — and dropping a
    # name from `needs:` puts the repo straight back in the #642 state with CI still green.
    needs = re.search(r"^\s*needs:\s*(.+)$", block, re.MULTILINE)
    missing = [j for j in REQUIRED_NEEDS if not (needs and re.search(rf"\b{j}\b", needs.group(1)))]
    if missing:
        report["violations"].append(
            f"job `{name}` must `needs:` {', '.join(REQUIRED_NEEDS)} or failure() never fires "
            f"for {', '.join(missing)}"
        )

    return (len(report["violations"]) == 0), report


def run_self_test():
    failures = []

    good = (
        "jobs:\n"
        "  decide:\n"
        "    runs-on: ubuntu-latest\n"
        "  release:\n"
        "    needs: decide\n"
        "  notify-failure:\n"
        "    needs: [decide, release]\n"
        "    if: failure()\n"
        "    permissions:\n"
        "      issues: write\n"
        "    steps:\n"
        "      - run: gh issue create --title x\n"
    )
    name, block = find_notify_job(good)
    if name != "notify-failure":
        failures.append(f"  find_notify_job: expected 'notify-failure', got {name!r}")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, ".github", "workflows"))
        good_path = os.path.join(td, WORKFLOW_REL)
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(good)
        ok, report = check_workflow(td)
        if not ok:
            failures.append(f"  well-formed workflow: expected ok=True, got violations={report['violations']}")

        # missing failure() gate entirely
        no_gate = "jobs:\n  decide:\n    runs-on: ubuntu-latest\n"
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(no_gate)
        ok, report = check_workflow(td)
        if ok or "if: failure()" not in report["violations"][0]:
            failures.append(f"  no-gate workflow: expected the missing-gate violation, got {report}")

        # gate present but the needs-graph no longer reaches the release job: failure()
        # can never be true for it, so the job silently never runs (#642 all over again).
        narrow_needs = good.replace("    needs: [decide, release]\n", "    needs: decide\n")
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(narrow_needs)
        ok, report = check_workflow(td)
        if ok or not any("needs:" in v for v in report["violations"]):
            failures.append(f"  narrowed-needs workflow: expected needs violation, got {report}")

        no_needs = good.replace("    needs: [decide, release]\n", "")
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(no_needs)
        ok, report = check_workflow(td)
        if ok or not any("needs:" in v for v in report["violations"]):
            failures.append(f"  no-needs workflow: expected needs violation, got {report}")

        # KNOWN LIMITATION (#658): the needs: regex (`^\s*needs:\s*(.+)$`, MULTILINE) only
        # anchors the FIRST line after `needs:` — `\s*` crosses the newline, so on block-list
        # style it captures "- decide" (the first list item) as group(1), not nothing. Every
        # `REQUIRED_NEEDS` name is then checked with `\b{name}\b` against that one captured
        # line: "decide" matches (it landed on the captured line) but "release" does not (it
        # is on a later, uncaptured line), so this is a PARTIAL false positive — only "release"
        # is wrongly reported missing, not both, and only because "decide" happens to be first
        # in the list. This case pins that exact asymmetric behavior as a known gap, not a
        # regression — do not "fix" the assertion to expect both flagged, that would document
        # the wrong bug.
        block_list_needs = good.replace(
            "    needs: [decide, release]\n",
            "    needs:\n      - decide\n      - release\n",
        )
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(block_list_needs)
        ok, report = check_workflow(td)
        violation_text = " ".join(report["violations"])
        if (
            ok
            or "release" not in violation_text
            or "never fires for release" not in violation_text
            or "never fires for decide" in violation_text
        ):
            failures.append(
                f"  block-list-needs workflow (known limitation — only 'release' should be "
                f"flagged missing, not 'decide'): got {report}"
            )

        # gate present but missing permission
        no_perm = good.replace("      issues: write\n", "")
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(no_perm)
        ok, report = check_workflow(td)
        if ok or not any("issues: write" in v for v in report["violations"]):
            failures.append(f"  no-permission workflow: expected permission violation, got {report}")

        # gate + permission present but no gh issue create call
        no_gh = good.replace("      - run: gh issue create --title x\n", "      - run: echo hi\n")
        with open(good_path, "w", encoding="utf-8") as fh:
            fh.write(no_gh)
        ok, report = check_workflow(td)
        if ok or not any("gh issue create" in v for v in report["violations"]):
            failures.append(f"  no-gh-call workflow: expected gh-issue-create violation, got {report}")

        # missing file entirely
        os.remove(good_path)
        ok, report = check_workflow(td)
        if ok or "fatal" not in report:
            failures.append(f"  missing file: expected fatal, got {report}")

    if failures:
        print("FAIL: check-release-failure-notify self-test")
        print("\n".join(failures))
        return 1
    print("OK: all check-release-failure-notify self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="auto-release.yml failure-notify guard")
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run in-memory + fixture cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    ok, report = check_workflow(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report.get("fatal"):
        print(f"ERROR: {report['fatal']}")
    elif ok:
        print(f"OK: {WORKFLOW_REL} has a failure-notify job (`{report['job']}`) "
              "gated on failure() with issues:write + gh issue create.")
    else:
        print(f"FAIL: {WORKFLOW_REL} failure-notify surface is broken:")
        for v in report["violations"]:
            print(f"  - {v}")
        print("Fix: restore a job gated on `if: failure()` that `needs: "
              f"[{', '.join(REQUIRED_NEEDS)}]`, has `issues: write` permission, and calls "
              "`gh issue create` (see #642).")

    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
