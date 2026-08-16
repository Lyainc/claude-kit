#!/usr/bin/env python3
"""Reduce audit Phase 1 SCAN's raw JSON to a bundle CLASSIFY can actually receive (#614,
mirrors #468's manifest-summary.py).

`scan-frontmatter` and `scan-filename` print their full record arrays to stdout —
175 KB and 116 KB on the 528-file fixture, 149 KB / 50 KB on the real 193-file vault.
The harness truncates large Bash output to a ~2 KB preview before the model ever sees
it, so the source data for E1/E2/E3/E5/E6/E10/E11/E12 arrived CUT, with no signal that
it had been cut — indistinguishable from a vault with three defects. This script reads
the raw scans from FILES ON DISK (untruncated) and prints only the defect-bearing
records, with only the fields each judgment in `reference/vault-audit-rules.md` needs.

Two consequences worth being explicit about:

  - Clean files are dropped entirely. A conforming file carries no information for the
    REPORT, and it is the 480-of-528 clean majority that blew the budget.
  - The deterministic predicates from vault-audit-rules.md run HERE, not in CLASSIFY.
    That is forced: filtering to "defect-bearing" is the same act as applying the rule.
    CLASSIFY still owns severity/priority, `detail` rendering, and every judgment that
    needs the other SCAN inputs (E5 candidates, E9 pairs). This file is not a second
    classifier — keep it in sync with vault-audit-rules.md, which stays canonical.

TRUNCATION IS EXPLICIT. `--max-per-type` caps the records emitted per error type, and a
type that hits the cap carries `"omitted": N` alongside its records. A cut is always
visible in the output; nothing is ever dropped silently — that silence is the whole bug.

Usage:
    scan-summary.py --frontmatter <fm.json> --filename <fn.json> [--index <index.json>]
                    [--max-per-type N]
    scan-summary.py --self-test            # rule + truncation-signal check, no fixture

    fm.json    <- ovm-primitives.sh scan-frontmatter "$scan_dir"
    fn.json    <- ovm-primitives.sh scan-filename "$scan_dir"
    index.json <- ovm-primitives.sh extract-wikilinks-batch "$VAULT_ROOT"   (the finished
                  {target_stem -> [source_paths]} inbound index; vault-wide, and optional —
                  without it E5 is reported as NOT COMPUTED, never as zero orphans)

E5 is derived here rather than in CLASSIFY for one reason: after this script drops clean
files, nothing else can enumerate the notes/ files that have no inbound link. The index
alone cannot — it lists link targets, not the vault's files.

Output (stdout, one compact JSON line) — 1.5 KB on the 528-file fixture with all nine
types firing, vs 291 KB of raw scan + 13 KB of index:

    {"total_files": N, "max_per_type": M, "link_index": {"targets": N, "sources": M},
     "errors": {
       "E1":  {"count": N, "paths":   ["<path>", ...]},              # missing_frontmatter
       "E2":  {"count": N, "records": [{path, missing_required}]},   # missing_required_fields
       "E3":  {"count": N, "records": [{path, type, created}]},      # filename_convention
       "E5":  {"count": N, "paths":   ["<path>", ...]},              # orphan_note
       "E6":  {"count": N, "records": [{path, created, age_days}]},  # stale_inbox
       "E10": {"count": N, "records": [{path, type}]},               # misplaced_file
       "E11": {"count": N, "paths":   ["<path>", ...]},              # unstructured_path
       "E12_stale":      {"count": N, "records": [{path, verified}]},
       "E12_unverified": {"count": N, "records": [{path, verified}]},
       "unreadable":     {"count": N, "records": [{path, error}]},   # only when it fires
     }}

Every type additionally carries `"omitted": N` whenever the cap cut its list. `unreadable`
appears only when scan-frontmatter could not read a file: those records are kept OUT of E1
and E5, because "we could not look" is not the same finding as "there is no frontmatter".

E9 (vault-wide vocabulary pairs) and the E5 connection candidates are NOT here — they come
from their own primitives (`detect-vocabulary`, `e5-candidates`), already small on stdout.

Exit codes:
    0  scans read and summarized
    3  an input file is absent, unreadable, or unparseable — never confused with
       "parsed to an empty scan" (same discipline as manifest-summary.py)
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

# Thresholds and folder tables are copied from reference/vault-audit-rules.md, and match
# scripts/test/audit-validate.py's constants of the same names (that file is the DoD
# reference oracle; drift between the two shows up as a --dod mismatch).
STALE_INBOX_DAYS = 14
STALE_WIKI_DAYS = 90
INBOX_RAW_STATUSES = {"", "raw"}
CANONICAL_FOLDERS = {"sources", "notes", "assets", "wiki"}
EXPECTED_FOLDER = {
    "session": "sources", "capture": "sources",
    "note": "notes", "decision": "notes", "plan": "notes",
    "wiki": "wiki",
}

# Default cap. Deliberately small: the budget is the harness's ~2 KB preview for the WHOLE
# bundle, and nine error types share it — a bundle that overruns the preview reintroduces
# the exact silent cut this script exists to remove. Measured on the 528-file fixture with
# all nine types firing: 1,536 B at 2, 2,046 B at 3, 3,467 B at 5. 3 sits two bytes under
# the limit, which is not a margin, so the default is 2.
# The long tail is NOT lost: raise --max-per-type for a run, redirect that bigger bundle to
# a file, and Read it — Read paginates, Bash stdout truncates. `omitted` says when to.
DEFAULT_MAX_PER_TYPE = 2

# Types whose entire finding is the path — they list bare strings, not one-key objects.
PATH_ONLY_TYPES = {"E1", "E5", "E11"}

DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def parse_date(value):
    """YYYY-MM-DD -> date, else None. Mirrors audit-validate.py's parse_created_date."""
    if not isinstance(value, str):
        return None
    m = DATE_RE.match(value.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def load(path: Path, kind=list):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, kind):
        raise ValueError(f"expected a JSON {kind.__name__}, got {type(data).__name__}")
    return data


