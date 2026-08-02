---
name: base
description: "Generate an Obsidian Bases (.base) view file in ~/vault/notes/ from enforced frontmatter — a live, non-destructive view that never modifies existing notes. Built-in templates: sources, notes, recent. Examples: '/base sources', '/base notes', '/base recent', '/base my-clippings --template sources'"
model: sonnet
allowed-tools: Read Write Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create a new Obsidian Bases view file at `~/vault/notes/{view-name}.base` for `$ARGUMENTS`.

A `.base` file is a **pure-YAML view definition** that renders a live table/cards/list over the vault's enforced frontmatter (`type` / `created` / `tags` / `provenance`). It is **new-file-only**: this skill writes a brand-new `.base` file and NEVER reads, edits, or overwrites any existing `.md` note. See `../../reference/obsidian-bases-schema.md` for the version-pinned `.base` schema.

## Argument Parsing

Parse `$ARGUMENTS`:
- `{view-name}` — when `{view-name}` is one of the built-in template names (`sources`, `notes`, `recent`), use that template and name the file `{view-name}.base`.
- `{view-name} --template {template}` — use the named built-in `{template}` but write the file as `{view-name}.base` (custom filename, built-in body).
- Valid templates: `sources`, `notes`, `recent`. If no template is resolvable from the name and no `--template` flag is given, ask the user which of the three templates to use (do not invent a filter).
- **Invalid `--template` value**: if `--template` is given with a value that is NOT one of the 3 built-ins, do NOT silently create a broken view. Instead, immediately stop, list the valid names (`sources`, `notes`, `recent`), and re-ask the user which template to apply.

## Built-in View Templates

Each template's filter is aligned with the B-layer folder split (v5 §5 — source text in `sources/`, your own prose in `notes/`). The status machine the old `inbox-raw`/`draft-notes`/`evergreen` templates filtered on was abolished in #480, so those three were replaced. **Every filter MUST include `property.type != null`** so notes without a `type:` field stay invisible (v4 §2.2 type opt-in) — never drop this condition.

### sources — everything in `sources/` (source text kept as-is)

```yaml
filters:
  and:
    - file.inFolder("sources")
    - property.type != null
views:
  - type: table
    name: "Sources"
    order:
      - file.name
      - type
      - created
    sort:
      - property: created
        direction: DESC
```

### notes — everything in `notes/` (prose you wrote), newest first

```yaml
filters:
  and:
    - file.inFolder("notes")
    - property.type != null
views:
  - type: table
    name: "Notes"
    order:
      - file.name
      - type
      - tags
      - created
    sort:
      - property: created
        direction: DESC
```

### recent — everything saved lately, across folders

```yaml
filters:
  and:
    - property.type != null
views:
  - type: table
    name: "Recent"
    order:
      - file.name
      - type
      - tags
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
- **Built-ins are starting points**: the 3 built-in templates cover the most common cases; users can author custom views with any other filter (tag, type, folder) — this skill is not limited to those 3.
- **type opt-in guard**: every template filter MUST keep `property.type != null` so untyped notes (diary, book notes, free folders) stay invisible (v4 §2.2). Never remove it.
- **Pure YAML body**: a `.base` file is YAML only — no YAML frontmatter delimiters (`---`), no Markdown sections.
- Show the plan first; write the file only after user confirmation.
- `notes/` allows free sub-folder structure; do not auto-create sub-folders unless the user specifies a path.
- Do not filter on `status:` — the status machine is abolished (v5 §5/§6, #480) and nothing writes that field anymore.
- For schema details / future Obsidian Bases version changes, consult `../../reference/obsidian-bases-schema.md`.
