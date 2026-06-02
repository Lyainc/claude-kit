#!/usr/bin/env python3
"""
Regression test for `plan-doc-syncer.py --discover` mode.

`--discover` walks a project root, applies effective include/exclude
patterns (DEFAULT + .vault-link overrides), and emits candidate paths one
per line. A silent regression here would suppress all plan-doc autosync
suggestions with no error — the SessionEnd hook would simply find zero
candidates and exit silently.

Run: python3 vault-bridge/scripts/test/test-discover.py
Exit 0 on pass, 1 on fail.
"""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYNCER = ROOT / "scripts" / "plan-doc-syncer.py"

# Allow direct import of gate functions for unit-level coverage.
sys.path.insert(0, str(SYNCER.parent))
spec = importlib.util.spec_from_file_location("plan_doc_syncer", SYNCER)
_pds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_pds)


def _touch(path: Path, body: str = "# stub\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _hermetic_env() -> dict:
    """Return a copy of os.environ with vault-path vars stripped.

    Prevents a developer's VAULT_BRIDGE_VAULT_ROOT / VAULT_BRIDGE_VAULT_PATH
    from leaking into subprocess calls and producing false passes or failures
    (plan-doc-syncer._default_vault_root() reads both vars).
    """
    env = os.environ.copy()
    for key in ("VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH"):
        env.pop(key, None)
    return env


def _run_discover(project_root: Path) -> tuple[int, list[str], str]:
    """Run --discover and return (returncode, stdout_lines, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(SYNCER), "--discover", str(project_root)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=_hermetic_env(),
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return proc.returncode, lines, proc.stderr


def _assert(cond: bool, desc: str, errors: list[str]) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


def case_default_patterns_only(errors: list[str]) -> None:
    """No .vault-link override → DEFAULT_INCLUDE_PATTERNS only."""
    print("\ncase: default patterns only")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Default-include matches:
        _touch(root / "docs" / "discussions" / "20260419_topic" / "analysis.md")
        _touch(root / "docs" / "design" / "feature-x.md")
        _touch(root / "docs" / "plans" / "rollout.md")
        _touch(root / "PLAN.md")
        _touch(root / "DESIGN.md")
        _touch(root / "RFC-001.md")
        # Default-exclude / non-matching files:
        _touch(root / ".omc" / "plans" / "spike.md")  # vendor-neutral: .omc no longer auto-discovered
        _touch(root / "node_modules" / "pkg" / "PLAN.md")
        _touch(root / "build" / "artifact.md")
        _touch(root / "CHANGELOG.md")
        _touch(root / "README.md")
        _touch(root / "src" / "main.py")
        # .vault-link with vault_path only (no override):
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")

        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)

        expected = {
            "docs/discussions/20260419_topic/analysis.md",
            "docs/design/feature-x.md",
            "docs/plans/rollout.md",
            "PLAN.md",
            "DESIGN.md",
            "RFC-001.md",
        }
        got = set(lines)
        _assert(expected.issubset(got), f"all default-include files surfaced (missing: {expected - got})", errors)
        _assert("CHANGELOG.md" not in got, "CHANGELOG.md excluded by DEFAULT_EXCLUDE", errors)
        _assert("README.md" not in got, "README.md excluded by DEFAULT_EXCLUDE", errors)
        _assert(not any("node_modules/" in ln for ln in got), "node_modules/ excluded", errors)
        _assert(not any("build/" in ln for ln in got), "build/ excluded", errors)
        _assert(not any(".omc/" in ln for ln in got), ".omc/ excluded (vendor-neutral)", errors)
        _assert(not any(ln.endswith("main.py") for ln in got), "non-md files not surfaced", errors)


def case_override_include(errors: list[str]) -> None:
    """`autosync_paths_include` extends defaults."""
    print("\ncase: override include")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _touch(root / "PLAN.md")
        _touch(root / "notes" / "specs" / "auth.md")
        _touch(root / "adrs" / "deep" / "0001-pick.md")
        (root / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "autosync_paths_include:\n"
            "  - notes/specs/*.md\n"
            "  - adrs/**/*.md\n",
            encoding="utf-8",
        )

        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        got = set(lines)
        _assert("PLAN.md" in got, "default-include preserved with override", errors)
        _assert("notes/specs/auth.md" in got, "override include matched", errors)
        _assert("adrs/deep/0001-pick.md" in got, "** override matched cross-segment", errors)


def case_override_exclude_suppresses_default(errors: list[str]) -> None:
    """`autosync_paths_exclude` can suppress a default include match."""
    print("\ncase: override exclude suppresses default")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _touch(root / "docs" / "discussions" / "20260419_topic" / "keep.md")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "draft-suppress.md")
        (root / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "autosync_paths_exclude:\n"
            "  - docs/discussions/*/draft-*.md\n",
            encoding="utf-8",
        )

        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        got = set(lines)
        _assert("docs/discussions/20260419_topic/keep.md" in got, "non-matching default-include kept", errors)
        _assert("docs/discussions/20260419_topic/draft-suppress.md" not in got, "exclude pattern suppresses default", errors)


def case_no_candidates(errors: list[str]) -> None:
    """Empty project emits nothing on stdout, exit 0."""
    print("\ncase: no candidates")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        _touch(root / "src" / "main.py")
        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        _assert(lines == [], f"stdout empty (got: {lines})", errors)


def case_no_dup_on_overlapping_patterns(errors: list[str]) -> None:
    """Overlapping include patterns must not produce duplicates."""
    print("\ncase: no duplicates on overlapping patterns")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _touch(root / "docs" / "plans" / "shared.md")
        # `docs/plans/**/*.md` (default) and `docs/**/*.md` (override) both match shared.md.
        (root / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "autosync_paths_include:\n"
            "  - docs/**/*.md\n",
            encoding="utf-8",
        )
        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        _assert(lines.count("docs/plans/shared.md") == 1, f"shared.md emitted exactly once (got: {lines})", errors)


def case_traversal_pattern_blocked(errors: list[str]) -> None:
    """
    Adversarial `autosync_paths_include` patterns that try to climb out of
    project_root must not surface files outside the tree. The guard is
    `Path.resolve().relative_to(project_root_resolved)` raising ValueError;
    this case pins it as a regression test.
    """
    print("\ncase: traversal pattern blocked")
    with tempfile.TemporaryDirectory() as tmp:
        outer = Path(tmp)
        project = outer / "proj"
        project.mkdir()
        # Files outside project_root that must NEVER appear in candidates.
        _touch(outer / "secret" / "exfil.md", body="leak\n")
        _touch(outer / "passwords.md", body="leak\n")
        # In-tree file that should still be discovered via DEFAULT.
        _touch(project / "PLAN.md")
        (project / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "autosync_paths_include:\n"
            "  - ../secret/*.md\n"
            "  - ../**/*.md\n"
            "  - ../passwords.md\n",
            encoding="utf-8",
        )
        rc, lines, stderr = _run_discover(project)
        _assert(rc == 0, "exit 0", errors)
        got = set(lines)
        _assert(
            not any("exfil" in ln or ln.endswith("passwords.md") for ln in got),
            f"traversal patterns did not exfiltrate outer files (got: {got})",
            errors,
        )
        _assert("PLAN.md" in got, "default-include preserved alongside rejected traversal patterns", errors)


def case_malformed_vault_link(errors: list[str]) -> None:
    """
    Pathologically malformed `.vault-link` (regex metachars in keys, extra
    colons, garbage scalars) must not crash discovery. The expectation is:
    parser silently drops what it can't make sense of, defaults still apply.
    Replaces the single-purpose `_yaml_value` regex-metachar test that lived
    in the deleted test-yaml-value.sh.
    """
    print("\ncase: malformed .vault-link tolerated")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _touch(root / "PLAN.md")
        (root / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "auto.capture[]: foo: bar\n"
            "::: weird :::\n"
            "autosync_paths_include: !!!\n"
            "autosync_paths_exclude:\n"
            "  - [unclosed\n",
            encoding="utf-8",
        )
        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0 on malformed input", errors)
        _assert("PLAN.md" in set(lines), "default-include still works after malformed override", errors)


def case_quoted_and_inline_array_scalars(errors: list[str]) -> None:
    """
    Parse correctness for `_parse_scalar` / `_FLOW_ARRAY_RE`: quoted scalars
    must have surrounding quotes stripped, and inline flow arrays must
    decompose into individual patterns. Replaces the parser-correctness
    surface that the deleted test-yaml-value.sh covered indirectly.
    """
    print("\ncase: quoted / inline-array override scalars")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _touch(root / "PLAN.md")
        _touch(root / "alpha.md")
        _touch(root / "beta.md")
        _touch(root / "specs" / "auth.md")
        # `autosync_paths_include` mixes a flow array of quoted+unquoted items
        # plus a single block-list quoted entry. All four files must surface.
        (root / ".vault-link").write_text(
            'vault_path: 20_Projects/test\n'
            'autosync_paths_include: [alpha.md, "beta.md"]\n'
            'autosync_paths_exclude:\n'
            '  - "PLAN.md"\n',
            encoding="utf-8",
        )
        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        got = set(lines)
        _assert("alpha.md" in got, "unquoted inline-array element matched", errors)
        _assert("beta.md" in got, "quoted inline-array element matched (quotes stripped)", errors)
        _assert("PLAN.md" not in got, "quoted exclude pattern strips quotes and suppresses default", errors)


def case_single_scalar_override(errors: list[str]) -> None:
    """
    `_resolve_effective_patterns` coerces a bare-string override into a
    single-element list. Without that branch a user writing
    `autosync_paths_include: foo.md` would silently get zero matches.
    """
    print("\ncase: single-scalar override coerced to list")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _touch(root / "PLAN.md")
        _touch(root / "single-target.md")
        (root / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "autosync_paths_include: single-target.md\n",
            encoding="utf-8",
        )
        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        got = set(lines)
        _assert("single-target.md" in got, "bare-string include coerced to list and matched", errors)
        _assert("PLAN.md" in got, "default-include preserved alongside scalar override", errors)


def case_snapshot_export_l1(errors: list[str]) -> None:
    print("\ncase: snapshot_export L1 (new key only)")
    _assert(_pds._check_gate_l1({"snapshot_export": True}) is True,
            "snapshot_export: true → gate passes", errors)
    _assert(_pds._check_gate_l1({"snapshot_export": False}) is False,
            "snapshot_export: false → gate fails (no alias fallback when explicit false)", errors)
    _assert(_pds._check_gate_l1({}) is False,
            "neither key present → gate fails", errors)


def case_auto_capture_alias_warns_stderr(errors: list[str]) -> None:
    print("\ncase: auto_capture alias emits stderr deprecation warning")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vl = root / ".vault-link"
        vl.write_text("vault_path: 20_Projects/test\nauto_capture: true\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            result = _pds._load_vault_link(vl)
        stderr_output = buf.getvalue()
        _assert(result.get("auto_capture") is True, "alias key parsed", errors)
        _assert("deprecated" in stderr_output and "snapshot_export" in stderr_output,
                f"stderr contains deprecation warning (got: {stderr_output!r})", errors)
        # Gate still passes via alias fallback.
        _assert(_pds._check_gate_l1(result) is True,
                "alias-only .vault-link still passes L1 gate", errors)


def case_both_keys_present_new_wins(errors: list[str]) -> None:
    print("\ncase: snapshot_export wins when both keys present")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vl = root / ".vault-link"
        vl.write_text("vault_path: 20_Projects/test\nsnapshot_export: false\nauto_capture: true\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            result = _pds._load_vault_link(vl)
        stderr_output = buf.getvalue()
        _assert(_pds._check_gate_l1(result) is False,
                "snapshot_export: false wins over alias auto_capture: true", errors)
        _assert("deprecated" not in stderr_output,
                f"no deprecation warning when new key is present (got: {stderr_output!r})", errors)


def case_snapshot_import_l2(errors: list[str]) -> None:
    """Layer 2 gate symmetry — `_check_gate_l2` honors `snapshot_import` over alias.

    Companion to `case_snapshot_export_l1`. Closes the L2/L1 coverage asymmetry
    flagged on PR #64 and pins the fail-closed behavior of the broadened
    exception handler in `_check_gate_l2`.
    """
    print("\ncase: snapshot_import L2 (new key only)")
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp) / "vault"
        project = "20_Projects/test"
        index_dir = vault_root / project
        index_dir.mkdir(parents=True)
        index = index_dir / "_index.md"

        index.write_text(
            "---\nsnapshot_import: true\ntitle: Test\n---\n# Body\n",
            encoding="utf-8",
        )
        _assert(_pds._check_gate_l2(vault_root, project) is True,
                "snapshot_import: true → gate passes", errors)

        index.write_text(
            "---\nsnapshot_import: false\nauto_capture: true\n---\n",
            encoding="utf-8",
        )
        _assert(_pds._check_gate_l2(vault_root, project) is False,
                "snapshot_import: false wins over alias auto_capture: true", errors)

        index.write_text(
            "---\nauto_capture: true\n---\n",
            encoding="utf-8",
        )
        _assert(_pds._check_gate_l2(vault_root, project) is True,
                "alias auto_capture: true (no new key) → gate passes via fallback", errors)

        # Missing _index.md → gate fails.
        index.unlink()
        _assert(_pds._check_gate_l2(vault_root, project) is False,
                "missing _index.md → gate fails", errors)


def case_deprecation_suppressed_by_env(errors: list[str]) -> None:
    """`VAULT_BRIDGE_SUPPRESS_DEPRECATION=1` silences the alias warning.

    session-end-pre.sh sets this env var before invoking the syncer so the
    deprecation notice doesn't pollute syncer_err and get reclassified as
    discovery_error. This pins that suppression contract.
    """
    print("\ncase: VAULT_BRIDGE_SUPPRESS_DEPRECATION=1 silences alias warning")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        vl = root / ".vault-link"
        vl.write_text("vault_path: 20_Projects/test\nauto_capture: true\n", encoding="utf-8")

        prev = os.environ.get("VAULT_BRIDGE_SUPPRESS_DEPRECATION")
        os.environ["VAULT_BRIDGE_SUPPRESS_DEPRECATION"] = "1"
        try:
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                result = _pds._load_vault_link(vl)
            stderr_output = buf.getvalue()
        finally:
            if prev is None:
                os.environ.pop("VAULT_BRIDGE_SUPPRESS_DEPRECATION", None)
            else:
                os.environ["VAULT_BRIDGE_SUPPRESS_DEPRECATION"] = prev

        _assert(result.get("auto_capture") is True, "alias key still parsed under suppression", errors)
        _assert("deprecated" not in stderr_output,
                f"deprecation warning suppressed when env var is 1 (got: {stderr_output!r})", errors)
        _assert(_pds._check_gate_l1(result) is True,
                "alias-only .vault-link still passes L1 gate when warning is suppressed", errors)


def case_recent_filter_hours(errors: list[str]) -> None:
    print("\ncase: --recent filter (hours)")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        recent_file = root / "docs" / "plans" / "fresh.md"
        old_file = root / "docs" / "plans" / "stale.md"
        _touch(recent_file)
        _touch(old_file)
        # Set old_file mtime to 100 hours ago.
        old_ts = time.time() - (100 * 3600)
        os.utime(old_file, (old_ts, old_ts))
        # --recent 24 should keep fresh.md, drop stale.md.
        proc = subprocess.run(
            [sys.executable, str(SYNCER), "--discover", str(root), "--recent", "24"],
            capture_output=True, text=True, cwd=str(root), env=_hermetic_env(),
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert("docs/plans/fresh.md" in lines, "recent file kept", errors)
        _assert("docs/plans/stale.md" not in lines, "100h-old file filtered out", errors)


def case_recent_zero_candidates(errors: list[str]) -> None:
    print("\ncase: --recent 0 → zero candidates (cutoff = now)")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        target = root / "PLAN.md"
        _touch(target)
        # Explicitly backdate mtime by 2 s to defeat 1-second mtime precision on
        # coarse filesystems (FAT, some CI mounts). Without this the file's mtime
        # can equal cutoff when --recent 0 evaluates `mtime < cutoff`, causing
        # intermittent failures because the strict-less comparison passes the file
        # through.
        past_ts = time.time() - 2
        os.utime(target, (past_ts, past_ts))
        proc = subprocess.run(
            [sys.executable, str(SYNCER), "--discover", str(root), "--recent", "0"],
            capture_output=True, text=True, cwd=str(root), env=_hermetic_env(),
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(lines == [], f"--recent 0 emits no candidates (got: {lines})", errors)


def case_recent_and_summary_require_discover(errors: list[str]) -> None:
    """`--recent` / `--summary` without `--discover` must parser.error, not silently ignore.

    Pairing the discovery-only flags with `--source` was almost certainly a typo
    and the prior silent ignore made the mistake invisible.
    """
    print("\ncase: --recent / --summary without --discover are rejected")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src.md"
        src.write_text("# stub\n", encoding="utf-8")
        for flag in (["--recent", "24"], ["--summary"]):
            proc = subprocess.run(
                [sys.executable, str(SYNCER), "--source", str(src), *flag],
                capture_output=True, text=True, env=_hermetic_env(),
            )
            _assert(proc.returncode != 0, f"non-zero exit for {flag}", errors)
            _assert("require --discover" in proc.stderr,
                    f"stderr explains the rejection ({flag}): {proc.stderr!r}", errors)


def case_threshold_metadata_in_output(errors: list[str]) -> None:
    print("\ncase: --summary emits category breakdown above threshold")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        # Create 12 candidates spread across two categories — threshold default 10.
        for i in range(7):
            _touch(root / "docs" / "discussions" / f"20260419_topic-{i}" / "design.md")
        for i in range(5):
            _touch(root / "docs" / "design" / f"feature-{i}.md")
        # With --summary and 12 >= threshold 10, stderr should include JSON.
        proc = subprocess.run(
            [sys.executable, str(SYNCER), "--discover", str(root), "--summary"],
            capture_output=True, text=True, cwd=str(root), env=_hermetic_env(),
        )
        _assert(proc.returncode == 0, "exit 0", errors)
        _assert(proc.stderr.strip() != "", "stderr non-empty when count >= threshold", errors)
        try:
            import json as _json
            summary = _json.loads(proc.stderr.strip().splitlines()[-1])
            _assert(summary.get("count") == 12, f"count=12 (got: {summary.get('count')})", errors)
            _assert(summary.get("threshold") == 10, f"threshold=10 (got: {summary.get('threshold')})", errors)
            _assert(isinstance(summary.get("categories"), dict) and len(summary["categories"]) >= 1,
                    "categories dict non-empty", errors)
        except (ValueError, IndexError) as exc:
            _assert(False, f"stderr summary not valid JSON: {exc}", errors)
        # Below-threshold case: --summary with <10 candidates → stderr empty for summary.
        for i in range(7):
            (root / "docs" / "discussions" / f"20260419_topic-{i}" / "design.md").unlink()
        proc2 = subprocess.run(
            [sys.executable, str(SYNCER), "--discover", str(root), "--summary"],
            capture_output=True, text=True, cwd=str(root), env=_hermetic_env(),
        )
        _assert(proc2.returncode == 0, "exit 0 (below threshold)", errors)
        # 5 candidates < 10 threshold, stderr should NOT contain summary JSON.
        _assert("count" not in proc2.stderr,
                f"no summary emitted below threshold (got stderr: {proc2.stderr!r})", errors)


def case_summary_unresolved_excluded(errors: list[str]) -> None:
    """SUMMARY.md and UNRESOLVED.md inside discussions topics are excluded by DEFAULT_EXCLUDE_PATTERNS."""
    print("\ncase: SUMMARY.md and UNRESOLVED.md excluded")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "analysis.md")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "SUMMARY.md")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "UNRESOLVED.md")
        rc, lines, stderr = _run_discover(root)
        got = set(lines)
        _assert(rc == 0, "exit 0", errors)
        _assert("docs/discussions/20260419_topic/analysis.md" in got, "design doc included", errors)
        _assert("docs/discussions/20260419_topic/SUMMARY.md" not in got, "SUMMARY.md excluded by DEFAULT_EXCLUDE", errors)
        _assert("docs/discussions/20260419_topic/UNRESOLVED.md" not in got, "UNRESOLVED.md excluded by DEFAULT_EXCLUDE", errors)


def case_transcripts_not_captured(errors: list[str]) -> None:
    """Transcript files at depth 5 (inside transcripts/ subdir) are not captured by */*.md pattern."""
    print("\ncase: transcripts/ subdir not captured")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "design.md")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "transcripts" / "01_intro.md")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "transcripts" / "02_analysis.md")
        rc, lines, stderr = _run_discover(root)
        got = set(lines)
        _assert(rc == 0, "exit 0", errors)
        _assert("docs/discussions/20260419_topic/design.md" in got, "design doc included", errors)
        _assert(
            not any("transcripts/" in ln for ln in got),
            f"no transcript files captured (got: {got})",
            errors,
        )


def case_flat_discussions_not_captured(errors: list[str]) -> None:
    """Files directly under docs/discussions/ (depth-2) are not matched by */*.md pattern."""
    print("\ncase: flat docs/discussions/ file not captured")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".vault-link").write_text("vault_path: 20_Projects/test\n", encoding="utf-8")
        _touch(root / "docs" / "discussions" / "flat-design.md")
        _touch(root / "docs" / "discussions" / "20260419_topic" / "design.md")
        rc, lines, stderr = _run_discover(root)
        got = set(lines)
        _assert(rc == 0, "exit 0", errors)
        _assert("docs/discussions/flat-design.md" not in got, "flat discussions file not captured (depth-2)", errors)
        _assert("docs/discussions/20260419_topic/design.md" in got, "topic subdir file still captured (depth-3)", errors)


def main() -> int:
    print(f"Running --discover regression tests against: {SYNCER}")
    errors: list[str] = []
    case_default_patterns_only(errors)
    case_override_include(errors)
    case_override_exclude_suppresses_default(errors)
    case_no_candidates(errors)
    case_no_dup_on_overlapping_patterns(errors)
    case_traversal_pattern_blocked(errors)
    case_malformed_vault_link(errors)
    case_quoted_and_inline_array_scalars(errors)
    case_single_scalar_override(errors)
    case_snapshot_export_l1(errors)
    case_auto_capture_alias_warns_stderr(errors)
    case_both_keys_present_new_wins(errors)
    case_snapshot_import_l2(errors)
    case_deprecation_suppressed_by_env(errors)
    case_recent_filter_hours(errors)
    case_recent_zero_candidates(errors)
    case_recent_and_summary_require_discover(errors)
    case_flat_discussions_not_captured(errors)
    case_summary_unresolved_excluded(errors)
    case_transcripts_not_captured(errors)
    case_threshold_metadata_in_output(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
