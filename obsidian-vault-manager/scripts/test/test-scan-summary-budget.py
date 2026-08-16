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
      trips. Fixed by extract-wikilinks-batch: one python3 process regardless of N.

Test matrix:
  1. budget: the default-cap bundle is under the 2048 B preview on a 528-file fixture where
     all nine error types fire.
  2. truncation signal: a cap that bites produces `omitted: N`, and count - len(list) == N —
     nothing is ever dropped without a number saying how much.
  3. batching: ONE batch invocation over N files returns N records in input order, and
     SKILL.md Step 7 uses the batch form rather than a per-file loop.
  4. fidelity: the records that survive the filter still reproduce the fixture's seeded
     detections — per-type `count` matches what gen-fixture.sh seeded.

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

PREVIEW_LIMIT = 2048  # the harness's Bash-output preview — the whole budget

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
    """528-file fixture with every audit error type seeded. Fresh dir, never a fixed path."""
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
    rc, stdout, err = _run(["bash", prim, "extract-wikilinks-batch", "-"], vault,
                           stdin_text="\n".join(md_files) + "\n")
    if rc != 0:
        print(f"FAIL: extract-wikilinks-batch exited {rc}: {err}", file=sys.stderr)
        sys.exit(1)
    links.write_text(stdout, encoding="utf-8")
    return fm, fn, links, md_files, stdout


def summary(fm: Path, fn: Path, links: Path, vault: Path, max_per_type=None) -> tuple:
    args = [sys.executable, str(_SCRIPTS / "scan-summary.py"),
            "--frontmatter", str(fm), "--filename", str(fn), "--links", str(links)]
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
    _assert(data["total_files"] == 528,
            f"bundle reports all 528 scanned files (got {data['total_files']})", errors)
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
    records = json.loads(batch_stdout)
    _assert(len(records) == len(md_files) == 528,
            f"one invocation over {len(md_files)} files returns {len(records)} records", errors)
    expected = [str(Path(p).resolve().relative_to(Path(vault).resolve())) for p in md_files]
    _assert([r["path"] for r in records] == expected,
            "batch output preserves input order, one element per path", errors)
    _assert(all("links" in r for r in records),
            "every element carries a `links` array (uniform schema)", errors)

    # SKILL.md Step 7 must pipe find into the batch form. A per-file loop is the #614 bug.
    phase1 = re.search(r"## Phase 1 — SCAN(.*?)## Phase 2",
                       _SKILL_MD.read_text(encoding="utf-8"), re.DOTALL).group(1)
    _assert("extract-wikilinks-batch -" in phase1,
            "SKILL.md Step 7 pipes the file list into extract-wikilinks-batch", errors)
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
    _assert(e5, "E5 orphans are computed (not the no --links placeholder)", errors)
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
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    if errors:
        print(f"FAIL: {len(errors)} assertion(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("OK: all 5 scan-summary budget/batching cases passed")


if __name__ == "__main__":
    main()
