---
name: base
description: "Generate an Obsidian Bases (.base) view file in ~/vault/notes/ from enforced frontmatter — a live, non-destructive view that never modifies existing notes. Built-in templates: inbox-raw, draft-notes, evergreen. Examples: '/base inbox-raw', '/base draft-notes', '/base evergreen', '/base my-tasks --template draft-notes'"
model: sonnet
allowed-tools: Read Write Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create a new Obsidian Bases view file at `~/vault/notes/{view-name}.base` for `$ARGUMENTS`.

A `.base` file is a **pure-YAML view definition** that renders a live table/cards/list over the vault's enforced frontmatter (`type` / `status` / `created` / `tags`). It is **new-file-only**: this skill writes a brand-new `.base` file and NEVER reads, edits, or overwrites any existing `.md` note. See `../../reference/obsidian-bases-schema.md` for the version-pinned `.base` schema.

## Argument Parsing

Parse `$ARGUMENTS`:
- `{view-name}` — when `{view-name}` is one of the built-in template names (`inbox-raw`, `draft-notes`, `evergreen`), use that template and name the file `{view-name}.base`.
- `{view-name} --template {template}` — use the named built-in `{template}` but write the file as `{view-name}.base` (custom filename, built-in body).
- Valid templates: `inbox-raw`, `draft-notes`, `evergreen`. If no template is resolvable from the name and no `--template` flag is given, ask the user which of the three templates to use (do not invent a filter).

## Built-in View Templates

Each template's filter is aligned with the v4 status machine. **Every filter MUST include `property.type != null`** so notes without a `type:` field stay invisible (v4 §2.2 type opt-in) — never drop this condition.

### inbox-raw — `inbox/` files with `status: raw`

Visualizes stale inbox signal (raw captures/sessions that have not been triaged).

```yaml
filters:
  and:
    - file.inFolder("inbox")
    - property.type != null
    - property.status == "raw"
views:
  - type: table
    name: "Inbox (raw)"
    order:
      - file.name
      - type
      - created
    sort:
      - property: created
        direction: DESC
```

### draft-notes — `notes/` files with `status: draft`, sorted by `created`

```yaml
filters:
  and:
    - file.inFolder("notes")
    - property.type != null
    - property.status == "draft"
views:
  - type: table
    name: "Draft notes"
    order:
      - file.name
      - type
      - created
    sort:
      - property: created
        direction: ASC
```

### evergreen — `notes/` files with `status: evergreen`

```yaml
filters:
  and:
    - file.inFolder("notes")
    - property.type != null
    - property.status == "evergreen"
views:
  - type: table
    name: "Evergreen"
    order:
      - file.name
      - type
      - created
    sort:
      - property: created
        direction: DESC
```

## Procedure

1. **Resolve view name + template**: Apply Argument Parsing. The view name becomes the filename stem; the template determines the body.

2. **Normalize filename**: `{view-name}` → lowercase kebab-case. Target path: `~/vault/notes/{view-name}.base`.
   - **Filename collision** (exact same stem `.base` exists): append `-v2`, `-v3`, etc. automatically — no AskUserQuestion. This is a mechanical uniqueness guarantee. Never overwrite an existing `.base`.

3. **Directory validation**: Run `mkdir -p ~/vault/notes/` before any write to guard against a missing directory.

4. **Show plan**: Present the target filename and the full `.base` YAML body, then wait for user confirmation before writing.

5. **Create file** (after user confirmation): Write the resolved template YAML to `~/vault/notes/{view-name}.base`. The file body is pure YAML — no frontmatter, no Markdown.

6. **Output result**: Created file path. No follow-up questions.

## Rules

- **New-file-only**: write ONLY the new `.base` file. NEVER read, edit, or overwrite any existing note. This skill has no path that touches `.md` content.
- **type opt-in guard**: every template filter MUST keep `property.type != null` so untyped notes (diary, book notes, free folders) stay invisible (v4 §2.2). Never remove it.
- **Pure YAML body**: a `.base` file is YAML only — no YAML frontmatter delimiters (`---`), no Markdown sections.
- Show the plan first; write the file only after user confirmation.
- `notes/` allows free sub-folder structure; do not auto-create sub-folders unless the user specifies a path.
- Filters align with the v4 status machine (`raw` / `draft` / `evergreen`); do not invent statuses outside that set.
- For schema details / future Obsidian Bases version changes, consult `../../reference/obsidian-bases-schema.md`.
