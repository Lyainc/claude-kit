# Topic 1 — 상태 파일 위치

**날짜**: 2026-05-12
**참가자**: Moderator, Optimistic Practitioner, Critical Practitioner, DX Expert, Plugin Architecture Expert, State Management Expert, i18n/Voice Expert, Operations/KPI Expert

## Briefing

claude-kit wizard의 영속 상태(setupCompleted, shownCount, dismissedAt 등)와 임시 진행 상태를 어디에 저장할 것인가.

- 옵션 A: `~/.claude/.claude-kit-config.json` (OMC `.omc-config.json` 패턴 차용)
- 옵션 B: `~/.claude/plugins/cache/Lyainc-claude-kit/.config.json` (플러그인 캐시 내부)
- 옵션 C: 양쪽 다 — 영속 메타는 A, 임시 progress는 캐시 내부

## Q&A

**[Optimistic Practitioner]**: 옵션 A가 가장 깔끔해요. OMC와 같은 위치 컨벤션이라 사용자가 익숙하고, 플러그인 uninstall/reinstall 시에도 살아남아서 "이미 끝났던 wizard 다시 안 떠요" 경험을 보장하거든요.

**[Critical Practitioner]**: 근데 `.claude-kit-config.json`이 OMC의 `.omc-config.json`과 같은 디렉토리에 살면 사용자 입장에선 "claude-kit이 뭔데 글로벌 config를 만들지?"가 의문이에요. 마켓플레이스가 그 권한이 있나요?

**[Plugin Architecture Expert]**: Claude Code의 표준 플러그인 컨벤션은 plugin이 자기 디렉토리 안에서 self-contained하게 살아야 한다는 거거든요. 단, 플러그인 캐시는 update할 때 새 버전 디렉토리로 분리되니까(`1.7.0/`, `1.8.0/`) — 캐시 안에 상태 파일 두면 업데이트마다 day-0 wizard가 다시 트리거돼요. 그건 치명적이에요.

**[State Management Expert]**: 양쪽 단점 다 잡으려면 옵션 C가 맞아요. 단, 디렉토리 통합으로. **영속 메타 = `~/.claude/.claude-kit/state.json`** (이름으로 출처 명확, OMC 컨벤션 따름, version-agnostic). **임시 progress = `~/.claude/.claude-kit/progress.json`** (같은 디렉토리). uninstall 시 사용자가 `rm -rf ~/.claude/.claude-kit/`로 한 번에 정리.

**[Operations/KPI Expert]**: 측정 관점에서는 영속 파일 한 곳이면 충분해요. `state.json`에 `firstShownAt`, `shownCount`, `setupCompleted`, `dismissedAt`, `setupVersion`, `pagesViewed[]`, `pluginsConfigured[]` 다 한 파일에 모이면 join 비용 없어요.

**[DX Expert]**: 사용자가 `~/.claude/` 안에 파일들 많아지는 걸 싫어할 수 있어요. 단일 디렉토리(`.claude-kit/`)로 묶는 게 시각적으로 깔끔.

## Dialectic

| 단계 | 내용 |
|------|------|
| **Thesis** | 옵션 A — `~/.claude/.claude-kit-config.json` (OMC 패턴 미러) |
| **Antithesis** | 옵션 B — 플러그인 캐시 내부 (self-contained 원칙) |
| **Synthesis** | 옵션 C 변형 — `~/.claude/.claude-kit/` 디렉토리 격리 |

## 결론

**옵션 C 채택 — 디렉토리 통합**

- **영속 상태**: `~/.claude/.claude-kit/state.json`
  - 필드: `firstShownAt`, `shownCount`, `setupCompleted`, `dismissedAt`, `setupVersion`, `pagesViewed[]`, `pluginsConfigured[]`
- **임시 진행**: `~/.claude/.claude-kit/progress.json` (24h TTL)
- **`CLAUDE_CONFIG_DIR` 환경변수 존중** (OMC 패턴 따름)
- uninstall 시 `rm -rf ~/.claude/.claude-kit/`로 정리

## Action Items

- [ ] `~/.claude/.claude-kit/state.json` 스키마 정의 (JSON Schema)
- [ ] `~/.claude/.claude-kit/progress.json` 스키마 정의 (24h TTL 명시)
- [ ] `CLAUDE_CONFIG_DIR` 환경변수 처리 로직
- [ ] `/welcome --uninstall` 또는 동등 정리 커맨드 정의 (선택)
