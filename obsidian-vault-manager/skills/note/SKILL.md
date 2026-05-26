---
name: note
description: "Create a new note (evergreen knowledge unit) or decision record in ~/vault/notes/. Examples: '/note kubernetes networking basics', '/note --type decision use-rust-over-go'"
model: sonnet
allowed-tools: Read Write Bash Glob
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Create a new note in `~/vault/notes/` on the topic of `$ARGUMENTS`.

## Argument Parsing

Parse `$ARGUMENTS`:
- `{topic}` — create a `note` type note (default)
- `--type decision {topic}` — create a `decision` type note (dated filename)

## Procedure

Before drafting the note, follow `../../reference/obsidian-format.md` for Obsidian-native wikilinks, callouts, task lists, comments, and YAML property formatting. Prefer wikilinks for internal vault references and Markdown links for external URLs.

1. **Parse type and topic**: Extract `--type {type}` flag (default: `note`). Strip the flag from the topic text. Valid types: `note`, `decision`.

2. **Determine target filename**:
   - `type: note` → `~/vault/notes/{topic-in-kebab-case}.md` (no date prefix — evergreen slug)
   - `type: decision` → `~/vault/notes/decision-YYYY-MM-DD-{topic-in-kebab-case}.md` (type-first, dated)
   - **Filename collision** (exact same stem already exists): append `-v2`, `-v3` etc. automatically — no AskUserQuestion. This is a mechanical uniqueness guarantee, not a content check.

3. **Check for content duplicates**: `find ~/vault/notes -name '*.md' 2>/dev/null | xargs -I{} basename {} .md | grep -i {keyword}`
   - This is a *content similarity* check, distinct from the filename collision in Step 2.
   - If a note with a semantically similar topic already exists, notify the user and ask: overwrite / rename / merge.

4. **Directory validation**: If `~/vault/notes/` does not exist, create it: `mkdir -p ~/vault/notes/`. This guard runs before any write attempt.

5. **Show plan**: Present the target filename and frontmatter to the user. Ask for confirmation before writing.

6. **Create file** (after user confirmation):
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [{type}, {keyword}]
   type: note|decision
   status: raw
   ---
   ```
   Write the note body based on the topic. For `decision` type, structure the body with:
   - `## 문제` — what decision was needed
   - `## 선택지` — options considered
   - `## 결정` — chosen option
   - `## 근거` — reasoning

7. **Output result**: Created file path. No follow-up questions.

## Filename and Status Reference

| Type | Filename pattern | Path | Evergreen eligible |
|------|-----------------|------|--------------------|
| `note` | `{slug}.md` | `notes/` | ✓ |
| `decision` | `decision-YYYY-MM-DD-{slug}.md` | `notes/` | ✓ |

**Status machine** (user-driven; this skill only writes `raw`):

```
raw ──[user]──► draft ──[user]──► evergreen
 │                                    │
 └──────────────► archived ◄──────────┘
```

| Status | Meaning | Set by |
|--------|---------|--------|
| `raw` | Created, not yet reviewed | This skill (always) |
| `draft` | Reviewed, intent to develop | User (Obsidian frontmatter edit) |
| `evergreen` | Stable knowledge unit | User |
| `archived` | Inactive | User |

## Frontmatter Standard

```yaml
---
created: YYYY-MM-DD          # required
tags: [type, keyword]        # required — include type + at least one keyword
type: note|decision          # required — determines filename pattern
status: raw                  # required — initial; user transitions forward
---
```

## Rules

- Show the plan first; write the file only after user confirmation.
- Always write `status: raw` at creation — never `draft` or `evergreen`.
- Default type is `note`; use `--type decision` for decision records.
- `notes/` allows free sub-folder structure; do not auto-create sub-folders.
- Do not add wikilinks to MOC files or project indexes — none exist in v4.
- `decision` type: body always uses the 4-section template (문제/선택지/결정/근거).
