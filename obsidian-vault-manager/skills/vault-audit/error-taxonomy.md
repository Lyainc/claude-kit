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
- Notes referenced by a project's `related_notes` or `absorbs` frontmatter field count as having one inbound reference (even if no explicit `[[...]]` link exists in the `_index.md` body).

---

## E6 — `broken_project_to_note`

**Severity**: Critical

**Definition**: A project `_index.md` has a `related_notes` or `absorbs` frontmatter field listing a vault-relative path, but no file exists at that path.

**Detection rule**:
```
For each project_index in project_indexes:
  for each path in (project_index.related_notes + project_index.absorbs):
    if ~/vault/{path} does not exist (case-insensitive):
      → broken_project_to_note
```

**Example**:
```yaml
# 20_Projects/alpha/_index.md
related_notes:
  - 30_Notes/audit-e6-ghost-001.md
  - 30_Notes/alpha-decisions.md
absorbs:
  - 30_Notes/api-redesign.md
```
`30_Notes/audit-e6-ghost-001.md` does not exist → broken (one E6 finding).

**Auto-fix eligible**: No — a missing note cannot be created automatically (content is unknown).

**False-positive guard**:
- Case-insensitive path matching.
- Notes in subdirectories of `30_Notes/` are resolved by full vault-relative path, not just stem.
- If both `related_notes` and `absorbs` are absent or empty, no E6 findings are generated for that project.

---

## E7 — `missing_back_reference`

**Severity**: Warning

**Definition**: A project `_index.md` lists a note path in `related_notes` or `absorbs`, the note exists, but the note does NOT have either `promoted_to_project: <project_name>` OR `<project_name>` in `also_related_projects`.

**Detection rule**:
```
For each project_index in project_indexes:
  project_name = directory name of project_index.path (e.g., "alpha")
  for each path in (project_index.related_notes + project_index.absorbs):
    note_path = ~/vault/{path}
    if note_path exists:
      note = note_projects[path]
      back_linked = (note.promoted_to_project == project_name)
                    OR (project_name in note.also_related_projects)
      if NOT back_linked:
        → missing_back_reference
```

**Example**:
```yaml
# 30_Notes/alpha-architecture.md
created: 2026-04-01
tags: [note]
type: note
# missing: promoted_to_project: alpha  OR  also_related_projects: [alpha]
```

**Auto-fix eligible**: Yes — append `<project_name>` to `also_related_projects` in note frontmatter. Creates the field as `also_related_projects: [<name>]` if absent. Never overwrites `promoted_to_project`.

**False-positive guard**:
- Only flag when the note actually exists (no double-flag with E6).
- Do NOT fire if `promoted_to_project == project_name` — primary promotion satisfies the back-reference.
- Do NOT fire if `project_name in also_related_projects` — secondary relation also satisfies.
- Both fields are optional; absence of both is required to trigger E7.

---

## E8 — `broken_note_to_project`

**Severity**: Critical

**Definition**: A note in `30_Notes/` has a `promoted_to_project: <name>` field OR contains `<name>` in `also_related_projects`, but `~/vault/20_Projects/<name>/_index.md` does NOT exist. Each broken project reference generates one E8 finding.

**Detection rule**:
```
For each note_path in note_projects:
  note = note_projects[note_path]
  candidates = []
  if note.promoted_to_project is not None:
    candidates.append(note.promoted_to_project)
  candidates.extend(note.also_related_projects)
  for project_name in candidates:
    if ~/vault/20_Projects/{project_name}/_index.md does not exist:
      → broken_note_to_project (one finding per missing project_name)
```

**Example**:
```yaml
# 30_Notes/orphaned-note.md
promoted_to_project: deleted-project
also_related_projects: [also-gone]
```
Both `20_Projects/deleted-project/_index.md` and `20_Projects/also-gone/_index.md` are missing → two E8 findings.

**Auto-fix eligible**: No — the project may have been renamed or deleted; correct action is ambiguous.

**False-positive guard**:
- Case-insensitive directory name matching.
- If `promoted_to_project` is present but empty string, skip (not a broken reference).
- Empty or absent `also_related_projects` array produces no E8 findings from that field.
- Check for `_index.md` specifically, not just the directory — a project directory without an `_index.md` is also broken.

---

## Derived — `missing_forward_reference`

**Severity**: Warning

**Definition**: A note in `30_Notes/` claims a project via `promoted_to_project` or `also_related_projects`, the project `_index.md` exists, but the project does NOT list this note's vault-relative path in its `related_notes` OR `absorbs` field.

This is the mirror of E7: E7 = project knows note but note doesn't know project; `missing_forward_reference` = note knows project but project doesn't know note.

**Detection rule**:
```
For each note_path in note_projects:
  note = note_projects[note_path]
  candidates = []
  if note.promoted_to_project is not None:
    candidates.append(note.promoted_to_project)
  candidates.extend(note.also_related_projects)
  for project_name in candidates:
    index_path = 20_Projects/{project_name}/_index.md
    if index_path exists:
      project = project_indexes[project_name]
      note_relpath = vault-relative path of note (e.g. "30_Notes/foo.md")
      if note_relpath not in (project.related_notes + project.absorbs) (case-insensitive):
        → missing_forward_reference
```

**Auto-fix eligible**: Yes — append vault-relative note path to `related_notes` list in the project `_index.md`. Frontmatter-only edit. Creates the field as an array if absent.

**False-positive guard**:
- Only flag when both the note and the project `_index.md` exist (no double-flag with E8 or E6).
- If the note path appears in `absorbs` (not `related_notes`), it still counts as a forward link — do NOT fire.
- If both `related_notes` and `absorbs` are absent from `_index.md`, treat as empty (flag applies).

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
