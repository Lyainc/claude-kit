---
name: audit
description: "Scan the vault for structural defects and surface a triage report. Detects 11 error types: missing frontmatter (E1), missing required fields (E2), filename convention violations (E3, with rename suggestion), broken wikilinks (E4), orphan notes (E5, with tag-based connection candidates), stale inbox (E6), stale draft (E7), promotion candidates (E8), tag/property vocabulary inconsistencies (E9), misplaced files (E10), and unstructured paths (E11). Example: '/audit'"
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

3. Emit a scan-start status line in Korean: indicate that the vault audit is starting, and report the number of files targeted along with an estimated scan time.

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

9. Detect E9 vocabulary inconsistency pairs (vault-wide, deterministic — never aggregate tags/keys in the LLM):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" detect-vocabulary "$VAULT_ROOT"
   ```
   Always run on the **full vault** (not the dirty subset) — E9 is a vault-level check. The command emits a JSON array of pairs `{sub, a, b, a_files, b_files}` (empty when consistent); pass it straight to CLASSIFY as the E9 findings source.

**Outputs**: An in-memory scan bundle:
```
{
  frontmatter_records[],   // from scan-frontmatter
  filename_records[],      // from scan-filename
  wikilinks_by_file{},     // source_path → links[]
  inbound_links{}          // target_stem → source_paths[]
  manifest_summary?        // {file_count, generated_at} or null
  vocabulary_pairs[]       // from detect-vocabulary (E9, vault-wide)
}
```

**Termination condition**: All scan data collected. Proceed to CLASSIFY.

---

## Phase 2 — CLASSIFY

**Purpose**: Apply deterministic rules to the scan bundle and produce a findings list. Zero LLM calls.

**Inputs**: Scan bundle from SCAN.

**Error types** (11 types, v4). Detailed pseudocode and false-positive guards live in `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` — read that file when implementing or debugging classification logic.

| Code | Type | Severity | Priority | Source | Auto-fix |
|---|---|---|---|---|---|
| E1 | `missing_frontmatter` | Critical | P0 | `frontmatter_records` | — |
| E2 | `missing_required_fields` | Critical | P0 | `frontmatter_records` | ✓ (add fields; `tags:` inferred via type/slug/folder — see Phase 4) |
| E3 | `filename_convention_violation` | Warning | P0 | `filename_records` | — (suggests `권장 파일명`) |
| E4 | `broken_wikilink` | Critical | P0 | `wikilinks_by_file` | — |
| E5 | `orphan_note` | Warning | P2 | `inbound_links` | — (suggests tag-based `연결 후보`) |
| E6 | `stale_inbox` | Warning | P1 | `frontmatter_records` (`created` + `status`) | — |
| E7 | `stale_draft` | Warning | P1 | `frontmatter_records` (`created` + `status`) | — |
| E8 | `promotion_candidate` | Info | P2 | `manifest.json` (`promotion_candidate: true`) | — |
| E9 | `tag_vocabulary_inconsistency` | Warning | P2 | `frontmatter_records` (vault-wide tags + keys) | — (display-only; `path: ""`) |
| E10 | `misplaced_file` | Warning | P1 | `frontmatter_records` (`type` + folder) | — (display-only) |
| E11 | `unstructured_path` | Warning | P1 | `frontmatter_records` (path) | — (display-only) |

> **Priority mapping** (v4 §6.1): E1–E4 = P0 (무결성/integrity). E6–E7, E10–E11 = P1 (정체·구조/stagnation·structure). E5, E8, E9 = P2 (quality signal). (E10/E11 are the structural checks per #128/#129.)
> **E9 vocabulary** (#119): a **vault-level** check, not per-file — aggregates tags/keys across the whole vault and emits one finding per inconsistent pair with `path: ""`. E9a = a tag and its regular `+s` plural both used (`api`↔`apis`); E9b = a frontmatter key in camelCase and its snake_case equivalent both used (`sourceUrl`↔`source_url`). FP guard: report only when BOTH forms appear in ≥3 files. E9c (semantic synonyms) is out of scope (separate issue). Never auto-fixed — the canonical form is the user's choice.
> **E3 suggestion**: when a filename violates the v4 convention, the finding `detail` includes `권장 파일명: {name}` (note→`{slug}.md`; decision/plan→`{type}-{date}-{slug}.md`; capture/session→`{type}-{date}.md`; missing type/created→no suggestion). Rename affects inbound links → suggestion only, never auto-applied.
> **E5 candidates**: orphan findings carry a structured `candidates: [{path, shared_tags}]` field (top-3 `notes/` files by exact tag-intersection) and a `연결 후보: [[X]] (공유 태그: a, b)` detail. Empty-tags / no-shared-tag orphans render `연결 후보 없음 (공유 태그 없음)` with `candidates: []`.
> **E10/E11**: folder-structure checks. E10 = `type` in the wrong canonical folder (e.g., `type: session` in `notes/`; v5 adds `type: wiki` → `wiki/`). E11 = file outside `inbox/notes/assets/wiki` (arbitrary folder or root-direct; `_index.md` exempt). Both are display-only — moving a file affects inbound links.

Detailed detection criteria for all error types: see `reference/vault-audit-rules.md` (canonical source).

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

## REPORT Output Contract

Output is grouped by priority:
- **P0** (CRITICAL findings): Must-fix items listed first
- **P1** (WARNING findings): Should-fix items
- **P2** (INFO findings): Nice-to-fix items

Within each priority group: sort by severity first (Critical → Warning → Info), then by error code ascending (E1→E2→E3→E4 within P0; E6→E7→E10→E11 within P1; E5→E8→E9 within P2). E9 findings are vault-level (`path: ""`) — render them under a vault-wide heading (e.g. `볼트 전역`) instead of a per-file bullet.

Each finding line format: `[E-code/priority/severity] type — N건` header, then one bullet per file with path and one-line description.

Report header: vault state summary (note count, clean/dirty/untracked), manifest info, promotion candidate count, recent git activity (omit if 0 commits or not a git repo).

Footer: auto-fixable count, manual-action count.

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

**Example** (representative — actual content varies by vault state):

```
볼트 감사 완료
──────────────────────────────────────────
볼트 상태: 42 노트 / clean 38 · dirty 3 · untracked 1
발견된 이슈: 4건 (P0 2건 · P1 1건 · P2 1건)
──────────────────────────────────────────

