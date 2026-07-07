# spec-first 분리 — 결정 및 인계 (2026-06-02)

> **상태 (2026-06-03 갱신)**: 미해결 4개 항목(명명·웹검증·인터뷰중복·구조실행)은 전부 **#111**로 이관·통합됨. spec-first는 아직 `thinking-tools/skills/spec-first`에 물리적으로 존재(분리 미실행). 06-02 저녁 레이어 재설계가 spec-first를 goal-doc 출력 스킬(②)로 재프레임 → 별도 플러그인 분리 여부 자체가 **#102(단일 vs 분산)** 결정에 게이트됨. 아래 결정·근거·정의는 그 맥락에서 읽을 것. 분리가 확정되면 실행, 분산/흡수면 §미해결 4 폐기.
>
> **최종 결과 (2026-07-07 확인, #102/#111 둘 다 CLOSED)**: #102는 "분산 유지"(별도 플러그인 신설 안 함)로 결정됐고, #111은 spec-first를 **`build-spec`으로 리네이밍**하는 걸로 닫혔어요 — "분리"도 "폐기"도 아니라 제3의 결과(개명 후 thinking-tools 잔류)예요. `thinking-tools/skills/spec-first`는 이제 없고 `thinking-tools/skills/build-spec`이 그 자리를 대신해요. 아래 §미해결 4개 항목은 이 리네임 시점에 함께 해소된 걸로 보세요.

ouroboros 대조 분석 중 spec-first의 정체성을 재검토한 결과, thinking-tools에서 분리하기로 결정. 이 문서는 분리 트랙 전체를 정리한다. (thinking-tools 잔여 7개 고도화는 `thinking-tools-enhancement-2026-06-02.md`.)

## 결정

spec-first를 thinking-tools에서 **분리**, **별도 플러그인**으로 (claude-kit 동일 마켓플레이스 내 존속).

## 이 스킬은 무엇을 하는가 (정의)

> 모호한 아이디어를 Socratic 인터뷰로 캐묻고, 정량 게이트(Ambiguity ≤ 0.2)를 통과할 때까지 명확히 한 뒤, 요구사항 명세(Goal/Constraints/Success-criteria, YAML Seed)로 결정화하는 스킬.

- **동작 3단계**: (a) 모호함 해소 인터뷰(Socratic, 4차원) → (b) 정량 게이트 → (c) 명세 결정화(YAML Seed).
- **출력물**: `goal` + `constraints` + `success_criteria` — 고전적 요구사항 3요소. "무엇을/왜"까지이고 "어떻게"(슬라이스 순서·E2E 검증법)는 **없음**.

## 사용 지점 (언제 쓰나)

```
막연한 아이디어 ──▶ [ spec-first ] ──▶ 명확한 요구사항 ──▶ 구현
                   (구현 직전, 여기)
```

"만들 건 정했는데 *무엇을 / 어떤 제약으로 / 무엇이 완성인지*가 머릿속에만 막연히 있어서, 구현(직접이든 에이전트 위임이든)으로 넘기기 직전에 빠짐없이 못박아야 할 때."

**고유 구별자 = 출력의 목적지**:
- doc-concretize → 사람이 읽음
- unknown-discovery → 내 계획 보강
- **spec-first → 구현 주체(기계/에이전트)에게 넘김** ← 정량 게이트(모호하면 안 넘김)·YAML 출력의 이유

## 분리 근거 (4)

1. **정체성 이질**: 잔여 7개는 출력이 *사람*에서 완결. spec-first만 *구현 주체*로 감 — thinking이 아니라 doing의 입구.
2. **방법 중복**: Socratic 인터뷰 엔진이 unknown-discovery와 거의 동일(방향만 반대: 요구사항 구축 vs 맹점 발견).
3. **도메인 편향**: Seed 스키마(`constraints.hard`, `success_criteria.measurable_via`, `context.integration_points`)는 소프트웨어 요구사항 전용. thinking-tools "개발 외 문서작업 전제"와 충돌.
4. **기능 중복**: ouroboros(`Q00/ouroboros`) Interview+Seed가 동일 작업을 더 성숙하게 수행(Ambiguity ≤ 0.2 게이트까지 동일). spec-first는 ouroboros Interview+Seed 단계의 직계 포팅(`spec-first` description의 "Ouroboros-style"이 자기 증언).

## telemetry 보강

19일 telemetry-on(65세션)에서 spec-first 호출 **0회**. 분리 결정을 약하게 보강. 단 dogfooding 1인 + telemetry-on 한정 → over-read 금지(절대적 근거 아님).

## 미해결 → #111로 전부 이관 (2026-06-03)

아래 4개는 더 이상 이 문서에서 트래킹하지 않음 — **#111** (`reconcile: spec-first extraction open items vs layer redesign`)이 단일 소유. 원문 요지만 남김:

1. **명명**: `build-spec`(유력) / `requirement-crystallize` 등 — 방법론 이름이라 동작·시점 불명.
2. **유사도구 웹검증**: spec-kit(GitHub)·Kiro(AWS)·ouroboros 대비 차별점(잠정 빈틈 = 경량+인터뷰형+정량게이트). 2025-08 cutoff라 재검증 필요.
3. **인터뷰 엔진 중복**: unknown-discovery와 Socratic 로직 중복 — 공통 추출 검토.
4. **플러그인 구조 실행** (조건부, 폐기 가능): `plugin.json`·`marketplace.json` 등록·디렉토리·버전 동기화. **#102가 분산/흡수로 결정하면 폐기**(별도 플러그인 신설 불필요).