def top_folder(rel: str) -> str:
    return rel.split("/", 1)[0] if "/" in rel else ""


def summarize(fm_records: list, fn_records: list, inbound, today: date) -> dict:
    """Apply each error type's deterministic predicate; keep only what fires."""
    errors: dict = {}

    def emit(code: str, records: list) -> None:
        errors[code] = records

    # A file scan-frontmatter could not READ emits a different record shape —
    # {path, error, frontmatter:{}} with no `has_frontmatter` key — so every predicate
    # below would read it as "no frontmatter" and file a Critical E1 for a file whose
    # frontmatter was never examined, dropping the `error` on the floor. Split those out
    # first and give them their own bucket: not knowing is not the same finding as
    # knowing the frontmatter is absent, and this script exists to stop exactly that kind
    # of unannounced substitution (#614). extract-wikilinks-batch already WARNs on the
    # same case; this is the summary path's half of that discipline.
    unreadable = [r for r in fm_records if r.get("error")]
    fm_records = [r for r in fm_records if not r.get("error")]
    if unreadable:
        emit("unreadable",
             [{"path": r.get("path"), "error": r["error"]} for r in unreadable])

    fm_by_path = {r.get("path"): r for r in fm_records}

    # E1 — has_frontmatter false. Path is the whole finding; `detail` is fixed text.
    emit("E1", [r["path"] for r in fm_records if not r.get("has_frontmatter")])

    # E2 — frontmatter present but incomplete. `missing_required` is load-bearing twice:
    # REPORT names the fields, and OPTIONAL-FIX routes the `tags`-missing subset into the
    # batched infer-tags call. Nothing else about the file matters to that judgment.
    emit("E2",
         [{"path": r["path"], "missing_required": r.get("missing_required") or []}
          for r in fm_records
          if r.get("has_frontmatter") and r.get("missing_required")])
    integrity_flagged = set(errors["E1"]) | {r["path"] for r in errors["E2"]}

    # E3 — the v3 date-first filename under notes/. `type` + `created` ride along because
    # the 권장 파일명 suggestion is built from them plus the slug (already in `path`); the
    # scan-filename record's own `violation` string is deliberately NOT forwarded — it
    # describes a broader predicate (any unrecognized name, anywhere) than E3's rule.
    e3 = []
    for r in fn_records:
        rel = r.get("path", "")
        name = rel.rsplit("/", 1)[-1]
        if name == "_index.md" or top_folder(rel) != "notes":
            continue
        if not re.match(r"^\d{4}-\d{2}-", name):
            continue
        fm = (fm_by_path.get(rel) or {}).get("frontmatter") or {}
        e3.append({"path": rel, "type": fm.get("type"), "created": fm.get("created")})
    emit("E3", e3)

    # E5 — a notes/ file with no inbound wikilink. Path only: the connection candidates
    # REPORT renders come from the separate e5-candidates primitive, joined on this path.
    # The index arrives finished from `extract-wikilinks-batch <dir>` and is keyed by
    # lowercased target stem, which is what a file's own stem is looked up by here.
    if inbound is None:
        errors["E5"] = None  # explicit "not computed", never a silent zero
    else:
        orphans = []
        for r in fm_records:
            rel = r["path"]
            name = rel.rsplit("/", 1)[-1]
            if name == "_index.md" or top_folder(rel) != "notes":
                continue
            stem = name[:-3].lower() if name.endswith(".md") else name.lower()
            if set(inbound.get(stem) or []) - {rel}:  # a self-link is not an inbound link
                continue
            orphans.append(rel)
        emit("E5", orphans)

    # E6 — a sources/ file still raw past the threshold. `created` + `age_days` are what
    # the Korean detail quotes ("age Nd > 14d, created Y"); age is computed here so
    # CLASSIFY never has to do date arithmetic against "today". `status` is NOT carried:
    # the predicate already constrains it to "" or "raw", so it is one bit of no
    # actionable content, and the budget is spent better on another file's path.
    e6 = []
    for r in fm_records:
        rel = r["path"]
        if top_folder(rel) != "sources":
            continue
        fm = r.get("frontmatter") or {}
        created = parse_date(fm.get("created"))
        if created is None:
            continue
        raw_status = fm.get("status")
        status = raw_status.strip() if isinstance(raw_status, str) else ""
        age = (today - created).days
        if status in INBOX_RAW_STATUSES and age > STALE_INBOX_DAYS:
            e6.append({"path": rel, "created": fm.get("created"), "age_days": age})
    emit("E6", e6)

    # E10 — type↔folder mismatch inside a canonical folder. `type` is the half of the
    # mismatch the path cannot show; the expected folder comes from EXPECTED_FOLDER,
    # which CLASSIFY already has in vault-audit-rules.md.
    e10 = []
    for r in fm_records:
        rel = r["path"]
        if rel in integrity_flagged:  # no reliable type until integrity is fixed
            continue
        top = top_folder(rel)
        if not top or top.startswith(".") or top == "assets":
            continue
        if top not in CANONICAL_FOLDERS:  # E11 owns these
            continue
        ftype = (r.get("frontmatter") or {}).get("type")
        expected = EXPECTED_FOLDER.get(ftype) if isinstance(ftype, str) else None
        if expected and top != expected:
            e10.append({"path": rel, "type": ftype})
    emit("E10", e10)

    # E11 — outside the canonical layout. Path only: the two detail variants
    # (root-direct vs non-canonical top folder) are readable off the path itself.
    e11 = []
    for r in fm_records:
        rel = r["path"]
        if rel.rsplit("/", 1)[-1] == "_index.md":
            continue
        top = top_folder(rel)
        if top.startswith(".") or top in CANONICAL_FOLDERS:
            continue
        e11.append(rel)
    emit("E11", e11)

    # E12 — wiki/ + type:wiki only. Both halves carry the raw `verified` value: for stale
    # it is the date the detail quotes (the age follows from it and the fixed 90-day
    # threshold), and for unverified it is what separates "field absent" from "field
    # unparseable" — two different Korean details (#494).
    stale, unverified = [], []
    for r in fm_records:
        rel = r["path"]
        fm = r.get("frontmatter") or {}
        if top_folder(rel) != "wiki" or fm.get("type") != "wiki":
            continue
        verified = parse_date(fm.get("verified"))
        if verified is None:
            unverified.append({"path": rel, "verified": fm.get("verified")})
            continue
        age = (today - verified).days
        if age > STALE_WIKI_DAYS:
            stale.append({"path": rel, "verified": fm.get("verified")})
    emit("E12_stale", stale)
    emit("E12_unverified", unverified)

    return errors


