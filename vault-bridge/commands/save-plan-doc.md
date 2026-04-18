---
description: Save external plan/design documents from the current project as vault snapshots — supports single file or batch, with 2-layer opt-in gate and dedup protection
allowed-tools: Read, Write, Bash, AskUserQuestion
---

Save one or more external plan/design documents from the current project into the bound vault project as snapshots.

**User language: Korean.** All user-facing output MUST be in Korean.

## Procedure

### Step 0 — Kill switch check

```bash
echo "${VAULT_BRIDGE_DISABLE:-0}"
```

If the value is `1`, output the following and stop:

> vault-bridge가 비활성화되어 있습니다 (`VAULT_BRIDGE_DISABLE=1`). `/save-plan-doc`을 사용하려면 이 환경변수를 해제해 주세요.

### Step 1 — Verify `.vault-link` exists

```bash
[ -f "$PWD/.vault-link" ] && cat "$PWD/.vault-link" || echo "NOT_FOUND"
```

If the output is `NOT_FOUND`, output the following and stop:

> `.vault-link` 파일이 없습니다. 먼저 `/vault-link`를 실행해 이 프로젝트를 vault 프로젝트에 연결해 주세요.

Parse the `.vault-link` content:
- `vault_path`: bound vault project path (e.g. `20_Projects/claude-kit`)
- `auto_capture`: Layer 1 opt-in flag (default: `false` if absent)

### Step 2 — Check 2-layer opt-in gate

#### Layer 1 — `.vault-link` auto_capture

If `auto_capture` is not `true` in `.vault-link`:

Use **AskUserQuestion**:

> **[L1 게이트 미활성]** `.vault-link`에 `auto_capture: true`가 설정되지 않았습니다.
>
> autosync를 활성화하려면 `.vault-link`에 다음을 추가해야 합니다:
> ```yaml
> auto_capture: true
> ```
>
> 어떻게 진행할까요?

Options:
- `auto_capture: true` 추가 후 계속
- 이번만 저장 (gate 우회, 1회성)
- 취소

If the user chooses option A, add `auto_capture: true` to `.vault-link` using Write tool, then continue.
If the user chooses option B, proceed with `--skip-gate-check` flag in Step 4.
If the user chooses option C, stop.

#### Layer 2 — `_index.md` auto_capture

```bash
VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}"
cat "${VAULT_ROOT}/{vault_path}/_index.md" 2>/dev/null | head -30 || echo "NOT_FOUND"
```

If `_index.md` is not found or `auto_capture: true` is not in its frontmatter:

Use **AskUserQuestion**:

> **[L2 게이트 미활성]** vault 프로젝트 `{vault_path}`의 `_index.md`에 `auto_capture: true`가 없습니다.
>
> vault 프로젝트 오너만 이 필드를 관리합니다. obsidian-vault-manager로 `_index.md`를 수정하거나,
> 이번만 저장(gate 우회)할 수 있습니다.
>
> 어떻게 진행할까요?

Options:
- 이번만 저장 (gate 우회, 1회성)
- 취소

If the user chooses option A, proceed with `--skip-gate-check` flag in Step 4.
If the user chooses option B, stop.

If both gates pass (both `auto_capture: true`), proceed without `--skip-gate-check`.

### Step 3 — Discover candidate files

Run the plan-doc-sync detection to find candidate files:

```bash
PROJ_ROOT="$PWD"
found_files=()

# Default include patterns (spec §3.2)
[ -d "$PROJ_ROOT/docs/discussions" ] && find "$PROJ_ROOT/docs/discussions" -name "*.md" 2>/dev/null
[ -d "$PROJ_ROOT/docs/design" ] && find "$PROJ_ROOT/docs/design" -name "*.md" 2>/dev/null
[ -d "$PROJ_ROOT/docs/plans" ] && find "$PROJ_ROOT/docs/plans" -name "*.md" 2>/dev/null
[ -d "$PROJ_ROOT/.omc/plans" ] && find "$PROJ_ROOT/.omc/plans" -maxdepth 1 -name "*.md" 2>/dev/null
[ -f "$PROJ_ROOT/PLAN.md" ] && echo "$PROJ_ROOT/PLAN.md"
[ -f "$PROJ_ROOT/DESIGN.md" ] && echo "$PROJ_ROOT/DESIGN.md"
find "$PROJ_ROOT" -maxdepth 1 -name "RFC-*.md" 2>/dev/null
```

Collect the file list. Filter out:
- Files inside `~/vault/` or any vault path (vault-native boundary)
- `node_modules/`, `dist/`, `build/`, `.git/`, `CHANGELOG.md`, `README.md`

If no candidates found, output and stop:

> 현재 프로젝트에서 저장할 plan/design 문서를 찾지 못했습니다.
> 대상 경로: `docs/discussions/`, `docs/design/`, `docs/plans/`, `.omc/plans/`, `PLAN.md`, `DESIGN.md`, `RFC-*.md`

If the user provided a specific file path as an argument to `/save-plan-doc`, use only that file (skip discovery).

### Step 4 — Present candidates and ask for approval

Use **AskUserQuestion** to show the discovered files and ask which to save:

> vault 프로젝트 `{vault_path}`에 스냅샷으로 저장할 문서를 선택해 주세요.
>
> **발견된 문서 ({N}개):**
> {numbered_file_list}
>
> 저장 방식을 선택하세요:

Options:
- 전체 저장 (모두 {N}개)
- 목록에서 선택 (번호 입력)
- 취소

If the user chooses option B, ask for comma-separated file numbers (e.g. "1,3") in the next turn.

### Step 5 — Run syncer for each selected file

For each selected file, run:

```bash
VAULT_LINK_FLAG=""
# If gate was bypassed in Step 2, add --skip-gate-check
# SKIP_GATE is set to "--skip-gate-check" or ""
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plan-doc-syncer.py" \
  --source "{file_path}" \
  --vault-root "${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}" \
  --vault-link "$PWD/.vault-link" \
  --enforce \
  ${SKIP_GATE_FLAG}
```

Parse the JSON output from each run. Collect results into a summary.

### Step 6 — Report results

Present a summary in Korean:

**Success case:**

> **저장 완료** ({success_count}/{total_count}개)
>
> {per_file_results}
>
> 스냅샷은 vault 프로젝트 `{vault_path}`에 저장되었습니다.
> `source_stale_risk: true`인 파일은 커밋되지 않은 변경사항을 포함할 수 있습니다.

Where `{per_file_results}` lists each file with status:
- `저장됨`: `{source_file}` → `{target_filename}` (commit: `{source_commit}`)
- `중복 건너뜀`: `{source_file}` — 동일 내용이 이미 vault에 있습니다
- `실패`: `{source_file}` — `{error_reason}`

**If vault has uncommitted changes after saving:**

> vault에 미커밋 변경이 생겼습니다. `/vault-commit`으로 커밋할 수 있습니다.

## Rules

- NEVER write to vault without explicit user approval (Step 4 AskUserQuestion).
- NEVER modify source files — only create snapshots in vault.
- NEVER write to paths outside the bound `vault_path` directory.
- Respect `VAULT_BRIDGE_DISABLE=1` (Step 0).
- Atomic writes are handled by the syncer script (`.tmp` → `rename`).
- If `source_stale_risk: true` appears in syncer output, include a stale warning in the report.
- Do not push vault git changes — only write files. Use `/vault-commit` for git.
- Vault-native plan files (`~/vault/20_Projects/*/plan-*.md`) are out of scope — skip silently.
- Maximum one AskUserQuestion per gate layer per invocation. Do not re-ask after user decision.
