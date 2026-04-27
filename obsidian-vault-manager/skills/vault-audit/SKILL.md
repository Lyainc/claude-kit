---
name: vault-audit
description: "Scan the entire vault for structural defects and surface them as a triage report. Detects 8 error types: orphan notes, broken wikilinks, filename violations, missing frontmatter, and 4 note↔project bidirectional link integrity errors. Example: '/vault-audit'"
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
   - Read its `related_notes` frontmatter field (list of vault-relative note paths, e.g. `30_Notes/oauth.md`).
   - Record: `{project_path, project_name, related_notes[]}`.

9. Collect note → project back-references — for each `.md` in `30_Notes/`:
   - Read its `promoted_to_project` frontmatter field (string, optional — primary project name).
   - Read its `also_related_projects` frontmatter field (list of project names, optional).
   - Record: `{note_path, promoted_to_project, also_related_projects[]}`.
   - The note's set of "linked projects" for back-reference checks is `{promoted_to_project} ∪ also_related_projects` (skipping null/empty).

**Outputs**: An in-memory scan bundle:
```
{
  frontmatter_records[],   // from scan-frontmatter
  filename_records[],      // from scan-filename
  wikilinks_by_file{},     // source_path → links[]
  inbound_links{},         // target_stem → source_paths[]
  project_indexes[],       // {project_path, project_name, related_notes[]}
  note_projects{}          // note_relpath → {promoted_to_project, also_related_projects[]}
}
```

**Termination condition**: All scan data collected. Proceed to CLASSIFY.

---

## Phase 2 — CLASSIFY

**Purpose**: Apply deterministic rules to the scan bundle and produce a findings list. Zero LLM calls.

**Inputs**: Scan bundle from SCAN.

**Error types and detection rules** (8 types, matched against spec):

### E1 — `missing_frontmatter` [Critical]
**Rule**: `has_frontmatter == false`
**Source**: `frontmatter_records`
**Guard**: Skip `.ovm/` and `.obsidian/` paths.

### E2 — `missing_required_fields` [Critical]
**Rule**: `has_frontmatter == true` AND `missing_required` is non-empty
**Source**: `frontmatter_records`
**Reports**: which fields are missing (`created`, `tags`, `type`).

### E3 — `filename_convention_violation` [Warning]
**Rule**: `conforms == false`
**Source**: `filename_records`
**Guard**: Skip `_index.md` (always valid), skip files in `00_Inbox/` that are temp/draft names only if `--strict` flag is absent.

### E4 — `broken_wikilink` [Critical]
**Rule**: For each `[[target]]` in a file — look up `target` stem in the vault file set. If no file exists with that stem (case-insensitive match), it is broken.
**Source**: `wikilinks_by_file`, global file index.
**Guard**: Ignore embed links `![[image.png]]` where target has a non-`.md` extension or no extension at all and a matching file exists in assets. Ignore links to headings/blocks within a found note.

### E5 — `orphan_note` [Warning]
**Rule**: A `.md` file in `30_Notes/` has zero entries in `inbound_links[stem]`.
**Source**: `inbound_links` (built from full vault scan).
**Guard**: `_index.md` files are never orphans. Files in `00_Inbox/` are exempt (not yet processed).

### E6 — `broken_project_to_note` [Critical]
**Rule**: `_index.md` has a `related_notes` field listing vault-relative path `P`, but no file exists at `~/vault/P`.
**Source**: `project_indexes`.
**False-positive guard**: Path matching is exact against the resolved vault path. If the path is bare (no directory prefix), resolve against `30_Notes/` before checking.

### E7 — `missing_back_reference` [Warning]
**Rule**: `_index.md` (project name `N`) has a `related_notes` field listing path `P`, the file at `P` exists, but the note's linked-projects set (`promoted_to_project` ∪ `also_related_projects`) does NOT contain `N`.
**Source**: `project_indexes`, `note_projects`.
**False-positive guard**: Only flag when the file at `P` actually exists (no double-flag with E6). A note that lists `N` in `also_related_projects` satisfies the back-reference requirement even if `promoted_to_project` is some other project.

### E8 — `broken_note_to_project` [Critical]
**Rule**: A note in `30_Notes/` has either a `promoted_to_project: <name>` field or includes `<name>` in its `also_related_projects` list, but `~/vault/20_Projects/<name>/_index.md` does NOT exist.
**Source**: `note_projects`.
**False-positive guard**: Each project name in the union set is checked independently; flag only the missing ones.

### Derived check — `missing_forward_reference` [Warning]
**Rule**: A note `R` in `30_Notes/` has `promoted_to_project: <name>` (or includes `<name>` in `also_related_projects`) pointing to an existing project, but the project's `_index.md` does NOT list `R`'s vault-relative path in its `related_notes` field.
**Source**: `project_indexes`, `note_projects`.
**False-positive guard**: Only flag when the note file actually exists and the project `_index.md` exists. Path comparison is exact.

> **Implementation note**: The spec W2 DoD lists 8 error type names. The mapping used here:
> `orphan_note` → E5, `broken_wikilink` → E4, `filename_convention_violation` → E3,
> `missing_frontmatter` → E1 (E2 is the field-level variant treated as Critical alongside E1),
> `broken_project_to_note` → E6, `missing_back_reference` → E7,
> `broken_note_to_project` → E8, `missing_forward_reference` → derived from E7/E8 pair.
> E1+E2 together cover the spec's `missing frontmatter` error. For DoD counting, E1 and E2 are
> reported as separate sub-types of the same category.

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
- `missing_back_reference` (E7): append the project name to the note's `also_related_projects` list (do NOT overwrite any existing `promoted_to_project`).
- `missing_forward_reference`: append the note's vault-relative path to the project `_index.md` `related_notes` list.

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
       • missing_back_reference: Y건 (note의 also_related_projects 에 프로젝트명 추가)
       • missing_forward_reference: Z건 (_index.md related_notes 에 note 경로 추가)
       
       frontmatter만 수정합니다. 파일 이름 · 내용 · 위치는 변경하지 않습니다.
     options:
       - "수정 실행"
       - "건너뜀"
   ```

2. If "건너뜀": exit without mutation. Mark scanned files clean in audit sidecar.

3. If "수정 실행":
   - For each `missing_required_fields` finding: use Edit to add the missing fields to the existing frontmatter block.
   - For each `missing_back_reference`: use Edit to append the project name to the note's `also_related_projects` list (creating the list if absent). Do NOT touch any existing `promoted_to_project` value.
   - For each `missing_forward_reference`: use Edit to append the note's vault-relative path to the `related_notes` list in the project `_index.md` (creating the list if absent).
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
