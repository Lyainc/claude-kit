# CLAUDE.md (for claude-kit contributors)

This file provides guidance to Claude Code when **developing/contributing to this repository**. Runtime behavior rules (how Claude should act when these plugins are active in external projects) live in each plugin's agent/skill `description` fields, which are the single source of truth for runtime delegation.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 세 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 6개 + 에이전트 1개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, thought-chain + thinking-facilitator agent)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 (vault-knowledge-manager, vault-file-organizer) + 스킬 6개 (capture, note, project, inbox-review, context, archive)
- **vault-reader** (`vault-reader/`): Obsidian vault I/O 서빙 플러그인 — 에이전트 1개 (vault-searcher, haiku) + 훅 2개 (Stop, SessionEnd). vault 검색 + session-note 4-mode 생성 + 세션 생명주기 안전망.

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **PR descriptions**: Korean
- **Branches**: `feature/`, `fix/`, `docs/`, `refactor/` prefixes

## Language Policy

All plugins (thinking-tools, obsidian-vault-manager, vault-reader) follow a unified policy:

- **Skill instructions** (SKILL.md body): English for LLM-optimized parsing
- **Agent instructions** (agents/*.md body): English for LLM-optimized parsing
- **Metadata** (frontmatter keys, section headers): English
- **User-facing output**: Korean (each file contains a Korean I/O directive)
- **README descriptions**: English by default (consistent with skill/agent body)
- **README trigger examples**: Korean OK (user-facing trigger phrases)
- **Reference docs / examples** (`reference/`, `examples.md`): Korean (user-facing content)
- **Korean text in templates/examples** representing actual vault content: preserved as Korean

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
python3 -m json.tool vault-reader/.claude-plugin/plugin.json > /dev/null

# 스킬 파일 존재 확인
find thinking-tools/skills -name "SKILL.md" | sort
find obsidian-vault-manager/skills -name "SKILL.md" | sort
```

## SKILL.md Frontmatter

```yaml
---
name: skill-name              # 필수: kebab-case
description: "One-line summary"  # Required: skill purpose + usage example
allowed-tools: Read Write Bash  # 필수: 스킬이 사용하는 도구 목록
# context: fork                # 선택: fork 시 별도 에이전트에서 실행
# agent: Explore               # 선택: fork 시 사용할 에이전트 타입
---
```

## Vault File Conventions

Files written to `~/vault/` by OVM or vault-reader follow a unified convention.

**Filename**: `{type}-YYYY-MM-DD[-{topic}][-vN].md` (type-first)

| Type | Example | Path |
|------|---------|------|
| `session` | `session-2026-04-12.md` | `00_Inbox/` or `20_Projects/{name}/` |
| `capture` | `capture-2026-04-12-api-changes.md` | `00_Inbox/` |
| `note` | `{topic}.md` (no date) | `30_Notes/` |
| `project` | `_index.md` (fixed) | `20_Projects/{name}/` |

Same-date collisions: `-v2`, `-v3` increment.

**Frontmatter standard**:
```yaml
created: YYYY-MM-DD            # required, all files
tags: [{type}, {domain}]       # required
type: session|capture|note|project  # required
status: active|archived        # conditional (session-handoff, project)
```

## Session-Note Hooks (vault-reader)

vault-reader registers two hooks plus one slash command for the session-note workflow:

- **Stop** (`hooks/stop-check.sh`, deterministic shell script): per-turn. Reads transcript JSONL, regex-matches the last user text against closing keywords (`세션 끝`, `마무리`, `wrap up`, `end session`, etc.), and emits a `systemMessage` suggesting `/save-session` only on match. **No LLM call** → no per-turn cost and no infinite-loop risk (the prior prompt-based hook caused a loop because every LLM response, even "(silent pass-through)", re-fired the Stop hook).
- **SessionEnd** (prompt-based): session close. Auto-saves quick-mode session-note as safety net if meaningful work happened without manual save. No user interaction (session already closing).
- **`/save-session`** (slash command): explicit user trigger to invoke vault-searcher Mode 4 with full mode selection (record/handoff/quick).

The split (deterministic Stop + prompt SessionEnd + explicit slash command) ensures: zero per-turn LLM cost, no loops, safety-net auto-save on `/exit`, and a clear user-driven path for full session notes.

## Cross-Plugin MECE Boundaries

Skills across `obsidian-vault-manager` and `vault-reader` share overlapping domains. Boundaries:

| Area | obsidian-vault-manager | vault-reader |
|------|----------------------|--------------|
| Domain context load | `context` skill (internal, `--exclude`/`--limit` options) | `vault-searcher` Mode 2 (external, read-only lightweight) |
| Session record | N/A (use vault-reader's session-note) | `vault-searcher` Mode 4: Session Note Creation (record/handoff/quick modes) |
| Note creation logic | `note` skill owns domain determination + MOC linking | `inbox-review` delegates to `note` skill procedure |

Within `thinking-tools`:
- `diverse-sampling`: creative generation (brainstorming, alternatives)
- `expert-panel`: evaluative debate (multi-perspective assessment, decision-making)
- Trigger "여러 관점" → `expert-panel` only (evaluative, not creative)

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