[P0 / Critical] missing_frontmatter — 1건
  • notes/scratch.md
      상세: frontmatter 없음

[P0 / Warning] filename_convention_violation — 1건
  • notes/2026-04-old-topic.md
      상세: v3 날짜 우선 파일명 — {type}-YYYY-MM-DD-{slug}.md 또는 {slug}.md로 변경 필요

[P1 / Warning] stale_inbox — 1건
  • inbox/capture-2026-03-15-old-topic.md
      상세: age 73d > 14d (status:raw, created 2026-03-15)

[P2 / Info] promotion_candidate — 1건
  • notes/high-ref-note.md
      상세: refs_in=5, access=2 (manual: status→evergreen)

──────────────────────────────────────────
자동 수정 가능: 0건
수동 처리 필요: 4건
```

> **git 활동 줄**: `commits == 0`이거나 vault가 git 저장소가 아닌 경우 해당 줄을 출력하지 않습니다.
- The 7-day window can be overridden via `VAULT_AUDIT_ACTIVITY_DAYS` env var.

> **우선순위 출력 순서**: P0 → P1 → P2. 각 priority 내 정렬: Critical severity 먼저, 그 다음 Warning, Info 순. 동일 severity 내에서는 error type 코드 순 (E1→E2→E3→E4 / E6→E7→E10→E11 / E5→E8→E9). E9는 볼트 전역(path:"") finding이라 파일별 bullet 대신 "볼트 전역" 헤딩 아래에 출력합니다. "사용자 확인 게이트"는 OPTIONAL-FIX 단계(E2 자동 수정)에만 적용됩니다 — 그 외 항목은 표시만 합니다. E6/E7/E8/E9/E10/E11은 의미적 판단(처리/promote/archive/이동/정준형 선택)이 필요해 auto-fix 대상이 아닙니다.

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and user has not already opted out. Otherwise exit after marking clean.

---

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings. Gate behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.

**Tag inference** (#127, deterministic — no LLM; batched #152): when `tags:` is
missing, do NOT insert an empty `tags: []`. Instead derive a tag PROPOSAL from
three tiers via a SINGLE batched call
`ovm-primitives.sh infer-tags <relpath1> <relpath2> ...` (one Python process for
all E2 findings, not one per finding). The call emits a JSON array — one element
per path — with order preserved, duplicates dropped, all lowercased so the result
plausibly passes a future E9 vocabulary check:

| Tier | Source | Rule |
|------|--------|------|
| 1 | `type:` field | always the first tag (`type: note` → `note`) |
| 2 | filename slug | words after stripping the date + `{type}-` prefix, split on `-`/`_` |
| 3 | parent folder | `notes/{domain}/...` → add `domain` |

Examples: `notes/llm/decision-2026-04-12-context-window.md` (`type: decision`)
→ `[decision, context, window, llm]`; `inbox/capture-2026-05-01-obsidian-api.md`
(`type: capture`) → `[capture, obsidian, api]`. Empty slug (date-only filename,
e.g. `session-2026-04-12.md`) gracefully falls back to the type tag only.
The proposal is never auto-committed — it is previewed in the confirmation gate below.

**Auto-fix NOT eligible** (never mutate):
- `missing_frontmatter` (E1): body structure unknown, skip.
- `broken_wikilink` (E4): requires human decision on rename/delete.
- `orphan_note` (E5): requires human decision on content value (connection candidates are suggestions only).
- `filename_convention_violation` (E3): renaming affects all inbound links (`권장 파일명` is a suggestion only).
- `tag_vocabulary_inconsistency` (E9): canonical-form choice + rewriting every affected file is the user's decision — display-only, vault-level.
- `misplaced_file` (E10) / `unstructured_path` (E11): moving a file affects all inbound links — display-only warning, user decides the destination.

**Procedure**:

1. If `auto_fix_eligible` count > 0, first compute the tag proposals for every
   E2 finding whose missing fields include `tags` in ONE batched call (pass all
   such relpaths as arguments — see **Tag inference** above):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" infer-tags <relpath1> <relpath2> ...
   # Large batch (more than ~200 tag-missing E2 findings, to stay well under any
   # platform's ARG_MAX)? Pipe one relpath per line instead:
   #   printf '%s\n' <relpath1> <relpath2> ... | bash ".../ovm-primitives.sh" infer-tags -
   ```
   The command returns a JSON array; match each element's `path` back to its
   finding. Per-file failures surface as an `error` field on that element with
   `inferred_tags: []` (the batch still succeeds for the rest — exit code is
   non-zero only when EVERY path failed). Then ask (single AskUserQuestion). For
   each file with an inferred `tags:`, show the proposal on its own line as
   `추론된 태그: [X, Y, Z]`:
   ```
   AskUserQuestion:
     question: "다음 F건의 frontmatter 이슈를 자동으로 수정할까요?"
     context: |
       수정 대상:
       • missing_required_fields: X건 (tags/type/created 추가)

       추론된 태그 (제안):
       • notes/llm/decision-2026-04-12-context-window.md → [decision, context, window, llm]
       • inbox/capture-2026-05-01-obsidian-api.md → [capture, obsidian, api]

       태그는 type·파일명·폴더에서 추론한 제안입니다. frontmatter만 수정하며
       파일 이름 · 내용 · 위치는 변경하지 않습니다.
     options:
       - "수정 실행"
       - "건너뜀"
   ```

2. If "건너뜀": exit without mutation. Mark scanned files clean in audit sidecar.

3. If "수정 실행":
   - For each `missing_required_fields` finding: use Edit to add the missing fields to the existing frontmatter block.
     - When `tags` is missing, write the inferred proposal from Step 1 (never an empty `tags: []`).
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
