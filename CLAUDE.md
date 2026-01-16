# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code skills plugin providing 4 productivity skills (diverse-sampling, doc-concretize, expert-panel, unknown-discovery).

## Commands

```bash
# Validate templates before committing
./scripts/validate-templates.sh           # Validate all
./scripts/validate-templates.sh --skills  # Skills only

# Setup pre-commit hooks (optional)
./scripts/setup-hooks.sh
```

## Skill Structure

Each skill lives in `skills/{name}/` with `SKILL.md` as the entry point:

```yaml
---
name: skill-name          # lowercase/numbers/hyphens, ≤64 chars
description: |            # ≤1024 chars, "Use when..." pattern required
  What this skill does.
  Use when [scenario], or when the user mentions [trigger].
---
```

Supporting files: `reference.md` (detailed procedures), `examples.md` (usage examples).

## Adding a New Skill

```bash
cp -r skills/_TEMPLATE skills/{name}
# Edit skills/{name}/SKILL.md
./scripts/validate-templates.sh --skills
git commit -m "feat: add {name} skill"
```

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **PR descriptions**: Korean
- **Branches**: `feature/`, `fix/`, `docs/`, `refactor/` prefixes
