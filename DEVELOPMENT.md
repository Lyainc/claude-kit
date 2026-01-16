# Development Guide

This file provides guidance for developers working on this repository.

## Project Overview

**claude-kit**: Claude Code skills plugin providing 4 productivity skills.

## Commands

```bash
# Validate templates before committing
./scripts/validate-templates.sh           # Validate all
./scripts/validate-templates.sh --skills  # Skills only

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
│   ├── diverse-sampling/
│   ├── doc-concretize/
│   ├── expert-panel/
│   └── unknown-discovery/
├── agents/                      # Subagent definitions (reserved for future use)
├── scripts/                     # Dev tools (validate-templates.sh, setup-hooks.sh)
└── docs/                        # Documentation and archives
```

## Skill Requirements

| Field         | Requirement                                    |
| ------------- | ---------------------------------------------- |
| Location      | `skills/{name}/SKILL.md`                       |
| `name`        | Required. Lowercase/numbers/hyphens, ≤64 chars |
| `description` | Required. ≤1024 chars, "Use when..." pattern   |
| References    | 1-level depth only                             |

### Validation Levels

- **ERROR**: Blocks commit/CI - missing required fields (`name`, `description`)
- **WARN**: Advisory - naming conventions, length limits

## Adding a New Skill

```bash
# 1. Copy template
cp -r skills/_TEMPLATE skills/{name}

# 2. Edit skill definition
vim skills/{name}/SKILL.md

# 3. Validate
./scripts/validate-templates.sh --skills

# 4. Commit
git add skills/{name}
git commit -m "feat: add {name} skill"
```

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- English for commits, Korean for PR descriptions
- CI runs `validate-templates.sh` on PRs touching `skills/`
- Pre-commit hooks optional but recommended (`./scripts/setup-hooks.sh`)
