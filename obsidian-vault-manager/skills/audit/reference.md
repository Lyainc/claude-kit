# audit — reference

Detail moved out of `SKILL.md` to keep it under Codex's 8,000-byte invoked-skill limit (#750). Text is the
previous `SKILL.md` wording (fenced commands omitted: they stay in `SKILL.md`). It refines the rules in
`SKILL.md`; it does not replace them. The Phase 4 procedure is in `fix.md`. Binding classification rules:
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`.

## Pipeline

```
SCAN (shell, LLM=0) → CLASSIFY (rule-based, LLM=0) → REPORT (grouped by severity) → OPTIONAL-FIX (explicit opt-in only)
```

Each phase has explicit inputs, outputs, and a termination condition. Do NOT collapse phases.

## Phase 1 — SCAN: purpose and per-step rationale

**Purpose**: Collect raw scan data from the vault using ovm-primitives. Zero LLM token cost.

**Inputs**: `$VAULT_ROOT` (Step 1); Steps 5–6 scope to `$VAULT_ROOT/<subdir>` under `--path`.

**Tools used**: Bash only.

**Procedure**:

3. Build the dirty file list using audit-state warm-up (O(dirty files) after first run):
   (command: `SKILL.md` Step 3)
   Files absent from sidecar (untracked) count as dirty; `status: clean` files are skipped unless `--force` was passed.

5. Run frontmatter scan (`--path`-scoped) **into a file** — never to stdout. `$scan_tmp` is
   a fresh per-run dir (`mktemp -d`, never a fixed `/tmp` path, to avoid concurrent-audit
   collisions); Steps 5–7 write there, Step 7b reads it back. **Run Steps 5–7b in ONE Bash
   call** — `$scan_tmp` can't be re-derived across calls, so a split run loses it:
   (command: `SKILL.md` Step 5)

7. Build a global link index (`{target_stem → [source_paths]}`) from wikilinks vault-wide —
   **never `--path`-scoped** (same E9 exception as Step 9): a file in-scope can still be
   linked from outside it.

   ONE dir-shaped call returns the FINISHED index — never drive a `find` loop and never
   call `extract-wikilinks` per file (#614):
   (command: `SKILL.md` Step 7)
   Wikilinks inside code fences or inline code are masked out (#434).

8. Read manifest summary (used for REPORT header) through the filter script — **never `cat` the
   manifest directly** (#468, #460). Uses the `$VAULT_ROOT` from Step 1:
   (command: `SKILL.md` Step 8)
   Exit 0 → `manifest_summary` = parsed `{file_count, generated_at}`; exit 3 → null.
   **Apply `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → Reading the manifest as
   written — that section is the binding contract** for why a raw `cat` is forbidden and the full
   exit-code branch; the line above is a locator, not a summary you may act from alone.

9. Detect E9 vocabulary inconsistency pairs (vault-wide, deterministic — never aggregate tags/keys in the LLM):
   (command: `SKILL.md` Steps 9–10)
   Always vault-wide, unscoped by `--path` (E9 is vault-level). Emits pairs `{sub, a, b, a_files, b_files}` (empty when consistent) straight into CLASSIFY as the E9 source.

10. Rank E5 orphan connection candidates (deterministic, no LLM):
   (command: `SKILL.md` Steps 9–10)
    Vault-wide, unscoped; paths are `$VAULT_ROOT`-relative — join on `rec.path`.

