# Topic 2: fork-worthiness 스코어링 — capture fork 불필요론

**Date**: 2026-05-17
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Plugin Architect, Cost/Infra Expert, Telemetry Expert, LLM Routing Expert

---

**[Optimistic Practitioner]**: 재설계안은 정적 Tier map 대신 skill별 fork-worthiness를 계산하자고 한다. 그 렌즈로 보면 capture는 fork 불필요다. 입출력이 작다 — 입력은 짧은 메모, 출력은 파일 경로 한 줄. opus로 돌아도 건당 비용이 작고, fork 오버헤드(subagent 초기화 + 시스템프롬프트 재로드)가 그 절감분을 까먹는다.

**[Critical Practitioner]**: 반론 둘. 하나, capture는 호출 빈도가 높다 — 작은 건당 차이도 누적되면 무시 못 한다. 둘, 더 중요한 건 입력 분포다. capture가 URL을 받으면 Defuddle parse 결과가 웹페이지 본문 통째다. 수천 토큰이 부모 context에 쌓인다. 그게 cost-optimization-panel이 1차 문제로 지목한 >150k 누적에 직접 기여한다. context 보호 관점에선 capture도 fork 가치가 있다.

**[Cost/Infra Expert]**: 핵심 변수가 드러났다 — **URL 캡처 비율**이다. 텍스트 메모 캡처면 fork 무가치, URL 캡처면 fork 가치 높음. 단일 정적 결정이 두 케이스에 동시에 맞을 수 없다.

**[LLM Routing Expert]**: 이상적 해법은 조건부 라우팅이다 — URL이면 fork, 텍스트면 main. 그런데 frontmatter `context: fork`는 정적이다. 조건부가 안 된다. skill 본문이 입력을 보고 분기하려 해도, 본문이 실행되는 시점엔 이미 모델이 정해진 뒤다.

**[Plugin Architect]**: 조건부 fork는 현 메커니즘으로 불가능하다. 차선책은 always-fork to haiku다. 기대값으로 판단한다 — URL 비율 p, fork 오버헤드 C_o, URL 케이스 보호 이득 G일 때:

```
always-fork 유리 ⟺ p·G > (1-p)·C_o
```

fork 대상이 haiku(vault-file-organizer)면 C_o가 작다. URL 케이스의 G(수천 토큰 context 보호 + 모델 델타)는 크다. p가 적당히만 돼도 부등식이 성립한다.

**[Moderator]**: 그러면 capture는 fork한다 안 한다 어느 쪽인가?

**[Cost/Infra Expert]**: 측정 없이는 확정 못 한다. p(URL 비율)가 미지수다. 잠정으론 always-fork to haiku — URL 케이스의 보호 가치가 크고 텍스트 케이스의 오버헤드는 haiku라 작다. 단 p를 측정해 부등식을 확인한 뒤 확정한다.

**[Telemetry Expert]**: p는 telemetry로 측정 가능하다. capture `skill_invoke` 이벤트의 `meta`에 입력이 URL인지 플래그를 넣으면 비율이 나온다. 단 이건 schema 변경이라 Topic 3과 충돌 — 거기서 다룬다.

**[Optimistic Practitioner]**: 입력 분포 논점은 인정한다. "capture fork 불필요"는 텍스트-only 가정이었다. URL 케이스를 넣으면 always-fork-haiku로 기운다.

---

**결론**: 합의 — fork-worthiness는 스칼라가 아니라 **입력 분포에 대한 기대값**
- capture는 URL 캡처 비율 p에 좌우됨. 측정 없이 정적 결정 불가 (측정 선행의 정당화)
- 조건부 fork(URL이면 fork)는 정적 frontmatter로 구현 불가
- **잠정안**: capture는 always-fork to vault-file-organizer(haiku). URL 비율 측정 후 `p·G > (1-p)·C_o` 확인하여 확정
- 원안의 "capture = 1순위, 호출 빈도 높음" 논리는 입력 분포를 무시한 것 — 폐기
