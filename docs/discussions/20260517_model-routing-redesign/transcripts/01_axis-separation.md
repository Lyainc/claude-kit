# Topic 1: 두 축 분리 — model tier vs fork

**Date**: 2026-05-17
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Plugin Architect, Cost/Infra Expert, Telemetry Expert, LLM Routing Expert

---

**[Optimistic Practitioner]**: 재설계안의 출발점은 "fork 결정과 model 결정을 분리한다"이다. 분리하면 각각 독립 최적화가 가능하다. facilitator는 fork 없이 model만 바꾸고(축 A), vault-audit는 fork + haiku를 같이 쓴다(축 A+B). 원안은 "haiku 에이전트로 fork"라는 한 동작에 두 결정을 융합했고, 그래서 capture처럼 fork가 무가치한 케이스도 강제로 fork됐다.

**[Critical Practitioner]**: 두 축이 진짜 독립인지 의심스럽다. skill을 비-opus로 실행하는 수단이 `context: fork`뿐이라면, skill 입장에서 축 A(모델)는 축 B(fork)에 종속이다. 에이전트는 `model:` frontmatter가 있지만 skill에는 없다. 분리를 주장하려면 이 비대칭을 먼저 인정해야 한다.

**[Plugin Architect]**: Critical이 정확하다. 메커니즘 매트릭스로 정리한다:

| 대상 | 모델 변경 수단 | fork 독립성 |
|------|--------------|------------|
| 에이전트 | `model:` frontmatter | 독립 (fork 없이 변경 가능) |
| skill | `context: fork + agent:` 외 없음 | 종속 (fork 통해서만 모델 결정) |

즉 축 분리는 *에이전트가 1차 시민*일 때만 성립한다. skill-first 관점에선 종속이다.

**[LLM Routing Expert]**: 그러면 함의가 분명하다. 라우팅의 단위를 skill이 아니라 **에이전트**로 잡아야 한다. 원안의 "skill→model" 직매핑(Tier H/S/O)은 존재하지 않는 수단을 가정한 것이다. 실제 구조는 "skill→agent→model" 2단 매핑이다.

**[Cost/Infra Expert]**: 동의한다. 비용 최적화의 제어점도 에이전트다. 에이전트 모델을 정하면 그 에이전트로 fork되는 모든 skill이 같은 모델을 상속한다. skill 단위로 흩어 보면 제어점이 N개로 늘지만, 에이전트 단위면 4개(vault-searcher / vault-file-organizer / vault-knowledge-manager / thinking-facilitator)로 수렴한다.

**[Moderator]**: 정리하면 — 축 분리 개념은 유효하나, 단위 재정의가 선행 조건이라는 것인가?

**[Plugin Architect]**: 그렇다. 원안의 skill별 Tier 분류는 폐기하고, agent별 Tier로 재작성해야 한다. skill은 "어느 에이전트로 fork되는가"만 정하면, 모델은 그 에이전트가 결정한다.

---

**결론**: 합의 — 축 분리는 유효, 단 **라우팅 단위를 에이전트로 재정의**
- skill은 `context: fork`를 통해서만 모델이 결정됨 → "skill→agent→model" 2단 매핑이 실제 구조
- 원안의 skill별 Tier H/S/O 분류 폐기, agent별 Tier로 재작성
- 비용 제어점은 4개 에이전트(vault-searcher, vault-file-organizer, vault-knowledge-manager, thinking-facilitator)
