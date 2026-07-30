#!/usr/bin/env python3
"""
Vault-audit detection validator (v4).

Mechanically applies the audit SKILL.md Phase 1 SCAN + Phase 2 CLASSIFY rules to
a fixture or live vault. Outputs per-type finding counts and a flat list of
finding records as JSON. Stdlib only.

v4 layout: inbox/ + notes/ + assets/  (no 00_Inbox, 20_Projects, 30_Notes)
Error types: E1-E12. E9 (#119) = tag/property vocabulary inconsistency, a
vault-LEVEL check (findings carry path:""); only deterministic sub-checks ship
(E9a singular/plural, E9b camel/snake property naming). E9c (semantic synonyms)
is out of scope, deferred to a separate issue.

E12 (#330) = wiki self-audit (v5 §7 U3). The rule has two halves, split on the
audit's LLM-0 (deterministic-only) boundary — the SAME split E9 makes:
  - E12a wiki staleness: `verified:` age > STALE_WIKI_DAYS. DETERMINISTIC (date
    arithmetic) → SHIPS here as E12_wiki_stale.
  - E12b cross-page semantic contradiction: two wiki pages asserting conflicting
    claims. NON-deterministic (needs LLM judgment) → OUT of scope for the
    reference impl, deferred to a `--deep` LLM opt-in exactly like E9c. Building a
    fake-deterministic contradiction heuristic would only manufacture false
    positives; staleness is the honest deterministic slice.

Usage:
  python3 audit-validate.py <vault_root>          # JSON summary on stdout
  python3 audit-validate.py <vault_root> --findings  # also emit findings list
  python3 audit-validate.py <vault_root> --dod    # DoD seeded-detection analysis

Exit code: always 0 unless the vault path is invalid (1).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

REQUIRED_FM_FIELDS = ("created", "tags", "type")
# status required for note/decision only (v4 §3.3 status machine)
STATUS_REQUIRED_TYPES = frozenset({"note", "decision"})
# Stagnation thresholds (v4 §6.1 Step 2).
STALE_INBOX_DAYS = 14
STALE_DRAFT_DAYS = 30
# E12 wiki staleness threshold (v5 §7 U3). A wiki page's `verified:` is auto-stamped
# on every write (v5 §4.1) — a last-touched signal, not active verification — so age
# past this bound flags a page that hasn't been re-compiled/re-touched in a quarter.
STALE_WIKI_DAYS = 90
# Inbox files with explicit non-raw status (e.g., session→active) are exempt from E6.
INBOX_RAW_STATUSES = frozenset({"", "raw"})
# Priority mapping per error type (v4 §6.1). P0 = 무결성, P1 = 정체, P2 = quality.
# This constant is the executable oracle; keep in sync with SKILL.md error-type table.
PRIORITY_BY_TYPE = {
    "E1_missing_frontmatter": "P0",
    "E2_missing_required_fields": "P0",
    "E3_filename_convention_violation": "P0",
    "E4_broken_wikilink": "P0",
    "E5_orphan_note": "P2",
    "E6_stale_inbox": "P1",
    "E7_stale_draft": "P1",
    "E8_promotion_candidate": "P2",
    "E9_tag_vocabulary_inconsistency": "P2",
    "E10_misplaced_file": "P1",
    "E11_unstructured_path": "P1",
    "E12_wiki_stale": "P1",
}
# E9 (#119) frequency threshold: report a vocabulary pair only when BOTH forms
# appear in this many files or more (per-form file count). Suppresses one-off
# typos and intentional distinct singulars (Risk-section mitigation).
E9_MIN_FILES = 3
# E9b camelCase marker: a lowercase letter immediately followed by an uppercase.
E9_CAMEL_RE = re.compile(r"[a-z][A-Z]")
# E10 type↔folder placement (v4 §3.1; v5 §3 adds wiki): each managed type lives in one folder.
EXPECTED_FOLDER = {
    "session": "inbox",
    "capture": "inbox",
    "note": "notes",
    "decision": "notes",
    "plan": "notes",
    "wiki": "wiki",
}
# E11 structural layout (v4 §3.1; v5 §3 adds wiki/): only these top-level folders are canonical.
# `wiki/` is the A-layer (LLM-compiled domain knowledge) — recognized here so wiki pages
# are NOT flagged as unstructured. Full wiki self-audit E-rules (contradiction / provenance
# gaps) are a separate slice (v5 §7); MVP only makes the folder canonical.
CANONICAL_FOLDERS = {"inbox", "notes", "assets", "wiki"}
# Files exempt from E11 (vault-level index lives at the root or any folder root).
EXEMPT_FILES = {"_index.md"}
# E5 candidate tuning (v4 §6.1): top-N tag-intersection candidates per orphan.
E5_CANDIDATE_TOP_N = 3
WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\]]*)?(?:\|[^\]]*)?\]\]")
# #434: mirrors ovm-primitives.sh's mask_code — [[...]] inside a code fence or inline
# code is a syntax example, not a link. The two copies are kept behaviourally identical;
# the E4 FP regression test drives BOTH over the same fixture.
# Each bound guards against over-masking, which is silent: a swallowed region stops E4
# reporting real broken links and manufactures E5 orphans. See ovm-primitives.sh for the
# full rationale — a closed fence opens and closes at any indent, only a column-0 fence
# runs to EOF unclosed, and an inline span never crosses a blank line.
CODE_FENCE = re.compile(r"^[ \t]*(?P<f>```+|~~~+)[^\n]*\n.*?^[ \t]*(?P=f)[`~]*[ \t\r]*$", re.S | re.M)
UNCLOSED_FENCE = re.compile(r"^(?P<f>```+|~~~+)[^\n]*\n.*\Z", re.S | re.M)
INLINE_CODE = re.compile(r"(?P<t>`+)(?:(?!(?P=t))(?:[^\n]|\n(?!\s*\n)))+(?P=t)")


def mask_code(text: str) -> str:
    return INLINE_CODE.sub("", UNCLOSED_FENCE.sub("", CODE_FENCE.sub("", text)))


def parse_frontmatter(content: str) -> Optional[dict]:
    if not content.startswith("---\n"):
        return None
    end_marker = content.find("\n---\n", 4)
    if end_marker == -1:
        return None
    body = content[4:end_marker]
    result: dict = {}
    current_key: Optional[str] = None
    current_list: Optional[list] = None
    for line in body.split("\n"):
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            item = stripped[2:].strip().strip("\"'")
            if current_key and current_list is not None:
                current_list.append(item)
                result[current_key] = current_list
            continue
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).rstrip()
        if value == "":
            current_key = key
            current_list = []
            result[key] = []
        elif value.startswith("["):
            inner = value.strip().lstrip("[").rstrip("]")
            items = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
            result[key] = items
            current_key, current_list = None, None
        else:
            result[key] = value.strip().strip("\"'")
            current_key, current_list = None, None
    return result


def filename_conforms(rel: Path) -> bool:
    """
    v4 filename convention check.

    - inbox/ and assets/ are exempt (raw input / attachments)
    - notes/ (any depth): VIOLATION if filename starts with YYYY-MM- (v3 date-first)
    - _index.md is always valid
    """
    if rel.name == "_index.md":
        return True
    top = rel.parts[0]
    if top in ("inbox", "assets"):
        return True
    if top == "notes":
        return not re.match(r"^\d{4}-\d{2}-", rel.name)
    return True


def _slug_from_filename(rel: Path) -> str:
    """Extract the user-chosen slug from a non-conforming filename.

    The filename is the source of truth for the slug (created: carries only the
    date). Strip a leading date prefix (YYYY-MM-DD- or YYYY-MM-) and a leading
    {type}- prefix if present, leaving the human-meaningful slug.
    """
    stem = rel.stem
    # Strip leading YYYY-MM-DD- or YYYY-MM- date prefix (v3 date-first artifact).
    stem = re.sub(r"^\d{4}-\d{2}(?:-\d{2})?-", "", stem)
    # Strip a single leading {type}- prefix so we don't double it on rebuild.
    stem = re.sub(r"^(?:note|decision|plan|capture|session)-", "", stem)
    return stem


def _compute_suggested_filename(rel: Path, fm: dict) -> Optional[str]:
    """Compute a v4-conforming filename suggestion for an E3 violation.

    note            → {slug}.md            (date prefix removed)
    decision / plan → {type}-{YYYY-MM-DD}-{slug}.md
    capture / session → {type}-{YYYY-MM-DD}.md
    missing type: or created: → None       (cannot suggest; keep base message)
    """
    ftype = fm.get("type")
    created = fm.get("created")
    if not isinstance(ftype, str) or not ftype:
        return None
    created_d = parse_created_date(created)
    if ftype == "note":
        slug = _slug_from_filename(rel)
        if not slug:
            return None
        return f"{slug}.md"
    if created_d is None:
        return None
    date_str = created_d.isoformat()
    if ftype in ("decision", "plan"):
        slug = _slug_from_filename(rel)
        if not slug:
            return f"{ftype}-{date_str}.md"
        return f"{ftype}-{date_str}-{slug}.md"
    if ftype in ("capture", "session"):
        return f"{ftype}-{date_str}.md"
    return None


# #127 E2 auto-fix tag inference. Deterministic, no LLM.
# Words that survive slug splitting but carry no semantic value as tags.
# Kept tiny + conservative (the audit only proposes; the user confirms).
INFER_STOPWORDS = frozenset({"the", "a", "an", "of", "and", "or", "to", "for"})


def infer_tags(rel: Path, fm: dict) -> list:
    """Infer a conservative tag proposal for an E2 missing-`tags:` fix (#127).

    Three deterministic tiers, in order; duplicates removed, original order kept:
      Tier 1 — `type:` field      → always the first tag (type: note → note)
      Tier 2 — filename slug      → meaningful words after stripping the date
                                    and the {type}- prefix, split on `-`/`_`
      Tier 3 — parent folder      → notes/{domain}/... → add `domain`

    All tokens are lowercased; stopwords and pure-numeric tokens are dropped so
    the result plausibly passes a future E9 vocabulary check (#119, still open):
    lowercase, kebab-friendly atoms, no duplicates. An empty slug (date-only
    filename) gracefully falls back to the type tag only — never crashes.
    """
    tags: list = []

    def _push(tok: str) -> None:
        tok = tok.strip().lower()
        if not tok or tok in INFER_STOPWORDS or tok.isdigit():
            return
        if tok not in tags:
            tags.append(tok)

    # Tier 1: type field (always first when present).
    ftype = fm.get("type")
    if isinstance(ftype, str) and ftype.strip():
        _push(ftype)

    # Tier 2: filename slug words (date + type prefix already stripped by
    # _slug_from_filename), split on `-` / `_`.
    slug = _slug_from_filename(rel)
    if slug:
        for word in re.split(r"[-_]+", slug):
            _push(word)

    # Tier 3: parent folder domain. Only meaningful inside notes/{domain}/...,
    # where parts == ("notes", "{domain}", ..., "file.md"). The immediate
    # vault-root folder ("notes") itself is structural, not a domain.
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "notes":
        _push(parts[1])

    return tags


def simulate_e2_autofix(rel: Path, fm: dict) -> dict:
    """Simulate the E2 OPTIONAL-FIX tag inference for one finding (#127).

    Mirrors what `ovm-primitives.sh infer-tags` would propose. Returns the
    inferred `tags` list plus the missing-field set the fix would populate.
    This is a *proposal* preview only — the production skill keeps the
    "수정 실행" confirmation gate; nothing is auto-committed here.
    """
    inferred = infer_tags(rel, fm)
    missing = []
    for f in REQUIRED_FM_FIELDS:
        if f not in fm or fm[f] in (None, ""):
            missing.append(f)
    if fm.get("type") in STATUS_REQUIRED_TYPES and (
        "status" not in fm or fm["status"] in (None, "")
    ):
        missing.append("status")
    return {"inferred_tags": inferred, "missing_fields": missing}


def collect(vault: Path) -> dict:
    fm_records: list = []
    files: list = []
    inbound: dict = {}
    wikilinks_by_file: dict = {}
    all_stems: set = set()

    for path in sorted(vault.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(vault).parts):
            continue
        rel = path.relative_to(vault)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        files.append(rel)
        all_stems.add(path.stem.lower())

        fm = parse_frontmatter(content)
        has_fm = fm is not None
        missing_required: list = []
        if has_fm:
            for f in REQUIRED_FM_FIELDS:
                if f not in fm or fm[f] in (None, ""):
                    missing_required.append(f)
            # status required for note/decision (v4 §3.3)
            if fm.get("type") in STATUS_REQUIRED_TYPES and (
                "status" not in fm or fm["status"] in (None, "")
            ):
                missing_required.append("status")
        fm_records.append(
            {
                "rel": str(rel),
                "has_fm": has_fm,
                "missing_required": missing_required,
                "fm": fm or {},
            }
        )

        for m in WIKILINK_PATTERN.finditer(mask_code(content)):
            target = m.group(1).strip().lower()
            inbound.setdefault(target, set()).add(str(rel))
            wikilinks_by_file.setdefault(str(rel), []).append(target)

    return {
        "fm_records": fm_records,
        "files": [str(f) for f in files],
        "all_stems": all_stems,
        "inbound": {k: sorted(v) for k, v in inbound.items()},
        "wikilinks_by_file": wikilinks_by_file,
        "vault": vault,
    }


def parse_created_date(value) -> Optional[date]:
    """Parse YYYY-MM-DD string into a date. Returns None on any parse failure."""
    if not isinstance(value, str):
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def detect_stale_wiki(fm_records: list, today: date, stale_days: int = STALE_WIKI_DAYS) -> list:
    """E12a: return (rel, detail) for wiki/ pages whose `verified:` age > stale_days.

    Deterministic reference-impl slice of the E12 wiki self-audit rule (v5 §7 U3).
    Scoped to genuine wiki pages only (top folder `wiki/` AND `type: wiki`) so a
    stray old `verified:` on a non-wiki file is never flagged. Pages with a
    missing/unparseable `verified:` are SKIPPED: staleness is uncomputable without
    it, and the field is auto-stamped on every wiki write (v5 §4.1) so absence is
    near-impossible in practice (an absent field is a write-path bug, not a staleness
    signal). Cross-page semantic contradiction (E12b) is the deferred `--deep` path.
    """
    findings: list = []
    for rec in fm_records:
        rel_path = Path(rec["rel"])
        if not rel_path.parts or rel_path.parts[0] != "wiki":
            continue
        fm = rec.get("fm") or {}
        if fm.get("type") != "wiki":
            continue
        verified = parse_created_date(fm.get("verified"))
        if verified is None:
            continue
        age_days = (today - verified).days
        if age_days > stale_days:
            findings.append((
                rec["rel"],
                f"verified {age_days}d old > {stale_days}d (verified {fm.get('verified')}) "
                f"— recompile or re-verify the page",
            ))
    return findings


def _promotion_candidates_from_manifest(vault: Path) -> list:
    """Return manifest entries with promotion_candidate=True for E8 classification.

    Silently skips pre-v3 manifests (schema_version gate introduced in PR 4c).
    Each result carries refs_in and access_count for detail construction.
    """
    path = vault / ".vault-bridge" / "manifest.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    schema_version = data.get("schema_version", 1)
    if not (isinstance(schema_version, int) and schema_version >= 3):
        return []
    results = []
    for f in data.get("files") or []:
        if f.get("promotion_candidate") is not True:
            continue
        rel = f.get("path", "")
        # Skip stale manifest entries: file deleted since last manifest refresh
        # would otherwise surface as a phantom E8 finding.
        if not rel or not (vault / rel).is_file():
            continue
        results.append({
            "rel": rel,
            "type": f.get("type", ""),
            "refs_in": f.get("references_in", 0),
            "access_count": f.get("access_count", 0),
        })
    return results


def _camel_to_snake(key: str) -> str:
    """Infer the snake_case equivalent of a camelCase key (E9b, #119).

    `sourceUrl` → `source_url`, `createdAtTime` → `created_at_time`. Lowercased.
    A key with no camel boundary maps to its own lowercase form (caller skips
    the self == inferred case).
    """
    return re.sub(r"([a-z])([A-Z])", r"\1_\2", key).lower()


def detect_vocabulary_pairs(fm_records: list) -> list:
    """E9 (#119): vault-wide tag/property vocabulary inconsistency detection.

    Deterministic, no LLM. Two sub-checks, each emitting vault-level pairs
    (one finding per pair, `path: ""`):

      E9a singular/plural — aggregate lowercase tags vault-wide; if a tag `t`
        and its regular `+s` plural `t+"s"` are BOTH present, report the pair.
        Only the literal `t+"s"` is paired, so irregular plurals (leaf/leaves,
        status/statuses) are excluded by construction — no morphology table.

      E9b property naming — aggregate frontmatter keys vault-wide; for each
        camelCase key (`[a-z][A-Z]`), infer the snake_case equivalent; if BOTH
        the camel and snake forms appear, report the pair.

    FP guard (E9_MIN_FILES = 3): a pair is reported only when BOTH forms appear
    in >= E9_MIN_FILES files (per-form file count, deduped per file). Returns a
    list of {sub, a, b, a_files, b_files} dicts in deterministic order.
    """
    tag_files: dict = {}   # lowercase tag → set(file paths)
    key_files: dict = {}   # frontmatter key → set(file paths)
    for rec in fm_records:
        fm = rec.get("fm") or {}
        path = rec.get("rel", "")
        raw_tags = fm.get("tags")
        if isinstance(raw_tags, list):
            for t in raw_tags:
                if isinstance(t, str) and t.strip():
                    tag_files.setdefault(t.strip().lower(), set()).add(path)
        for k in fm.keys():
            key_files.setdefault(k, set()).add(path)

    pairs: list = []

    # E9a — singular/plural tags.
    seen: set = set()
    for t in sorted(tag_files):
        plural = t + "s"
        if plural not in tag_files:
            continue
        if t in seen or plural in seen:
            continue
        if len(tag_files[t]) >= E9_MIN_FILES and len(tag_files[plural]) >= E9_MIN_FILES:
            pairs.append({
                "sub": "E9a",
                "a": t, "b": plural,
                "a_files": len(tag_files[t]), "b_files": len(tag_files[plural]),
            })
            seen.add(t)
            seen.add(plural)

    # E9b — camelCase vs snake_case property keys.
    # E9b: no `seen` set needed — each camelCase key has exactly one snake_case form.
    for camel in sorted(key_files):
        if not E9_CAMEL_RE.search(camel):
            continue
        snake = _camel_to_snake(camel)
        if snake == camel or snake not in key_files:
            continue
        if len(key_files[camel]) >= E9_MIN_FILES and len(key_files[snake]) >= E9_MIN_FILES:
            pairs.append({
                "sub": "E9b",
                "a": camel, "b": snake,
                "a_files": len(key_files[camel]), "b_files": len(key_files[snake]),
            })

    return pairs


def classify(bundle: dict) -> dict:
    findings: list = []
    today = date.today()

    def add(etype: str, rel: str, detail: str = "", **extra) -> None:
        rec = {
            "type": etype,
            "priority": PRIORITY_BY_TYPE.get(etype, "P_UNKNOWN"),
            "path": rel,
            "detail": detail,
        }
        rec.update(extra)
        findings.append(rec)

    # E1 + E2: frontmatter presence and required fields
    # (dotfiles already excluded in collect())
    for rec in bundle["fm_records"]:
        if not rec["has_fm"]:
            add("E1_missing_frontmatter", rec["rel"])
        elif rec["missing_required"]:
            # #127: attach the OPTIONAL-FIX tag proposal so REPORT can preview
            # "추론된 태그: [...]" and the DoD harness can verify non-empty
            # inference. Inference is a proposal — the skill still gates on
            # "수정 실행"; nothing is auto-committed here.
            inferred = (
                infer_tags(Path(rec["rel"]), rec.get("fm") or {})
                if "tags" in rec["missing_required"]
                else []
            )
            add("E2_missing_required_fields", rec["rel"],
                ",".join(rec["missing_required"]), inferred_tags=inferred)

    # E3: filename convention violation (v4: date-first prefix in notes/)
    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if not filename_conforms(rel_path):
            fm = rec.get("fm") or {}
            suggested = _compute_suggested_filename(rel_path, fm)
            detail = ""
            if suggested:
                detail = f"권장 파일명: {suggested}"
            add("E3_filename_convention_violation", str(rel_path), detail)

    # E4: broken wikilinks
    for rel, targets in bundle["wikilinks_by_file"].items():
        for target in targets:
            if target not in bundle["all_stems"]:
                add("E4_broken_wikilink", rel, target)

    # E5: orphan notes in notes/ (any depth).
    # Pre-build a notes/ tag index once (avoids O(N²) re-scan inside the loop).
    # Index entry: (rel_str, frozenset(tags)). Only notes/ files with non-empty
    # tags are candidate targets for connection suggestions.
    notes_tag_index: list = []
    for rec in bundle["fm_records"]:
        rp = Path(rec["rel"])
        if rp.name == "_index.md" or not rp.parts or rp.parts[0] != "notes":
            continue
        fm = rec.get("fm") or {}
        raw_tags = fm.get("tags")
        tagset = frozenset(
            t for t in raw_tags if isinstance(t, str) and t
        ) if isinstance(raw_tags, list) else frozenset()
        notes_tag_index.append((rec["rel"], tagset))

    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if rel_path.name == "_index.md" or rel_path.parts[0] != "notes":
            continue
        stem = rel_path.stem.lower()
        sources = [s for s in bundle["inbound"].get(stem, []) if s != rec["rel"]]
        if sources:
            continue
        # Compute tag-intersection candidates (exact match only, top-N).
        fm = rec.get("fm") or {}
        raw_tags = fm.get("tags")
        orphan_tags = frozenset(
            t for t in raw_tags if isinstance(t, str) and t
        ) if isinstance(raw_tags, list) else frozenset()
        candidates: list = []
        if orphan_tags:
            scored = []
            for cand_rel, cand_tags in notes_tag_index:
                if cand_rel == rec["rel"]:
                    continue
                shared = orphan_tags & cand_tags
                if shared:
                    scored.append((len(shared), cand_rel, sorted(shared)))
            # Sort: shared count desc, then path asc.
            scored.sort(key=lambda x: (-x[0], x[1]))
            for _, cand_rel, shared_sorted in scored[:E5_CANDIDATE_TOP_N]:
                candidates.append({"path": cand_rel, "shared_tags": shared_sorted})

        if candidates:
            rendered = "; ".join(
                f"[[{Path(c['path']).stem}]] (공유 태그: {', '.join(c['shared_tags'])})"
                for c in candidates
            )
            detail = f"연결 후보: {rendered}"
        else:
            detail = "연결 후보 없음 (공유 태그 없음)"
        add("E5_orphan_note", rec["rel"], detail, candidates=candidates)

    # E6 + E7: stagnation (v4 §6.1 Step 2). Uses frontmatter `created:` —
    # mtime is unreliable across git clones.
    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        fm = rec.get("fm") or {}
        if not rel_path.parts:
            continue
        top = rel_path.parts[0]
        created = parse_created_date(fm.get("created"))
        if created is None:
            continue
        age_days = (today - created).days
        raw_status = fm.get("status")
        # Non-string status (e.g., list from `status: [raw]` YAML) is treated
        # as absent — the audit's job is to flag malformed status via E1/E2.
        status = raw_status.strip() if isinstance(raw_status, str) else ""

        # E6/E7 are mutually exclusive (top folder is a single value).
        if top == "inbox":
            if status in INBOX_RAW_STATUSES and age_days > STALE_INBOX_DAYS:
                add("E6_stale_inbox", rec["rel"],
                    f"age {age_days}d > {STALE_INBOX_DAYS}d (status:{status or 'none'}, created {fm.get('created')})")
        elif top == "notes" and rel_path.name != "_index.md":
            if status == "draft" and age_days > STALE_DRAFT_DAYS:
                add("E7_stale_draft", rec["rel"],
                    f"age {age_days}d > {STALE_DRAFT_DAYS}d (status:draft, created {fm.get('created')})")

    # E12a: wiki staleness (v5 §7 U3) — deterministic slice of the wiki self-audit
    # rule. Semantic cross-page contradiction (E12b) is the deferred --deep LLM path.
    for rel, detail in detect_stale_wiki(bundle["fm_records"], today):
        add("E12_wiki_stale", rel, detail)

    # E10 + E11 prep: set of files already flagged for E1/E2 (integrity defects).
    # Misplaced/unstructured checks skip these — fix integrity first.
    integrity_flagged = {
        f["path"] for f in findings
        if f["type"] in ("E1_missing_frontmatter", "E2_missing_required_fields")
    }

    # E10: misplaced_file — type↔folder placement mismatch (v4 §3.1).
    # Skip files with E1/E2 (no reliable type), exempt assets/ and hidden dirs.
    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if rec["rel"] in integrity_flagged:
            continue
        if not rel_path.parts:
            continue
        top = rel_path.parts[0]
        if top.startswith(".") or top == "assets":
            continue
        # E11 (unstructured) owns non-canonical folders and root-direct files;
        # type↔folder placement is only meaningful within canonical folders.
        if "/" not in rec["rel"] or top not in CANONICAL_FOLDERS:
            continue
        fm = rec.get("fm") or {}
        ftype = fm.get("type")
        if not isinstance(ftype, str):
            continue
        expected = EXPECTED_FOLDER.get(ftype)
        if expected is None:
            continue
        if top != expected:
            add("E10_misplaced_file", rec["rel"],
                f"type:{ftype} expected in {expected}/ but found in {top}/")

    # E11: unstructured_path — file outside canonical top-level folders (v4 §3.1).
    # Root-direct files are included; _index.md and hidden dirs are exempt.
    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if rel_path.name in EXEMPT_FILES:
            continue
        if not rel_path.parts:
            continue
        # Root-direct file (no folder component): top folder is the file itself.
        if "/" not in rec["rel"]:
            add("E11_unstructured_path", rec["rel"],
                "root-direct file outside canonical folders (inbox/notes/assets/wiki)")
            continue
        top = rel_path.parts[0]
        if top.startswith("."):
            continue
        if top in CANONICAL_FOLDERS:
            continue
        add("E11_unstructured_path", rec["rel"],
            f"top folder '{top}/' is not canonical (inbox/notes/assets/wiki)")

    # E8: promotion candidates from manifest (schema_version ≥ 3 only).
    # note/decision meeting refs_in or access_count thresholds — manual
    # status→evergreen. capture meeting access_count only (Model X, no
    # references_in signal) — recalled ore, no status field to flip; the
    # next action is /note or /wiki, not a status edit.
    for cand in _promotion_candidates_from_manifest(bundle["vault"]):
        r = cand["refs_in"]
        a = cand["access_count"]
        if cand["type"] == "capture":
            detail = f"refs_in={r}, access={a} (recalled capture ore — consider /note or /wiki to promote)"
        else:
            detail = f"refs_in={r}, access={a} (manual: status→evergreen)"
        add("E8_promotion_candidate", cand["rel"], detail)

    # E9: tag/property vocabulary inconsistency (#119). Vault-LEVEL findings —
    # path is "" because the inconsistency is a property of the vault, not of
    # one file. Each detected pair is one finding (DoD counts pairs). The
    # carried `sub`/`a`/`b`/file-count fields let REPORT render the Korean
    # detail and a future test assert sub-check breakdown.
    for pair in detect_vocabulary_pairs(bundle["fm_records"]):
        if pair["sub"] == "E9a":
            detail = (f"태그 단복수 혼용: '{pair['a']}' ({pair['a_files']}개 파일) ↔ "
                      f"'{pair['b']}' ({pair['b_files']}개 파일) — 정준 형태를 하나로 통일하세요")
        else:
            detail = (f"프로퍼티 이름 혼용(camel/snake): '{pair['a']}' ({pair['a_files']}개 파일) ↔ "
                      f"'{pair['b']}' ({pair['b_files']}개 파일) — 정준 형태를 하나로 통일하세요")
        add("E9_tag_vocabulary_inconsistency", "", detail,
            sub=pair["sub"], form_a=pair["a"], form_b=pair["b"])

    counts: dict = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return {"counts": counts, "findings": findings, "total": len(findings)}


# DoD seed prefixes: (field_to_check, prefix_in_that_field).
# Detection uses `if prefix in candidate` (substring containment, not startswith).
# E2 seeds: both "audit-e2-missing-fields-XXX" and "audit-e2-status-missing-XXX"
# match the "audit-e2-" prefix via containment → seeded_detected.E2 expects 10.
SEED_PREFIXES = {
    "E1_missing_frontmatter": ("path", "audit-e1-"),
    "E2_missing_required_fields": ("path", "audit-e2-"),
    "E3_filename_convention_violation": ("path", "audit-e3-"),
    "E4_broken_wikilink": ("path", "audit-e4-"),
    "E5_orphan_note": ("path", "audit-e5-"),
    "E6_stale_inbox": ("path", "audit-e6-"),
    "E7_stale_draft": ("path", "audit-e7-"),
    "E8_promotion_candidate": ("path", "audit-e8-"),
    "E10_misplaced_file": ("path", "audit-e10-"),
    "E11_unstructured_path": ("path", "audit-e11-"),
    "E12_wiki_stale": ("path", "audit-e12-"),
}


# E9 (#119) is a vault-LEVEL check: every finding carries path:"" so the
# path-prefix SEED_PREFIXES mechanism cannot reach it. The DoD counting unit for
# E9 is the PAIR (each detected pair = one finding = +1 toward seeded_detected),
# and fp_on_clean.E9 stays 0 because clean-fixture notes never form a pair.
E9_TYPE = "E9_tag_vocabulary_inconsistency"


def dod_report(findings: list) -> dict:
    detected: dict = {k: 0 for k in SEED_PREFIXES}
    fp_clean: dict = {k: 0 for k in SEED_PREFIXES}
    # E9 is path-less → counted by pair, separate from the prefix mechanism.
    detected[E9_TYPE] = 0
    fp_clean[E9_TYPE] = 0
    priority_counts: dict = {"P0": 0, "P1": 0, "P2": 0}
    findings_missing_priority: int = 0
    priority_mismatches: list = []
    # #126/#130: count display-only suggestion/candidate enrichment so the
    # DoD report is self-contained (E2E also asserts via --findings).
    e3_with_suggestion: int = 0
    e5_with_candidates: int = 0
    # #127: count E2 findings whose tags: would be inferred (proposal preview).
    # e2_tags_missing = E2 findings where `tags` is among the missing fields;
    # e2_with_inferred_tags = of those, how many got a NON-EMPTY tag proposal.
    # The two are equal when inference never degenerates to an empty list.
    e2_tags_missing: int = 0
    e2_with_inferred_tags: int = 0

    for f in findings:
        if f["type"] == "E3_filename_convention_violation" and "권장 파일명" in (f.get("detail") or ""):
            e3_with_suggestion += 1
        if f["type"] == "E5_orphan_note" and f.get("candidates"):
            e5_with_candidates += 1
        if f["type"] == "E2_missing_required_fields" and "tags" in (f.get("detail") or ""):
            e2_tags_missing += 1
            if f.get("inferred_tags"):
                e2_with_inferred_tags += 1

        etype = f["type"]
        prio = f.get("priority")
        if prio in priority_counts:
            priority_counts[prio] += 1
        else:
            findings_missing_priority += 1

        # Drift detector: verify each seeded finding has the expected priority.
        expected_prio = PRIORITY_BY_TYPE.get(etype)
        if expected_prio is not None and prio != expected_prio:
            priority_mismatches.append({
                "type": etype,
                "path": f.get("path", ""),
                "expected": expected_prio,
                "got": prio,
            })

        # E9 is path-less (vault-level): count every finding as one detected
        # pair. It can never carry an "audit-clean-" path, so fp_on_clean.E9
        # stays 0 (clean-fixture notes don't form vocabulary pairs).
        if etype == E9_TYPE:
            detected[E9_TYPE] += 1
            continue

        marker = SEED_PREFIXES.get(etype)
        if marker is None:
            continue
        field, prefix = marker
        candidate = f.get(field, "") or ""
        if prefix in candidate:
            detected[etype] += 1
        elif "audit-clean-" in (f.get("path") or ""):
            fp_clean[etype] += 1

    return {
        "seeded_detected": detected,
        "fp_on_clean": fp_clean,
        "priority_counts": priority_counts,
        "findings_missing_priority": findings_missing_priority,
        "priority_mismatches": priority_mismatches,
        "e3_with_suggestion": e3_with_suggestion,
        "e5_with_candidates": e5_with_candidates,
        "e2_tags_missing": e2_tags_missing,
        "e2_with_inferred_tags": e2_with_inferred_tags,
    }


def read_manifest_summary(vault: Path) -> Optional[dict]:
    """Read .vault-bridge/manifest.json if present.

    Returns summary dict or None. promotion_candidate_count is None for
    pre-v3 manifests (field not available), and an integer (possibly 0) for
    v3+ manifests so callers can distinguish "unavailable" from "no candidates".
    """
    path = vault / ".vault-bridge" / "manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    schema_version = data.get("schema_version", 1)
    if isinstance(schema_version, int) and schema_version >= 3:
        files = data.get("files") or []
        promotion_count: Optional[int] = sum(
            1 for f in files if f.get("promotion_candidate") is True
        )
    else:
        promotion_count = None

    return {
        "file_count": data.get("file_count"),
        "generated_at": data.get("generated_at"),
        "schema_version": data.get("schema_version"),
        "promotion_candidate_count": promotion_count,
    }


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _git_activity_summary(vault: Path, days: int = 7) -> Optional[dict]:
    """Return git activity stats for the vault over the last N days, or None on any failure.

    Caller is responsible for resolving any env var override (e.g., VAULT_AUDIT_ACTIVITY_DAYS).
    """
    since = f"{days} days ago"
    try:
        # Count commits
        r_commits = subprocess.run(
            ["git", "-C", str(vault), "log", f"--since={since}", "--oneline"],
            capture_output=True, text=True, timeout=10,
        )
        if r_commits.returncode != 0:
            return None
        commits = len([line for line in r_commits.stdout.splitlines() if line.strip()])

        # Count file-level changes
        r_files = subprocess.run(
            ["git", "-C", str(vault), "log", f"--since={since}",
             "--pretty=format:", "--name-status"],
            capture_output=True, text=True, timeout=10,
        )
        if r_files.returncode != 0:
            return None

        added = modified = deleted = 0
        for line in r_files.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            status = line[0].upper()
            if status == "A":
                added += 1
            elif status == "M":
                modified += 1
            elif status == "D":
                deleted += 1
            elif status in ("R", "C"):
                modified += 1

        return {"days": days, "commits": commits, "added": added,
                "modified": modified, "deleted": deleted}
    except FileNotFoundError:
        return None  # git not in PATH
    except Exception:
        return None


def _infer_self_test() -> int:
    """Deterministic self-test of the #127 E2 tag inference (no fixture needed).

    Asserts the three-tier behavior + graceful empty-slug fallback. Returns 0
    on pass, 1 on any mismatch. Slug words are split on `-`/`_` per the G9
    goal-doc S6 spec, so a multi-word slug yields one tag per word.
    """
    cases = [
        # (rel, fm, expected_tags)
        ("notes/llm/decision-2026-04-12-context-window.md",
         {"type": "decision", "created": "2026-04-12"},
         ["decision", "context", "window", "llm"]),
        ("inbox/capture-2026-05-01-obsidian-api.md",
         {"type": "capture", "created": "2026-05-01"},
         ["capture", "obsidian", "api"]),
        # Tier-3 only fires for notes/{domain}/...; inbox/ has no domain folder.
        ("notes/some-topic.md",
         {"type": "note", "created": "2026-04-01"},
         ["note", "some", "topic"]),
        # Graceful empty slug: date-only filename → type tag only, no crash.
        ("inbox/session-2026-04-12.md",
         {"type": "session", "created": "2026-04-12"},
         ["session"]),
        # No type field → slug + domain only (type tier skipped, no crash).
        ("notes/db/index-tuning.md",
         {"created": "2026-04-01"},
         ["index", "tuning", "db"]),
        # Duplicate dedup: slug word equals domain → appears once.
        ("notes/llm/llm-routing.md",
         {"type": "note", "created": "2026-04-01"},
         ["note", "llm", "routing"]),
    ]
    failures = 0
    for rel_str, fm, expected in cases:
        got = infer_tags(Path(rel_str), fm)
        status = "OK" if got == expected else "FAIL"
        if got != expected:
            failures += 1
        print(f"[{status}] {rel_str}: got={got} expected={expected}")

    # E2 auto-fix simulation case: a file missing `tags:` must receive a
    # NON-EMPTY proposal, and the fix must report `tags` among the fields it
    # would populate. (#127 acceptance: inferred result, not an empty array.)
    sim = simulate_e2_autofix(
        Path("notes/llm/decision-2026-04-12-context-window.md"),
        {"type": "decision", "created": "2026-04-12"},  # tags + status missing
    )
    if not sim["inferred_tags"]:
        failures += 1
        print("[FAIL] E2 sim: inferred_tags is empty (expected non-empty proposal)")
    elif sim["inferred_tags"][0] != "decision":
        failures += 1
        print(f"[FAIL] E2 sim: first tag != type ({sim['inferred_tags']})")
    elif "tags" not in sim["missing_fields"] or "status" not in sim["missing_fields"]:
        failures += 1
        print(f"[FAIL] E2 sim: missing_fields wrong ({sim['missing_fields']})")
    else:
        print(f"[OK] E2 sim: inferred_tags={sim['inferred_tags']} "
              f"missing_fields={sim['missing_fields']}")

    if failures:
        print(f"FAIL: {failures} infer-tags self-test case(s) failed", file=sys.stderr)
        return 1
    print(f"OK: all {len(cases)} infer-tags cases + E2 auto-fix simulation passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("vault", nargs="?")
    ap.add_argument("--findings", action="store_true")
    ap.add_argument("--dod", action="store_true",
                    help="Emit DoD analysis (seeded detection + FP on clean subset)")
    ap.add_argument("--infer-self-test", action="store_true",
                    help="Run the #127 E2 tag-inference self-test and exit")
    args = ap.parse_args()

    if args.infer_self_test:
        return _infer_self_test()
    if args.vault is None:
        ap.error("vault path is required unless --infer-self-test is given")

    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"ERROR: not a directory: {vault}", file=sys.stderr)
        return 1

    bundle = collect(vault)
    result = classify(bundle)

    manifest = read_manifest_summary(vault)
    activity_days = _env_int("VAULT_AUDIT_ACTIVITY_DAYS", 7)
    git_activity = _git_activity_summary(vault, days=activity_days)
    output: dict = {
        "vault": str(vault),
        "total_findings": result["total"],
        "counts": dict(sorted(result["counts"].items())),
        "manifest": manifest,
        "git_activity": git_activity,
    }
    if args.dod:
        output["dod"] = dod_report(result["findings"])
    if args.findings:
        output["findings"] = result["findings"]
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
