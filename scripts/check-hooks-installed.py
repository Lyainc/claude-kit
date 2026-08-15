#!/usr/bin/env python3
"""check-hooks-installed.py — verify .git/hooks/pre-commit matches the tracked shim (#651).

RULE (P12): a payload copied into someone else's location is current only if its content
still matches its origin — existence alone is not enough. scripts/install-hooks.sh writes
the shim documented verbatim in scripts/hooks/pre-commit's own header comment (the
"Install it verbatim:" block) into .git/hooks/pre-commit. This script re-extracts that
same block and compares it against whatever is actually installed, so "looks installed"
and "still matches what this repo expects" cannot silently drift apart.

Three outcomes, on purpose:
  - MISSING: no hook installed. Exit 0. A fresh clone, a CI checkout, and a contributor
    who has not run the installer yet are all this case, and none of them is a defect —
    the guard must not fail hard in an environment where the hook legitimately cannot be
    installed (CI has no interactive install step). Reports the install command instead.
  - STALE: a hook is installed but its content no longer matches the tracked shim (edited
    by hand, or left over from before #651). Exit 1 — this is the case P12 exists to catch,
    since "a file exists at .git/hooks/pre-commit" reads as installed while carrying the
    wrong behavior.
  - OK: installed and matches. Exit 0.

Usage:
    python3 scripts/check-hooks-installed.py [--root DIR] [--self-test]

Exit codes: 0 = MISSING or OK. 1 = STALE. 2 = usage error / source file unreadable.
"""
import argparse
import os
import re
import subprocess
import sys

SOURCE_REL = "scripts/hooks/pre-commit"
INDENT = "#   "


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_common_dir(root):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True, cwd=root,
        )
        common = out.stdout.strip()
        return common if os.path.isabs(common) else os.path.join(root, common)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def extract_shim(source_text):
    """Pull the indented '#   ' block out of scripts/hooks/pre-commit's header comment."""
    lines = [
        line[len(INDENT):]
        for line in source_text.splitlines()
        if line.startswith(INDENT)
    ]
    return "\n".join(lines) + "\n" if lines else ""


def check(root):
    source_path = os.path.join(root, SOURCE_REL)
    try:
        with open(source_path, encoding="utf-8") as f:
            source_text = f.read()
    except OSError as e:
        return 2, f"FATAL: cannot read {SOURCE_REL}: {e}"

    expected = extract_shim(source_text)
    if not expected:
        return 2, f"FATAL: no verbatim shim block found in {SOURCE_REL}"

    common_dir = _git_common_dir(root)
    if common_dir is None:
        return 0, "OK: not a git checkout — hook install is not applicable here"

    target = os.path.join(common_dir, "hooks", "pre-commit")
    if not os.path.isfile(target):
        return 0, (
            "MISSING: .git/hooks/pre-commit is not installed — run "
            "`bash scripts/install-hooks.sh` (fine in CI/fresh clones; not a failure)"
        )

    with open(target, encoding="utf-8") as f:
        installed = f.read()

    if installed != expected:
        return 1, (
            f"STALE: {target} does not match the shim tracked at {SOURCE_REL} — "
            "re-run `bash scripts/install-hooks.sh`"
        )

    return 0, f"OK: {target} matches the tracked shim"


def self_test():
    import tempfile

    cases = []

    def record(name, ok):
        cases.append((name, ok))

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "scripts", "hooks"))
        source_path = os.path.join(tmp, "scripts", "hooks", "pre-commit")
        shim_body = (
            "#!/bin/sh\n"
            "# Shim only.\n"
            '[ -x "$(git rev-parse --show-toplevel)/scripts/hooks/pre-commit" ] || exit 0\n'
            'exec "$(git rev-parse --show-toplevel)/scripts/hooks/pre-commit" "$@"\n'
        )
        source_text = (
            "#!/usr/bin/env bash\n"
            "# some header\n"
            "#\n"
            "# Install it verbatim:\n"
            "#\n"
            + "\n".join(INDENT + line if line else "#" for line in shim_body.splitlines())
            + "\n#\n# trailing\nset -u\n"
        )
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_text)

        expected = extract_shim(source_text)
        record("extract_shim recovers the indented block", expected == shim_body)

        # Case 1: no .git at all -> treated as not-applicable, exit 0.
        code, msg = check(tmp)
        record("no git checkout -> exit 0", code == 0 and "not a git checkout" in msg)

        # Simulate a git-common-dir by monkeypatching.
        git_common = os.path.join(tmp, ".git")
        os.makedirs(os.path.join(git_common, "hooks"))

        real_git_common_dir = globals()["_git_common_dir"]
        globals()["_git_common_dir"] = lambda root: git_common

        try:
            # Case 2: hook missing.
            code, msg = check(tmp)
            record("missing hook -> exit 0 MISSING", code == 0 and msg.startswith("MISSING"))

            # Case 3: hook installed and matches.
            hook_path = os.path.join(git_common, "hooks", "pre-commit")
            with open(hook_path, "w", encoding="utf-8") as f:
                f.write(expected)
            code, msg = check(tmp)
            record("matching hook -> exit 0 OK", code == 0 and msg.startswith("OK"))

            # Case 4: hook installed but stale.
            with open(hook_path, "w", encoding="utf-8") as f:
                f.write(expected.replace("exit 0", "exit 1"))
            code, msg = check(tmp)
            record("stale hook -> exit 1 STALE", code == 1 and msg.startswith("STALE"))
        finally:
            globals()["_git_common_dir"] = real_git_common_dir

        # Case 5: source file missing entirely.
        os.remove(source_path)
        code, msg = check(tmp)
        record("missing source file -> exit 2", code == 2 and "FATAL" in msg)

    failed = [name for name, ok in cases if not ok]
    if failed:
        print(f"FAIL: {len(failed)}/{len(cases)} self-test cases failed: {failed}")
        return 1
    print(f"OK: all {len(cases)} check-hooks-installed self-test cases passed")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", help="Repo root (default: git toplevel, else CWD)")
    parser.add_argument("--self-test", action="store_true", help="Run in-memory self-test")
    args = parser.parse_args()

    if args.self_test:
        sys.exit(self_test())

    root = args.root or _git_toplevel() or os.getcwd()
    code, msg = check(root)
    print(msg)
    sys.exit(code)


if __name__ == "__main__":
    main()
