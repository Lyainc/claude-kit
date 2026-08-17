---
name: audit
description: "Scan the vault for structural defects and surface a triage report. Detects 9 error types: missing frontmatter (E1), missing required fields (E2), filename convention violations (E3, rename suggestion), orphan notes (E5, tag-based connection candidates), stale sources (E6), tag/property vocabulary inconsistencies (E9a/E9b deterministic; `--deep` adds E9c semantic synonym), misplaced files (E10), unstructured paths (E11), and stale or unverifiable wiki pages (E12a, stale/missing/unparseable `verified:`; `--deep` adds E12b cross-page contradiction). Example: '/audit' or '/audit --deep'"
effort: low
allowed-tools: Read Edit Bash AskUserQuestion
---

**User language: Korean.** All user-facing output (responses, AskUserQuestion prompts, confirmation messages, progress lines) MUST be in Korean.

Scan the vault at `$VAULT_ROOT` (Phase 1 Step 1) for structural defects and produce a triage report grouped by severity.

---

## Pipeline Overview

```
SCAN (shell, LLM=0) → CLASSIFY (rule-based, LLM=0) → REPORT (grouped by severity) → OPTIONAL-FIX (explicit opt-in only)
```

Each phase has explicit inputs, outputs, and a termination condition. Do NOT collapse phases.

---

## Phase 1 — SCAN

**Purpose**: Collect raw scan data from the vault using ovm-primitives. Zero LLM token cost.

**Inputs**: `$VAULT_ROOT` (Step 1); Steps 5–6 scope to `$VAULT_ROOT/<subdir>` under `--path`.

**Tools used**: Bash only.

**Procedure**:

1. Resolve `$VAULT_ROOT` — same chain as `ovm-primitives.sh`/`pre-write-guard.sh`:
   ```bash
   VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
   [ -z "$VAULT_ROOT" ] && VAULT_ROOT="$HOME/vault"
   VAULT_ROOT="${VAULT_ROOT/#\~/$HOME}"
   ```
   `scan_dir` = `$VAULT_ROOT` unscoped, or `$VAULT_ROOT/<subdir>` under `--path <subdir>`.
   `$scan_dir` → Steps 5–6; `$VAULT_ROOT` → everything else.

2. Start metrics (save `token`):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics start "audit"
   ```

3. Build the dirty file list using audit-state warm-up (O(dirty files) after first run):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state list-dirty-since
   ```
   Files absent from sidecar (untracked) count as dirty; `status: clean` files are skipped unless `--force` was passed.

> **`audit-state` exit 3 applies to EVERY call** — the state file is unusable and nothing is
> written back. **STOP the audit at the first exit 3**, never treat it as empty state; report
> the sidecar path in Korean (what is preserved, how to recover: `scripts/README.md` → `audit-state`).

4. Emit a Korean scan-start status line: file count targeted + estimated scan time.

5. Run frontmatter scan (`--path`-scoped) **into a file** — never to stdout. `$scan_tmp` is
   a fresh per-run dir (`mktemp -d`, never a fixed `/tmp` path, to avoid concurrent-audit
   collisions); Steps 5–7 write there, Step 7b reads it back. **Run Steps 5–7b in ONE Bash
   call** — `$scan_tmp` can't be re-derived across calls, so a split run loses it:
   ```bash
   scan_tmp="$(mktemp -d)"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-frontmatter "$scan_dir" > "$scan_tmp/fm.json"
   ```

