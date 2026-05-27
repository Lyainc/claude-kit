---
name: audit
description: "Scan the vault for structural defects and surface a triage report. Detects 8 error types: missing frontmatter (E1), missing required fields (E2), filename convention violations (E3), broken wikilinks (E4), orphan notes (E5), stale inbox (E6), stale draft (E7), and promotion candidates (E8). Example: '/audit'"
model: haiku
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
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics start "audit"
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

8. Read manifest summary (used for REPORT header and E8 classification):
   ```bash
   cat "$VAULT_ROOT/.vault-bridge/manifest.json" 2>/dev/null
   ```
   Use the resolved `$VAULT_ROOT` from Steps 4–7 (`VAULT_BRIDGE_VAULT_ROOT` → `VAULT_BRIDGE_VAULT_PATH` → `~/vault`), not a hardcoded path.
   Extract `file_count`, `generated_at`, `schema_version`, and `files[]` if the file exists and is valid JSON. If absent or unparseable, set `manifest_summary` to null. For `schema_version ≥ 3`, entries with `promotion_candidate: true` are passed to CLASSIFY to generate E8 findings.

**Outputs**: An in-memory scan bundle:
```
{
  frontmatter_records[],   // from scan-frontmatter
  filename_records[],      // from scan-filename
  wikilinks_by_file{},     // source_path → links[]
  inbound_links{}          // target_stem → source_paths[]
  manifest_summary?        // {file_count, generated_at} or null
}
```

**Termination condition**: All scan data collected. Proceed to CLASSIFY.

---

## Phase 2 — CLASSIFY

**Purpose**: Apply deterministic rules to the scan bundle and produce a findings list. Zero LLM calls.

**Inputs**: Scan bundle from SCAN.

**Error types** (7 types, v4). Detailed pseudocode and false-positive guards live in `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` — read that file when implementing or debugging classification logic.

| Code | Type | Severity | Priority | Source | Auto-fix |
|---|---|---|---|---|---|
| E1 | `missing_frontmatter` | Critical | P0 | `frontmatter_records` | — |
| E2 | `missing_required_fields` | Critical | P0 | `frontmatter_records` | ✓ (add inferred values) |
| E3 | `filename_convention_violation` | Warning | P0 | `filename_records` | — |
| E4 | `broken_wikilink` | Critical | P0 | `wikilinks_by_file` | — |
| E5 | `orphan_note` | Warning | P2 | `inbound_links` | — |
| E6 | `stale_inbox` | Warning | P1 | `frontmatter_records` (`created` + `status`) | — |
| E7 | `stale_draft` | Warning | P1 | `frontmatter_records` (`created` + `status`) | — |
| E8 | `promotion_candidate` | Info | P2 | `manifest.json` (`promotion_candidate: true`) | — |

> **Priority mapping** (v4 §6.1): E1–E4 = P0 (무결성/integrity). E6–E7 = P1 (정체/stagnation). E5, E8 = P2 (quality signal).

**E3 v4 convention** (files in `notes/` only; `inbox/` and `assets/` are exempt):
- VIOLATION: filename starts with `\d{4}-\d{2}-` (v3 date-first pattern, e.g. `2026-04-topic.md`)
- OK: `{slug}.md` (no date), `decision-YYYY-MM-DD-{slug}.md`, `plan-YYYY-MM-DD-{slug}.md` (type-first)
- Guard: `_index.md` is always valid; skip.

**E5 orphan scope**: files in `notes/` (any depth) with zero inbound wikilinks. Files in `inbox/` and `assets/` are exempt.

**E6/E7 stagnation** (uses already-scanned `fm.created` and `fm.status` — no extra primitive needed):
- E6 trigger: `path` startswith `inbox/`, `fm.status` ∈ {`""`, `raw`, missing}, age in days from `fm.created` > 14.
- E7 trigger: `path` startswith `notes/`, `fm.status == "draft"`, age in days from `fm.created` > 30.
- Age is computed against `date.today()` using the `YYYY-MM-DD` value parsed from `fm.created`. Files with malformed or missing `created:` are skipped (E1/E2 catch them).
- Thresholds (`STALE_INBOX_DAYS=14`, `STALE_DRAFT_DAYS=30`) are canonical constants in `audit-validate.py`. To change them, update the constant in `audit-validate.py`, this SKILL.md's E6/E7 rows + triggers, and the matching values in `reference/vault-audit-rules.md`.

**Output**: Findings list:
```
[
  {
    "error_type": "broken_wikilink",
    "severity": "Critical|Warning|Info",
    "priority": "P0|P1|P2",
    "path": "relpath",
    "detail": "human-readable context",
    "auto_fix_eligible": true|false
  }
]
```

