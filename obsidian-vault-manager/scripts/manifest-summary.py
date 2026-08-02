#!/usr/bin/env python3
"""Emit the audit REPORT header's manifest summary without a raw `cat` (#468, mirrors #460's
feedback-loop/scripts/e8-candidates.py). The harness truncates large Bash output to a 2 KB
preview before the model ever sees it — a raw `cat` of .vault-bridge/manifest.json (121 KB /
168 files on a real vault) silently degrades to whichever ~3 entries survive the cut,
indistinguishable from a legitimately small manifest. This script reads the full file on disk
(untruncated) and prints only the two scalar fields the audit REPORT header actually uses.

Usage:
    manifest-summary.py [MANIFEST_PATH]   # default: <vault root>/.vault-bridge/manifest.json

Output (stdout, one line): {"file_count": N, "generated_at": "..."}

Exit codes:
    0  manifest read and parsed
    3  manifest absent, unparseable, or missing a required field — caller sets
       manifest_summary to null (same as before); the exit code exists so "absent" is never
       confused with "parsed to an unexpectedly empty value".
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


def main(argv: list) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    path = Path(argv[0]) if argv else vault_root() / ".vault-bridge" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = {"file_count": data["file_count"], "generated_at": data["generated_at"]}
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"manifest unusable at {path}: {e}", file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
