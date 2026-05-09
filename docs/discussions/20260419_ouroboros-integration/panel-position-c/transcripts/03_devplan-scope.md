# Transcript — Topic 3: dev-plan.md 스코프 축소의 부작용

**Date**: 2026-04-19
**Topic**: dev-plan.md를 "Ouroboros 통합 한정"으로 좁힐 때 기존 Phase D와 새 매트릭스의 충돌·중복 우려
**Round**: 1 (합의 도달)

---

## Briefing

**[Optimistic Practitioner]**: dev-plan을 Ouroboros 통합 한정으로 좁혀도 Phase A-E 구조는 유효해요. Phase D는 "Ouroboros 통합으로 파생된 기타 개선"으로 정의하고 살리면 돼요. 매트릭스는 더 넓은 cross-cutting 전략(W·D 매트릭스)을 다루니까 추상화 레벨이 다르고, 충돌 없이 공존 가능해요.

**[Critical Practitioner]**: **이게 제일 위험한 토픽이에요.** 기존 dev-plan Phase D 항목과 새 차별화 매트릭스가 명명까지 충돌해요. dev-plan Phase D: D1=diverse-sampling, D2=doc-concretize, D3=doc-polish, D4=expert-panel, D5=adversarial-review, D6=facilitator. 새 매트릭스 D1-D5: 페르소나 라이브러리, 발산 전략, 비-코딩 영역, 투명성 기능화, facilitator 오케스트레이터화. **ID 충돌 + D6과 D5가 둘 다 facilitator 다룸 → 실제 작업 중복 있음**. 매핑 확인 없이 분리 강행은 반대예요.

## Q&A

**[Moderator]**: 잠깐 사실 확인할게요. 두 분 — 명명 충돌이 실제로 맞나요?

**[Technical Documentation Expert]**: 맞아요. Topic 2에서 ID 재활용 금지 원칙을 합의했는데, 두 영역이 같은 D-prefix를 다른 의미로 쓰는 건 IA 위반이에요. **네임스페이스 분리가 필수**예요. 매트릭스는 다른 prefix — M1-M5 또는 R1-R5 — 권고. M(Matrix) 또는 D'(Direction)으로 가는 게 깔끔해요.

**[OSS Maintainer Expert]**: 동결 자체는 별 문제 아니에요. PEP의 `Superseded-By` 헤더처럼 dev-plan.md frontmatter에 `tracking_continued_in: thinking-tools/docs/improvement-matrix.md` 추가하면 추적성 OK. 단 내용상 중복은 별개 문제 — 매핑 표가 있어야 "이 작업이 어디 추적되나" 명확해져요.

**[Plugin Ecosystem Expert]**: 버저닝 측면에서 dev-plan 스코프 축소는 안 깨져요. Phase 완료가 thinking-tools minor 범프 트리거이고, 매트릭스 항목 완료는 별도 patch/minor 범프. 두 트리거가 명확히 분리되면 SemVer 일관성 유지돼요. 단 README나 CONTRIBUTING에 "Phase 완료 = minor 범프, matrix 항목 resolution = patch 범프 (구조 변경 동반 시 minor)" 같은 룰 명시 안 하면 누군가 어느 한쪽을 놓쳐요.

**[Critical Practitioner]**: 네임스페이스 분리(D vs M)는 동의해요. 그 전제 하에 dev-plan Phase D 유지 + 매트릭스 M1-M5는 추상화 레벨이 다른 cross-cutting concern으로 정의하면 중복 회피 가능. 단 **dev-plan Phase D ↔ matrix M 매핑 표가 양쪽 문서에 명시되어야 해요**. 한쪽만 있으면 다른 쪽 읽는 사람이 "이거 뭐랑 관련 있는지" 모르고 넘어가요.

**[Optimistic Practitioner]**: 매핑 표 동의해요. 분석해보면:

| Phase D (실행) | Matrix M (전략) | 관계 |
|---------------|-----------------|------|
| D1 diverse-sampling | M2 발산 전략 | M2 일부 |
| D2 doc-concretize | M4 투명성 (cross-cut) | 간접 |
| D3 doc-polish | M4 (cross-cut) | 간접 |
| D4 expert-panel | M1 페르소나 | M1 활용 |
| D5 adversarial-review | M1 (Attacker) | M1 활용 |
| D6 facilitator | M5 오케스트레이터 | M5의 1단계 |

D는 M의 구체 인스턴스 또는 직접 활용 작업이에요. 중복이 아니라 의존 관계로 정리돼요.

**[Critical Practitioner]**: 그 매핑 표가 양쪽에 들어가면 우려 해소돼요. 그리고 dev-plan에 `Scope Note (frozen)` 섹션 추가해서 "이 dev-plan은 Ouroboros 통합 한정, 전반 개선은 matrix 참조"라고 못박아 주세요. 안 그러면 6개월 뒤 누가 보고 "왜 이 dev-plan은 X 안 다루나" 물어볼 거예요.

**[Technical Documentation Expert]**: PEP `Superseded-By`처럼 양방향 추적 필수예요. dev-plan frontmatter에 `tracking_continued_in: matrix path`, matrix frontmatter에 `source_discussions: [discussion path]` — 이미 합의된 사항이니 그대로 적용.

## Dialectic

**[Thesis — Optimistic]**: Phase D 유지, 매트릭스 별도 추상화 레벨로 공존.

**[Antithesis — Critical]**: 명명 충돌과 작업 중복 실재. 매핑 명시 없이는 위험.

**[Synthesis]**: Position C 채택, 단 다음 3종 보완:
1. **ID 네임스페이스 분리**: 매트릭스는 M1-M5 prefix 사용 (D 충돌 회피)
2. **매핑 표 양쪽 문서 명시**: dev-plan과 matrix 모두에 D ↔ M 매핑 표
3. **Forward pointer**: dev-plan frontmatter `tracking_continued_in:` + Scope Note 섹션

## 결론

**합의 (조건부)**: Position C 채택, 위 3종 보완 동시 도입 전제.

**Confidence**: High (5명 전원, Critical Practitioner는 최초 강한 우려에서 보완 후 동의로 전환)

## Action Item Recap

- dev-plan.md frontmatter에 `status: frozen`, `frozen_at: 2026-04-19`, `tracking_continued_in: thinking-tools/docs/improvement-matrix.md` 추가
- dev-plan.md에 `## Scope Note` 섹션 추가
- dev-plan.md에 `## Phase D ↔ Matrix M 매핑` 표 추가
- improvement-matrix.md ID는 M1-M5 prefix 사용 (D와 격리)
- improvement-matrix.md에도 동일 매핑 표 포함
