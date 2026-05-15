# claude-kit Setup Wizard 설계

**상태**: 설계 합의 완료, 구현 대기
**최종 합의일**: 2026-05-12
**근거 문서**: [`docs/discussions/20260512_setup-wizard-design/`](../discussions/20260512_setup-wizard-design/)
**관련 PR/이슈**: TBD (구현 단계에서 채움)

---

## 1. 개요

claude-kit은 thinking-tools, obsidian-vault-manager, vault-bridge 세 플러그인으로 구성된 Claude Code 마켓플레이스에요. 각 플러그인이 독립적으로 설치되지만 외부 의존성(Obsidian, vault 경로 등)이 서로 다르고, 사용자가 첫 설치 후 "무엇을 할 수 있는지" 자연스럽게 파악할 진입점이 부재했어요. 이 문서는 마켓플레이스 첫 실행 시 자동 안내와 명시적 슬래시 커맨드를 결합한 **세련된 wizard 경험**의 설계를 정의해요.

목적은 세 가지예요. 첫째, 신규 사용자가 README를 읽지 않아도 핵심 기능을 30초 이내 파악할 수 있게 한다. 둘째, 초기 설정(vault 경로, `.vault-link` 등)을 강요하지 않으면서도 필요할 때 안내한다. 셋째, 미래에 추가될 플러그인까지 자연스럽게 흡수할 확장 구조를 마련한다.

비목표는 의도적으로 제외했어요. 단계별 액션 강요(예: 첫 세션에서 무조건 vault 만들기)는 하지 않아요. 외부 의존성(Obsidian) 자동 설치도 하지 않아요. wizard 본문 자동 생성(LLM이 페이지 콘텐츠를 즉석에서 만드는 것)도 하지 않아요.

## 2. 설계 원칙

| 원칙 | 의미 |
|------|------|
| **Hybrid Trigger** | 자동 감지(SessionStart) + 명시적 호출(`/welcome`) 결합. 자동 감지는 1회성에 가깝게 제한. |
| **Hub & Spoke** | 마켓플레이스 입구(허브)에서 설치된 플러그인을 안내하고, 각 플러그인 깊은 설정은 스포크 페이지로 위임. |
| **Read-Only Walkthrough** | 관조형 — 사용자에게 액션 강요 안 함. wizard는 정보 제공, 실행은 사용자 의지. |
| **Graceful Degradation** | 외부 의존성(Obsidian, vault) 미충족 시 안내 링크만 제공하고 wizard 자체는 끝까지 완주. |
| **Idempotent State** | 영속 상태 파일로 "이미 본/완료한" 판정. 플러그인 업데이트나 reinstall이 wizard 재실행을 유발하지 않음. |
| **Pluggable Extension** | 새 플러그인 추가 시 `pages/{plugin-id}.md` 파일 동봉만으로 wizard 자동 등록. |

## 3. 아키텍처

claude-kit 마켓플레이스 자체는 hook을 정의할 수 없어요. Claude Code의 플러그인 시스템에서 `marketplace.json`은 `plugins[].source` 경로만 보유하고, hook은 각 plugin의 `plugin.json`/`hooks/` 안에서만 등록되거든요. 따라서 wizard 책임을 **신설 4번째 플러그인 `claude-kit-welcome`** 에 격리해요.

```
┌─────────────────────────────────────────────────────────────┐
│  claude-kit (marketplace)                                   │
│  ├─ claude-kit-welcome   ← wizard 책임 (NEW)                │
│  │   ├─ SessionStart hook (1회 안내)                        │
│  │   ├─ /welcome slash command (명시 호출)                  │
│  │   └─ welcome skill (페이지 orchestration)                │
│  ├─ thinking-tools       ← 변경 없음                        │
│  ├─ obsidian-vault-manager ← 변경 없음                      │
│  └─ vault-bridge         ← 변경 없음 (manifest hook과 독립) │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ reads/writes
┌─────────────────────────────────────────────────────────────┐
│  ~/.claude/.claude-kit/                                     │
│  ├─ state.json     (영속, wizard 메타)                      │
│  └─ progress.json  (임시, 24h TTL)                          │
└─────────────────────────────────────────────────────────────┘
```

