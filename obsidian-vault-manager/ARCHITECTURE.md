# Vault Knowledge Manager — 개선 아키텍처 가이드

## 디렉토리 구조

### 플러그인 구조 (이 저장소)

```
obsidian-vault-manager/
├── agents/
│   ├── vault-knowledge-manager.md    # 메인 에이전트 (Sonnet)
│   └── vault-file-organizer.md       # 경량 파일 정리 subagent (Haiku)
├── skills/
│   ├── capture/SKILL.md              # /capture — 즉시 저장
│   ├── note/SKILL.md                 # /note — 노트 생성 + MOC 연결
│   └── audit/SKILL.md                # /audit — vault 구조 무결성 감사
└── ARCHITECTURE.md
```

### 설치 후 vault 구조

```
~/vault/.claude/
├── agents/
│   ├── vault-knowledge-manager.md
│   └── vault-file-organizer.md
├── skills/
│   ├── capture/SKILL.md
│   ├── note/SKILL.md
│   └── audit/SKILL.md
└── agent-memory/
    └── vault-knowledge-manager/
        └── MEMORY.md
```

## 기존 대비 주요 변경점

### 1. Agent ↔ Skill 분리 (Progressive Disclosure)

**Before**: 1개 agent 파일(~300줄)에 모든 것이 포함
**After**: agent(~90줄) + 3개 skill 파일

| 항목 | 효과 |
|------|------|
| Context window 절약 | agent 로드 시 ~90줄만 소비. skill은 호출 시에만 로드 |
| 유지보수성 | 개별 skill을 독립적으로 수정/테스트 가능 |
| 재사용성 | skill은 다른 agent에서도 사용 가능 |

Anthropic 공식 가이드: "Skills extend what Claude can do...
Claude uses skills when relevant, or you can invoke one directly."
— https://code.claude.com/docs/en/skills

### 2. Haiku subagent 도입 (vault-file-organizer)

| 작업 유형 | 담당 | 모델 |
|-----------|------|------|
| 판단이 필요한 작업 (도메인 분류, audit 해석, 노트·결정 초안 작성 — 쓰기는 사용자가 스킬로) | vault-knowledge-manager | Sonnet |
| 기계적 작업 (파일 이동, 이름 변경, 아카이브) | vault-file-organizer | Haiku |

Karpathy의 핵심 인사이트: "idle tokens mean you're the bottleneck."
비용 효율 + 속도 최적화를 위해 단순 작업은 Haiku에 위임.

### 3. 해결된 문제들

| # | 문제 | 해결 |
|---|------|------|
| A1 | Session Init 시 Home.md 없으면 에러 | fallback 로직 추가: 초기화 여부 확인 → 기본 파일 생성 |
| A2 | /capture 예외 처리 모순 | skill 분리로 해결. capture skill 자체에 "확인 없이 즉시 저장" 명시 |
| A3 | 파일명 충돌 처리 없음 | note skill에 중복 확인 + 덮어쓰기/이름변경/병합 선택 로직 추가 |
| B4 | MOC 자동 업데이트 ↔ confirm 원칙 충돌 | "노트 생성 확인 = MOC 업데이트도 승인" 정책 명시. 새 MOC 생성은 별도 확인 |
| B5 | mdfind macOS 의존성 | agent 본문에 macOS 전용임을 명시 |
| C7 | Memory system 이중 관리 | agent memory (`memory: project`)만 사용. 커스텀 memory system 제거 |
| C8 | Memory types 과잉 설계 | 제거. Claude Code 내장 agent memory 시스템에 위임 |
| D9 | description의 \\n escape | description을 한 줄로 정리 |

### 4. Skill별 설계 근거

#### /capture — 즉시 저장
- `disable-model-invocation` 미설정 (자연어로도 트리거 가능: "빠르게 메모해줘")
- 유일하게 확인 없이 동작하는 skill
- Karpathy 패턴: "spending time on things an agent can handle means adding friction"

### 5. 제거한 것들

| 제거 항목 | 이유 |
|-----------|------|
| 커스텀 memory system (user/feedback/project/reference 4타입) | Claude Code `memory: project` 내장 기능으로 대체. 토큰 ~150줄 절약 |
| Agent description의 예시 대화 | subagent description은 250자 권장. 예시는 불필요한 토큰 소비 |
| "Update Your Agent Memory" 섹션 | 내장 memory system이 자동 처리 |

## 설치 방법

### 마켓플레이스 설치 (권장)

```bash
# 플러그인 설치
claude plugin install obsidian-vault-manager@Lyainc-claude-kit

# agent memory 디렉토리 생성
mkdir -p ~/vault/.claude/agent-memory/vault-knowledge-manager

# 확인
cd ~/vault && claude agents
```

### 수동 설치

```bash
# 1. agent 파일 복사
cp agents/vault-knowledge-manager.md ~/vault/.claude/agents/
cp agents/vault-file-organizer.md ~/vault/.claude/agents/

# 2. skill 디렉토리 복사
cp -r skills/* ~/vault/.claude/skills/

# 3. agent memory 디렉토리 생성
mkdir -p ~/vault/.claude/agent-memory/vault-knowledge-manager

# 4. 확인
cd ~/vault && claude agents
```

## 추가 고려사항

### 향후 확장 가능한 skill 아이디어

- `/link` — 두 노트 간 양방향 링크 생성
- `/search` — vault 전체 검색 + 결과 요약
- `/daily` — 데일리 노트 생성 (날짜 기반 템플릿)
- `/refactor` — MOC 구조 리팩토링 제안

### CLAUDE.md와의 관계

vault의 `CLAUDE.md`에는 vault 구조 컨벤션이나 자주 쓰는 태그 목록 등
**모든 에이전트/세션에 공통으로 적용할 규칙**을 넣는다.
agent-specific 규칙은 agent 파일에, task-specific 절차는 skill에 넣는다.
