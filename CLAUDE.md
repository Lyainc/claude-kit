# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code skills plugin providing 4 productivity skills (diverse-sampling, doc-concretize, expert-panel, unknown-discovery).

## Commands

```bash
# Validate skills/agents before committing
./scripts/validate-templates.sh           # Validate all
./scripts/validate-templates.sh --skills  # Skills only
./scripts/validate-templates.sh --agents  # Agents only

# Setup pre-commit hooks (optional)
./scripts/setup-hooks.sh
```

## Validation Levels

- **ERROR**: Blocks execution - missing `name` or `description` fields
- **WARN**: Advisory - naming conventions, length limits, directory/name mismatch

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **PR descriptions**: Korean
- **Branches**: `feature/`, `fix/`, `docs/`, `refactor/` prefixes
