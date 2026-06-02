---
description: Generate a handoff prompt for the next session — paste-ready one-liner, formatted summary, or saved as resume.md
allowed-tools: Read, Write, Bash, AskUserQuestion
argument-hint: "[--paste|--save|--summary]"
disable-model-invocation: true
---

# /handoff

Generate a continuation handoff for the next session. Summarizes current work state and produces a ready-to-use resume prompt in the format the user chooses.

**User language: Korean.** All user-facing output MUST be in Korean.

---

## Step 0 — Kill switch check

```bash
echo "${VAULT_BRIDGE_DISABLE:-0}"
```

If the value is `1`, output the following and stop:

> vault-bridge가 비활성화되어 있어요 (`VAULT_BRIDGE_DISABLE=1`). `/handoff`를 사용하려면 이 환경변수를 해제해 주세요.

---

## Step 1 — Read project context

Extract the project name only. Do NOT expose or retain the vault path as a variable.

```bash
_vl="${CLAUDE_PROJECT_ROOT:-$PWD}/.vault-link"
if [ -f "$_vl" ]; then
  _vp=$(grep '^vault_path:' "$_vl" 2>/dev/null | head -1 | sed 's/vault_path:[[:space:]]*//')
  PROJECT_NAME="${_vp##*/}"
fi
if [ -z "${PROJECT_NAME:-}" ]; then PROJECT_NAME=$(basename "${CLAUDE_PROJECT_ROOT:-$PWD}"); fi
echo "PROJECT_NAME=$PROJECT_NAME"
```

Use the printed `PROJECT_NAME` value in the handoff output. Discard all other parsed values — the vault path is NOT used in this command.

---

## Step 2 — Summarize current session

Scan the conversation context and build a continuation summary with these fields:

- **작업 주제**: 1-line description of what was being worked on this session
- **현재 상태**: what was completed / what is still in progress
- **다음 단계**: 1–3 specific, actionable items the next session should start with
- **관련 파일**: key files worked on (from conversation context)

If context is sparse, be explicit about uncertainty rather than padding with filler.

---

## Step 3 — Choose delivery method (AskUserQuestion)

> 다음 세션 인수인계 내용을 준비했어요. 어떻게 전달할까요?

Options:
- **복붙 한 줄** — 다음 세션에 붙여넣을 한 줄짜리 프롬프트를 출력해요
- **복붙 요약** — 상세 인수인계 요약을 출력해요 (복붙 용)
- **파일 저장** — `.claude-kit/vault-bridge/resume.md`에 저장해요 — 다음 세션 시작 시 자동 안내돼요

---

## Step 4 — Deliver

### Option A: 복붙 한 줄

Compose a single-line prompt from the session summary:

> `{project_name}` 작업 이어받아줘. {one-line work state}. 다음 단계: {first next step}.

Present as:

> 다음 세션에 아래 한 줄을 붙여넣으세요:
>
> ```
> {one-line prompt}
> ```

---

### Option B: 복붙 요약

Compose a structured markdown summary:

```markdown
## 세션 인수인계 — {YYYY-MM-DD}

**프로젝트**: {project_name}
**작업 주제**: {topic}

### 현재 상태
{work summary — completed items + in-progress items}

### 다음 단계
1. {step 1}
2. {step 2}

### 관련 파일
- {file}: {role}
```

Present as:

> 다음 세션에 아래 내용을 붙여넣으세요:
>
> ````
> {formatted summary}
> ````

---

### Option C: 파일 저장

Build `resume.md`: a **compact one-liner section** followed by the Option B summary body, prefixed with YAML frontmatter:

```markdown
---
created: {YYYY-MM-DD}
type: resume
project: {project_name}
---

## 한 줄 재개 프롬프트

```
{one-line prompt from Option A}
```

{Option B summary body}
```

The `## 한 줄 재개 프롬프트` section is parsed by the SessionStart hook to show a compact resume notification — the one-liner is displayed to the user, the full summary is passed to the model as context only.

Resolve the canonical write destination:

```bash
RESUME_PATH=$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/resolve-resume-path.sh")
```

If this command fails (non-zero exit), stop immediately — output the stderr error to the user and do NOT write to any fallback path.

Use the Write tool with `file_path` set to **exactly** `$RESUME_PATH` (the value echoed by the script above). Do NOT recompute the path or substitute a different destination.

Ensure `.claude-kit/` is gitignored:

```bash
grep -qF '.claude-kit' "${CLAUDE_PROJECT_ROOT:-$PWD}/.gitignore" 2>/dev/null \
  || printf '\n.claude-kit/\n' >> "${CLAUDE_PROJECT_ROOT:-$PWD}/.gitignore"
```

Output:

> 저장 완료: `.claude-kit/vault-bridge/resume.md`
>
> 다음 세션 시작 시 자동으로 인수인계 내용이 안내돼요.

---

## Rules

- `resume.md` MUST be written to the path echoed by `resolve-resume-path.sh` and nowhere else. Never substitute a vault path or any other destination.
- The `.claude-kit/vault-bridge/` directory is ephemeral and gitignored — do not commit it.
- Always generate a continuation summary even if context is sparse; state uncertainty explicitly rather than omitting sections.
- "다음 단계" items must be specific and actionable (e.g., "POST /api/bookings에 세션 검증 추가" not "API 구현").
