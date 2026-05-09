# Topic 5: context Skill Fork Removal

**Date**: 2026-04-16
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Cost/Infra Expert, Plugin Architect, UX Expert

---

**[Optimistic Practitioner]**: context 스킬은 `context: fork` + `agent: Explore`로 별도 에이전트를 spawn한다. 내부 로직은 MOC 읽기 + Grep 검색인데, fork 없이 직접 실행하면 subagent 1회를 절약한다.

**[Critical Practitioner]**: fork가 있는 이유를 생각해야 한다. vault 탐색은 많은 파일을 읽고 검색하면서 context를 빠르게 소비한다. fork로 분리하면 탐색 결과만 요약되어 부모 context로 돌아오므로, 부모 세션의 context 오염을 방지한다. fork를 제거하면 vault 탐색의 모든 중간 결과가 부모 context에 쌓여서 >150k 문제를 오히려 악화시킨다.

**[Cost/Infra Expert]**: 핵심적인 지적이다. fork는 subagent 비용을 추가하지만, 부모 context를 보호한다. 부모 context가 150K에 도달하면 compaction이 발생하고, 중요한 이전 context가 손실될 수 있다. fork의 비용은 subagent 1회(~$0.01-0.03)이고, context 오염의 비용은 세션 전체 품질 저하다. 비용 대비 효과가 역전된다.

**[Plugin Architect]**: Explore 에이전트 타입은 탐색 특화 에이전트로, 파일 패턴 매칭과 검색에 최적화되어 있다. 일반 컨텍스트에서 직접 Grep/Read를 실행하는 것보다 구조적으로 더 나은 탐색 결과를 제공한다. fork 제거는 탐색 품질도 낮출 수 있다.

**[UX Expert]**: fork 분리는 사용자 체감 지연을 추가한다(에이전트 초기화 시간). 하지만 이후 세션의 context 품질을 보호한다. 단기 지연 vs 장기 품질의 트레이드오프에서, vault 작업처럼 세션이 긴 경우 fork 유지가 유리하다.

---

**결론**: 합의 -- fork 유지 권장
- fork 제거 시 vault 탐색 중간 결과가 부모 context를 오염
- >150k context 문제를 악화시키는 역효과
- Explore 에이전트의 탐색 특화 이점 상실
- **우선순위: 기각 (Negative impact)**
