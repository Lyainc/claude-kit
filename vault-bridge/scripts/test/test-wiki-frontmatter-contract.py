#!/usr/bin/env python3
"""wiki frontmatter cross-plugin contract: WRITER (vault-bridge) ↔ AUDITOR (OVM) (#645 B3).

`/wiki`'s deployment unit moved OVM -> vault-bridge (#645), which put the WRITER of wiki-page
frontmatter and its READER in two different plugins:

  WRITER   vault-bridge/skills/wiki/SKILL.md   Phase 4 PLAN declares the schema,
                                               Phase 5 WRITE stamps `verified:`/`provenance:`
  AUDITOR  obsidian-vault-manager              E12 (`verified:`) + E2 (`provenance:`),
                                               via scripts/scan-summary.py (production path)
                                               and scripts/test/audit-validate.py (DoD oracle)

**Why this file exists — the failure it makes loud.** Every other break in this repo fails
noisily; this one does not. E12's scope guard is `top folder == wiki/ AND type == wiki`, and its
predicate is `parse_date(fm["verified"]) is None -> unverified, else age > 90 -> stale`. If the
writer stops emitting `verified:`, reshapes it (`YYYY/MM/DD`, an ISO timestamp), or drops
`type: wiki`, the audit does not error — `/audit` keeps exiting 0 and simply stops flagging
staleness. The wiki silently loses its only staleness signal and the scan still reports a clean
vault. Same shape for `provenance:`: it is in the auditor's required-field set (E2), so a writer
that stops emitting it turns every new page into a P0 finding — noise, in the other direction.
Before this file there were ZERO tests pinning either half across the plugin boundary.

**What is pinned, and in which direction.**
  - WRITER: the frontmatter block in `wiki/SKILL.md` is PARSED here (not string-matched), and the
    functional fixture below is generated FROM it. `verified:`'s documented placeholder is turned
    into a real date via a `YYYY-MM-DD` -> `%Y-%m-%d` mapping, so reshaping the documented
    placeholder produces a string the real auditor cannot parse and the round trip fails.
  - READER: the auditor's own `REQUIRED_FM_FIELDS` drives the writer-side field checks, so a new
    required field on the OVM side fails here until `wiki/SKILL.md` emits it. `STALE_WIKI_DAYS`
    and the date grammar are compared across BOTH auditor implementations.
  - ROUND TRIP: a temp vault holding one page built from the documented schema is run through the
    real production path (`ovm-primitives.sh scan-frontmatter|scan-filename` -> `scan-summary.py`)
    and the real DoD oracle (`audit-validate.py` `collect()` + `classify()`). Clean page -> zero
    findings from both. Four mutations (missing / unparseable / stale `verified:`, missing
    `provenance:`) -> each FLAGGED by both, never silently passed.

Not a duplicate of OVM's `test-wiki-self-audit.py`: that one pins E12's scoping edges against
hand-built records inside one plugin. This one starts at the writer's documented schema, goes
through files on disk, and asserts the two plugins still agree.

Reaching into `../obsidian-vault-manager/` is deliberate and has precedent — `test-vault-path.py`
does the same for `ovm-primitives.sh`. The path is resolved relative to this file, never absolute.
The test writes only into `tempfile` directories; no real vault is touched.

Run: python3 vault-bridge/scripts/test/test-wiki-frontmatter-contract.py
  -> per-check lines + "OK: ..." (exit 0) / "FAILED: ..." (exit 1).
Self-test (mutation fixtures, in-memory, no subprocess, no vault):
  python3 vault-bridge/scripts/test/test-wiki-frontmatter-contract.py --self-test
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_VAULT_BRIDGE = _HERE.parent.parent
_OVM = _VAULT_BRIDGE.parent / "obsidian-vault-manager"

_WIKI_SKILL = _VAULT_BRIDGE / "skills" / "wiki" / "SKILL.md"
_AUDIT_PY = _OVM / "scripts" / "test" / "audit-validate.py"
_SCAN_SUMMARY = _OVM / "scripts" / "scan-summary.py"
_OVM_PRIM = _OVM / "scripts" / "ovm-primitives.sh"

errors: list = []


def check(cond, desc: str) -> None:
    if cond:
        print(f"  ok   {desc}")
    else:
        print(f"  FAIL {desc}")
        errors.append(desc)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# The two auditor implementations, imported as the reader side of the contract.
_audit = _load("audit_validate_contract", _AUDIT_PY)      # DoD reference oracle
_scan = _load("scan_summary_contract", _SCAN_SUMMARY)     # production SCAN summarizer

FIXTURE_NAME = "wiki-frontmatter-contract-fixture.md"
FIXTURE_REL = f"wiki/{FIXTURE_NAME}"


# ---------------------------------------------------------------------------
# WRITER side — parse `wiki/SKILL.md`'s own documented frontmatter block
# ---------------------------------------------------------------------------

_FM_BLOCK_RE = re.compile(r"\*\*Frontmatter\*\*[^\n]*\n```ya?ml\n(.*?)\n```", re.S)
_FIELD_RE = re.compile(r"^([a-zA-Z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")


def documented_frontmatter(wiki_text: str) -> dict:
    """{field: {"value": ..., "comment": ...}} from wiki/SKILL.md's Phase 4 PLAN yaml block.

    Parsed, not string-matched: the fixture the auditor is run against is generated from this,
    so the writer's *documented* schema is what actually gets audited. Returns {} when the block
    is gone — that is itself a contract failure, reported as a failed check, never an exception.
    """
    m = _FM_BLOCK_RE.search(wiki_text)
    if not m:
        return {}
    fields: dict = {}
    for raw in m.group(1).splitlines():
        line, comment = (raw.split("#", 1) + [""])[:2]
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        fm = _FIELD_RE.match(line)
        if fm:
            fields[fm.group(1)] = {"value": fm.group(2).strip(), "comment": comment.strip()}
    return fields


def _is_optional(info: dict) -> bool:
    return "optional" in (info.get("comment") or "").lower()


def static_checks(wiki_text: str) -> list:
    """(ok, description) pairs pinning the WRITER half. Each names ONE invariant, so a failure
    line says which half of the contract died rather than "the section changed"."""
    f = documented_frontmatter(wiki_text)
    verified = f.get("verified") or {}
    provenance = f.get("provenance") or {}
    out = [
        (bool(f), "WRITER: wiki/SKILL.md still documents a wiki frontmatter block (Phase 4 PLAN)"),
        ("verified" in f,
         "WRITER: the frontmatter block declares `verified:` (E12's only input)"),
        (verified.get("value") == "YYYY-MM-DD",
         "WRITER: `verified:` keeps the YYYY-MM-DD shape the OVM auditor parses"),
        (not _is_optional(verified) and "always" in (verified.get("comment") or "").lower(),
         "WRITER: `verified:` is documented as always written, never conditional"),
        (f.get("type", {}).get("value") == "wiki",
         "WRITER: `type: wiki` is stamped (E12 scope guard, half 1 — type)"),
        ("~/vault/wiki/" in wiki_text,
         "WRITER: pages are written under wiki/ (E12 scope guard, half 2 — top folder)"),
        (bool(provenance) and not _is_optional(provenance),
         "WRITER: the frontmatter block declares `provenance:` as non-optional"),
        ("Always stamp `verified:` to today on write" in wiki_text,
         "WRITER: the Rules section keeps the unconditional verified: stamp"),
        ("**Always write `provenance:`.**" in wiki_text,
         "WRITER: the Rules section keeps the unconditional provenance: write"),
        ("`; ` delimiter" in wiki_text,
         "WRITER: provenance stays single-line, `; `-joined across updates"),
    ]
    # Reader-driven: the OVM auditor's required-field set decides what the writer must emit.
    # A field added on the OVM side fails HERE until wiki/SKILL.md emits it (E2 noise otherwise).
    for field in _audit.REQUIRED_FM_FIELDS:
        out.append((field in f,
                    f"WRITER: emits `{field}:`, required by the OVM auditor's E2 field set"))
    return out


# ---------------------------------------------------------------------------
# Fixture generation — the page the auditor is run against comes from the doc
# ---------------------------------------------------------------------------

def _placeholder_to_date(placeholder: str, d: date) -> str:
    """Render `d` in the shape wiki/SKILL.md documents. `YYYY-MM-DD` -> `2026-08-26`.

    The indirection is the point: reshape the documented placeholder (to `YYYY/MM/DD`, or to an
    ISO timestamp) and this emits a string the real auditor cannot parse, so the functional round
    trip below fails instead of the doc and the code drifting apart in silence.
    """
    fmt = placeholder.replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d")
    return d.strftime(fmt)


def page_from_documented_schema(wiki_text: str, created: date, verified: date) -> str:
    """A wiki page whose frontmatter is exactly what the WRITER's documented schema produces."""
    fields = documented_frontmatter(wiki_text)
    lines = ["---"]
    for key, info in fields.items():
        if _is_optional(info):  # `anchor:` — documented as omitted for source-free pages
            continue
        value = info["value"]
        if key == "created":
            value = _placeholder_to_date(value, created)
        elif key == "verified":
            value = _placeholder_to_date(value, verified)
        elif value.startswith("<"):          # `<one line: the query ...>`
            value = f"{key}-fixture-value"
        elif "{" in value:                   # `[{domain}]`
            value = "[wiki-contract-test]"
        lines.append(f"{key}: {value}")
    lines += ["---", "", "계약 테스트용 고정 본문.", ""]
    return "\n".join(lines)


