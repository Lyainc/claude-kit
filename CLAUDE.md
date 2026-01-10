# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code 글로벌 설정 키트. `template/` 디렉토리의 설정 파일을 `~/.claude/`에 설치.

## Commands

```bash
# Interactive mode
./setup-claude-global.sh

# Direct modes
./setup-claude-global.sh install      # First installation
./setup-claude-global.sh update       # Update (add new files only)
./setup-claude-global.sh reset        # Reset (backup and replace all)

# Options
./setup-claude-global.sh update --dry-run     # Preview changes
./setup-claude-global.sh reset --show-diff    # Show diff
./setup-claude-global.sh update --cleanup     # Remove orphaned files
```

**Mode Behaviors**:

- **install**: First-time setup. Fails if any files exist (prevents accidental overwrites).
- **update**: Adds new files only. Keeps existing files (user customizations preserved).
- **reset**: Backup and replace all files (clean slate).

**Edge Case Handling**:

- File hash comparison for change detection
- CLAUDE.md reference validation (fails if modules missing)
- Atomic folder operations for skills/agents
- Orphaned file detection (use `--cleanup` to remove)
- `_TEMPLATE` patterns automatically excluded

## Architecture

### Directory Structure

```text
claude-kit/
├── template/                  # 배포 원본 (live) → ~/.claude/로 복사됨
│   ├── CLAUDE.md              # 핵심 설정
│   ├── modules/               # @import로 로드되는 모듈
│   ├── agents/                # 서브에이전트 정의
│   ├── skills/                # 스킬 (폴더 단위)
│   ├── output-styles/         # 출력 스타일
│   ├── commands/              # 슬래시 커맨드
│   └── characters/            # 캐릭터 정의 (SSOT)
├── docs/                      # 분석/참조 문서 (archive)
├── setup-claude-global.sh     # 설치 스크립트
└── README.md
```

### Hybrid Language Strategy

| 구성요소                        | 언어   | 근거                         |
|---------------------------------|--------|------------------------------|
| Core Rules, Verification, Never | 영어   | LLM 절차적 정렬에 최적화     |
| Identity, 톤, 출력 지시         | 한국어 | 문화적 뉘앙스 및 응답 일관성 |

## Development Workflow

1. `template/` 내 파일 수정
2. `./setup-claude-global.sh` 실행하여 `~/.claude/`에 배포
3. Claude Code 재시작하여 테스트

## Git Workflow

**Automation First**: Use scripts for safety and consistency.

### Starting New Work

```bash
# Recommended: Timestamp-based branches
./scripts/new-branch.sh feature add-new-skill
./scripts/new-branch.sh fix typo-in-readme

# Creates: feature/YYYYMMDD-HHMM-description
```

**Direct commits OK for**: Typos, docs-only, single-line fixes.

### Completing Work

```bash
# REQUIRED: Use safe-merge script
./scripts/safe-merge.sh feature/xyz

# Automatically: fetch, conflict check, merge, push, cleanup
```

### Multi-Agent Rules

When multiple Claude sessions/agents work simultaneously:

1. **Start with**: `git fetch && git status`
2. **Use automation**: Scripts required (don't manually merge)
3. **Keep branches short**: Same day preferred, max 2-3 days

### Commit Messages

Follow conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

**Language**: English for commits, Korean for PR descriptions.

**Details**: See [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md)

## Version Management Workflow

**CRITICAL**: After modifying any file in `template/`, you MUST update the manifest version.

**Detailed guide**: See [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md)

### Workflow for template/ modifications

```bash
# 1. Modify template files
vim template/skills/expert-panel/SKILL.md

# 2. Update version in manifest (REQUIRED)
# Edit template/.claude-kit-manifest.json and bump version:
# "skills/expert-panel": { "version": "1.0.0" → "1.1.0" }

# 3. Regenerate manifest to update hash
./scripts/generate-manifest.sh

# 4. Commit changes
git add template/ && git commit -m "feat: Update expert-panel skill to v1.1.0"
```

### Version Bumping Rules

Follow semantic versioning:

- **Major (1.0.0 → 2.0.0)**: Breaking changes, API changes
- **Minor (1.0.0 → 1.1.0)**: New features, enhancements (backward compatible)
- **Patch (1.0.0 → 1.0.1)**: Bug fixes, typos, documentation updates

### Quick Version Update

```bash
# Update version for a specific module
jq '.modules["skills/expert-panel"].version = "1.1.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json

# Regenerate manifest (updates hash automatically)
./scripts/generate-manifest.sh
```

## Extension Patterns

```bash
# 에이전트
cp template/agents/_TEMPLATE.md template/agents/[name].md
# Then: Set version to "1.0.0" in manifest

# 스킬 (폴더 단위)
cp -r template/skills/_TEMPLATE template/skills/[name]
# Then: Add to manifest with version "1.0.0"

# 스타일/커맨드/캐릭터
cp template/output-styles/_TEMPLATE.md template/output-styles/[name].md
cp template/commands/_TEMPLATE.md template/commands/[name].md
cp template/characters/_TEMPLATE.md template/characters/[name].md
# Then: Regenerate manifest with ./scripts/generate-manifest.sh
```

## Key Files

| 파일                                                               | 역할                      |
|--------------------------------------------------------------------|---------------------------|
| [template/CLAUDE.md](template/CLAUDE.md)                           | 배포될 핵심 설정          |
| [template/modules/principles.md](template/modules/principles.md)   | Analysis/Engineering 모드 |
| [template/modules/models.md](template/modules/models.md)           | Opus/Sonnet 최적화        |
| [template/skills/expert-panel/](template/skills/expert-panel/)     | 전문가 패널 토론 스킬     |
| [template/skills/doc-concretize/](template/skills/doc-concretize/) | 문서 구체화 스킬          |
| [setup-claude-global.sh](setup-claude-global.sh)                   | 설치 스크립트             |

## Template Requirements

### Agent

- `name`, `description`, `tools`, `model` 필수
- `description`에 자동 호출 트리거 키워드 포함

### Skill (Anthropic 공식)

- `SKILL.md` 필수 (~100줄, 500줄 이하)
- `description`: 1024자 이하, "Use when..." 패턴
- `name`: 소문자/숫자/하이픈, 64자 이하
- 참조 파일: 1단계 깊이만

### Command Variables

- `$ARGUMENTS`: 전체 인자
- `$1`, `$2`, ...: 개별 인자
