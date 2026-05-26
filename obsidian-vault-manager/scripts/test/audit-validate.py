#!/usr/bin/env python3
"""
Vault-audit detection validator (v4).

Mechanically applies the audit SKILL.md Phase 1 SCAN + Phase 2 CLASSIFY rules to
a fixture or live vault. Outputs per-type finding counts and a flat list of
finding records as JSON. Stdlib only.

v4 layout: inbox/ + notes/ + assets/  (no 00_Inbox, 20_Projects, 30_Notes)
Error types: E1-E5 only (E6-E9 project-binding checks removed in v4)

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
import sys
from pathlib import Path
from typing import Optional

REQUIRED_FM_FIELDS = ("created", "tags", "type")
# status required for note/decision only (v4 §3.3 status machine)
STATUS_REQUIRED_TYPES = frozenset({"note", "decision"})
# Priority mapping per error type (v4 §6.1). P0 = 무결성 (integrity), P2 = quality.
# P1 is reserved for stagnation checks (Step 2, future PR).
# This constant is the executable oracle; keep in sync with SKILL.md error-type table.
PRIORITY_BY_TYPE = {
    "E1_missing_frontmatter": "P0",
    "E2_missing_required_fields": "P0",
    "E3_filename_convention_violation": "P0",
    "E4_broken_wikilink": "P0",
    "E5_orphan_note": "P2",
}
WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\]]*)?(?:\|[^\]]*)?\]\]")


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

        for m in WIKILINK_PATTERN.finditer(content):
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


def classify(bundle: dict) -> dict:
    findings: list = []

    def add(etype: str, rel: str, detail: str = "") -> None:
        findings.append({
            "type": etype,
            "priority": PRIORITY_BY_TYPE.get(etype, "P_UNKNOWN"),
            "path": rel,
            "detail": detail,
        })

    # E1 + E2: frontmatter presence and required fields
    # (dotfiles already excluded in collect())
    for rec in bundle["fm_records"]:
        if not rec["has_fm"]:
            add("E1_missing_frontmatter", rec["rel"])
        elif rec["missing_required"]:
            add("E2_missing_required_fields", rec["rel"], ",".join(rec["missing_required"]))

    # E3: filename convention violation (v4: date-first prefix in notes/)
    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if not filename_conforms(rel_path):
            add("E3_filename_convention_violation", str(rel_path))

    # E4: broken wikilinks
    for rel, targets in bundle["wikilinks_by_file"].items():
        for target in targets:
            if target not in bundle["all_stems"]:
                add("E4_broken_wikilink", rel, target)

    # E5: orphan notes in notes/ (any depth)
    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if rel_path.name == "_index.md" or rel_path.parts[0] != "notes":
            continue
        stem = rel_path.stem.lower()
        sources = [s for s in bundle["inbound"].get(stem, []) if s != rec["rel"]]
        if not sources:
            add("E5_orphan_note", rec["rel"])

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
}


def dod_report(findings: list) -> dict:
    detected: dict = {k: 0 for k in SEED_PREFIXES}
    fp_clean: dict = {k: 0 for k in SEED_PREFIXES}
    priority_counts: dict = {"P0": 0, "P1": 0, "P2": 0}
    findings_missing_priority: int = 0
    priority_mismatches: list = []

    for f in findings:
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
    }


def read_manifest_summary(vault: Path) -> Optional[dict]:
    """Read .vault-bridge/manifest.json if present. Returns {file_count, generated_at} or None."""
    path = vault / ".vault-bridge" / "manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return {
        "file_count": data.get("file_count"),
        "generated_at": data.get("generated_at"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--findings", action="store_true")
    ap.add_argument("--dod", action="store_true",
                    help="Emit DoD analysis (seeded detection + FP on clean subset)")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    if not vault.is_dir():
        print(f"ERROR: not a directory: {vault}", file=sys.stderr)
        return 1

    bundle = collect(vault)
    result = classify(bundle)

    manifest = read_manifest_summary(vault)
    output: dict = {
        "vault": str(vault),
        "total_findings": result["total"],
        "counts": dict(sorted(result["counts"].items())),
        "manifest": manifest,
    }
    if args.dod:
        output["dod"] = dod_report(result["findings"])
    if args.findings:
        output["findings"] = result["findings"]
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
