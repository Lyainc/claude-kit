#!/usr/bin/env python3
"""Check every vault-bridge shell hook, including a broken-second-file regression."""

from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def syntax_failures(paths):
    """Bash treats later filename arguments as script arguments, so run once per file."""
    failures = []
    for path in paths:
        try:
            result = subprocess.run(
                ["bash", "-n", str(path)], capture_output=True, text=True
            )
        except FileNotFoundError:
            print("FAIL: `bash` not found on PATH; cannot check shell hook syntax", file=sys.stderr)
            sys.exit(1)
        if result.returncode:
            failures.append((path, result.stderr.strip()))
    return failures


def second_file_regression():
    with tempfile.TemporaryDirectory() as directory:
        first = Path(directory) / "a-valid.sh"
        second = Path(directory) / "b-broken.sh"
        first.write_text("#!/bin/bash\nprintf 'valid\\n'\n", encoding="utf-8")
        second.write_text("#!/bin/bash\nif true; then\n", encoding="utf-8")
        failures = syntax_failures([first, second])
        if [path for path, _ in failures] != [second]:
            raise AssertionError("a broken second shell file must fail syntax checking")
        second.write_text("#!/bin/bash\ntrue\n", encoding="utf-8")
        if syntax_failures([first, second]):
            raise AssertionError("valid shell files must pass syntax checking")


def main():
    second_file_regression()
    hooks = sorted((ROOT / "vault-bridge" / "hooks").glob("*.sh"))
    if not hooks:
        print("FAIL: no vault-bridge shell hooks found", file=sys.stderr)
        return 1
    failures = syntax_failures(hooks)
    for path, error in failures:
        print(f"FAIL: {path}\n{error}", file=sys.stderr)
    if failures:
        return 1
    print("OK: shell hook syntax and second-file regression passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
