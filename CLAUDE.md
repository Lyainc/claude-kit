# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**claude-kit**: Claude Code Plugin. Skills, agents, modules를 포함한 설정 키트.

## Commands

### Installation (Plugin System)

```bash
# Install from official marketplace
/plugin install claude-kit@claude-plugin-directory

# Plugin management
/plugin list                    # See installed plugins
/plugin enable claude-kit       # Enable plugin
/plugin disable claude-kit      # Disable plugin
/plugin remove claude-kit       # Remove plugin
```

### Development & Validation

```bash
# Validate templates before committing
./scripts/validate-templates.sh           # Validate all
./scripts/validate-templates.sh --skills  # Skills only
./scripts/validate-templates.sh --agents  # Agents only
```

## Architecture

### Directory Structure

```text
claude-kit/
├── .claude-plugin/
│   └── plugin.json            # Plugin 메타데이터 (필수)
├── template/                  # Plugin 콘텐츠
│   ├── CLAUDE.md              # 핵심 설정
│   ├── modules/               # @import로 로드되는 모듈
│   ├── agents/                # 서브에이전트 정의
│   ├── skills/                # 스킬 (폴더 단위)
│   ├── output-styles/         # 출력 스타일
│   ├── commands/              # 슬래시 커맨드
│   └── characters/            # 캐릭터 정의 (SSOT)
├── scripts/                   # 개발 도구
├── docs/                      # 분석/참조 문서 (archive)
└── README.md
```

### Hybrid Language Strategy

| 구성요소                        | 언어   | 근거                         |
|---------------------------------|--------|------------------------------|
| Core Rules, Verification, Never | 영어   | LLM 절차적 정렬에 최적화     |
| Identity, 톤, 출력 지시         | 한국어 | 문화적 뉘앙스 및 응답 일관성 |

## Development Workflow

1. `template/` 내 파일 수정
2. `./scripts/validate-templates.sh` 실행하여 검증
3. Plugin 테스트 후 커밋

## Git Workflow

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

**Note**: Hooks are optional but recommended. CI validation is mandatory for all PRs.

### Commit Messages

Follow conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

**Language**: English for commits, Korean for PR descriptions.

### CI/CD

All PRs must pass automated validation:

- **Template Validation**: Frontmatter errors block merge
- **Branch Protection**: Direct push to main is blocked

See [.github/workflows/README.md](.github/workflows/README.md) for details.

## Extension Patterns

### Adding New Components

```bash
# Skill (folder-based)
cp -r template/skills/_TEMPLATE template/skills/[name]
vim template/skills/[name]/SKILL.md
./scripts/validate-templates.sh --skills

# Agent (file-based)
cp template/agents/_TEMPLATE.md template/agents/[name].md
vim template/agents/[name].md
./scripts/validate-templates.sh --agents

# Output Style / Command / Character
cp template/output-styles/_TEMPLATE.md template/output-styles/[name].md
cp template/commands/_TEMPLATE.md template/commands/[name].md
cp template/characters/_TEMPLATE.md template/characters/[name].md
```

### Template File Exclusions

Files/folders with `_TEMPLATE` pattern are automatically excluded from:

- Template validation
- Plugin distribution

## Key Files

| 파일                                                               | 역할                      |
|--------------------------------------------------------------------|---------------------------|
| [template/CLAUDE.md](template/CLAUDE.md)                           | 배포될 핵심 설정          |
| [template/modules/principles.md](template/modules/principles.md)   | Analysis/Engineering 모드 |
| [template/modules/models.md](template/modules/models.md)           | Opus/Sonnet 최적화        |
| [template/skills/expert-panel/](template/skills/expert-panel/)     | 전문가 패널 토론 스킬     |
| [template/skills/doc-concretize/](template/skills/doc-concretize/) | 문서 구체화 스킬          |
| [scripts/validate-templates.sh](scripts/validate-templates.sh)     | 템플릿 검증 스크립트      |

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
