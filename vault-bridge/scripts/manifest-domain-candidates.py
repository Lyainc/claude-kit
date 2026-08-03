#!/usr/bin/env python3
"""Emit vault-searcher Mode 2 (Domain Context) manifest candidates without a raw `Read` of
.vault-bridge/manifest.json (#523, mirrors #468's obsidian-vault-manager/scripts/manifest-wiki-match.py).

vault-searcher.md used to `Read` the whole manifest file. On a real vault (180+ entries / 129 KB /
3,338 lines pretty-printed) that overflows the Read tool's 2,000-line default cap, and because
generate-manifest.py sorts entries by `rel_path`, `wiki/` (alphabetically last) landed 100% inside
the truncated tail — the "wiki/ is always included" contract (vault-searcher.md L94, #272) silently
lost every entry. This script reads the full file on disk directly (untruncated) and emits only the
narrow field set + entry subset this mode actually needs.

Usage:
    manifest-domain-candidates.py [--domain DOM] [--vault-path VP] [MANIFEST_PATH]

Selection (OR'd, matches vault-searcher.md Mode 2 Manifest-First Protocol):
    - type == "wiki"                     (always included — #272, L94 contract)
    - path == --vault-path, or path startswith --vault-path + "/"
                                          (.vault-link project scoping, directory-boundary safe —
                                           a raw string prefix would let "notes/api" match the
                                           sibling "notes/api-legacy/...")
    - any tag, or the workstream field, contains --domain
                                          (substring, case-insensitive; comma-separated domains
                                           are split and OR'd, matching the standard-scan
                                           fallback's "query each individually" handling)
    - status == "active"

Output (stdout, one line). `candidate_count` is serialized FIRST so the coverage count survives
even if the entry list itself is ever truncated downstream by the caller's tool-output cap:
    {"candidate_count": N, "candidates": [{path,type,title,summary,tags,status,workstream,mtime,
                                            recent_commits,references_in}, ...]}

Exit codes:
    0  manifest read and filtered (an empty candidate list is a normal result — e.g. a fresh vault)
    3  manifest absent, unparseable, or malformed — caller falls back to the standard full-scan
       procedure. A truncation-avoided read failure must never report "0 candidates" as if it
       were a real empty vault.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_FIELDS = ("path", "type", "title", "summary", "tags", "status", "workstream",
           "mtime", "recent_commits", "references_in")


def vault_root() -> Path:
    raw = (os.environ.get("VAULT_BRIDGE_VAULT_ROOT")
           or os.environ.get("VAULT_BRIDGE_VAULT_PATH")
           or "~/vault")
    return Path(os.path.expanduser(raw))


def _matches(entry: dict, domain: str, vault_path: str) -> bool:
    if entry.get("type") == "wiki":
        return True
    if vault_path:
        entry_path = str(entry.get("path") or "")
        if entry_path == vault_path or entry_path.startswith(vault_path + "/"):
            return True
    if domain:
        tags = entry.get("tags") or []
        domains = [d.strip().lower() for d in domain.split(",") if d.strip()]
        if any(dom in str(t).lower() for t in tags for dom in domains):
            return True
        workstream = str(entry.get("workstream") or "").lower()
        if workstream and any(dom in workstream for dom in domains):
            return True
    if entry.get("status") == "active":
        return True
    return False


def main(argv: list) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="")
    parser.add_argument("--vault-path", default="")
    parser.add_argument("manifest_path", nargs="?", default=None)
    args = parser.parse_args(argv)

    path = Path(args.manifest_path) if args.manifest_path else vault_root() / ".vault-bridge" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data["files"]
        if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
            raise TypeError("`files` is not a list of objects")
        candidates = [
            {k: f.get(k) for k in _FIELDS}
            for f in files
            if _matches(f, args.domain, args.vault_path)
        ]
        payload = {"candidate_count": len(candidates), "candidates": candidates}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"manifest unusable at {path}: {e}", file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
