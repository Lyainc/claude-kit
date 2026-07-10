---
name: audit
description: "Scan the vault for structural defects and surface a triage report. Detects 12 error types: missing frontmatter (E1), missing required fields (E2), filename convention violations (E3, with rename suggestion), broken wikilinks (E4), orphan notes (E5, with tag-based connection candidates), stale inbox (E6), stale draft (E7), promotion candidates (E8), tag/property vocabulary inconsistencies (E9a/E9b deterministic; optional `--deep` LLM opt-in for E9c semantic synonym), misplaced files (E10), unstructured paths (E11), and stale wiki pages (E12a, stale `verified:`; optional `--deep` LLM opt-in for E12b cross-page contradiction). Example: '/audit' or '/audit --deep'"
model: haiku
allowed-tools: Read Write Edit Bash Glob Grep AskUserQuestion
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

**Error types** (12 types: E1–E11 v4, E12 v5). Detailed pseudocode and false-positive guards live in `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` — read that file when implementing or debugging classification logic.

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
| E12 | `wiki_self_audit` | Warning | P1 | `frontmatter_records` (`wiki/` path + `type: wiki` + `verified`) | — (display-only) |

> **Priority mapping** (v4 §6.1): E1–E4 = P0 (무결성/integrity). E6–E7, E10–E12 = P1 (정체·구조/stagnation·structure). E5, E8, E9 = P2 (quality signal). (E10/E11 are the structural checks per #128/#129; E12 is the wiki self-audit per #330.)
> **E9 vocabulary** (#119): a **vault-level** check, not per-file — aggregates tags/keys across the whole vault and emits one finding per inconsistent pair with `path: ""`. E9a = a tag and its regular `+s` plural both used (`api`↔`apis`); E9b = a frontmatter key in camelCase and its snake_case equivalent both used (`sourceUrl`↔`source_url`). FP guard: report only when BOTH forms appear in ≥3 files. E9c (semantic synonyms, e.g. `llm`↔`large-language-model`) ships as the skill-only `--deep` LLM opt-in (#167) — see Phase 2.5 below (mirrors E12b's skill-only design). Never auto-fixed — the canonical form is the user's choice.
> **E3 suggestion**: when a filename violates the v4 convention, the finding `detail` includes `권장 파일명: {name}` (note→`{slug}.md`; decision/plan→`{type}-{date}-{slug}.md`; capture/session→`{type}-{date}.md`; missing type/created→no suggestion). Rename affects inbound links → suggestion only, never auto-applied.
> **E5 candidates**: orphan findings carry a structured `candidates: [{path, shared_tags}]` field (top-3 `notes/` files by exact tag-intersection) and a `연결 후보: [[X]] (공유 태그: a, b)` detail. Empty-tags / no-shared-tag orphans render `연결 후보 없음 (공유 태그 없음)` with `candidates: []`.
> **E10/E11**: folder-structure checks. E10 = `type` in the wrong canonical folder (e.g., `type: session` in `notes/`; v5 adds `type: wiki` → `wiki/`). E11 = file outside `inbox/notes/assets/wiki` (arbitrary folder or root-direct; `_index.md` exempt). Both are display-only — moving a file affects inbound links.
> **E12 wiki self-audit** (#330, v5 §7 U3): flags a `wiki/` page (top folder `wiki/` AND `type: wiki`) whose `verified:` age exceeds `STALE_WIKI_DAYS` (90) — staleness is the abandonment risk for the LLM wiki. A missing/unparseable `verified:` is skipped (uncomputable). Display-only (recompile/re-verify is a semantic decision). E12a (staleness) ships deterministically in CLASSIFY. E12b (cross-page semantic contradiction, #336) ships as the skill-only `--deep` LLM opt-in — see Phase 2.5 DEEP below (mirrors E9c's skill-only design).

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

**Termination condition**: All dirty files classified. Proceed to Phase 2.5 if `--deep` was passed, otherwise directly to REPORT.

---

## Phase 2.5 — DEEP (opt-in, `--deep`)

**Purpose**: Run every LLM-judgment check gated behind `--deep`. This is the **only** phase in this skill that reads file bodies or uses LLM judgment — SCAN, CLASSIFY, and REPORT stay LLM-cost-0 without `--deep`. Two independent sub-checks run here, each with its own candidate-pair prefilter and its own confirm gate: E12b (cross-page wiki contradiction, #336, below) and E9c (tag semantic synonym, #167, further down).

### E12b — cross-page wiki contradiction

**Purpose**: Detect `wiki/` pages that assert conflicting claims about the same subject (#336).

**Inputs**: `frontmatter_records` and `wikilinks_by_file` from the scan bundle (already collected, no re-scan).

**Tools used**: Read, AskUserQuestion.

**Skip conditions** (exit phase immediately, no findings added):
- `--deep` flag not passed.
- Fewer than 2 records with top folder `wiki/` AND `fm.type == "wiki"`.

**Procedure**:

1. Collect `wiki_pages` = every `frontmatter_records` entry with top folder `wiki/` and `fm.type == "wiki"`.

2. Build **candidate pairs** deterministically (no LLM, cheap prefilter — bounds the expensive judgment step to topically-related pages instead of every O(n²) pair): two wiki pages `(A, B)` are a candidate when EITHER holds:
   - they share at least one tag (case-insensitive intersection of `fm.tags`), or
   - one wikilinks to the other (via `wikilinks_by_file`).

   If zero candidate pairs, exit phase (no findings).

3. Read each **unique** page in `wiki_pages` that appears in at least one candidate pair exactly once, and cache its body by path — a hub page in several candidate pairs is not re-read per pair.

4. Judge each candidate pair using the cached bodies: do the two pages assert **conflicting claims about the same subject** (a fact, a number, a decision, a status that cannot both be true)? Complementary information, different scopes, or purely stylistic differences are NOT a contradiction — do not flag those.

5. Stage every pair judged contradictory as a DEEP candidate. Do **not** add it to the findings list yet — Step 6 is the mandatory FP-mitigation gate.

6. If any DEEP candidates exist, confirm each **individually** — a single generic accept/decline does not let the user keep one pair and drop another. `AskUserQuestion` takes up to 4 questions per call, so ask one question per candidate pair, batching in groups of ≤4 (sequential calls if there are more than 4):
   ```
   AskUserQuestion:
     questions:
       - question: "wiki/a.md ↔ wiki/b.md — 이 쌍, 실제 상충으로 볼까요?"
         header: "상충 확인"
         options:
           - label: "실제 상충 — 보고에 포함"
             description: "<one-line reason the pages conflict>"
           - label: "상충 아님 — 무시"
             description: "판단 오류로 보고 이 쌍은 건너뜀"
       - question: "wiki/c.md ↔ wiki/d.md — 이 쌍, 실제 상충으로 볼까요?"
         header: "상충 확인"
         options: [...]   # same two-option shape, one row per additional candidate pair
   ```
   Each pair's answer is independent. A candidate the user declines is dropped silently — no finding, no residual state.

7. Every confirmed pair becomes one finding:
   ```
   {
     "error_type": "wiki_contradiction",
     "severity": "Warning",
     "priority": "P1",
     "path": "wiki/a.md ↔ wiki/b.md",
     "detail": "human-readable reason",
     "auto_fix_eligible": false
   }
   ```
   Append it to the findings list produced by CLASSIFY (sorts under E12 in REPORT, alongside E12a staleness findings).

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to the E9c sub-check below.

### E9c — tag semantic synonym

**Purpose**: Detect two vault-wide tags that name the same concept under different spellings (e.g. `llm` ↔ `large-language-model`, `react` ↔ `reactjs`, #167). A fixed synonym dictionary was rejected in #119 as over-firing and costly to maintain, so this judgment is LLM-only, gated and confirmed the same way as E12b above.

**Inputs**: `frontmatter_records` from the scan bundle (already collected, no re-scan) — the same vault-wide tag aggregation E9a already builds in `audit-validate.py`, re-derived here in-skill. E9c never touches that reference impl or the `--dod` gate.

**Tools used**: AskUserQuestion (no Read needed — tag strings and file counts are enough context for the judgment; unlike E12b there are no file bodies to read).

**Skip conditions** (exit sub-check immediately, no findings added):
- `--deep` flag not passed.
- Fewer than 2 distinct tags meet the `E9_MIN_FILES` (= 3) floor below.

**Procedure**:

1. Build `tag_files` = lowercase tag → set(file paths), from every `frontmatter_records[].fm.tags` (same aggregation as E9a). Drop any tag used in fewer than `E9_MIN_FILES` (3) files — reuses E9a/E9b's existing FP floor so a one-off tag never reaches LLM judgment.

2. Build **candidate pairs** deterministically (no LLM, cheap prefilter — mirrors E12b's shared-tag/wikilink prefilter, adapted to compare tags instead of pages; #167's D10 design note names these signals source-overlap + common-neighbor). First precompute a tag → co-occurring-tags map once, in a single pass over `frontmatter_records` (not per pair — that map is what Step 1's `tag_files` pass already walks, so build both together). Then, for every distinct pair `(A, B)` that both survived Step 1, it's a candidate when EITHER holds:
   - **source overlap**: at least one file's `tags` list contains BOTH `A` and `B`, or
   - **common neighbor**: `A`'s entry in the precomputed map shares at least one tag with `B`'s entry.

   Skip any pair already reported by E9a — a lookup against `vocabulary_pairs[]` (produced by SCAN Phase's `detect-vocabulary` step), not a re-derivation. Regular singular/plural is already deterministically handled there, no LLM opinion needed. If zero candidate pairs, exit sub-check (no findings).

3. Judge each candidate pair: do `A` and `B` name the **same concept** under two different spellings/phrasings (a true synonym), as opposed to two related-but-distinct concepts that merely tend to co-occur (e.g. a language and a tool commonly used with it)? Judge from the tag strings and their file counts alone.

4. Stage every pair judged synonymous as a DEEP candidate. Do **not** add it to the findings list yet — Step 5 is the mandatory FP-mitigation gate (same contract as E12b Step 6).

5. If any DEEP candidates exist, confirm each **individually**, exactly like E12b Step 6 — one `AskUserQuestion` per candidate pair, batched in groups of ≤4 (sequential calls if more than 4):
   ```
   AskUserQuestion:
     questions:
       - question: "'llm' (N개 파일) ↔ 'large-language-model' (M개 파일) — 같은 개념의 동의어로 볼까요?"
         header: "동의어 확인"
         options:
           - label: "동의어 — 보고에 포함"
             description: "<one-line reason the tags are synonymous>"
           - label: "동의어 아님 — 무시"
             description: "판단 오류로 보고 이 쌍은 건너뜀"
       - question: "'X' (N개 파일) ↔ 'Y' (M개 파일) — 같은 개념의 동의어로 볼까요?"
         header: "동의어 확인"
         options: [...]   # same two-option shape, one row per additional candidate pair
   ```
   Each pair's answer is independent. A candidate the user declines is dropped silently — no finding, no residual state.

6. Every confirmed pair becomes one finding, folded into the SAME `tag_vocabulary_inconsistency` bucket E9a/E9b already populate (renders under the existing E9 vault-wide heading in REPORT — no new error type):
   ```
   {
     "error_type": "tag_vocabulary_inconsistency",
     "severity": "Warning",
     "priority": "P2",
     "path": "",
     "detail": "태그 의미 동의어(LLM 판단, --deep): 'llm' (N개 파일) ↔ 'large-language-model' (M개 파일) — <reason>",
     "auto_fix_eligible": false
   }
   ```
   Append it to the findings list produced by CLASSIFY.

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to REPORT with the (possibly unchanged) findings list.

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

Within each priority group: sort by severity first (Critical → Warning → Info), then by error code ascending (E1→E2→E3→E4 within P0; E6→E7→E10→E11→E12 within P1; E5→E8→E9 within P2). E9 findings are vault-level (`path: ""`) — render them under a vault-wide heading (e.g. `볼트 전역`) instead of a per-file bullet.

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

> **우선순위 출력 순서**: P0 → P1 → P2. 각 priority 내 정렬: Critical severity 먼저, 그 다음 Warning, Info 순. 동일 severity 내에서는 error type 코드 순 (E1→E2→E3→E4 / E6→E7→E10→E11→E12 / E5→E8→E9). E9는 볼트 전역(path:"") finding이라 파일별 bullet 대신 "볼트 전역" 헤딩 아래에 출력합니다. "사용자 확인 게이트"는 OPTIONAL-FIX 단계(E2 자동 수정)에만 적용됩니다 — 그 외 항목은 표시만 합니다. E6/E7/E8/E9/E10/E11/E12는 의미적 판단(처리/promote/archive/이동/정준형 선택/재컴파일)이 필요해 auto-fix 대상이 아닙니다.

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
| `--deep` | Opt-in LLM path (#336, #167): after CLASSIFY, run Phase 2.5 DEEP to judge candidate `wiki/` page pairs for cross-page semantic contradiction (E12b) and candidate tag pairs for semantic synonym (E9c). Off by default. |
| `status` | Show current audit-state stats only (no scan) |

---

## Rules

- NEVER call vault-searcher. This skill is OVM-local.
- NEVER re-implement frontmatter or filename parsing inline. Always delegate to `ovm-primitives.sh`.
- NEVER read file bodies during SCAN or CLASSIFY. All classification is derived from primitive JSON outputs.
- Auto-fix is OFF by default. OPTIONAL-FIX only runs after explicit "수정 실행" confirmation.
- `audit-state mark-clean` MUST be called after every successfully processed file.
- Dry-run mode outputs the REPORT but performs no mutations and does not call `mark-clean`.
- The AskUserQuestion in OPTIONAL-FIX is the only allowed user interaction, EXCEPT the Phase 2.5 DEEP confirm gates (`--deep` only, E12b and E9c).
- Phase 2.5 DEEP never runs without `--deep`. Without it, this skill makes zero LLM judgment calls end to end.
- Every DEEP candidate MUST pass the AskUserQuestion confirm gate before becoming a finding — no silent auto-report of a semantic judgment.
- Severity levels: Critical (data integrity risk), Warning (quality/navigation risk), Info (style/convention).
