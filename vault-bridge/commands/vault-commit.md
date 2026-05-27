---
description: Commit uncommitted vault changes to git — shows diff summary, generates a commit message, and requires user approval before committing
allowed-tools: Bash AskUserQuestion
disable-model-invocation: true
---

Commit uncommitted changes in the vault git repository with user approval.

**User language: Korean.** All user-facing output MUST be in Korean.

## Procedure

### Step 0 — Kill switch check

```bash
echo "${VAULT_BRIDGE_DISABLE:-0}"
```

If the value is `1`, output the following and stop:

> vault-bridge가 비활성화되어 있습니다 (`VAULT_BRIDGE_DISABLE=1`). `/vault-commit`을 사용하려면 이 환경변수를 해제해 주세요.

### Step 1 — Determine vault root

```bash
echo "${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}"
```

Use this path as `{vault_root}` for all subsequent steps.

### Step 2 — Verify vault is a git repository

```bash
git -C "{vault_root}" rev-parse --git-dir 2>&1
```

If this fails (non-zero exit), output the following and stop:

> `{vault_root}`은 git 리포지토리가 아닙니다. vault를 git으로 초기화하거나 올바른 vault 경로를 `VAULT_BRIDGE_VAULT_ROOT`에 설정해 주세요.

### Step 3 — Check for uncommitted changes

```bash
git -C "{vault_root}" status --porcelain
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
git -C "{vault_root}" diff --cached --name-status
```

Capture the output as `{diff_output}`.

#### Step 4c — Generate commit message via helper

```bash
python3 vault-bridge/scripts/vault-commit-message.py "{vault_root}" <<'EOF'
{diff_output}
EOF
```

Capture the output as `{auto_msg}`. If the command fails or returns empty output, fall back to `"vault: update notes"`.

### Step 5 — Present summary and ask for approval

Use **AskUserQuestion** to present the change summary and get user approval.

Show the user:
1. The list of changed files (grouped by status: modified / added / deleted / untracked)
2. The auto-generated commit message
3. Three options

**AskUserQuestion options**:

```json
{
  "question": "vault에 미커밋 변경사항이 {N}개 있습니다.\n\n**변경 파일:**\n{file_list}\n\n**자동 생성 커밋 메시지:**\n`{auto_msg}`\n\n어떻게 진행할까요?",
  "options": [
    "이 메시지로 커밋",
    "메시지 직접 입력 후 커밋",
    "커밋 안 함 (건너뛰기)"
  ]
}
```

Where `{file_list}` lists each file on its own line with a status prefix (`수정:`, `추가:`, `삭제:`, `미추적:`).

### Step 6 — Handle user choice

**Option A — "이 메시지로 커밋"** (index 0):

Run:
```bash
git -C "{vault_root}" commit -m "{auto_msg}"
```

**Option B — "메시지 직접 입력 후 커밋"** (index 1):

Do NOT call AskUserQuestion (it does not support freeform text). Instead, output this prompt in Korean and wait for the next user turn:

> 커밋 메시지를 한 줄로 입력해 주세요. (예: `vault: 2026-04-18 session notes`)

On the next turn, treat the user's reply as `{custom_msg}` (single-line, trimmed). If the reply is empty or only whitespace, fall back to the auto-generated message. Then run:
```bash
git -C "{vault_root}" commit -m "{custom_msg}"
```

**Option C — "커밋 안 함 (건너뛰기)"** (index 2):

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

- NEVER run `git commit` without explicit user approval in Step 5.
- Step 4a runs `git add -A` before generating the diff — this is staging-for-preview only. The commit itself requires user approval.
- NEVER leave a partial state: if `commit` fails, report the failure clearly.
- Respect `VAULT_BRIDGE_DISABLE=1` (Step 0).
- Handle git errors gracefully: permission errors, detached HEAD, locked index — report stderr verbatim.
- This command only commits. It does not push. Never run `git push`.
- Do not modify any vault files — only git operations.
- This command is fully independent of `.vault-link` and the vault manifest subsystem.