**Termination condition**: All dirty files classified. Proceed to REPORT.

---

## Phase 3 — REPORT

**Purpose**: Group findings by priority (P0 → P1 → P2) and display a structured triage report in Korean.

**Inputs**: Findings list from CLASSIFY.

**Tools used**: None (output only).

**Output format**:

```
볼트 감사 완료
──────────────────────────────────────────
볼트 상태: N 노트 / clean X · dirty Y · untracked Z
매니페스트: F 파일 · 갱신 YYYY-MM-DDTHH:MM  (없음: vault-bridge 미설치)
promotion_candidate 계산 완료: N개 후보  (없음: manifest v3 미만 / vault-bridge 미설치)
최근 7일 활동: 12 commits · +5 added · 23 modified · 1 deleted

발견된 이슈: K건 (P0 a건 · P1 b건 · P2 c건)
──────────────────────────────────────────

[P0 / Critical] missing_frontmatter — 3건
  • notes/no-frontmatter-001.md
      상세: frontmatter 없음
  • ...

[P0 / Critical] missing_required_fields — 10건
  • notes/missing-fields-001.md
      상세: 누락 필드 tags,type
  • notes/draft-note-without-status.md
      상세: 누락 필드 status (type:note은 status 필수, v4 §3.3)
  • ...

[P0 / Critical] broken_wikilink — 5건
  • notes/broken-links-001.md
      상세: [[totally-nonexistent-note-1]] → 대상 없음
  • ...

[P0 / Warning] filename_convention_violation — 5건
  • notes/2026-04-bad-name-001.md
      상세: v3 날짜 우선 파일명 — {type}-YYYY-MM-DD-{slug}.md 또는 {slug}.md로 변경 필요
  • ...

[P1 / Warning] stale_inbox — 7건
  • inbox/capture-2026-03-15-old-topic.md
      상세: age 73d > 14d (status:raw, created 2026-03-15)
  • ...

[P1 / Warning] stale_draft — 2건
  • notes/half-written-idea.md
      상세: age 45d > 30d (status:draft, created 2026-04-12)
  • ...

[P2 / Warning] orphan_note — 10건
  • notes/orphan-001.md
      상세: 인바운드 링크 없음
  • ...

[P2 / Info] promotion_candidate — 3건
  • notes/high-ref-note.md
      상세: refs_in=5, access=2 (manual: status→evergreen)
  • notes/frequent-note.md
      상세: refs_in=1, access=7 (manual: status→evergreen)
  • ...

──────────────────────────────────────────
자동 수정 가능: F건 (missing_required_fields — frontmatter 필드 추가)
수동 처리 필요: M건 (broken wikilinks, orphan notes, filename violations, stale inbox/draft, promotion candidates)
```

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

> **git 활동 줄**: `commits == 0`이거나 vault가 git 저장소가 아닌 경우 해당 줄을 출력하지 않습니다.

> **우선순위 출력 순서**: P0 → P1 → P2. 각 priority 내 정렬: Critical severity 먼저, 그 다음 Warning, Info 순. 동일 severity 내에서는 error type 코드 순 (E1→E2→E3→E4 / E6→E7 / E5→E8). "사용자 확인 게이트"는 OPTIONAL-FIX 단계(E2 자동 수정)에만 적용됩니다 — 그 외 항목은 표시만 합니다. E6/E7/E8은 의미적 판단(처리/promote/archive)이 필요해 auto-fix 대상이 아닙니다.

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and user has not already opted out. Otherwise exit after marking clean.

---

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings. Gate behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.

**Auto-fix NOT eligible** (never mutate):
- `missing_frontmatter` (E1): body structure unknown, skip.
- `broken_wikilink` (E4): requires human decision on rename/delete.
- `orphan_note` (E5): requires human decision on content value.
- `filename_convention_violation` (E3): renaming affects all inbound links.

**Procedure**:

1. If `auto_fix_eligible` count > 0, ask (single AskUserQuestion):
   ```
   AskUserQuestion:
     question: "다음 F건의 frontmatter 이슈를 자동으로 수정할까요?"
     context: |
       수정 대상:
       • missing_required_fields: X건 (tags/type/created 추가)

       frontmatter만 수정합니다. 파일 이름 · 내용 · 위치는 변경하지 않습니다.
     options:
       - "수정 실행"
       - "건너뜀"
   ```

2. If "건너뜀": exit without mutation. Mark scanned files clean in audit sidecar.

3. If "수정 실행":
   - For each `missing_required_fields` finding: use Edit to add the missing fields to the existing frontmatter block.
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
| `--path <dir>` | Limit scan to a subdirectory (e.g., `--path notes`) |
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
