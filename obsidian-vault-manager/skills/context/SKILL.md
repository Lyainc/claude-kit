---
name: context
description: "Load existing notes and context for a specific domain. Example: '/context kubernetes', '/context devops,kubernetes --exclude private'"
allowed-tools: Read Bash Glob Grep
context: fork
agent: Explore
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Load context for the `$ARGUMENTS` domain.

## Procedure

1. Read `~/vault/10_MOC/$ARGUMENTS.md` (or a similarly named file).
   - If no MOC exists, search based on platform:
     - macOS (`uname -s` = `Darwin`): `mdfind -onlyin ~/vault "$ARGUMENTS"`
     - Other: `grep -rl "$ARGUMENTS" ~/vault --include="*.md"`
   - **Cross-domain**: If `$ARGUMENTS` contains a comma (e.g., `devops,kubernetes`), query each domain individually and merge the results.
2. Collect the titles and tags of notes linked in the MOC.
3. If there are handoff notes with `status: active` in the domain, display them first under a "Work in Progress" section.
4. Prioritize recently modified related notes.
5. Format and output the results:
   ```
   ## {domain} Domain Context

   ### Work in Progress
   - handoff-2025-01-15.md — {current status summary}

   ### MOC: 10_MOC/{domain}.md
   - N notes linked

   ### Related Notes (most recently modified)
   1. note-a.md — 2025-01-15
   2. note-b.md — 2025-01-10

   무엇을 작업할까요?
   ```

## Rules

- This is a read-only operation; do not modify any files.

## Options

| Option | Description | Example |
|--------|-------------|---------|
| `--exclude {tag}` | Exclude notes with the specified tag | `/context kubernetes --exclude private` |
| `--limit N` | Maximum number of notes to display (positive integer, default: 20) | `/context devops --limit 10` |

**Validation**: `--limit` accepts positive integers only (0 or below / non-numeric → use default of 20). If `--exclude` specifies a tag that does not exist, ignore it and continue.
