---
name: inbox-review
description: "Organize Inbox notes. Shows a batch list and decides move/delete/keep by number selection. Example: '/inbox-review'"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Organize files in `~/vault/00_Inbox/`.

## Procedure

1. **List files**: Get the full file list sorted by date using `ls -1t ~/vault/00_Inbox/`.
   - If no files exist, output "인박스가 비어 있습니다" and exit.
2. **Display all at once**: Show the full list with numbers. Each item includes the filename + a 5-line preview (excluding frontmatter).
   ```
   1. 2025-01-15-api-design.md — API 설계 회의에서 나온 ...
   2. 2025-01-14-todo.md — 이번 주 할 일 목록 ...
   3. 2025-01-13-idea.md — 새로운 기능 아이디어 ...
   ```
3. **Wait for user selection**: Allow the user to specify numbers and actions.
   - Example: "1,3 → Notes로 이동", "2 → 삭제", "나머지 유지"
4. **Handle moves** (when moving to Notes):
   - Determine the domain and move to `30_Notes/{topic}.md`
   - If a file with the same name already exists, ask the user for confirmation
   - Add a backlink to the relevant MOC
5. **Handle deletions**: Ask for final confirmation before deleting.

## Rules

- Show the full batch list first rather than asking one by one (saves conversation turns).
- Allow the user to process multiple items at once.

## Input Grammar

The following user input formats are recognized:

| Format | Example | Interpretation |
|--------|---------|----------------|
| `{number} → Notes` | `1,3 → Notes로 이동` | Move specified items to `30_Notes/` |
| `{number} → 삭제` | `2 → 삭제` | Guide the user to delete manually (vault-file-organizer cannot delete) |
| `{number} → {project}` | `4 → api-project` | Move specified items to `20_Projects/{project}/` |
| `나머지 유지` / `keep rest` | `나머지 유지` | Keep unspecified items in Inbox |
| `전체 이동` / `move all` | `전체 Notes로` | Move all items to `30_Notes/` |

**On unrecognized input**: output "입력을 이해하지 못했습니다. 예: `1,3 → Notes로 이동`" and wait for re-input.