def cap(errors: dict, max_per_type: int) -> dict:
    """Apply the per-type cap, recording every cut as an `omitted` count.

    A path-only type (E1/E5/E11) lists bare path strings under `paths`; a type with extra
    fields lists objects under `records`. `count` is always the FULL number found, so
    `count` > len(kept) plus `omitted` makes every cut readable two ways.
    """
    out = {}
    for code, found in errors.items():
        if found is None:
            out[code] = {"computed": False, "reason": "no --index input"}
            continue
        key = "paths" if code in PATH_ONLY_TYPES else "records"
        entry = {"count": len(found), key: found[:max_per_type]}
        if len(found) > max_per_type:
            entry["omitted"] = len(found) - max_per_type
        out[code] = entry
    return out


def build_payload(fm_records: list, fn_records: list, inbound, max_per_type: int,
                  today: date) -> dict:
    payload = {
        "total_files": len(fm_records),
        "max_per_type": max_per_type,
        # The inbound index itself never enters context (13 KB on the 528-file fixture —
        # it would be cut like everything else). These two numbers say it was read and how
        # big it was, so "E5 found nothing" is distinguishable from "the index was empty".
        "link_index": ({"targets": len(inbound),
                        "sources": len({s for v in inbound.values() for s in v})}
                       if inbound is not None else None),
        "errors": cap(summarize(fm_records, fn_records, inbound, today), max_per_type),
    }
    return payload


