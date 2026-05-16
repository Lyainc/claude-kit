# Topic 4: 실행 순서 — facilitator 먼저 vs 측정 먼저

**Date**: 2026-05-17
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Plugin Architect, Cost/Infra Expert, Telemetry Expert, LLM Routing Expert

---

**[Optimistic Practitioner]**: 재설계안은 Phase 0 측정 → Phase 1 facilitator → Phase 2 fork-worthiness 순서다. 그런데 facilitator 다운그레이드는 2026-04-16 cost-optimization-panel이 이미 승인했다. frontmatter `model:` 한 줄 변경 + 경계케이스 10개 라우팅 테스트(그 패널 UNRESOLVED Issue 2에 정의됨)면 끝난다. 측정 인프라를 기다릴 이유가 없다.

**[Critical Practitioner]**: 측정 없이 먼저 풀면 효과를 정량화하지 못한다. 패널 승인은 "해도 된다"이지 "효과가 이만큼"이 아니다. facilitator를 먼저 풀어버리면 이후 fork-worthiness 결정의 보정 기준점이 사라진다.

**[LLM Routing Expert]**: 두 사람 다 절반씩 맞다. 구분이 빠졌다 — facilitator는 fork가 아니라 **순수 model 변경(축 A 단독)**이다. fork-worthiness 스코어링(축 A+B)과 메커니즘이 다르다. 그러니 같은 선형 Phase에 둘 이유가 없다. 별도 트랙으로 병렬화해야 한다.

**[Telemetry Expert]**: 그리고 facilitator는 측정의 가장 깨끗한 *첫 샘플*이 될 수 있다. 다운그레이드 전후로 telemetry 라우팅 정확도(skill_invoke outcome 분포) + 벤치마크 토큰을 둘 다 떠두면, 그 측정값이 이후 모든 fork-worthiness 결정의 검량선(calibration baseline)이 된다. "facilitator 먼저"와 "측정 먼저"는 양립한다 — facilitator를 측정하면서 푸는 것이다.

**[Cost/Infra Expert]**: 동의한다. 선형 Phase가 아니라 **2트랙 병렬**이 맞다. 트랙마다 게이트가 다르다 — facilitator 트랙의 리스크는 토큰이 아니라 라우팅 정확도이고, fork-worthiness 트랙의 리스크는 fork 메커니즘 동작 여부와 토큰 회수율이다.

**[Plugin Architect]**: 게이트를 명시하자. facilitator 트랙은 경계케이스 10개 ≥95% 정확도. fork-worthiness 트랙은 — 그 전에 짚을 게 있다. `context: fork + agent:`가 **커스텀 플러그인 에이전트**로 동작하는지가 미검증이다. 기존 사례는 `agent: Explore`(Claude Code 내장)뿐이다. 이게 안 되면 트랙 B 전체가 무너진다. 트랙 B의 첫 게이트는 측정이 아니라 fork PoC다.

**[Critical Practitioner]**: 그 지적이 맞다. 트랙 B는 "fork PoC → 측정 → fork-worthiness 적용" 순서다. PoC가 실패하면(커스텀 에이전트 fork 불가) 트랙 B는 폐기, 트랙 A(facilitator)만 살아남는다. 사용자가 앞서 "fork 안 되면 전체 폐기"라고 했지만, 정확히는 트랙 B만 폐기다 — 트랙 A는 fork를 안 쓰므로 영향받지 않는다.

**[Moderator]**: 정리하면 2트랙, 트랙 B는 PoC 게이트가 최선두인가?

**[Plugin Architect]**: 그렇다.

---

**결론**: 합의 — 선형 Phase 폐기, **2트랙 병렬** 재구성

| 트랙 | 내용 | 메커니즘 | 게이트 (순서대로) |
|------|------|---------|------------------|
| **A** | facilitator sonnet→haiku | 축 A 단독 (`model:` frontmatter) | 경계케이스 10개 ≥95% 라우팅 정확도 |
| **B** | fork-worthiness 라우팅 | 축 A+B (`context: fork`) | ① 커스텀 에이전트 fork PoC → ② 벤치마크+telemetry 측정 → ③ 적용 |

- 트랙 A는 측정 인프라와 동시 착수, 측정 *완료*를 안 기다림 (패널 기승인). 전후 측정값은 트랙 B 검량선
- 트랙 B의 첫 게이트는 **fork PoC** — 실패 시 트랙 B만 폐기, 트랙 A는 무영향 (fork 미사용)
- 사용자의 "fork 안 되면 전체 폐기"는 정확히는 "트랙 B 폐기"로 재해석
