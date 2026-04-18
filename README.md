# claude-kit

Claude Code용 **스킬 플러그인 마켓플레이스**. 독립적인 플러그인들을 하나의 저장소에서 관리합니다.

## 플러그인 버전

| 플러그인 | 버전 | 구성 |
|---|---|---|
| [thinking-tools](thinking-tools/) | `1.6.0` | 스킬 7 + 에이전트 1 |
| [obsidian-vault-manager](obsidian-vault-manager/) | `0.5.0` | 스킬 6 + 에이전트 2 |
| [vault-bridge](vault-bridge/) | `1.1.0` | 에이전트 1 + 훅 2 (Stop / SessionEnd) + 슬래시 커맨드 2 (`/save-session`, `/vault-link`) (구 `vault-reader`) |

## 플러그인 목록

### [thinking-tools](thinking-tools/)

분석, 문서 작성, 품질 검증을 위한 사고 도구 스킬 플러그인. 7개 스킬 + 1개 에이전트.

```bash
claude plugin install thinking-tools@Lyainc-claude-kit
```

| Component | Description |
| --- | --- |
| `diverse-sampling` | Verbalized Sampling 기반 다양한 응답 생성 |
| `doc-concretize` | 추상적 개념을 구조화된 문서로 변환 |
| `doc-polish` | 마크다운 문서 3-layer QA 검증 |
| `expert-panel` | 변증법적 전문가 패널 토론 |
| `unknown-discovery` | 반복 인터뷰를 통한 맹점 발견 |
| `thought-chain` | 스킬 파이프라인 오케스트레이션 |
| `adversarial-review` | 주장 반증 테스트 + Survival Score 정량 평가 |
| `thinking-facilitator` (agent) | 요청을 분석하여 최적 스킬로 자동 라우팅 |

### [obsidian-vault-manager](obsidian-vault-manager/)

Obsidian vault 지식 관리 플러그인. 2개 에이전트 + 6개 스킬.

```bash
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

| Component | Description |
| --- | --- |
| `vault-knowledge-manager` (agent) | 메인 에이전트 — 노트 생성, MOC 관리, 프로젝트 추적 |
| `vault-file-organizer` (agent) | 경량 subagent — 파일 이동, 이름 변경, 아카이브 |
| `capture` | 즉시 Inbox에 메모 저장 |
| `note` | 새 노트 생성 + MOC 연결 |
| `project` | 프로젝트 디렉토리 생성 |
| `inbox-review` | Inbox 파일 일괄 정리 |
| `context` | vault 내부 도메인 맥락 로드 (Explore fork) |
| `archive` | 프로젝트 아카이브 + MOC 정리 |

### [vault-bridge](vault-bridge/)

> v1.0.0에서 `vault-reader` → `vault-bridge`로 리네이밍 (read-only 뉘앙스 제거, 외부 프로젝트↔vault 양방향 브릿지 역할 반영).

외부 프로젝트에서 Obsidian vault에 접근하는 브릿지 플러그인. `vault-searcher` 에이전트(Haiku)가 **proactive invocation**으로 `~/vault/` 접근 시 자동 소환됩니다.

```bash
claude plugin install vault-bridge@Lyainc-claude-kit
```

| Component | Description |
| --- | --- |
| `vault-searcher` (agent) | 4-mode I/O: (1) Session Restore, (2) Domain Context Load, (3) Keyword Search, (4) Session Note Creation (record/handoff/quick) |
| Stop hook | 매 턴 실행 (결정형 셸). 세션 종료 신호(`세션 끝`, `wrap up` 등) 감지 시 `/save-session` 제안 `systemMessage` 방출 |
| SessionEnd hook | 세션 종료 시 silent 안전망 — meaningful work(파일 수정/볼트 읽기/결정 기록/코드 실행/리서치 중 하나 + 3턴 이상) 감지 시 자동 quick-save |
| `/save-session` | 사용자가 명시적으로 호출하는 슬래시 커맨드 — vault-searcher Mode 4 전체 플로우 진입 |
| `/vault-link` | 현재 디렉토리에 `.vault-link` 포인터 파일 생성 — 코드 리포를 특정 vault 프로젝트에 바인딩. Mode 2 검색 스코프 제한 + Mode 4 저장 경로 자동 결정 |

자세한 4-mode 동작, `.vault-link` 포인터 파일 컨벤션은 [vault-bridge/README.md](vault-bridge/README.md) 참조.

## 마이그레이션

### `vault-reader` → `vault-bridge` (v1.0.0, 2026-04-13)

**Breaking change**: `vault-reader` 플러그인이 `vault-bridge`로 리네이밍되었습니다. vault 데이터는 완전 호환되므로 파일 이관 불필요.

```bash
claude plugin uninstall vault-reader
claude plugin install vault-bridge@Lyainc-claude-kit
```

에이전트/훅/슬래시 커맨드 동작과 트리거 문구는 동일. 스크립트에서 에이전트를 정식 이름으로 참조한다면 `vault-reader:vault-searcher` → `vault-bridge:vault-searcher`로 갱신하세요.

### 기존 `claude-kit` → `thinking-tools`

기존 `claude-kit` 플러그인이 `thinking-tools`로 이름이 변경되었습니다.

```bash
# 1. 기존 플러그인 제거
claude plugin uninstall claude-kit

# 2. 새 이름으로 재설치
claude plugin install thinking-tools@Lyainc-claude-kit
```

스킬 이름과 트리거는 동일하므로 사용법 변경은 없습니다.

### `/wrapup` 스킬 제거 (obsidian-vault-manager v0.4.0)

**Breaking change**: obsidian-vault-manager의 `/wrapup` 스킬이 제거되고, 세션 기록은 `vault-bridge` 플러그인의 `vault-searcher` 에이전트 Mode 4 (Session Note Creation)로 일원화되었습니다.

| 기존 `/wrapup` 사용 | 신규 사용 |
|---|---|
| `/wrapup` | "세션 정리해줘" / "세션 노트 만들어줘" — vault-searcher가 자동 소환되어 Mode 4 실행 |
| `/wrapup --hours 3` | Mode 4 프로시저가 대화 컨텍스트 + 최근 변경 파일(`find -mmin`)을 수집. 범위는 세션 내용 기반으로 자동 판단. |
| `/wrapup --no-save` | Mode 4 Step 6의 AskUserQuestion에서 `[취소]` 선택 |
| 자동 저장 (세션 종료 시) | SessionEnd hook이 meaningful work 감지 시 자동 quick-save (`session-YYYY-MM-DD.md`, `tags: [session, auto-saved]`) |

**기존 파일 처리**:
- 과거 `session-wrapup` 태그/파일명의 노트는 그대로 유지 (migration script 제공하지 않음)
- 필요 시 수동으로 `type: session` frontmatter 추가 또는 그대로 아카이브

자세한 session-note 3-mode(`record` / `handoff` / `quick`) 설명은 [`vault-bridge/README.md`](vault-bridge/README.md) 참조.

## 문제 해결

**설치 후 적용 안됨**: Claude Code 재시작 필요

- VS Code: `Cmd+Shift+P` → "Claude: Restart"
- Terminal: 새 세션 시작

## 개발

개발자 가이드는 [CLAUDE.md](CLAUDE.md) 참조.

## 라이선스

MIT
