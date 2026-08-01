#!/usr/bin/env python3
"""Assert audit-validate --dod output against the date-INDEPENDENT DoD invariants (#175).

`audit-validate.py --dod` prints a DoD seeded-detection report but always exits 0 — it
measures, it does not gate. This helper turns that measurement into a real gate: it reads
the audit `--dod` JSON and fails (exit 1) if any date-independent invariant drifts.

What is asserted (all deterministic across run dates — see docs/VALIDATION.md `## Validation`):
  - seeded_detected == the expected per-type counts (false-negative guard)
  - fp_on_clean == 0 for every type           (false-positive guard)
  - findings_missing_priority == 0            (every finding carries a priority)
  - priority_mismatches == []                 (priority-by-type drift guard)
  - e2_tags_missing == e2_with_inferred_tags == 10  (#127 inference coverage)

What is NOT asserted: priority_counts (P1 varies by run date) and the display-only
e3_with_suggestion / e5_with_candidates magnitudes (only their floors are checked in
CLAUDE.md). Keeping those out keeps this gate non-flaky.

Usage:
    python3 audit-validate.py <vault> --dod > dod.json
    python3 assert-dod.py dod.json          # or: ... --dod | python3 assert-dod.py -

Exit 0 = all invariants hold, 1 = drift, 2 = unreadable input.
"""
import json
import sys

# Full type-name keys (matching audit-validate.py SEED_PREFIXES + E9_TYPE), not the
# short E1..E11 aliases used in the CLAUDE.md prose comment.
EXPECTED_SEEDED = {
    "E1_missing_frontmatter": 5,
    "E2_missing_required_fields": 5,
    "E3_filename_convention_violation": 5,
    "E4_broken_wikilink": 5,
    "E5_orphan_note": 6,
    "E6_stale_inbox": 5,
    "E7_stale_draft": 5,
    "E8_promotion_candidate": 2,
    "E9_tag_vocabulary_inconsistency": 2,
    "E10_misplaced_file": 5,
    "E11_unstructured_path": 5,
    "E12_wiki_stale": 5,
}


def assert_invariants(dod: dict) -> list:
    """Return a list of human-readable drift messages (empty == all invariants hold)."""
    errors: list = []

    seeded = dod.get("seeded_detected", {})
    if seeded != EXPECTED_SEEDED:
        # Report only the differing keys for a readable failure.
        keys = set(EXPECTED_SEEDED) | set(seeded)
        diffs = {k: (EXPECTED_SEEDED.get(k), seeded.get(k)) for k in sorted(keys)
                 if EXPECTED_SEEDED.get(k) != seeded.get(k)}
        errors.append(f"seeded_detected drift (type: expected->got): {diffs}")

    fp = dod.get("fp_on_clean", {})
    nonzero_fp = {k: v for k, v in fp.items() if v != 0}
    if nonzero_fp:
        errors.append(f"fp_on_clean must be 0 for every type; got non-zero: {nonzero_fp}")

    if dod.get("findings_missing_priority") != 0:
        errors.append(f"findings_missing_priority={dod.get('findings_missing_priority')} (expected 0)")

    if dod.get("priority_mismatches"):
        errors.append(f"priority_mismatches not empty: {dod.get('priority_mismatches')}")

    e2_missing = dod.get("e2_tags_missing")
    e2_inferred = dod.get("e2_with_inferred_tags")
    if e2_missing != 10 or e2_inferred != 10:
        errors.append(
            f"e2 tag-inference coverage: e2_tags_missing={e2_missing} "
            f"e2_with_inferred_tags={e2_inferred} (both expected 10)"
        )

    return errors


def main(argv: list) -> int:
    if not argv:
        print("ERROR: usage: assert-dod.py <dod.json|->", file=sys.stderr)
        return 2
    src = argv[0]
    try:
        if src == "-":
            raw = sys.stdin.read()
        else:
            with open(src, encoding="utf-8") as f:
                raw = f.read()
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read DoD JSON from {src!r}: {exc}", file=sys.stderr)
        return 2

    dod = payload.get("dod") if isinstance(payload, dict) else None
    if not isinstance(dod, dict):
        print("ERROR: input has no 'dod' object (run audit-validate.py with --dod)", file=sys.stderr)
        return 2

    errors = assert_invariants(dod)
    if errors:
        print("FAILED: audit DoD invariant drift:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: audit DoD invariants hold (seeded_detected={dod['seeded_detected']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
