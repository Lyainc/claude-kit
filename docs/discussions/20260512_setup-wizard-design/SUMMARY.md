# Setup Wizard 설계 — Expert Panel SUMMARY

**날짜**: 2026-05-12
**주제**: claude-kit 마켓플레이스 첫 실행 setup wizard 고도화 설계
**참가자**: Moderator + Optimistic/Critical Practitioner + 5 Domain Experts (DX, Plugin Architecture, State Management, i18n/Voice, Operations/KPI)
**라운드**: 5개 토픽 각 1라운드, 모두 합의 도달

## 토론 개요

Stage 1 Discovery에서 확정된 8개 핵심 결정(트리거·범위·상태관리·외부의존성·튜토리얼스타일·플러그인감지·길이구조·dismissal)을 전제로, 구현 단계 트레이드오프 5개 토픽을 패널 토론으로 해소.

## 합의 사항

### Topic 1 — 상태 파일 위치
**옵션 C 변형 — 디렉토리 통합**: `~/.claude/.claude-kit/state.json`(영속) + `~/.claude/.claude-kit/progress.json`(임시, 24h TTL). 단일 디렉토리 격리로 `~/.claude/` 오염 최소화, uninstall 시 `rm -rf`로 일괄 정리. `CLAUDE_CONFIG_DIR` 환경변수 존중.

### Topic 2 — SessionStart 훅 경합
**새 4번째 플러그인 `claude-kit-welcome` 신설**: vault-bridge의 manifest 훅과 독립. 마켓플레이스 레벨 hook은 불가능하므로 별도 플러그인이 필수. `hooks/session-start-welcome.sh` + `commands/welcome.md` + `skills/welcome/SKILL.md` 구성. `marketplace.json` 첫 위치에 "recommended" 배치. 다른 플러그인 감지는 `~/.claude/plugins/marketplaces/Lyainc-claude-kit/.claude-plugin/marketplace.json` 직접 파싱.

### Topic 3 — 페이지네이션 UX
**AskUserQuestion 총 2회로 압축**:
1. 입구 multi-select: "어떤 플러그인부터 볼까요? (thinking-tools / OVM / vault-bridge / 모두 / 건너뛰기)"
2. 종료 single-select: "마침 / 추가 페이지 보기 / 이 wizard 다시 안 보기"

선택된 페이지는 AskUserQuestion 없이 순차 표시. 페이지 본문 8-12줄 가이드. `state.json.pagesViewed`에 진행 기록.

### Topic 4 — wizard 본문 분리
**플러그인 단위 분리**: `claude-kit-welcome/skills/welcome/pages/{plugin-name}.md`. frontmatter (`title`/`order`/`appliesTo`/`enabled`)로 자동 발견. `00-hub.md`/`99-closing.md` 고정 페이지. 향후 i18n은 `.ko.md`/`.en.md` 동일 디렉토리 공존.

### Topic 5 — 확장성
**3-레이어 전략**:
1. **구조 자동 인식**: `pages/*.md` 스캔으로 새 페이지 자동 등록
2. **본문 Contributor 의무**: 새 플러그인 PR에 페이지 동봉 (CONTRIBUTING.md 명시)
3. **누락 시 Fallback**: "상세 안내 없음 — README 참조" 1줄 페이지
4. **신규 콘텐츠 알림**: `setupVersion` bump + 새 페이지 발견 시 SessionStart 안내 + `/welcome --new`

## 최종 아키텍처 (합의 통합)

