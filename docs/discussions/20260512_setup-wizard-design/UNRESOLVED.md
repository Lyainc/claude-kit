# UNRESOLVED — Setup Wizard 설계

**날짜**: 2026-05-12
**상태**: 5개 토픽 모두 합의 도달. **현재 미해결 토픽 없음.**

## 합의 후 검증 필요 항목 (Hold-until-implementation)

다음 항목은 토론 단계에서 합의됐으나 구현 단계에서 검증/조정이 필요해요. 본격적인 미해결이 아닌 "implementation-time decisions"로 분류.

### 1. AskUserQuestion `multiSelect: true` 옵션 갯수 제한
- **상황**: Topic 3에서 입구 multi-select으로 플러그인 선택 결정. 현재 마켓플레이스에 플러그인 3개라 옵션 5개(3 + 모두 + 건너뛰기) — 안전.
- **검증 필요**: AskUserQuestion 도구의 옵션 최대값(현재 schema는 `maxItems: 4`로 명시됨). 플러그인이 5개 이상으로 늘어나면 옵션 분할/2-step 선택 필요.
- **검증 시점**: 구현 시작 시 즉시 확인. 4-옵션 cap이 사실이면 "주요/기타" 2단계 selection 필요.

### 2. SessionStart 훅 systemMessage 길이 캡
- **상황**: Topic 2에서 `session-start-welcome.sh`가 systemMessage를 통해 1회 안내 표시 결정.
- **검증 필요**: vault-bridge의 `pre-access-guard`에서 systemMessage 캡(N=1,5,10) 경험상, 안내 메시지가 어느 길이까지 graceful한지 측정 필요. 너무 길면 Claude가 안내문 자체를 사용자 instruction으로 잘못 해석할 우려.
- **검증 시점**: 첫 구현 후 dogfooding 단계. 권장 시작값: 3-5줄 (≈ 200자).

### 3. 페이지 순차 표시의 "다음 페이지로 넘어감" 신호
- **상황**: Topic 3에서 페이지 사이에 AskUserQuestion 없이 "── 다음: {next page title}" 표지로 구분 결정.
- **검증 필요**: LLM이 단일 응답에서 N개 페이지를 한 번에 표시할지, 페이지마다 별도 응답으로 분리할지. 후자는 자동으로 사용자의 "ㅇㅇ" 같은 응답이 필요해질 수 있음.
- **검증 시점**: 구현 prototype 작성 후 첫 dogfooding. 권장: 단일 응답에 페이지 N개 연속 출력 + 종료 시 1회 AskUserQuestion.

### 4. 4번째 플러그인의 이름 (brand voice 결정)
- **후보**: `claude-kit-welcome`, `claude-kit-tour`, `claude-kit-onboarding`
- **이유**: 패널에서 i18n/Voice Expert가 짧고 명확한 이름 선호 의견. 최종 선택은 마켓플레이스 운영자 권한.
- **검증 시점**: P0 결정 단계. 다른 모든 implementation은 이름 확정 후 일관 적용.

## 미해결 토론 주제

없음. 모든 토픽에서 합의 도달.

───
*전체 5개 토픽 중 0개 보류, 4개 implementation-time 검증 항목*
