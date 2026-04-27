---
description: Create or update a .vault-link pointer file that binds the current code repository to a specific vault project
allowed-tools: Read, Write, Bash, Glob
---

Create a `.vault-link` pointer file in the current working directory (CWD), binding this repository to a specific `~/vault/20_Projects/` project.

**User language: Korean.** All user-facing output MUST be in Korean.

## Procedure

### Step 1 — Check for existing `.vault-link`

```bash
[ -f "$PWD/.vault-link" ] && cat "$PWD/.vault-link"
```

If a `.vault-link` already exists in CWD, read its contents and show them to the user. Then use AskUserQuestion:

> 이미 `.vault-link` 파일이 존재합니다:
> ```
> {current contents}
> ```
> 덮어쓰시겠습니까?
> - **덮어쓰기**: 새 내용으로 교체합니다
> - **취소**: 현재 파일을 유지합니다

If the user chooses 취소, stop without changes.

### Step 2 — Scan available vault projects

```bash
ls -1 ~/vault/20_Projects/ 2>/dev/null
```

Collect the list of subdirectory names under `~/vault/20_Projects/`. Present them to the user as a numbered list.

Use AskUserQuestion:

> `~/vault/20_Projects/` 하위 프로젝트 목록입니다:
>
> 1. {project-a}
> 2. {project-b}
> …
>
> 연결할 프로젝트를 선택하거나 신규 생성을 요청하세요:
> - **번호 입력**: 기존 프로젝트 선택
> - **신규**: OVM `/project` 스킬로 새 프로젝트를 먼저 생성한 뒤 다시 `/vault-link`를 실행하세요
> - **취소**: 중단

If the user selects 신규: output the following message and stop:

> 신규 프로젝트를 생성하려면 `obsidian-vault-manager`의 `/project` 스킬을 먼저 실행하세요.
> 프로젝트 디렉토리가 생성된 후 다시 `/vault-link`를 실행하면 연결할 수 있습니다.

If the user selects 취소: stop without changes.

### Step 3 — Write `.vault-link`

Construct the `vault_path` value as `20_Projects/{selected-project-name}`.

Write the following content to `{CWD}/.vault-link`:

```yaml
version: 1
vault_path: 20_Projects/{selected-project-name}
```

Use the Write tool. Do not overwrite other files.

### Step 4 — Confirm and suggest `.vault-link.local`

After writing, output:

> `.vault-link` 파일을 생성했습니다:
> ```
> vault_path: 20_Projects/{selected-project-name}
> ```
> vault root가 `~/vault/`가 아닌 경우(예: 팀 공유 vault 또는 별도 경로), `.vault-link.local` 파일을 만들어 `vault_root`를 지정할 수 있습니다.
>
> **선택적 `.vault-link.local` 스켈레톤**:
> ```yaml
> vault_root: /Users/{username}/your-vault-path
> ```
>
> `.vault-link.local`은 개인 경로가 담기므로 `.gitignore`에 추가를 권장합니다.

### Step 5 — Offer to append `.vault-link.local` to `.gitignore`

1. Check whether the CWD is inside a git working tree (`git rev-parse --is-inside-work-tree` returns `true`). If not, skip this step.
2. Resolve the project root via `git rev-parse --show-toplevel` and inspect `${root}/.gitignore`. If the file already contains a non-comment line equal to `.vault-link.local`, skip this step (already protected).
3. Otherwise, AskUserQuestion:
   ```
   질문: ".vault-link.local 항목을 .gitignore에 추가할까요?"
   옵션:
     - "추가" (Recommended)
     - "건너뜀"
   ```
4. On "추가":
   - If `.gitignore` does not exist, create it with a single line `.vault-link.local\n`.
   - If it exists, append `.vault-link.local` on a new line (ensure trailing newline before append).
   - Confirm with: `> .gitignore에 .vault-link.local 항목을 추가했습니다.`
5. On "건너뜀": output `> .gitignore는 변경하지 않았습니다. 필요하면 직접 추가해 주세요.` and continue.

## Rules

- Write `.vault-link` to CWD only. Never write to parent directories or inside `~/vault/`.
- `.gitignore` is modified only after explicit user confirmation in Step 5; never write without the AskUserQuestion answer.
- Never auto-call OVM skills or create vault project directories.
- If `~/vault/20_Projects/` does not exist or is empty, inform the user and stop:
  > `~/vault/20_Projects/` 디렉토리가 없거나 비어 있습니다. `obsidian-vault-manager`의 `/project` 스킬로 프로젝트를 먼저 생성해 주세요.
