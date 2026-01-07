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

### Branch Strategy

**Main branch only** for production-ready code. Feature/fix branches are short-lived (max 1 day).

### Starting New Work

```bash
# 1. Sync with remote (prevent conflicts)
git fetch origin
git checkout main
git pull origin main

# 2. Create feature branch (if needed)
git checkout -b feature/descriptive-name
# or fix/descriptive-name
```

**When to skip branching**: Single-file trivial changes can commit directly to main.

### Completing Work

```bash
# 1. Check for remote changes (CRITICAL for multi-session work)
git fetch origin
git checkout main
git pull origin main

# 2. Merge with no-ff (preserve merge commit)
git merge --no-ff feature/xyz

# 3. Push to remote
git push origin main

# 4. Delete branch immediately (local + remote)
git branch -d feature/xyz
git push origin --delete feature/xyz
```

### Multi-Session Protocol

When working across multiple Claude sessions or terminals:

1. **Always start with**: `git fetch && git status`
2. **Before merge**: Verify no uncommitted changes
3. **Branch lifespan**: Same day only - merge or discard before EOD

### Commit Messages

Follow conventional commits when appropriate:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation only
- `refactor:` Code restructuring
- `chore:` Tooling, dependencies

**Language**: English for commit messages, Korean for PR descriptions (unless otherwise specified).

**Detailed guidelines**: See [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md)

## Extension Patterns

```bash
# 에이전트
cp template/agents/_TEMPLATE.md template/agents/[name].md

# 스킬 (폴더 단위)
cp -r template/skills/_TEMPLATE template/skills/[name]

# 스타일/커맨드/캐릭터
cp template/output-styles/_TEMPLATE.md template/output-styles/[name].md
cp template/commands/_TEMPLATE.md template/commands/[name].md
cp template/characters/_TEMPLATE.md template/characters/[name].md
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