`claude-kit-welcome`은 다른 플러그인 감지를 위해 캐시 디렉토리(`~/.claude/plugins/cache/`)를 스캔하지 않고, 대신 마켓플레이스 매니페스트(`~/.claude/plugins/marketplaces/Lyainc-claude-kit/.claude-plugin/marketplace.json`)를 직접 파싱해요. 캐시 디렉토리 구조 변경에 더 강건하고, "마켓플레이스가 무엇을 제공하는지"의 source of truth를 따르는 거예요.

분리 근거 토론은 [`transcripts/02_session-start-hook.md`](../discussions/20260512_setup-wizard-design/transcripts/02_session-start-hook.md) 참조.

## 4. 디렉토리 구조

### 마켓플레이스 리포지토리

```
claude-kit/
├── .claude-plugin/
│   └── marketplace.json              # claude-kit-welcome을 첫 위치/recommended로 추가
├── claude-kit-welcome/                # 신설 4번째 플러그인
│   ├── .claude-plugin/plugin.json
│   ├── hooks/
│   │   ├── hooks.json                 # SessionStart 훅 등록
│   │   └── session-start-welcome.sh   # 1회 안내 + grace 판정
│   ├── commands/
│   │   └── welcome.md                 # /welcome 슬래시 (--new, --replay, --reset, --uninstall)
│   └── skills/
│       └── welcome/
│           ├── SKILL.md               # wizard orchestration logic
│           └── pages/
│               ├── 00-hub.md          # 입구 페이지 (multi-select)
│               ├── thinking-tools.md
│               ├── obsidian-vault-manager.md
│               ├── vault-bridge.md
│               └── 99-closing.md      # 종료 페이지 (3지 액션)
├── thinking-tools/                    # 기존 그대로
├── obsidian-vault-manager/            # 기존 그대로
└── vault-bridge/                      # 기존 그대로
```

### 사용자 홈 디렉토리

```
~/.claude/.claude-kit/                 # 모든 wizard 상태를 단일 디렉토리에 격리
├── state.json                         # 영속 메타
└── progress.json                      # 임시 진행 상태 (24h TTL, 자동 정리)
```

`CLAUDE_CONFIG_DIR` 환경변수가 설정되면 그 경로를 따라요(OMC 컨벤션과 동일). uninstall 시 `rm -rf ~/.claude/.claude-kit/` 한 번으로 정리되도록 디렉토리 격리를 선택했어요. 위치 결정 근거는 [`transcripts/01_state-file-location.md`](../discussions/20260512_setup-wizard-design/transcripts/01_state-file-location.md) 참조.

본문 페이지를 플러그인 단위로 분리한 근거는 [`transcripts/04_content-separation.md`](../discussions/20260512_setup-wizard-design/transcripts/04_content-separation.md) 참조.

## 5. 상태 관리

### state.json 스키마 (영속)

```json
{
  "firstShownAt": "2026-05-12T10:00:00+09:00",
  "shownCount": 1,
  "setupCompleted": null,
  "dismissedAt": null,
  "setupVersion": "1.0.0",
  "pagesViewed": ["00-hub", "vault-bridge"],
  "pluginsConfigured": ["vault-bridge"]
}
```

| 필드 | 타입 | 의미 |
|------|------|------|
| `firstShownAt` | ISO8601 \| null | SessionStart 안내가 처음 표시된 시각 |
| `shownCount` | integer | SessionStart 안내가 표시된 누적 횟수 |
| `setupCompleted` | ISO8601 \| null | `/welcome` 종료 페이지에서 "마침"을 선택한 시각 |
| `dismissedAt` | ISO8601 \| null | 종료 페이지에서 "이 wizard 다시 안 보기"를 선택한 시각 |
| `setupVersion` | semver | wizard 완료 시점의 `claude-kit-welcome` 버전 (신규 콘텐츠 감지용) |
| `pagesViewed[]` | string[] | 사용자가 실제로 본 페이지 ID 목록 (frontmatter의 id 필드 또는 파일명) |
| `pluginsConfigured[]` | string[] | wizard 안에서 사용자가 직접 설정한 플러그인 ID (선택적 — 액션 강요 안 함이라 0개가 정상) |

