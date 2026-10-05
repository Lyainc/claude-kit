---
name: vault-commit
description: "Commit uncommitted vault changes to git — shows a diff summary, generates a commit message, and requires user approval before committing. Invoke via /vault-commit."
allowed-tools: Bash AskUserQuestion Read
---

Commit uncommitted changes in the vault git repository with user approval.

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

**User language: Korean.** All user-facing output MUST be in Korean.

## Procedure

### Step 0 — Kill switch check

```bash
echo "${VAULT_BRIDGE_DISABLE:-0}"
```

If the value is `1`, output the following and stop:

> vault-bridge가 비활성화되어 있습니다 (`VAULT_BRIDGE_DISABLE=1`). `/vault-commit`을 사용하려면 이 환경변수를 해제해 주세요.

### Step 1 — Determine vault root

Resolve in priority order — `VAULT_BRIDGE_VAULT_ROOT` (env override) > `VAULT_BRIDGE_VAULT_PATH`
(userConfig) > `~/vault` (default), same chain as `hooks/pre-write-guard.sh`:

```bash
_vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
[ -z "$_vr" ] && _vr="$HOME/vault"
_vr="${_vr/#\~/$HOME}"
echo "$_vr"
if [ ! -d "$_vr" ]; then echo "VAULT_ABSENT"
elif [ ! -d "$_vr/.obsidian" ]; then echo "VAULT_NO_OBSIDIAN"; fi
```

