# claude-kit

Claude Code의 기본 동작을 커스터마이징하는 설정 키트이자 **Claude Code 플러그인**.

## 플러그인으로 설치 (권장)

Claude Code 마켓플레이스 또는 로컬에서 플러그인으로 설치:

```bash
# 마켓플레이스에서 설치 (추후 지원)
claude plugin install claude-kit

# 로컬 설치 (GitHub에서 클론 후)
git clone https://github.com/Lyainc/claude-kit.git
claude plugin add ./claude-kit
```

### 플러그인에 포함된 스킬

| Skill | Description | Triggers (EN/KO) |
|-------|-------------|------------------|
| `expert-panel` | Expert panel discussions with dialectical analysis | expert panel, design review / 전문가 토론, 찬반 분석 |
| `doc-concretize` | Transform abstract concepts into structured documents | 문서화, 구체화, 체계적 정리 |
| `docx` | Word document generation and editing | 워드, 문서 작성 |
| `pptx` | PowerPoint presentation generation | PPT, 프레젠테이션, 슬라이드 |

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

## 개발자 가이드

### 컴포넌트 추가

```bash
# Skill (폴더 기반)
cp -r template/skills/_TEMPLATE template/skills/[name]
vim template/skills/[name]/SKILL.md
./scripts/validate-templates.sh --skills

# Agent (파일 기반)
cp template/agents/_TEMPLATE.md template/agents/[name].md
./scripts/validate-templates.sh --agents

# Output Style / Command / Character
cp template/output-styles/_TEMPLATE.md template/output-styles/[name].md
cp template/commands/_TEMPLATE.md template/commands/[name].md
cp template/characters/_TEMPLATE.md template/characters/[name].md
```

### Git Workflow

- **간단 체크리스트**: [CLAUDE.md - Git Workflow](CLAUDE.md#git-workflow)
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`

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
├── .claude-plugin/
│   └── plugin.json            # Plugin 메타데이터
├── template/                  # Plugin 콘텐츠
│   ├── CLAUDE.md              # 핵심 설정
│   ├── modules/               # @import 모듈
│   ├── agents/                # 서브에이전트
│   ├── skills/                # 스킬 (폴더 단위)
│   ├── output-styles/         # 출력 스타일
│   ├── commands/              # 슬래시 커맨드
│   └── characters/            # 캐릭터 정의
├── scripts/                   # 개발 도구
└── README.md
```

## 문제 해결

### 설치 후 적용 안됨

Claude Code 재시작 필요:

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

## 라이선스

MIT