**Outputs**: the scan bundle — `scan_summary` (Step 7b), `manifest_summary` (Step 8, or null),
`vocabulary_pairs[]` (Step 9), `e5_candidates[]` (Step 10). Raw scans stay in `$scan_tmp`, never
in context (#614). Bundle shape and the binding `count`/`omitted`/`unreadable` contract:
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **SCAN output budget** — apply as
written. Report `count`, never the list length; say in the REPORT whenever a list was cut.

**Termination condition**: All scan data collected. Proceed to CLASSIFY.

## Phase 2 — CLASSIFY

Read before CLASSIFY, or when changing classification behavior: SKILL.md keeps only the priority order.

**Purpose**: Apply deterministic rules to the scan bundle and produce a findings list. Zero LLM calls.

**Inputs**: Scan bundle from SCAN.

**Error types** (10: E1–E3, E5–E6, E9–E13 — E4/E7/E8 are retired, never reused).

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
| E12 | `wiki_self_audit` (`wiki_stale` + `wiki_unverified` + `wiki_near_dup`) | Warning | P1 | `scan_summary.errors.E12_stale` / `.E12_unverified` / `.E12_near_dup` | — (display-only) |
| E13 | `custom_schema_violation` | Warning | P1 | `scan_summary.errors.E13` (only with `.vault-schema.json`; `computed: false` → report its `reason`) | — (display-only) |

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
`wiki_near_dup` (E12c) findings additionally carry `"other_path": "relpath"` — copy it straight
from `scan_summary.errors.E12_near_dup[].other_path`, never drop it (REPORT needs both paths of
the pair; see `reference/vault-audit-rules.md` → **Finding shape**).

**Termination condition**: All dirty files classified — Phase 2.5 if `--deep` was passed, else REPORT directly.

## Phase 2.5 — DEEP

**Purpose**: Run every LLM-judgment check gated behind `--deep` — the only phase that reads file bodies or uses LLM judgment; SCAN/CLASSIFY/REPORT stay LLM-cost-0 without it.

**Skip condition**: `--deep` not passed → skip this phase entirely and go to REPORT. This is the default.

**When `--deep` IS passed**: read `${CLAUDE_PLUGIN_ROOT}/reference/audit-deep.md` and apply it as written — full procedure for E12b (#336) and E9c (#167), each with its own prefilter and `AskUserQuestion` confirm gate. Only confirmed pairs become findings.

**Termination condition**: All candidate pairs judged and either confirmed or declined. Proceed to REPORT.

## Phase 3 — REPORT

**Purpose**: Group findings by priority (P0 → P1 → P2) and display a structured triage report in Korean.

**Inputs**: Findings list from CLASSIFY.

**Tools used**: None (output only).

### REPORT Output Contract

Grouped by priority (P0 must-fix → P1 → P2); within each group, sort by severity (Critical→Warning→Info), then error code ascending (unreadable→E1→E2→E3 in P0; E6→E10→E11→E12→E13 in P1; E5→E9 in P2). E9 is vault-level (`path: ""`) — render under a vault-wide heading (e.g. `볼트 전역`), not per-file.

Each finding line: `[E-code/priority/severity] type — N건` header, then one bullet per file (path + one-line description). A finding carrying `other_path` (`wiki_near_dup`/E12c) renders both paths in that one bullet (e.g. `path ↔ other_path`) — no separate bullet for the pair's second file.

Report header: vault state (note count, clean/dirty/untracked), manifest info, recent git activity (omit if none or not a repo).

Footer: auto-fixable count, manual-action count.

If zero findings: output "이슈 없음 — 볼트가 깨끗합니다."

A representative sample of this layout (header, per-priority groups, footer) is in
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` under **REPORT output example**.

> **사용자 확인 게이트는 OPTIONAL-FIX(E2 자동 수정)에만 적용됩니다** — 나머지 타입은 의미적 판단이 필요해 표시만 합니다.

**Termination condition**: Report displayed. Proceed to OPTIONAL-FIX if auto-fixable items exist and the user hasn't opted out; otherwise exit after marking clean.

## Flags

| Flag | Behavior |
|------|----------|
| `--force` | Ignore audit-state; re-audit all vault files |
| `--dry-run` | Run SCAN→CLASSIFY→REPORT but skip OPTIONAL-FIX and mark-clean |
| `--path <dir>` | Scope Steps 5–6 to `$VAULT_ROOT/<dir>` (link index/E9 stay vault-wide) |
| `--reset-state` | Call `audit-state invalidate` on all vault files before scanning |
| `--deep` | Opt-in LLM path (#336/#167): run Phase 2.5 DEEP after CLASSIFY. Off by default. |
| `status` | Bare positional arg (not `--flag`). Skips the pipeline: run `audit-state stats`, render one Korean status line, terminate — no mutation. |
