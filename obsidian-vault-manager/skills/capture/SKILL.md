---
name: capture
description: "Quick memo capture. Saves immediately to Inbox and outputs file path only. Example: '/capture API changes from today's meeting'"
allowed-tools: Read Write Bash
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Immediately save the content of `$ARGUMENTS` to `~/vault/00_Inbox/`.

## Rules

1. Filename: `YYYY-MM-DD-{2-3 word topic summary in kebab-case}.md`
2. frontmatter:
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [inbox]
   ---
   ```
3. Write the content of `$ARGUMENTS` in the body.
4. **Directory validation**: If `~/vault/00_Inbox/` does not exist, create it automatically (`mkdir -p`).
5. **Duplicate detection**: If a file with the same date and topic already exists, append `-v2`, `-v3`, etc. to the filename.
6. **Save immediately without confirmation.** This is the core behavior of this skill.
7. Output only the saved file path. No follow-up questions.
