# vault-audit — Error Type Detection Rules

Detection rules for the `vault-audit` skill's CLASSIFY phase. The skill body (`skills/vault-audit/SKILL.md`) summarizes these as a table; this file is the canonical pseudocode reference.

The 8 base error types map to W2 DoD's 8 spec entries. The 9th type (`missing_forward_reference`) is derived from the E7/E8 pair. Severity buckets: **Critical** (data integrity risk), **Warning** (quality / navigation risk), **Info** (style / convention).

## E1 — `missing_frontmatter` [Critical]

**Rule**: `has_frontmatter == false`
**Source**: `frontmatter_records`
**Guard**: Skip `.ovm/` and `.obsidian/` paths.

## E2 — `missing_required_fields` [Critical]

**Rule**: `has_frontmatter == true` AND `missing_required` is non-empty
**Source**: `frontmatter_records`
**Reports**: which fields are missing (`created`, `tags`, `type`).

## E3 — `filename_convention_violation` [Warning]

**Rule**: `conforms == false`
**Source**: `filename_records`
**Guard**: Skip `_index.md` (always valid). Skip files in `00_Inbox/` that are temp / draft names only if `--strict` flag is absent.

## E4 — `broken_wikilink` [Critical]

**Rule**: For each `[[target]]` in a file — look up `target` stem in the vault file set. If no file exists with that stem (case-insensitive match), it is broken.
**Source**: `wikilinks_by_file`, global file index.
**Guard**: Ignore embed links `![[image.png]]` where target has a non-`.md` extension or no extension at all and a matching file exists in assets. Ignore links to headings / blocks within a found note.

## E5 — `orphan_note` [Warning]

**Rule**: A `.md` file in `30_Notes/` has zero entries in `inbound_links[stem]`.
**Source**: `inbound_links` (built from full vault scan).
**Guard**: `_index.md` files are never orphans. Files in `00_Inbox/` are exempt (not yet processed).

## E6 — `broken_project_to_note` [Critical]

**Rule**: `_index.md` has a `related_notes` or `absorbs` field listing a vault-relative path `P`, but no file exists at `~/vault/P`.
**Source**: `project_indexes`.

```
for each project_index in project_indexes:
  for each path in (project_index.related_notes + project_index.absorbs):
    if ~/vault/{path} does not exist:
      → broken_project_to_note
```

**False-positive guard**: Path matching is case-insensitive. Notes in subdirectories of `30_Notes/` are resolved by full path, not stem. If both `related_notes` and `absorbs` are absent or empty, no E6 findings are generated.

## E7 — `missing_back_reference` [Warning]

**Rule**: `_index.md` lists a note path `P` in `related_notes` or `absorbs`, the note at `P` exists, but the note does NOT have either `promoted_to_project == <project_name>` OR `<project_name>` in `also_related_projects`.
**Source**: `project_indexes`, `note_projects`.

```
for each project_index in project_indexes:
  project_name = directory name of project_index (e.g., "alpha")
  for each path in (project_index.related_notes + project_index.absorbs):
    if ~/vault/{path} exists:
      note = note_projects[path]
      back_linked = (note.promoted_to_project == project_name)
                    OR (project_name in note.also_related_projects)
      if NOT back_linked:
        → missing_back_reference
```

**Auto-fix**: Append `project_name` to `also_related_projects` in the note's frontmatter. Do NOT overwrite `promoted_to_project`.
**False-positive guard**: Only flag when the note actually exists (no double-flag with E6). Do NOT fire if `promoted_to_project == project_name` OR `project_name in also_related_projects` — either field satisfies the back-reference.

## E8 — `broken_note_to_project` [Critical]

**Rule**: A note in `30_Notes/` has a `promoted_to_project: <name>` field OR contains `<name>` in `also_related_projects`, but `~/vault/20_Projects/<name>/_index.md` does NOT exist. Each broken project reference is one E8 finding (a note with both a broken `promoted_to_project` and a broken entry in `also_related_projects` generates two E8 findings).
**Source**: `note_projects`.

```
for each note_path in note_projects:
  note = note_projects[note_path]
  candidates = []
  if note.promoted_to_project is not None:
    candidates.append(note.promoted_to_project)
  candidates.extend(note.also_related_projects)
  for project_name in candidates:
    if ~/vault/20_Projects/{project_name}/_index.md does not exist:
      → broken_note_to_project (one finding per missing project_name)
```

## Derived check — `missing_forward_reference` [Warning]

**Rule**: A note in `30_Notes/` claims a project via `promoted_to_project` or `also_related_projects`, the project `_index.md` exists, but the project does NOT list this note's vault-relative path in its `related_notes` OR `absorbs` field.
**Source**: `project_indexes`, `note_projects`.

```
for each note_path in note_projects:
  note = note_projects[note_path]
  candidates = []
  if note.promoted_to_project is not None:
    candidates.append(note.promoted_to_project)
  candidates.extend(note.also_related_projects)
  for project_name in candidates:
    index_path = 20_Projects/{project_name}/_index.md
    if index_path exists:
      project = project_indexes[project_name]
      note_relpath = vault-relative path of note_path (e.g. "30_Notes/foo.md")
      if note_relpath not in (project.related_notes + project.absorbs) (case-insensitive):
        → missing_forward_reference
```

**False-positive guard**: Only flag when both the note and the project `_index.md` exist (no double-flag with E8 or E6).

## Auto-fix eligibility

Only the following are mutated by Phase 4 OPTIONAL-FIX (frontmatter-only edits):

| Type | Auto-fix action |
|------|-----------------|
| `missing_required_fields` (E2) | Add missing `tags`, `type`, `created` fields with inferred values |
| `missing_back_reference` (E7) | Append `<project_name>` to note's `also_related_projects` array |
| `missing_forward_reference` (derived) | Append note's vault-relative path to project's `related_notes` |

Never auto-fixed: E1 (body unknown), E3 (rename affects inbound links), E4 (needs human decision), E5 (content value judgment), E6 (cannot create note stub), E8 (project may not exist).

## Spec → implementation mapping

The W2 DoD lists 8 error type names. Mapping used here:

| Spec name | Implementation type |
|-----------|---------------------|
| `orphan_note` | E5 |
| `broken_wikilink` | E4 |
| `filename_convention_violation` | E3 |
| `missing frontmatter` | E1 + E2 (file-level + field-level, both Critical) |
| `broken_project_to_note` | E6 |
| `missing_back_reference` | E7 |
| `broken_note_to_project` | E8 |
| `missing_forward_reference` | derived from E7/E8 pair |

For DoD counting, E1 and E2 are reported as separate sub-types of the same category (`missing frontmatter`).
