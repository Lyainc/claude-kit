---
description: Create a session note recording the current session's work — record / handoff / quick modes
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# /save-session

Create a new vault session note for the current session. Executes the session-note recipe inline in main context (see `reference/session-note-recipe.md`).

**User language: Korean.** All user-facing output MUST be in Korean.

# Procedure mirrored from vault-bridge/reference/session-note-recipe.md

---

## Step 0 — Kill switch check

```bash
echo "${VAULT_BRIDGE_DISABLE:-0}"
```

If the value is `1`, output the following and stop:

> vault-bridge가 비활성화되어 있어요 (`VAULT_BRIDGE_DISABLE=1`). `/save-session`을 사용하려면 이 환경변수를 해제해 주세요.

---

## Step 1 — `.vault-link` Discovery

Run the following shell snippet to walk upward from CWD:

```bash
[ "${VAULT_BRIDGE_DISABLE}" = "1" ] && echo "disabled" && exit 0

dir="${CLAUDE_PROJECT_ROOT:-$PWD}"
while [ "$dir" != "/" ]; do
  if [ -f "$dir/.vault-link" ]; then
    echo "found:$dir/.vault-link"
    [ -f "$dir/.vault-link.local" ] && echo "local:$dir/.vault-link.local"
    break
  fi
  dir="$(dirname "$dir")"
done
```

**Parsing the pointer**:
- Read `.vault-link` as YAML. Required field: `vault_path` (e.g. `20_Projects/claude-kit`). Optional field: `version`.
- If `.vault-link.local` exists at the same level: read `vault_root` field to override default `~/vault/`.
- Default vault root: `${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}`.

**Path resolution failure recovery**:
- Construct `{vault_root}/{vault_path}` and check if the directory exists: `[ -d "{full_path}" ]`.
- If NOT found:
  1. List `{vault_root}/20_Projects/` subdirectories.
  2. Find candidates with edit distance ≤ 2 from `vault_path`'s leaf segment.
  3. If candidates found: use AskUserQuestion to ask which project to use, or proceed with Inbox fallback.
  4. If none: warn "`.vault-link`의 경로를 찾을 수 없어 `00_Inbox/`에 저장합니다." and fall back to Inbox.
- Resolution failure must never halt operation — always fall back gracefully.

---

## Step 2 — Classify artifact type

`/save-session` defaults to `type: session`. Allow override via `$ARGUMENTS`:

- If `$ARGUMENTS` contains `capture` → `type: capture`
- If `$ARGUMENTS` contains `plan` → `type: plan`
- Otherwise → `type: session`

For `capture` and `plan`, skip mode selection (Step 3) and proceed directly to Step 4 with single-format drafting.

---

## Step 3 — Mode tier routing (session type only)

Scan `$ARGUMENTS` and conversation context using the synonym dictionary (case-insensitive, bounded word match):

| mode | EN tokens | KR tokens |
|---|---|---|
| record | record, log, archive | 기록, 정리, 회고 |
| handoff | handoff, continue, resume | 인수인계, 이어서, 다음 세션 |
| quick | quick, brief, summary | 간단히, 짧게, 빠르게, 요약 |

**Tier rules**:

- **Tier 1 (Strong)** — tokens from exactly one row match → pre-select that mode, skip AskUserQuestion, output one-line confirmation `→ {mode} 모드`.
- **Tier 2 (Inferred)** — no token match → AskUserQuestion with default inferred from context (next-step or blocker mentions → handoff; conversation under ~5 turns → quick; else → record).
- **Tier 3 (Ambiguous)** — tokens from two or more rows match → AskUserQuestion with three equal options, no default.

Use **AskUserQuestion** for Tier 2 / Tier 3:

> 어떤 방식으로 세션 노트를 작성할까요?

Options:
- **record** — 작업 기록 — 완료한 작업 중심 요약 (다음 단계 없음)
- **handoff** — 인수인계 — 진행 중 작업 + 다음 단계 + 블로커 포함
- **quick** — 간단히 — Summary + Related Files만 (Next Steps는 handoff-quick에서만 포함)

