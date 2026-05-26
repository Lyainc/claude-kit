# Vault Write Recipe — Session Note, Capture, Plan

Detailed procedure executed inline by the `/save-session` slash command (main context). Originally housed in `vault-searcher` Mode 4 — moved here when vault writes were narrowed to user-initiated slash commands only (2026-05-12).

The entry point is [`../commands/save-session.md`](../commands/save-session.md); the full procedure, templates, and rules live here.

**Scope**: artifact types `session` (with two modes: record / quick), `capture`, `plan`.

**User language**: All user-facing output (AskUserQuestion labels, draft content, error suggestions) MUST be in Korean.

## Procedure

### 1. Skim and classify (rule-based, no user prompt needed)

Scan the input context to determine artifact `type`:

- **session** — recording current session work (what was done / what's next)
- **capture** — quick note, snippet, or reference captured mid-session
- **plan** — forward-looking plan document for a workstream or feature

### 2. Select mode (Tier routing — `session` type only)

For `type: session`, route to one of two modes via the synonym dictionary. For `capture` / `plan`, skip mode selection (single format).

**Synonym dictionary** (case-insensitive, bounded — 4–5 tokens per row):

| mode | EN tokens | KR tokens |
|---|---|---|
| record | record, log, archive | 기록, 정리, 회고 |
| quick | quick, brief, summary | 간단히, 짧게, 빠르게, 요약 |

**Tier rules**:

- **Tier 1 (Strong)** — trigger matches tokens from exactly one row → pre-select that mode, skip AskUserQuestion, output one-line confirmation `→ {mode} 모드`.
- **Tier 2 (Inferred)** — no token match → AskUserQuestion with default inferred from context (conversation under ~5 turns → quick; else → record).
- **Tier 3 (Ambiguous)** — tokens from both rows match → AskUserQuestion with two equal options, no default.

Mode descriptions for AskUserQuestion (Tier 2/3):

- **record** — 작업 기록 — past-focused summary only
- **quick** — 간단히 — minimal summary (Summary + Related Files)

### 3. Generate frontmatter (rule-based)

Auto-generate frontmatter before drafting body:

- `created: YYYY-MM-DD` (today's date)
- `tags: [{type}, ...domain_tags]` (derive domain tags from conversation context)
- `type: {classified}` (session / capture / plan)
- `status: active` — required for `plan`; omit for `session` and `capture`

### 4. Determine save path

- **Step A — `.vault-link` pointer** (run Discovery Protocol first):
  - `.vault-link` found, path resolves, AND `type ∈ {session, plan}` → `save_dir = {vault_root}/{vault_path}/` (project-scoped). Skip Step B.
  - `type = capture` OR no pointer OR resolution failed → Step B.
- **Step B — explicit argument or auto-detect**:
  - If `$ARGUMENTS` contains a project name, check `~/vault/notes/{name}/` existence.
    - Exists: `save_dir = ~/vault/notes/{name}/`
    - Not found: confirm with user to save to Inbox (`save_dir = ~/vault/inbox/`)
  - No arguments: auto-detect from session topics. Default to `~/vault/inbox/`.
- **Path conflict** (AskUserQuestion if `.vault-link` path differs from auto-detected):
  - Option A: use suggested path
  - Option B: specify a different path
  - Option C: cancel

### 5. Build filename

Pattern: `{type}-YYYY-MM-DD[-{topic-kebab}][-vN].md`

- `topic-kebab`: lowercase, hyphenated, derived from main subject (omit for plain session/capture)
- Collision check: if base name exists, try `-v2`, `-v3`, … up to `-v9`.
- If all suffixes taken: report a `name_collision` error inline and stop.
- **Collision AskUserQuestion** (when `-v2` or higher is needed):
  - Option A: create `{filename}-vN.md` as proposed
  - Option B: cancel

### 6. Draft content

Use the templates below. For captures and plans, use a minimal freeform structure appropriate to the content type.

### 7. Gather related files

Collect file paths mentioned in conversation. Supplement with `find ~/vault -mmin -{hours × 60} -type f -not -path '*/\.*'` if insufficient (default: `--hours 1` = 60min).

### 8. Check existing session note (`session` type only)

Search for previous `status: active` session note in the same project/domain.

- Search pattern: `session-*.md`.
- If found: cross-reference "next steps" with current session work. Carry over incomplete items.
- Suggest to user: "이전 active session note를 archived로 변경할까요?" (/save-session는 기존 파일을 수정할 수 없으므로, 사용자에게 직접 변경하거나 obsidian-vault-manager의 vault-file-organizer에게 위임할지 안내).

### 9. Show draft

Show the assembled draft to user for confirmation before saving.

### 10. Save confirmation (AskUserQuestion)

Ask: "이 내용으로 저장할까요?"

- **저장** — save as-is
- **수정 후 저장** — incorporate user feedback, then save
- **취소** — discard without saving

### 11. Write

- Write to `{save_dir}/{filename}` using Write tool (new file only — never Edit).
- On write failure, report the error inline to the user in this structured form: `kind` (permission/path_invalid/convention_violation/name_collision/disabled), `path`, `detail`, `suggestion`. Never silently swallow.

## Templates

### Session note — record

```markdown
---
created: YYYY-MM-DD
tags: [session, {project-or-domain}]
type: session
---
# Session Note — {title} (YYYY-MM-DD)

## Summary
{2-3 line summary}

## Done This Session
- {completed work}

## Related Files
- [[path/to/file]] — {role/change}

## Reference Context
{background knowledge, decisions, discussion notes}
```

### Session note — quick (abbreviated)

```markdown
---
created: YYYY-MM-DD
tags: [session, {project-or-domain}]
type: session
---
# Session Note — {title} (YYYY-MM-DD)

## Summary
{2-3 line summary}

## Related Files
- [[path/to/file]] — {role/change}
```

## Rules

- Confirm with user before saving (AskUserQuestion). Never auto-save.
- All discrete choices (mode, path, filename collision, save confirmation) MUST use AskUserQuestion. Free-form content (edit instructions, extra sections) uses plain text.
- Ask user for supplementary info if conversation context is insufficient.
- Omit the `status` field from frontmatter (record and quick modes do not use it).
- On any write failure, report the error inline to the user in this structured form: `kind` (permission/path_invalid/convention_violation/name_collision/disabled), `path`, `detail`, `suggestion`. Never silently swallow errors.

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `{project-name}` | Link to project (`notes/` subdirectory) | auto-detect |
| `--quick` | Brief version (Summary + Related Files) | false |
| `--hours N` | File change search range (integer 1-24, invalid → warning + default) | 1 hour |
