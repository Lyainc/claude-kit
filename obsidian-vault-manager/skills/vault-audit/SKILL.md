---
name: vault-audit
description: "Scan the entire vault for structural defects and surface them as a triage report. Detects 9 error types (8 base + 1 derived): orphan notes, broken wikilinks, filename violations, missing frontmatter, and 5 note↔project bidirectional link integrity errors (4 base + 1 derived missing_forward_reference). Example: '/vault-audit'"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, AskUserQuestion prompts, confirmation messages, progress lines) MUST be in Korean.

Scan the entire vault rooted at `~/vault/` for structural defects and produce a triage report grouped by severity.

---

## Pipeline Overview

```
SCAN (shell, LLM=0) → CLASSIFY (rule-based, LLM=0) → REPORT (grouped by severity) → OPTIONAL-FIX (explicit opt-in only)
```

Each phase has explicit inputs, outputs, and a termination condition. Do NOT collapse phases.

---

## Phase 1 — SCAN

**Purpose**: Collect raw scan data from the vault using ovm-primitives. Zero LLM token cost.

**Inputs**: `~/vault/` (or `--path <subdir>` if flag provided).

**Tools used**: Bash only.

**Procedure**:

1. Start metrics:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics start "vault-audit"
   ```

2. Build the dirty file list using audit-state warm-up (O(dirty files) after first run):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state list-dirty-since
   ```
   Files absent from sidecar (untracked) are treated as dirty. Files with `status: clean` are skipped unless `--force` was passed.

3. Emit scan-start status line (Korean):
   ```
   볼트 감사 시작 중...
   감사 대상: Y 파일 (예상 시간: ~Ns)
   ```

4. Run frontmatter scan on the full vault:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-frontmatter ~/vault
   ```

5. Run filename scan on the full vault:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-filename ~/vault
   ```

6. Run wikilink extraction on every dirty `.md` file:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" extract-wikilinks ~/vault/<relpath>
   ```
   Collect: `{source_path, links[]}` for each file.

7. Build a global link index: `{target_stem → [source_paths]}` from all extracted wikilinks across the full vault (not just dirty files). This is required for orphan detection (which needs the full inbound-link map).

   To build the full link index efficiently, run `extract-wikilinks` on all `.md` files found by:
   ```bash
   find ~/vault -name '*.md' -not -path '*/.*' 
   ```

8. Collect project binding data — for each `_index.md` under `20_Projects/`:
   - Read its `related_notes` frontmatter field (list of vault-relative paths, e.g. `30_Notes/foo.md`).
   - Read its `absorbs` frontmatter field (list of vault-relative paths). Both fields are forward links — checks against the project's forward set use `(related_notes + absorbs)`.
   - Record: `{project_path, project_name, related_notes[], absorbs[]}`.

9. Collect note → project back-references — for each `.md` in `30_Notes/`:
   - Read its `promoted_to_project` frontmatter field (single string, optional).
   - Read its `also_related_projects` frontmatter field (array of strings, optional).
   - Record: `{note_path, promoted_to_project, also_related_projects[]}`.
   - Back-reference and forward-link checks treat both fields as a union (`{promoted_to_project} ∪ also_related_projects`, skipping null/empty).

**Outputs**: An in-memory scan bundle:
```
{
  frontmatter_records[],   // from scan-frontmatter
  filename_records[],      // from scan-filename
  wikilinks_by_file{},     // source_path → links[]
  inbound_links{},         // target_stem → source_paths[]
  project_indexes[],       // {project_path, project_name, related_notes[], absorbs[]}
  note_projects{}          // note_relpath → {promoted_to_project, also_related_projects[]}
}
```

**Termination condition**: All scan data collected. Proceed to CLASSIFY.

---

## Phase 2 — CLASSIFY

**Purpose**: Apply deterministic rules to the scan bundle and produce a findings list. Zero LLM calls.

**Inputs**: Scan bundle from SCAN.

**Error types** (8 base + 1 derived). Detailed pseudocode and false-positive guards live in `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` — read that file when implementing or debugging classification logic.

| Code | Type | Severity | Source | Auto-fix |
|---|---|---|---|---|
| E1 | `missing_frontmatter` | Critical | `frontmatter_records` | — |
| E2 | `missing_required_fields` | Critical | `frontmatter_records` | ✓ (add inferred values) |
| E3 | `filename_convention_violation` | Warning | `filename_records` | — |
| E4 | `broken_wikilink` | Critical | `wikilinks_by_file` | — |
| E5 | `orphan_note` | Warning | `inbound_links` | — |
| E6 | `broken_project_to_note` | Critical | `project_indexes` | — |
| E7 | `missing_back_reference` | Warning | `project_indexes` × `note_projects` | ✓ (append `also_related_projects`) |
| E8 | `broken_note_to_project` | Critical | `note_projects` | — |
| derived | `missing_forward_reference` | Warning | E7/E8 pair | ✓ (append `related_notes`) |

Spec W2 DoD lists 8 error type names; E1 + E2 together cover the spec's `missing frontmatter` and are reported as separate sub-types for DoD counting.

**Output**: Findings list:
```
[
  {
    "error_type": "broken_wikilink",
    "severity": "Critical|Warning|Info",
    "path": "relpath",
    "detail": "human-readable context",
    "auto_fix_eligible": true|false
  }
]
```

**Termination condition**: All dirty files classified. Proceed to REPORT.

---

## Phase 3 — REPORT

**Purpose**: Group findings by severity and display a structured triage report in Korean.

**Inputs**: Findings list from CLASSIFY.

**Tools used**: None (output only).

**Output format**:

```
볼트 감사 완료
──────────────────────────────────────────
볼트 상태: N 노트 / clean X · dirty Y · untracked Z

