#!/usr/bin/env python3
"""
E12c wiki near-duplicate unit regression (#698, #645 F1 follow-up).

The DoD fixture run exercises E12c end-to-end (1 seeded near-dup pair, distinct
`dup-fixture` tag so it never exact-tag-matches the E12a/companion/clean seed
groups → seeded_detected.E12_wiki_near_dup == 1, fp_on_clean == 0). This file
pins the SCOPING and MATCHING edges that fixture cannot isolate, all against
`detect_wiki_near_dup`:

  - exact tag match required: an overlapping-but-not-identical tags set does NOT
    pair, even with fully overlapping title tokens.
  - title token overlap required: identical tags alone (e.g. two pages both
    tagged just `[wiki]`) do NOT pair without a shared title token.
  - numeric-only filename segments carry no title signal (a bare "-001"/"-002"
    suffix never creates a false match).
  - case-insensitive tag/token comparison.
  - wiki/+type:wiki scope guard (same `_wiki_pages` filter as E12a/companion) —
    a non-wiki file or a wiki/ file with type != wiki is never a candidate.
  - self-pairs are never reported, and a pair is reported exactly once with
    rel_a < rel_b (never both orders).
  - a three-way match reports every pairing, not just adjacent ones.

E12b (cross-page semantic contradiction) ships nowhere here — it is the
deferred `--deep` LLM path (mirrors E9c). No test asserts it because the
deterministic reference impl deliberately does not implement it.

Test-only: does NOT modify audit-validate.py.

Run: python3 obsidian-vault-manager/scripts/test/test-wiki-near-dup.py
  → "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_PY = _HERE / "audit-validate.py"

_spec = importlib.util.spec_from_file_location("audit_validate", _AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

detect_wiki_near_dup = _mod.detect_wiki_near_dup


def _rec(rel: str, **fm) -> dict:
    return {"rel": rel, "fm": fm}


def _pairs(records: list) -> set:
    return {(a, b) for a, b, _ in detect_wiki_near_dup(records)}


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def main() -> int:
    errors: list = []

    # 1. Same tags + overlapping title token → flagged, sorted (rel_a < rel_b).
    recs = [
        _rec("wiki/defuddle.md", type="wiki", tags=["wiki", "defuddle"]),
        _rec("wiki/defuddle-cli.md", type="wiki", tags=["wiki", "defuddle"]),
    ]
    _assert(_pairs(recs) == {("wiki/defuddle-cli.md", "wiki/defuddle.md")},
            "same tags + overlapping title token is flagged, sorted pair order", errors)

    # 2. Different domain (no title token overlap, no tag overlap) → not flagged.
    recs = [
        _rec("wiki/defuddle.md", type="wiki", tags=["wiki", "defuddle"]),
        _rec("wiki/obsidian-bases.md", type="wiki", tags=["wiki", "obsidian"]),
    ]
    _assert(_pairs(recs) == set(), "unrelated wiki pages are not flagged", errors)

    # 3. Exact tag match required: overlapping-but-not-identical tags do NOT pair,
    # even with fully overlapping title tokens.
    recs = [
        _rec("wiki/defuddle.md", type="wiki", tags=["wiki", "defuddle"]),
        _rec("wiki/defuddle-cli.md", type="wiki", tags=["wiki", "defuddle", "cli-tools"]),
    ]
    _assert(_pairs(recs) == set(),
            "overlapping-but-not-identical tags does not pair (exact match required)", errors)

    # 4. Title token overlap required: identical tags alone do not pair without a
    # shared title token.
    recs = [
        _rec("wiki/alpha.md", type="wiki", tags=["wiki", "shared"]),
        _rec("wiki/beta.md", type="wiki", tags=["wiki", "shared"]),
    ]
    _assert(_pairs(recs) == set(),
            "identical tags without shared title tokens does not pair", errors)

    # 5. Numeric-only filename segments carry no title signal.
    recs = [
        _rec("wiki/audit-e12-stale-001.md", type="wiki", tags=["wiki", "domain"]),
        _rec("wiki/audit-e12-stale-002.md", type="wiki", tags=["wiki", "domain"]),
    ]
    _assert(_pairs(recs) == {("wiki/audit-e12-stale-001.md", "wiki/audit-e12-stale-002.md")},
            "shared non-numeric tokens (audit/e12/stale) still pair — numeric suffix "
            "alone would not, but this pair also shares real words", errors)
    recs = [
        _rec("wiki/topic-001.md", type="wiki", tags=["wiki", "domain"]),
        _rec("wiki/other-002.md", type="wiki", tags=["wiki", "domain"]),
    ]
    _assert(_pairs(recs) == set(),
            "numeric-only shared segment ('001' vs '002' differ anyway) does not "
            "manufacture a match on its own", errors)

    # 6. Case-insensitive tag/token comparison.
    recs = [
        _rec("wiki/Defuddle.md", type="wiki", tags=["Wiki", "Defuddle"]),
        _rec("wiki/DEFUDDLE-CLI.md", type="wiki", tags=["wiki", "defuddle"]),
    ]
    _assert(_pairs(recs) == {("wiki/DEFUDDLE-CLI.md", "wiki/Defuddle.md")},
            "tag and token comparison is case-insensitive", errors)

    # 7. wiki/+type:wiki scope guard — a non-wiki file or a wiki/ file with
    # type != wiki is never a candidate, even with matching tags/tokens.
    recs = [
        _rec("notes/defuddle.md", type="note", tags=["wiki", "defuddle"]),
        _rec("wiki/defuddle-cli.md", type="wiki", tags=["wiki", "defuddle"]),
    ]
    _assert(_pairs(recs) == set(), "a non-wiki file is never a near-dup candidate", errors)
    recs = [
        _rec("wiki/defuddle.md", type="note", tags=["wiki", "defuddle"]),
        _rec("wiki/defuddle-cli.md", type="wiki", tags=["wiki", "defuddle"]),
    ]
    _assert(_pairs(recs) == set(),
            "a wiki/ file with type != wiki is never a near-dup candidate", errors)

    # 8. Self-pairs are never reported.
    recs = [_rec("wiki/defuddle.md", type="wiki", tags=["wiki", "defuddle"])]
    _assert(_pairs(recs) == set(), "a single page never pairs with itself", errors)

    # 9. A three-way match reports every pairing.
    recs = [
        _rec("wiki/defuddle.md", type="wiki", tags=["wiki", "defuddle"]),
        _rec("wiki/defuddle-cli.md", type="wiki", tags=["wiki", "defuddle"]),
        _rec("wiki/defuddle-plugin.md", type="wiki", tags=["wiki", "defuddle"]),
    ]
    _assert(_pairs(recs) == {
        ("wiki/defuddle-cli.md", "wiki/defuddle.md"),
        ("wiki/defuddle-plugin.md", "wiki/defuddle.md"),
        ("wiki/defuddle-cli.md", "wiki/defuddle-plugin.md"),
    }, "a three-way match reports every pairing (3 pairs from 3 pages)", errors)

    # 10. Missing/empty tags never pairs (would otherwise trivially match another
    # untagged page).
    recs = [
        _rec("wiki/defuddle.md", type="wiki"),
        _rec("wiki/defuddle-cli.md", type="wiki"),
    ]
    _assert(_pairs(recs) == set(), "wiki pages with no tags never pair", errors)

    if errors:
        print(f"\nFAILED: {len(errors)} assertion(s) failed")
        return 1
    print("\nOK: all cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
