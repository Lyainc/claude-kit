---
name: project
description: "Create a new project, promote a note to a project, or enrich an existing project's _index.md. Example: '/project api-gateway', '/project api-gateway --promote-from 30_Notes/api-design.md', '/project api-gateway --enrich related_notes=30_Notes/oauth.md'"
model: sonnet
allowed-tools: Read Write Edit Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create or update a project named `$ARGUMENTS`.

Parse `$ARGUMENTS` to detect options:
- `{name}` — plain project creation
- `{name} --promote-from {note-path}` — promote an existing note to a new project
- `{name} --enrich {field}={value}` — add enrichment fields to an existing project's `_index.md`

---

## Format Reference

When generating `_index.md` content, frontmatter, or internal vault links, follow `../../reference/obsidian-format.md`. Prefer wikilinks for vault-internal references, keep `_index.md` properties flat YAML, and quote wikilinks inside YAML values.

---

## Mode A: Plain Project Creation

Arguments: `{name}` (no flags)

### Procedure

1. **Check for duplicates**: Verify whether `~/vault/20_Projects/{name}/` already exists.
   - If it exists, notify the user and stop.
2. **Show plan**: Present the `_index.md` that will be created and ask for confirmation.
3. **Ask about `auto_capture` opt-in** (one-time, before creation): use **AskUserQuestion** to ask whether to enable plan-doc autosync (Layer 2 of vault-bridge's 2-layer gate). Default is **No**.

   > **`auto_capture` 옵트인** — 이 프로젝트에서 작성한 외부 plan/design 문서(`docs/plans/`, `PLAN.md`, `RFC-*.md` 등)를 vault에 자동 스냅샷할까요?
   >
   > 이 설정은 vault-bridge의 `/save-plan-doc` 명령과 SessionEnd 자동 제안에 사용됩니다. 나중에 `/project {name} --enrich auto_capture=true|false`로 변경 가능합니다.

   Options:
   - 아니요 (기본) — `auto_capture: false`로 명시 기입
   - 네 — `auto_capture: true`로 명시 기입

4. **Create directory + `_index.md`**: `~/vault/20_Projects/{name}/_index.md`

   Minimum 6-field template (5 required + auto_capture):
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [project, {name}]
   type: project
   status: active
   domain: [{inferred-domain}]
   auto_capture: {user-choice}
   ---
   # {Project Name}
   ## Overview
   ## Goals
   ## Outputs
   ## Related Notes
   ```

   - Infer `domain` from the project name (same domain inference rules as the `note` skill).
   - If domain cannot be inferred, ask the user via AskUserQuestion before creating.
   - `auto_capture`: write the boolean value chosen in Step 3 (default `false`).

5. **Update `Home.md`**: Add `[[20_Projects/{name}/_index|{Project Name}]]` to the "Active Projects" section.
6. **Output result**: Created path and frontmatter summary.

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

4. **Ask about `auto_capture` opt-in** (same as Mode A Step 3): use **AskUserQuestion** with default `No`. The chosen boolean is written into the new `_index.md` frontmatter at Step 5.

5. **Execute (all steps or none — abort on any failure)**:

   **Step 1 — Create `_index.md`**:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [project, {name}]
   type: project
   status: active
   domain: [{domain-from-note-or-inferred}]
   auto_capture: {user-choice}
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

6. **Output result**: Confirm all 3 steps completed. Show the note frontmatter diff and the created `_index.md` frontmatter.

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
| `auto_capture` | bool | `true` (set/replace — required field since Mode A/B Step 3 writes it at creation) |

### Procedure

1. **Validate**: Verify `~/vault/20_Projects/{name}/_index.md` exists. If not, report error and stop.
2. **Show plan**: Show the current field value (if any) and the new value. Ask for confirmation.
3. **Update frontmatter**: Merge the new field into the existing YAML frontmatter.
   - For array fields (`related_notes`, `related_plans`): append the new value to the existing array.
   - For scalar fields: set or replace.
4. **Output result**: Confirm the update with the new frontmatter block.

---

## Backward Compatibility

Existing `_index.md` files are **not automatically modified**. If an existing project is opened and the `_index.md` is missing required fields (`domain`, `status`, `type`), provide a migration guide:

> "이 프로젝트의 `_index.md`에 필수 필드(`created`, `tags`, `type`, `status`, `domain`)가 빠져 있을 수 있습니다. `/project {name} --enrich`로 추가하거나 직접 수정하세요. `auto_capture`는 옵트인 필드이므로 필요할 때만 추가하면 됩니다."

`auto_capture` absent in pre-existing files is interpreted as `false` (vault-bridge SessionEnd hook and `/save-plan-doc` both treat absent as opt-out). Migration is not required for plan-doc autosync to remain off; users only need to add it explicitly to opt **in**.

Do NOT auto-fix existing files.

---

## _index.md Schema Reference

### Minimum schema at creation (5 required + 1 opt-in)

| Field | Type | Notes |
|-------|------|-------|
| `created` | date | required — `YYYY-MM-DD` |
| `tags` | array | required — must include `project` and `{name}` |
| `type` | enum | required — always `project` |
| `status` | enum | required — `active \| paused \| completed \| archived` |
| `domain` | array | required — inferred domain slugs |
| `auto_capture` | bool | opt-in — asked via AskUserQuestion at creation (default `false`). W8 plan-doc autosync, Layer 2 of vault-bridge's 2-layer gate. |

### Progressive enrichment (add when needed)

| Field | Type | Notes |
|-------|------|-------|
| `last_session` | path | updated after each session |
| `vault_link_source` | abs-path | `.vault-link` integration (vault-bridge W0) |
| `absorbs` | array[path] | notes this project was promoted from |
| `related_notes` | array[path] | notes referenced during work |
| `related_plans` | array[path] | `plan-*.md` files inside the project |

---

## Rules

- Show the plan first and create/modify only after user confirmation.
- All file operations are atomic: if any step fails during `--promote-from`, abort remaining steps and report the failure clearly.
- Never overwrite existing project directories.
- `absorbs` and `related_notes` are append-only (never remove existing entries automatically).
