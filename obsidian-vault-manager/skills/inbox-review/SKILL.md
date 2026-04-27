---
name: inbox-review
description: "Organize Inbox notes using a 4-phase pipeline (SCAN→PROPOSE→CONFIRM→EXECUTE). Token-efficient: shell primitives handle scanning, LLM only touches ambiguous items. Example: '/inbox-review'"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, AskUserQuestion prompts, confirmation messages) MUST be in Korean.

Organize files in `~/vault/00_Inbox/`.

---

## Pipeline Overview

```
SCAN (shell, LLM=0) → PROPOSE (rule-based, minimal LLM) → CONFIRM (≤3 AskUserQuestion) → EXECUTE (deterministic)
```

Each phase has explicit inputs, outputs, and a termination condition. Do NOT collapse phases.

---

## Phase 1 — SCAN

**Purpose**: Classify every inbox file using shell primitives. Zero LLM token cost.

**Inputs**: `~/vault/00_Inbox/` directory.

**Tools used**: Bash only.

**Procedure**:

1. Check inbox is non-empty:
   ```bash
   ls -1t ~/vault/00_Inbox/*.md 2>/dev/null | wc -l
   ```
   - If count is 0, output "인박스가 비어 있습니다" and exit.
   - If the above returns empty, verify with `ls -la ~/vault/00_Inbox/` before concluding empty.

2. Start metrics:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics start "inbox-review"
   ```

3. Build dirty list — skip files already marked clean in the audit sidecar:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state list-dirty-since
   ```
   Files absent from sidecar (untracked) are treated as dirty. Files with `"clean": true` are skipped unless `--force` flag was passed by the user.

4. For each dirty inbox file, run both scans:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-frontmatter ~/vault/00_Inbox/
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-filename ~/vault/00_Inbox/
   ```

5. Assign a classification tag to each file based on scan output (no LLM reading of file body):

   | Tag | Rule |
   |-----|------|
   | `auto-classifiable` | `missing_required` is empty AND `conforms: true` AND type is `capture` or `session` |
   | `needs-triage` | `missing_required` non-empty OR no frontmatter OR `conforms: false` |
   | `project-bound` | frontmatter contains `project:` field pointing to a known project dir |
   | `delete-candidate` | filename matches patterns: `temp-*`, `draft-*`, `test-*`, or size_bytes < 50 |
   | `duplicate-candidate` | same `title` or same filename stem as an existing `30_Notes/` file |

   A file may carry multiple tags; the first matching tag in the table above is primary.

**Outputs**: An in-memory classification table:
```
{path, primary_tag, secondary_tags[], frontmatter{}, missing_required[], conforms, size_bytes}
```

**Termination condition**: All dirty inbox files have been classified. Proceed to PROPOSE.

---

## Phase 2 — PROPOSE

**Purpose**: Generate a proposed action for every classified file using rules. Minimize LLM reads — read file body only when classification is `needs-triage` AND the triage reason is ambiguous (i.e., frontmatter present but `type` field is missing).

**Inputs**: Classification table from SCAN.

**Tools used**: Bash (for wikilink extraction if needed), Read (only for ambiguous needs-triage files, body preview ≤ 10 lines).

**Action rules** (deterministic, no LLM for auto-classifiable):

| Primary tag | Default proposed action |
|-------------|------------------------|
| `auto-classifiable` (type=capture) | Keep in `00_Inbox/` → display for Q1 so user decides next destination |
| `auto-classifiable` (type=session) | Move to `20_Projects/{project}/` if `project:` present, else keep |
| `project-bound` | Move to `20_Projects/{project}/` per frontmatter `project:` field |
| `delete-candidate` | Propose delete; include reason (size / name pattern) |
| `duplicate-candidate` | Propose merge or rename; show existing file path |
| `needs-triage` | Propose move to `30_Notes/` with Low confidence; requires user review |

**Confidence levels**:
- High: frontmatter complete + filename conforms + action is unambiguous
- Medium: frontmatter partial or one field missing
- Low: no frontmatter OR filename non-conforming OR triage required

**Output format** (display after PROPOSE is complete, before Q1):
```
볼트 상태: N 노트 / clean X · dirty Y · untracked Z
스캔 대상: Y (예상 시간: ~Ns)

[스캔 Y/Y | 이슈 K건]
[1/K] 00_Inbox/capture-2026-04-12-api.md
  제안: 30_Notes/api-design.md로 이동
  근거: type=capture, conforms=true, no duplicate
  신뢰도: High

[2/K] 00_Inbox/draft-idea.md
  제안: 삭제 후보
  근거: filename=draft-*, size=42B
  신뢰도: Medium
```

**Termination condition**: Every dirty inbox file has a proposed action and confidence level. Proceed to CONFIRM.

---

## Phase 3 — CONFIRM

**Purpose**: Collect user decisions via structured AskUserQuestion calls. Cap at **3 interactions per session** (Q1 + Q2 + Q3). Merge related questions into batched multi-field forms.

**Inputs**: Proposed action table from PROPOSE.

**Tools used**: AskUserQuestion only (no file reads, no bash).

**Interaction budget**:

### Q1 — Bulk action selection (always asked)

Present the full proposed action list. User may accept all, override specific items, or mark items for Q2.

```
AskUserQuestion:
  question: "인박스 정리 제안입니다. 번호별로 액션을 수정하거나 그대로 진행해 주세요."
  context: |
    [전체 제안 목록]
    1. capture-2026-04-12-api.md → 30_Notes/api-design.md [High]
    2. draft-idea.md → 삭제 [Medium]
    3. needs-triage-note.md → 30_Notes/ 이동 (검토 필요) [Low]

    형식: "1,3 → Notes, 2 → 삭제, 나머지 승인" 또는 "전체 승인"
    나머지 유지: "나머지 유지"로 미지정 항목 보존
