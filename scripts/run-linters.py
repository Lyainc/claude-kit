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

Contract (whole run): if NOT ONE linter ran, the run **exits 2 and reports no verdict**.
Per-linter skips stay graceful — but a run where every one of them skipped inspected
nothing, and "nothing was inspected" must not be spelled the same way as "the tree is
clean". That is #456, the same silent-safeguard-off failure class as #447/#454: through
2026-07 this script exited 0 on a machine with no ruff / prettier / shellcheck installed,
so `check-test-exitcode.py` counted it among the passing guards while it had looked at no
file at all. Exit 2 is borrowed deliberately from check-skill-token-budget.py, which
refuses a verdict without tiktoken rather than downgrading to a backend it just called
insufficient. There is no `--allow-none` escape: nothing in this repo invokes real mode,
so an opt-out would exist only to restore the green light this exit code removes.

This keeps the MECHANISM committed and active the moment a linter is added to the repo /
CI image, with zero per-repo reimplementation. The delegation is still latent on a repo
with no linter installed — latent now announces itself instead of passing.

Usage:
    python3 scripts/run-linters.py [--root DIR] [--json] [--self-test]

Exit codes: 0 = at least one linter ran and every present linter passed,
            1 = a present linter failed,
            2 = no linter ran at all (nothing inspected) / usage error.
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


def nothing_ran_verdict(report):
    """Return (exit_code, message) for a run that inspected nothing. None exit = proceed."""
    if report["ran"]:
        return None, ""
    skipped = ", ".join(f"{s['name']}({s['reason']})" for s in report["skipped"]) or "no linters known"
    return 2, (
        "FATAL: no linter ran, so nothing was inspected and this run reports no verdict.\n"
        f"  skipped: {skipped}\n"
        "  An all-skipped run is indistinguishable from a clean one, so it is not spelled\n"
        "  exit 0 (#456). Install at least one of ruff / prettier / shellcheck, with the repo\n"
        "  config it delegates to, and re-run."
    )


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

    # 6) NOTHING ran: every linter skipped -> refuse a verdict (#456). The per-linter skips
    #    above are still graceful; it is the whole-run silence that must not read as a pass.
    _, rep = run_linters("/tmp", [fake("absent", False, True, 0), fake("noconf", True, False, 0)])
    code, msg = nothing_ran_verdict(rep)
    if code != 2 or "FATAL" not in msg:
        failures.append(f"  an all-skipped run must exit 2 with a FATAL message, got {code}: {msg!r}")
    if "absent" not in msg or "noconf" not in msg:
        failures.append("  the refusal must name what it skipped, so the cause is readable")

    # 7) One linter ran -> the whole-run verdict stays out of the way.
    code, _ = nothing_ran_verdict(run_linters("/tmp", [fake("pass", True, True, 0)])[1])
    if code is not None:
        failures.append(f"  a run with one linter must proceed, got exit {code}")

    # 8) A failing linter still reports exit 1, not the exit-2 refusal — the two signals
    #    mean different things (a lint failure vs no measurement at all).
    code, _ = nothing_ran_verdict(run_linters("/tmp", [fake("fail", True, True, 1)])[1])
    if code is not None:
        failures.append(f"  a failing linter is a verdict, not a refusal, got exit {code}")

    # 9) WIRING: the refusal must be reachable from main(), not merely correct as a function.
    #    Deleting the call from main() leaves cases 6-8 green, which is how the original
    #    silent-pass shipped. default_linters is patched so no real tool needs to exist.
    import contextlib
    import io

    def run_main(argv, table):
        saved = globals()["default_linters"]
        out, err = io.StringIO(), io.StringIO()
        try:
            globals()["default_linters"] = lambda: table
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                return main(argv), out.getvalue(), err.getvalue()
        finally:
            globals()["default_linters"] = saved

    rc, _, err = run_main(["--root", "/tmp"], [fake("absent", False, True, 0)])
    if rc != 2 or "FATAL" not in err:
        failures.append(f"  wiring: main() with no linter available must exit 2 + FATAL, got {rc}")
    rc, _, _ = run_main(["--root", "/tmp"], [fake("pass", True, True, 0)])
    if rc != 0:
        failures.append(f"  wiring: main() with a passing linter must exit 0, got {rc}")

    # --json is a separate consumer: an exit code it never reads must not be the only place
    # the refusal is recorded, so the payload's own `ok` is asserted, not just the rc.
    rc, out, _ = run_main(["--root", "/tmp", "--json"], [fake("absent", False, True, 0)])
    payload = json.loads(out)
    if rc != 2 or payload["ok"] is not False:
        failures.append(
            f"  wiring: --json must not launder the refusal into a pass, got rc={rc} ok={payload['ok']}"
        )
    rc, out, _ = run_main(["--root", "/tmp", "--json"], [fake("pass", True, True, 0)])
    if rc != 0 or json.loads(out)["ok"] is not True:
        failures.append("  wiring: --json on a real pass must still report ok=true")

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
    code, message = nothing_ran_verdict(report)

    if args.json:
        # ok must not stay True on a run that inspected nothing — a JSON consumer reading
        # `"ok": true` off an all-skipped run is exactly the silent green #456 is about.
        report["ok"] = ok and code is None
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        ran = ", ".join(f"{r['name']}(exit {r['exit']})" for r in report["ran"]) or "none"
        skipped = ", ".join(f"{s['name']}({s['reason']})" for s in report["skipped"]) or "none"
        print(f"linters ran: {ran}")
        print(f"linters skipped: {skipped}")
        if report["failed"]:
            print(f"FAIL: linter(s) failed: {', '.join(report['failed'])}")
        elif code is None:
            print("OK: every linter that ran passed (per-linter skips are graceful).")

    if message:
        print(message, file=sys.stderr)
    if code is not None:
        return code
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
