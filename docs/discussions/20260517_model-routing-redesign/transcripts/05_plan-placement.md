# Topic 5: plan 배치 — 독립 문서 vs unified-dev-plan W5 편입

**Date**: 2026-05-17
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Plugin Architect, Cost/Infra Expert, Telemetry Expert, LLM Routing Expert

---

**[Optimistic Practitioner]**: 재플래닝 결과물을 어디에 둘 것인가. `unified-dev-plan-2026-05-13.md`가 현재 살아있는 마스터 plan이다. 거기 W5 워크스트림으로 편입하면 추적이 일원화되고, 별도 문서 관리 부담이 없다.

**[Critical Practitioner]**: unified-dev-plan은 W1-W4로 구성된 4주 프로그램이고, W4 D28 Phase Gate로 명확히 닫히는 구조다. W5를 붙이면 프로그램 종료 조건이 흐려진다. 또 unified plan의 워크스트림은 telemetry/thought-chain/setup-wizard라는 *기능 추가*인데, 모델 라우팅은 *비용 최적화*다. 성격이 다른 작업을 한 프로그램에 섞으면 Phase Gate 평가 기준이 모호해진다.

**[Plugin Architect]**: 결정적인 건 의존 방향이다. 모델 라우팅은 telemetry W4 Phase Gate의 *산출물*에 의존한다 — `report.py --top=10` 인사이트, schema 안정성 확인, 그리고 그 위에 얹을 벤치마크. 즉 이 plan은 unified plan의 **후속(downstream)**이지 *구성요소*가 아니다. W5로 편입하면 "W5가 W4 산출물에 의존" — 같은 프로그램 안에서 워크스트림이 서로 의존하는 꼴이라 병렬성이 깨진다.

**[Cost/Infra Expert]**: 계보(lineage)도 unified plan이 아니다. 이 plan의 직계 조상은 2026-04-16 `cost-optimization-panel`이다 — 거기서 facilitator 다운그레이드 승인, vault-knowledge-manager 보류, context fork 유지가 결정됐고, 이 재설계는 그 action item의 직접 연장이다. 추적성을 살리려면 cost-optimization-panel에 연결된 독립 plan이어야 한다.

**[Telemetry Expert]**: 보강하면 — telemetry W4 Phase Gate의 entry criteria 중 하나가 "≥1 data-gap area identified for Phase 2 backlog"다. 모델 라우팅 벤치마크가 바로 그 data-gap의 후보다. 즉 이 plan은 W4 Phase Gate를 *통과한 뒤* 그 출력을 입력으로 받아 시작하는 게 자연스럽다.

**[Optimistic Practitioner]**: 의존 방향 논점을 받아들인다. W5 편입은 의존관계를 거꾸로 그린다. 독립 문서가 맞다.

**[Moderator]**: 그러면 독립 plan, 단 의존성과 계보를 문서에 명시 — 합의되나? 위치는?

**[Plugin Architect]**: `docs/plans/`에 둔다. 파일명은 기존 `unified-dev-plan-2026-05-13.md` 컨벤션을 따라 날짜 포함. 문서 헤더에 (1) 진입 의존성 = unified-dev-plan W4 Phase Gate, (2) 계보 = `20260517_model-routing-redesign` 토론 + `20260416_cost-optimization-panel`을 명시한다.

---

**결론**: 합의 — unified-dev-plan W5 편입 **기각**, 독립 후속 plan으로 작성
- 사유: (1) 의존 방향 — 모델 라우팅은 unified plan W4 Phase Gate 산출물에 의존하는 *downstream*, (2) 성격 차이 — 기능 추가 vs 비용 최적화, (3) 계보 — 직계 조상은 `20260416_cost-optimization-panel`
- 위치: `docs/plans/` (날짜 포함 파일명, unified-dev-plan 컨벤션 준수)
- 문서 헤더에 명시: 진입 의존성 = unified-dev-plan W4 D28 Phase Gate / 계보 = 본 토론 + cost-optimization-panel(2026-04-16)
