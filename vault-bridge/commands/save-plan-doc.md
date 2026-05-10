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

> vault-bridge가 비활성화되어 있어요 (`VAULT_BRIDGE_DISABLE=1`). `/save-plan-doc`을 사용하려면 이 환경변수를 해제해 주세요.

### Step 1 — Verify `.vault-link` exists

```bash
[ -f "$PWD/.vault-link" ] && cat "$PWD/.vault-link" || echo "NOT_FOUND"
```

If the output is `NOT_FOUND`, output the following and stop:

> `.vault-link` 파일이 없어요. 먼저 `/vault-link`를 실행해 이 프로젝트를 vault 프로젝트에 연결해 주세요.

Parse the `.vault-link` content:
- `vault_path`: bound vault project path (e.g. `20_Projects/claude-kit`)
- `snapshot_export`: Layer 1 opt-in flag (default: `false` if absent). `auto_capture` is honored as a 4-week deprecation alias — the syncer emits a stderr warning when only the alias is present.

### Step 1.7 — Pre-discover for impact preview

Run `--discover --summary` once before the gate prompt so AskUserQuestion can show the candidate count and the category breakdown when noise is high:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plan-doc-syncer.py" \
  --discover "$PWD" \
  --vault-link "$PWD/.vault-link" \
  --summary 2>/tmp/save-plan-doc-summary-$$.json
```

Read the candidate list from stdout and the optional category-breakdown JSON from stderr (`/tmp/save-plan-doc-summary-$$.json`). If candidate count >= `VAULT_BRIDGE_DISCOVER_WARN_THRESHOLD` (default 10), the JSON contains `{"count": N, "threshold": T, "categories": {...}}`. Hold these values for Step 2's L1 message body and Step 4's candidate list.

If the user provided a specific file path as an argument to `/save-plan-doc`, skip discovery and use that single file (also skip the category breakdown).

### Step 2 — Check 2-layer opt-in gate

#### Layer 1 — `.vault-link` snapshot_export

If `snapshot_export` (or alias `auto_capture`) is not `true` in `.vault-link`:

Use **AskUserQuestion**:

> 이 프로젝트의 plan/design 파일을 vault에 스냅샷으로 저장하려고 해요.
>
> **발견된 후보 ({N}개){threshold_warning}:**
> {category_summary_or_first_5}
>
> 각 파일은 `~/vault/{vault_path}/` 아래에 frontmatter가 추가된 새 파일로 박제되며 원본은 수정되지 않아요.
>
> 이 프로젝트의 vault 내보내기 권한(`.vault-link`의 `snapshot_export`)이 켜져 있지 않아요. 어떻게 진행할까요?

`{threshold_warning}`: count >= threshold일 때 ` — 후보가 많아요. 카테고리 분포 참고`. 아니면 빈 문자열.
`{category_summary_or_first_5}`: count >= threshold일 때 카테고리 분포 (예: `docs/discussions/...: 60개\ndocs/design/: 5개`). 미만이면 처음 5개 파일 경로.

Options:
- `snapshot_export: true` 추가 후 계속 — 이후 모든 호출이 통과해요. SessionEnd 안내가 활성화돼요. 되돌리려면 `.vault-link`에서 해당 줄을 지우면 돼요.
- 이번만 저장 (1회 우회) — 이번 호출 한정. `.vault-link`는 변경되지 않아요.
- 취소 — 저장하지 않고 종료해요.

If the user chooses option A, add `snapshot_export: true` to `.vault-link` using Write tool, then continue.
If the user chooses option B, proceed with `--skip-gate-check` flag in Step 5.
If the user chooses option C, stop.

#### Layer 2 — `_index.md` snapshot_import

```bash
VAULT_ROOT="${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}"
cat "${VAULT_ROOT}/{vault_path}/_index.md" 2>/dev/null | head -30 || echo "NOT_FOUND"
```

If `_index.md` is not found or `snapshot_import: true` (or alias `auto_capture: true`) is not in its frontmatter:

Use **AskUserQuestion**:

> 캡처 대상 vault 프로젝트(`{vault_path}/_index.md`)가 외부 스냅샷 수신 권한(`snapshot_import`)을 켜지 않았어요.
>
> 이 권한은 vault 오너만 변경할 수 있어요. 본인이 vault 오너라면 다음 명령으로 켤 수 있어요:
>
> ```
> /project {project_name} --enrich auto_capture=true
> ```
>
> (vault 오너가 아닌 경우 우회 저장한 스냅샷은 vault 오너 정책에 따라 나중에 정리될 수 있어요.)

Options:
- 이번만 저장 (1회 우회) — 이번 호출 한정. 이후 호출은 다시 차단돼요.
- 취소 — 저장하지 않고 종료해요.

L2에는 "권한 켜고 계속" 옵션이 없어요 — vault-bridge는 `_index.md`에 write 권한이 없어요. OVM 트랙으로만 변경 가능해요.

If the user chooses option A, proceed with `--skip-gate-check` flag in Step 5.
If the user chooses option B, stop.

If both gates pass (both `snapshot_export` and `snapshot_import` true, or via alias), proceed without `--skip-gate-check`.

### Step 3 — Use Step 1.7's discovery result

The candidate list and optional category breakdown are already in memory from Step 1.7 — do not re-run `--discover`. If no candidates were found there, output and stop:

> 현재 프로젝트에서 저장할 plan/design 문서를 찾지 못했어요.
> 대상 경로: `docs/discussions/`, `docs/design/`, `docs/plans/`, `.omc/plans/`, `PLAN.md`, `DESIGN.md`, `RFC-*.md`

### Step 4 — Present candidates and ask for approval

Use **AskUserQuestion** to show the discovered files and ask which to save:

> vault 프로젝트 `{vault_path}`에 스냅샷으로 저장할 문서를 선택해 주세요.
>
> **발견된 문서 ({N}개){threshold_warning}:**
> {numbered_file_list_or_category_summary}
>
> 저장 방식을 선택하세요:

If count >= threshold, prefer the category summary (from Step 1.7) over the full numbered list to keep the prompt readable. Offer "전체 저장" / "최근 N시간만 (--recent)" / "목록에서 선택" / "취소" in that case.

Options (default):
- 전체 저장 (모두 {N}개)
- 목록에서 선택 (번호 입력)
- 취소

Optional 4th option when count >= threshold:
- 최근 24시간만 ({M}개) — 이 옵션 선택 시 Step 1.7을 `--recent 24`로 재실행하여 후보 좁힘.

If the user chooses "목록에서 선택", ask for comma-separated file numbers (e.g. "1,3") in the next turn.

### Step 5 — Run syncer for each selected file

For each selected file, run:

```bash
# SKIP_GATE_FLAG is set in Step 2: "--skip-gate-check" if user chose "이번만 저장", else ""
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
> 스냅샷은 vault 프로젝트 `{vault_path}`에 저장됐어요.
> `source_stale_risk: true`인 파일은 커밋되지 않은 변경사항을 포함할 수 있어요.

Where `{per_file_results}` lists each file with status:
- `저장됨`: `{source_file}` → `{target_filename}` (commit: `{source_commit}`)
- `중복 건너뜀`: `{source_file}` — 동일 내용이 이미 vault에 있어요
- `실패`: `{source_file}` — `{error_reason}`

**If vault has uncommitted changes after saving:**

> vault에 미커밋 변경이 생겼어요. `/vault-commit`으로 커밋할 수 있어요.

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
- `auto_capture` (`.vault-link` and `_index.md`) is a 4-week deprecation alias for `snapshot_export` / `snapshot_import`. New configurations should use the new keys.
