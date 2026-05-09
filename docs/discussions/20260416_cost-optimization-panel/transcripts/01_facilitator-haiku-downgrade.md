# Topic 1: thinking-facilitator Sonnet → Haiku Downgrade

**Date**: 2026-04-16
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Cost/Infra Expert, Plugin Architect, UX Expert

---

**[Optimistic Practitioner]**: thinking-facilitator는 결정 트리 기반 라우팅만 수행한다. 6가지 스킬 중 하나를 선택하고, 강신호면 즉시 실행, 약신호면 AskUserQuestion으로 확인하는 구조다. 본질적으로 분류(classification) 작업이며 Haiku가 잘하는 영역이다. Sonnet 대비 ~60% 비용 절감이 가능하고, 91% subagent-heavy 세션에서 매번 호출되므로 누적 효과가 크다.

**[Critical Practitioner]**: 단순 라우팅이라 하지만, "다중 신호 감지 시 우선순위 결정"과 "약신호/불명확 상황에서의 의도 파악"은 미묘한 판단이다. 예를 들어 사용자가 "이 설계를 여러 관점에서 깊이 분석해줘"라고 하면 expert-panel인지 thought-chain인지 판단해야 한다. Haiku가 이런 경계 케이스를 정확히 라우팅할 수 있는가?

**[Cost/Infra Expert]**: 수치를 보면, facilitator 호출 당 평균 입력 ~2-3K 토큰(사용자 요청 + 라우팅 룰), 출력 ~200-500 토큰이다. Sonnet 기준 호출당 약 $0.01-0.02, Haiku로 내리면 $0.001-0.002. 세션당 1-2회 호출이면 절대값은 작지만, 91% 세션에서 발생하므로 전체적으로 유의미하다. 다만 비용 절감의 핵심은 facilitator 자체보다는 뒤에 오는 skill 체인 비용이 더 크다.

**[Plugin Architect]**: 구조적으로, facilitator의 라우팅 로직은 명시적 결정 트리(SKILL.md에 6개 경로 기술)이기 때문에 Haiku로 충분하다. 다만 facilitator가 파이프라인 오케스트레이션(thought-chain 같은 복합 실행)도 담당한다는 점은 고려 필요. "inter-skill pipelines when needed"라는 설명이 있어, 단순 라우팅 이상의 조율이 필요할 수 있다.

**[UX Expert]**: 사용자 관점에서 라우팅 정확도가 99%에서 95%로 떨어지면, 20번 중 1번은 잘못된 스킬이 실행된다. 혼란과 재시도가 발생한다. 그러나 현재 약신호 시 AskUserQuestion으로 확인하는 안전장치가 있으므로, Haiku에서도 작동한다면 리스크는 낮다.

**[Moderator]**: Haiku 다운그레이드에 대한 찬성 근거가 강하다. 단, 경계 케이스 검증이 필요하다.

---

**결론**: 합의 -- Haiku 다운그레이드 승인 (조건부)
- 경계 케이스 10개(다중 신호, 모호한 요청) 테스트 후 라우팅 정확도 95% 이상 확인
- 실패 시 Sonnet 복귀 경로 확보
- **우선순위: 1순위 (Low risk, High impact)**
