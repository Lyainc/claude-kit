# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 두 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 6개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, dev-wrap)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 + 스킬 6개

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **PR descriptions**: Korean
- **Branches**: `feature/`, `fix/`, `docs/`, `refactor/` prefixes

## Language Policy

### thinking-tools

- **Skill instructions** (SKILL.md body, reference.md): English for LLM-optimized parsing
- **Skill output/examples** (examples.md, templates): Korean (primary user language)
- **Metadata** (frontmatter, section headers): English 유지
- **테이블 헤더**: 한국어 우선, 기술 용어는 영어 원문 유지

### obsidian-vault-manager

- **Skill instructions** (SKILL.md body): Korean (사용자 대면 vault 관리 도메인)
- **Agent instructions**: Korean body + English frontmatter
- **Metadata** (frontmatter keys): English 유지
