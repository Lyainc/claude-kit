#!/usr/bin/env python3
"""
`ovm-primitives.sh e5-candidates` production/oracle parity gate (#619, following #495's
oracle-only test-e5-candidate-ranking.py).

Before this fix, the rarity-weighted E5 connection-candidate score
(score(P,Q) = Sum 1/log(1+df(t)), top-3, E5_MIN_CANDIDATE_SCORE floor) existed only
inside audit-validate.py, which that file's own docstring calls "not the production
classifier". CLASSIFY had no primitive to call, so the audit skill was left to
hand-execute vault-wide document-frequency aggregation and float log-scoring itself —
the exact class of defect detect-vocabulary already avoids for E9 (#165's parity gate).

An earlier version of this file emitted `path` relative to the `<dir>` argument
(e.g. "a.md" for a file at notes/a.md) — the same convention scan-frontmatter uses for
ITS OWN argument, but NOT the convention CLASSIFY actually needs: `frontmatter_records`
(from `scan-frontmatter "$VAULT_ROOT"`, the unscoped default `/audit` path) keys findings
$VAULT_ROOT-relative ("notes/a.md"), so a CLASSIFY lookup against "a.md" always missed —
E5 candidates silently reported empty for every orphan. `cmd_e5_candidates` now resolves
`path` against `$VAULT_ROOT` regardless of which subdirectory was walked; `case_matches_scan_frontmatter_basis`
below pins that join directly instead of only checking score/floor/top-3 math in isolation.

Run: python3 obsidian-vault-manager/scripts/test/test-e5-candidates-primitive.py
  -> "OK: all cases passed" (exit 0) / "FAILED: N assertion(s) failed" (exit 1).
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUDIT_PY = _HERE / "audit-validate.py"
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"

_spec = importlib.util.spec_from_file_location("audit_validate", _AUDIT_PY)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

rank_e5_candidates = _mod.rank_e5_candidates
_e5_tag_df = _mod._e5_tag_df
E5_MIN_CANDIDATE_SCORE = _mod.E5_MIN_CANDIDATE_SCORE


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def write_note(vault: Path, relpath: str, tags: list) -> None:
    p = vault / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    tags_str = ", ".join(tags)
    p.write_text(
        f"---\ntype: note\ntags: [{tags_str}]\ncreated: 2026-01-01\nprovenance: t\n---\nbody\n",
        encoding="utf-8",
    )


def _env(vault_root: Path) -> dict:
    env = {**os.environ, "VAULT_ROOT": str(vault_root)}
    for k in ("VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH", "AUDIT_STATE_PATH"):
        env.pop(k, None)
    return env


def run_e5_candidates(vault: Path, notes_dir: Path) -> list:
    proc = subprocess.run(
        ["bash", str(_PRIM_SH), "e5-candidates", str(notes_dir)],
        capture_output=True, text=True, env=_env(vault),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"e5-candidates failed: {proc.stderr}")
    return json.loads(proc.stdout)


def run_scan_frontmatter(vault: Path) -> list:
    proc = subprocess.run(
        ["bash", str(_PRIM_SH), "scan-frontmatter", str(vault)],
        capture_output=True, text=True, env=_env(vault),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"scan-frontmatter failed: {proc.stderr}")
    return json.loads(proc.stdout)


def reference_result(files: dict) -> dict:
    """files: {vault-relative relpath: [tags]}. Returns {relpath: {candidates, floor_gated}}
    via the audit-validate.py oracle, mirroring classify()'s own notes_tag_index
    construction (case-sensitive, _index.md excluded — see classify()'s E5 block)."""
    notes_tag_index = [(rel, frozenset(tags)) for rel, tags in files.items()
                        if Path(rel).name != "_index.md"]
    tag_df = _e5_tag_df(notes_tag_index)
    out = {}
    for rel, tags in notes_tag_index:
        candidates, floor_gated = rank_e5_candidates(rel, frozenset(tags), notes_tag_index, tag_df)
        out[rel] = {"candidates": candidates, "floor_gated": floor_gated}
    return out


def case_matches_scan_frontmatter_basis(errors: list) -> None:
    """The actual #619 bug: e5-candidates' `path` must key-match `frontmatter_records`
    from the unscoped `scan-frontmatter "$VAULT_ROOT"` call SKILL.md's CLASSIFY joins
    against — not just agree with an oracle built from the same convention as itself."""
    print("\ncase: matches_scan_frontmatter_basis")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        write_note(vault, "notes/orphan.md", ["alpha"])
        write_note(vault, "notes/sub/candidate.md", ["alpha"])

        fm_paths = {r["path"] for r in run_scan_frontmatter(vault)}
        e5_paths = {r["path"] for r in run_e5_candidates(vault, vault / "notes")}

        _assert(fm_paths == {"notes/orphan.md", "notes/sub/candidate.md"},
                f"scan-frontmatter basis is $VAULT_ROOT-relative (got {sorted(fm_paths)})", errors)
        _assert(e5_paths == fm_paths,
                f"e5-candidates paths match scan-frontmatter's basis exactly "
                f"(e5={sorted(e5_paths)}, fm={sorted(fm_paths)})", errors)

        by_path = {r["path"]: r for r in run_e5_candidates(vault, vault / "notes")}
        cand_paths = {c["path"] for c in by_path["notes/orphan.md"]["candidates"]}
        _assert("notes/sub/candidate.md" in cand_paths,
                f"orphan's candidate is reachable via the SAME key CLASSIFY would look up "
                f"(got {cand_paths})", errors)


def case_missing_notes_dir_degrades_gracefully(errors: list) -> None:
    """A vault with no notes/ yet (sources/-only) must not fail SCAN Step 10 — it has
    nothing to rank, not an error."""
    print("\ncase: missing_notes_dir_degrades_gracefully")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        (vault / "sources").mkdir(parents=True)
        proc = subprocess.run(
            ["bash", str(_PRIM_SH), "e5-candidates", str(vault / "notes")],
            capture_output=True, text=True, env=_env(vault),
        )
        _assert(proc.returncode == 0,
                f"exits 0 on a missing notes/ dir (got {proc.returncode}: {proc.stderr!r})", errors)
        _assert(json.loads(proc.stdout) == [], "emits an empty array, not an error", errors)


def case_parity_over_fixture(errors: list) -> None:
    """Rare tag outranks a common one; a purely-common-tag pool floor-gates to []."""
    print("\ncase: parity_over_fixture")
    files = {
        "notes/a.md": ["shared-rare", "note"],
        "notes/b.md": ["shared-rare", "note"],
        "notes/c.md": ["note"],
        "notes/d.md": ["note"],
        "notes/e.md": ["note"],
        "notes/f.md": ["note"],
        "notes/g.md": ["note"],
    }
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        for rel, tags in files.items():
            write_note(vault, rel, tags)

        prim_out = {r["path"]: {"candidates": r["candidates"], "floor_gated": r["floor_gated"]}
                    for r in run_e5_candidates(vault, vault / "notes")}
        ref_out = reference_result(files)

        _assert(set(prim_out) == set(ref_out),
                f"same file set (prim={sorted(prim_out)}, ref={sorted(ref_out)})", errors)
        for rel in ref_out:
            _assert(prim_out.get(rel) == ref_out[rel],
                    f"{rel}: primitive matches oracle (prim={prim_out.get(rel)}, ref={ref_out[rel]})",
                    errors)

        # a.md and b.md share a rare tag (df=2) -> real candidate, not floor-gated.
        _assert(ref_out["notes/a.md"]["floor_gated"] is False, "a.md not floor-gated (sanity)", errors)
        _assert(any(c["path"] == "notes/b.md" for c in ref_out["notes/a.md"]["candidates"]),
                "a.md's top candidate is b.md (sanity)", errors)
        # c.md..g.md only share the vault-wide `note` tag (df=7) -> floor-gated to [].
        _assert(ref_out["notes/c.md"]["floor_gated"] is True, "c.md floor-gated on common tag alone (sanity)", errors)
        _assert(ref_out["notes/c.md"]["candidates"] == [], "c.md candidates empty when floor-gated (sanity)", errors)


def case_no_shared_tags(errors: list) -> None:
    """Distinct tags across every file -> candidates: [], floor_gated: false (not the
    same as floor-gated — no shared tag exists at all)."""
    print("\ncase: no_shared_tags")
    files = {"notes/a.md": ["alpha"], "notes/b.md": ["beta"]}
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        for rel, tags in files.items():
            write_note(vault, rel, tags)

        prim_out = {r["path"]: r for r in run_e5_candidates(vault, vault / "notes")}
        for rel in files:
            _assert(prim_out[rel]["candidates"] == [], f"{rel}: candidates == []", errors)
            _assert(prim_out[rel]["floor_gated"] is False, f"{rel}: floor_gated == False", errors)


def case_index_md_excluded(errors: list) -> None:
    """`_index.md` is never a candidate or a target (E5 guard)."""
    print("\ncase: index_md_excluded")
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        write_note(vault, "notes/_index.md", ["alpha"])
        write_note(vault, "notes/a.md", ["alpha"])
        write_note(vault, "notes/b.md", ["alpha"])

        prim_out = {r["path"]: r for r in run_e5_candidates(vault, vault / "notes")}
        _assert("notes/_index.md" not in prim_out, "_index.md is not a scored file", errors)
        a_candidate_paths = {c["path"] for c in prim_out.get("notes/a.md", {}).get("candidates", [])}
        _assert("notes/_index.md" not in a_candidate_paths, "_index.md never appears as a candidate", errors)


def case_top3_cap(errors: list) -> None:
    """More than 3 equally-scoring candidates -> capped at 3, sorted path-asc on ties."""
    print("\ncase: top3_cap")
    files = {f"notes/n{i}.md": ["rare"] for i in range(5)}
    files["notes/orphan.md"] = ["rare"]
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td) / "vault"
        for rel, tags in files.items():
            write_note(vault, rel, tags)

        prim_out = {r["path"]: r for r in run_e5_candidates(vault, vault / "notes")}
        cands = prim_out["notes/orphan.md"]["candidates"]
        _assert(len(cands) == 3, f"top-3 cap enforced (got {len(cands)})", errors)
        paths = [c["path"] for c in cands]
        _assert(paths == sorted(paths), f"tie-break is path-ascending (got {paths})", errors)


def main() -> int:
    errors: list = []
    for case in (
        case_matches_scan_frontmatter_basis,
        case_missing_notes_dir_degrades_gracefully,
        case_parity_over_fixture,
        case_no_shared_tags,
        case_index_md_excluded,
        case_top3_cap,
    ):
        case(errors)
    print()
    if errors:
        print(f"FAILED: {len(errors)} assertion(s) failed")
        return 1
    print("OK: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
