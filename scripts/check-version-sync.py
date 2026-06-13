#!/usr/bin/env python3
"""check-version-sync.py — marketplace ↔ plugin.json version-sync drift guard (#134).

The Version Sync Rule (CLAUDE.md): for every plugin, the `version`, `description`,
and `keywords` fields in `.claude-plugin/marketplace.json` MUST equal the same fields
in that plugin's `{source}/.claude-plugin/plugin.json`. The plugin `name` must match too.

This is a BLOCK guard: any drift (or an unresolvable plugin.json a marketplace entry
points at) exits non-zero, so a release that would ship divergent manifests is stopped
in CI before merge.

plugin.json is the source of truth; --fix rewrites marketplace.json entries to match.

Usage:
    python3 scripts/check-version-sync.py [--root DIR] [--json] [--self-test] [--fix]

    --root DIR    Repo root to check (default: git toplevel, else CWD). Looks for
                  DIR/.claude-plugin/marketplace.json and DIR/<source>/.claude-plugin/plugin.json.
    --json        Emit a machine-readable JSON report instead of text.
    --fix         Reconcile drift by copying version/description/keywords from each
                  plugin.json into its marketplace.json entry (plugin.json wins), then
                  re-check. The plugin `name` (the match key) is never rewritten.
    --self-test   Run in-memory drift-detection cases (version/description/keywords/name)
                  and exit 0 only if every case is detected as expected.

Exit codes: 0 = synced (or fixed), 1 = drift detected, 2 = usage / unreadable marketplace.json, 3 = marketplace.json not found.
"""
import argparse
import json
import os
import subprocess
import sys

# Fields that must stay identical between a marketplace plugin entry and its plugin.json.
SYNCED_FIELDS = ("name", "version", "description", "keywords")


def _git_toplevel():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def compare_entry(mp_entry, plugin_json):
    """Return a list of (field, marketplace_value, plugin_value) drift tuples."""
    drifts = []
    for field in SYNCED_FIELDS:
        mp_val = mp_entry.get(field)
        pj_val = plugin_json.get(field)
        if mp_val != pj_val:
            drifts.append((field, mp_val, pj_val))
    return drifts


def check_root(root):
    """Check version-sync under `root`. Returns (ok: bool, report: dict)."""
    report = {"root": root, "plugins": [], "violations": []}
    mp_path = os.path.join(root, ".claude-plugin", "marketplace.json")
    if not os.path.isfile(mp_path):
        report["violations"].append(f"marketplace.json not found: {mp_path}")
        report["missing_manifest"] = True
        return False, report

    try:
        marketplace = _load_json(mp_path)
    except (json.JSONDecodeError, OSError) as exc:
        report["violations"].append(f"marketplace.json unreadable: {mp_path} ({exc})")
        report["fatal"] = True
        return False, report

    plugins = marketplace.get("plugins", [])
    if not plugins:
        report["violations"].append("marketplace.json has no plugins[]")
        report["fatal"] = True
        return False, report

    ok = True
    for entry in plugins:
        name = entry.get("name", "<unnamed>")
        source = entry.get("source", "")
        pj_path = os.path.normpath(
            os.path.join(root, source, ".claude-plugin", "plugin.json")
        )
        plugin_status = {"name": name, "plugin_json": pj_path, "drifts": []}

        if not os.path.isfile(pj_path):
            msg = f"[{name}] plugin.json not found at {pj_path}"
            report["violations"].append(msg)
            plugin_status["error"] = "plugin.json not found"
            report["plugins"].append(plugin_status)
            ok = False
            continue

        try:
            plugin_json = _load_json(pj_path)
        except (json.JSONDecodeError, OSError) as exc:
            msg = f"[{name}] plugin.json unreadable: {exc}"
            report["violations"].append(msg)
            plugin_status["error"] = "plugin.json unreadable"
            report["plugins"].append(plugin_status)
            ok = False
            continue

        drifts = compare_entry(entry, plugin_json)
        for field, mp_val, pj_val in drifts:
            report["violations"].append(
                f"[{name}] {field} drift: marketplace={mp_val!r} != plugin.json={pj_val!r}"
            )
            plugin_status["drifts"].append(
                {"field": field, "marketplace": mp_val, "plugin_json": pj_val}
            )
        if drifts:
            ok = False
        report["plugins"].append(plugin_status)

    return ok, report


