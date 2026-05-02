# Transcript 04 — 유지보수·진입 장벽·1-year 전망

**[Moderator]**: 장기 비용 기준.

**[Critical Practitioner]**: 1년 시나리오 —
- C: PM 기능 확장(Gantt, dep viz, release note)이 plan-orchestrator에 자연 흡수. OVM 본업 유지.
- D: OVM에 PM 기능 누적 → "큰 원숭이" 플러그인화. 5년차 OVM은 괴물.

**[Optimistic Practitioner]**: 6개월 시점에 필요하면 D → C 리팩터링 가능.

**[Plugin Architecture Expert]**: 리팩터링 비용 크다. 에이전트 이동, description 재학습, breaking change. 초기 결정 우세.

**[Project Manager]**: 장기 비용이 결정 변수. 초기 진입 장벽 한 번 vs 영구 정체성 오염. C 선호.

**[KM Expert]**: 동의. C.

**[LLM Orchestration]**: 하이브리드 제안 — C 플러그인 내 planner + executor(vault-aware wrapper) + verifier 3층 풀셋 + 진입 스킬 2개. vault 쓰기는 vault-bridge 의존, 읽기는 vault-searcher 의존. 완전 자립.

**[Optimistic]**: 3층 풀셋은 과설계. planner 하나 + OMC executor/verifier 재사용이 MVP.

**[Critical]**: MVP OK. 다만 vault-aware 쓰기(컨벤션 준수)는 OMC executor 자동 안 함. vault adapter layer는 skill 수준에서 주입.

**[Plugin Architecture]**: 타협 — planner만 신규, executor는 OMC executor + vault adapter prompt preamble 주입. 래퍼 코드는 skill 레벨.

**[Moderator]**: 정리 —
- MVP: plan-orchestrator 플러그인, planner 에이전트 1, 스킬 2(/plan-audit, /plan-consolidate), executor/verifier는 OMC 재사용, adapter preamble은 skill 수준
- V2: 필요 시 전용 executor/verifier 분화

**전원 합의.**

**결론**: C + MVP 범위 최종 채택.
