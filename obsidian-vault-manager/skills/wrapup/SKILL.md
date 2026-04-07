---
name: wrapup
description: "Summarize session work and save a session wrapup note to Inbox. Example: '/wrapup', '/wrapup --hours 3'"
allowed-tools: Read Write Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Summarize the files created or modified during the current session.

## Procedure

1. **Track file changes**: Compile a list of files created or modified during the session.
   - Collect file paths created or modified in this session from the conversation context.
   - If no record exists in the context, find recently changed files with `find ~/vault -mmin -{minutes} -type f -not -path '*/\.*'`. (`{minutes}` = `--hours N` value × 60, default: 60 minutes)
2. **Generate summary**: Summarize the core session content in 3 lines or fewer.
3. **Offer to save**: Ask the user whether to save as `00_Inbox/YYYY-MM-DD-session-wrapup.md`.
   - If the `--no-save` option is present, skip this step and only output the summary.
4. **Save format**:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [session-wrapup]
   ---
   # Session Wrapup — YYYY-MM-DD

   ## 요약
   {3줄 요약}

   ## 생성/수정된 파일
   - [[path/to/file1]]
   - [[path/to/file2]]
   ```

## Rules

- If a `00_Inbox/YYYY-MM-DD-daily.md` exists for today: suggest to the user whether to append the wrapup summary to the `## Notes` section of the daily note.
- After saving the wrapup, if there is work to continue in the next session: inform the user — "handoff 노트도 생성할까요? (vault-reader 플러그인의 vault-searcher 에이전트를 사용합니다)".

## Metrics

Include work metrics in addition to the file list when saving:

```markdown
## Metrics
- 생성: {N}개 파일
- 수정: {N}개 파일
- 이동: {N}개 파일
- 삭제: {N}개 파일
- MOC 업데이트: {N}건
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--hours N` | File change search range (positive integer, min 1, max 24. Out of range / non-numeric → output warning "유효하지 않은 값입니다. 기본값(1시간)을 사용합니다" and use default) | 1 hour (60 minutes) |
| `--no-save` | Output summary only, do not save file | false |
