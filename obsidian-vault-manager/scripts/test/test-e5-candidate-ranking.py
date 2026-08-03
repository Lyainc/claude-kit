#!/usr/bin/env python3
"""
E5 orphan connection-candidate ranking regression (#495).

Replaces E5's raw shared-tag-COUNT ranking with a rarity-weighted score
(score(P,Q) = Sum 1/log(1+df(t)), df = vault-wide notes/ tag document
frequency, E9a-style aggregation) so a tag common across the vault (e.g.
every note tagged `note`) doesn't manufacture a "connection" on its own.
Pins three guarantees the #495 change makes:

  1. A candidate sharing only a common/dominant tag ranks BELOW one sharing
     a rare tag (score_e5_candidate + rank_e5_candidates ordering).
  2. When even the best-scoring candidate misses E5_MIN_CANDIDATE_SCORE,
     rank_e5_candidates returns ([], True) rather than force-filling
     E5_CANDIDATE_TOP_N with noise (the "dominant tag only" floor case).
  3. That floor-gated [] is distinguishable from the "no note shares any tag
     with this orphan at all" [] case (rank_e5_candidates' 2nd return value) —
     classify() renders a different, accurate detail message for each; the two
     must never collapse into one flag.

Drives the pure functions (_e5_tag_df / score_e5_candidate /
rank_e5_candidates) directly against synthetic (rel, frozenset(tags)) index
entries — mirrors test-vocabulary-pairs.py PART A's synthetic-fm_records
approach; no on-disk fixture needed since E5 ranking has no I/O of its own.

Run: python3 obsidian-vault-manager/scripts/test/test-e5-candidate-ranking.py
  -> "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import importlib.util
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_PY = _HERE / "audit-validate.py"

_spec = importlib.util.spec_from_file_location("audit_validate", _AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_e5_tag_df = _mod._e5_tag_df
score_e5_candidate = _mod.score_e5_candidate
rank_e5_candidates = _mod.rank_e5_candidates
E5_CANDIDATE_TOP_N = _mod.E5_CANDIDATE_TOP_N
E5_MIN_CANDIDATE_SCORE = _mod.E5_MIN_CANDIDATE_SCORE


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}", file=sys.stderr)
        errors.append(desc)


def _entry(rel: str, tags) -> tuple:
    return (rel, frozenset(tags))


def case_rare_tag_outranks_common_tag(errors: list) -> None:
    """A candidate sharing only a rare tag outranks candidates sharing only a common tag.

    Filler files (needed to inflate df(common)) inevitably also share the
    "common" tag with the orphan, so they show up as (weaker) candidates too —
    E5_CANDIDATE_TOP_N caps the pool at 3, dropping the weakest of the tied
    common-tag matches. What's pinned is the ORDER: rare-tag first.
    """
    index = [
        _entry("notes/orphan.md", ["common", "rare"]),
        _entry("notes/cand-common.md", ["common"]),
        _entry("notes/cand-rare.md", ["rare"]),
        # Filler files inflate df(common) to 4 without touching df(rare) (=2).
        _entry("notes/filler-1.md", ["common"]),
        _entry("notes/filler-2.md", ["common"]),
    ]
    tag_df = _e5_tag_df(index)
    _assert(
        tag_df["common"] == 4 and tag_df["rare"] == 2,
        f"df: common=4 rare=2 (got common={tag_df['common']} rare={tag_df['rare']})",
        errors,
    )

    candidates, floor_gated = rank_e5_candidates(
        "notes/orphan.md", frozenset({"common", "rare"}), index, tag_df,
    )
    _assert(
        len(candidates) == E5_CANDIDATE_TOP_N,
        f"4 candidates clear the floor, top-{E5_CANDIDATE_TOP_N} cap applies "
        f"(got {len(candidates)})",
        errors,
    )
    _assert(not floor_gated, "candidates present -> floor_gated is False", errors)
    if candidates:
        _assert(
            candidates[0]["path"] == "notes/cand-rare.md",
            f"rare-tag candidate ranks first, ahead of every common-tag-only match "
            f"(got order {[c['path'] for c in candidates]})",
            errors,
        )
        _assert(
            all(c["shared_tags"] == ["common"] for c in candidates[1:]),
            "every candidate after the rare-tag one connects only via the common tag",
            errors,
        )


def case_boundary_dominant_tag_floor(errors: list) -> None:
    """df=6 (score ~0.514) clears E5_MIN_CANDIDATE_SCORE; df=7 (score ~0.481) doesn't."""
    index6 = [_entry("notes/orphan.md", ["tag6"]), _entry("notes/cand.md", ["tag6"])]
    index6 += [_entry(f"notes/filler-{i}.md", ["tag6"]) for i in range(4)]
    tag_df6 = _e5_tag_df(index6)
    _assert(tag_df6["tag6"] == 6, f"df(tag6) == 6 (got {tag_df6['tag6']})", errors)
    score6 = score_e5_candidate(frozenset({"tag6"}), tag_df6)
    _assert(
        score6 >= E5_MIN_CANDIDATE_SCORE,
        f"df=6 single-tag score {score6:.4f} clears the {E5_MIN_CANDIDATE_SCORE} floor",
        errors,
    )
    # index6 has 5 files sharing tag6 with the orphan (cand + 4 df-fillers) —
    # all score identically at df=6, so the top-N cap (not the floor) trims the pool.
    candidates6, floor_gated6 = rank_e5_candidates("notes/orphan.md", frozenset({"tag6"}), index6, tag_df6)
    _assert(
        len(candidates6) == E5_CANDIDATE_TOP_N,
        f"df=6: pool survives the floor, top-{E5_CANDIDATE_TOP_N} cap applies "
        f"(got {len(candidates6)})",
        errors,
    )
    _assert(not floor_gated6, "df=6: pool survives -> floor_gated is False", errors)

    index7 = index6 + [_entry("notes/filler-4.md", ["tag6"])]
    tag_df7 = _e5_tag_df(index7)
    _assert(tag_df7["tag6"] == 7, f"df(tag6) == 7 (got {tag_df7['tag6']})", errors)
    score7 = score_e5_candidate(frozenset({"tag6"}), tag_df7)
    _assert(
        score7 < E5_MIN_CANDIDATE_SCORE,
        f"df=7 single-tag score {score7:.4f} misses the {E5_MIN_CANDIDATE_SCORE} floor",
        errors,
    )
    candidates7, floor_gated7 = rank_e5_candidates("notes/orphan.md", frozenset({"tag6"}), index7, tag_df7)
    _assert(candidates7 == [], f"df=7: best score below floor -> [] (got {candidates7})", errors)
    _assert(floor_gated7, "df=7: best score below floor -> floor_gated is True", errors)


