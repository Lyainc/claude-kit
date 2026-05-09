---
name: note
description: "Create a new note and link it to the relevant MOC. Examples: '/note kubernetes networking basics' or '/note oauth flow' (offers to link to active projects)"
allowed-tools: Read Write Edit Bash Glob Grep
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create a new note in `~/vault/30_Notes/` on the topic of `$ARGUMENTS`.

## Procedure

Before drafting the note, follow `../../reference/obsidian-format.md` for Obsidian-native wikilinks, callouts, task lists, comments, and YAML property formatting. Prefer wikilinks for internal vault references and Markdown links for external URLs.

1. **Determine domain**: Identify the relevant domain from the topic.
2. **Check for duplicates**: Use `mdfind -onlyin ~/vault/30_Notes "$ARGUMENTS"` or `ls ~/vault/30_Notes/ | grep -i {keyword}` to check for existing notes.
   - If an identical or similar note exists, notify the user and ask them to choose: overwrite / rename / merge.
3. **Scan active projects** (optional project linking):
   - List directories under `~/vault/20_Projects/` to discover active projects.
   - If any project names appear relevant to the note topic, ask the user via AskUserQuestion:
     > "이 노트를 연관 프로젝트에 연결할까요? 아래 프로젝트 중 관련된 것을 선택해 주세요."
     > Options: `[{project-a}]`, `[{project-b}]`, ..., `[여러 개 선택]`, `[나중에 정할게]`
   - If the user selects one or more projects, set `also_related_projects: [{name1}, {name2}]` in the frontmatter.
   - If the user selects "나중에 정할게" or no projects are relevant, omit `also_related_projects`.
   - If no projects exist yet (`20_Projects/` is empty or absent), skip this step silently.
4. **Create file**: `30_Notes/{topic-in-kebab-case}.md`
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [note, {domain}, {keyword}]
   type: note
   # also_related_projects: []   # populated if user selected projects in step 3
   # promoted_to_project: ""     # populated when this note is promoted via /project --promote-from
   ---
   ```
   - Include `also_related_projects` only if the user selected projects (non-empty).
   - Never include `promoted_to_project` at creation time — it is set only during `/project {name} --promote-from` promotion.
5. **Link to MOC**:
   - If `10_MOC/{domain}.md` exists → add backlink
   - If not → create a new domain MOC, then add a link in `Home.md` as well (requires user confirmation)
   - If the topic spans multiple domains → link to all relevant MOCs
6. **Update project back-references** (only when Step 3 produced project selections):
   - For each selected project name, locate `~/vault/20_Projects/{name}/_index.md`.
   - If `_index.md` is missing for a selected project, log a warning and continue (do not fail note creation).
   - **Reference format**: append `30_Notes/{topic}.md` (relative path from vault root, no quotes, no wikilink). This matches the convention used by the `project` skill Mode B and lets vault-audit cross-check both directions.
   - **YAML safety**: if `{topic}` contains any character outside `[a-z0-9-]` (the kebab-case filename invariant from Step 4), abort Step 6 for that project and add the project to the `skipped_projects` list (reported in Step 7) with the unsafe character as the reason. The note file itself is still created.
   - **Idempotent check**: read the current `related_notes` array. Skip if `30_Notes/{topic}.md` is already present (string equality on the relative path). Different forms — absolute path, wikilink `[[30_Notes/{topic}]]`, `./{topic}.md` — are NOT considered equivalent and will be added; vault-audit surfaces such duplicates if they accumulate. Note: this skill writes only the canonical form (vault-relative path, no quotes); humans editing `_index.md` should match this form to avoid duplicate accumulation.
   - **Append form**: if `related_notes` is absent, add it as a flow array on a new line: `related_notes: [30_Notes/{topic}.md]`. If present in flow form `[a, b]`, insert before the closing `]`. If present in block form (`- a` / `- b` lines), append a new `- 30_Notes/{topic}.md` line preserving indentation. Use the Edit tool — never Write the whole `_index.md`.
   - **Concurrency**: this skill assumes serial execution per vault. Two concurrent note creations targeting the same project may produce a lost update; vault-audit `missing_forward_reference` (E8) surfaces it on next run. No locking is performed here.
   - In the common (serial) case, this step prevents W2 vault-audit `missing_forward_reference` (E8) from firing on the new note.
7. **Output result**: Created file path + list of updated MOCs + project links established + project `_index.md` files updated + `skipped_projects` (projects whose `_index.md` was skipped due to YAML safety abort, with the unsafe character reason — empty if none)

## Optional Note Fields

| Field | When to use | Example |
|-------|-------------|---------|
| `also_related_projects` | note is relevant to one or more projects (user-confirmed) | `[foo, bar]` |
| `promoted_to_project` | note was promoted to a project via `/project --promote-from` | `foo` |

Both fields are optional. Do not prompt the user about `promoted_to_project` at note creation — it is set automatically by the `project` skill.

## AskUserQuestion — Project Linking (Step 3)

When active projects exist and at least one appears relevant, present this question:

```json
{
  "question": "이 노트를 연관 프로젝트에 연결할까요?",
  "options": [
    "{project-a}",
    "{project-b}",
    "여러 개 선택",
    "나중에 정할게"
  ],
  "note": "선택한 프로젝트는 노트 frontmatter의 also_related_projects 필드에 기록됩니다."
}
```

If the user selects "여러 개 선택", follow up with a multi-select list of all active projects.

## Rules

- Do not create subdirectories inside `30_Notes/`.
- Show the creation plan first and create the file only after user confirmation.
- The project linking question (step 3) adds at most 1–2 extra interaction steps; keep it concise.
- If scanning `20_Projects/` fails or is empty, silently skip step 3 and proceed with note creation.
- Preserve all existing MOC connection logic unchanged.
