#!/usr/bin/env python3
"""Emit retro's E8 promotion candidates from the vault-bridge manifest (#460).

Why this is not `cat manifest.json`: the harness persists a large Bash result to a
file and hands the model only a 2 KB PREVIEW. On the live vault that manifest is
121 KB / 168 files, and 2 KB holds THREE `path` entries (the third truncated
mid-string) — so retro was scanning 1.8% of the vault and reporting "no promotion
candidates" in a form indistinguishable from a real full scan. Filtering here keeps
the output far below the truncation line (37 B for a 0-candidate / 168-file vault),
and `scanned` makes the coverage claim checkable instead of assumed. Measured on the
live vault: 185 B / 1 candidate / 168 scanned.

Why the E8 condition is re-derived instead of reading the manifest's own
`promotion_candidate` flag: that flag ignores `status` (#435), so its only `true`
entry on the live vault is a `status: archived` note that retro's PROMOTE guard then
skips. Deriving the condition here keeps the consumer independent of the leaf flag's
meaning — this stays correct whether or not #435 lands.

Manifest fields are the CANDIDATE screen, not the verdict: retro PROMOTE re-reads each
note's own frontmatter afterwards. `status` is deliberately NOT screened here even though
it is part of the E8 condition — it is exactly the field PROMOTE re-reads, so screening a
possibly-stale manifest copy of it could silently drop a note that went back to `draft`
since the last refresh. That silent under-report is the failure class this script exists
to close; over-listing costs nothing, because PROMOTE drops the ineligible ones before the
user gate. `status` is still emitted, for the gate's display.

Usage:
    e8-candidates.py [MANIFEST_PATH]     # default: <vault root>/.vault-bridge/manifest.json

Output (stdout, one line). `scanned` is serialized FIRST so that if the list ever does grow
past the preview cut, the coverage number is the one thing that survives:
    {"scanned": N, "e8_candidates": [{path, references_in, access_count, status, type}, ...]}

Exit codes:
    0  manifest read and filtered (an empty candidate list is a normal result)
    3  manifest absent, unparseable, or malformed (a `files` entry that is not an object, a
       non-numeric threshold field, a bad env override) — the caller must skip PROMOTE and
       suggest `/vault-manifest-refresh`, NOT report "no candidates". There is no other
       failure exit: a crash would be a fourth branch retro has no instruction for.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROMOTABLE_TYPES = {"note", "decision"}   # v4 §3.3 — session/capture/plan never promote


def vault_root() -> Path:
    raw = (os.environ.get("VAULT_BRIDGE_VAULT_ROOT")
           or os.environ.get("VAULT_BRIDGE_VAULT_PATH")
           or "~/vault")
    return Path(os.path.expanduser(raw))


def e8_candidates(files: list[dict], refs: int, access: int) -> list[dict]:
    out = []
    for f in files:
        if f.get("type") not in PROMOTABLE_TYPES:
            continue
        if not (int(f.get("references_in") or 0) >= refs
                or int(f.get("access_count") or 0) >= access):
            continue
        out.append({k: f.get(k) for k in
                    ("path", "references_in", "access_count", "status", "type")})
    return out


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    path = Path(argv[0]) if argv else vault_root() / ".vault-bridge" / "manifest.json"
    # One try around read AND filter: a `files` entry that is not an object, or a
    # non-numeric refs/access/env value, must take the same exit-3 branch as an unreadable
    # file. Letting it traceback out at exit 1 would be a branch retro has no instruction for.
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        files = data["files"]
        if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
            raise TypeError("`files` is not a list of objects")
        refs = int(os.environ.get("VAULT_AUDIT_PROMOTION_REFS") or 3)
        access = int(os.environ.get("VAULT_AUDIT_PROMOTION_ACCESS") or 5)
        payload = {"scanned": len(files),
                   "e8_candidates": e8_candidates(files, refs, access)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"manifest unusable at {path}: {e}", file=sys.stderr)
        return 3

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
