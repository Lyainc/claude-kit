#!/usr/bin/env python3
"""
E12 wiki self-audit (staleness) unit regression (#330).

The DoD fixture run exercises E12 end-to-end (5 seeded stale wiki pages + 2 fresh
clean pages → seeded=5, fp=0). This file pins the SCOPING edges that the fixture
cannot isolate, all against `detect_stale_wiki`:

  - wiki-only scope: a stale `verified:` on a NON-wiki file (notes/ type:note) is
    never flagged — E12 is `wiki/` + `type:wiki`, not a vault-wide verified check.
  - type-only scope: a page under `wiki/` whose `type:` is not `wiki` is skipped.
  - staleness boundary: age == STALE_WIKI_DAYS is NOT stale (strict `>`); +1 is.
  - graceful skip: a wiki page with missing / unparseable `verified:` is skipped
    (staleness is uncomputable; the field is write-time auto-stamped so absence is
    a write-path bug, not a staleness signal — flagging it would be a false E12).

E12b (cross-page semantic contradiction) ships nowhere here — it is the deferred
`--deep` LLM path (mirrors E9c). No test asserts it because the deterministic
reference impl deliberately does not implement it.

Test-only: does NOT modify audit-validate.py.

Run: python3 obsidian-vault-manager/scripts/test/test-wiki-self-audit.py
  → "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import importlib.util
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_PY = _HERE / "audit-validate.py"

_spec = importlib.util.spec_from_file_location("audit_validate", _AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

detect_stale_wiki = _mod.detect_stale_wiki
STALE_WIKI_DAYS = _mod.STALE_WIKI_DAYS

# Fixed "today" so the boundary assertions are date-independent.
TODAY = date(2026, 7, 10)


def _rec(rel: str, **fm) -> dict:
    return {"rel": rel, "fm": fm}


def _verified_days_ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


def _flagged_paths(records: list) -> set:
    return {rel for rel, _ in detect_stale_wiki(records, TODAY)}


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def main() -> int:
    errors: list = []

    # 1. Stale wiki page → flagged.
    recs = [_rec("wiki/old.md", type="wiki", verified=_verified_days_ago(STALE_WIKI_DAYS + 30))]
    _assert(_flagged_paths(recs) == {"wiki/old.md"}, "stale wiki page is flagged", errors)

    # 2. Fresh wiki page → not flagged.
    recs = [_rec("wiki/fresh.md", type="wiki", verified=_verified_days_ago(1))]
    _assert(_flagged_paths(recs) == set(), "fresh wiki page is not flagged", errors)

    # 3. Boundary: age == STALE_WIKI_DAYS is NOT stale (strict >); +1 IS.
    recs = [_rec("wiki/edge.md", type="wiki", verified=_verified_days_ago(STALE_WIKI_DAYS))]
    _assert(_flagged_paths(recs) == set(), f"age == {STALE_WIKI_DAYS}d is not stale (strict >)", errors)
    recs = [_rec("wiki/edge.md", type="wiki", verified=_verified_days_ago(STALE_WIKI_DAYS + 1))]
    _assert(_flagged_paths(recs) == {"wiki/edge.md"}, f"age == {STALE_WIKI_DAYS + 1}d is stale", errors)

    # 4. wiki-only scope: a stale verified on a non-wiki file is NOT flagged.
    old = _verified_days_ago(STALE_WIKI_DAYS + 100)
    recs = [
        _rec("notes/note.md", type="note", verified=old),
        _rec("inbox/cap.md", type="capture", verified=old),
    ]
    _assert(_flagged_paths(recs) == set(), "stale verified on non-wiki file is not flagged", errors)

    # 5. type-only scope: a page under wiki/ whose type != wiki is skipped.
    recs = [_rec("wiki/stray.md", type="note", verified=old)]
    _assert(_flagged_paths(recs) == set(), "wiki/ page with type!=wiki is skipped", errors)

    # 6. Graceful skip: missing / unparseable verified is skipped, never flagged.
    recs = [
        _rec("wiki/no-verified.md", type="wiki"),                     # missing
        _rec("wiki/bad-verified.md", type="wiki", verified="soon"),   # unparseable
        _rec("wiki/list-verified.md", type="wiki", verified=["x"]),   # wrong shape
    ]
    _assert(_flagged_paths(recs) == set(), "missing/unparseable verified is skipped", errors)

    # 7. Mixed batch: only the genuinely-stale wiki page surfaces.
    recs = [
        _rec("wiki/stale-a.md", type="wiki", verified=_verified_days_ago(STALE_WIKI_DAYS + 1)),
        _rec("wiki/stale-b.md", type="wiki", verified=_verified_days_ago(STALE_WIKI_DAYS + 500)),
        _rec("wiki/fresh.md", type="wiki", verified=_verified_days_ago(0)),
        _rec("notes/decoy.md", type="note", verified=old),
    ]
    _assert(_flagged_paths(recs) == {"wiki/stale-a.md", "wiki/stale-b.md"},
            "mixed batch surfaces only stale wiki pages", errors)

    if errors:
        print(f"\nFAILED: {len(errors)} assertion(s) failed")
        return 1
    print("\nOK: all cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
