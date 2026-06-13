#!/usr/bin/env python3
"""run-linters.py — thin delegation to external linters/formatters (#216 c4).

claude-kit does NOT reimplement linting. This script only DELEGATES: "if a linter is
present (tool on PATH + its repo config), run it and enforce that it passes; otherwise
skip gracefully." All style/taste lives in the linter's repo-owned config (ruff.toml,
.prettierrc, ...), per #216 c6/ac4 — never hardcoded here.

Contract (per linter):
  - tool absent (not on PATH)                  -> SKIP, contributes exit 0 (graceful)
  - tool present but no repo config            -> SKIP, contributes exit 0 (nothing to enforce)
  - tool present + config + lint passes        -> PASS, exit 0
  - tool present + config + lint fails          -> FAIL, exit 1 (enforce pass)

This keeps the MECHANISM committed and active the moment a linter is added to the repo /
CI image, with zero per-repo reimplementation. On a repo/CI with no linters installed
(the current state), every linter SKIPs and this exits 0 — the gate is latent, not absent.

Usage:
    python3 scripts/run-linters.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = all present linters passed (or all skipped), 1 = a present linter failed,
            2 = usage error.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# Each linter is (name, tool-on-PATH probe, config-present probe, run callable).
# The run callable returns an int exit code. Kept as data so --self-test can inject fakes.
def _ruff_config(root):
    return any(os.path.isfile(os.path.join(root, f)) for f in ("ruff.toml", ".ruff.toml")) or (
        os.path.isfile(os.path.join(root, "pyproject.toml"))
        and "[tool.ruff" in _read(os.path.join(root, "pyproject.toml"))
    )


def _prettier_config(root):
    return any(
        os.path.isfile(os.path.join(root, f))
        for f in (".prettierrc", ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.yml", "prettier.config.js")
    )


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def default_linters():
    """Real linter table. Each entry: name, present(), configured(root), run(root)->int."""
    return [
        {
            "name": "ruff",
            "present": lambda: shutil.which("ruff") is not None,
            "configured": _ruff_config,
            "run": lambda root: subprocess.run(["ruff", "check", "."], cwd=root).returncode,
        },
        {
            "name": "prettier",
            "present": lambda: shutil.which("prettier") is not None,
            "configured": _prettier_config,
            "run": lambda root: subprocess.run(["prettier", "--check", "."], cwd=root).returncode,
        },
        {
            "name": "shellcheck",
            "present": lambda: shutil.which("shellcheck") is not None,
            # shellcheck has no repo config gate here; treat presence as opt-in only if .sh files exist.
            "configured": lambda root: _has_shell(root),
            "run": lambda root: _run_shellcheck(root),
        },
    ]


def _has_shell(root):
    try:
        out = subprocess.run(
            ["git", "ls-files", "*.sh"], cwd=root, capture_output=True, text=True, check=True
        )
        return bool(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _run_shellcheck(root):
    try:
        files = subprocess.run(
            ["git", "ls-files", "*.sh"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0
    if not files:
        return 0
    return subprocess.run(["shellcheck", *files], cwd=root).returncode


def run_linters(root, linters):
    """Run each present+configured linter; enforce pass. Returns (ok, report)."""
    report = {"root": root, "ran": [], "skipped": [], "failed": []}
    ok = True
    for lt in linters:
        name = lt["name"]
        if not lt["present"]():
            report["skipped"].append({"name": name, "reason": "tool absent"})
            continue
        if not lt["configured"](root):
            report["skipped"].append({"name": name, "reason": "no repo config / nothing to lint"})
            continue
        code = lt["run"](root)
        if code == 0:
            report["ran"].append({"name": name, "exit": 0})
        else:
            report["ran"].append({"name": name, "exit": code})
            report["failed"].append(name)
            ok = False
    return ok, report


def run_self_test():
    """Validate the delegation logic with injected fake linters (no real tools needed)."""
    def fake(name, present, configured, exit_code):
        return {
            "name": name,
            "present": lambda: present,
            "configured": lambda root: configured,
            "run": lambda root: exit_code,
        }

    failures = []

    # 1) tool absent -> skipped, ok=True
    ok, rep = run_linters("/tmp", [fake("absent", False, True, 1)])
    if not ok or rep["skipped"][0]["reason"] != "tool absent":
        failures.append("  absent tool should skip gracefully (ok=True)")

    # 2) present but unconfigured -> skipped, ok=True
    ok, rep = run_linters("/tmp", [fake("noconf", True, False, 1)])
    if not ok or not rep["skipped"]:
        failures.append("  present-but-unconfigured should skip gracefully")

    # 3) present + configured + passes -> ran, ok=True
    ok, rep = run_linters("/tmp", [fake("pass", True, True, 0)])
    if not ok or rep["ran"][0]["exit"] != 0:
        failures.append("  present+configured+pass should be ok=True")

    # 4) present + configured + fails -> failed, ok=False (enforce pass)
    ok, rep = run_linters("/tmp", [fake("fail", True, True, 2)])
    if ok or "fail" not in rep["failed"]:
        failures.append("  present+configured+fail should enforce (ok=False)")

    # 5) mixed: one failing among skips makes the whole run fail
    ok, rep = run_linters("/tmp", [
        fake("absent", False, True, 0),
        fake("fail", True, True, 1),
        fake("pass", True, True, 0),
    ])
    if ok or "fail" not in rep["failed"]:
        failures.append("  a single failing linter must fail the whole run")

    if failures:
        print("FAIL: run-linters self-test")
        print("\n".join(failures))
        return 1
    print("OK: all run-linters self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Thin external-linter delegation (#216 c4)")
    parser.add_argument("--root", default=None, help="repo root (default: git toplevel else CWD)")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--self-test", action="store_true", help="run injected-fake delegation cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())
    ok, report = run_linters(root, default_linters())

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        ran = ", ".join(f"{r['name']}(exit {r['exit']})" for r in report["ran"]) or "none"
        skipped = ", ".join(f"{s['name']}({s['reason']})" for s in report["skipped"]) or "none"
        print(f"linters ran: {ran}")
        print(f"linters skipped: {skipped}")
        if report["failed"]:
            print(f"FAIL: linter(s) failed: {', '.join(report['failed'])}")
        else:
            print("OK: no present linter reported failures (skips are graceful).")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
