---
description: Create a session note recording the current session's work — record / quick modes
allowed-tools: Read, Write, Bash, AskUserQuestion
argument-hint: "[--record|--quick]"
---

# /save-session

Create a new vault session note for the current session. The full procedure lives in `vault-bridge/reference/session-note-recipe.md` — this file is the slash-command entry point and contract surface.

**User language: Korean.** All user-facing output MUST be in Korean.

---

## Step 0 — Kill switch check

```bash
echo "${VAULT_BRIDGE_DISABLE:-0}"
```

If the value is `1`, output the following and stop:

> vault-bridge가 비활성화되어 있어요 (`VAULT_BRIDGE_DISABLE=1`). `/save-session`을 사용하려면 이 환경변수를 해제해 주세요.

---

## Step 0.5 — Handoff redirect check

Check whether `$ARGUMENTS` contains any handoff-mode token (case-insensitive):
`handoff`, `continue`, `resume`, `인수인계`, `이어서`, `다음 세션`

If any token matches, output the following and stop:

> `/save-session`은 더 이상 handoff 모드를 지원하지 않아요.
> 대신 `/handoff`를 사용해 주세요 — 복붙 한 줄 / 복붙 요약 / resume.md 저장 중 하나를 선택할 수 있어요.

---

## Step 1 — Load the recipe

Read `vault-bridge/reference/session-note-recipe.md` (resolve relative to `${CLAUDE_PROJECT_ROOT:-$PWD}`; walk upward if not found) and follow its 11-step procedure inline. The recipe is the single source of truth for:

- `.vault-link` discovery + path resolution (recovery, graceful fallback)
- artifact type classification (`session` / `capture` / `plan`) with skim rules
- session mode tier routing (record / quick) — synonym dictionary, Tier 1/2/3 rules, AskUserQuestion prompts
- frontmatter auto-generation
- save path determination (`.vault-link` first, then explicit argument / auto-detect, then Inbox fallback) + path-conflict dialog
- filename pattern `{type}-YYYY-MM-DD[-topic][-vN].md` + collision walk + AskUserQuestion
- record / quick body templates
- related-files gathering (`--hours N` window)
- existing-active-note carry-over logic
- write + structured inline error reporting

---

## Entry contract

When invoked through this slash command:

- `type` defaults to `session` unless `$ARGUMENTS` contains `capture` or `plan` (override).
- For `capture` / `plan`, skip the recipe's mode tier routing (single-format drafting).
- All discrete choices (mode, path conflict, filename collision, save confirmation) MUST use AskUserQuestion. Free-form content (edit instructions) uses plain text response.
- Write tool only — new files only. Never Edit, never overwrite existing vault files.
- On any write failure, report the recipe §11 structured inline error: `kind` ∈ `permission | path_invalid | convention_violation | name_collision | disabled`, plus `path`, `detail`, `suggestion`. Never silently swallow errors.
- `VAULT_BRIDGE_DISABLE=1` always wins — Step 0 short-circuits before the recipe is read.

After a successful save:

> 저장 완료: `{save_dir}/{filename}`
>
> vault에 미커밋 변경이 생겼어요. `/vault-commit`으로 커밋할 수 있어요.

---

## Arguments

| Argument | Description | Default |
|---|---|---|
| `$ARGUMENTS` contains `capture` / `plan` | Override `type` (skips mode tier routing) | `type: session` |
| Mode tokens (`record`, `quick`, `기록`, `간단히`, …) | Tier 1 strong match → pre-select mode (see recipe §2) | Tier 2/3 → AskUserQuestion |
| `--hours N` (integer 1–24) | File-change search window for Related Files | 1 hour |
| `{project-name}` | Link to `~/vault/20_Projects/{name}/` | auto-detect from `.vault-link` |

Mode rules, synonym dictionary, and the full procedure live in the recipe — do not re-implement here.
