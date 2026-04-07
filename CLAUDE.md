# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 두 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 6개 + 에이전트 1개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, thought-chain + thinking-facilitator agent)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 (vault-knowledge-manager, vault-file-organizer) + 스킬 8개 (capture, note, project, inbox-review, wrapup, context, archive, vault-daily)
- **vault-reader** (`vault-reader/`): Obsidian vault I/O 서빙 플러그인 — 에이전트 1개 (vault-searcher, haiku). vault 검색 + handoff 생성.

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
- **Agent instructions** (agents/*.md body): Korean (사용자 대면 라우팅 로직) + English frontmatter

### obsidian-vault-manager

- **Skill instructions** (SKILL.md body): Korean (사용자 대면 vault 관리 도메인)
- **Agent instructions**: Korean body + English frontmatter
- **Metadata** (frontmatter keys): English 유지

## Directory Structure

```
claude-kit/                              # marketplace repo (Lyainc-claude-kit)
├── .claude-plugin/
│   └── marketplace.json                 # 마켓플레이스 매니페스트 (플러그인 목록 + source 경로)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── thinking-tools/                      # plugin: thinking-tools
│   ├── .claude-plugin/plugin.json       # 플러그인 매니페스트
│   ├── skills/                          # 스킬 디렉토리 (SKILL.md 기반 자동 검색)
│   ├── agents/                          # 에이전트 디렉토리 (thinking-facilitator)
│   ├── reference/
│   └── docs/
├── obsidian-vault-manager/              # plugin: obsidian-vault-manager
│   ├── .claude-plugin/plugin.json
│   ├── skills/
│   └── agents/
├── vault-reader/                        # plugin: vault-reader
│   ├── .claude-plugin/plugin.json
│   └── agents/                          # 에이전트 디렉토리 (vault-searcher)
├── CLAUDE.md
└── README.md
```

## Marketplace Structure

- `marketplace.json`: 전체 플러그인 목록. 각 항목의 `source` 필드가 플러그인 루트 경로
- `plugin.json`: 개별 플러그인 메타데이터 (name, version, keywords)
- `skills/*/SKILL.md`: Claude Code가 자동 검색하는 스킬 정의 파일
- `agents/*.md`: 에이전트 정의 파일 (두 플러그인 모두 보유)

## Validation

```bash
# JSON 유효성 검사
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null

# 스킬 파일 존재 확인
find thinking-tools/skills -name "SKILL.md" | sort
find obsidian-vault-manager/skills -name "SKILL.md" | sort
```

## SKILL.md Frontmatter

```yaml
---
name: skill-name              # 필수: kebab-case
description: "한 줄 설명"       # 필수: 스킬 용도 + 사용 예시
allowed-tools: Read Write Bash  # 필수: 스킬이 사용하는 도구 목록
# context: fork                # 선택: fork 시 별도 에이전트에서 실행
# agent: Explore               # 선택: fork 시 사용할 에이전트 타입
---
```

## Adding a New Skill

1. 해당 플러그인의 `skills/{skill-name}/SKILL.md` 생성
2. `plugin.json`의 `keywords`에 스킬명 추가
3. 상위 `marketplace.json`의 해당 플러그인 항목 버전 범프
4. 에이전트가 해당 스킬을 사용해야 하면: 에이전트 `.md`의 `skills:` frontmatter에 추가

## Adding a New Agent

1. 해당 플러그인의 `agents/{agent-name}.md` 생성 (frontmatter: name, description, model, skills)
2. `plugin.json`의 `keywords`에 에이전트명 추가
3. 상위 `marketplace.json`의 해당 플러그인 항목 버전 범프

## Version Sync Rule

`plugin.json`과 `marketplace.json`의 다음 필드는 항상 동기화:
- `version`: 양쪽 동일하게 범프
- `description`: 양쪽 동일한 문자열 유지
- `keywords`: 양쪽 동일한 배열 유지

## Adding a New Plugin

1. `{plugin-name}/` 디렉토리 생성
2. `{plugin-name}/.claude-plugin/plugin.json` 작성
3. `{plugin-name}/skills/` 하위에 스킬 추가
4. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목 추가 (`source` 경로 지정)
5. `{plugin-name}/README.md` 작성
6. 루트 `README.md`에 플러그인 소개 추가