def fix_root(root):
    """Rewrite marketplace.json entries to match each plugin.json (plugin.json wins).

    Only the synced fields except `name` are copied (name is the match key). Returns
    (fixed_count, errors[]). A plugin.json that is missing/unreadable is reported as an
    error and left for the normal check to flag — --fix does not invent data.
    """
    mp_path = os.path.join(root, ".claude-plugin", "marketplace.json")
    errors = []
    try:
        marketplace = _load_json(mp_path)
    except (json.JSONDecodeError, OSError) as exc:
        return 0, [f"marketplace.json unreadable: {exc}"]

    fixed = 0
    fixable_fields = [f for f in SYNCED_FIELDS if f != "name"]
    for entry in marketplace.get("plugins", []):
        name = entry.get("name", "<unnamed>")
        source = entry.get("source", "")
        pj_path = os.path.normpath(
            os.path.join(root, source, ".claude-plugin", "plugin.json")
        )
        try:
            plugin_json = _load_json(pj_path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"[{name}] plugin.json unreadable, skipped: {exc}")
            continue
        for field in fixable_fields:
            if field in plugin_json and entry.get(field) != plugin_json[field]:
                entry[field] = plugin_json[field]
                fixed += 1

    if fixed:
        with open(mp_path, "w", encoding="utf-8") as fh:
            json.dump(marketplace, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return fixed, errors


def run_self_test():
    """Validate drift detection independently of the filesystem."""
    base_mp = {
        "name": "demo",
        "version": "1.2.3",
        "description": "demo plugin",
        "keywords": ["a", "b"],
    }
    base_pj = dict(base_mp)

    cases = [
        ("clean", base_mp, base_pj, []),
        ("version drift", base_mp, {**base_pj, "version": "1.2.4"}, ["version"]),
        ("description drift", base_mp, {**base_pj, "description": "other"}, ["description"]),
        ("keywords drift", base_mp, {**base_pj, "keywords": ["a"]}, ["keywords"]),
        ("keywords reorder", base_mp, {**base_pj, "keywords": ["b", "a"]}, ["keywords"]),
        ("name drift", base_mp, {**base_pj, "name": "demo2"}, ["name"]),
        ("multi drift", base_mp,
         {**base_pj, "version": "9.9.9", "keywords": ["x"]}, ["version", "keywords"]),
    ]

    failures = []
    for label, mp_entry, plugin_json, expected_fields in cases:
        drifts = compare_entry(mp_entry, plugin_json)
        got_fields = [d[0] for d in drifts]
        if got_fields != expected_fields:
            failures.append(
                f"  {label}: expected {expected_fields}, got {got_fields}"
            )

    # Test missing manifest vs drift exit code modes
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        ok, missing_report = check_root(tmpdir)
        if not missing_report.get("missing_manifest"):
            failures.append("  missing marketplace: expected missing_manifest=True")

    # Test --fix reconciles drift on a real fixture (plugin.json wins).
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "demo", ".claude-plugin"))
        os.makedirs(os.path.join(tmpdir, ".claude-plugin"))
        with open(os.path.join(tmpdir, "demo", ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump({"name": "demo", "version": "2.0.0",
                       "description": "new desc", "keywords": ["x", "y"]}, fh)
        with open(os.path.join(tmpdir, ".claude-plugin", "marketplace.json"), "w") as fh:
            json.dump({"name": "mp", "version": "1.0.0", "plugins": [
                {"name": "demo", "version": "1.0.0", "description": "old desc",
                 "keywords": ["x"], "source": "./demo/"}]}, fh)
        # Before fix: drift exists.
        ok_before, _ = check_root(tmpdir)
        if ok_before:
            failures.append("  --fix fixture: expected drift before fix")
        fixed, errs = fix_root(tmpdir)
        if errs:
            failures.append(f"  --fix fixture: unexpected errors {errs}")
        if fixed != 3:  # version + description + keywords
            failures.append(f"  --fix fixture: expected 3 fields fixed, got {fixed}")
        ok_after, _ = check_root(tmpdir)
        if not ok_after:
            failures.append("  --fix fixture: drift remains after fix")
        # name is the match key — never rewritten.
        mp_after = _load_json(os.path.join(tmpdir, ".claude-plugin", "marketplace.json"))
        if mp_after["plugins"][0]["name"] != "demo":
            failures.append("  --fix fixture: name must not be rewritten")

    if failures:
        print("FAIL: check-version-sync self-test")
        print("\n".join(failures))
        return 1
    print(f"OK: all {len(cases)} version-sync self-test cases passed "
          f"(+ missing-manifest mode + --fix reconcile check)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="marketplace ↔ plugin.json version-sync guard")
    parser.add_argument("--root", default=None, help="repo root to check")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--fix", action="store_true",
                        help="rewrite marketplace.json entries to match plugin.json")
    parser.add_argument("--self-test", action="store_true", help="run in-memory drift cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    root = args.root or _git_toplevel() or os.getcwd()
    root = os.path.abspath(root)

    if args.fix:
        fixed, errors = fix_root(root)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        if fixed:
            print(f"FIXED: reconciled {fixed} field(s) into marketplace.json from plugin.json")
        else:
            print("OK: nothing to fix — marketplace.json already matches plugin.json")
        # Fall through to a normal check so the exit code reflects the post-fix state.

    ok, report = check_root(root)

    if args.json:
        report["ok"] = ok
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if ok:
            n = len(report["plugins"])
            print(f"OK: version-sync clean — {n} plugin(s), no drift (root: {root})")
        else:
            print("DRIFT: version-sync violations found:")
            for v in report["violations"]:
                print(f"  - {v}")
            print("Fix: keep version/description/keywords identical between "
                  ".claude-plugin/marketplace.json and each plugin's plugin.json "
                  "(see CLAUDE.md 'Version Sync Rule').")

    if report.get("missing_manifest"):
        return 3
    if report.get("fatal"):
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
