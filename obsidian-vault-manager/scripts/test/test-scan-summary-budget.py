#!/usr/bin/env python3
"""
Regression test — audit Phase 1 SCAN survives the harness's 2 KB Bash-output preview (#614).

Two defects shipped together in audit/SKILL.md Phase 1, and this pins both fixes:

  (A) SILENT TRUNCATION. Steps 5-6 printed the raw scan-frontmatter / scan-filename arrays
      to stdout — 175 KB + 116 KB on this fixture — so E1/E2/E3/E5/E6/E10/E11/E12's entire
      source data reached the model already cut, with nothing saying it had been cut.
      Fixed by scan-summary.py: read the scans off disk, emit only defect-bearing records,
      and make every cut explicit via `omitted`.
  (B) PER-FILE FANOUT. Step 7 ran extract-wikilinks once per .md file — 528 Bash round
      trips, and the model assembled the inbound index by hand. Fixed by
      `extract-wikilinks-batch <dir>`: one python3 process returning the finished index.

Test matrix:
  1. budget: the default-cap bundle is under the 2048 B preview on a 530-file fixture where
     all nine error types fire.
  2. truncation signal: a cap that bites produces `omitted: N`, and count - len(list) == N —
     nothing is ever dropped without a number saying how much.
  3. batching: ONE dir-shaped batch invocation returns the finished inbound index for the
     whole vault, and SKILL.md Step 7 uses that call rather than a per-file loop.
  4. fidelity: the records that survive the filter still reproduce the fixture's seeded
     detections — per-type `count` matches what gen-fixture.sh seeded.
  5. input handling: an absent scan input exits 3 with empty stdout.
  6. budget WITH a schema: E13 records name every missing field, so a record-count cap alone
     let a schema push the bundle past the preview (1,802 B -> 2,114 B on this fixture, and
     the first 2,048 B no longer parsed as JSON). The default line must hold its real byte
     budget with several schemas and long values, keep every `count`, account for every lost
     record in `omitted`, and flag the trim — while an explicit --max-per-type (the file
     re-run) stays unbudgeted.

Run: python3 obsidian-vault-manager/scripts/test/test-scan-summary-budget.py
Exit 0 on pass, 1 on fail. Builds its own fixture under a fresh mktemp dir (never a fixed
/tmp path) and removes it on the way out.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
_SKILL_MD = _SCRIPTS.parent / "skills" / "audit" / "SKILL.md"

PREVIEW_LIMIT = 2048  # the ~2 KB preview the audit docs assume; runtimes may differ
BUDGET_LIMIT = 2000   # scan-summary.py's own default --max-bytes (newline included)

# What gen-fixture.sh --with-audit-errors seeds, PLUS the legacy defect files the base
# fixture already carried (no-frontmatter-*, missing-fields-*, 2026-04-bad-name-*, and the
# 2020-dated captures). Both cohorts are genuine detections; the summary must see all of them.
SEEDED = {
    "E1": 10,             # 5 audit-e1-* + 5 legacy no-frontmatter-*
    "E2": 10,             # 5 audit-e2-* + 5 legacy missing-fields-*
    "E3": 10,             # 5 audit-e3-* + 5 legacy 2026-04-bad-name-*
    "E10": 5,
    "E11": 5,             # 2 root-direct + 3 in 20_Projects/
    "E12_stale": 5,
    "E12_unverified": 2,
    "E12_near_dup": 1,
}


def _assert(cond: bool, desc: str, errors: list) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}", file=sys.stderr)
        errors.append(desc)


def _run(args: list, vault: Path, stdin_text=None) -> tuple:
    env = os.environ.copy()
    for k in ("VAULT_ROOT", "VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH",
              "AUDIT_STATE_PATH", "VAULT_BRIDGE_DISABLE"):
        env.pop(k, None)
    env["VAULT_ROOT"] = str(vault)
    proc = subprocess.run(args, capture_output=True, text=True, env=env, input=stdin_text)
    return proc.returncode, proc.stdout, proc.stderr


def build_fixture(workdir: Path) -> Path:
    """530-file fixture with every audit error type seeded. Fresh dir, never a fixed path."""
    fixture = workdir / "fixture"
    env = os.environ.copy()
    env["OVM_FIXTURE_DIR"] = str(fixture)
    proc = subprocess.run(["bash", str(_HERE / "gen-fixture.sh"), "--with-audit-errors"],
                          capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        print(f"FAIL: gen-fixture.sh failed: {proc.stderr}", file=sys.stderr)
        sys.exit(1)
    return fixture


def scan(vault: Path, workdir: Path) -> tuple:
    """Run Phase 1's three scans exactly as SKILL.md does, into files. Returns their paths."""
    prim = str(_SCRIPTS / "ovm-primitives.sh")
    fm, fn, links = workdir / "fm.json", workdir / "fn.json", workdir / "links.json"

    for sub, out in (("scan-frontmatter", fm), ("scan-filename", fn)):
        rc, stdout, err = _run(["bash", prim, sub, str(vault)], vault)
        if rc != 0:
            print(f"FAIL: {sub} exited {rc}: {err}", file=sys.stderr)
            sys.exit(1)
        out.write_text(stdout, encoding="utf-8")

    md_files = sorted(str(p) for p in vault.rglob("*.md")
                      if not any(part.startswith(".") for part in p.relative_to(vault).parts))
    # ONE dir-shaped call — the subcommand walks the vault itself and returns the finished
    # inbound index (same shape as detect-vocabulary/e5-candidates). md_files is computed
    # here only as the independent oracle the index is checked against.
    rc, stdout, err = _run(["bash", prim, "extract-wikilinks-batch", str(vault)], vault)
    if rc != 0:
        print(f"FAIL: extract-wikilinks-batch exited {rc}: {err}", file=sys.stderr)
        sys.exit(1)
    links.write_text(stdout, encoding="utf-8")
    return fm, fn, links, md_files, stdout


