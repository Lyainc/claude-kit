# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code Plugin providing skills (diverse-sampling, doc-concretize, expert-panel, unknown-discovery, docx, pptx), agents, and modules.

## Commands

```bash
# Validate templates before committing
./scripts/validate-templates.sh           # Validate all
./scripts/validate-templates.sh --skills  # Skills only
./scripts/validate-templates.sh --agents  # Agents only

# Setup pre-commit hooks (optional)
./scripts/setup-hooks.sh                  # Auto-detect best method
```

## Architecture

```text
claude-kit/
├── .claude-plugin/plugin.json    # Plugin metadata (required)
├── template/                     # Plugin content (deployed to ~/.claude/)
│   ├── CLAUDE.md                 # Core instructions
│   ├── modules/                  # @import modules
│   ├── agents/                   # Subagent definitions
│   ├── skills/                   # Skills (folder-based, SKILL.md required)
│   ├── output-styles/            # Output styles
│   ├── commands/                 # Slash commands
│   └── characters/               # Character definitions
└── scripts/                      # Dev tools (validate-templates.sh, setup-hooks.sh)
```

## Template Requirements

### Skill (folder-based)

| Field         | Requirement                                        |
| ------------- | -------------------------------------------------- |
| Location      | `template/skills/{name}/SKILL.md`                  |
| `name`        | Required. Lowercase/numbers/hyphens, ≤64 chars     |
| `description` | Required. ≤1024 chars, "Use when..." pattern       |
| References    | 1-level depth only                                 |

### Agent (file-based)

| Field         | Requirement                                            |
| ------------- | ------------------------------------------------------ |
| Location      | `template/agents/{name}.md`                            |
| `name`        | Required                                               |
| `description` | Required. Include trigger keywords for auto-invocation |
| `model`       | Optional: sonnet, opus, haiku, inherit                 |

### Validation Levels

- **ERROR**: Blocks commit/CI - missing required fields (`name`, `description`)
- **WARN**: Advisory - naming conventions, length limits

## Adding Components

```bash
# Skill
cp -r template/skills/_TEMPLATE template/skills/{name}
vim template/skills/{name}/SKILL.md

# Agent
cp template/agents/_TEMPLATE.md template/agents/{name}.md

# Others (output-styles, commands, characters)
cp template/{type}/_TEMPLATE.md template/{type}/{name}.md
```

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- English for commits, Korean for PR descriptions
- CI runs `validate-templates.sh` on PRs touching `template/`
- Pre-commit hooks optional but recommended (`./scripts/setup-hooks.sh`)

## Hybrid Language Strategy

| Component                         | Language | Rationale                |
| --------------------------------- | -------- | ------------------------ |
| Core Rules, Verification, Never   | English  | LLM procedural alignment |
| Identity, tone, output directives | Korean   | Cultural nuance          |
