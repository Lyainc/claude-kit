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

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYNCER = ROOT / "scripts" / "plan-doc-syncer.py"


def _touch(path: Path, body: str = "# stub\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _run_discover(project_root: Path) -> tuple[int, list[str], str]:
    """Run --discover and return (returncode, stdout_lines, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(SYNCER), "--discover", str(project_root)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
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
        _touch(root / "docs" / "discussions" / "topic-a.md")
        _touch(root / "docs" / "design" / "feature-x.md")
        _touch(root / "docs" / "plans" / "rollout.md")
        _touch(root / ".omc" / "plans" / "spike.md")
        _touch(root / "PLAN.md")
        _touch(root / "DESIGN.md")
        _touch(root / "RFC-001.md")
        # Default-exclude / non-matching files:
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
            "docs/discussions/topic-a.md",
            "docs/design/feature-x.md",
            "docs/plans/rollout.md",
            ".omc/plans/spike.md",
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
        _touch(root / "docs" / "discussions" / "keep.md")
        _touch(root / "docs" / "discussions" / "draft-suppress.md")
        (root / ".vault-link").write_text(
            "vault_path: 20_Projects/test\n"
            "autosync_paths_exclude:\n"
            "  - docs/discussions/draft-*.md\n",
            encoding="utf-8",
        )

        rc, lines, stderr = _run_discover(root)
        _assert(rc == 0, "exit 0", errors)
        got = set(lines)
        _assert("docs/discussions/keep.md" in got, "non-matching default-include kept", errors)
        _assert("docs/discussions/draft-suppress.md" not in got, "exclude pattern suppresses default", errors)


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


def main() -> int:
    print(f"Running --discover regression tests against: {SYNCER}")
    errors: list[str] = []
    case_default_patterns_only(errors)
    case_override_include(errors)
    case_override_exclude_suppresses_default(errors)
    case_no_candidates(errors)
    case_no_dup_on_overlapping_patterns(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed", file=sys.stderr)
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