def summary(fm: Path, fn: Path, links: Path, vault: Path, max_per_type=None) -> tuple:
    args = [sys.executable, str(_SCRIPTS / "scan-summary.py"),
            "--frontmatter", str(fm), "--filename", str(fn), "--index", str(links)]
    if max_per_type is not None:
        args += ["--max-per-type", str(max_per_type)]
    rc, stdout, err = _run(args, vault)
    return rc, stdout, err


# ---------------------------------------------------------------------------
# Case 1: the default bundle fits inside the 2 KB preview
# ---------------------------------------------------------------------------

def case_budget(fm, fn, links, vault, errors: list) -> dict:
    print("\ncase: budget")
    rc, out, err = summary(fm, fn, links, vault)
    _assert(rc == 0, f"scan-summary.py exits 0 (stderr: {err!r})", errors)
    size = len(out.encode("utf-8"))
    _assert(size < PREVIEW_LIMIT,
            f"default bundle is {size} B, under the {PREVIEW_LIMIT} B preview limit", errors)
    data = json.loads(out)
    _assert(data["total_files"] == 530,
            f"bundle reports all 530 scanned files (got {data['total_files']})", errors)
    raw = fm.stat().st_size + fn.stat().st_size
    _assert(raw > 100 * PREVIEW_LIMIT,
            f"the raw scans it replaces are {raw} B — far past the preview (the bug)", errors)
    return data


# ---------------------------------------------------------------------------
# Case 2: a cut always announces itself
# ---------------------------------------------------------------------------

