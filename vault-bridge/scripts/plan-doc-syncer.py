#!/usr/bin/env python3
"""
Plan Doc Syncer — vault-bridge W8
Copies an external plan/design document into the bound vault project as a snapshot.

Usage:
  python3 plan-doc-syncer.py \\
    --source PATH        Source file path (absolute or relative to CWD)
    [--vault-root PATH]  Vault root (default: ~/vault)
    [--vault-link PATH]  .vault-link file (default: CWD/.vault-link)
    [--dry-run]          Report only; do not write (default: True)
    [--enforce]          Actually write the snapshot (disables dry-run)
    [--skip-gate-check]  Skip 2-layer opt-in gate (for /save-plan-doc explicit path)

Stdout (always JSON):
  {
    "status": "ok" | "skip" | "dry_run" | "error",
    "reason": "...",
    "target_path": "..." | null,
    "source_commit": "...",
    "source_stale_risk": bool,
    "gate_l1": bool | null,
    "gate_l2": bool | null
  }

Exit codes:
  0 — ok or skip (expected outcomes)
  1 — fatal error (missing source, bad args, write failure)
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1

DEFAULT_INCLUDE_PATTERNS = [
    "docs/discussions/**/*.md",
    "docs/design/**/*.md",
    "docs/plans/**/*.md",
    ".omc/plans/*.md",
    "PLAN.md",
    "DESIGN.md",
    "RFC-*.md",
]

DEFAULT_EXCLUDE_PATTERNS = [
    "node_modules/",
    "dist/",
    "build/",
    ".git/",
    "CHANGELOG.md",
    "README.md",
]


def _resolve_effective_patterns(vault_link: dict) -> tuple[list[str], list[str]]:
    """
    Merge DEFAULT patterns with .vault-link override fields.

    Override schema (flat, v1.1 micro-bump — backward compat with v1):
      autosync_paths_include: [pattern1, pattern2, ...]
      autosync_paths_exclude: [pattern1, pattern2, ...]

    Policy: append. User-provided patterns extend defaults; to suppress a
    default include, add a counter-pattern via autosync_paths_exclude.
    """
    extra_include = vault_link.get("autosync_paths_include") or []
    extra_exclude = vault_link.get("autosync_paths_exclude") or []
    if isinstance(extra_include, str):
        extra_include = [extra_include]
    if isinstance(extra_exclude, str):
        extra_exclude = [extra_exclude]
    include = list(DEFAULT_INCLUDE_PATTERNS) + [p for p in extra_include if p not in DEFAULT_INCLUDE_PATTERNS]
    exclude = list(DEFAULT_EXCLUDE_PATTERNS) + [p for p in extra_exclude if p not in DEFAULT_EXCLUDE_PATTERNS]
    return include, exclude


def _glob_pattern(project_root: Path, pattern: str) -> list[Path]:
    """Resolve a glob pattern relative to project_root, supporting `**` and direct paths."""
    if not pattern:
        return []
    if "**" in pattern:
        base, tail = pattern.split("**", 1)
        base = base.rstrip("/")
        tail = tail.lstrip("/") or "*"
        base_path = project_root / base if base else project_root
        if not base_path.exists() or not base_path.is_dir():
            return []
        return [p for p in base_path.rglob(tail) if p.is_file()]
    return [p for p in project_root.glob(pattern) if p.is_file()]


def _matches_exclude(rel_path: str, exclude_patterns: list[str]) -> bool:
    """Return True if rel_path matches any exclude pattern (directory prefix or fnmatch)."""
    name = Path(rel_path).name
    for excl in exclude_patterns:
        if excl.endswith("/"):
            if rel_path.startswith(excl) or f"/{excl}" in f"/{rel_path}":
                return True
        elif fnmatch.fnmatch(name, excl) or fnmatch.fnmatch(rel_path, excl):
            return True
    return False


def _discover_candidates(project_root: Path, vault_link: dict) -> list[str]:
    """
    Scan project_root using effective include patterns; filter out exclude
    patterns and vault-native paths. Returns sorted project-root-relative paths.
    """
    include, exclude = _resolve_effective_patterns(vault_link)
    found: set[str] = set()
    for pattern in include:
        for f in _glob_pattern(project_root, pattern):
            try:
                rel = str(f.resolve().relative_to(project_root.resolve()))
            except ValueError:
                continue
            if _is_vault_native(f):
                continue
            if _matches_exclude(rel, exclude):
                continue
            found.add(rel)
    return sorted(found)

# Vault-native plan paths — never autosync these (§9.5 boundary)
VAULT_NATIVE_PATTERN = re.compile(r"(~/vault/|/Users/[^/]+/vault/|/home/[^/]+/vault/)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Frontmatter parser (stdlib only — reused from generate-manifest.py pattern)
# ---------------------------------------------------------------------------

_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FLOW_ARRAY_RE = re.compile(r"^\[([^\]]*)\]$")


def _parse_scalar(value: str) -> object:
    v = value.strip()
    if not v:
        return None
    m = _FLOW_ARRAY_RE.match(v)
    if m:
        inner = m.group(1)
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def _parse_frontmatter(text: str) -> dict:
    m = _FM_BLOCK_RE.match(text)
    if not m:
        return {}
    result = {}
    current_key = None
    current_list = None
    for raw_line in m.group(1).splitlines():
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            item = raw_line.lstrip("- ").strip().strip("\"'")
            if current_key is not None:
                if current_list is None:
                    current_list = []
                    result[current_key] = current_list
                current_list.append(item)
            continue
        if ":" in raw_line:
            idx = raw_line.index(":")
            key = raw_line[:idx].strip()
            value = raw_line[idx + 1:].strip()
            current_key = key
            current_list = None
            parsed = _parse_scalar(value)
            if isinstance(parsed, list):
                result[key] = parsed
                current_list = parsed
            elif parsed is None or parsed == "":
                result[key] = None
            else:
                result[key] = parsed
    return result


# ---------------------------------------------------------------------------
# .vault-link parser
# ---------------------------------------------------------------------------

def _load_vault_link(vault_link_path: Path) -> dict:
    """Parse .vault-link YAML (simple key: value, no nested structures needed)."""
    if not vault_link_path.exists():
        return {}
    text = vault_link_path.read_text(encoding="utf-8")
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            idx = line.index(":")
            key = line[:idx].strip()
            value = line[idx + 1:].strip()
            result[key] = _parse_scalar(value) if value else None
    return result


# ---------------------------------------------------------------------------
# Git source_commit resolution — 5 cases per spec §7
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    now = datetime.now(timezone.utc).astimezone()
    return now.isoformat(timespec="seconds")


def _resolve_source_commit(source_path: Path) -> tuple[str, bool, str | None]:
    """
    Returns (source_commit: str, stale_risk: bool, git_error: str | None).

    5 cases from spec §7:
      Clean:       <short-hash>               stale_risk=False
      Dirty:       <short-hash>-dirty         stale_risk=True
      Untracked:   uncommitted@{ISO8601}      stale_risk=True
      Non-git:     non-git@{sha256[:10]}      stale_risk=True
      Git failure: unknown@{ISO8601}          stale_risk=True  (+ stderr captured)
    """
    ts = _iso_now()

    # Case 4: Not a git repo (.git/ absent in any ancestor)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(source_path.parent),
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            # Compute sha256 of file content as stable fingerprint
            sha = hashlib.sha256(source_path.read_bytes()).hexdigest()[:10]
            return f"non-git@{sha}", True, None
    except Exception as exc:
        return f"unknown@{ts}", True, str(exc)

    try:
        # Case 3: Untracked (git ls-files --error-unmatch fails)
        track_result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(source_path)],
            cwd=str(source_path.parent),
            capture_output=True, text=True, timeout=5
        )
        if track_result.returncode != 0:
            return f"uncommitted@{ts}", True, None

        # Get HEAD short hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(source_path.parent),
            capture_output=True, text=True, timeout=5
        )
        if hash_result.returncode != 0:
            return f"unknown@{ts}", True, hash_result.stderr.strip() or None

        short_hash = hash_result.stdout.strip()

        # Case 2: Tracked but dirty (file has uncommitted changes)
        diff_result = subprocess.run(
            ["git", "diff", "--quiet", str(source_path)],
            cwd=str(source_path.parent),
            capture_output=True, text=True, timeout=5
        )
        # Also check staged diff
        staged_result = subprocess.run(
            ["git", "diff", "--cached", "--quiet", str(source_path)],
            cwd=str(source_path.parent),
            capture_output=True, text=True, timeout=5
        )
        if diff_result.returncode != 0 or staged_result.returncode != 0:
            return f"{short_hash}-dirty", True, None

        # Case 1: Clean tracked file
        return short_hash, False, None

    except Exception as exc:
        # Case 5: Git operation failed
        return f"unknown@{ts}", True, str(exc)


# ---------------------------------------------------------------------------
# Opt-in gate checks
# ---------------------------------------------------------------------------

def _check_gate_l1(vault_link: dict) -> bool:
    """Layer 1: .vault-link auto_capture: true"""
    val = vault_link.get("auto_capture")
    return val is True


def _check_gate_l2(vault_root: Path, vault_path: str) -> bool:
    """Layer 2: _index.md auto_capture: true in bound vault project."""
    index_path = vault_root / vault_path / "_index.md"
    if not index_path.exists():
        return False
    try:
        text = index_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        return fm.get("auto_capture") is True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Vault-native boundary check (§9.5 / spec §1 boundary enforcement)
# ---------------------------------------------------------------------------

def _is_vault_native(source_path: Path) -> bool:
    """Return True if source path is inside a vault directory — must skip."""
    abs_str = str(source_path.resolve())
    home = str(Path.home())
    vault_abs = str(Path(home) / "vault")
    # Match ~/vault/ or any /Users/*/vault/ pattern
    if abs_str.startswith(vault_abs + os.sep) or abs_str.startswith(vault_abs + "/"):
        return True
    if VAULT_NATIVE_PATTERN.search(abs_str):
        return True
    return False


# ---------------------------------------------------------------------------
# Target filename resolution (spec §3.3)
# ---------------------------------------------------------------------------

_DATE_PREFIX_RE = re.compile(r"(\d{4})(\d{2})(\d{2})")


def _resolve_target_filename(source_path: Path, source_text: str) -> str:
    """
    Derive vault filename from source path + frontmatter.

    Rules (spec §3.3):
    - Parse YYYYMMDD from parent directory name
    - Slug from remaining directory name portion (kebab-case)
    - type from frontmatter (plan | design | rfc) or filename heuristic
    - Collision handled by caller with -v2/-v3 suffix
    """
    fm = _parse_frontmatter(source_text)

    # Determine type
    doc_type = "plan"
    fm_type = fm.get("type")
    if fm_type and str(fm_type).lower() in ("plan", "design", "rfc"):
        doc_type = str(fm_type).lower()
    elif source_path.name.lower().startswith("rfc"):
        doc_type = "rfc"
    elif source_path.name.lower().startswith("design"):
        doc_type = "design"

    # Try to extract date from parent directory name
    parent_name = source_path.parent.name
    date_str = None
    slug_part = ""

    m = _DATE_PREFIX_RE.search(parent_name)
    if m:
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # Slug is everything after the date prefix in the directory name
        after_date = parent_name[m.end():].lstrip("_-").strip()
        slug_part = _to_kebab(after_date) if after_date else ""
    else:
        # Fall back to frontmatter date or today
        fm_date = fm.get("created") or fm.get("date")
        if fm_date:
            date_str = str(fm_date)[:10]
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
        # Use source filename stem as slug
        slug_part = _to_kebab(source_path.stem)

    if slug_part:
        return f"{doc_type}-{date_str}-{slug_part}.md"
    else:
        return f"{doc_type}-{date_str}.md"


def _to_kebab(text: str) -> str:
    """Convert a string to kebab-case."""
    # Replace underscores and spaces with hyphens
    text = re.sub(r"[\s_]+", "-", text)
    # Remove non-alphanumeric except hyphens
    text = re.sub(r"[^a-zA-Z0-9-]", "", text)
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    return text.lower().strip("-")


_MAX_VERSION_SUFFIX = 99


def _resolve_collision_free_path(target_dir: Path, base_filename: str) -> Path:
    """Return a collision-free path, appending -v2/-v3 as needed."""
    stem = base_filename[:-3] if base_filename.endswith(".md") else base_filename
    candidate = target_dir / base_filename
    if not candidate.exists():
        return candidate
    for n in range(2, _MAX_VERSION_SUFFIX + 1):
        candidate = target_dir / f"{stem}-v{n}.md"
        if not candidate.exists():
            return candidate
    raise RuntimeError(
        f"refused to allocate -v{_MAX_VERSION_SUFFIX + 1} suffix for {base_filename!r} "
        f"in {target_dir} (filesystem may be full or inaccessible)"
    )


# ---------------------------------------------------------------------------
# Hash comparison for dedup (R3)
# ---------------------------------------------------------------------------

def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Snapshot frontmatter builder
# ---------------------------------------------------------------------------

def _build_snapshot_content(
    source_text: str,
    source_path: Path,
    vault_root: Path,
    source_commit: str,
    stale_risk: bool,
    git_error: str | None,
) -> str:
    """
    Prepend snapshot frontmatter to source content.
    Required fields: source_path, source_commit, captured_at (spec §3.4).
    Tags must include 'snapshot'.
    """
    fm = _parse_frontmatter(source_text)
    now = _iso_now()
    today = now[:10]

    # Merge tags, always include 'snapshot'
    existing_tags = fm.get("tags") or []
    if isinstance(existing_tags, str):
        existing_tags = [existing_tags]
    tags = list(existing_tags)
    if "snapshot" not in tags:
        tags.append("snapshot")

    doc_type = fm.get("type") or "plan"
    status = fm.get("status") or "active"

    # Relative source path for portability
    try:
        rel_source = str(source_path.resolve().relative_to(Path.cwd()))
    except ValueError:
        rel_source = str(source_path.resolve())

    tags_yaml = "[" + ", ".join(tags) + "]"

    frontmatter_lines = [
        "---",
        f"created: {today}",
        f"tags: {tags_yaml}",
        f"type: {doc_type}",
        f"status: {status}",
        f"source_path: {rel_source}",
        f"source_commit: {source_commit}",
        f"captured_at: {now}",
        f"source_stale_risk: {'true' if stale_risk else 'false'}",
    ]

    if git_error:
        # Inline git error as a single-line YAML double-quoted scalar.
        # Must escape backslash and double-quote to keep frontmatter valid.
        safe_err = (
            git_error.replace("\n", " ")[:120]
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
        )
        frontmatter_lines.append(f"source_commit_error: \"{safe_err}\"")

    frontmatter_lines.append("---")
    frontmatter_lines.append("")

    # Strip original frontmatter from source, keep body
    body = _FM_BLOCK_RE.sub("", source_text, count=1).lstrip("\n")

    return "\n".join(frontmatter_lines) + "\n" + body


# ---------------------------------------------------------------------------
# Main sync logic
# ---------------------------------------------------------------------------

def sync(
    source_path: Path,
    vault_root: Path,
    vault_link: dict,
    dry_run: bool,
    skip_gate: bool,
) -> dict:
    """
    Core sync logic. Returns result dict.
    """
    result: dict = {
        "status": "ok",
        "reason": "",
        "target_path": None,
        "source_commit": None,
        "source_stale_risk": False,
        "gate_l1": None,
        "gate_l2": None,
    }

    # Vault-native boundary check
    if _is_vault_native(source_path):
        result["status"] = "skip"
        result["reason"] = "vault-native path — autosync out of scope (spec §9.5)"
        return result

    # Source must exist and be readable
    if not source_path.exists():
        result["status"] = "error"
        result["reason"] = f"source file not found: {source_path}"
        return result

    # .vault-link must have vault_path
    vault_path = vault_link.get("vault_path")
    if not vault_path:
        result["status"] = "error"
        result["reason"] = ".vault-link missing vault_path field"
        return result

    vault_project_dir = vault_root / vault_path
    if not vault_project_dir.exists():
        result["status"] = "error"
        result["reason"] = f"vault project directory not found: {vault_project_dir}"
        return result

    # 2-layer opt-in gate
    if not skip_gate:
        l1 = _check_gate_l1(vault_link)
        l2 = _check_gate_l2(vault_root, str(vault_path))
        result["gate_l1"] = l1
        result["gate_l2"] = l2

        if not l1:
            result["status"] = "skip"
            result["reason"] = "gate L1 closed: .vault-link auto_capture is not true"
            return result
        if not l2:
            result["status"] = "skip"
            result["reason"] = "gate L2 closed: _index.md auto_capture is not true"
            return result
    else:
        result["gate_l1"] = _check_gate_l1(vault_link)
        result["gate_l2"] = _check_gate_l2(vault_root, str(vault_path))

    # Resolve source_commit
    source_commit, stale_risk, git_error = _resolve_source_commit(source_path)
    result["source_commit"] = source_commit
    result["source_stale_risk"] = stale_risk

    # Read source content
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        result["status"] = "error"
        result["reason"] = f"cannot read source: {exc}"
        return result

    # Resolve target filename
    base_filename = _resolve_target_filename(source_path, source_text)

    # Dedup check (R3): scan all existing vN snapshots for body match BEFORE
    # resolving a collision-free name. source_commit changes per run so compare
    # body only (frontmatter stripped).
    source_body = _FM_BLOCK_RE.sub("", source_text, count=1).strip()
    stem = base_filename[:-3] if base_filename.endswith(".md") else base_filename
    candidates_to_check: list[Path] = [vault_project_dir / base_filename]
    for n in range(2, _MAX_VERSION_SUFFIX + 1):
        vn = vault_project_dir / f"{stem}-v{n}.md"
        if not vn.exists():
            break
        candidates_to_check.append(vn)
    for existing_candidate in candidates_to_check:
        if existing_candidate.exists():
            try:
                existing_body = _FM_BLOCK_RE.sub(
                    "", existing_candidate.read_text(encoding="utf-8"), count=1
                ).strip()
                if existing_body == source_body:
                    result["status"] = "skip"
                    result["reason"] = "duplicate: existing snapshot has identical content"
                    result["target_path"] = str(existing_candidate)
                    return result
            except OSError:
                pass

    target_path = _resolve_collision_free_path(vault_project_dir, base_filename)
    result["target_path"] = str(target_path)

    # Build snapshot content
    snapshot_text = _build_snapshot_content(
        source_text, source_path, vault_root, source_commit, stale_risk, git_error
    )

    if dry_run:
        result["status"] = "dry_run"
        result["reason"] = f"dry-run: would write {target_path}"
        return result

    # Atomic write: .tmp then rename
    tmp_path = target_path.with_suffix(".tmp")
    try:
        tmp_path.write_text(snapshot_text, encoding="utf-8")
        os.rename(str(tmp_path), str(target_path))
    except OSError as exc:
        result["status"] = "error"
        result["reason"] = f"write failed: {exc}"
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return result

    result["status"] = "ok"
    result["reason"] = f"written: {target_path}"
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Sync external plan doc to vault snapshot")
    parser.add_argument("--source", help="Source file path (required unless --get-paths)")
    parser.add_argument(
        "--vault-root",
        default=str(Path("~/vault").expanduser()),
        help="Vault root (default: ~/vault)",
    )
    parser.add_argument(
        "--vault-link",
        default=None,
        help=".vault-link file path (default: CWD/.vault-link)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report only; do not write (default)",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        default=False,
        help="Actually write the snapshot (disables dry-run)",
    )
    parser.add_argument(
        "--skip-gate-check",
        action="store_true",
        default=False,
        help="Skip 2-layer opt-in gate (for explicit /save-plan-doc path)",
    )
    parser.add_argument(
        "--get-paths",
        action="store_true",
        default=False,
        help="Print effective include/exclude patterns (DEFAULT + .vault-link override) as JSON and exit.",
    )
    parser.add_argument(
        "--discover",
        metavar="PROJECT_ROOT",
        default=None,
        help="Scan PROJECT_ROOT and emit candidate plan-doc paths (one per line, project-root-relative).",
    )

    args = parser.parse_args()

    # --get-paths short-circuit: emit effective patterns and exit
    if args.get_paths:
        vault_link_path = Path(args.vault_link).expanduser() if args.vault_link else Path.cwd() / ".vault-link"
        vault_link = _load_vault_link(vault_link_path)
        include, exclude = _resolve_effective_patterns(vault_link)
        print(json.dumps({"include": include, "exclude": exclude}, ensure_ascii=False))
        sys.exit(0)

    # --discover short-circuit: emit candidate paths and exit
    if args.discover:
        project_root = Path(args.discover).expanduser().resolve()
        vault_link_path = Path(args.vault_link).expanduser() if args.vault_link else project_root / ".vault-link"
        vault_link = _load_vault_link(vault_link_path)
        for rel in _discover_candidates(project_root, vault_link):
            print(rel)
        sys.exit(0)

    if not args.source:
        parser.error("--source is required (omit only with --get-paths or --discover)")

    # VAULT_BRIDGE_DISABLE check
    if os.environ.get("VAULT_BRIDGE_DISABLE") == "1":
        print(json.dumps({
            "status": "skip",
            "reason": "VAULT_BRIDGE_DISABLE=1",
            "target_path": None,
            "source_commit": None,
            "source_stale_risk": False,
            "gate_l1": None,
            "gate_l2": None,
        }))
        sys.exit(0)

    source_path = Path(args.source).expanduser()
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path
    source_path = source_path.resolve()

    vault_root = Path(args.vault_root).expanduser().resolve()

    vault_link_path = Path(args.vault_link).expanduser() if args.vault_link else Path.cwd() / ".vault-link"
    vault_link = _load_vault_link(vault_link_path)

    dry_run = not args.enforce  # enforce overrides dry_run

    try:
        result = sync(
            source_path=source_path,
            vault_root=vault_root,
            vault_link=vault_link,
            dry_run=dry_run,
            skip_gate=args.skip_gate_check,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "error",
            "reason": f"unhandled exception: {exc}",
            "target_path": None,
            "source_commit": None,
            "source_stale_risk": False,
            "gate_l1": None,
            "gate_l2": None,
        }))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))

    exit_code = 0 if result["status"] in ("ok", "skip", "dry_run") else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
