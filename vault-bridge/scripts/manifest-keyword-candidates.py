#!/usr/bin/env python3
"""Emit vault-searcher Mode 3 (Keyword Search) manifest pre-filter candidates without a raw
`Read` of .vault-bridge/manifest.json (#523, sibling of manifest-domain-candidates.py, mirrors
#468's manifest-wiki-match.py, this same directory since #645).

Same defect class: an unbounded `Read` of the full manifest overflows the Read tool's 2,000-line
cap on a real vault, and because generate-manifest.py sorts `wiki/` alphabetically last, 100% of
wiki/ entries fell in the truncated tail — a keyword search could never surface a compiled wiki
page that matched, even though it was never excluded by the match logic itself.

Usage:
    manifest-keyword-candidates.py KEYWORD [MANIFEST_PATH]

Selection: KEYWORD as a case-insensitive substring of `title` or `summary`.

Output (stdout, one line). `candidate_count` is serialized FIRST so the coverage count survives
even if the entry list itself is ever truncated downstream by the caller's tool-output cap:
    {"candidate_count": N, "candidates": [{path,type,title,summary,tags,mtime,
                                            recent_commits,references_in}, ...]}

Exit codes:
    0  manifest read and filtered (an empty candidate list means "fall through to the adaptive
       mdfind/grep scan", per vault-searcher.md Mode 3 step 1 — not an error)
    3  manifest absent, unparseable, or malformed — same fallback as an empty result, but
       distinguishable in stderr for debugging; never silently reported as "0 matches".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_FIELDS = ("path", "type", "title", "summary", "tags", "mtime", "recent_commits", "references_in")


def vault_root() -> Path:
    raw = (os.environ.get("VAULT_BRIDGE_VAULT_ROOT")
           or os.environ.get("VAULT_BRIDGE_VAULT_PATH")
           or "~/vault")
    return Path(os.path.expanduser(raw))


def main(argv: list) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword")
    parser.add_argument("manifest_path", nargs="?", default=None)
    args = parser.parse_args(argv)

    keyword = args.keyword.lower()
    path = Path(args.manifest_path) if args.manifest_path else vault_root() / ".vault-bridge" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data["files"]
        if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
            raise TypeError("`files` is not a list of objects")
        candidates = [
            {k: f.get(k) for k in _FIELDS}
            for f in files
            if keyword in str(f.get("title") or "").lower() or keyword in str(f.get("summary") or "").lower()
        ]
        payload = {"candidate_count": len(candidates), "candidates": candidates}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"manifest unusable at {path}: {e}", file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
