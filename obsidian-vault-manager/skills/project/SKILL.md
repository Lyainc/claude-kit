---
name: project
description: "Create a new project and register it in Home.md. Example: '/project api-gateway'"
allowed-tools: Read Write Edit Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create a new project named `$ARGUMENTS`.

## Procedure

1. **Check for duplicates**: Verify whether `~/vault/20_Projects/$ARGUMENTS/` already exists.
   - If it exists, notify the user and stop.
2. **Create directory + `_index.md`**:
   ```
   ~/vault/20_Projects/{project-name}/_index.md
   ```
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [project, {project-name}]
   type: project
   status: active
   ---
   # {Project Name}
   ## Overview
   ## Goals
   ## Outputs
   ## Related Notes
   ```
3. **Update `Home.md`**: Add `[[20_Projects/{project-name}/_index|{Project Name}]]` link to the "Active Projects" section.
4. **Output result**: The created path.

## Rules

- Show the plan first and create only after user confirmation.