def case_truncation_signal(fm, fn, links, vault, errors: list) -> None:
    print("\ncase: truncation_signal")
    rc, out, err = summary(fm, fn, links, vault, max_per_type=1)
    _assert(rc == 0, f"capped run exits 0 (stderr: {err!r})", errors)
    types = json.loads(out)["errors"]

    cut = {code: e for code, e in types.items()
           if e.get("count", 0) > 1}
    _assert(bool(cut), "at least one type exceeds the cap on this fixture", errors)
    for code, entry in cut.items():
        listed = entry.get("paths", entry.get("records", []))
        ok = (entry.get("omitted") == entry["count"] - len(listed)
              and len(listed) == 1 and entry["omitted"] > 0)
        _assert(ok, f"{code}: omitted={entry.get('omitted')} == count({entry['count']}) - "
                    f"listed({len(listed)})", errors)

    # And no `omitted` key when the cap does not bite — the signal means something.
    types_big = json.loads(summary(fm, fn, links, vault, max_per_type=500)[1])["errors"]
    _assert(all("omitted" not in e for e in types_big.values()),
            "no type claims omissions when the cap is above every count", errors)


# ---------------------------------------------------------------------------
# Case 3: the wikilink step is ONE batch call, not a per-file loop
# ---------------------------------------------------------------------------

def case_batch_wikilinks(vault: Path, md_files: list, batch_stdout: str, errors: list) -> None:
    print("\ncase: batch_wikilinks")
    index = json.loads(batch_stdout)
    _assert(isinstance(index, dict),
            f"one invocation over {len(md_files)} files returns the finished inbound index "
            f"({len(index)} target stems), not per-file records", errors)
    _assert(all(isinstance(v, list) for v in index.values()),
            "every stem maps to a list of source paths (uniform schema)", errors)

    # Sources are $VAULT_ROOT-relative and are real files in the fixture — the index is
    # built from the same walk the per-file loop used to do, so its sources must be a
    # subset of the vault's .md files.
    rel_files = {str(Path(p).resolve().relative_to(Path(vault).resolve())) for p in md_files}
    stray = {s for sources in index.values() for s in sources} - rel_files
    _assert(not stray, f"every index source is a vault-relative .md path (stray: {sorted(stray)[:3]})",
            errors)
    _assert(all(k == k.lower() and not k.endswith(".md") for k in index),
            "keys are lowercased, .md-stripped target stems (what E5 looks a file up by)", errors)

    # SKILL.md Step 7 must make ONE dir-shaped call. A per-file loop is the #614 bug, and
    # so is a `find | ... -` pipeline — that shape belongs to the superseded stdin form and
    # would die on `-` being resolved as a path.
    phase1 = re.search(r"## Phase 1 — SCAN(.*?)## Phase 2",
                       _SKILL_MD.read_text(encoding="utf-8"), re.DOTALL).group(1)
    _assert(re.search(r'extract-wikilinks-batch\s+"\$VAULT_ROOT"', phase1),
            "SKILL.md Step 7 calls extract-wikilinks-batch with the unscoped $VAULT_ROOT", errors)
    _assert("extract-wikilinks-batch -" not in phase1,
            "SKILL.md Step 7 does not use the superseded stdin form", errors)
    _assert(not re.search(r"extract-wikilinks\s+\"?\$\{?f", phase1),
            "SKILL.md Step 7 has no per-file extract-wikilinks loop", errors)
    _assert("scan-summary.py" in phase1,
            "SKILL.md Phase 1 reads the scans back through scan-summary.py", errors)


# ---------------------------------------------------------------------------
# Case 4: the kept records still reproduce the seeded detections
# ---------------------------------------------------------------------------

