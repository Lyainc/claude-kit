# Topic 3: thought-chain Pipeline Intermediate Delegation Removal

**Date**: 2026-04-16
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Cost/Infra Expert, Plugin Architect, UX Expert

---

**[Optimistic Practitioner]**: thought-chain은 4단계 파이프라인(unknown-discovery → expert-panel → doc-concretize → doc-polish)이다. 각 단계 전환 시 체크포인트에서 facilitator를 재호출하는 구조를 제거하고 직접 AskUserQuestion으로 "계속/중단/재실행"을 물으면 불필요한 에이전트 spawn 3회를 절약한다.

**[Critical Practitioner]**: 현재 구조를 정확히 봐야 한다. thought-chain SKILL.md를 보면, 체크포인트는 thought-chain 스킬 자체가 AskUserQuestion을 호출하는 구조다. allowed-tools에 `Skill, Read, Write, AskUserQuestion`이 있고, 각 단계에서 `Skill`로 하위 스킬을 호출한다. facilitator가 중간에 개입하는 구조가 아닐 수 있다.

**[Plugin Architect]**: 정확한 지적이다. thought-chain은 자체적으로 파이프라인을 조율하는 스킬이다. facilitator는 초기 라우팅에서 thought-chain을 선택하는 역할만 한다. 이후 thought-chain 내부에서 Skill 도구로 직접 하위 스킬을 호출한다. "facilitator 재호출 제거"는 이미 해당 없는 개선안이다.

**[Cost/Infra Expert]**: 비용 이슈의 실체가 다르다. thought-chain이 Skill 도구로 하위 스킬을 호출하면, 각 스킬이 fork context에서 실행되는지가 핵심이다. SKILL.md에 `context: fork`가 없으므로 같은 컨텍스트에서 실행된다. 4개 스킬의 컨텍스트가 누적되면서 >150k에 도달하는 것이 실제 문제다.

**[UX Expert]**: 체크포인트 자체는 사용자 경험에 좋다. "다음 단계로 진행할까요?"라는 확인은 파이프라인의 투명성을 높인다. 문제는 체크포인트의 존재가 아니라 각 단계의 출력이 컨텍스트에 누적되는 것이다.

**[Moderator]**: 원래 제안("facilitator 재호출 제거")은 현재 구조에 부합하지 않는 것으로 확인됨. 실제 개선 방향을 재정의한다.

**[Plugin Architect]**: 실제 개선안: thought-chain의 각 단계를 `context: fork`로 분리하여 별도 에이전트에서 실행되게 하고, 단계 간에는 요약된 결과만 전달하는 것이다. 컨텍스트 누적 방지 가능.

**[Cost/Infra Expert]**: 하지만 fork는 각 단계마다 새 에이전트를 spawn하므로 subagent 비용이 증가한다. 91% subagent-heavy 문제를 악화시킬 수 있다. 트레이드오프가 존재한다.

---

**결론**: 원래 제안 수정 -- facilitator 재호출은 이미 해당 없음
- 대안: thought-chain 단계 간 출력 요약(compaction) 메커니즘 도입 검토
- fork 전환은 subagent 비용 증가와 트레이드오프 -- 추가 분석 필요
- **우선순위: 3순위 (재정의 필요, Medium complexity)**
