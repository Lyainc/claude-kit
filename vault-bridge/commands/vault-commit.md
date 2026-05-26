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

### Step 4 — Analyze changes and generate commit message

Parse the porcelain output to determine:

**File type counts** — for each changed file, determine its type using this priority order:
1. Read its frontmatter `type` field if accessible (e.g., `session`, `capture`, `note`, `plan`, `project`)
2. Fall back to filename prefix: files matching `session-*` → `session`, `capture-*` → `capture`, `plan-*` → `plan`, `project-*` or `_index.md` → `project`
3. Files under `notes/*/` that don't match the above → `note`
4. Anything else → `file`

**Project names** — collect unique directory names immediately under `notes/` that contain changed files.

**Auto commit message** — construct using this logic:

- Today's date in `YYYY-MM-DD` format (from `date +%F`)
- If project names were found: `"vault session {date}: {type_summary} in {projects}"`
- Otherwise: `"vault session {date}: {type_summary}"`

Where `{type_summary}` is built from non-zero type counts:
- Single type, single file: `"1 {type}-note"` (e.g., `"1 session-note"`)
- Single type, multiple files: `"{N} {type}s"` (e.g., `"2 plans"`)
- Multiple types: `"{N} {type1}s, {M} {type2}s"` (e.g., `"2 plans, 1 note"`)
- Fallback when type is unclear for all files: `"{total} files"`

Examples:
- `"vault session 2026-04-18: 1 session-note"`
- `"vault session 2026-04-18: 2 plans, 1 note in claude-kit"`
- `"vault session 2026-04-18: 3 files"`

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
git -C "{vault_root}" add -A && git -C "{vault_root}" commit -m "{auto_msg}"
```

**Option B — "메시지 직접 입력 후 커밋"** (index 1):

Do NOT call AskUserQuestion (it does not support freeform text). Instead, output this prompt in Korean and wait for the next user turn:

> 커밋 메시지를 한 줄로 입력해 주세요. (예: `vault: 2026-04-18 session notes`)

On the next turn, treat the user's reply as `{custom_msg}` (single-line, trimmed). If the reply is empty or only whitespace, fall back to the auto-generated message. Then run:
```bash
git -C "{vault_root}" add -A && git -C "{vault_root}" commit -m "{custom_msg}"
```

**Option C — "커밋 안 함 (건너뛰기)"** (index 2):

Output:
> 커밋을 건너뛰었습니다. 변경사항은 그대로 유지됩니다.

Stop. Do not run any git commands.

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

- NEVER run `git add` or `git commit` without explicit user approval in Step 5.
- NEVER leave a partial state: if `git add -A` succeeds but `commit` fails, report the failure clearly.
- Respect `VAULT_BRIDGE_DISABLE=1` (Step 0).
- Handle git errors gracefully: permission errors, detached HEAD, locked index — report stderr verbatim.
- This command only commits. It does not push. Never run `git push`.
- Do not modify any vault files — only git operations.
- This command is fully independent of `.vault-link` and the vault manifest subsystem.
