---
name: audit
description: "Scan the vault for structural defects and surface a triage report. Detects 9 error types: missing frontmatter (E1), missing required fields (E2), filename convention violations (E3, with rename suggestion), orphan notes (E5, with tag-based connection candidates), stale sources (E6), tag/property vocabulary inconsistencies (E9a/E9b deterministic; optional `--deep` LLM opt-in for E9c semantic synonym), misplaced files (E10), unstructured paths (E11), and stale or unverifiable wiki pages (E12a, stale/missing/unparseable `verified:`; optional `--deep` LLM opt-in for E12b cross-page contradiction). Example: '/audit' or '/audit --deep'"
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

1. Resolve `$VAULT_ROOT`/`$scan_dir` — same chain as `ovm-primitives.sh`/`pre-write-guard.sh`
   (`VAULT_BRIDGE_VAULT_ROOT` > `VAULT_BRIDGE_VAULT_PATH` > `~/vault`, tilde-expanded).
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
   Files absent from sidecar (untracked) are treated as dirty. Files with `status: clean` are skipped unless `--force` was passed.

> **`audit-state` exit 3 applies to EVERY call** (#443) — the state file is unusable and
> nothing is written back. **STOP the audit at the first exit 3**, never treat it as empty
> state; report the sidecar path in Korean (what is preserved where, and how to recover:
> `scripts/README.md` → `audit-state`).

4. Emit a Korean scan-start status line: file count targeted + estimated scan time.

5. Run frontmatter scan (`--path`-scoped) **into a file** — never to stdout. `$scan_tmp` is
   a fresh per-run dir (`mktemp -d`, never a fixed `/tmp` path — concurrent audits would
   overwrite each other's scans); Steps 5–7 write there and Step 7b reads them back.
   **Run Steps 5–7b in ONE Bash call** — shell state does not survive between Bash calls
   and a `mktemp -d` value cannot be re-derived, so a split run resolves `"$scan_tmp/..."`
   against an empty variable:
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
   Always vault-wide, `--path`-unscoped — E9 is a vault-level check. Emits a JSON array of pairs `{sub, a, b, a_files, b_files}` (empty when consistent); pass it straight to CLASSIFY as the E9 findings source.

10. Rank E5 orphan connection candidates (deterministic, no LLM):
    ```bash
    bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" e5-candidates "$VAULT_ROOT/notes"
    ```
    Vault-wide, unscoped; paths are `$VAULT_ROOT`-relative (#631) — join on `rec.path`.

**Outputs**: An in-memory scan bundle. The raw per-file scans stay on disk in `$scan_tmp`
and are NEVER read into context — CLASSIFY gets only the reduced form (#614):
```
{
  scan_summary {           // Step 7b — replaces raw frontmatter/filename records + link index
    total_files, max_per_type,
    link_index {targets, sources},   // size of the Step 7 index (which never enters context)
    errors {               // E1 E2 E3 E5 E6 E10 E11 E12_stale E12_unverified — each
                           // {count, paths[] | records[], omitted?}; ONLY defect-bearing
                           // entries, clean files never appear. Per-type field set:
                           // scripts/README.md → scan-summary.py.
    }
  }
  manifest_summary?        // {file_count, generated_at} or null
  vocabulary_pairs[]       // from detect-vocabulary (E9, vault-wide)
  e5_candidates[]          // from e5-candidates (E5) — joined to E5 paths by path
}
```
`count` is the FULL number found; `paths`/`records` may be a capped prefix. Report `count`,
never the emitted-list length, and say a list was cut whenever `omitted` is present.
**Bullet-per-file or per-finding work (REPORT's file bullets, Phase 4's E2 batch) needs the
whole list** — whenever that type carries `omitted`, re-run Step 7b with a larger
`--max-per-type` into a file and **Read** it before acting.
An `unreadable` bucket means those files could not be READ at all — its own item, never
E1/E3/E5 findings about content nobody examined.

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
| E9 | `tag_vocabulary_inconsistency` | Warning | P2 | `vocabulary_pairs` (vault-wide, Step 9) | — (display-only; `path: ""`) |
| E10 | `misplaced_file` | Warning | P1 | `scan_summary.errors.E10` | — (display-only) |
| E11 | `unstructured_path` | Warning | P1 | `scan_summary.errors.E11` | — (display-only) |
| E12 | `wiki_self_audit` (`wiki_stale` + `wiki_unverified`, #494) | Warning | P1 | `scan_summary.errors.E12_stale` / `.E12_unverified` | — (display-only) |

> **The table above is a summary; the binding rules are in
> `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`** — priority rationale per code
> (`## Priority Mapping`), E9's vault-level `path: ""` finding shape and its ≥3-files-per-form
> FP guard (`## E9`), E12's `STALE_WIKI_DAYS` staleness plus the `wiki_unverified` companion
> (`## E12`), and the display-only criteria for E3/E5/E10/E11. E9c and E12b are the `--deep`
> opt-ins (Phase 2.5). Read that file before changing any classification behavior.

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

**Termination condition**: All dirty files classified. Proceed to Phase 2.5 if `--deep` was passed, otherwise directly to REPORT.

---

## Phase 2.5 — DEEP (opt-in, `--deep`)

**Purpose**: Run every LLM-judgment check gated behind `--deep`. This is the **only** phase that reads file bodies or uses LLM judgment — SCAN, CLASSIFY, and REPORT stay LLM-cost-0 without `--deep`.

**Skip condition**: `--deep` not passed → skip this phase entirely and go to REPORT. This is the default.

**When `--deep` IS passed**: read `${CLAUDE_PLUGIN_ROOT}/reference/audit-deep.md` and follow it — it holds the full procedure for both sub-checks, E12b (cross-page wiki contradiction, #336) and E9c (tag semantic synonym, #167), each with its own deterministic prefilter and per-candidate `AskUserQuestion` confirm gate. Only confirmed pairs become findings (E12b → `wiki_contradiction`; E9c → the existing `tag_vocabulary_inconsistency` bucket); a declined candidate is dropped silently.

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to REPORT.

---

## Phase 3 — REPORT

**Purpose**: Group findings by priority (P0 → P1 → P2) and display a structured triage report in Korean.

**Inputs**: Findings list from CLASSIFY.

**Tools used**: None (output only).

## REPORT Output Contract

Output is grouped by priority, P0 (must-fix) first, then P1, then P2.
Within each priority group: sort by severity first (Critical → Warning → Info), then by error code ascending (unreadable→E1→E2→E3 in P0; E6→E10→E11→E12 in P1; E5→E9 in P2). E9 findings are vault-level (`path: ""`) — render them under a vault-wide heading (e.g. `볼트 전역`) instead of a per-file bullet.

Each finding line format: `[E-code/priority/severity] type — N건` header, then one bullet per file with path and one-line description.

Report header: vault state summary (note count, clean/dirty/untracked), manifest info, recent git activity (omit if 0 commits or not a git repo).

Footer: auto-fixable count, manual-action count.

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

A representative sample of this layout (header, per-priority groups, footer) is in
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` under **REPORT output example**.

> **사용자 확인 게이트는 OPTIONAL-FIX(E2 자동 수정)에만 적용됩니다** — 나머지 타입은 의미적 판단이 필요해 표시만 합니다.

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and user has not already opted out. Otherwise exit after marking clean.

---

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings. Gate behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.
  `provenance` is a required E2 field (#477 item 4) but is NOT auto-fillable — unlike `tags`,
  there is no safe deterministic inference for "where did this come from." When `provenance` is
  among the missing fields, surface it in the confirmation gate and ask the user for the actual
  origin instead of writing a placeholder.

**Tag inference** (#127, deterministic — no LLM; batched #152): when `tags:` is missing, do
NOT insert an empty `tags: []`. Derive a tag PROPOSAL via a SINGLE batched
`ovm-primitives.sh infer-tags <relpath1> <relpath2> ...` — one Python process for all E2
findings, never one per finding. Tier rules and worked examples:
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **E2 tag inference**.
The proposal is never auto-committed — it is previewed in the confirmation gate below.

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
| `--deep` | Opt-in LLM path (#336, #167): run Phase 2.5 DEEP after CLASSIFY (E12b + E9c). Off by default. |
| `status` | Bare positional arg (not `--flag`). Skips SCAN/CLASSIFY/REPORT/OPTIONAL-FIX: run `audit-state stats`, render as one Korean status line, terminate — no mutation. |

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
