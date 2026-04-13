---
name: vault-daily
description: "Create a daily note and integrate previous day review. Example: '/vault-daily', '/vault-daily --review'"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create today's daily note or perform a previous-day review.

## Procedure

### Default mode (`/vault-daily`)

1. **Check date**: Confirm today's date (YYYY-MM-DD)
2. **Check for duplicates**: Check whether `~/vault/00_Inbox/daily-YYYY-MM-DD.md` already exists
   - If it exists: show the existing file contents and ask "이어서 작성할까요?"
3. **Load previous day summary** (automatic):
   - If the previous day's daily note exists, read it and collect incomplete items
   - If a previous day's session note exists (`session-*.md`), reference it
4. **Create daily note**:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [daily]
   type: daily
   ---
   # Daily — YYYY-MM-DD

   ## Carry-over
   {전날 미완료 항목 — 없으면 섹션 생략}

   ## Today's Focus
   - 

   ## Notes
   - 

   ## End of Day
   - [ ] Inbox 정리 완료
   - [ ] 주요 작업 노트 작성 완료
   ```
5. **Output**: Created file path + number of carry-over items from the previous day

### Review mode (`/vault-daily --review`)

1. **Load previous day's daily note**: Read the previous day's `daily-YYYY-MM-DD.md`
   - If not found: output "전날 데일리 노트가 없습니다" and exit
2. **Search for active session notes**: Search for session notes with `status: active` in `~/vault/20_Projects/*/session-*.md`, `~/vault/20_Projects/*/handoff-*.md`, `~/vault/00_Inbox/session-*.md`, and `~/vault/00_Inbox/*-handoff.md`.
   - If active session notes exist: include their "next steps" items as carry-over candidates.
3. **Analyze completion status**:
   - Check whether the `End of Day` checklist was completed
   - Check whether `Today's Focus` items were achieved
4. **Output review summary**:
   ```
   ## Daily Review — YYYY-MM-DD

   ### 완료 상태
   - Today's Focus: {N}/{M} 완료
   - End of Day checklist: {완료/미완료}

   ### 미완료 → Carry-over
   - {item 1}
   - {item 2}

   오늘의 데일리 노트를 생성할까요?
   ```
5. Upon user confirmation, switch to default mode and create a daily note with carry-over items included

## Rules

- Daily notes are created in `00_Inbox/` (no MOC links).
- `--review` targets only the previous day's note.
