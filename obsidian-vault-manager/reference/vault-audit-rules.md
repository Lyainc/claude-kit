# vault-audit — Error Type Detection Rules

Detection rules for the `audit` skill's CLASSIFY phase. The skill body (`skills/audit/SKILL.md`) summarizes these as a table; this file is the canonical pseudocode reference.

Five error types cover v4's three-folder vault layout (`inbox/`, `notes/`, `assets/`). Severity buckets: **Critical** (data integrity risk), **Warning** (quality / navigation risk), **Info** (style / convention).

> **v4 note**: E6–E9 (project-binding checks) were removed in v4 because `20_Projects/` is no longer part of the vault layout. PR 4 (`/audit` Phase 1) will add manifest-level metadata checks as replacements.

## E1 — `missing_frontmatter` [Critical]

**Rule**: `has_frontmatter == false`
**Source**: `frontmatter_records`
**Guard**: Skip `.ovm/` and `.obsidian/` paths.

## E2 — `missing_required_fields` [Critical]

**Rule**: `has_frontmatter == true` AND `missing_required` is non-empty
**Source**: `frontmatter_records`
**Reports**: which fields are missing.

**Required fields**:

| Scope | Fields |
|-------|--------|
| All types (universal) | `created`, `tags`, `type` |
| `type: note` and `type: decision` only | `status` (v4 §3.3 status machine) |

`status` is optional for `capture`, `session`, and `plan` — omitting it for those types is not an E2 violation.

## E3 — `filename_convention_violation` [Warning]

**Rule**: file does not conform to v4 naming convention (v4 §3.6)
**Source**: `filename_records`

v4 filename rules per folder:

| Folder | Convention | Example violation |
|--------|-----------|-------------------|
| `notes/` | `{slug}.md` (no date prefix) — or `{type}-YYYY-MM-DD-{slug}.md` for dated types (`decision`, `plan`) | `2026-04-bad-name.md` (`\d{4}-\d{2}-` date-first, v3 style) |
| `inbox/` | Exempt — raw input zone; any filename accepted | — |
| `assets/` | Exempt — attachments; any filename accepted | — |

**Guard**: `_index.md` is always valid (skip). Files in `inbox/` and `assets/` are exempt.

**Detection pseudocode** for files in `notes/`:

```
for each file in notes/ (recursive):
  if file.name == "_index.md": skip
  if file.name matches /^\d{4}-\d{2}-/: → filename_convention_violation
  # date-first prefix is a v3 artifact; v4 requires type-first or no-date slugs
```

## E4 — `broken_wikilink` [Critical]

**Rule**: For each `[[target]]` in a file — look up `target` stem in the vault file set. If no file exists with that stem (case-insensitive match), it is broken.
**Source**: `wikilinks_by_file`, global file index.
**Guard**: Ignore embed links `![[image.png]]` where target has a non-`.md` extension or no extension at all and a matching file exists in assets. Ignore links to headings / blocks within a found note.

## E5 — `orphan_note` [Warning]

**Rule**: A `.md` file in `notes/` (any depth) has zero entries in `inbound_links[stem]`.
**Source**: `inbound_links` (built from full vault scan).
**Guard**: `_index.md` files are never orphans. Files in `inbox/` are exempt (unprocessed captures). Files in `assets/` are exempt.

## Auto-fix eligibility

Only the following are mutated by Phase 4 OPTIONAL-FIX (frontmatter-only edits):

| Type | Auto-fix action |
|------|-----------------|
| `missing_required_fields` (E2) | Add missing `tags`, `type`, `created` fields with inferred values |

Never auto-fixed: E1 (body structure unknown), E3 (rename affects inbound links), E4 (requires human decision on rename/delete), E5 (content value judgment).
