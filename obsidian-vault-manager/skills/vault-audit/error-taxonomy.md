# Vault Audit Error Taxonomy

8 error types for the vault-audit skill. Each entry defines: detection rule, severity, example, auto-fix eligibility, and false-positive guard.

Source of truth: W2 DoD in `project-2026-04-13-vault-audit-plan.md` + `project-2026-04-16-master-plan.md` §3 W2.

---

## E1 — `missing_frontmatter`

**Severity**: Critical

**Definition**: A `.md` file has no YAML frontmatter block at all (no opening `---` delimiter).

**Detection rule**:
```
scan-frontmatter output: has_frontmatter == false
```

**Example**:
```markdown
# My Note

Content without any frontmatter.
```

**Auto-fix eligible**: No — body structure is unknown; inserting a frontmatter block could conflict with existing H1 or document structure. Requires human review.

**False-positive guard**:
- Skip files under `.ovm/`, `.obsidian/`, and any path starting with `.` (hidden dirs).
- Skip non-content stubs that are intentionally frontmatter-free (e.g., `README.md` at vault root).

---

## E2 — `missing_required_fields`

**Severity**: Critical

**Definition**: A `.md` file has a frontmatter block but is missing one or more of the three required fields: `created`, `tags`, `type`.

**Detection rule**:
```
scan-frontmatter output: has_frontmatter == true AND missing_required is non-empty
```

**Example**:
```yaml
---
created: 2026-04-01
---
```
Missing: `tags`, `type`.

**Auto-fix eligible**: Yes — the missing fields can be inferred or set to safe defaults:
- `created`: infer from filename date segment or file mtime.
- `tags`: default to `[]` (empty list; user should populate later).
- `type`: infer from file location (`30_Notes/` → `note`, `00_Inbox/` → `capture`, `20_Projects/*/` → `plan` or `session`).

**False-positive guard**:
- `_index.md` files have a different required field set (`status` is also required); do not flag `_index.md` for missing `type` alone since their type is always `project` and can be auto-inferred.
- Files in `.ovm/` are excluded.

---

## E3 — `filename_convention_violation`

**Severity**: Warning

**Definition**: A `.md` filename does not conform to the vault naming convention:
- `session`, `capture`, `plan`: `{type}-YYYY-MM-DD[-{topic}][-vN].md`
- `note`: `{topic-kebab}.md` (flat, no date prefix, all lowercase)
- `project`: `_index.md` (fixed name)

**Detection rule**:
```
scan-filename output: conforms == false
```

**Example**:
```
30_Notes/2026-04-bad-name-001.md    # dated prefix on a note
30_Notes/My Note with Spaces.md     # uppercase + spaces
```

**Auto-fix eligible**: No — renaming a file invalidates all inbound wikilinks. A separate `--rename` workflow (not this skill) handles safe renames with link-update. Flag only.

**False-positive guard**:
- `_index.md` is always `conforms: true` by scan-filename; never flagged.
- Files with `.md` extension that are not vault content (e.g., `README.md` in vault root) should be excluded if they match a known exception list.
- Do not flag filenames in `00_Inbox/` that are temporary/draft only when `--strict` flag is absent (drafts may have non-standard names before first review).

---

## E4 — `broken_wikilink`

**Severity**: Critical

**Definition**: A file contains a `[[target]]` wikilink where no file exists in the vault with a matching stem (case-insensitive).

**Detection rule**:
```
For each link in extract-wikilinks output:
  stem = target (strip path separators, heading anchors #..., block refs #^...)
  if no file in vault_file_index has stem == link.target (case-insensitive):
    → broken_wikilink
```

**Example**:
```markdown
Points to [[totally-nonexistent-note]] and [[also-missing]].
```

**Auto-fix eligible**: No — the correct target is ambiguous (renamed, deleted, or typo). Requires human decision.

**False-positive guard**:
- Ignore `![[image.png]]` embed links where the extension is not `.md` (images, PDFs, etc.).
- Ignore links with heading/block anchors when the base file exists: `[[existing-note#section]]` is valid even if the heading no longer exists.
- Case-insensitive stem matching: `[[API Design]]` matches `api-design.md` (Obsidian resolves case-insensitively).
- Aliases do not affect target resolution: `[[target|display text]]` → resolve `target`.

---

## E5 — `orphan_note`

**Severity**: Warning

**Definition**: A note in `30_Notes/` has zero inbound wikilinks from any other file in the vault.

**Detection rule**:
```
Build inbound_links: { stem → [source_files] } from all extract-wikilinks outputs across full vault.
For each file in 30_Notes/:
  stem = filename without .md extension
  if stem not in inbound_links OR inbound_links[stem] is empty:
    → orphan_note
```

**Example**: `30_Notes/orphan-001.md` — no other file contains `[[orphan-001]]`.

**Auto-fix eligible**: No — whether a note should be linked or deleted is a content decision.

**False-positive guard**:
- `_index.md` files are never orphans (they are the root of a project, not expected to be linked).
- Files in `00_Inbox/` are exempt — inbox items are unprocessed and not yet linked.
- A note linked only from itself (self-link) counts as having zero external inbound links.
- Notes referenced by a project's `linked_notes` frontmatter field count as having one inbound reference (even if no explicit `[[...]]` link exists in the `_index.md` body).

