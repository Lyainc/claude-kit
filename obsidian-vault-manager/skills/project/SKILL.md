---
name: project
description: "Create a new project, promote a note to a project, or enrich an existing project's _index.md. Example: '/project api-gateway', '/project api-gateway --promote-from 30_Notes/api-design.md', '/project api-gateway --enrich related_notes=30_Notes/oauth.md'"
allowed-tools: Read Write Edit Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create or update a project named `$ARGUMENTS`.

Parse `$ARGUMENTS` to detect options:
- `{name}` — plain project creation
- `{name} --promote-from {note-path}` — promote an existing note to a new project
- `{name} --enrich {field}={value}` — add enrichment fields to an existing project's `_index.md`

---

## Mode A: Plain Project Creation

Arguments: `{name}` (no flags)

### Procedure

1. **Check for duplicates**: Verify whether `~/vault/20_Projects/{name}/` already exists.
   - If it exists, notify the user and stop.
2. **Show plan**: Present the `_index.md` that will be created and ask for confirmation.
3. **Create directory + `_index.md`**: `~/vault/20_Projects/{name}/_index.md`

   Minimum 5-field template:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [project, {name}]
   type: project
   status: active
   domain: [{inferred-domain}]
   ---
   # {Project Name}
   ## Overview
   ## Goals
   ## Outputs
   ## Related Notes
   ```

   - Infer `domain` from the project name (same domain inference rules as the `note` skill).
   - If domain cannot be inferred, ask the user via AskUserQuestion before creating.

4. **Update `Home.md`**: Add `[[20_Projects/{name}/_index|{Project Name}]]` to the "Active Projects" section.
5. **Output result**: Created path and frontmatter summary.

---

## Mode B: Note → Project Promotion (`--promote-from`)

Arguments: `{name} --promote-from {note-path}`

Promote an existing note at `~/vault/{note-path}` into a new project.

### Procedure

1. **Validate inputs**:
   - Verify `~/vault/{note-path}` exists. If not, report an error and stop.
   - Verify `~/vault/20_Projects/{name}/` does NOT exist. If it does, report a conflict and stop.

2. **Read the source note**:
   - Parse the note's frontmatter (YAML block between `---` delimiters).
   - Extract the first paragraph of the body (first non-empty, non-heading line block after frontmatter) for use as the Overview prefill.

3. **Show plan**: Present all changes that will be made (new `_index.md`, note frontmatter diff) and ask for confirmation.

4. **Execute (all steps or none — abort on any failure)**:

   **Step 1 — Create `_index.md`**:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [project, {name}]
   type: project
   status: active
   domain: [{domain-from-note-or-inferred}]
   absorbs:
     - {note-path}
   ---
   # {Project Name}
   ## Overview
   {first-paragraph-from-note}
   ## Goals
   ## Outputs
   ## Related Notes
   ```
   - `domain`: reuse the note's domain tags if present; otherwise infer from topic.
   - `absorbs`: set to `[{note-path}]` using the path relative to vault root.

   **Step 2 — Update the source note's frontmatter**:
   - Read the note file.
   - Parse YAML frontmatter.
   - Add field `promoted_to_project: {name}` (merge into existing frontmatter — do NOT overwrite other fields).
   - Rewrite only the frontmatter block; preserve the note body exactly.

   **Step 3 — Update `Home.md`**:
   - Add `[[20_Projects/{name}/_index|{Project Name}]]` to the "Active Projects" section (reuse existing logic).

5. **Output result**: Confirm all 3 steps completed. Show the note frontmatter diff and the created `_index.md` frontmatter.

### YAML Frontmatter Merge — Implementation Notes

Use Python 3 stdlib to parse and merge YAML safely:

```bash
python3 - <<'EOF'
import sys, re

note_path = sys.argv[1]
project_name = sys.argv[2]

with open(note_path, 'r') as f:
    content = f.read()

# Split frontmatter
match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
if not match:
    print("ERROR: no frontmatter found")
    sys.exit(1)

fm_text, body = match.group(1), match.group(2)

# Add promoted_to_project if not already present
if 'promoted_to_project' not in fm_text:
    fm_text = fm_text.rstrip() + f'\npromoted_to_project: {project_name}'

new_content = f'---\n{fm_text}\n---\n{body}'
with open(note_path, 'w') as f:
    f.write(new_content)

print("OK")
EOF
"$NOTE_FULL_PATH" "$PROJECT_NAME"
```

---

## Mode C: Enrichment (`--enrich`)

Arguments: `{name} --enrich {field}={value}`

Add or update an optional enrichment field in an existing project's `_index.md`.

### Supported enrichment fields

| Field | Type | Example value |
|-------|------|---------------|
| `last_session` | path | `20_Projects/foo/session-2026-04-15.md` |
| `vault_link_source` | abs-path | `/Users/x/dev/prj/foo` |
| `related_notes` | array[path] | `30_Notes/oauth.md` (appended to array) |
| `related_plans` | array[path] | `20_Projects/foo/plan-2026-04-16-api.md` (appended) |
| `auto_capture` | bool | `true` |

### Procedure

1. **Validate**: Verify `~/vault/20_Projects/{name}/_index.md` exists. If not, report error and stop.
2. **Show plan**: Show the current field value (if any) and the new value. Ask for confirmation.
3. **Update frontmatter**: Merge the new field into the existing YAML frontmatter.
   - For array fields (`related_notes`, `related_plans`): append the new value to the existing array.
   - For scalar fields: set or replace.
4. **Output result**: Confirm the update with the new frontmatter block.

---

## Backward Compatibility

Existing `_index.md` files with fewer than 5 required fields are **not automatically modified**. If an existing project is opened and the `_index.md` is missing required fields (`domain`, `status`, `type`), provide a migration guide:

> "이 프로젝트의 `_index.md`가 최소 스키마(5필드: created, tags, type, status, domain)를 충족하지 않습니다. `/project {name} --enrich` 로 필드를 추가하거나 직접 수정하세요."

Do NOT auto-fix existing files.

---

## _index.md Schema Reference

### Minimum (required at creation)

| Field | Type | Notes |
|-------|------|-------|
| `created` | date | `YYYY-MM-DD` |
| `tags` | array | must include `project` and `{name}` |
| `type` | enum | always `project` |
| `status` | enum | `active \| paused \| completed \| archived` |
| `domain` | array | inferred domain slugs |

### Progressive enrichment (add when needed)

| Field | Type | Notes |
|-------|------|-------|
| `last_session` | path | updated after each session |
| `vault_link_source` | abs-path | `.vault-link` integration (vault-bridge W0) |
| `absorbs` | array[path] | notes this project was promoted from |
| `related_notes` | array[path] | notes referenced during work |
| `related_plans` | array[path] | `plan-*.md` files inside the project |
| `auto_capture` | bool | W8 opt-in, default `false` |

---

## Rules

- Show the plan first and create/modify only after user confirmation.
- All file operations are atomic: if any step fails during `--promote-from`, abort remaining steps and report the failure clearly.
- Never overwrite existing project directories.
- `absorbs` and `related_notes` are append-only (never remove existing entries automatically).