```
claude-kit/  (marketplace)
├── .claude-plugin/marketplace.json   # claude-kit-welcome을 첫 위치 추가
├── claude-kit-welcome/               # 신설 4번째 플러그인
│   ├── .claude-plugin/plugin.json
│   ├── hooks/
│   │   ├── hooks.json
│   │   └── session-start-welcome.sh  # 1회 안내 + grace 판정
│   ├── commands/
│   │   └── welcome.md                # /welcome 슬래시 (`--new`/`--replay`/`--reset` 플래그)
│   └── skills/
│       └── welcome/
│           ├── SKILL.md              # wizard orchestration
│           └── pages/
│               ├── 00-hub.md         # 입구 페이지 (multi-select)
│               ├── thinking-tools.md
│               ├── obsidian-vault-manager.md
│               ├── vault-bridge.md
│               └── 99-closing.md     # 종료 페이지 (3지 액션)
├── thinking-tools/                   # 변경 없음
├── obsidian-vault-manager/           # 변경 없음
└── vault-bridge/                     # 변경 없음

~/.claude/.claude-kit/                # 신설 상태 디렉토리
├── state.json                        # 영속 (firstShownAt, shownCount, setupCompleted, dismissedAt, setupVersion, pagesViewed, pluginsConfigured)
└── progress.json                     # 임시 (24h TTL)
```

## 사용자 흐름 (확정안)

1. **첫 SessionStart**: `session-start-welcome.sh` → state.json 없음 → systemMessage로 "claude-kit 플러그인 설치하신 것 같아요. `/welcome` 입력하면 짧은 안내 보실 수 있어요" 표시. state.json 생성 + `shownCount: 1`.

2. **2-3번째 SessionStart (grace)**: state.json 존재, `setupCompleted` null, `shownCount < 3` → 동일 안내 재노출. `shownCount` 증가.

3. **4번째 이상 (silent)**: `shownCount >= 3` OR `dismissedAt != null` OR `setupCompleted != null` → 안내 표시 안 함.

4. **`/welcome` 실행**: pages 스캔 → 설치 플러그인과 매칭 → 입구 multi-select → 선택된 페이지 순차 표시 → 종료 액션 (마침/추가/다시 안 보기) → state.json 업데이트.

5. **마켓플레이스 업데이트 후**: `setupVersion` 차이 + 새 페이지 발견 → SessionStart에서 "새 안내 있어요" 1줄 + `/welcome --new`로 신규만 보기.

## Action Items (전체)

### P0 (구현 시작 전 필수 결정)
- [ ] 4번째 플러그인 이름 확정 (`claude-kit-welcome` / `claude-kit-tour` / `claude-kit-onboarding`)
- [ ] `state.json` JSON Schema 정의
- [ ] `progress.json` JSON Schema 정의
- [ ] 페이지 frontmatter 스키마 확정

### P1 (구현 작업)
- [ ] `claude-kit-welcome` 디렉토리 스캐폴드
- [ ] `session-start-welcome.sh` 작성 (deterministic shell, jq 기반 state 판정)
- [ ] `welcome` slash command 작성 (multi-select 입구 + 페이지 순차 + 종료 3지)
- [ ] `pages/` 5개 초안 작성 (hub + 3 플러그인 + closing)
- [ ] `marketplace.json` 첫 위치에 항목 추가

### P2 (확장·운영)
- [ ] CONTRIBUTING.md에 페이지 동봉 의무 섹션 추가
- [ ] `/welcome --new` / `--replay` / `--reset` 플래그 명세
- [ ] Fallback 페이지 템플릿
- [ ] `setupVersion` 비교 로직
- [ ] (선택) `/welcome --uninstall`로 상태 디렉토리 정리

## 미해결 이슈

UNRESOLVED.md 참조 — 현재 모든 토픽이 합의에 도달하여 보류 없음. 단, 다음 항목은 구현 단계에서 검증 필요:
1. AskUserQuestion `multiSelect: true`의 옵션 갯수 제한 (현재 max 4 → 플러그인이 5개 이상이면 페이지네이션 분할 필요)
2. SessionStart 훅의 systemMessage 캡 (vault-bridge의 pre-access-guard 사례처럼 N=1,5,10 같은 cap 필요할 수 있음)

───
*5개 토픽 논의 완료 · 5개 합의, 0개 보류 · Stage 2 종료, Stage 3 (문서화)로 진행 가능*
