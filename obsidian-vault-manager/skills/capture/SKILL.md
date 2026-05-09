---
name: capture
description: "Quick memo capture. Saves immediately to Inbox and outputs file path only. Example: '/capture API changes from today's meeting'"
allowed-tools: Read Write Bash
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Immediately save the content of `$ARGUMENTS` to `~/vault/00_Inbox/`.

## Rules

Before writing the note body or frontmatter, follow `../../reference/obsidian-format.md` for Obsidian-native wikilinks, callouts, comments, and YAML property formatting when those constructs are relevant.

1. Filename: `capture-YYYY-MM-DD-{2-3 word topic summary in kebab-case}.md`
2. frontmatter:
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [capture, {topic-keyword}]
   type: capture
   ---
   ```
3. Write the content of `$ARGUMENTS` in the body.
   - If `$ARGUMENTS` starts with `http://` or `https://`, treat it as URL capture:
     1. Check for an installed Defuddle CLI with `command -v defuddle`.
     2. Detect a timeout helper using the same pattern as `../../reference/obsidian-cli.md` (`timeout` → `gtimeout` → none); store as `$DEFUDDLE_TO`. Then run `${DEFUDDLE_TO:+$DEFUDDLE_TO 15} defuddle parse "$URL" --md`. The `${VAR:+...}` form expands the wrapper only when a helper is available, so the call still works on default macOS (where `timeout` is `command not found`).
     3. If Defuddle is missing, exits non-zero, or hits the timeout (124), do not install anything and do not block capture; write the original URL only and continue. Do not add explanatory body text — the URL alone is the captured content. The "save immediately" core behavior MUST hold even if Defuddle is slow.
     4. Preserve the skill's core behavior: save immediately and output only the saved file path.
4. **Directory validation**: If `~/vault/00_Inbox/` does not exist, create it automatically (`mkdir -p`).
5. **Duplicate detection**: If a file with the same date and topic already exists, append `-v2`, `-v3`, etc. to the filename.
6. **Save immediately without confirmation.** This is the core behavior of this skill.
7. Output only the saved file path. No follow-up questions.