---

## Step 4 — Determine save path

**Step A — `.vault-link` pointer**:
- `.vault-link` found, path resolves, AND `type ∈ {session, plan}` → `save_dir = {vault_root}/{vault_path}/` (project-scoped). Skip Step B.
- `type = capture` OR no pointer OR resolution failed → Step B.

**Step B — explicit argument or auto-detect**:
- If `$ARGUMENTS` contains a project name, check `~/vault/20_Projects/{name}/` existence.
  - Exists: `save_dir = ~/vault/20_Projects/{name}/`
  - Not found: confirm with user via AskUserQuestion — save to `~/vault/00_Inbox/` instead?
- No project argument: default `save_dir = ~/vault/00_Inbox/`.

**Path conflict** (AskUserQuestion if `.vault-link` path differs from auto-detected path):

> 저장 경로를 선택해 주세요.

Options:
- `.vault-link` 연결 경로 사용: `{vault_path}/`
- 다른 경로 직접 지정
- 취소

---

## Step 5 — Build filename + collision check

Pattern: `{type}-YYYY-MM-DD[-{topic-kebab}][-vN].md`

- `topic-kebab`: lowercase, hyphenated, derived from main subject. Omit for plain session/capture.
- `YYYY-MM-DD`: today's date.
- Collision check via Bash:

```bash
SAVE_DIR="{resolved_save_dir}"
BASE="{type}-YYYY-MM-DD"
CANDIDATE="${BASE}.md"
if [ -f "${SAVE_DIR}/${CANDIDATE}" ]; then
  for i in 2 3 4 5 6 7 8 9; do
    CANDIDATE="${BASE}-v${i}.md"
    [ ! -f "${SAVE_DIR}/${CANDIDATE}" ] && break
    CANDIDATE=""
  done
fi
echo "${CANDIDATE}"
```

- If all `-v2` through `-v9` are taken: report the following error inline and stop:

```
오류 (name_collision):
경로: {save_dir}/{base}.md
내용: {base}.md부터 {base}-v9.md까지 모두 존재해요. 자동 증가를 더 할 수 없어요.
제안: 기존 session 파일 하나를 아카이브하거나 직접 이름을 바꾼 뒤 다시 시도해 주세요.
```

- If `-v2` or higher is needed, use **AskUserQuestion**:

> 오늘 날짜 파일이 이미 있어요. `{filename}`으로 저장할까요?

Options:
- `{filename}-vN.md`로 저장 (제안)
- 취소

---

## Step 6 — Draft body

Use the template for the selected mode. Fill placeholders from conversation context.

### Template: record / handoff

```markdown
---
created: YYYY-MM-DD
tags: [session, {project-or-domain}]
type: session
status: active                 # handoff 모드만 포함; record 모드에서는 이 줄 제거
---
# Session Note — {title} (YYYY-MM-DD)

## Summary
{2-3 line summary}

## Done This Session
- {completed work}

## In Progress                  # handoff 모드만 포함
- [ ] {incomplete work — specify how far it got}

## Blockers / Warnings          # handoff 모드만; 없으면 섹션 전체 제거
- {constraints, issues, dependencies}

## Next Steps                   # handoff 모드만 포함
1. {specific, actionable item}

## Related Files
- [[path/to/file]] — {role/change}

## Reference Context
{background knowledge, decisions, discussion notes}
```

**record 모드**: `status: active`, In Progress, Blockers / Warnings, Next Steps 섹션 모두 제거.

### Template: quick (abbreviated)

```markdown
---
created: YYYY-MM-DD
tags: [session, {project-or-domain}]
type: session
---
# Session Note — {title} (YYYY-MM-DD)

## Summary
{2-3 line summary}

## Next Steps                   # handoff-type quick에서만 포함
1. {actionable item}

## Related Files
- [[path/to/file]] — {role/change}
```

