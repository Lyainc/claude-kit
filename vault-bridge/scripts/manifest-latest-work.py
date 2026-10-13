#!/usr/bin/env python3
"""Emit vault-searcher Mode 1 (Session Restore) candidates from the manifest without a raw `Read`
of .vault-bridge/manifest.json (#866, sibling of manifest-domain-candidates.py).

Mode 1 used to Glob `session-*.md` and filter `status: active`; no current writer produces either
(vault-save writes `capture-*` / `{slug}` / `decision-*` and never writes `status:`). The latest
work document is found by manifest `type` and `mtime` instead.

Usage:
    manifest-latest-work.py [--vault-path VP] [--limit N] [MANIFEST_PATH]

Selection:
    - type in {capture, note, decision, session}   (what vault-save writes, plus `session` for
      legacy/daily-style notes). `wiki` and `discussion` are excluded: they are repo-transcending
      knowledge pages, not "what I was working on".
    - `_index.md` / `Home.md` hub pages are never candidates: housekeeping touches them.
    - with --vault-path (.vault-link scope): path == VP or startswith VP + "/" (directory
      boundary); surrounding slashes are stripped, so `notes/proj/` scopes like `notes/proj`.
    - legacy: an entry whose basename starts with `session-` or whose status == "active" is
      flagged `legacy_session: true` and selected even if its `type` is unknown (never wiki or
      discussion), so
      older vaults keep working. It sorts by mtime like any other entry, so a stale session note
      never outranks newer work.

Order: mtime descending, then path. Top --limit (default 5).

Output (stdout, one line, `candidate_count` first = total matches before --limit):
    {"candidate_count": N, "candidates": [{path,type,title,summary,status,mtime,legacy_session}, ...]}

Exit codes: 0 ok (empty list is a normal result); 3 manifest absent/unparseable/malformed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_WORK_TYPES = {"capture", "note", "decision", "session"}
_KNOWLEDGE_TYPES = {"wiki", "discussion"}
# Hub pages are touched by housekeeping, not by the work being restored.
_HUB_NAMES = {"_index.md", "Home.md", "home.md"}
_FIELDS = ("path", "type", "title", "summary", "status", "mtime")


def vault_root() -> Path:
    raw = (os.environ.get("VAULT_BRIDGE_VAULT_ROOT")
           or os.environ.get("VAULT_BRIDGE_VAULT_PATH")
           or "~/vault")
    return Path(os.path.expanduser(raw))


def _in_scope(entry: dict, vault_path: str) -> bool:
    if not vault_path:
        return True
    p = str(entry.get("path") or "")
    return p == vault_path or p.startswith(vault_path + "/")


def _selectable(entry: dict) -> bool:
    if str(entry.get("path") or "").rsplit("/", 1)[-1] in _HUB_NAMES:
        return False
    if entry.get("type") in _KNOWLEDGE_TYPES:
        return False
    return entry.get("type") in _WORK_TYPES or _is_legacy(entry)


def _is_legacy(entry: dict) -> bool:
    base = str(entry.get("path") or "").rsplit("/", 1)[-1]
    return base.startswith("session-") or entry.get("status") == "active"


def _mtime(entry: dict) -> float:
    try:
        return float(entry.get("mtime") or 0)
    except (TypeError, ValueError):
        return 0.0


def main(argv: list) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault-path", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("manifest_path", nargs="?", default=None)
    args = parser.parse_args(argv)

    vault_path = args.vault_path.strip().strip("/")
    path = Path(args.manifest_path) if args.manifest_path else vault_root() / ".vault-bridge" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data["files"]
        if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
            raise TypeError("`files` is not a list of objects")
        picked = [
            f for f in files
            if _in_scope(f, vault_path) and _selectable(f)
        ]
        picked.sort(key=lambda f: (-_mtime(f), str(f.get("path") or "")))
        candidates = [
            {**{k: f.get(k) for k in _FIELDS}, "legacy_session": _is_legacy(f)}
            for f in picked[: max(args.limit, 0)]
        ]
        payload = {"candidate_count": len(picked), "candidates": candidates}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"manifest unusable at {path}: {e}", file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
