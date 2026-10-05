---
name: audit
description: "Audit an Obsidian vault for structural, metadata, link, placement, vocabulary, and wiki freshness/duplication defects; --deep adds semantic checks. Return a triage report and apply only authorized eligible fixes. Use doc-polish for a document's prose/facts and retro for session waste. Examples: '/audit', '/audit --deep'."
allowed-tools: Read Edit Bash AskUserQuestion
---

**User language: Korean.** All user-facing output, including AskUserQuestion prompts, MUST be in Korean.

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Audit `$VAULT_ROOT` structure: `SCAN → CLASSIFY → REPORT → OPTIONAL-FIX (opt-in)`, never collapsed.
Detail: `reference.md`; Phase 4 procedure: `fix.md`.

## Phase 1 — SCAN

1. Resolve `$VAULT_ROOT` — same chain as `ovm-primitives.sh`/`pre-write-guard.sh`:
   ```bash
   VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
   [ -z "$VAULT_ROOT" ] && VAULT_ROOT="$HOME/vault"
   VAULT_ROOT="${VAULT_ROOT/#\~/$HOME}"
   echo "$VAULT_ROOT"
   if [ ! -d "$VAULT_ROOT" ]; then echo "VAULT_ABSENT"
   elif [ ! -d "$VAULT_ROOT/.obsidian" ]; then echo "VAULT_NO_OBSIDIAN"; fi
   ```
   `VAULT_ABSENT` → stop before any scan (#763) and say: "`{vault_root}`에 볼트 디렉토리가 없어요.
   볼트가 다른 곳에 있다면 `VAULT_BRIDGE_VAULT_ROOT` 환경변수나 vault-bridge 플러그인 설정
   `vault_path`로 경로를 지정해 주세요." `VAULT_NO_OBSIDIAN` → warn once that it may not be an
   Obsidian vault (same two settings), then continue.
   `scan_dir` = `$VAULT_ROOT` unscoped, or `$VAULT_ROOT/<subdir>` under `--path <subdir>`.
   `$scan_dir` → Steps 5–6; `$VAULT_ROOT` → everything else.

2. Start metrics (save `token`):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics start "audit"
   ```

3. Dirty file list (untracked = dirty; `status: clean` skipped unless `--force`):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state list-dirty-since
   ```

> **`audit-state` exit 3 applies to EVERY call** — state file unusable, nothing written back. **STOP the audit at
> the first exit 3**, never treat it as empty state; report the sidecar path in Korean (what is preserved, recovery:
> `scripts/README.md` → `audit-state`).

4. Emit a Korean scan-start status line (file count, estimated time). Steps 5–7b write into a fresh
   `$scan_tmp` (never stdout) in ONE Bash call.

5. Frontmatter scan (`--path`-scoped):
   ```bash
   scan_tmp="$(mktemp -d)"
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-frontmatter "$scan_dir" > "$scan_tmp/fm.json"
   ```

6. Filename scan (`--path`-scoped):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" scan-filename "$scan_dir" > "$scan_tmp/fn.json"
   ```

7. Build a global link index (`{target_stem → [source_paths]}`) from wikilinks vault-wide —
   **never `--path`-scoped**; ONE call, never a per-file loop (#614):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" extract-wikilinks-batch "$VAULT_ROOT" > "$scan_tmp/links.json"
   ```

7b. Reduce those three files to the bundle — the ONLY form of them CLASSIFY ever sees:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan-summary.py" \
     --frontmatter "$scan_tmp/fm.json" --filename "$scan_tmp/fn.json" --index "$scan_tmp/links.json" \
     --schema "$VAULT_ROOT/.vault-schema.json"
   ```
   **Never `cat` a raw scan file** (#468, #460). Exit 0 → parse stdout as `scan_summary`.
   Exit 3 (a scan file absent or unparseable) → **STOP the audit**, name the unusable input;
   never fall back to a raw `cat`, never treat it as an empty scan. `omitted: N` → re-run
   Steps 5–7b as ONE new Bash call with a larger `--max-per-type`, into a file, via **Read**.
   Apply `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **SCAN output budget**: report `count`, never the
   list length; say in the REPORT when a list was cut.

8. Read manifest summary (REPORT header) — **never `cat` the manifest** (#468, #460):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-summary.py" "$VAULT_ROOT/.vault-bridge/manifest.json"
   ```
   Exit 0 → `manifest_summary` = `{file_count, generated_at}`; exit 3 → null, never a raw `cat` fallback.
   **Apply `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → Reading the manifest as
   written — the binding contract**; this line is a locator, not a summary to act from alone.

9. Detect E9 vocabulary inconsistency pairs (vault-wide, deterministic — never aggregate tags/keys in the LLM):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" detect-vocabulary "$VAULT_ROOT"
   ```

10. Rank E5 orphan candidates (join on `rec.path`); steps 9–10 are never `--path`-scoped:
    ```bash
    bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" e5-candidates "$VAULT_ROOT/notes"
    ```

## Phase 2 — CLASSIFY

Zero LLM calls, from `scan_summary.errors.<code>`. Priority order: P0 `unreadable`, E1, E2, E3; P1 E6, E10, E11,
E12, E13; P2 E5, E9. Only E2 (`missing_required_fields`) is auto-fixable. An E12c finding also carries `other_path`
(from `E12_near_dup[].other_path`) — never drop it. Read `reference.md` → **Phase 2** for type names, severities,
sources (E13 only with `.vault-schema.json`; `computed: false` → report its `reason`) and finding JSON; rules:
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`.

## Phase 2.5 — DEEP (opt-in, `--deep`)

Not passed → skip. Passed → read `${CLAUDE_PLUGIN_ROOT}/reference/audit-deep.md` and apply it as written
(E12b #336, E9c #167, each with its own `AskUserQuestion` confirm gate); only confirmed pairs become findings.

## Phase 3 — REPORT

Grouped P0 → P1 → P2 in Phase 2's order; E9 is vault-level (`볼트 전역`). Per type `[E-code/priority/severity] type
— N건`, then one bullet per file (E12c: `path ↔ other_path` in ONE bullet). Header: note count,
clean/dirty/untracked, manifest info, git activity (omit if none). Footer: auto-fixable, manual-action counts. Zero
findings: "이슈 없음 — 볼트가 깨끗합니다." Then Phase 4 if auto-fixable items exist; otherwise, unless `--dry-run`, Read `fix.md` and run only its Steps 4–5 (mark-clean, metrics), then exit.

## Phase 4 — OPTIONAL-FIX

OFF by default: only after REPORT, on the user's explicit opt-in, never under `--dry-run`. **On entering Phase 4, before asking anything or any write, Read
`fix.md` in full and follow it**; if unreadable, STOP, apply no fix and tell the user in Korean. Never use Edit on, or
otherwise write, a vault file without the user's approval through the AskUserQuestion gate in `fix.md` Step 1
("수정 실행"). Only E2 is auto-fixable (frontmatter-only), and it requires the provenance gate: ask for the real
origin, never a placeholder. E9, E13 and every other type are display-only, never mutated.

## Flags

- `--force`: re-audit all files. `--reset-state`: `audit-state invalidate` all first.
- `--dry-run`: SCAN→CLASSIFY→REPORT only.
- `--path <dir>`: scope Steps 5–6 only.
- `--deep`: run Phase 2.5 (off by default).
- `status` (bare arg): skip the pipeline; `audit-state stats` → one Korean status line, no mutation.

## Rules

- NEVER call vault-searcher, re-implement frontmatter/filename parsing inline (use `ovm-primitives.sh`), or read
  file bodies during SCAN or CLASSIFY.
- Auto-fix is OFF by default — only after explicit "수정 실행" confirmation. Dry-run never mutates or calls `mark-clean`;
  `audit-state mark-clean` MUST run after every successfully processed file.
- AskUserQuestion in OPTIONAL-FIX is the only user interaction besides Phase 2.5's confirm gates. DEEP never runs
  without `--deep`; every DEEP candidate MUST pass its gate — no silent auto-report.