### Frontmatter auto-generation rules

- `created`: today's date (`YYYY-MM-DD`)
- `tags`: `[session, {domain_tags}]` — derive domain tags from conversation topics
- `type: session`
- `status: active` — handoff 모드만 포함; record 모드 및 quick 모드에서는 생략

---

## Step 7 — Gather related files

Collect file paths mentioned in the conversation. Supplement with:

```bash
HOURS="${VAULT_BRIDGE_HOURS:-1}"
find ~/vault -mmin -$((HOURS * 60)) -type f -not -path '*/\.*' 2>/dev/null | head -20
```

- Default: files modified in the last 1 hour (`--hours 1`).
- If `$ARGUMENTS` contains `--hours N` (integer 1–24): use that value. Invalid value → warn "유효하지 않은 --hours 값이에요. 기본값(1시간)을 사용해요." and use 1.

Include gathered paths in the "Related Files" section of the draft.

---

## Step 8 — Check existing active session note

Search for previous `status: active` session notes in the resolved `save_dir` (and `~/vault/00_Inbox/` if project-scoped):

```bash
grep -rl "status: active" "{save_dir}" --include="session-*.md" 2>/dev/null
grep -rl "status: active" "${VAULT_BRIDGE_VAULT_ROOT:-$HOME/vault}/00_Inbox" --include="session-*.md" 2>/dev/null
```

If found:
- Cross-reference any "Next Steps" with what was accomplished this session. Carry over incomplete items into the new note's "In Progress" section (handoff mode) or note them in Reference Context.
- Inform the user: "이전 active session note(`{filename}`)가 있어요. 완료된 다음 단계가 있으면 반영했어요. 이전 파일을 archived로 변경하려면 OVM의 `/archive` 커맨드를 사용하거나 직접 수정해 주세요."

---

## Step 9 — Show draft preview

Output the full assembled draft so the user can review it before saving.

---

## Step 10 — Save confirmation

Use **AskUserQuestion**:

> 이 내용으로 저장할까요?
>
> 저장 경로: `{save_dir}/{filename}`

Options:
- 저장 — 그대로 저장해요.
- 수정 후 저장 — 수정 내용을 알려주시면 반영한 뒤 저장해요.
- 취소 — 저장하지 않고 종료해요.

If "수정 후 저장" is chosen: incorporate user feedback, update the draft, and re-show Step 9 → Step 10.

---

## Step 11 — Write

Write the file using the Write tool (new file only — never Edit, never overwrite):

```
Write tool: path = {save_dir}/{filename}, content = {draft}
```

On success, report:

> 저장 완료: `{save_dir}/{filename}`
>
> vault에 미커밋 변경이 생겼어요. `/vault-commit`으로 커밋할 수 있어요.

On write failure, report the error inline to the user:

```
오류 ({kind}):
경로: {attempted_path}
내용: {human-readable explanation}
제안: {alternative action}
```

Where `kind` is one of: `permission` | `path_invalid` | `convention_violation` | `name_collision` | `disabled`.

---

## Rules

- NEVER write to vault without explicit user confirmation (Step 10 AskUserQuestion). Never auto-save.
- Write tool only — new files only. Never use Edit. Never overwrite or modify existing vault files.
- All discrete choices (mode, path conflict, collision, save confirmation) MUST use AskUserQuestion. Free-form content (edit instructions) uses plain text response.
- "Next Steps" must be specific and actionable (e.g., "Add session validation to POST /api/bookings" — not "Implement API").
- Omit Blockers/Warnings section entirely if none exist.
- In `record` mode: omit `status: active` from frontmatter; omit In Progress, Blockers/Warnings, Next Steps sections.
- In `quick` mode: only Summary + Related Files (+ Next Steps if handoff-type quick).
- On any write failure: report structured inline error. Never silently swallow errors.
- `VAULT_BRIDGE_DISABLE=1` always wins — check at Step 0 before any other action.
