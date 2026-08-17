#!/usr/bin/env python3
"""
Regression test — audit/SKILL.md's Phase 1 SCAN resolves $VAULT_ROOT and honors --path,
instead of hardcoding ~/vault (#619, following #613/#616's vault-root-chain fix).

Before this fix, audit/SKILL.md Steps 4-6 passed a literal `~/vault` to
scan-frontmatter/scan-filename/find regardless of VAULT_BRIDGE_VAULT_ROOT/VAULT_BRIDGE_VAULT_PATH,
so a non-default vault died in ovm-primitives.sh's validate_vault_path (the same #613 symptom,
still reachable end-to-end through the skill even after ovm-primitives.sh itself was fixed) and
the documented `--path <dir>` flag was inert (nothing consumed it).

Test matrix:
  1. SKILL.md structural wiring: Step 1 resolves $VAULT_ROOT via the shared chain; Steps
     scanning the vault use $scan_dir/$VAULT_ROOT, never a literal ~/vault; the link index
     and E9 vocabulary check stay unscoped by --path (by design — see SKILL.md Step 7/9).
  2. Functional: ovm-primitives.sh scan-frontmatter, invoked exactly as SKILL.md's Step 5
     would invoke it, against a non-default VAULT_BRIDGE_VAULT_PATH vault — succeeds (the
     #613/#619 repro).
  3. Functional: --path scoping actually narrows results — scanning $VAULT_ROOT/notes only
     returns files under notes/, scanning $VAULT_ROOT (unscoped) returns both.

Run: python3 obsidian-vault-manager/scripts/test/test-audit-vault-root-wiring.py
Exit 0 on pass, 1 on fail.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SKILL_MD = _HERE.parent.parent / "skills" / "audit" / "SKILL.md"
_PRIM_SH = _HERE.parent / "ovm-primitives.sh"


def _assert(cond: bool, desc: str, errors: list) -> bool:
    if cond:
        print(f"  ok   {desc}")
        return True
    print(f"  FAIL {desc}", file=sys.stderr)
    errors.append(desc)
    return False


# ---------------------------------------------------------------------------
# #673: whole-section verbatim + neighbour-identity pin for Step 1, same pattern as
# test-manifest-reads.py's `_SKILL_STEP8`. The loose `"VAULT_BRIDGE_VAULT_ROOT" in phase1`
# substring check below stays green even if the snippet is reworded to prose or the env-var
# priority is reversed, as long as both names still appear somewhere in Phase 1 — only a
# whole-step comparison catches that, and only a neighbour-identity pin catches a sibling
# heading wedged between Step 1 and Step 2 that parks contradicting text just outside it.
# ---------------------------------------------------------------------------

_STEP_OR_HEADING_ANCHOR_RE = re.compile(r"^(?:#{1,6} |\d+\. )")

_STEP1_RE = re.compile(
    r"^1\. Resolve `\$VAULT_ROOT`.*?(?=^\d+\. |^#{1,6} |\Z)",
    re.MULTILINE | re.DOTALL,
)


def _normalise(s: str) -> str:
    """Whitespace is not the contract — reflowing a paragraph must not read as a rewrite."""
    return " ".join(s.split())


def _section(pattern: re.Pattern, text: str) -> str:
    match = pattern.search(text)
    return _normalise(match.group(0)) if match else ""


def _neighbour_anchors(pattern: re.Pattern, text: str, anchor: re.Pattern) -> tuple:
    match = pattern.search(text)
    if not match:
        return ("", "")
    before = [ln for ln in text[:match.start()].splitlines() if anchor.match(ln)]
    after = [ln for ln in text[match.end():].splitlines() if anchor.match(ln)]
    return (before[-1] if before else "", after[0] if after else "")


_STEP1 = _normalise(
    "1. Resolve `$VAULT_ROOT` — same chain as `ovm-primitives.sh`/`pre-write-guard.sh`:\n"
    "   ```bash\n"
    "   VAULT_ROOT=\"${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}\"\n"
    "   [ -z \"$VAULT_ROOT\" ] && VAULT_ROOT=\"$HOME/vault\"\n"
    "   VAULT_ROOT=\"${VAULT_ROOT/#\\~/$HOME}\"\n"
    "   ```\n"
    "   `scan_dir` = `$VAULT_ROOT` unscoped, or `$VAULT_ROOT/<subdir>` under `--path <subdir>`.\n"
    "   `$scan_dir` → Steps 5–6; `$VAULT_ROOT` → everything else.\n"
)
_STEP1_NEIGHBOURS = ("## Phase 1 — SCAN", "2. Start metrics (save `token`):")


# ---------------------------------------------------------------------------
# Case 1: SKILL.md structural wiring
# ---------------------------------------------------------------------------

def case_skill_md_wiring(errors: list) -> None:
    print("\ncase: skill_md_wiring")
    text = _SKILL_MD.read_text(encoding="utf-8")

    _assert(_section(_STEP1_RE, text) == _STEP1,
            "Step 1 ($VAULT_ROOT resolution) matches VERBATIM (#673)", errors)
    _assert(_neighbour_anchors(_STEP1_RE, text, _STEP_OR_HEADING_ANCHOR_RE) == _STEP1_NEIGHBOURS,
            "Step 1 still sits between its two known anchors "
            "(an inserted sibling would park text outside the pin)", errors)
    # Isolate Phase 1 SCAN so a hardcoded ~/vault elsewhere in the file (there is none, but
    # future edits could add one) doesn't get conflated with this phase's own contract.
    m = re.search(r"## Phase 1 — SCAN(.*?)## Phase 2", text, re.DOTALL)
    _assert(m is not None, "Phase 1 SCAN section found", errors)
    phase1 = m.group(1) if m else ""

    # Step 1 resolves the shared chain, same as ovm-primitives.sh/pre-write-guard.sh.
    _assert("VAULT_BRIDGE_VAULT_ROOT" in phase1 and "VAULT_BRIDGE_VAULT_PATH" in phase1,
            "Step 1 names both VAULT_BRIDGE_VAULT_ROOT and VAULT_BRIDGE_VAULT_PATH", errors)

    # No exec call takes a literal ~/vault as its scan target anymore.
    literal_vault_calls = re.findall(
        r"(?:scan-frontmatter|scan-filename|find)\s+~/vault\b", phase1)
    _assert(not literal_vault_calls,
            f"no scan-frontmatter/scan-filename/find call hardcodes ~/vault (found: {literal_vault_calls})",
            errors)

    # Steps 5-6 (frontmatter/filename scan) use the --path-aware $scan_dir.
    _assert('scan-frontmatter "$scan_dir"' in phase1,
            "scan-frontmatter is called with \"$scan_dir\"", errors)
    _assert('scan-filename "$scan_dir"' in phase1,
            "scan-filename is called with \"$scan_dir\"", errors)

    # Step 7 (link index) and Step 9 (E9 vocabulary) stay vault-wide by design — they use
    # $VAULT_ROOT, not the --path-scoped $scan_dir, so a scoped run can't manufacture a
    # false E5 orphan or a false E9 vocabulary split.
    # #614 replaced the per-file `find | extract-wikilinks` loop with one dir-shaped
    # `extract-wikilinks-batch` call; the vault-wide invariant this guards is unchanged,
    # only which call carries it.
    _assert('extract-wikilinks-batch "$VAULT_ROOT"' in phase1,
            "the wikilink-index call uses the unscoped $VAULT_ROOT", errors)
    _assert('detect-vocabulary "$VAULT_ROOT"' in phase1,
            "detect-vocabulary is called with the unscoped $VAULT_ROOT", errors)


# ---------------------------------------------------------------------------
# Helpers for the functional cases
# ---------------------------------------------------------------------------

def _run_ovm(*args: str, env_overrides: dict) -> tuple:
    import os
    env = os.environ.copy()
    for k in ("VAULT_ROOT", "VAULT_BRIDGE_VAULT_ROOT", "VAULT_BRIDGE_VAULT_PATH",
              "AUDIT_STATE_PATH", "VAULT_BRIDGE_DISABLE"):
        env.pop(k, None)
    env.update(env_overrides)
    proc = subprocess.run(
        ["bash", str(_PRIM_SH), *args],
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write_note(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\ncreated: 2026-08-14\ntype: note\ntags: [x]\nprovenance: test\n---\n# {title}\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Case 2: scan-frontmatter succeeds under VAULT_BRIDGE_VAULT_PATH, invoked as Step 5 would
# ---------------------------------------------------------------------------

def case_scan_frontmatter_non_default_vault(errors: list) -> None:
    print("\ncase: scan_frontmatter_non_default_vault")
    with tempfile.TemporaryDirectory() as vault:
        _write_note(Path(vault) / "notes" / "one.md", "One")
        # scan_dir with no --path == $VAULT_ROOT unscoped, exactly Step 1's construction.
        rc, out, err = _run_ovm(
            "scan-frontmatter", vault,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": vault},
        )
        _assert(rc == 0, f"scan-frontmatter succeeds under a non-default vault (stderr: {err!r})", errors)
        try:
            records = json.loads(out)
        except json.JSONDecodeError:
            records = None
        _assert(isinstance(records, list) and len(records) == 1,
                f"one frontmatter record returned (got: {out!r})", errors)


# ---------------------------------------------------------------------------
# Case 3: --path scoping actually narrows the scan target
# ---------------------------------------------------------------------------

def case_path_flag_scopes_scan(errors: list) -> None:
    print("\ncase: path_flag_scopes_scan")
    with tempfile.TemporaryDirectory() as vault:
        _write_note(Path(vault) / "notes" / "in-scope.md", "In scope")
        _write_note(Path(vault) / "sources" / "out-of-scope.md", "Out of scope")

        # Unscoped ($VAULT_ROOT, --path not given): both files.
        rc_all, out_all, err_all = _run_ovm(
            "scan-frontmatter", vault,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": vault},
        )
        _assert(rc_all == 0, f"unscoped scan succeeds (stderr: {err_all!r})", errors)
        all_records = json.loads(out_all) if rc_all == 0 else []
        _assert(len(all_records) == 2,
                f"unscoped scan sees both files (got {len(all_records)})", errors)

        # Scoped ($VAULT_ROOT/notes, --path notes): only the in-scope file — the exact
        # scan_dir construction Step 1 documents ("$VAULT_ROOT/<subdir>" under --path).
        scan_dir = str(Path(vault) / "notes")
        rc_scoped, out_scoped, err_scoped = _run_ovm(
            "scan-frontmatter", scan_dir,
            env_overrides={"VAULT_BRIDGE_VAULT_PATH": vault},
        )
        _assert(rc_scoped == 0, f"--path-scoped scan succeeds (stderr: {err_scoped!r})", errors)
        scoped_records = json.loads(out_scoped) if rc_scoped == 0 else []
        _assert(len(scoped_records) == 1 and "in-scope.md" in scoped_records[0].get("path", ""),
                f"--path notes scan sees only the in-scope file (got: {out_scoped!r})", errors)


# ---------------------------------------------------------------------------
# #673 self-test: mutation fixtures for the Step 1 pin (in-memory, no live-file side effects)
# ---------------------------------------------------------------------------

_CLEAN_SKILL = _SKILL_MD.read_text(encoding="utf-8")

# The env-var resolution + tilde-expansion collapsed back into a prose summary — the #673
# regression class (a whole-step rewrite the old substring check couldn't see).
_SKILL_STEP1_PROSE = _CLEAN_SKILL.replace(
    "   VAULT_ROOT=\"${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}\"\n"
    "   [ -z \"$VAULT_ROOT\" ] && VAULT_ROOT=\"$HOME/vault\"\n"
    "   VAULT_ROOT=\"${VAULT_ROOT/#\\~/$HOME}\"\n",
    "   Falls back to ~/vault when neither env var is set.\n")

# ADJACENT-CLAUSE CORRUPTION: a heading wedged between Step 1 and Step 2 parks contradicting
# text where the whole-section comparison stays byte-identical; only adjacency sees it.
_SKILL_STEP1_HEADING_WEDGED = _CLEAN_SKILL.replace(
    "\n\n2. Start metrics (save `token`):",
    "\n\n#### Vault root note\n\nA relative path is also accepted here.\n"
    "\n2. Start metrics (save `token`):")

for _name, _fixture in (
    ("_SKILL_STEP1_PROSE", _SKILL_STEP1_PROSE),
    ("_SKILL_STEP1_HEADING_WEDGED", _SKILL_STEP1_HEADING_WEDGED),
):
    assert _fixture != _CLEAN_SKILL, f"{_name} is identical to its base — its .replace() no-opped"


def _step1_pin_ok(text: str) -> bool:
    return (_section(_STEP1_RE, text) == _STEP1
            and _neighbour_anchors(_STEP1_RE, text, _STEP_OR_HEADING_ANCHOR_RE) == _STEP1_NEIGHBOURS)


def _self_test() -> int:
    cases = [
        ("clean audit/SKILL.md passes the Step 1 pin", _step1_pin_ok(_CLEAN_SKILL) is True),
        ("Step 1 collapsed into prose -> FAIL", _step1_pin_ok(_SKILL_STEP1_PROSE) is False),
        ("heading wedged between Step 1 and Step 2 -> FAIL "
         "(whole-section comparison stays byte-identical; only adjacency sees it)",
         _step1_pin_ok(_SKILL_STEP1_HEADING_WEDGED) is False),
        ("adjacency-only: the heading-wedge mutation leaves the pinned Step 1 text itself unchanged",
         _section(_STEP1_RE, _SKILL_STEP1_HEADING_WEDGED) == _STEP1),
    ]
    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    errors: list = []

    case_skill_md_wiring(errors)
    case_scan_frontmatter_non_default_vault(errors)
    case_path_flag_scopes_scan(errors)

    print()
    if errors:
        print(f"FAIL: {len(errors)} case(s) failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print("OK: all 3 audit-vault-root-wiring cases passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (in-memory fixtures)...\n")
        raise SystemExit(_self_test())
    main()