def case_seeded_detections(fm, fn, links, vault, errors: list) -> None:
    print("\ncase: seeded_detections")
    types = json.loads(summary(fm, fn, links, vault, max_per_type=500)[1])["errors"]
    for code, expected in SEEDED.items():
        _assert(types[code]["count"] == expected,
                f"{code}: {types[code]['count']} detected == {expected} seeded", errors)

    # E6's count is date-dependent (the base fixture's own captures age past 14 days), so
    # assert the 5 deliberately-seeded 2020 captures are all present rather than a total.
    e6 = {r["path"] for r in types["E6"]["records"]}
    seeded_e6 = {f"sources/audit-e6-stale-capture-{i:03d}.md" for i in range(1, 6)}
    _assert(seeded_e6 <= e6, f"all 5 seeded E6 captures detected (missing: {seeded_e6 - e6})",
            errors)

    # E5 orphans are link-derived: the E10 seeds each link to a note, so those targets must
    # NOT be orphans — proof the batch link index actually feeds the orphan derivation.
    e5 = set(types["E5"]["paths"])
    _assert(e5, "E5 orphans are computed (not the no --index placeholder)", errors)
    _assert(not (e5 & {f"notes/audit-e10-misplaced-session-{i:03d}.md" for i in range(1, 6)}),
            "linked-to notes are not reported as orphans", errors)

    # Field set: each type carries exactly what its rule needs to be re-rendered.
    _assert(all(set(r) == {"path", "missing_required"} for r in types["E2"]["records"]),
            "E2 records carry path + missing_required", errors)
    _assert(all(set(r) == {"path", "type", "created"} for r in types["E3"]["records"]),
            "E3 records carry path + type + created (the 권장 파일명 inputs)", errors)
    _assert(all(set(r) == {"path", "verified"} for r in types["E12_unverified"]["records"]),
            "E12_unverified records carry path + the raw verified value", errors)


# ---------------------------------------------------------------------------
# Case 5: an unreadable input is never mistaken for a clean vault
# ---------------------------------------------------------------------------

def case_missing_input_exit_code(fm, fn, vault, workdir: Path, errors: list) -> None:
    print("\ncase: missing_input_exit_code")
    rc, out, _ = summary(workdir / "absent.json", fn, workdir / "absent2.json", vault)
    _assert(rc == 3 and not out.strip(),
            f"absent scan input exits 3 with empty stdout (rc={rc}, stdout={out!r})", errors)


# ---------------------------------------------------------------------------
# Case 6: the budget holds with a schema present (several schemas, long values)
# ---------------------------------------------------------------------------

LONG = "장기-업무-항목-스키마-" + "가" * 40

BIG_SCHEMAS = {"schemas": [
    {"name": LONG + "-1", "when": {"type": "note"},
     "required": ["track", "track_order", "item", "item_order", "status", "status_since",
                  "output_at", "long_required_field_name_" + "x" * 30],
     "enum": {"created": ["never-matches-" + "y" * 40]}},
    {"name": LONG + "-2", "when": {"type": "wiki"},
     "required": ["owner", "reviewer", "review_cycle", "audience"],
     "enum": {"verified": ["no-such-value-" + "z" * 40]}},
    {"name": LONG + "-3", "when": {"type": "session"},
     "required": ["project", "ticket", "participants"]},
]}


def schema_summary(fm, fn, links, vault, schema, extra=()) -> tuple:
    args = [sys.executable, str(_SCRIPTS / "scan-summary.py"), "--frontmatter", str(fm),
            "--filename", str(fn), "--index", str(links), "--schema", str(schema), *extra]
    return _run(args, vault)


