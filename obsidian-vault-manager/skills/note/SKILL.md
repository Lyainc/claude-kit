---
name: note
description: "Create a new note and link it to the relevant MOC. Example: '/note kubernetes networking basics'"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create a new note in `~/vault/30_Notes/` on the topic of `$ARGUMENTS`.

## Procedure

1. **Determine domain**: Identify the relevant domain from the topic.
2. **Check for duplicates**: Use `mdfind -onlyin ~/vault/30_Notes "$ARGUMENTS"` or `ls ~/vault/30_Notes/ | grep -i {keyword}` to check for existing notes.
   - If an identical or similar note exists, notify the user and ask them to choose: overwrite / rename / merge.
3. **Create file**: `30_Notes/{topic-in-kebab-case}.md`
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [domain, keyword]
   ---
   ```
4. **Link to MOC**:
   - If `10_MOC/{domain}.md` exists → add backlink
   - If not → create a new domain MOC, then add a link in `Home.md` as well (requires user confirmation)
   - If the topic spans multiple domains → link to all relevant MOCs
5. **Output result**: Created file path + list of updated MOCs

## Rules

- Do not create subdirectories inside `30_Notes/`.
- Show the creation plan first and create the file only after user confirmation.
