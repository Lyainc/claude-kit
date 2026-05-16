# Topic 3: 측정 gap — telemetry 토큰 측정 보강

**Date**: 2026-05-17
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Plugin Architect, Cost/Infra Expert, Telemetry Expert, LLM Routing Expert

---

**[Optimistic Practitioner]**: fork-worthiness 계산엔 건당 토큰 델타가 필요하다. telemetry는 지금 이벤트만 찍고 토큰은 안 찍는다. 스키마에 `meta.tokens` 필드를 추가하면 된다 — PostToolUse(Skill/Agent) hook이 tool_response를 받을 때 usage 정보를 캡처한다.

**[Telemetry Expert]**: 안 된다. telemetry README의 Phase 2 진입 기준이 명시돼 있다 — `validate-schema --since=7d`가 **schema 변경 0건**을 보일 것. 지금 telemetry는 schema-freeze 상태로 1주 안정성을 측정 중인 W1 dogfooding 단계다. `meta.tokens`를 추가하면 그 측정이 리셋되고 W1 Phase Gate(W4 D28)와 정면 충돌한다.

**[Critical Practitioner]**: 추가로, PostToolUse(Skill/Agent) payload에 토큰 usage가 실제로 들어오는지 미검증이다. Claude Code hook이 tool_response에 usage를 노출하는지 확인된 바 없다. 없으면 빈 필드만 남고 schema만 더럽힌다.

**[Cost/Infra Expert]**: 별도 경로가 답이다. **고정입력 벤치마크** — 각 에이전트(또는 그 에이전트로 fork되는 대표 skill)에 대표 입력 3-5개를 고정하고, opus 1회 + 대상모델 1회를 실행해 `/cost` 또는 API usage로 토큰을 비교한다. 재현 가능하고, schema-free이고, telemetry에 무간섭이다.

**[LLM Routing Expert]**: 벤치마크가 정확도 면에서도 우월하다. telemetry 실사용 데이터는 입력이 매번 달라서 opus와 haiku를 같은 입력으로 비교할 수 없다 — 입력 크기가 혼란변수(confounder)다. 고정입력이라야 순수 모델 델타가 분리된다.

**[Plugin Architect]**: 역할 분담이 깔끔해진다:

| 측정 | 출처 | 측정 대상 |
|------|------|----------|
| 호출 빈도 | telemetry (기존, 무변경) | skill/agent가 얼마나 자주 호출되는가 |
| 건당 토큰 델타 | 고정입력 벤치마크 (신설) | opus 대비 대상모델의 절감폭 |

fork-worthiness = 빈도 × 건당델타. 두 입력의 출처가 다르다.

**[Telemetry Expert]**: 한 가지 보강 — Topic 2의 capture URL 비율 p도 같은 문제다. telemetry `meta`에 URL 플래그를 넣는 것도 schema 변경이다. p는 별도로, capture 입력 로그를 1-2주 수동 집계하거나, 벤치마크 입력 셋 구성 시 실제 capture 히스토리에서 URL/텍스트 비율을 한 번 표본조사하는 걸로 대체한다.

**[Moderator]**: telemetry는 손대지 않고, 토큰 측정은 독립 벤치마크로 — 합의되나?

**[Optimistic Practitioner]**: 합의한다. `meta.tokens` 추가는 W1 Phase Gate 리스크가 절감 가치보다 크다. 철회한다.

---

**결론**: 합의 — telemetry 스키마 **무변경**, 토큰 측정은 독립 벤치마크
- telemetry 스키마 동결 유지 (W1 Phase Gate `validate-schema --since=7d` 0-change 보호)
- 토큰 측정 = **고정입력 벤치마크** 신설: 에이전트별 대표 입력 3-5개, opus vs 대상모델 A/B, `/cost` 비교
- fork-worthiness 입력값 = telemetry 빈도(기존) + 벤치마크 건당델타(신설)
- capture URL 비율 p는 capture 히스토리 표본조사로 1회 측정 (telemetry meta 변경 회피)