def case_budget_with_schema(fm, fn, links, vault, errors: list) -> None:
    print("\ncase: budget_with_schema")
    schema = vault / ".vault-schema.json"
    schema.write_text(json.dumps(BIG_SCHEMAS, ensure_ascii=False), encoding="utf-8")
    try:
        # Reference: the same schemas with no budget (explicit cap, as the file re-run uses).
        rc, full_out, err = schema_summary(fm, fn, links, vault, schema,
                                           ["--max-per-type", "5000"])
        _assert(rc == 0, f"unbudgeted schema run exits 0 (stderr: {err!r})", errors)
        full = json.loads(full_out)["errors"]
        _assert(len(full_out.encode("utf-8")) > PREVIEW_LIMIT and "budget" not in json.loads(full_out),
                "an explicit --max-per-type run is big and carries no budget key (file path)", errors)

        rc, out, err = schema_summary(fm, fn, links, vault, schema)
        _assert(rc == 0, f"default schema run exits 0 (stderr: {err!r})", errors)
        size = len(out.encode("utf-8"))
        _assert(size <= BUDGET_LIMIT and size < PREVIEW_LIMIT,
                f"default bundle WITH schemas is {size} B, within the {BUDGET_LIMIT} B budget", errors)
        try:
            json.loads(out.encode("utf-8")[:PREVIEW_LIMIT])
            parses = True
        except ValueError:
            parses = False
        _assert(parses, f"the first {PREVIEW_LIMIT} B of the line still parse as JSON", errors)
        data = json.loads(out)
        got = data["errors"]
        _assert(data.get("budget") == {"max_bytes": BUDGET_LIMIT, "trimmed": True},
                "a trimmed bundle flags budget.trimmed", errors)
        _assert(got["E13"]["count"] == full["E13"]["count"] and got["E13"]["count"] > 0,
                f"E13 keeps its full count ({got['E13']['count']}) — a cut never reads as zero",
                errors)
        _assert(set(got) == set(full), "every error type survives the trim", errors)
        for code, entry in got.items():
            listed = len(entry.get("paths", entry.get("records", [])))
            _assert(entry["count"] == full[code]["count"]
                    and entry.get("omitted", 0) == entry["count"] - listed,
                    f"{code}: count {entry['count']} intact, omitted == count - listed ({listed})",
                    errors)
        names = {r["schema"] for r in got["E13"]["records"]}
        _assert(len(names) >= 1 and all(n.startswith(LONG) for n in names),
                "kept E13 records are real records (long schema names intact)", errors)
        kept_total = sum(len(e.get("paths", e.get("records", []))) for e in got.values())
        _assert(kept_total >= 5, f"the budget is used, not just met ({kept_total} records kept)",
                errors)

        # A budget the caller sets is honoured in both directions.
        rc, out0, _ = schema_summary(fm, fn, links, vault, schema, ["--max-bytes", "0"])
        _assert(rc == 0 and len(out0.encode("utf-8")) > BUDGET_LIMIT
                and "budget" not in json.loads(out0), "--max-bytes 0 removes the budget", errors)
        rc, out1, _ = schema_summary(fm, fn, links, vault, schema, ["--max-bytes", "1500"])
        _assert(rc == 0 and len(out1.encode("utf-8")) <= 1500
                and json.loads(out1)["budget"]["max_bytes"] == 1500,
                "--max-bytes 1500 is enforced and recorded", errors)
        rc, _, err = schema_summary(fm, fn, links, vault, schema, ["--max-bytes", "-1"])
        _assert(rc == 2, f"a negative --max-bytes is a usage error (rc={rc})", errors)
    finally:
        schema.unlink()

    # A vault with no schema is untouched: nothing trimmed, no budget key.
    rc, plain, _ = summary(fm, fn, links, vault)
    _assert("budget" not in json.loads(plain), "no schema, nothing to trim: no budget key", errors)


def main() -> None:
    errors: list = []
    workdir = Path(tempfile.mkdtemp(prefix="scan-summary-budget-"))
    try:
        vault = build_fixture(workdir)
        fm, fn, links, md_files, batch_stdout = scan(vault, workdir)

        case_budget(fm, fn, links, vault, errors)
        case_truncation_signal(fm, fn, links, vault, errors)
        case_batch_wikilinks(vault, md_files, batch_stdout, errors)
        case_seeded_detections(fm, fn, links, vault, errors)
        case_missing_input_exit_code(fm, fn, vault, workdir, errors)
        case_budget_with_schema(fm, fn, links, vault, errors)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    if errors:
        print(f"FAIL: {len(errors)} assertion(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("OK: all 6 scan-summary budget/batching cases passed")


if __name__ == "__main__":
    main()
