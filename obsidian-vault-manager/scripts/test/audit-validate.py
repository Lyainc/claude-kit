#!/usr/bin/env python3
"""
Vault-audit detection validator.

Mechanically applies the SKILL.md Phase 1 SCAN + Phase 2 CLASSIFY rules to
a fixture or live vault. Outputs per-type finding counts and a flat list of
finding records as JSON. Stdlib only.

Usage:
  python3 audit-validate.py <vault_root>          # JSON summary on stdout
  python3 audit-validate.py <vault_root> --findings  # also emit findings list

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
FILENAME_PATTERN = re.compile(
    r"^(?:capture|session|project)-\d{4}-\d{2}-\d{2}(?:-[a-z0-9-]+)?(?:-v\d+)?\.md$"
)
NOTE_TOPIC_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")
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
        if line.startswith("  - ") or line.startswith("- "):
            item = line.strip().lstrip("- ").strip().strip("\"'")
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
    name = rel.name
    if name == "_index.md":
        return True
    parts = rel.parts
    if "00_Inbox" in parts:
        return True
    if FILENAME_PATTERN.match(name):
        return True
    if "30_Notes" in parts:
        # Notes are topic-only ({topic}.md) — no leading date prefix.
        if re.match(r"^\d{4}-\d{2}-", name):
            return False
        if NOTE_TOPIC_PATTERN.match(name):
            return True
    return False


def collect(vault: Path) -> dict:
    fm_records: list = []
    files: list = []
    inbound: dict = {}
    project_indexes: list = []
    note_projects: dict = {}
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

        if rel.name == "_index.md" and len(rel.parts) >= 2 and rel.parts[0] == "20_Projects":
            project_indexes.append(
                {
                    "rel": str(rel),
                    "name": rel.parts[1],
                    "related_notes": fm.get("related_notes", []) if fm else [],
                    "absorbs": fm.get("absorbs", []) if fm else [],
                }
            )

        if rel.parts[0] == "30_Notes" and fm:
            promoted = fm.get("promoted_to_project")
            also = fm.get("also_related_projects", [])
            if isinstance(also, str):
                also = [also] if also else []
            note_projects[str(rel)] = {
                "promoted_to_project": promoted if promoted else None,
                "also_related_projects": also if isinstance(also, list) else [],
            }

    return {
        "fm_records": fm_records,
        "files": [str(f) for f in files],
        "all_stems": all_stems,
        "inbound": {k: sorted(v) for k, v in inbound.items()},
        "project_indexes": project_indexes,
        "note_projects": note_projects,
        "vault": vault,
    }


def classify(bundle: dict) -> dict:
    vault = bundle["vault"]
    findings: list = []

    def add(etype: str, rel: str, detail: str = "") -> None:
        findings.append({"type": etype, "path": rel, "detail": detail})

    for rec in bundle["fm_records"]:
        rel = rec["rel"]
        if Path(rel).parts[0].startswith("."):
            continue
        if not rec["has_fm"]:
            add("E1_missing_frontmatter", rel)
            continue
        if rec["missing_required"]:
            add(
                "E2_missing_required_fields",
                rel,
                ",".join(rec["missing_required"]),
            )

    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if not filename_conforms(rel_path):
            add("E3_filename_convention_violation", str(rel_path))

    for rel in bundle["files"]:
        try:
            content = (vault / rel).read_text(encoding="utf-8")
        except OSError:
            continue
        for m in WIKILINK_PATTERN.finditer(content):
            target = m.group(1).strip().lower()
            if target not in bundle["all_stems"]:
                add("E4_broken_wikilink", rel, target)

    for rec in bundle["fm_records"]:
        rel_path = Path(rec["rel"])
        if rel_path.name == "_index.md":
            continue
        if rel_path.parts[0] != "30_Notes":
            continue
        stem = rel_path.stem.lower()
        sources = [s for s in bundle["inbound"].get(stem, []) if s != rec["rel"]]
        for proj in bundle["project_indexes"]:
            if rec["rel"] in (proj.get("related_notes") or []) + (proj.get("absorbs") or []):
                sources.append(proj["rel"])
        if not sources:
            add("E5_orphan_note", rec["rel"])

    # SKILL.md: path comparisons in E6/E7/E9 are case-insensitive.
    file_set_lower = {f.lower() for f in bundle["files"]}
    note_projects_lower = {k.lower(): v for k, v in bundle["note_projects"].items()}
    for proj in bundle["project_indexes"]:
        forward = (proj.get("related_notes") or []) + (proj.get("absorbs") or [])
        for path in forward:
            if path.lower() not in file_set_lower:
                add("E6_broken_project_to_note", proj["rel"], path)

    for proj in bundle["project_indexes"]:
        forward = (proj.get("related_notes") or []) + (proj.get("absorbs") or [])
        for path in forward:
            path_l = path.lower()
            if path_l not in file_set_lower:
                continue
            note = note_projects_lower.get(path_l)
            if not note:
                continue
            promoted = note.get("promoted_to_project")
            also = note.get("also_related_projects") or []
            back_linked = (promoted == proj["name"]) or (proj["name"] in also)
            if not back_linked:
                add("E7_missing_back_reference", path, proj["name"])

    project_index_set = {p["name"] for p in bundle["project_indexes"]}
    proj_by_name = {p["name"]: p for p in bundle["project_indexes"]}
    for note_path, note in bundle["note_projects"].items():
        candidates: list = []
        if note.get("promoted_to_project"):
            candidates.append(note["promoted_to_project"])
        candidates.extend(note.get("also_related_projects") or [])
        for project_name in candidates:
            if project_name not in project_index_set:
                add("E8_broken_note_to_project", note_path, project_name)
            else:
                proj = proj_by_name[project_name]
                forward_lower = {
                    p.lower() for p in
                    (proj.get("related_notes") or []) + (proj.get("absorbs") or [])
                }
                if note_path.lower() not in forward_lower:
                    add("E9_missing_forward_reference", note_path, project_name)

    counts: dict = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return {"counts": counts, "findings": findings, "total": len(findings)}


SEED_PREFIXES = {
    "E1_missing_frontmatter": ("path", "audit-e1-"),
    "E2_missing_required_fields": ("path", "audit-e2-"),
    "E3_filename_convention_violation": ("path", "audit-e3-"),
    "E4_broken_wikilink": ("path", "audit-e4-"),
    "E5_orphan_note": ("path", "audit-e5-"),
    "E6_broken_project_to_note": ("detail", "30_Notes/audit-e6-"),
    "E7_missing_back_reference": ("path", "audit-e7-"),
    "E8_broken_note_to_project": ("path", "audit-e8-"),
    "E9_missing_forward_reference": ("path", "audit-e9-"),
}


def dod_report(findings: list) -> dict:
    detected: dict = {k: 0 for k in SEED_PREFIXES}
    fp_clean: dict = {k: 0 for k in SEED_PREFIXES}
    for f in findings:
        etype = f["type"]
        marker = SEED_PREFIXES.get(etype)
        if marker is None:
            continue
        field, prefix = marker
        candidate = f.get(field, "") or ""
        if prefix in candidate:
            detected[etype] += 1
        elif "audit-clean-" in (f.get("path") or ""):
            fp_clean[etype] += 1
    return {"seeded_detected": detected, "fp_on_clean": fp_clean}


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
    bundle["vault"] = vault
    result = classify(bundle)

    output: dict = {
        "vault": str(vault),
        "total_findings": result["total"],
        "counts": dict(sorted(result["counts"].items())),
    }
    if args.dod:
        output["dod"] = dod_report(result["findings"])
    if args.findings:
        output["findings"] = result["findings"]
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
