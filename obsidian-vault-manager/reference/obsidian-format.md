# Obsidian Format Reference

Use this reference when generating or editing notes in an Obsidian vault. Prefer Obsidian-native syntax for internal navigation, metadata, and structured annotations.

Sources: Obsidian Help — [Basic formatting syntax](https://obsidian.md/help/syntax), [Properties](https://obsidian.md/help/properties), [Callouts](https://obsidian.md/help/callouts).

## Authoring rules for vault notes

1. Use wikilinks for internal vault references: `[[Note]]`, `[[Note|Alias]]`, `[[Note#Heading]]`.
2. Use Markdown links only for external URLs: `[label](https://example.com)`.
3. Keep frontmatter valid YAML and place it at the very start of the file.
4. Quote wikilinks inside YAML properties: `source: "[[Some Note]]"`.
5. Use callouts for warnings, summaries, decisions, and todos that should stand out in Reading view.
6. Do not invent nested YAML properties for generated notes; keep properties flat and machine-readable.

## Wikilinks and embeds

| Purpose | Syntax | Notes |
| --- | --- | --- |
| Note link | `[[Project Plan]]` | Preferred for internal vault notes. |
| Alias | `[[Project Plan|plan]]` | Use when the display text should be shorter. |
| Heading link | `[[Project Plan#Risks]]` | Link directly to a heading. |
| Block link | `[[Project Plan#^block-id]]` | Use only when a stable block ID exists. |
| Note embed | `![[Project Plan]]` | Embeds another note inline. |
| Asset embed | `![[diagram.png]]` | Use for existing vault assets; do not create image assets unless requested. |

When a target note is known by path, include enough path context to disambiguate:

```md
[[20_Projects/claude-kit/_index|claude-kit]]
[[30_Notes/api-design]]
```

## Properties / YAML frontmatter

Properties are YAML frontmatter fields. Keep generated properties flat, unique per note, and easy to parse.

```yaml
---
created: 2026-05-02
tags:
  - note
  - obsidian
  - reference
type: note
status: active
related:
  - "[[20_Projects/claude-kit/_index]]"
publish: false
reviewed_at: 2026-05-02T18:30:00
---
```

### Property type guide

| Type | Preferred YAML | Notes |
| --- | --- | --- |
| Text | `title: Obsidian format` | Single-line text. Markdown is not rendered inside properties. |
| List | <code>aliases:<br>  - Format Guide<br>  - OVM Format</code> | Use block lists for multi-value fields. |
| Number | `priority: 2` | Use literal integers or decimals, not expressions. |
| Checkbox | `publish: false` | Use `true` / `false`. |
| Date | `created: 2026-05-02` | Use ISO `YYYY-MM-DD` for generated notes. |
| Date & time | `captured_at: 2026-05-02T18:30:00` | Use ISO-like local time unless a workflow requires UTC. |
| Tags | <code>tags:<br>  - capture<br>  - project/foo</code> | Tags are a list. Inline YAML lists are acceptable for short existing templates. |
| Internal link | `project: "[[Project]]"` | Quote wikilinks in YAML values. |

## Tags

Use tags for broad classification, not for every concept mentioned in the body.

```md
#project/active
#domain/devops
```

In frontmatter, prefer YAML lists:

```yaml
tags:
  - project
  - domain/devops
```

## Callouts

Callouts are blockquotes with a type marker on the first line.

```md
> [!note] Summary
> Key context that should remain visible.
```

Common types:

| Type | Use for |
| --- | --- |
| `[!note]` | Neutral notes and summaries |
| `[!info]` | Background context |
| `[!tip]` | Helpful usage guidance |
| `[!todo]` | Action items |
| `[!question]` | Open questions |
| `[!warning]` | Risks or constraints |
| `[!danger]` | Data-loss/security warnings |
| `[!success]` | Completed outcomes |
| `[!failure]` | Failed checks or blockers |

Foldable callouts add `+` or `-` immediately after the type:

```md
> [!question]- Open decision
> Collapsed by default until the reader expands it.
```

Nested callouts use additional blockquote markers:

```md
> [!warning] Risk
> Primary risk statement.
> > [!todo] Mitigation
> > Follow-up action.
```

## Comments

Use Obsidian comments for generator notes that should not render in Reading view:

```md
%% internal note: generated from capture workflow %%
```

Do not store sensitive information in comments; comments remain in the Markdown file.

## Task lists

Use task lists for actionable checklist items:

```md
- [ ] Confirm project link
- [x] Create initial note
```

## Good generated-note skeleton

```md
---
created: 2026-05-02
tags:
  - note
  - api-design
type: note
also_related_projects:
  - claude-kit
---
# API design note

> [!note] Summary
> One-paragraph summary of the note.

## Context

Link related vault material with `[[wikilinks]]`.

## Details

Use ordinary Markdown for prose and tables.

## Next actions

- [ ] Follow-up task
```
