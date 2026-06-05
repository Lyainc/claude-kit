#!/usr/bin/env python3
"""
E9 vocabulary-pair regression + duplicate-parser parity gate (#165).

PR #162 claude-review flagged two gaps:
  1. No standalone unit test for E9 (`detect_vocabulary_pairs`) — the existing
     coverage was only the mechanical DoD fixture run.
  2. ovm-primitives.sh embeds its OWN copy of the frontmatter parser (in both
     `scan-frontmatter` and `detect-vocabulary`) with no automated test proving
     it stays aligned with audit-validate.py's `parse_frontmatter`.

This file closes BOTH in one place:

PART A — E9 unit tests: import `detect_vocabulary_pairs` / `_camel_to_snake` /
  `E9_MIN_FILES` from audit-validate.py and drive them with synthetic
  `fm_records` (each rec = {"rel": "<path>", "fm": {...}}). Pins the
  E9_MIN_FILES threshold boundary, E9a seen-set dedup, multi-boundary camelCase,
  irregular-plural exclusion, and the two-camel→one-snake double-report.

PART B — parser parity gate: runs BOTH duplicate parsers (ovm-primitives.sh via
  subprocess vs. audit-validate.py in-process) over identical fixtures and locks
  their alignment. PRIMARY: end-to-end E9 output parity over a real temp vault.
  SECONDARY: parser-unit parity over a battery of frontmatter strings, asserting
  equality where they agree on the E9-relevant surface (tags + key set) and
  LOCKING the two known divergences (hyphenated keys, trailing-space opener) with
  explicit assertions so future silent drift in EITHER parser is caught.

Test-only: does NOT modify audit-validate.py or ovm-primitives.sh.

Run: python3 obsidian-vault-manager/scripts/test/test-vocabulary-pairs.py
  → "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── module + script resolution ───────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_AUDIT_PY = _HERE / "audit-validate.py"
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"

_spec = importlib.util.spec_from_file_location("audit_validate", _AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

detect_vocabulary_pairs = _mod.detect_vocabulary_pairs
_camel_to_snake = _mod._camel_to_snake
parse_frontmatter = _mod.parse_frontmatter
collect = _mod.collect
E9_MIN_FILES = _mod.E9_MIN_FILES


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


# ── helpers for PART A (synthetic fm_records) ────────────────────────────────

def _rec(rel: str, fm: dict) -> dict:
    """Minimal fm_record shape consumed by detect_vocabulary_pairs."""
    return {"rel": rel, "fm": fm}


def _tag_recs(prefix: str, tags: list, n: int, start: int = 0) -> list:
    """n records, each carrying the given tags list, with distinct paths."""
    return [_rec(f"notes/{prefix}-{start + i}.md", {"tags": list(tags)}) for i in range(n)]


def _key_recs(prefix: str, keys: dict, n: int, start: int = 0) -> list:
    """n records, each carrying the given frontmatter keys, distinct paths."""
    return [_rec(f"notes/{prefix}-{start + i}.md", dict(keys)) for i in range(n)]


def _pairs_of_sub(pairs: list, sub: str) -> list:
    return [p for p in pairs if p["sub"] == sub]


# ── PART A: E9 unit tests ────────────────────────────────────────────────────

def case_threshold_boundary_e9a(errors: list) -> None:
    """E9a (tags singular/plural): N-1 files → NOT reported; ==E9_MIN_FILES → reported."""
    below = E9_MIN_FILES - 1
    # Each form in exactly E9_MIN_FILES-1 files → suppressed.
    recs = _tag_recs("api", ["api", "apis"], below)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9a")
    _assert(pairs == [], f"E9a: both forms in {below} (<MIN) files → 0 pairs", errors)

    # Bump each to exactly E9_MIN_FILES files → reported.
    recs = _tag_recs("api", ["api", "apis"], E9_MIN_FILES)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9a")
    _assert(len(pairs) == 1, f"E9a: both forms in {E9_MIN_FILES} (==MIN) files → 1 pair", errors)
    if pairs:
        p = pairs[0]
        _assert(
            p["a"] == "api" and p["b"] == "apis"
            and p["a_files"] == E9_MIN_FILES and p["b_files"] == E9_MIN_FILES,
            "E9a: reported pair carries a=api b=apis with correct file counts",
            errors,
        )


def case_threshold_boundary_e9b(errors: list) -> None:
    """E9b (camel/snake key): N-1 files → NOT reported; ==E9_MIN_FILES → reported."""
    below = E9_MIN_FILES - 1
    keys = {"sourceUrl": "x", "source_url": "y"}
    recs = _key_recs("k", keys, below)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9b")
    _assert(pairs == [], f"E9b: both keys in {below} (<MIN) files → 0 pairs", errors)

    recs = _key_recs("k", keys, E9_MIN_FILES)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9b")
    _assert(len(pairs) == 1, f"E9b: both keys in {E9_MIN_FILES} (==MIN) files → 1 pair", errors)
    if pairs:
        p = pairs[0]
        _assert(
            p["a"] == "sourceUrl" and p["b"] == "source_url",
            "E9b: reported pair carries a=sourceUrl b=source_url",
            errors,
        )


def case_e9a_seen_set_dedup(errors: list) -> None:
    """E9a `seen` dedup: a tag participates in at most one reported pair.

    Construct a chain where the `seen` set matters: `bug` / `bugs` / `bugss`.
    `bug`+s=`bugs` and `bugs`+s=`bugss` are both literal-+s pairs. Sorted
    iteration hits `bug` first → reports (bug, bugs) and adds both to `seen`.
    When iteration reaches `bugs`, it is already in `seen` → the (bugs, bugss)
    pair is suppressed, so `bugs` appears in exactly one reported pair.
    """
    n = E9_MIN_FILES
    recs = []
    recs += _tag_recs("g", ["bug"], n, start=0)
    recs += _tag_recs("g", ["bugs"], n, start=100)
    recs += _tag_recs("g", ["bugss"], n, start=200)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9a")
    _assert(len(pairs) == 1, "E9a dedup: chain bug/bugs/bugss → exactly 1 pair", errors)
    if pairs:
        p = pairs[0]
        _assert(
            p["a"] == "bug" and p["b"] == "bugs",
            "E9a dedup: the reported pair is (bug, bugs) — bugs consumed by seen-set",
            errors,
        )
    # Assert each tag participates in at most one reported pair.
    forms = []
    for p in pairs:
        forms += [p["a"], p["b"]]
    _assert(len(forms) == len(set(forms)), "E9a dedup: no tag appears in >1 reported pair", errors)


def case_multi_boundary_camelcase(errors: list) -> None:
    """Multi-boundary camelCase: createdAtTime + created_at_time → one E9b pair.

    Confirms _camel_to_snake handles MULTIPLE camel boundaries (not just one).
    """
    _assert(
        _camel_to_snake("createdAtTime") == "created_at_time",
        "_camel_to_snake: createdAtTime → created_at_time (multi-boundary)",
        errors,
    )
    keys = {"createdAtTime": "1", "created_at_time": "1"}
    recs = _key_recs("c", keys, E9_MIN_FILES)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9b")
    _assert(len(pairs) == 1, "E9b: createdAtTime/created_at_time → exactly 1 pair", errors)
    if pairs:
        p = pairs[0]
        _assert(
            p["a"] == "createdAtTime" and p["b"] == "created_at_time",
            "E9b: multi-boundary pair carries a=createdAtTime b=created_at_time",
            errors,
        )


def case_irregular_plural_excluded(errors: list) -> None:
    """Irregular plurals excluded: only literal t+'s' pairs match.

    status/statuses and leaf/leaves each in >=E9_MIN_FILES files → ZERO E9a:
    `status`+'s' = `statuss` != `statuses`; `leaf`+'s' = `leafs` != `leaves`.
    """
    n = E9_MIN_FILES
    recs = []
    recs += _tag_recs("s", ["status"], n, start=0)
    recs += _tag_recs("s", ["statuses"], n, start=100)
    recs += _tag_recs("l", ["leaf"], n, start=200)
    recs += _tag_recs("l", ["leaves"], n, start=300)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9a")
    _assert(
        pairs == [],
        "E9a: status/statuses + leaf/leaves (irregular) → 0 findings",
        errors,
    )


def case_two_camel_same_snake(errors: list) -> None:
    """Two camelCase → same snake → two independent E9b findings (no seen-set).

    sourceUrl, sourceURL, source_url each in >=E9_MIN_FILES files.
    _camel_to_snake('sourceUrl') == _camel_to_snake('sourceURL') == 'source_url'
    (only the e→U boundary matches in each). E9b has NO seen-set, so BOTH
    pairs (sourceUrl↔source_url AND sourceURL↔source_url) are reported.
    """
    # Empirically pin both camel forms collapse to the same snake form.
    _assert(
        _camel_to_snake("sourceUrl") == "source_url",
        "_camel_to_snake: sourceUrl → source_url",
        errors,
    )
    _assert(
        _camel_to_snake("sourceURL") == "source_url",
        "_camel_to_snake: sourceURL → source_url (only e→U boundary matches)",
        errors,
    )
    n = E9_MIN_FILES
    # All three keys co-occur on each of the n files (distinct values irrelevant).
    keys = {"sourceUrl": "1", "sourceURL": "2", "source_url": "3"}
    recs = _key_recs("u", keys, n)
    pairs = _pairs_of_sub(detect_vocabulary_pairs(recs), "E9b")
    _assert(len(pairs) == 2, "E9b: two camel→same snake → exactly 2 findings (no seen-set)", errors)
    ab = {(p["a"], p["b"]) for p in pairs}
    _assert(
        ab == {("sourceUrl", "source_url"), ("sourceURL", "source_url")},
        "E9b: both pairs are (sourceUrl,source_url) and (sourceURL,source_url)",
        errors,
    )


# ── PART B: parser parity gate ───────────────────────────────────────────────

def _run_prim(subcmd: str, vault_dir: str) -> object:
    """Invoke ovm-primitives.sh <subcmd> <vault_dir> with VAULT_ROOT=vault_dir.

    The fixture dir IS the vault root so validate_vault_path accepts it (mirrors
    test-infer-tags-batch.sh's VAULT_ROOT=<tmp> approach). Returns parsed JSON.
    """
    env = dict(os.environ)
    env["VAULT_ROOT"] = vault_dir
    proc = subprocess.run(
        ["bash", str(_PRIM_SH), subcmd, vault_dir],
        capture_output=True, text=True, env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ovm-primitives.sh {subcmd} failed (rc={proc.returncode}): {proc.stderr}"
        )
    return json.loads(proc.stdout)


def _norm_pairs(pairs: list) -> set:
    """Order-insensitive comparable form of a pair list."""
    return {
        (p["sub"], p["a"], p["b"], p["a_files"], p["b_files"])
        for p in pairs
    }


def case_parity_e9_end_to_end(errors: list) -> None:
    """PRIMARY: ovm detect-vocabulary JSON == audit detect_vocabulary_pairs(collect()).

    Build a temp vault exercising tags inline-list, tags block-list, quoted
    values, and snake + camelCase keys — with enough repetition to cross
    E9_MIN_FILES for at least one E9a and one E9b pair. Run BOTH duplicate
    parsers over the SAME files and assert the pair lists are EQUAL
    (order-insensitive). Locks E9 alignment end-to-end.
    """
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        notes = vault / "notes"
        notes.mkdir()

        # 3 files: tags inline-list [api, apis] + camel/snake keys → E9a(api/apis) + E9b(sourceUrl/source_url)
        for i in range(E9_MIN_FILES):
            (notes / f"inline-{i}.md").write_text(
                "---\n"
                "created: 2026-01-01\n"
                "tags: [api, apis]\n"
                'sourceUrl: "http://example.com/x"\n'
                "source_url: http://example.com/y\n"
                "type: note\n"
                "status: raw\n"
                "---\n\nbody\n",
                encoding="utf-8",
            )
        # 3 more files using BLOCK-list tags form to exercise the list-item branch,
        # carrying a distinct E9a candidate (bug/bugs) and the same camel/snake keys.
        for i in range(E9_MIN_FILES):
            (notes / f"block-{i}.md").write_text(
                "---\n"
                "created: 2026-01-02\n"
                "tags:\n"
                "  - bug\n"
                "  - bugs\n"
                "sourceUrl: http://b/x\n"
                "source_url: http://b/y\n"
                "type: note\n"
                "status: draft\n"
                "---\n\nbody\n",
                encoding="utf-8",
            )
        # A consistent control file (no inconsistency contributed).
        (notes / "control.md").write_text(
            "---\ncreated: 2026-01-03\ntags: [note]\ntype: note\nstatus: evergreen\n---\n\nok\n",
            encoding="utf-8",
        )

        ovm_pairs = _run_prim("detect-vocabulary", str(vault))
        audit_pairs = detect_vocabulary_pairs(collect(vault)["fm_records"])

        # Sanity: the fixture actually produces findings (gate is meaningful).
        _assert(len(audit_pairs) > 0, "parity e2e: fixture yields >0 E9 findings", errors)
        _assert(
            _norm_pairs(ovm_pairs) == _norm_pairs(audit_pairs),
            f"parity e2e: ovm pairs == audit pairs (ovm={_norm_pairs(ovm_pairs)} "
            f"audit={_norm_pairs(audit_pairs)})",
            errors,
        )


# Frontmatter battery for the parser-unit parity gate. Each entry: (name, content).
_BATTERY = [
    ("inline_list", "---\ntags: [api, apis]\ntype: note\n---\nbody\n"),
    ("block_list", "---\ntags:\n  - api\n  - apis\ntype: note\n---\nbody\n"),
    ("quoted_scalar", '---\ntitle: "Hello World"\ntype: note\n---\nbody\n'),
    ("quoted_list_item", "---\ntags:\n  - 'api'\n  - \"apis\"\n---\nbody\n"),
    ("camel_snake_keys", "---\nsourceUrl: http://x\nsource_url: http://y\n---\nbody\n"),
    ("empty_brackets", "---\ntags: []\ntype: note\n---\nbody\n"),
]


def case_parity_parser_unit_agreement(errors: list) -> None:
    """SECONDARY: parser-unit parity on the E9-relevant surface (tags + key set).

    ovm's isolated parse output is obtained by writing each content to a temp
    .md and reading the `frontmatter` field of `scan-frontmatter`'s JSON record
    (that field IS ovm's parse_frontmatter result). For each battery case where
    the two parsers AGREE, assert the tags list + frontmatter key set match.
    """
    for name, content in _BATTERY:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "notes").mkdir()
            (vault / "notes" / "case.md").write_text(content, encoding="utf-8")
            records = _run_prim("scan-frontmatter", str(vault))
            ovm_fm = records[0]["frontmatter"]
            audit_fm = parse_frontmatter(content) or {}

            # E9-relevant surface: the tags list and the set of keys.
            _assert(
                ovm_fm.get("tags") == audit_fm.get("tags"),
                f"parity unit [{name}]: tags list agrees",
                errors,
            )
            _assert(
                set(ovm_fm.keys()) == set(audit_fm.keys()),
                f"parity unit [{name}]: frontmatter key set agrees",
                errors,
            )


def case_parity_parser_unit_divergences(errors: list) -> None:
    """SECONDARY (locked divergences): the two parsers are NOT byte-identical.

    These are the divergences discovered empirically. They are LOCKED with
    explicit assertions of each parser's CURRENT behavior so that future silent
    drift in EITHER parser trips this gate. Test-only — neither parser is
    "more correct"; we just pin the status quo on the E9 surface.

    Divergence 1 — hyphenated key (`my-key`):
      audit's key regex `^([a-zA-Z_][a-zA-Z0-9_]*)` REJECTS hyphens → key dropped.
      ovm's `^(\\w[\\w\\-_]*)` ACCEPTS them → key present.

    Divergence 2 — trailing space on the opening fence (`--- `):
      audit requires exact `content.startswith("---\\n")` → returns None (no FM).
      ovm uses `lines[0].strip() == '---'` → tolerates the space → parses FM.
    """
    # ── Divergence 1: hyphenated key ─────────────────────────────────────────
    hyphen = "---\nmy-key: val\nnormal: ok\n---\nbody\n"
    audit_h = parse_frontmatter(hyphen) or {}
    _assert(
        "my-key" not in audit_h and audit_h.get("normal") == "ok",
        "divergence1: audit REJECTS hyphenated key (my-key absent, normal kept)",
        errors,
    )
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        (vault / "notes").mkdir()
        (vault / "notes" / "h.md").write_text(hyphen, encoding="utf-8")
        ovm_h = _run_prim("scan-frontmatter", str(vault))[0]["frontmatter"]
    _assert(
        ovm_h.get("my-key") == "val" and ovm_h.get("normal") == "ok",
        "divergence1: ovm ACCEPTS hyphenated key (my-key present)",
        errors,
    )

    # ── Divergence 2: trailing space on the opening fence ────────────────────
    trailing = "--- \ntags: [api]\ntype: note\n---\nbody\n"
    audit_t = parse_frontmatter(trailing)
    _assert(
        audit_t is None,
        "divergence2: audit returns None for '--- ' opener (exact ---\\n required)",
        errors,
    )
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        (vault / "notes").mkdir()
        (vault / "notes" / "t.md").write_text(trailing, encoding="utf-8")
        ovm_t = _run_prim("scan-frontmatter", str(vault))[0]["frontmatter"]
    _assert(
        ovm_t.get("tags") == ["api"] and ovm_t.get("type") == "note",
        "divergence2: ovm tolerates '--- ' opener and parses FM",
        errors,
    )


# ── runner ───────────────────────────────────────────────────────────────────

def main() -> int:
    errors: list = []
    cases = [
        # PART A — E9 unit tests
        case_threshold_boundary_e9a,
        case_threshold_boundary_e9b,
        case_e9a_seen_set_dedup,
        case_multi_boundary_camelcase,
        case_irregular_plural_excluded,
        case_two_camel_same_snake,
        # PART B — parser parity gate
        case_parity_e9_end_to_end,
        case_parity_parser_unit_agreement,
        case_parity_parser_unit_divergences,
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
