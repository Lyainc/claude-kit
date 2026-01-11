# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code 글로벌 설정 키트. `template/` 디렉토리의 설정 파일을 `~/.claude/`에 설치.

## Commands

### Setup & Installation

```bash
# Interactive mode (recommended)
./setup-claude-global.sh

# Direct modes
./setup-claude-global.sh install      # First installation
./setup-claude-global.sh update       # Smart update (version-aware, preserves user changes)
./setup-claude-global.sh reset        # Reset (backup and replace all)
./setup-claude-global.sh doctor       # Health check and version status

# Options
./setup-claude-global.sh update --dry-run       # Preview changes
./setup-claude-global.sh update --force-update  # Update even user-modified files (with backup)
./setup-claude-global.sh reset --show-diff      # Show diff
./setup-claude-global.sh update --cleanup       # Remove orphaned files
```

### Development & Validation

```bash
# Validate templates before committing
./scripts/validate-templates.sh           # Validate all
./scripts/validate-templates.sh --skills  # Skills only
./scripts/validate-templates.sh --agents  # Agents only

# Generate/update manifest after template changes
./scripts/generate-manifest.sh
```

**Mode Behaviors**:

- **install**: First-time setup. Fails if any files exist (prevents accidental overwrites).
- **update**: Adds new files only. Keeps existing files (user customizations preserved).
- **reset**: Backup and replace all files (clean slate).

**Edge Case Handling**:

- File hash comparison for change detection
- CLAUDE.md reference validation (fails if modules missing)
- Atomic folder operations for skills/agents
- Orphaned file detection - **only scans managed paths** (see below)
- `_TEMPLATE` patterns automatically excluded

**Managed Paths** (orphaned detection scope):

The script only manages these paths in `~/.claude/`:

- Files: `CLAUDE.md`, `CLAUDE-PLATFORM-SETTINGS.md`
- Directories: `modules/`, `agents/`, `skills/`, `output-styles/`, `commands/`, `characters/`

All other paths (e.g., `mcp/`, `hooks/`, `sessions/`, custom files) are **completely ignored** by the script.

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

### Pre-commit Hooks (Optional)

Install hooks for automatic validation before commits:

```bash
# Recommended: Auto-detect best method
./scripts/setup-hooks.sh

# Or choose explicitly
./scripts/setup-hooks.sh native       # No dependencies
./scripts/setup-hooks.sh pre-commit   # Industry standard (requires pip)
```

**Hook features**:

- Template validation (ERROR → blocks commit)
- Manifest integrity check (hash verification)
- Version bump warning (non-blocking)

**Note**: Hooks are optional but recommended. CI validation is mandatory for all PRs.

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
4. **Tag AI branches**: Use descriptive names (e.g., `agent-update-skill-v2`)

### Commit Messages

Follow conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

**Language**: English for commits, Korean for PR descriptions.

**Details**: See [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md)

### CI/CD

All PRs must pass automated validation:

- **Template Validation**: Frontmatter errors block merge
- **Manifest Integrity**: Hash mismatch blocks merge
- **Branch Protection**: Direct push to main is blocked

See [.github/workflows/README.md](.github/workflows/README.md) for details.

## Version Management

**CRITICAL**: Template 수정 후 반드시 manifest 버전 업데이트 필요.

**Workflow**: [CONTRIBUTING.md](CONTRIBUTING.md)

**Details**: [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md)

## Extension Patterns

### Adding New Components

```bash
# Skill (folder-based)
cp -r template/skills/_TEMPLATE template/skills/[name]
vim template/skills/[name]/SKILL.md
./scripts/validate-templates.sh --skills
./scripts/generate-manifest.sh  # Auto-adds with version 1.0.0

# Agent (file-based)
cp template/agents/_TEMPLATE.md template/agents/[name].md
vim template/agents/[name].md
./scripts/validate-templates.sh --agents
./scripts/generate-manifest.sh  # Auto-adds with version 1.0.0

# Output Style / Command / Character
cp template/output-styles/_TEMPLATE.md template/output-styles/[name].md
cp template/commands/_TEMPLATE.md template/commands/[name].md
cp template/characters/_TEMPLATE.md template/characters/[name].md
./scripts/generate-manifest.sh
```

### Template File Exclusions

Files/folders with `_TEMPLATE` pattern are automatically excluded from:

- Manifest generation
- Template validation
- Installation/update operations

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