### progress.json 스키마 (임시)

`/welcome` 실행 중간에 사용자가 세션을 중단한 경우 재개를 돕기 위한 임시 파일이에요. 24시간 경과 시 자동 무효화되며, 종료 페이지 도달 시 즉시 삭제돼요.

```json
{
  "startedAt": "2026-05-12T10:00:00+09:00",
  "selectedPages": ["thinking-tools", "vault-bridge"],
  "currentIndex": 1
}
```

### Silent 조건

SessionStart hook이 안내를 표시할지 결정하는 로직:

```
표시 = (
  state.json 없음
  OR shownCount < 3
) AND (
  setupCompleted == null
  AND dismissedAt == null
)
```

C 절충형 dismissal 전략 — 첫 노출 후 3 세션까지 grace, 사용자가 명시 행동(완료/거부) 하면 즉시 종료. 결정 근거는 Stage 1 Discovery에서 사용자 확인.

## 6. 사용자 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  Case A: 첫 SessionStart (state.json 없음)                      │
├─────────────────────────────────────────────────────────────────┤
│  hook → systemMessage 표시:                                     │
│    "claude-kit 플러그인이 감지됐어요.                           │
│     `/welcome` 으로 짧은 안내를 받아보세요."                    │
│  state.json 생성, shownCount=1                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Case B: 2-3번째 SessionStart (grace period)                    │
├─────────────────────────────────────────────────────────────────┤
│  shownCount < 3 && setupCompleted==null && dismissedAt==null    │
│  → 동일 안내 재노출, shownCount 증가                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Case C: 4번째 이상 SessionStart 또는 사용자 행동 완료           │
├─────────────────────────────────────────────────────────────────┤
│  shownCount >= 3 OR setupCompleted OR dismissedAt               │
│  → 침묵 (안내 표시 안 함)                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Case D: /welcome 실행 (사용자 명시 호출)                       │
├─────────────────────────────────────────────────────────────────┤
│  1. pages/ 스캔                                                  │
│  2. marketplace.json 파싱 → 설치된 플러그인 목록 확보            │
│  3. frontmatter `appliesTo` 매칭으로 노출할 페이지 필터링        │
│  4. 입구 페이지 → AskUserQuestion (multiSelect)                  │
│     "어떤 플러그인부터 볼까요?"                                 │
│     [thinking-tools / OVM / vault-bridge / 모두 / 건너뛰기]     │
│  5. 선택된 페이지를 순차 표시 (AskUserQuestion 없이)             │
│     각 페이지 끝에 "── 다음: {next title}" 표지                 │
│  6. 종료 페이지 → AskUserQuestion (single)                       │
│     "마침 / 추가 페이지 보기 / 이 wizard 다시 안 보기"           │
│  7. state.json 업데이트 (pagesViewed 누적, 종료 조건 기록)       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Case E: 마켓플레이스 업데이트 후                               │
├─────────────────────────────────────────────────────────────────┤
│  setupVersion 차이 감지 + pages/에 새 파일 발견                 │
│  → SessionStart에서 짧은 알림                                   │
│    "claude-kit에 새 안내가 추가됐어요.                          │
│     `/welcome --new` 로 확인하세요."                            │
│  /welcome --new 는 pagesViewed에 없는 페이지만 노출             │
└─────────────────────────────────────────────────────────────────┘
```

UX 결정 근거는 [`transcripts/03_pagination-ux.md`](../discussions/20260512_setup-wizard-design/transcripts/03_pagination-ux.md) 참조.

## 7. 페이지 콘텐츠 가이드

각 페이지(`pages/*.md`)는 다음 frontmatter를 가져요:

```yaml
---
title: "thinking-tools — 사고 도구 7종"
order: 10
appliesTo: thinking-tools     # null이면 항상 표시 (hub/closing 전용)
enabled: true
---
```

| frontmatter 필드 | 의미 |
|------------------|------|
| `title` | 입구 multi-select 옵션 라벨, 페이지 헤더로도 사용 |
| `order` | 정렬 키. 00-hub은 0, 99-closing은 99, 플러그인은 10/20/30… |
| `appliesTo` | 매칭 플러그인 ID. marketplace.json의 `plugins[].name`과 비교. null이면 모든 환경에서 표시 |
| `enabled` | false면 스캔에서 제외 (drafting/maintenance 용도) |

**본문 길이**: 8~12줄 권장. 너무 짧으면 페이지네이션이 무겁게 느껴지고, 너무 길면 관조형의 '읽는 흐름'을 깨요.

**톤**: claude-kit 전체 언어 정책(skill body는 영어, user-facing은 한국어 해요체)에 맞춰 페이지 본문은 한국어 해요체. 코드 예시는 영어 유지.

**구성 패턴**:

```markdown
---
title: "..."
order: 10
appliesTo: thinking-tools
enabled: true
---

## 한 줄 소개
(이 플러그인이 무엇을 해결하는지 — 1줄)

## 대표 기능 2-3개
- 기능 A: ...
- 기능 B: ...

## 어떻게 써요?
간단한 트리거 예시 1-2개 (코드/명령어)

## 더 알아보기
- README: [링크]
- 핵심 스킬: [링크]
```

## 8. 확장 방법

새 플러그인을 claude-kit 마켓플레이스에 추가할 때, contributor는 wizard 페이지를 동봉해야 해요. 절차는 단순해요.

1. 새 플러그인 디렉토리 추가 (예: `claude-kit/new-plugin/`)
2. `marketplace.json`에 `plugins[]` 항목 추가
3. `claude-kit-welcome/skills/welcome/pages/{new-plugin-id}.md` 작성 (위 가이드 따름)
4. `claude-kit-welcome` 의 `plugin.json` version bump (사용자에게 새 콘텐츠 알림 트리거)

페이지를 누락한 채로 마켓플레이스에 추가하면 wizard 입구 multi-select에서 자동으로 fallback 항목으로 분류돼요. fallback 페이지는 "(이 플러그인의 상세 안내가 아직 없어요. README를 참조하세요)" 1줄 + 플러그인 README 링크로 자동 구성되며, 실제 파일이 추가되면 자동으로 교체돼요.

확장 결정 근거는 [`transcripts/05_extensibility.md`](../discussions/20260512_setup-wizard-design/transcripts/05_extensibility.md) 참조.

## 9. 구현 로드맵

### P0 — 구현 시작 전 확정 사항

- [ ] 4번째 플러그인 이름 확정: `claude-kit-welcome` 후보 (대안: `claude-kit-tour`, `claude-kit-onboarding`)
- [ ] `state.json` / `progress.json` JSON Schema 파일 작성 및 commit
- [ ] 페이지 frontmatter 스키마 명세 commit (이 문서의 §7을 SSOT로 인용)
- [ ] AskUserQuestion `multiSelect` 최대 옵션 갯수 검증 (현재 schema 상 `maxItems: 4` — 5개 옵션 필요 시 분할 전략 명세)

### P1 — 코어 구현

- [ ] `claude-kit-welcome` 플러그인 디렉토리 스캐폴드
- [ ] `hooks/hooks.json` 작성 (SessionStart 등록)
- [ ] `hooks/session-start-welcome.sh` 구현 (deterministic shell, jq 기반 state 판정, systemMessage 출력)
- [ ] `commands/welcome.md` 작성 (플래그: `--new`, `--replay`, `--reset`, `--uninstall`)
- [ ] `skills/welcome/SKILL.md` 구현 (페이지 스캔 → 매칭 → multi-select → 순차 표시 → 종료 액션 → state 업데이트)
- [ ] `pages/00-hub.md`, `pages/99-closing.md` 작성
- [ ] `pages/thinking-tools.md`, `pages/obsidian-vault-manager.md`, `pages/vault-bridge.md` 초안 작성
- [ ] `marketplace.json`에 `claude-kit-welcome` 첫 위치/recommended 등록

### P2 — 운영·확장 준비

- [ ] `CONTRIBUTING.md`에 "마켓플레이스에 플러그인 추가 시 `pages/{id}.md` 동봉 필수" 섹션 추가
- [ ] fallback 페이지 자동 생성 로직 (페이지 없는 플러그인 발견 시)
- [ ] `setupVersion` 비교 + 신규 페이지 감지 로직
- [ ] `/welcome --new` 옵션 구현 (pagesViewed 빈 페이지만 노출)
- [ ] (선택) `omc-doctor` 스타일의 `/welcome --diagnose` — state.json 무결성 검사

### P3 — 미래 작업

- [ ] i18n 확장: `pages/{name}.{locale}.md` 형식 (현재 ko 단일, 향후 en 등 추가 가능)
- [ ] AskUserQuestion preview 활용 (페이지 미리보기를 옵션 카드에 ASCII 미니어처로 표시)
- [ ] state.json 마이그레이션 핸들러 (schema 변경 시 hands-free 업그레이드)

## 10. 미해결 검증 항목

토론 단계에서 합의됐으나 구현 단계에서 실측이 필요한 항목이에요. UNRESOLVED 토론 주제는 없지만, dogfooding으로 검증해야 할 가정 4개를 명시해요.

| # | 항목 | 검증 방법 | 위험도 |
|---|------|-----------|--------|
| 1 | AskUserQuestion `maxItems: 4` 제약 | 플러그인 4개 이상 환경에서 입구 multi-select 분할 동작 확인 | Medium |
| 2 | SessionStart systemMessage 길이 캡 | vault-bridge `pre-access-guard` 경험치(N=1,5,10) 참고. 시작값 3-5줄(≈200자) 제안, dogfooding으로 조정 | Low |
| 3 | 단일 응답 내 N개 페이지 연속 출력 가능성 | prototype 작성 후 페이지 3-4개 묶음이 자연스럽게 출력되는지 확인. 끊기면 페이지마다 응답 분리 필요 | Medium |
| 4 | claude-kit-welcome 자체 이름 (brand voice) | i18n/Voice 검토 후 P0에서 확정 | Low |

상세 — [`UNRESOLVED.md`](../discussions/20260512_setup-wizard-design/UNRESOLVED.md).

---

## 참고

- **Stage 1 Discovery 결과**: 본 conversation transcript (저장 위치는 vault-bridge `/save-session` 로 채움 가능)
- **Stage 2 Expert Panel 토론**: [`docs/discussions/20260512_setup-wizard-design/`](../discussions/20260512_setup-wizard-design/)
  - [`SUMMARY.md`](../discussions/20260512_setup-wizard-design/SUMMARY.md) — 5 토픽 합의 압축
  - [`transcripts/`](../discussions/20260512_setup-wizard-design/transcripts/) — 토픽별 대화록
  - [`UNRESOLVED.md`](../discussions/20260512_setup-wizard-design/UNRESOLVED.md) — 구현 단계 검증 항목
- **레퍼런스 패턴**: OMC `omc-setup` (`~/.claude/plugins/cache/omc/oh-my-claudecode/<ver>/skills/omc-setup/`) — phases 분리, setupCompleted 메타, 그레이스풀 resume
- **외부 레퍼런스**: VS Code activation events (1회 표시), oh-my-zsh update prompt (N-session grace), npm `update-notifier` (timestamp throttle)

───
*10개 섹션 작성 완료 · 검토 통과*