def self_test() -> int:
    """Fixture-free check of every predicate + the truncation signal (#614).

    Deliberately hand-built records rather than a generated vault: this pins the RULES
    (which type fires on what, which fields survive, that a cut is announced), and runs in
    milliseconds with no fixture to drift. The vault-scale byte budget is the separate
    test/test-scan-summary-budget.py.
    """
    today = date(2026, 8, 16)
    fm = [
        {"path": "notes/no-fm.md", "has_frontmatter": False, "missing_required": [],
         "frontmatter": {}},
        {"path": "notes/partial.md", "has_frontmatter": True,
         "missing_required": ["provenance", "tags"], "frontmatter": {"type": "note"}},
        {"path": "notes/2026-04-old-name.md", "has_frontmatter": True,
         "missing_required": [], "frontmatter": {"type": "note", "created": "2026-04-01"}},
        {"path": "notes/linked.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "note"}},
        {"path": "notes/lonely.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "note"}},
        {"path": "notes/_index.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "note"}},
        {"path": "sources/old-capture.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "capture", "created": "2020-01-01", "status": "raw"}},
        {"path": "sources/fresh-capture.md", "has_frontmatter": True,
         "missing_required": [],
         "frontmatter": {"type": "capture", "created": "2026-08-15", "status": "raw"}},
        {"path": "notes/misplaced.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "session"}},
        {"path": "20_Projects/stray.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "note"}},
        {"path": "wiki/stale.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "wiki", "verified": "2020-01-01"}},
        {"path": "wiki/unverified.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "wiki", "verified": "TBD"}},
        {"path": "wiki/fresh.md", "has_frontmatter": True, "missing_required": [],
         "frontmatter": {"type": "wiki", "verified": "2026-08-10"}},
    ]
    fn = [{"path": r["path"]} for r in fm]
    inbound = {"linked": ["notes/lonely.md"], "lonely": ["notes/lonely.md"]}

    errors = summarize(fm, fn, inbound, today)
    cases = [
        ("E1 fires on missing frontmatter only", errors["E1"] == ["notes/no-fm.md"]),
        ("E2 carries the missing field list",
         errors["E2"] == [{"path": "notes/partial.md",
                           "missing_required": ["provenance", "tags"]}]),
        ("E3 fires on the date-first name, with type + created",
         errors["E3"] == [{"path": "notes/2026-04-old-name.md", "type": "note",
                           "created": "2026-04-01"}]),
        ("E5 skips a linked note, keeps an unlinked one, ignores _index.md",
         errors["E5"] == ["notes/no-fm.md", "notes/partial.md",
                          "notes/2026-04-old-name.md", "notes/lonely.md",
                          "notes/misplaced.md"]),
        ("E5 treats a self-link as no inbound link",
         "notes/lonely.md" in errors["E5"] and "notes/linked.md" not in errors["E5"]),
        ("E6 fires past 14 days and not before",
         [r["path"] for r in errors["E6"]] == ["sources/old-capture.md"]
         and errors["E6"][0]["age_days"] == 2419),
        ("E10 fires on type:session inside notes/",
         errors["E10"] == [{"path": "notes/misplaced.md", "type": "session"}]),
        ("E11 fires outside the canonical folders",
         errors["E11"] == ["20_Projects/stray.md"]),
        ("E12_stale reports the verified date it judged on",
         errors["E12_stale"] == [{"path": "wiki/stale.md", "verified": "2020-01-01"}]),
        ("E12_unverified keeps the unparseable raw value",
         errors["E12_unverified"] == [{"path": "wiki/unverified.md", "verified": "TBD"}]),
        ("a clean file appears in no bucket",
         all("wiki/fresh.md" not in json.dumps(v) for v in errors.values())),
        ("no --index means E5 is 'not computed', never zero orphans",
         summarize(fm, fn, None, today)["E5"] is None),
    ]

    # An UNREADABLE file must not be laundered into a finding about content nobody read.
    # scan-frontmatter emits {path, error, frontmatter:{}} with no has_frontmatter key, so
    # the naive predicate files a Critical E1 and drops the error (#614 review finding 1).
    unread = summarize(
        fm + [{"path": "notes/locked.md", "error": "[Errno 13] Permission denied",
               "frontmatter": {}}],
        fn + [{"path": "notes/locked.md"}], inbound, today)
    cases += [
        ("an unreadable file gets its own bucket, carrying the error",
         unread["unreadable"] == [{"path": "notes/locked.md",
                                   "error": "[Errno 13] Permission denied"}]),
        ("an unreadable file is NOT reported as missing frontmatter",
         "notes/locked.md" not in unread["E1"]),
        ("an unreadable file is NOT reported as an orphan either",
         "notes/locked.md" not in unread["E5"]),
        ("no unreadable input means no unreadable bucket",
         "unreadable" not in errors),
    ]

    capped = cap(errors, 2)
    cases += [
        ("a cut list announces itself", capped["E5"]["omitted"] == capped["E5"]["count"] - 2),
        ("an uncut list carries no omitted key", "omitted" not in capped["E1"]),
        ("count is always the full number found", capped["E5"]["count"] == 5),
        ("E5 unavailable renders as computed:false, not an empty list",
         cap(summarize(fm, fn, None, today), 2)["E5"] == {"computed": False,
                                                          "reason": "no --index input"}),
    ]

    failed = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if failed:
        print(f"FAIL: {len(failed)} scan-summary self-test case(s) failed", file=sys.stderr)
        return 1
    print(f"OK: all {len(cases)} scan-summary self-test cases passed")
    return 0


def main(argv: list) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] == "--self-test":
        return self_test()

    opts = {"--frontmatter": None, "--filename": None, "--index": None,
            "--max-per-type": str(DEFAULT_MAX_PER_TYPE)}
    i = 0
    while i < len(argv):
        if argv[i] not in opts or i + 1 >= len(argv):
            print(f"usage error near {argv[i]!r} — see --help", file=sys.stderr)
            return 2
        opts[argv[i]] = argv[i + 1]
        i += 2

    if not opts["--frontmatter"] or not opts["--filename"]:
        print("--frontmatter and --filename are required", file=sys.stderr)
        return 2
    try:
        max_per_type = int(opts["--max-per-type"])
        if max_per_type < 1:
            raise ValueError("must be >= 1")
    except ValueError as e:
        print(f"bad --max-per-type: {e}", file=sys.stderr)
        return 2

    try:
        fm_records = load(Path(opts["--frontmatter"]))
        fn_records = load(Path(opts["--filename"]))
        inbound = load(Path(opts["--index"]), dict) if opts["--index"] else None
    except (OSError, ValueError, TypeError) as e:
        # Exit 3, not 0-with-empty: an unreadable scan must never look like a clean vault.
        print(f"scan input unusable: {e}", file=sys.stderr)
        return 3

    payload = build_payload(fm_records, fn_records, inbound, max_per_type, date.today())
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