def case_dominant_common_tag_drops_to_empty(errors: list) -> None:
    """All candidates share only ONE dominant vault-wide tag -> [] not top-3 noise."""
    index = [_entry("notes/orphan.md", ["note"])]
    index += [_entry(f"notes/cand-{i}.md", ["note"]) for i in range(6)]  # df=7
    tag_df = _e5_tag_df(index)
    candidates, floor_gated = rank_e5_candidates("notes/orphan.md", frozenset({"note"}), index, tag_df)
    _assert(
        candidates == [],
        f"dominant single-tag pool -> [] instead of forced top-3 (got {candidates})",
        errors,
    )
    _assert(
        floor_gated,
        "dominant single-tag pool: floor_gated is True (shared tags existed, all too weak)",
        errors,
    )


def case_empty_orphan_tags(errors: list) -> None:
    """Empty orphan tags -> [] immediately, no candidate computation attempted."""
    index = [_entry("notes/orphan.md", []), _entry("notes/other.md", ["x"])]
    tag_df = _e5_tag_df(index)
    candidates, floor_gated = rank_e5_candidates("notes/orphan.md", frozenset(), index, tag_df)
    _assert(candidates == [], "empty orphan tags -> []", errors)
    _assert(not floor_gated, "empty orphan tags: floor_gated is False (not a floor case)", errors)


def case_no_shared_tag_distinct_from_floor_gated(errors: list) -> None:
    """#495 review fix: 'no note shares any tag' must NOT be reported as floor_gated.

    An orphan whose tag is genuinely unique in the vault (no other note carries
    it at all) gets candidates == [] for a totally different reason than the
    floor case above (there SHARED tags existed, just too weak). Both cases
    look identical if classify() only tested `orphan_tags` truthiness, which
    used to misreport "공유 태그가 너무 흔해 신호가 되지 못함" (shared tags too
    common) for an orphan that shares NO tag with anyone.
    """
    index = [
        _entry("notes/orphan.md", ["unicorn"]),
        _entry("notes/other.md", ["completely-different-tag"]),
    ]
    tag_df = _e5_tag_df(index)
    candidates, floor_gated = rank_e5_candidates(
        "notes/orphan.md", frozenset({"unicorn"}), index, tag_df,
    )
    _assert(candidates == [], "no note shares the orphan's tag -> []", errors)
    _assert(
        not floor_gated,
        "no note shares the orphan's tag -> floor_gated is False, NOT the floor case",
        errors,
    )


def case_top_n_truncation_preserved(errors: list) -> None:
    """>3 candidates clearing the floor -> only E5_CANDIDATE_TOP_N survive, score-ranked."""
    # 5 distinct rare tags (df=2 each), one per candidate, all clearing the floor.
    index = [_entry("notes/orphan.md", [f"t{i}" for i in range(5)])]
    index += [_entry(f"notes/cand-{i}.md", [f"t{i}"]) for i in range(5)]
    tag_df = _e5_tag_df(index)
    candidates, _floor_gated = rank_e5_candidates(
        "notes/orphan.md", frozenset({f"t{i}" for i in range(5)}), index, tag_df,
    )
    _assert(
        len(candidates) == E5_CANDIDATE_TOP_N,
        f"5 equal-scoring candidates -> exactly top-{E5_CANDIDATE_TOP_N} kept "
        f"(got {len(candidates)})",
        errors,
    )
    _assert(
        [c["path"] for c in candidates] == ["notes/cand-0.md", "notes/cand-1.md", "notes/cand-2.md"],
        f"equal-score tie-break falls back to path ascending "
        f"(got {[c['path'] for c in candidates]})",
        errors,
    )


def case_score_e5_candidate_sums_multiple_tags(errors: list) -> None:
    """score_e5_candidate sums 1/log(1+df) over EVERY shared tag, not just one."""
    tag_df = {"a": 2, "b": 3}
    expected = 1.0 / math.log(3) + 1.0 / math.log(4)
    got = score_e5_candidate(frozenset({"a", "b"}), tag_df)
    _assert(
        abs(got - expected) < 1e-9,
        f"score sums both shared tags (expected {expected:.4f}, got {got:.4f})",
        errors,
    )


def main() -> int:
    errors: list = []
    cases = [
        case_rare_tag_outranks_common_tag,
        case_boundary_dominant_tag_floor,
        case_dominant_common_tag_drops_to_empty,
        case_empty_orphan_tags,
        case_no_shared_tag_distinct_from_floor_gated,
        case_top_n_truncation_preserved,
        case_score_e5_candidate_sums_multiple_tags,
    ]
    for fn in cases:
        print(f"# {fn.__name__}")
        fn(errors)
    if errors:
        print(f"\nFAILED: {len(errors)} assertion(s) failed")
        return 1
    print("\nOK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
