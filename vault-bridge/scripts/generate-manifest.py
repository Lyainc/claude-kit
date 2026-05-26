#!/usr/bin/env python3
"""
Vault Manifest Generator — vault-bridge W10 Phase A
Generates ~/vault/.vault-bridge/manifest.json from vault .md files.

Usage:
  python3 generate-manifest.py [--vault-root PATH] [--force] [--out PATH]

Stdout (always JSON):
  {"generated": N, "updated": N, "removed": N, "elapsed_ms": N}

Exit codes:
  0 — success
  1 — vault_root does not exist
  2 — write failure
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCHEMA_VERSION = 2  # v2: type opt-in (v4 §2.2); v1 manifests invalidated on first run.
SUMMARY_MAX_CHARS = 400
EXCLUDED_DIRS = {".vault-bridge", ".claude", "assets", ".git"}


def _default_vault_root() -> str:
    """Resolve the default vault root with 3-level priority:
    1. VAULT_BRIDGE_VAULT_ROOT  — explicit env override (CI / runtime)
    2. VAULT_BRIDGE_VAULT_PATH  — userConfig value injected by Claude Code
    3. ~/vault                  — built-in default

    NOTE: keep in sync with plan-doc-syncer.py:_default_vault_root().
    """
    raw = os.environ.get("VAULT_BRIDGE_VAULT_ROOT") or \
          os.environ.get("VAULT_BRIDGE_VAULT_PATH", "")
    return str(Path(raw).expanduser()) if raw else str(Path.home() / "vault")


# ---------------------------------------------------------------------------
# Frontmatter parser (no external deps — regex + manual line parsing)
# ---------------------------------------------------------------------------

_FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FLOW_ARRAY_RE = re.compile(r"^\[([^\]]*)\]$")


def _parse_scalar(value: str) -> object:
    """Parse a YAML scalar string into a Python value."""
    v = value.strip()
    if not v:
        return None
    # Flow-style array: [a, b, c]
    m = _FLOW_ARRAY_RE.match(v)
    if m:
        inner = m.group(1)
        return [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
    # Quoted scalars: strip before bool/int coercion so `"true"` → True
    # (parity with plan-doc-syncer.py _parse_scalar).
    if len(v) >= 2 and (
        (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")
    ):
        v = v[1:-1]
    # Boolean
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    # Integer
    try:
        return int(v)
    except ValueError:
        pass
    return v


def _parse_frontmatter(text: str) -> dict:
    """
    Extract YAML frontmatter from a markdown string.
    Returns a dict of top-level scalar / flow-array values.
    Supports block-sequence lists (lines starting with '- ').
    """
    m = _FM_BLOCK_RE.match(text)
    if not m:
        return {}

    result = {}
    current_key = None
    current_list = None

    for raw_line in m.group(1).splitlines():
        # Block-sequence item
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            item = raw_line.lstrip("- ").strip().strip("\"'")
            if current_key is not None:
                if current_list is None:
                    # Preserve any inline scalar so `key: foo\n  - bar` yields
                    # ["foo", "bar"] (parity with plan-doc-syncer.py).
                    existing = result.get(current_key)
                    if isinstance(existing, list):
                        current_list = existing
                    else:
                        current_list = []
                        if existing not in (None, ""):
                            current_list.append(existing)
                        result[current_key] = current_list
                current_list.append(item)
            continue

        # Key: value line
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
                # Value may follow as block sequence on next lines
                result[key] = None
            else:
                result[key] = parsed

    return result


# ---------------------------------------------------------------------------
# Content extractors
# ---------------------------------------------------------------------------

def _strip_frontmatter(text: str) -> str:
    """Return text with leading frontmatter block removed."""
    return _FM_BLOCK_RE.sub("", text, count=1).lstrip("\n")


def _extract_title(text: str, fallback: str) -> str:
    """Return first H1 heading text, or fallback (stem of filename)."""
    body = _strip_frontmatter(text)
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


_HR_LINES = {"---", "***", "___"}
_CALLOUT_HEADER_RE = re.compile(r"^>\s*\[![A-Za-z]+\][^\n]*$")
_LIST_ITEM_RE = re.compile(r"^([-*+]\s|\d+[.)]\s)")


def _is_prose_skipline(stripped: str) -> bool:
    """
    True for markup that should not start a summary paragraph.

    Skipped: headings (#), horizontal rules, list/task items, callout headers
    (`> [!type] ...`).
    Allowed: regular blockquote content (`> ...`) — Obsidian callouts are
    structurally a blockquote and often contain the most informative copy
    for held/draft files.
    """
    if not stripped:
        return False
    if stripped.startswith("#") or stripped in _HR_LINES:
        return True
    if _LIST_ITEM_RE.match(stripped):
        return True
    if _CALLOUT_HEADER_RE.match(stripped):
        return True
    return False


def _strip_blockquote_marker(stripped: str) -> str:
    """Strip leading `>` (and optional space) used by Obsidian callouts."""
    if stripped.startswith(">"):
        return stripped[1:].lstrip()
    return stripped


def _extract_summary(text: str) -> str:
    """
    Return the first prose paragraph after frontmatter, capped at SUMMARY_MAX_CHARS.

    Skips leading non-prose markup (headings, horizontal rules, list items,
    callout headers, fenced code blocks) so the summary reflects actual body
    content rather than the H1 echo. Callout body lines are kept (with `>`
    stripped) because they carry meaningful copy in held/draft notes.
    This is what vault-searcher uses to triage notes without opening them.
    """
    body = _strip_frontmatter(text)
    paragraph_lines: list[str] = []
    in_paragraph = False
    in_fence = False

    for line in body.splitlines():
        stripped = line.strip()

        # Track ``` / ~~~ fenced code blocks; never include their contents.
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if in_paragraph:
                break
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if stripped == "":
            if in_paragraph:
                break
            continue

        if _is_prose_skipline(stripped):
            if in_paragraph:
                break
            continue

        in_paragraph = True
        paragraph_lines.append(_strip_blockquote_marker(stripped))

    summary = " ".join(paragraph_lines).strip()
    if len(summary) > SUMMARY_MAX_CHARS:
        summary = summary[:SUMMARY_MAX_CHARS]
    return summary


# ---------------------------------------------------------------------------
# File entry builder
# ---------------------------------------------------------------------------

def _build_entry(rel_path: str, abs_path: Path, vault_root: Path) -> dict:
    """Parse a single .md file and return a manifest entry dict."""
    stat = abs_path.stat()
    mtime = int(stat.st_mtime)
    size_bytes = stat.st_size

    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"WARNING: cannot read {abs_path}: {exc}", file=sys.stderr)
        text = ""

    fm = _parse_frontmatter(text)
    fallback_title = abs_path.stem
    title = _extract_title(text, fallback_title)
    summary = _extract_summary(text)

    entry: dict = {
        "path": rel_path,
        "type": fm.get("type") or "unknown",
        "tags": fm.get("tags") or [],
        "title": title,
        "summary": summary,
        "mtime": mtime,
        "size_bytes": size_bytes,
    }

    # Optional fields — only include when present in frontmatter
    status = fm.get("status")
    if status:
        entry["status"] = str(status)

    workstream = fm.get("workstream")
    if workstream:
        entry["workstream"] = str(workstream)

    return entry


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def _load_existing_manifest(out_path: Path) -> dict | None:
    """Load existing manifest JSON; return None if absent or corrupt."""
    if not out_path.exists():
        return None
    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _manifest_mtime(out_path: Path) -> float:
    """Return mtime of manifest file, or 0.0 if absent."""
    try:
        return out_path.stat().st_mtime
    except OSError:
        return 0.0


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def generate(vault_root: Path, out_path: Path, force: bool) -> dict:
    """
    Generate or incrementally update manifest.json.

    Returns stats dict: {generated, updated, removed, elapsed_ms}
    """
    t0 = time.monotonic()

    # Collect all .md paths (relative to vault_root)
    md_files: dict[str, Path] = {}  # rel_path -> abs_path
    for abs_path in vault_root.rglob("*.md"):
        # Skip excluded directories (any component matches)
        if any(part in EXCLUDED_DIRS for part in abs_path.parts):
            continue
        try:
            rel = str(abs_path.relative_to(vault_root))
        except ValueError:
            continue
        md_files[rel] = abs_path

    existing = None if force else _load_existing_manifest(out_path)

    if existing is None:
        # Full scan
        files_list = []
        for rel, abs_path in sorted(md_files.items()):
            try:
                entry = _build_entry(rel, abs_path, vault_root)
                if entry["type"] == "unknown":
                    continue  # type opt-in (v4 §2.2)
                files_list.append(entry)
            except Exception as exc:
                print(f"WARNING: skipping {rel}: {exc}", file=sys.stderr)

        manifest = {
            "generated_at": _iso_now(),
            "vault_root": str(vault_root),
            "schema_version": SCHEMA_VERSION,
            "file_count": len(files_list),
            "files": files_list,
        }
        updated_count = 0
        removed_count = 0
        processed_count = len(files_list)
    else:
        # Incremental update: compare mtimes
        manifest_mtime = _manifest_mtime(out_path)

        existing_by_path: dict[str, dict] = {e["path"]: e for e in existing.get("files", [])}

        updated_count = 0
        removed_count = 0
        new_files_list: list[dict] = []

        for rel, abs_path in sorted(md_files.items()):
            try:
                file_mtime = abs_path.stat().st_mtime
            except OSError:
                continue

            if rel in existing_by_path and file_mtime <= manifest_mtime:
                existing_entry = existing_by_path[rel]
                if existing_entry.get("type", "unknown") == "unknown":
                    continue  # safety net for manually-edited v2 manifests
                new_files_list.append(existing_entry)
            else:
                try:
                    entry = _build_entry(rel, abs_path, vault_root)
                    if entry["type"] == "unknown":
                        continue  # type opt-in (v4 §2.2)
                    new_files_list.append(entry)
                    if rel in existing_by_path:
                        updated_count += 1
                except Exception as exc:
                    print(f"WARNING: skipping {rel}: {exc}", file=sys.stderr)

        # Detect removed files
        current_paths = set(md_files.keys())
        removed_count = sum(1 for p in existing_by_path if p not in current_paths)

        processed_count = len(new_files_list)

        manifest = {
            "generated_at": _iso_now(),
            "vault_root": str(vault_root),
            "schema_version": SCHEMA_VERSION,
            "file_count": processed_count,
            "files": new_files_list,
        }

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    # NOTE: stats key stays "generated" for back-compat with README/consumers;
    # this counts every file in the resulting manifest, not just newly added ones.
    return manifest, {
        "generated": processed_count,
        "updated": updated_count,
        "removed": removed_count,
        "elapsed_ms": elapsed_ms,
    }


def _iso_now() -> str:
    """Return current local time as ISO 8601 string with UTC offset."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    return now.isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate vault manifest JSON")
    parser.add_argument(
        "--vault-root",
        default=_default_vault_root(),
        help="Path to vault root (default: VAULT_BRIDGE_VAULT_ROOT > VAULT_BRIDGE_VAULT_PATH > ~/vault)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore staleness check; regenerate from scratch",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path (default: {vault-root}/.vault-bridge/manifest.json)",
    )
    args = parser.parse_args()

    vault_root = Path(args.vault_root).expanduser().resolve()
    if not vault_root.is_dir():
        print(f"ERROR: vault_root does not exist: {vault_root}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out).expanduser().resolve() if args.out else vault_root / ".vault-bridge" / "manifest.json"

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        manifest, stats = generate(vault_root, out_path, args.force)
    except Exception as exc:
        print(f"ERROR: generation failed: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: write failed ({out_path}): {exc}", file=sys.stderr)
        sys.exit(2)

    # Stdout: machine-readable stats for hook consumption
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
