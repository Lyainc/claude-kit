---
name: base
description: "Generate a new, non-destructive Obsidian Bases (.base) view from built-in sources/notes/recent or user-defined filters and optional sorting. Accept natural-language conditions or --filter and --sort; ask for missing details. Examples: '/base sources', '/base notes', '/base recent', '/base my-clippings --template sources', '/base work --filter track != null', '/base 대기·진행중을 status_since 오름차순으로'"
allowed-tools: Read Write Bash Glob AskUserQuestion
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Create a new Obsidian Bases view file at `~/vault/notes/{view-name}.base` for `$ARGUMENTS`.

A `.base` file is a **pure-YAML view definition** over note properties. This skill creates table views and is **new-file-only**: never read existing notes or views to infer conditions, edit them, or overwrite them. Read `../../reference/obsidian-bases-schema.md` for syntax and the four custom examples before composing a custom view.

## Argument Parsing

Interpret the request as text, never as a shell command:
- `{view-name}` matching `sources`, `notes`, or `recent` selects that built-in.
- `{view-name} --template {sources|notes|recent}` selects a built-in with a custom filename.
- `{view-name} --filter '<expression>' [--sort '<property>:ASC|DESC']` supplies a custom filter and optionally one row-sort key. Quotes delimit the argument; preserve quoted literals inside the expression. Without outer quotes, consume the expression up to the next flag. Never evaluate flags through Bash, `eval`, or shell interpolation.
- Natural language may supply the same property, condition, comparison value, and sort direction. AskUserQuestion for anything needed to form the condition but missing or ambiguous. Existence tests need no comparison value. If no filter or built-in is given, ask whether to use a built-in or custom conditions; do not invent either.
- Omitted custom sorting means no `sort` key. If sorting is requested, both property and direction are required. Do not guess a date cutoff from “old”: confirm the filter and sort; “oldest first by status_since” specifies ASC, not an age threshold.
- Unknown flags/templates, empty values, duplicate flags, malformed expressions/directions, conflicting natural-language/flag conditions, or a built-in name/`--template` combined with `--filter` require AskUserQuestion before continuing. For mixed template/filter input, ask whether to combine the template conditions with the filter or use a custom view instead; never choose precedence silently.

## Custom Views

Use only user-supplied or explicitly confirmed conditions. Reference note properties as `note.<key>` or bare `<key>`, never `property.<key>`. Keep expressions as YAML strings and escape their YAML quotes without changing the expression. Compose AND/OR from the stated meaning. Place the **whole** custom condition under a global `and` alongside `file.hasProperty("type")`, so an OR branch cannot bypass the guard.

Display `file.name` plus the referenced filter/sort properties, or user-specified columns. Do not add folder restrictions, status values, date cutoffs, missing-property exclusions, or tie-break sorts. Missing sort values follow Obsidian's ordering; disclose that no exclusion was added. Custom `status` values are permitted when supplied by the user. They do not restore the abolished built-in status machine or its old templates.

## Built-in View Templates

Built-ins follow the source/prose folder split. **Every filter includes `file.hasProperty("type")`**: notes without `type:` stay invisible (type opt-in). The old status templates remain abolished (#480).

### sources — everything in `sources/` (source text kept as-is)

```yaml
filters:
  and:
    - file.inFolder("sources")
    - file.hasProperty("type")
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
    - file.hasProperty("type")
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
    - file.hasProperty("type")
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

1. **Resolve request**: Apply Argument Parsing, awaiting required answers. Read the schema reference for custom syntax. Resolve a view name (ask if absent), filter, displayed columns, and optional sort; then compose the YAML. Preserve built-ins unless an override was explicitly confirmed.

2. **Normalize filename**: `{view-name}` → lowercase kebab-case. Target path: `~/vault/notes/{view-name}.base`.
   - **Filename collision**: use Glob over `~/vault/notes/*.base` to see which view files already exist. If the exact same stem `.base` is there, append `-v2`, `-v3`, etc. automatically — no AskUserQuestion. This is a mechanical uniqueness guarantee. Never overwrite an existing `.base`.

3. **Directory validation**: use Bash to run `mkdir -p ~/vault/notes/` before any write, to guard against a missing directory.

4. **Check and show plan**: Check the YAML structure, quoted expressions, global type guard, and sort property/direction against the reference. Present the actual target path, full `.base` YAML, and a short explanation of included/excluded notes and sorting (including missing values). Use AskUserQuestion and wait for user confirmation before writing. No answer means no write.

5. **Create file** (after user confirmation): Recheck the target with Glob immediately before Write. A new collision requires a new unique path and renewed confirmation of that path. Write ONLY the new `.base` file. The body is pure YAML, without frontmatter or Markdown.

6. **Output result**: Created path and a reminder (in Korean) to open the `.base` in Obsidian to check rows and sorting. Empty rows may mean no matching data or a property/expression mismatch; do not infer which. File creation alone does not verify rendering: say rendering is unverified unless it was actually observed. No other follow-up questions.

## Rules

- **New-file-only**: write ONLY the new `.base`; never read or change existing notes/views.
- **Built-ins and custom views**: support the 3 built-ins and explicit property/value, folder, tag, or date conditions. Never infer conditions from existing notes or a vault schema.
- **type opt-in**: retain the global `file.hasProperty("type")` guard for every view.
- **Pure YAML**: no frontmatter delimiters or Markdown.
- Show the plan first; write the file only after user confirmation.
- `notes/` allows free sub-folder structure; do not auto-create sub-folders unless the user specifies a path.
- Custom `status` filters are allowed; the plugin does not create or manage that field. The former built-in state machine stays abolished (#480).
- For syntax, examples, and future Bases changes, Read `../../reference/obsidian-bases-schema.md`. Specific-work selection, grouping, and schema inference are outside this minimum contract.
