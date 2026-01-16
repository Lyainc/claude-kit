# Development Guide

This file provides guidance for developers working on this repository.

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
├── .claude-plugin/
│   ├── plugin.json              # Plugin metadata (required)
│   └── marketplace.json         # Marketplace catalog (required for GitHub distribution)
├── skills/                      # Skills (folder-based, SKILL.md required)
├── commands/                    # Slash commands
├── agents/                      # Subagent definitions
├── output-styles/               # Output styles
├── modules/                     # @import modules
├── characters/                  # Character definitions
├── CLAUDE.md                    # Plugin user instructions
├── CLAUDE-PLATFORM-SETTINGS.md  # Platform (Web/macOS) settings guide
├── scripts/                     # Dev tools (validate-templates.sh, setup-hooks.sh)
└── docs/                        # Documentation and archives
```

## Component Requirements

### Skill (folder-based)

| Field         | Requirement                                    |
| ------------- | ---------------------------------------------- |
| Location      | `skills/{name}/SKILL.md`                       |
| `name`        | Required. Lowercase/numbers/hyphens, ≤64 chars |
| `description` | Required. ≤1024 chars, "Use when..." pattern   |
| References    | 1-level depth only                             |

### Agent (file-based)

| Field         | Requirement                                            |
| ------------- | ------------------------------------------------------ |
| Location      | `agents/{name}.md`                                     |
| `name`        | Required                                               |
| `description` | Required. Include trigger keywords for auto-invocation |
| `model`       | Optional: sonnet, opus, haiku, inherit                 |

### Validation Levels

- **ERROR**: Blocks commit/CI - missing required fields (`name`, `description`)
- **WARN**: Advisory - naming conventions, length limits

## Adding Components

```bash
# Skill
cp -r skills/_TEMPLATE skills/{name}
vim skills/{name}/SKILL.md

# Agent
cp agents/_TEMPLATE.md agents/{name}.md

# Others (output-styles, commands, characters)
cp {type}/_TEMPLATE.md {type}/{name}.md
```

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- English for commits, Korean for PR descriptions
- CI runs `validate-templates.sh` on PRs touching plugin components
- Pre-commit hooks optional but recommended (`./scripts/setup-hooks.sh`)

## Hybrid Language Strategy

| Component                         | Language | Rationale                |
| --------------------------------- | -------- | ------------------------ |
| Core Rules, Verification, Never   | English  | LLM procedural alignment |
| Identity, tone, output directives | Korean   | Cultural nuance          |