---

## E6 — `broken_project_to_note`

**Severity**: Critical

**Definition**: A project `_index.md` has a `linked_notes` frontmatter field listing a note stem, but no file with that stem exists in `30_Notes/`.

**Detection rule**:
```
For each project_index in project_indexes:
  for each stem in project_index.linked_notes:
    if no file exists at 30_Notes/{stem}.md (case-insensitive):
      → broken_project_to_note
```

**Example**:
```yaml
# 20_Projects/alpha/_index.md
linked_notes: [alpha-architecture, alpha-decisions, nonexistent-note]
```
`30_Notes/nonexistent-note.md` does not exist → broken.

**Auto-fix eligible**: No — a missing note cannot be created automatically (content is unknown).

**False-positive guard**:
- Case-insensitive stem matching.
- Notes in subdirectories of `30_Notes/` are resolved by walking the directory tree, not just the flat root.
- If `linked_notes` field is absent or empty, no E6 findings are generated for that project.

---

## E7 — `missing_back_reference`

**Severity**: Warning

**Definition**: A project `_index.md` lists a note stem in `linked_notes`, the note exists, but the note does NOT have a `project:` frontmatter field pointing back to this project.

**Detection rule**:
```
For each project_index in project_indexes:
  project_name = directory name of project_index.path (e.g., "alpha")
  for each stem in project_index.linked_notes:
    note_path = 30_Notes/{stem}.md
    if note_path exists:
      note_project_field = note_projects[note_path]
      if note_project_field is None OR note_project_field != project_name:
        → missing_back_reference
```

**Example**:
```yaml
# 30_Notes/alpha-architecture.md
created: 2026-04-01
tags: [note]
type: note
# missing: project: alpha
```

**Auto-fix eligible**: Yes — add `project: <name>` to note frontmatter. Only touches the frontmatter block; body is unchanged.

**False-positive guard**:
- Only flag when the note actually exists (no double-flag with E6).
- If `project:` field exists but points to a different project, flag as E8 (`broken_note_to_project`) instead, not E7.
- Notes may legitimately belong to multiple projects; if `also_related_projects` field is used, check both `project:` and `also_related_projects` before flagging.

---

## E8 — `broken_note_to_project`

**Severity**: Critical

**Definition**: A note in `30_Notes/` has a `project:` frontmatter field, but the referenced project directory (`~/vault/20_Projects/<value>/`) does not contain an `_index.md`.

**Detection rule**:
```
For each note_path in note_projects:
  project_name = note_projects[note_path]
  if project_name is not None:
    index_path = 20_Projects/{project_name}/_index.md
    if index_path does not exist in vault:
      → broken_note_to_project
```

**Example**:
```yaml
# 30_Notes/orphaned-note.md
project: deleted-project
```
`20_Projects/deleted-project/_index.md` does not exist → broken.

**Auto-fix eligible**: No — the project may have been renamed or deleted; correct action is ambiguous.

**False-positive guard**:
- Case-insensitive directory name matching.
- If `project:` field is present but empty string, skip (not a broken reference).
- Check for `_index.md` specifically, not just the directory — a project directory without an `_index.md` is also broken.

---

## Derived — `missing_forward_reference`

**Severity**: Warning

**Definition**: A note in `30_Notes/` has a `project: <name>` field pointing to an existing project, but the project's `_index.md` does NOT list this note's stem in its `linked_notes` field.

This is the mirror of E7: E7 = project knows note but note doesn't know project; `missing_forward_reference` = note knows project but project doesn't know note.

**Detection rule**:
```
For each note_path in note_projects:
  project_name = note_projects[note_path]
  if project_name is not None:
    index_path = 20_Projects/{project_name}/_index.md
    if index_path exists:
      project_linked = project_indexes[project_name].linked_notes
      note_stem = stem(note_path)
      if note_stem not in project_linked (case-insensitive):
        → missing_forward_reference
```

**Auto-fix eligible**: Yes — append note stem to `linked_notes` list in the project `_index.md`. Frontmatter-only edit.

**False-positive guard**:
- Only flag when both the note and the project `_index.md` exist (no double-flag with E8 or E6).
- If `linked_notes` is absent from `_index.md`, treat as empty list (flag applies).

---

## Severity Summary

| Error type | Severity | Auto-fix |
|---|---|---|
| `missing_frontmatter` | Critical | No |
| `missing_required_fields` | Critical | Yes |
| `broken_wikilink` | Critical | No |
| `broken_project_to_note` | Critical | No |
| `broken_note_to_project` | Critical | No |
| `filename_convention_violation` | Warning | No |
| `orphan_note` | Warning | No |
| `missing_back_reference` | Warning | Yes |
| `missing_forward_reference` | Warning | Yes |

Severity levels follow the spec:
- **Critical**: data integrity risk — broken references, missing structure
- **Warning**: quality/navigation risk — isolated notes, convention drift
- **Info**: not currently assigned to any error type in this taxonomy