Use the first line as `{vault_root}` for all subsequent steps. Then (#763):

- `VAULT_ABSENT` → output the following and stop:

  > `{vault_root}`에 볼트 디렉토리가 없습니다. 볼트가 다른 곳에 있다면 `VAULT_BRIDGE_VAULT_ROOT` 환경변수나 플러그인 설정 `vault_path`로 경로를 지정해 주세요.

- `VAULT_NO_OBSIDIAN` → warn once and continue:

  > `{vault_root}`에 `.obsidian/`이 없어 Obsidian 볼트가 아닐 수 있습니다. 다른 경로라면 `VAULT_BRIDGE_VAULT_ROOT` 환경변수나 플러그인 설정 `vault_path`로 지정해 주세요.

### Step 2 — Verify vault is a git repository

```bash
git -C "{vault_root}" rev-parse --git-dir 2>&1
```

If this fails (non-zero exit), output the following and stop:

> `{vault_root}`은 git 리포지토리가 아닙니다. vault를 git으로 초기화하거나 올바른 vault 경로를 `VAULT_BRIDGE_VAULT_ROOT`에 설정해 주세요.

### Step 3 — Check for uncommitted changes

```bash
git -C "{vault_root}" -c core.quotepath=false status --porcelain
```

If the output is empty, output the following and stop:

> 커밋할 변경사항이 없습니다. vault가 이미 최신 상태입니다.

Collect the full list of changed files from the porcelain output.

### Step 4 — Stage all changes and generate commit message

#### Step 4a — Stage all changes

```bash
git -C "{vault_root}" add -A
```

#### Step 4b — Get staged diff for message generation

```bash
git -C "{vault_root}" -c core.quotepath=false diff --cached --name-status
```

Capture the output as `{diff_output}`.

#### Step 4c — Generate commit message via helper

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit-message.py" "{vault_root}" <<'EOF'
{diff_output}
EOF
```

Capture the output as `{auto_msg}`. If the command fails or returns empty output, fall back to `"vault: update notes"`.

### Step 5 — Present summary and ask for approval

Use **AskUserQuestion** to present the change summary and get user approval.

Show the changed files (grouped by status), the auto-generated message, and four options. Run the commit and git commands with Bash.

**AskUserQuestion options**:

```json
{
  "question": "vault에 미커밋 변경사항이 {N}개 있습니다.\n\n**변경 파일:**\n{file_list}\n\n**자동 생성 커밋 메시지:**\n`{auto_msg}`\n\n어떻게 진행할까요?",
  "options": [
    "이 메시지로 커밋",
    "그룹별로 나눠서 커밋",
    "메시지 직접 입력 후 커밋",
    "커밋 안 함 (건너뛰기)"
  ]
}
```

`{file_list}`: one file per line with a status prefix (`수정:`, `추가:`, `삭제:`, `미추적:`).

When `{N}` ≥ 10, list per-path-group counts above the file list (`wiki/ 23 · notes/ 2 · 기타 1`) so the approval is a real one; see `reference.md` §Step 5.

### Step 6 — Handle user choice

**Option A — "이 메시지로 커밋"** (index 0):

```bash
git -C "{vault_root}" commit -m "{auto_msg}"
```

**Option B — "그룹별로 나눠서 커밋"** (index 1):

Split the staged changes into one commit per path group. Before step 1, read `reference.md` §Step 6 Option B — it defines the grouping (first path segment only, never content), the `기타` group for top-level files (pathspec = its explicit quoted member paths, never the label), and the exact per-group `add` forms.

1. **Read the groups off the still-staged set first**, before anything un-stages it:
   ```bash
   git -C "{vault_root}" -c core.quotepath=false diff --cached --name-only
   ```
   Group each path by its first segment; paths with no `/` are `기타` members (record them verbatim).
2. Un-stage everything Step 4a staged:
   ```bash
   git -C "{vault_root}" reset HEAD
   ```
3. For each group in step 1 order, stage only that group (`add -A -- {group_pathspec}`), generate its message with the Step 4c helper from `-c core.quotepath=false diff --cached --name-status`, then `reset HEAD`. Collect `{group} → {group_msg}`. Do not commit yet.
4. Show the full plan (every group, its file count, and its message) and get **one** confirmation covering all of them. The approval must name each message — "커밋해줘" without the messages displayed does not authorize them.
5. On approval, run per group: `add -A -- {group_pathspec}` then `commit -m "{group_msg}"`.
6. Report every commit hash in Step 7, one line each.

If any group's commit fails, **stop** — do not continue. Report which groups committed and which did not.

**Option C — "메시지 직접 입력 후 커밋"** (index 2):

Do NOT call AskUserQuestion (it does not support freeform text). Instead, output this prompt in Korean and wait for the next user turn:

> 커밋 메시지를 한 줄로 입력해 주세요. (예: `vault: 2026-04-18 session notes`)

On the next turn, treat the user's reply as `{custom_msg}` (single-line, trimmed). If the reply is empty or only whitespace, fall back to the auto-generated message. Then run:
```bash
git -C "{vault_root}" commit -m "{custom_msg}"
```

**Option D — "커밋 안 함 (건너뛰기)"** (index 3):

Un-stage the changes that Step 4a staged for preview:
```bash
git -C "{vault_root}" reset HEAD
```

Output:
> 커밋을 건너뛰었습니다. Step 4a에서 스테이징한 변경사항은 해제됐어요. 작업 트리는 그대로 유지됩니다.

Stop. Do not run any other git commands.

### Step 7 — Report result

**On success (exit 0)**:

Capture the short commit hash:
```bash
git -C "{vault_root}" rev-parse --short HEAD
```

Output:
> ✓ 커밋됨: `{hash}` — {used_msg}

**On failure (non-zero exit)**:

Output the stderr content and:
> 커밋에 실패했습니다. 위 오류 내용을 확인하고 수동으로 처리해 주세요.

## Rules

- NEVER run `git commit` without explicit user approval in Step 5 (Step 4a's `git add -A` is staging-for-preview only).
- **Grouping is by path prefix only** (Option B). Do not filter derived/generated files; the vault's `.gitignore` owns exclusions (`reference.md` §Rules).
- If interrupted after Step 4a before Step 6 cleanup, restore with `git -C {vault_root} reset HEAD`.
- NEVER leave a partial state: if `commit` fails, report the failure clearly. Handle git errors (permissions, detached HEAD, locked index) by reporting stderr verbatim.
- Respect `VAULT_BRIDGE_DISABLE=1` (Step 0).
- This command only commits. Never run `git push`. Do not modify any vault files — only git operations.
