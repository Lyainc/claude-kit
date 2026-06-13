#!/usr/bin/env python3
"""bump-version.py — set the single lockstep version across all manifests.

claude-kit releases lockstep: every plugin shares one version, published under a
single tag `vX.Y.Z`. This script is the one entry point that writes that version to:

  - each plugin's {plugin}/.claude-plugin/plugin.json  ($.version)
  - the root marketplace.json                          ($.version)
  - each marketplace.json plugins[] entry              ($.version)

It does NOT touch description/keywords — plugin.json stays the source of truth for
those, and `check-version-sync.py --fix` reconciles them into marketplace.json. Here we
only move the version, so the diff a release commit carries is minimal and reviewable.

Usage:
    python3 scripts/bump-version.py 3.0.0 [--root DIR] [--check]
    python3 scripts/bump-version.py --self-test

    --check   Don't write; exit 1 if any manifest is not already at the given version
              (used by CI to assert a release commit is internally consistent).

Exit codes: 0 = written (or --check passed), 1 = --check mismatch, 2 = usage/IO error.
"""
import argparse
import json
import os
import re
import sys

PLUGIN_DIRS = [
    "thinking-tools",
    "obsidian-vault-manager",
    "vault-bridge",
    "workflow-harness",
]
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def _git_toplevel():
    import subprocess
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(path, data):
    # Preserve a trailing newline and 2-space indent (matches the repo's manifests).
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def manifest_paths(root):
    """Return (plugin_json_paths[], marketplace_path)."""
    pjs = [
        os.path.join(root, d, ".claude-plugin", "plugin.json") for d in PLUGIN_DIRS
    ]
    mp = os.path.join(root, ".claude-plugin", "marketplace.json")
    return pjs, mp


def current_versions(root):
    """Return {label: version} across all manifests, for --check / reporting."""
    pjs, mp_path = manifest_paths(root)
    out = {}
    for d, pj in zip(PLUGIN_DIRS, pjs):
        out[f"plugin.json:{d}"] = _read(pj).get("version")
    marketplace = _read(mp_path)
    out["marketplace:root"] = marketplace.get("version")
    for entry in marketplace.get("plugins", []):
        out[f"marketplace:{entry.get('name')}"] = entry.get("version")
    return out


def apply_version(root, version):
    """Write `version` to every manifest. Returns the count of files changed."""
    pjs, mp_path = manifest_paths(root)
    changed = 0
    for pj in pjs:
        data = _read(pj)
        if data.get("version") != version:
            data["version"] = version
            _write(pj, data)
            changed += 1
    marketplace = _read(mp_path)
    dirty = False
    if marketplace.get("version") != version:
        marketplace["version"] = version
        dirty = True
    for entry in marketplace.get("plugins", []):
        if entry.get("version") != version:
            entry["version"] = version
            dirty = True
    if dirty:
        _write(mp_path, marketplace)
        changed += 1
    return changed


def run_self_test():
    import tempfile
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        # Build a minimal fixture mirroring the real layout.
        for d in PLUGIN_DIRS:
            os.makedirs(os.path.join(tmp, d, ".claude-plugin"))
            _write(os.path.join(tmp, d, ".claude-plugin", "plugin.json"),
                   {"name": d, "version": "0.0.1"})
        os.makedirs(os.path.join(tmp, ".claude-plugin"))
        _write(os.path.join(tmp, ".claude-plugin", "marketplace.json"),
               {"name": "mp", "version": "0.0.1",
                "plugins": [{"name": d, "version": "0.0.1", "source": f"./{d}/"}
                            for d in PLUGIN_DIRS]})

        changed = apply_version(tmp, "3.0.0")
        if changed != 5:  # 4 plugin.json + 1 marketplace.json
            failures.append(f"  expected 5 files changed, got {changed}")
        versions = set(current_versions(tmp).values())
        if versions != {"3.0.0"}:
            failures.append(f"  expected all 3.0.0, got {versions}")
        # Idempotent: re-applying same version changes nothing.
        if apply_version(tmp, "3.0.0") != 0:
            failures.append("  re-apply of same version should change 0 files")

    if failures:
        print("FAIL: bump-version self-test")
        print("\n".join(failures))
        return 1
    print("OK: all bump-version self-test cases passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="set the lockstep version across manifests")
    parser.add_argument("version", nargs="?", help="X.Y.Z to write")
    parser.add_argument("--root", default=None)
    parser.add_argument("--check", action="store_true",
                        help="assert all manifests already equal version (no write)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.version:
        parser.error("version is required (unless --self-test)")
    if not _SEMVER_RE.match(args.version):
        parser.error(f"not a valid SemVer: {args.version!r}")

    root = os.path.abspath(args.root or _git_toplevel() or os.getcwd())

    try:
        if args.check:
            versions = current_versions(root)
            mismatched = {k: v for k, v in versions.items() if v != args.version}
            if mismatched:
                print(f"MISMATCH: manifests not all at {args.version}:")
                for k, v in mismatched.items():
                    print(f"  - {k}: {v}")
                return 1
            print(f"OK: all {len(versions)} manifest versions == {args.version}")
            return 0

        changed = apply_version(root, args.version)
        print(f"OK: set version {args.version} ({changed} file(s) updated)")
        return 0
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