발견된 이슈: K건 (Critical C · Warning W · Info I)
──────────────────────────────────────────

[Critical] missing_frontmatter — 3건
  • 30_Notes/no-frontmatter-001.md
      상세: frontmatter 없음
  • ...

[Critical] broken_wikilink — 5건
  • 30_Notes/broken-links-001.md
      상세: [[totally-nonexistent-note-1]] → 대상 없음
  • ...

[Warning] orphan_note — 10건
  • 30_Notes/orphan-001.md
      상세: 인바운드 링크 없음
  • ...

[Warning] filename_convention_violation — 5건
  • ...

──────────────────────────────────────────
자동 수정 가능: F건 (frontmatter 필드 추가, back-reference 추가)
수동 처리 필요: M건 (broken wikilinks, orphan notes)
```

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and user has not already opted out. Otherwise exit after marking clean.

---

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings. Gate behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.
- `missing_back_reference` (E7): append `<project_name>` to `also_related_projects` array in note frontmatter. Do NOT overwrite `promoted_to_project`.
- `missing_forward_reference`: append vault-relative note path to `related_notes` list in the project `_index.md`.

**Auto-fix NOT eligible** (never mutate):
- `missing_frontmatter` (E1): body structure unknown, skip.
- `broken_wikilink` (E4): requires human decision on rename/delete.
- `orphan_note` (E5): requires human decision on content value.
- `broken_project_to_note` (E6): cannot create note stub automatically.
- `broken_note_to_project` (E8): project directory/index may not exist.
- `filename_convention_violation` (E3): renaming affects all inbound links.

**Procedure**:

1. If `auto_fix_eligible` count > 0, ask (single AskUserQuestion):
   ```
   AskUserQuestion:
     question: "다음 F건의 frontmatter 이슈를 자동으로 수정할까요?"
     context: |
       수정 대상:
       • missing_required_fields: X건 (tags/type/created 추가)
       • missing_back_reference: Y건 (also_related_projects 추가)
       • missing_forward_reference: Z건 (_index.md related_notes 추가)
       
       frontmatter만 수정합니다. 파일 이름 · 내용 · 위치는 변경하지 않습니다.
     options:
       - "수정 실행"
       - "건너뜀"
   ```

2. If "건너뜀": exit without mutation. Mark scanned files clean in audit sidecar.

3. If "수정 실행":
   - For each `missing_required_fields` finding: use Edit to add the missing fields to the existing frontmatter block.
   - For each `missing_back_reference`: use Edit to append the project name to `also_related_projects` in the note's frontmatter (create the field as an array if absent; never overwrite `promoted_to_project`).
   - For each `missing_forward_reference`: use Edit to append the vault-relative note path to the `related_notes` list in the project `_index.md` (create the field as an array if absent).
   - All edits are **frontmatter-only** — never touch the markdown body.

4. After all fixes, mark all processed files clean:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state mark-clean <relpath>
   ```

5. Stop metrics and output final summary:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics stop
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics report
   ```
   Output:
   ```
   완료: 이슈 K건 발견, F건 자동 수정됨
   소요 시간: {elapsed}ms
   ```

**Termination condition**: All confirmed fixes applied (or skipped), audit sidecar updated, metrics reported.

---

## Flags

| Flag | Behavior |
|------|----------|
| `--force` | Ignore audit-state; re-audit all vault files |
| `--dry-run` | Run SCAN→CLASSIFY→REPORT but skip OPTIONAL-FIX and mark-clean |
| `--path <dir>` | Limit scan to a subdirectory (e.g., `--path 30_Notes`) |
| `--reset-state` | Call `audit-state invalidate` on all vault files before scanning |
| `status` | Show current audit-state stats only (no scan) |

---

## Rules

- NEVER call vault-searcher. This skill is OVM-local.
- NEVER re-implement frontmatter or filename parsing inline. Always delegate to `ovm-primitives.sh`.
- NEVER read file bodies during SCAN or CLASSIFY. All classification is derived from primitive JSON outputs.
- Auto-fix is OFF by default. OPTIONAL-FIX only runs after explicit "수정 실행" confirmation.
- `audit-state mark-clean` MUST be called after every successfully processed file.
- Dry-run mode outputs the REPORT but performs no mutations and does not call `mark-clean`.
- The AskUserQuestion in OPTIONAL-FIX is the only allowed user interaction. No additional questions.
- Severity levels: Critical (data integrity risk), Warning (quality/navigation risk), Info (style/convention).
