#!/usr/bin/env python3
"""Emit `type: wiki` manifest entries (path/title/tags) for wiki DEDUP matching, without a raw
`cat` (#468, mirrors #460's feedback-loop/scripts/e8-candidates.py). Same 2 KB harness-preview
truncation risk as audit's manifest read — worse here, since DEDUP needs a real field
(title + tags) per matching entry rather than two top-level scalars, so more of the 121 KB
manifest has to survive the round trip.

Usage:
    manifest-wiki-match.py [MANIFEST_PATH]   # default: <vault root>/.vault-bridge/manifest.json

Output (stdout, one line). `scanned` is serialized FIRST so the coverage count survives even if
the entry list itself ever grows past the preview cut:
    {"scanned": N, "wiki_entries": [{path, title, tags}, ...]}

Exit codes:
    0  manifest read and filtered (an empty wiki_entries list is a normal result — a vault
       with no wiki/ pages yet)
    3  manifest absent, unparseable, or malformed — the caller falls back to `ls ~/vault/wiki/`
       and slug-only matching (wiki/SKILL.md Phase 3), the SAME fallback already used for a
       hard-absent manifest. A truncation-avoided read failure must never report "0 pages".
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def vault_root() -> Path:
    raw = (os.environ.get("VAULT_BRIDGE_VAULT_ROOT")
           or os.environ.get("VAULT_BRIDGE_VAULT_PATH")
           or "~/vault")
    return Path(os.path.expanduser(raw))


def wiki_entries(files: list) -> list:
    return [{"path": f.get("path"), "title": f.get("title"), "tags": f.get("tags") or []}
            for f in files if f.get("type") == "wiki"]


def main(argv: list) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    path = Path(argv[0]) if argv else vault_root() / ".vault-bridge" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data["files"]
        if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
            raise TypeError("`files` is not a list of objects")
        payload = {"scanned": len(files), "wiki_entries": wiki_entries(files)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"manifest unusable at {path}: {e}", file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
