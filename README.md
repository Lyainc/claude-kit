# claude-kit

Claude Code용 **스킬 플러그인 마켓플레이스**. 독립적인 플러그인들을 하나의 저장소에서 관리합니다.

## 플러그인 버전

| 플러그인 | 버전 | 구성 |
|---|---|---|
| [thinking-tools](thinking-tools/) | `2.2.0` | 스킬 8 + 에이전트 1 |
| [obsidian-vault-manager](obsidian-vault-manager/) | `0.19.0` | 스킬 4 (capture/note/audit/base) + 에이전트 2 + scripts (ovm-primitives) + reference (vault-audit-rules) |
| [vault-bridge](vault-bridge/) | `2.1.0` | 에이전트 1 (read-only) + 훅 5 (Stop / SessionEnd command+prompt / SessionStart / PreToolUse Read\|Grep\|Glob / PreToolUse Write\|Edit) + 슬래시 커맨드 6 (`/save-session`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`, `/save-plan-doc`, `/handoff`) (구 `vault-reader`) |
| [workflow-harness](workflow-harness/) | `0.2.0` | 스킬 1 (retro) — layer ⑤ 실행 하네스 (audit E8 승격 + 3갈래 출력 + dedup + 회고예산) |

## 4-흐름 카탈로그

claude-kit은 사용자의 직관적인 활용을 위해 기능을 4가지 주요 흐름(Flow)으로 논리적으로 묶어 제공합니다. 이는 물리적 재구조화가 아니며, 기존 5-레이어 구조와 직교(Orthogonal)로 매핑됩니다 (CON-5 위반 회피). 이 논리적 묶음은 #117 setup-wizard의 온보딩 제안과 연결됩니다. 자세한 매핑 구조는 [`docs/design/4-flow-catalog.md`](docs/design/4-flow-catalog.md)를 참고하세요.

| 4-흐름 (Logical Flow) | 매핑되는 5-레이어 (Physical) |
| --- | --- |
| **사고/기획** | ①인지, ②결정화·출력, ⑤실행 |
| **작업/폴리싱** | ①인지, ②결정화·출력, ⑤실행 |
| **시각화** | ②결정화·출력 |
| **지식관리** | ③딜리버리, ④지식베이스 |

## 플러그인 목록

### [thinking-tools](thinking-tools/)

분석, 문서 작성, 품질 검증을 위한 사고 도구 스킬 플러그인. 8개 스킬 + 1개 에이전트.

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
| `spec-first` | 모호한 아이디어를 machine-readable Seed 스펙으로 구체화 (Socratic + ambiguity gate) |
| `thinking-facilitator` (agent) | 요청을 분석하여 최적 스킬로 자동 라우팅 |

### [obsidian-vault-manager](obsidian-vault-manager/)

Obsidian vault 지식 관리 플러그인 (v4). 2개 에이전트 + 4개 스킬.

```bash
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

| Component | Description |
| --- | --- |
| `vault-knowledge-manager` (agent) | 메인 에이전트 — 노트 생성, MOC 관리, 프로젝트 추적 |
| `vault-file-organizer` (agent) | 경량 subagent — 파일 이동, 이름 변경, 아카이브 |
| `capture` | 즉시 Inbox에 메모 저장 + URL Defuddle 추출 옵션 |
| `note` | 새 노트 생성 + MOC 연결 + 프로젝트 연결 옵션 |
| `audit` | vault 구조 무결성 감사 — E1-E11 오류 감지 (P0-P2 우선순위), promotion candidate 추적 |
| `base` | 비파괴 Obsidian Bases(.base) 뷰 생성 |

### [vault-bridge](vault-bridge/)

> v1.0.0에서 `vault-reader` → `vault-bridge`로 리네이밍 (read-only 뉘앙스 제거, 외부 프로젝트↔vault 양방향 브릿지 역할 반영).

외부 프로젝트에서 Obsidian vault에 접근하는 브릿지 플러그인. `vault-searcher` 에이전트(Haiku)가 **proactive invocation**으로 `~/vault/` 접근 시 자동 소환됩니다.

```bash
claude plugin install vault-bridge@Lyainc-claude-kit
```

| Component | Description |
| --- | --- |
| `vault-searcher` (agent) | 3-mode read/search I/O: (1) Session Restore, (2) Domain Context Load, (3) Keyword Search (optional Obsidian CLI acceleration). **Read-only since v1.9.0** — vault writes route through slash commands (`/save-session`, `/save-plan-doc`, `/vault-commit`) executed in main context. |
| Stop hook | 매 턴 실행 (결정형 셸). 세션 종료 신호(`세션 끝`, `wrap up` 등) 감지 시 `/save-session` 제안 `systemMessage` 방출 |
| SessionEnd hook | 세션 종료 시 silent 안전망 — meaningful work(파일 수정/볼트 읽기/결정 기록/코드 실행/리서치 중 하나 + 3턴 이상) 감지 시 자동 quick-save |
| `/save-session` | 사용자가 명시적으로 호출하는 슬래시 커맨드 — record/handoff/quick 3-mode 세션 노트 작성을 main context에서 inline 실행 |
| `/vault-link` | 현재 디렉토리에 `.vault-link` 포인터 파일 생성 — 코드 리포를 특정 vault 프로젝트에 바인딩. 검색 스코프 제한 + `/save-session` 저장 경로 자동 결정 |
| `/vault-manifest-refresh` | vault manifest 강제 재생성 — `~/vault/.vault-bridge/manifest.json` 갱신. 토큰 절감 효과: 도메인 컨텍스트 로드 시 ~97% 절감 |
| `/vault-commit` | vault git 리포의 미커밋 변경사항 commit — 변경 요약 표시, 커밋 메시지 자동 생성, 사용자 승인 후 실행 |
| `/save-plan-doc` | 외부 프로젝트의 plan/design/RFC 문서를 바인딩된 vault 프로젝트에 스냅샷으로 저장 — 2-layer opt-in gate(`.vault-link`의 `snapshot_export: true` + vault `_index.md`의 `snapshot_import: true`), 5-case source_commit fallback, 본문 기준 중복 제거 |
| SessionStart hook | 세션 시작 시 manifest staleness 체크 → 변경 파일만 incremental 업데이트 (백그라운드, 세션 차단 없음) |
| PreToolUse hook (Read\|Grep\|Glob) | `Read`/`Grep`/`Glob`으로 `~/vault/` 직접 접근 감지 → vault-searcher 사용 권장 `systemMessage` 방출 (soft warning, 차단 없음). 세션 직접 접근 횟수 카운팅 → SessionEnd 요약에 포함 |
| PreToolUse hook (Write\|Edit) | `Write`/`Edit`으로 `~/vault/` 쓰기 시 파일명 컨벤션 검증 → 위반 시 `systemMessage` 경고 (log-only 기본). `VAULT_BRIDGE_STRICT_NAMING=1` 시 차단 (exit 2) |

자세한 3-mode 동작, `.vault-link` 포인터 파일 컨벤션, Write Role 정책은 [vault-bridge/README.md](vault-bridge/README.md) 참조.

### [workflow-harness](workflow-harness/)

> **v0.2.0 — thin scaffold + 첫 스킬 `retro`** — layer ⑤(실행) 경량 하네스. 전체 OMC-strangler 엔진(#122)이 아니라, ⑤ 스킬이 경계 계약을 지키며 점진 입주하는 구조예요. 첫 입주: `retro`(#123) — 측정→개선 루프를 닫는 회고 스킬.

Claude Code 네이티브 기능(`/goal`, dynamic Workflow, agents, hooks)을 substrate로 한 경량 오케스트레이션 플러그인. **단방향 의존(CON-5)**: `workflow-harness`(harness) → leaf 플러그인(`vault-bridge`·`obsidian-vault-manager`) + 프로젝트 로컬 `telemetry/` dogfooding 출력(플러그인 아님). 역방향·순환 금지. 자세한 경계는 [`docs/design/claude-kit-boundary.md`](docs/design/claude-kit-boundary.md) §3/§5, 로드맵은 [workflow-harness/README.md](workflow-harness/README.md) 참조.

## 빠른 시작 (신규 사용자)

5분 안에 vault second brain을 시작하는 방법이에요.

### 1. vault 초기화

```bash
mkdir -p ~/vault/{inbox,notes,assets}
cd ~/vault
git init
git add -A
git commit -m "initial vault structure (v4)"
```

### 2. 플러그인 설치

```bash
# 최소 설치 (vault 브릿지 + 세션 노트)
claude plugin install vault-bridge@Lyainc-claude-kit

# vault 지식 관리 스킬까지 포함
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

Claude Code를 재시작하면 적용됩니다.

### 3. 프로젝트와 vault 연결

코드 프로젝트 루트에서:

```
/vault-link
```

`.vault-link` 파일이 생성되면 이후 `/save-session`, `/save-plan-doc`이 이 프로젝트 경로로 자동 저장됩니다.

### 4. 첫 캡처

```
/capture 오늘 배운 것: Claude Code 플러그인 구조
```

`~/vault/inbox/capture-YYYY-MM-DD-{slug}.md`로 저장됩니다. URL을 전달하면 본문을 자동 추출해요 (`defuddle` 설치 시).

### 5. 세션 노트 저장

작업 마무리 시:

```
/save-session
```

record / handoff / quick 모드 중 선택 후 `~/vault/inbox/` 또는 연결된 프로젝트 폴더에 저장됩니다.

---

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

**Breaking change**: obsidian-vault-manager의 `/wrapup` 스킬이 제거되고, 세션 기록은 `vault-bridge` 플러그인의 `/save-session` 슬래시 커맨드로 일원화되었습니다 (v1.0.0에서는 `vault-searcher` 에이전트 Mode 4에 위임했고, v1.9.0부터는 `/save-session`이 main context에서 inline 실행).

| 기존 `/wrapup` 사용 | 신규 사용 |
|---|---|
| `/wrapup` | `/save-session` 또는 "세션 정리해줘" / "세션 노트 만들어줘" — record/handoff/quick 3-mode 라우팅 후 inline 실행 |
| `/wrapup --hours 3` | `/save-session` 프로시저가 대화 컨텍스트 + 최근 변경 파일(`find -mmin`)을 수집. 범위는 세션 내용 기반으로 자동 판단 |
| `/wrapup --no-save` | `/save-session` Step 10의 AskUserQuestion에서 `[취소]` 선택 |
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
