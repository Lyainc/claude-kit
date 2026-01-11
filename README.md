# claude-kit

Claude Code의 기본 동작을 커스터마이징하는 설정 키트.

## 빠른 시작

### 원라인 설치

```bash
curl -fsSL https://raw.githubusercontent.com/Lyainc/claude-kit/main/install.sh | bash
```

### 수동 설치

```bash
git clone https://github.com/Lyainc/claude-kit.git ~/.claude-kit
cd ~/.claude-kit
./setup-claude-global.sh
```

### 업데이트

```bash
# 동일한 curl 명령어 재실행 (자동 업데이트)
curl -fsSL https://raw.githubusercontent.com/Lyainc/claude-kit/main/install.sh | bash

# 또는 수동
cd ~/.claude-kit && git pull && ./setup-claude-global.sh
```

## 설치 옵션

```bash
# Interactive mode (recommended for first-time users)
./setup-claude-global.sh

# Direct modes
./setup-claude-global.sh install      # First-time installation
./setup-claude-global.sh update       # Smart update (version-aware, preserves user changes)
./setup-claude-global.sh reset        # Reset (backup and replace all)
./setup-claude-global.sh doctor       # Check installation health

# Options
./setup-claude-global.sh update --dry-run       # Preview changes
./setup-claude-global.sh update --force-update  # Update even user-modified modules
./setup-claude-global.sh reset --show-diff      # Show diff for changed files
./setup-claude-global.sh update --cleanup       # Remove orphaned files
```

## 버전 관리 시스템

v1.1.0부터 manifest 기반 스마트 업데이트를 지원합니다:

- **자동 버전 감지**: 모듈 변경 사항 자동 추적
- **사용자 수정 보호**: 수정한 파일은 자동으로 skip
- **선택적 업데이트**: `--force-update`로 선택적 강제 업데이트
- **Health Check**: `doctor` 명령으로 설치 상태 확인

```bash
# 업데이트 확인
./setup-claude-global.sh doctor

# 스마트 업데이트 (사용자 수정 보호)
./setup-claude-global.sh update

# 수정한 파일도 강제 업데이트 (백업 후)
./setup-claude-global.sh update --force-update
```

## 설치 구조

```text
~/.claude/
├── CLAUDE.md                  # 핵심 설정
├── modules/
│   ├── principles.md          # 사고 원칙
│   ├── models.md              # 모델별 최적화
│   └── characters.md          # 멀티 캐릭터 모드
├── agents/                    # 서브에이전트
├── skills/                    # 스킬 (폴더 단위)
│   ├── expert-panel/          # 전문가 패널 토론
│   └── doc-concretize/        # 문서 구체화 (재귀적 작성)
├── output-styles/             # 출력 스타일
├── commands/                  # 슬래시 커맨드
└── characters/                # 캐릭터 정의
```

## 포함된 스킬

| 스킬             | 설명                             | 트리거                            |
|------------------|----------------------------------|-----------------------------------|
| `expert-panel`   | 전문가 패널 토론 시뮬레이션      | "전문가 토론", "찬반 분석"        |
| `doc-concretize` | 추상적 개념을 구체적 문서로 변환 | "문서화", "구체화", "체계적 정리" |

## 개발자 가이드

### Git Workflow

이 프로젝트에 기여하거나 개발하는 경우, Git 워크플로우 가이드를 참조하세요:

- **간단 체크리스트**: [CLAUDE.md - Git Workflow](CLAUDE.md#git-workflow)
- **상세 가이드**: [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md)

핵심 규칙:

- Main 브랜치 중심, feature/fix 브랜치는 당일 완료
- 작업 시작 전 항상 `git fetch && git status`
- 머지 후 브랜치 즉시 삭제 (로컬 + 리모트)

## 커스터마이징

### 개인 설정 추가

`template/local/` 폴더에 개인 설정을 추가하면 git에 커밋되지 않습니다.

```bash
mkdir -p ~/.claude-kit/template/local
# 개인 설정 파일 추가
./setup-claude-global.sh
```

### 스킬 추가

```bash
cp -r template/skills/_TEMPLATE template/skills/[name]
# SKILL.md 편집 후
./setup-claude-global.sh
```

### 에이전트/커맨드/스타일 추가

```bash
cp template/agents/_TEMPLATE.md template/agents/[name].md
cp template/commands/_TEMPLATE.md template/commands/[name].md
cp template/output-styles/_TEMPLATE.md template/output-styles/[name].md
```

## 설정 철학

### 하이브리드 언어 전략

| 구성요소                 | 언어   | 근거                     |
|--------------------------|--------|--------------------------|
| Core Rules, Verification | 영어   | LLM 절차적 정렬에 최적화 |
| Identity, 톤, 출력 지시  | 한국어 | 문화적 뉘앙스 유지       |

## 기능 지원 상태

| 기능             | 상태 | 문서                                                                            |
|------------------|------|---------------------------------------------------------------------------------|
| `@import` 문법   | 공식 | [Memory](https://docs.anthropic.com/en/docs/claude-code/memory)                 |
| `agents/` 폴더   | 공식 | [Sub-agents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)         |
| `skills/` 폴더   | 공식 | [Skills](https://docs.anthropic.com/en/docs/claude-code/skills)                 |
| `commands/` 폴더 | 공식 | [Slash Commands](https://docs.anthropic.com/en/docs/claude-code/slash-commands) |
| `output-styles/` | 공식 | [Output Styles](https://docs.anthropic.com/en/docs/claude-code/output-styles)   |

## 프로젝트 구조

```text
claude-kit/
├── template/                  # 배포 원본 → ~/.claude/로 복사
├── docs/                      # 참조 문서
├── install.sh                 # 원라인 설치 스크립트
├── setup-claude-global.sh     # 설치/업데이트 스크립트
└── README.md
```

## FAQ

### 커스텀 스킬을 유지하면서 업데이트하려면?

`update` 모드를 사용하세요. 기존 파일은 절대 덮어쓰지 않습니다.

```bash
./setup-claude-global.sh update
```

### 수정한 모듈을 최신 버전으로 업데이트하려면?

두 가지 방법이 있습니다:

**방법 1**: 선택적 강제 업데이트 (권장)

```bash
# 수정한 파일도 업데이트 (자동 백업)
./setup-claude-global.sh update --force-update
```

**방법 2**: 수동 삭제 후 재설치

```bash
# 1. 특정 모듈 삭제
rm -rf ~/.claude/skills/expert-panel

# 2. 업데이트 (새 버전 설치됨)
./setup-claude-global.sh update
```

### 대화 이력이나 MCP 설정은 어떻게 되나요?

이 스크립트는 **관리하는 경로만** 건드립니다:

- **관리 대상**: `CLAUDE.md`, `modules/`, `agents/`, `skills/`, `output-styles/`, `commands/`, `characters/`
- **완전히 무시**: `mcp/`, `hooks/`, `sessions/`, 기타 모든 커스텀 파일/폴더

따라서 MCP 서버 설정, Git 훅, 대화 세션, 에디터 설정 등은 **절대 영향받지 않습니다**.

### Update vs Reset 차이는?

- **Update**: 새 파일만 추가 (안전, 커스터마이징 보존)
- **Reset**: 전부 교체 (위험, 커스텀 파일 삭제됨)

대부분의 경우 `update`를 사용하세요.

## 문제 해결

### 설치 후 적용 안됨

Claude Code 재시작 필요:

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

### 버전 확인

```bash
./setup-claude-global.sh --version
# 또는
cat ~/.claude/.claude-kit-version
```

## 라이선스

MIT