```

### Q2 — Ambiguous items (only if ≥1 Low-confidence or needs-triage item exists)

Ask about ambiguous items only. Show at most top 5 by count. Merge into a single multi-field question.

```
AskUserQuestion:
  question: "다음 항목은 확인이 필요합니다. 각 항목의 처리 방법을 알려주세요."
  context: |
    [모호한 항목 최대 5개]
    A. needs-triage-note.md (frontmatter 없음)
       → 이동할 위치: Notes / Projects/{name} / 삭제 / 유지
    B. ambiguous-file.md (type 필드 없음, 내용: "...")
       → 이동할 위치: Notes / Projects/{name} / 삭제 / 유지
```

### Q3 — Final apply confirmation (always asked before any mutation)

```
AskUserQuestion:
  question: "다음 작업을 실행합니다. 계속할까요?"
  context: |
    이동: 3건
    삭제: 1건 (파일명 목록)
    건너뜀: N건
  options:
    - "실행"
    - "취소"
```

**Interaction rules**:
- Q2 is SKIPPED if all items are High/Medium confidence with no ambiguous items.
- If Q3 answer is "취소", exit without any mutation.
- AskUserQuestion total per session ≤ 3. Do not ask additional follow-up questions; handle edge cases (file conflicts, duplicate names) in EXECUTE with safe defaults (rename with `-v2` suffix).

**Input grammar** (same as previous skill — backward compatible):

| Format | Example | Interpretation |
|--------|---------|----------------|
| `{number} → Notes` | `1,3 → Notes로 이동` | Move specified items to `30_Notes/` |
| `{number} → 삭제` | `2 → 삭제` | Mark for deletion (confirmed in Q3) |
| `{number} → {project}` | `4 → api-project` | Move to `20_Projects/{project}/` |
| `나머지 유지` / `keep rest` | `나머지 유지` | Keep unspecified items in Inbox |
| `전체 이동` / `move all` | `전체 Notes로` | Move all items to `30_Notes/` |
| `전체 승인` | `전체 승인` | Accept all proposed actions from PROPOSE |

**On unrecognized input**: output "입력을 이해하지 못했습니다. 예: `1,3 → Notes로 이동`" and wait for re-input (does NOT consume an additional AskUserQuestion slot).

**Termination condition**: Q3 answered "실행". Proceed to EXECUTE. If "취소", exit cleanly.

---

## Phase 4 — EXECUTE

**Purpose**: Apply all confirmed actions deterministically. No user interaction. No LLM decisions.

**Inputs**: Confirmed action table from CONFIRM.

**Tools used**: Bash, Write (for MOC backlinks), Edit (for frontmatter-only updates).

**Procedure**:

1. For each file confirmed for **move to 30_Notes/**:
   - Follow the `note` skill's procedure for domain determination and MOC linking.
   - Target path: `~/vault/30_Notes/{topic-kebab}.md`
   - Collision handling: if target exists, append `-v2`, `-v3`, etc. (no additional AskUserQuestion).
   - Execute move:
     ```bash
     mv ~/vault/00_Inbox/{filename} ~/vault/30_Notes/{topic}.md
     ```

2. For each file confirmed for **move to 20_Projects/{project}/**:
   - Verify project directory exists: `ls ~/vault/20_Projects/{project}/`
   - Execute move:
     ```bash
     mv ~/vault/00_Inbox/{filename} ~/vault/20_Projects/{project}/{filename}
     ```

3. For each file confirmed for **deletion**:
   - Note: vault-file-organizer cannot delete; guide user to delete manually.
   - Output: "삭제 대상 파일: {filename} — Obsidian에서 직접 삭제하거나 `rm ~/vault/00_Inbox/{filename}` 명령을 실행해 주세요."

4. Mark each processed file as clean in the audit sidecar:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state mark-clean 00_Inbox/{relpath}
   ```

5. Stop metrics and report:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics stop
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics report
   ```

6. Output final summary in Korean:
   ```
   완료: {N}건 처리됨 (이동 X건 · 삭제 안내 Y건 · 건너뜀 Z건)
   소요 시간: {elapsed}ms
   ```

**Termination condition**: All confirmed actions applied, audit sidecar updated, metrics reported.

---

## Flags

| Flag | Behavior |
|------|----------|
| `--force` | Ignore audit-state; scan all inbox files regardless of clean status |
| `--dry-run` | Run SCAN→PROPOSE→CONFIRM but skip EXECUTE mutations (show what would happen) |
| `--reset-state` | Call `audit-state invalidate` on all inbox files before scanning |

Hidden files (`.` prefix) are skipped by default. Pass `--include-hidden` to include them.

---

## Rules

- NEVER call vault-searcher. This skill is OVM-local.
- NEVER re-implement frontmatter or filename parsing inline. Always delegate to `ovm-primitives.sh`.
- NEVER read file body during SCAN. Body reads are only permitted in PROPOSE for Low-confidence items, and only the first 10 lines.
- The 3-interaction cap (Q1+Q2+Q3) is a hard limit. Merge questions; do not split them.
- `audit-state mark-clean` MUST be called after each successfully processed file in EXECUTE.
- Dry-run mode outputs the EXECUTE plan but performs no mutations and does not call `mark-clean`.