6. Run filename scan (`--path`-scoped), same redirect:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-filename "$scan_dir" > "$scan_tmp/fn.json"
   ```

7. Build a global link index (`{target_stem → [source_paths]}`) from wikilinks vault-wide —
   **never `--path`-scoped** (same E9 exception as Step 9): a file in-scope can still be
   linked from outside it.

   ONE dir-shaped call returns the FINISHED index — never drive a `find` loop and never
   call `extract-wikilinks` per file (#614):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" extract-wikilinks-batch "$VAULT_ROOT" > "$scan_tmp/links.json"
   ```
   Wikilinks inside code fences or inline code are masked out (#434).

7b. Reduce those three files to the bundle — the ONLY form of them CLASSIFY ever sees:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan-summary.py" \
     --frontmatter "$scan_tmp/fm.json" --filename "$scan_tmp/fn.json" --index "$scan_tmp/links.json"
   ```
   **Never `cat` a raw scan file** — same rule as Step 8's manifest (#468, #460) at a
   worse scale; measurements and the cap rationale: `reference/vault-audit-rules.md` →
   `## SCAN output budget`.
   Exit 0 → parse stdout as the scan bundle (shape below).
   Exit 3 (a scan file absent or unparseable) → **STOP the audit**, name the unusable input;
   never fall back to a raw `cat`, never treat it as an empty scan.
   `omitted: N` means that type's list was CUT — `$scan_tmp` is gone by then (Step 5), so
   re-run Steps 5–7b as ONE new Bash call with a larger `--max-per-type`, into a file, via
   **Read**.

8. Read manifest summary (used for REPORT header) through the filter script — **never `cat` the
   manifest directly** (#468, #460). Uses the `$VAULT_ROOT` from Step 1:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/.vault-bridge/manifest.json"
   ```
   Exit 0 → `manifest_summary` = parsed `{file_count, generated_at}`; exit 3 → null.
   **Apply `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → Reading the manifest as
   written — that section is the binding contract** for why a raw `cat` is forbidden and the full
   exit-code branch; the line above is a locator, not a summary you may act from alone. This whole
   step is pinned VERBATIM by `_SKILL_STEP8` in
   `obsidian-vault-manager/scripts/test/test-manifest-reads.py`.

9. Detect E9 vocabulary inconsistency pairs (vault-wide, deterministic — never aggregate tags/keys in the LLM):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" detect-vocabulary "$VAULT_ROOT"
   ```
   Always vault-wide, unscoped by `--path` (E9 is vault-level). Emits pairs `{sub, a, b, a_files, b_files}` (empty when consistent) straight into CLASSIFY as the E9 source.

10. Rank E5 orphan connection candidates (deterministic, no LLM):
    ```bash
    bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" e5-candidates "$VAULT_ROOT/notes"
    ```
    Vault-wide, unscoped; paths are `$VAULT_ROOT`-relative — join on `rec.path`.

**Outputs**: An in-memory scan bundle. The raw per-file scans stay on disk in `$scan_tmp`
and are NEVER read into context — CLASSIFY gets only the reduced form (#614):
```
{
  scan_summary {           // Step 7b — reduces raw frontmatter/filename records + link index
    total_files, max_per_type,
    link_index {targets, sources},   // size only — the Step 7 index itself never enters context
    errors {               // E1 E2 E3 E5 E6 E10 E11 E12_stale E12_unverified, defect-bearing
                           // only; {count, paths[] | records[], omitted?}. Field set:
                           // scripts/README.md → scan-summary.py.
    }
  }
  manifest_summary?        // {file_count, generated_at} or null
  vocabulary_pairs[]       // from detect-vocabulary (E9, vault-wide)
  e5_candidates[]          // from e5-candidates (E5) — joined to E5 paths by path
}
```
`count`/`omitted`/`unreadable` semantics and the re-run procedure for a capped type are the
binding contract in `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **SCAN output
budget** — apply as written. Report `count`, never the emitted-list length.

**Termination condition**: All scan data collected. Proceed to CLASSIFY.

---

## Phase 2 — CLASSIFY

**Purpose**: Apply deterministic rules to the scan bundle and produce a findings list. Zero LLM calls.

**Inputs**: Scan bundle from SCAN.

**Error types** (9: E1–E3, E5–E6, E9–E11, E12 — E4/E7/E8 are retired, never reused).

| Code | Type | Severity | Priority | Source | Auto-fix |
|---|---|---|---|---|---|
| — | `unreadable` | Critical | P0 | `scan_summary.errors.unreadable` | — |
| E1 | `missing_frontmatter` | Critical | P0 | `scan_summary.errors.E1` | — |
| E2 | `missing_required_fields` | Critical | P0 | `scan_summary.errors.E2` | ✓ (add fields; `tags:` inferred via type/slug/folder — see Phase 4) |
| E3 | `filename_convention_violation` | Warning | P0 | `scan_summary.errors.E3` | — (suggests `권장 파일명`) |
| E5 | `orphan_note` | Warning | P2 | `scan_summary.errors.E5` + `e5_candidates` | — (suggests tag-based `연결 후보`) |
| E6 | `stale_inbox` | Warning | P1 | `scan_summary.errors.E6` | — |
| E9 | `tag_vocabulary_inconsistency` | Warning | P2 | `vocabulary_pairs` (vault-wide) | — (display-only; `path: ""`) |
| E10 | `misplaced_file` | Warning | P1 | `scan_summary.errors.E10` | — (display-only) |
| E11 | `unstructured_path` | Warning | P1 | `scan_summary.errors.E11` | — (display-only) |
| E12 | `wiki_self_audit` (`wiki_stale` + `wiki_unverified`) | Warning | P1 | `scan_summary.errors.E12_stale` / `.E12_unverified` | — (display-only) |

> **The table above is a summary; the binding rules — priority rationale per code, E9/E12
> FP guards and staleness constants, display-only criteria per type — are in
> `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`.** Read that file before changing
> any classification behavior. (E9c/E12b are the `--deep` opt-ins, Phase 2.5.)

**Output**: Findings list:
```
[
  {
    "error_type": "missing_frontmatter",
    "severity": "Critical|Warning|Info",
    "priority": "P0|P1|P2",
    "path": "relpath",
    "detail": "human-readable context",
    "auto_fix_eligible": true|false
  }
]
```

**Termination condition**: All dirty files classified — Phase 2.5 if `--deep` was passed, else REPORT directly.

---

## Phase 2.5 — DEEP (opt-in, `--deep`)

**Purpose**: Run every LLM-judgment check gated behind `--deep` — the only phase that reads file bodies or uses LLM judgment; SCAN/CLASSIFY/REPORT stay LLM-cost-0 without it.

**Skip condition**: `--deep` not passed → skip this phase entirely and go to REPORT. This is the default.

**When `--deep` IS passed**: read `${CLAUDE_PLUGIN_ROOT}/reference/audit-deep.md` and apply it as written — full procedure for E12b (#336) and E9c (#167), each with its own prefilter and `AskUserQuestion` confirm gate. Only confirmed pairs become findings.

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to REPORT.

---

## Phase 3 — REPORT

**Purpose**: Group findings by priority (P0 → P1 → P2) and display a structured triage report in Korean.

**Inputs**: Findings list from CLASSIFY.

**Tools used**: None (output only).

## REPORT Output Contract

Grouped by priority (P0 must-fix → P1 → P2); within each group, sort by severity (Critical→Warning→Info), then error code ascending (unreadable→E1→E2→E3 in P0; E6→E10→E11→E12 in P1; E5→E9 in P2). E9 is vault-level (`path: ""`) — render under a vault-wide heading (e.g. `볼트 전역`), not per-file.

Each finding line: `[E-code/priority/severity] type — N건` header, then one bullet per file (path + one-line description).

Report header: vault state (note count, clean/dirty/untracked), manifest info, recent git activity (omit if none or not a repo).

Footer: auto-fixable count, manual-action count.

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

A representative sample of this layout (header, per-priority groups, footer) is in
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` under **REPORT output example**.

> **사용자 확인 게이트는 OPTIONAL-FIX(E2 자동 수정)에만 적용됩니다** — 나머지 타입은 의미적 판단이 필요해 표시만 합니다.

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and the user hasn't opted out; otherwise exit after marking clean.

---

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings, gated behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.
  `provenance` is required but NOT auto-fillable — surface it in the confirmation gate per-file
  and ask the user for the real origin, never a placeholder. Full rationale:
  `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **Auto-fix eligibility**.

**Tag inference**: when `tags:` is missing, do NOT insert an empty `tags: []` — derive a
proposal via ONE batched `ovm-primitives.sh infer-tags <relpath1> <relpath2> ...` call, never
one per finding. Tier rules and examples: `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`
→ **E2 tag inference**. Never auto-committed — previewed in the confirmation gate below.

**Auto-fix NOT eligible** (never mutate): E1, E3, E5, E6, E9, E10, E11, E12. The binding list,
with each type's reason for needing a human decision:
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **Auto-fix eligibility**.

**Procedure**:

1. If `auto_fix_eligible` count > 0, first compute the tag proposals for every
   E2 finding whose missing fields include `tags` in ONE batched call (pass all
   such relpaths as arguments — see **Tag inference** above):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" infer-tags <relpath1> <relpath2> ...
   # >~200 paths (ARG_MAX headroom)? Pipe one per line into `infer-tags -` instead.
   ```
   Match each element's `path` back to its finding. A per-file failure surfaces as
   `error` + `inferred_tags: []` on that element and the batch still succeeds (exit
   is non-zero only when EVERY path failed). Then ask (single AskUserQuestion),
   showing each inferred proposal on its own line as `추론된 태그: [X, Y, Z]`:
   ```
   AskUserQuestion:
     question: "다음 F건의 frontmatter 이슈를 자동으로 수정할까요?"
     context: |
       수정 대상:
       • missing_required_fields: X건 (tags/type/created 추가)

       추론된 태그 (제안):
       • notes/llm/decision-2026-04-12-context-window.md → [decision, context, window, llm]
       • sources/capture-2026-05-01-obsidian-api.md → [capture, obsidian, api]

       provenance 누락 (자동 추론 불가, 개별 확인 필요):
       • sources/capture-2026-05-03-untitled-clip.md → 출처를 알려주시면 채워 넣을게요

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
     - When `provenance` is missing, do NOT write a placeholder — ask the user for the real origin
       (or skip that field on this file if they don't know it) rather than fabricate one.
   - All edits are **frontmatter-only** — never touch the markdown body.

4. After all fixes, mark all processed files clean:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state mark-clean <relpath>
   ```

5. Stop metrics (`token`):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics stop <token>
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics report <token>
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
| `--path <dir>` | Scope Steps 5–6 to `$VAULT_ROOT/<dir>` (link index/E9 stay vault-wide) |
| `--reset-state` | Call `audit-state invalidate` on all vault files before scanning |
| `--deep` | Opt-in LLM path (#336/#167): run Phase 2.5 DEEP after CLASSIFY. Off by default. |
| `status` | Bare positional arg (not `--flag`). Skips the pipeline: run `audit-state stats`, render one Korean status line, terminate — no mutation. |

---

## Rules

- NEVER call vault-searcher. This skill is OVM-local.
- NEVER re-implement frontmatter/filename parsing inline — always delegate to `ovm-primitives.sh`.
- NEVER read file bodies during SCAN or CLASSIFY — classification is derived from primitive JSON outputs.
- Auto-fix is OFF by default — OPTIONAL-FIX only runs after explicit "수정 실행" confirmation.
- `audit-state mark-clean` MUST run after every successfully processed file.
- Dry-run outputs the REPORT but performs no mutations and never calls `mark-clean`.
- AskUserQuestion in OPTIONAL-FIX is the only allowed user interaction, except Phase 2.5 DEEP's confirm gates (`--deep` only).
- Phase 2.5 DEEP never runs without `--deep`. Without it, this skill makes zero LLM judgment calls end to end.
- Every DEEP candidate MUST pass the AskUserQuestion confirm gate before becoming a finding — no silent semantic auto-report.