def drop_field(page: str, field: str) -> str:
    return "\n".join(l for l in page.splitlines() if not l.startswith(f"{field}:")) + "\n"


def reshape_field(page: str, field: str, value: str) -> str:
    return "\n".join(f"{field}: {value}" if l.startswith(f"{field}:") else l
                     for l in page.splitlines()) + "\n"


# ---------------------------------------------------------------------------
# READER side — run the two real auditors over a temp vault
# ---------------------------------------------------------------------------

def _write_vault(root: Path, page: str) -> Path:
    (root / "wiki").mkdir(parents=True, exist_ok=True)
    (root / "wiki" / FIXTURE_NAME).write_text(page, encoding="utf-8")
    return root


def run_production_audit(vault: Path, scratch: Path) -> dict:
    """The path a real `/audit` takes: ovm-primitives.sh scans -> scan-summary.py predicates.

    Returns scan-summary.py's `errors` object. Raises on any non-zero exit — a broken toolchain
    must never be read as "the vault is clean" (#614's whole point).
    """
    env = dict(os.environ)
    env.pop("VAULT_BRIDGE_DISABLE", None)
    env["VAULT_ROOT"] = str(vault)
    paths = {}
    for sub, out in (("scan-frontmatter", "fm.json"), ("scan-filename", "fn.json")):
        r = subprocess.run(["bash", str(_OVM_PRIM), sub, str(vault)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"{sub} failed (rc={r.returncode}): {r.stderr.strip()}")
        paths[sub] = scratch / out
        paths[sub].write_text(r.stdout, encoding="utf-8")
    r = subprocess.run([sys.executable, str(_SCAN_SUMMARY),
                        "--frontmatter", str(paths["scan-frontmatter"]),
                        "--filename", str(paths["scan-filename"])],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"scan-summary.py failed (rc={r.returncode}): {r.stderr.strip()}")
    return json.loads(r.stdout)["errors"]


def run_oracle_audit(vault: Path) -> dict:
    """The DoD reference oracle: audit-validate.py collect() + classify(). {type: [paths]}."""
    result = _audit.classify(_audit.collect(vault))
    by_type: dict = {}
    for f in result["findings"]:
        by_type.setdefault(f["type"], []).append(f)
    return by_type


def _prod_fired(errs: dict) -> set:
    """Error codes with at least one record in scan-summary.py's output (E5 may be 'not computed'
    — no --index is passed, and an uncomputed type is never counted as a finding)."""
    return {code for code, entry in errs.items()
            if entry.get("computed", True) and entry.get("count", 0) > 0}


# ---------------------------------------------------------------------------
# mutation fixtures, built by `.replace()` off the REAL file (no-op guard below)
# ---------------------------------------------------------------------------

_CLEAN_WIKI = _WIKI_SKILL.read_text(encoding="utf-8")

# Anchored on the schema line as it is FOUND, not on its literal text, so an unrelated edit to
# the trailing comment does not detonate every fixture at once.
_VERIFIED_LINE = (re.search(r"^verified:.*$", _CLEAN_WIKI, re.M) or [""])[0]


def _sub(old: str, new: str) -> str:
    """Mutate the real file text. An empty anchor returns the base unchanged, so the no-op guard
    below reports the drift instead of `str.replace("", x)` mangling every line of the fixture."""
    return _CLEAN_WIKI.replace(old, new) if old else _CLEAN_WIKI


_WIKI_NO_VERIFIED = _sub(_VERIFIED_LINE + "\n", "")
_WIKI_RESHAPED_DATE = _sub(_VERIFIED_LINE, _VERIFIED_LINE.replace("YYYY-MM-DD", "YYYY/MM/DD"))
_WIKI_OPTIONAL_VERIFIED = _sub(_VERIFIED_LINE,
                               _VERIFIED_LINE.split("#")[0] + "# optional, written when known")
_WIKI_NO_PROVENANCE = "\n".join(
    l for l in _CLEAN_WIKI.splitlines() if not l.startswith("provenance:"))
_WIKI_NO_PROVENANCE_RULE = _CLEAN_WIKI.replace("**Always write `provenance:`.**",
                                               "Write `provenance:` when it is known.")
_WIKI_NOT_TYPE_WIKI = _CLEAN_WIKI.replace("\ntype: wiki\n", "\ntype: knowledge\n")

_WIKI_FIXTURES = [
    ("_WIKI_NO_VERIFIED", _WIKI_NO_VERIFIED),
    ("_WIKI_RESHAPED_DATE", _WIKI_RESHAPED_DATE),
    ("_WIKI_OPTIONAL_VERIFIED", _WIKI_OPTIONAL_VERIFIED),
    ("_WIKI_NO_PROVENANCE", _WIKI_NO_PROVENANCE),
    ("_WIKI_NO_PROVENANCE_RULE", _WIKI_NO_PROVENANCE_RULE),
    ("_WIKI_NOT_TYPE_WIKI", _WIKI_NOT_TYPE_WIKI),
]
# A fixture that no-ops is a fixture that proves nothing — guarded at import time. The guard is
# conditioned on the base file still passing every writer pin: when wiki/SKILL.md is the thing that
# regressed, the fixture it mutates is legitimately gone, and a hard assert here would replace
# main()'s "which pin broke" report with a traceback about a test fixture.
_BASE_PINS_HOLD = all(ok for ok, _ in static_checks(_CLEAN_WIKI))
for _name, _fixture in _WIKI_FIXTURES:
    assert _fixture != _CLEAN_WIKI or not _BASE_PINS_HOLD, (
        f"{_name} is identical to its base — its .replace() no-opped against a wiki/SKILL.md that "
        f"still passes every writer pin, so the fixture itself drifted.")

_PIN_CASES = [
    ("clean wiki/SKILL.md passes every writer-side guard", _CLEAN_WIKI, True),
    ("WRITER drops `verified:` from the schema -> FAIL", _WIKI_NO_VERIFIED, False),
    ("WRITER reshapes `verified:` to YYYY/MM/DD -> FAIL", _WIKI_RESHAPED_DATE, False),
    ("WRITER demotes `verified:` to optional -> FAIL", _WIKI_OPTIONAL_VERIFIED, False),
    ("WRITER drops `provenance:` from the schema -> FAIL", _WIKI_NO_PROVENANCE, False),
    ("WRITER softens the always-write-provenance rule -> FAIL", _WIKI_NO_PROVENANCE_RULE, False),
    ("WRITER stops stamping `type: wiki` -> FAIL", _WIKI_NOT_TYPE_WIKI, False),
]


def _self_test() -> int:
    cases = []
    for desc, wiki, expect_pass in _PIN_CASES:
        results = static_checks(wiki)
        got = all(ok for ok, _ in results)
        detail = ""
        if expect_pass and not got:
            detail = f" — unexpectedly failed: {[d for ok, d in results if not ok]}"
        cases.append((f"{desc}{detail}", got == expect_pass))

    # Reader-side mutation: the same page text, run through the REAL auditor's parser and E12
    # predicates in memory (no vault, no subprocess) — pins that each mutation is FLAGGED, which
    # is the half a static grep of the skill body can never show.
    today = date.today()
    clean_page = page_from_documented_schema(_CLEAN_WIKI, today - timedelta(days=10), today)
    page_cases = [
        ("auditor: schema-conformant page is neither stale nor unverified", clean_page, set()),
        ("auditor: missing `verified:` -> unverified",
         drop_field(clean_page, "verified"), {"unverified"}),
        ("auditor: unparseable `verified:` (ISO timestamp) -> unverified",
         reshape_field(clean_page, "verified", f"{today.isoformat()}T09:00:00"), {"unverified"}),
        ("auditor: `verified:` older than STALE_WIKI_DAYS -> stale",
         reshape_field(clean_page, "verified",
                       (today - timedelta(days=_audit.STALE_WIKI_DAYS + 30)).isoformat()),
         {"stale"}),
    ]
    for desc, page, expected in page_cases:
        fm = _audit.parse_frontmatter(page) or {}
        rec = [{"rel": FIXTURE_REL, "fm": fm}]
        fired = set()
        if _audit.detect_stale_wiki(rec, today):
            fired.add("stale")
        if _audit.detect_unverifiable_wiki(rec):
            fired.add("unverified")
        cases.append((f"{desc} (fired: {sorted(fired) or 'none'})", fired == expected))

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(f"  [{'OK' if ok else 'FAIL'}] {n}")
    if failed:
        print(f"\nSELF-TEST FAILED: {len(failed)} case(s)")
        return 1
    print(f"\nOK: all {len(cases)} self-test cases passed")
    return 0


# ---------------------------------------------------------------------------

def main() -> int:
    wiki_text = _WIKI_SKILL.read_text(encoding="utf-8")
    today = date.today()

    print("WRITER (vault-bridge/skills/wiki/SKILL.md):")
    for ok, desc in static_checks(wiki_text):
        check(ok, desc)

    print("\nREADER (obsidian-vault-manager auditors):")
    check("provenance" in _audit.REQUIRED_FM_FIELDS,
          "READER: `provenance` is still in the auditor's required-field set (E2)")
    check(re.search(r"required_fields\s*=\s*\{[^}]*'provenance'", _OVM_PRIM.read_text(encoding="utf-8")),
          "READER: ovm-primitives.sh scan-frontmatter still counts `provenance` as required")
    check(_audit.STALE_WIKI_DAYS == _scan.STALE_WIKI_DAYS,
          f"READER: both auditors agree on STALE_WIKI_DAYS ({_audit.STALE_WIKI_DAYS})")
    written_shape = _placeholder_to_date(
        (documented_frontmatter(wiki_text).get("verified") or {}).get("value", ""), today)
    check(_audit.parse_created_date(written_shape) is not None
          and _scan.parse_date(written_shape) is not None,
          f"READER: both auditors parse the exact string the writer stamps ({written_shape!r})")
    check(_audit.parse_created_date(f"{today.isoformat()}T09:00:00") is None
          and _audit.parse_created_date(today.strftime("%Y/%m/%d")) is None,
          "READER: the date grammar is strict — a timestamp or YYYY/MM/DD is NOT accepted")
    check([r for r in _audit._wiki_pages([{"rel": FIXTURE_REL, "fm": {"type": "wiki"}}])]
          and not [r for r in _audit._wiki_pages([{"rel": FIXTURE_REL, "fm": {"type": "note"}}])]
          and not [r for r in _audit._wiki_pages([{"rel": "notes/x.md", "fm": {"type": "wiki"}}])],
          "READER: E12 scope is wiki/ + type:wiki — both halves still required")

    print("\nROUND TRIP (documented schema -> real auditors over a temp vault):")
    clean_page = page_from_documented_schema(wiki_text, today - timedelta(days=10), today)
    stale_date = (today - timedelta(days=_audit.STALE_WIKI_DAYS + 30)).isoformat()
    cases = [
        ("schema-conformant page", clean_page, set(), set()),
        ("missing `verified:`", drop_field(clean_page, "verified"),
         {"E12_unverified"}, {"E12_wiki_unverified"}),
        ("unparseable `verified:`",
         reshape_field(clean_page, "verified", f"{today.isoformat()}T09:00:00"),
         {"E12_unverified"}, {"E12_wiki_unverified"}),
        (f"`verified:` {_audit.STALE_WIKI_DAYS + 30}d old",
         reshape_field(clean_page, "verified", stale_date),
         {"E12_stale"}, {"E12_wiki_stale"}),
        ("missing `provenance:`", drop_field(clean_page, "provenance"),
         {"E2"}, {"E2_missing_required_fields"}),
    ]

    with tempfile.TemporaryDirectory() as scratch_dir:
        scratch = Path(scratch_dir)
        for desc, page, prod_expected, oracle_expected in cases:
            with tempfile.TemporaryDirectory() as vault_dir:
                vault = _write_vault(Path(vault_dir), page)
                prod = _prod_fired(run_production_audit(vault, scratch))
                oracle_findings = run_oracle_audit(vault)
            oracle = set(oracle_findings)
            check(prod == prod_expected,
                  f"production (scan-summary.py): {desc} -> {sorted(prod_expected) or 'no finding'}"
                  f" (got {sorted(prod) or 'none'})")
            check(oracle == oracle_expected,
                  f"oracle (audit-validate.py): {desc} -> {sorted(oracle_expected) or 'no finding'}"
                  f" (got {sorted(oracle) or 'none'})")
            if desc == "missing `provenance:`":
                # The field name is load-bearing: REPORT quotes it, and `provenance` is the one
                # E2 field with no deterministic auto-fill (vault-audit-rules.md OPTIONAL-FIX).
                detail = ",".join(f["detail"] for f
                                  in oracle_findings.get("E2_missing_required_fields", []))
                check("provenance" in detail,
                      "oracle: the E2 finding names `provenance` as the missing field")

    if errors:
        print(f"\nFAILED: {len(errors)} check(s) failed")
        return 1
    print(f"\nOK: all wiki frontmatter contract checks passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        print("Running self-test (mutation fixtures, in-memory)...\n")
        raise SystemExit(_self_test())
    raise SystemExit(main())
