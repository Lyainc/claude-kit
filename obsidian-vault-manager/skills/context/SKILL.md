---
name: context
description: "Load existing notes and context for a specific domain. Example: '/context kubernetes', '/context devops,kubernetes --exclude private'"
allowed-tools: Read Bash Glob Grep
context: fork
agent: Explore
---

**User language: Korean.** All user-facing output (responses, generated content, file contents) MUST be in Korean.

Load context for the `$ARGUMENTS` domain.

## Scope

This skill is for use **within vault management sessions** (via `vault-knowledge-manager`). It provides advanced options (`--exclude`, `--limit`) for filtering results. For lightweight read-only access from external projects, use `vault-bridge`'s `vault-searcher` agent (Mode 2: Domain Context Load) instead.

## Procedure

1. Read `~/vault/10_MOC/$ARGUMENTS.md` (or a similarly named file).
   - Optional CLI path: follow the availability gate and timeout helper in `../../reference/obsidian-cli.md`. When the gate passes, `${OBSIDIAN_TO:+$OBSIDIAN_TO 10} obsidian read path="10_MOC/{domain}.md"` may be used for an exact MOC path, and `${OBSIDIAN_TO:+$OBSIDIAN_TO 10} obsidian search query="$ARGUMENTS" limit={N}` may be used for indexed search (add `path="{folder}"` when scoping to a subtree).
   - If no MOC exists or the CLI path is unavailable/fails/times out, search based on platform:
     - macOS (`uname -s` = `Darwin`): `mdfind -onlyin ~/vault "$ARGUMENTS"`
     - Other: `grep -rl "$ARGUMENTS" ~/vault --include="*.md"`
   - **Cross-domain**: If `$ARGUMENTS` contains a comma (e.g., `devops,kubernetes`), query each domain individually and merge the results.
2. Collect the titles and tags of notes linked in the MOC.
3. If there are handoff notes with `status: active` in the domain, display them first under a "Work in Progress" section.
4. Prioritize recently modified related notes.
5. Format and output the results:
   ```
   ## {domain} 도메인 맥락

   ### 진행 중인 작업
   - handoff-2025-01-15.md — {현재 상태 요약}

   ### MOC: 10_MOC/{domain}.md
   - N개 노트 연결

   ### 관련 노트 (최근 수정순)
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
