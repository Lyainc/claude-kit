---
name: archive
description: "Archive a project and clean up related MOC/Home.md. Example: '/archive api-gateway'"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Archive the `$ARGUMENTS` project.

## Procedure

1. **Verify project**: Check whether the `~/vault/20_Projects/$ARGUMENTS/` directory exists.
   - If not found: output "프로젝트를 찾을 수 없습니다: $ARGUMENTS" and exit.
   - Check the `status` frontmatter of `_index.md`. (Required format: `status: active|completed|archived`. If missing, warn and treat as `active`.)
2. **Check status**: Verify the current status (`active` or `completed`).
   - If `archived`: output "이미 아카이브된 프로젝트입니다" and exit.
   - If `active` or `completed`: continue with the procedure.
3. **Present archive plan**: Show the archive plan to the user and ask for confirmation:
   ```
   ## 아카이브 계획 — {project-name}

   1. 20_Projects/{name}/ → 50_Archive/{name}/ 이동
   2. _index.md status: active → archived 변경
   3. Home.md "Active Projects"에서 링크 제거
   4. 관련 30_Notes/ 노트의 MOC 링크는 유지 (노트 이동 없음)

   진행할까요?
   ```
4. **Execute** (after user confirmation):
   a. Update `status` in `_index.md` to `archived` and add an `archived` date.
      - Optional CLI path: follow the availability gate and timeout helper in `../../reference/obsidian-cli.md`. When the gate passes, run `${OBSIDIAN_TO:+$OBSIDIAN_TO 5} obsidian property:set name="status" value="archived" path="20_Projects/{name}/_index.md"` and `${OBSIDIAN_TO:+$OBSIDIAN_TO 5} obsidian property:set name="archived" value="YYYY-MM-DD" type=date path="20_Projects/{name}/_index.md"` before moving the project. The `type=date` parameter is required so Obsidian Properties and Dataview treat `archived` as a date, not text. (Never hard-code bare `timeout` — it is missing on default macOS.)
      - Fallback path: if either CLI command is unavailable, fails, or times out, update YAML frontmatter directly with Edit as before.
   b. Delegate file move to the `vault-file-organizer` agent: `20_Projects/{name}/` → `50_Archive/{name}/` (error handling follows the file-organizer's Error Handling policy).
   c. Remove the corresponding link from the "Active Projects" section in `Home.md`.
   d. Search related MOCs: use `grep -rl "{project-name}" ~/vault/10_MOC/` to find MOCs that reference the project, and append `(archived)` to those links (use `grep` even on macOS — `mdfind` is only for full-vault searches).
5. **Output result**:
   ```
   ✓ 아카이브 완료: {project-name}
     - 이동: 50_Archive/{name}/
     - Home.md 업데이트 완료
     - 관련 노트 MOC 링크 유지됨
   ```

## Status Lifecycle

```
active → completed → archived
```

- `active`: project in progress
- `completed`: work finished, still active in the vault
- `archived`: moved to `50_Archive/`

`/archive` transitions a project in `active` or `completed` status to `archived`.

## Rules

- Always obtain user confirmation before archiving.
- Do not move notes in `30_Notes/` — only preserve MOC links.
