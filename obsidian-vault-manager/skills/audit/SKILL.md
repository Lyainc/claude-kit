---
name: audit
description: "Scan the vault for structural defects and surface a triage report. Detects 10 error types: missing frontmatter (E1), missing required fields (E2), filename convention violations (E3, with rename suggestion), broken wikilinks (E4), orphan notes (E5, with tag-based connection candidates), stale inbox (E6), tag/property vocabulary inconsistencies (E9a/E9b deterministic; optional `--deep` LLM opt-in for E9c semantic synonym), misplaced files (E10), unstructured paths (E11), and stale wiki pages (E12a, stale `verified:`; optional `--deep` LLM opt-in for E12b cross-page contradiction). Example: '/audit' or '/audit --deep'"
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

> **`audit-state` exit 3 — applies to EVERY call of this subcommand** (#443), not just the one above: `list-dirty-since`, `is-clean`, `mark-clean`, and the per-file `invalidate` loop that `--reset-state` runs all load the state file before dispatch, so any of them can be the first to hit it. Exit 3 means the state file is unusable; the original was preserved at `<path>.corrupt-<ISO8601>` (identical content reuses one sidecar, so a per-file loop does not litter) and nothing was written back. **STOP the audit at the first exit 3** — do not continue the loop, and never treat it as an empty state. Report in Korean: the sidecar path, and that `audit-state.json.bak` holds the last good state if present, while deleting `audit-state.json` instead discards all audit state and forces a full re-scan.

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
   Collect: `{source_path, links[]}` for each file. Wikilinks inside code fences or inline code are masked out before extraction (#434) — a backticked `[[Note]]` is a syntax example, so it must never reach E4.

7. Build a global link index: `{target_stem → [source_paths]}` from all extracted wikilinks across the full vault (not just dirty files). This is required for orphan detection (which needs the full inbound-link map).

   To build the full link index efficiently, run `extract-wikilinks` on all `.md` files found by:
   ```bash
   find ~/vault -name '*.md' -not -path '*/.*'
   ```

8. Read manifest summary (used for REPORT header):
   ```bash
   cat "$VAULT_ROOT/.vault-bridge/manifest.json" 2>/dev/null
   ```
   Use the resolved `$VAULT_ROOT` from Steps 4–7 (`VAULT_BRIDGE_VAULT_ROOT` → `VAULT_BRIDGE_VAULT_PATH` → `~/vault`), not a hardcoded path.
   Extract `file_count` and `generated_at` if the file exists and is valid JSON. If absent or unparseable, set `manifest_summary` to null.

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

**Error types** (10 types: E1–E6, E9–E11 v4, E12 v5 — E7/E8 were removed with the v4 §3.3 status-machine promotion gate, v5 §6, #480). Detailed pseudocode and false-positive guards live in `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` — read that file when implementing or debugging classification logic.

| Code | Type | Severity | Priority | Source | Auto-fix |
|---|---|---|---|---|---|
| E1 | `missing_frontmatter` | Critical | P0 | `frontmatter_records` | — |
| E2 | `missing_required_fields` | Critical | P0 | `frontmatter_records` | ✓ (add fields; `tags:` inferred via type/slug/folder — see Phase 4) |
| E3 | `filename_convention_violation` | Warning | P0 | `filename_records` | — (suggests `권장 파일명`) |
| E4 | `broken_wikilink` | Critical | P0 | `wikilinks_by_file` | — |
| E5 | `orphan_note` | Warning | P2 | `inbound_links` | — (suggests tag-based `연결 후보`) |
| E6 | `stale_inbox` | Warning | P1 | `frontmatter_records` (`created` + `status`) | — |
| E9 | `tag_vocabulary_inconsistency` | Warning | P2 | `frontmatter_records` (vault-wide tags + keys) | — (display-only; `path: ""`) |
| E10 | `misplaced_file` | Warning | P1 | `frontmatter_records` (`type` + folder) | — (display-only) |
| E11 | `unstructured_path` | Warning | P1 | `frontmatter_records` (path) | — (display-only) |
| E12 | `wiki_self_audit` | Warning | P1 | `frontmatter_records` (`wiki/` path + `type: wiki` + `verified`) | — (display-only) |

> **Priority mapping** (v4 §6.1): E1–E4 = P0 (무결성/integrity). E6, E10–E12 = P1 (정체·구조/stagnation·structure). E5, E9 = P2 (quality signal). (E10/E11 are the structural checks per #128/#129; E12 is the wiki self-audit per #330.)
> **E9 vocabulary** (#119): a **vault-level** check, not per-file — aggregates tags/keys across the whole vault and emits one finding per inconsistent pair with `path: ""`. E9a = a tag and its regular `+s` plural both used (`api`↔`apis`); E9b = a frontmatter key in camelCase and its snake_case equivalent both used (`sourceUrl`↔`source_url`). FP guard: report only when BOTH forms appear in ≥3 files. E9c (semantic synonyms, e.g. `llm`↔`large-language-model`) ships as the skill-only `--deep` LLM opt-in (#167) — see Phase 2.5 below (mirrors E12b's skill-only design). Never auto-fixed — the canonical form is the user's choice.
> **E3 / E5 / E10 / E11 detail** (suggested filename, orphan connection candidates,
> misplaced-file and unstructured-path scoping): all display-only, full criteria in
> `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`.
> **E12 wiki self-audit** (#330, v5 §7 U3): flags a `wiki/` page (top folder `wiki/` AND `type: wiki`) whose `verified:` age exceeds `STALE_WIKI_DAYS` (90) — staleness is the abandonment risk for the LLM wiki. A missing/unparseable `verified:` is skipped (uncomputable). Display-only (recompile/re-verify is a semantic decision). E12a (staleness) ships deterministically in CLASSIFY. E12b (cross-page semantic contradiction, #336) ships as the skill-only `--deep` LLM opt-in — see Phase 2.5 DEEP below (mirrors E9c's skill-only design).

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

**Purpose**: Run every LLM-judgment check gated behind `--deep`. This is the **only** phase that reads file bodies or uses LLM judgment — SCAN, CLASSIFY, and REPORT stay LLM-cost-0 without `--deep`.

**Skip condition**: `--deep` not passed → skip this phase entirely and go to REPORT. This is the default.

**When `--deep` IS passed**: read `${CLAUDE_PLUGIN_ROOT}/reference/audit-deep.md` and follow it. It holds the full procedure for both sub-checks — E12b (cross-page wiki contradiction, #336) and E9c (tag semantic synonym, #167) — each with its own deterministic candidate prefilter and its own per-candidate `AskUserQuestion` confirm gate. Every confirmed pair becomes a finding appended to the CLASSIFY list (E12b → `wiki_contradiction`; E9c → the existing `tag_vocabulary_inconsistency` bucket). A declined candidate is dropped silently.

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to REPORT.

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

Within each priority group: sort by severity first (Critical → Warning → Info), then by error code ascending (E1→E2→E3→E4 within P0; E6→E10→E11→E12 within P1; E5→E9 within P2). E9 findings are vault-level (`path: ""`) — render them under a vault-wide heading (e.g. `볼트 전역`) instead of a per-file bullet.

Each finding line format: `[E-code/priority/severity] type — N건` header, then one bullet per file with path and one-line description.

Report header: vault state summary (note count, clean/dirty/untracked), manifest info, recent git activity (omit if 0 commits or not a git repo).

Footer: auto-fixable count, manual-action count.

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

A representative sample of this layout (header, per-priority groups, footer) is in
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` under **REPORT output example**.

> **사용자 확인 게이트는 OPTIONAL-FIX 단계(E2 자동 수정)에만 적용됩니다** — 그 외 항목은 표시만 합니다. E6/E9/E10/E11/E12는 의미적 판단(처리/archive/이동/정준형 선택/재컴파일)이 필요해 auto-fix 대상이 아닙니다. (정렬 순서는 위 REPORT Output Contract 참조.)

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and user has not already opted out. Otherwise exit after marking clean.

---

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings. Gate behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.

**Tag inference** (#127, deterministic — no LLM; batched #152): when `tags:` is missing, do
NOT insert an empty `tags: []`. Derive a tag PROPOSAL from three tiers (1 `type:` field, 2
filename slug, 3 parent folder) via a SINGLE batched call
`ovm-primitives.sh infer-tags <relpath1> <relpath2> ...` — one Python process for all E2
findings, not one per finding. It emits a JSON array, one element per path, order preserved,
duplicates dropped, all lowercased. The tier rules and worked examples are in
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` under **E2 tag inference**.
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
