@AGENTS.md

# Claude Code contributor adapter

Shared repository rules are in AGENTS.md. The import also supports sessions without the
builtin AGENTS.md loader; supported loaders deduplicate that same file.

Claude agent definitions use `agents/*.md`; model aliases and `allowed-tools`/`tools` fields
are Claude mechanics. When editing those definitions or skill effort, read
`docs/contributor-authoring.md` → SKILL.md Frontmatter / Adding a New Skill / Adding a New Agent.
Check hook behavior in Claude itself; a passing Codex check does not exercise a Claude hook.
Do not put personal model routing or global persona preferences in this public repository.
