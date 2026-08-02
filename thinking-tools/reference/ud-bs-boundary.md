# unknown-discovery ↔ build-spec — 역할 경계

`unknown-discovery`(UD)와 `build-spec`(BS)은 엔진이 사실상 같다 — 인터뷰 루프, Y/N 체크리스트
채점, 최저 영역 자동 타게팅, 격리 Agent 채점, 게이트, STATE, Quick Mode, 종료 조건 6종. 다른 건
질문 축 이름 4개와 산출물뿐이라, 실제 세션에서 스킬 선택이 갈린다. 이 파일이 두 스킬이 공유하는
단일 계약이다 — `docs/specs/thinking-tools-ud-bs-boundary.yaml` c1(hard): 이 계약은 파일 하나를
넘지 않는다.

## 축 — 인터뷰가 끝났을 때 답의 모양

"Diagnostic vs Constructive"는 틀린 축이다. 둘 다 결국 구성으로 이어지기 때문이다. 실제로 갈리는
축은 하나 — **인터뷰가 끝났을 때 답이 어떤 모양인가**.

| 스킬 | 답의 모양 | 산출물 |
|---|---|---|
| unknown-discovery | **목록** — 무엇을 모르는지 | Discovery Report (findings 목록, 아직 답 없음) |
| build-spec | **명세** — 무엇을 만들지 | Seed YAML (goal/constraints/success, 답이 굳음) |

diverse-sampling(창의적 대안 생성) / expert-panel(다관점 평가) / adversarial-review(단일 주장
공격)는 이 축 바깥이다 — 셋 다 "답의 모양"이 아니라 "인터뷰 자체를 하는가"에서 이미 갈린다.

## 세 경로

다리는 조건부 경로이지 기본 경로가 아니다.

1. **UD 단독** — 이미 굴러가는 시스템 검토, 남이 쓴 기획서 점검, 도입 여부 결정 자체. 발견이
   스펙으로 굳지 않는다(굳힐 대상이 없다).
2. **BS 단독** — 만들 건 정해졌고 어떻게 쓸지만 남았을 때.
3. **UD → BS** — 만들 건 정해졌는데 위험이 커서 먼저 훑을 때만.

왕복은 같은 세션에서 하지 않는다 — seed 파일을 경유하는 비동기 경로다:
`seed v1` → (세션 분리) UD가 seed를 대상으로 인터뷰 → BS refine → `seed v2`.

## findings → blindspots 매핑

UD 리포트 frontmatter의 `findings[].category`(assumption|blindspot|trade-off|edge-case|dependency)와
Seed `blindspots[].area`가 이미 같은 어휘를 공유한다 — 둘 다 [common-schema.md](common-schema.md)
기인이라 새 필드가 필요 없다.

`constraints[]`/`success_criteria[]`로는 매핑하지 않는다 — `type`/`hard`/`verifiable`/`measurable_via`가
UD에 없고, 더 근본적으로 **UD 발견은 답이 아니라 아직 답이 없는 질문**이기 때문이다. 그래서 올바른
배관은 Seed 필드 직행이 아니라 **BS Phase 1 질문 큐 주입**이다 (A3 Refine mode의 prior-seed +
feedback preamble 경로가 이미 지원). 답이 나오면 constraint/success로 굳고, 안 나오면
`blindspots[]`에 남는다.

## 판정 기준표 — 샘플 입력별

| 샘플 입력 | 기대 스킬 | 왜 |
|---|---|---|
| "새로운 결제 시스템 도입을 검토해줘, 놓친 게 있는지 봐줘" | UD | 도입 여부 자체가 검토 대상 — 굳힐 스펙이 없다 |
| "이미 짠 마이그레이션 계획에 빈틈 있는지 봐줘" | UD | 계획이 이미 존재, 답은 목록(빈틈)이지 명세가 아니다 |
| "task CLI 만들고 싶은데 뭐가 필요한지 모르겠어" | BS | 만들 대상이 이미 확정(task CLI), 남은 건 구조화 |
| "이 아이디어를 스펙으로 정리해줘" | BS | "스펙으로"가 명세 산출물을 직접 지목 |
| "이 결제 시스템 리스크가 커서, 먼저 맹점부터 훑고 나서 스펙 짤게" | UD → BS | 위험이 커서 먼저 훑는다는 조건이 명시된 세 번째 경로 |
| "이 기획서 다 좋은데 내가 뭘 놓쳤는지 한번만 봐줘" | UD | "놓친 것"이 목록형 질문, 만들 대상이 없다 |
| "빠르게 스펙만 뽑아줘" | BS (Quick Mode) | "스펙만"이 명세 산출물 + 압축 모드를 동시에 지목 |
| "간단히 맹점만 짚어줘" | UD (Quick Discovery Mode) | "간단히"+"맹점"이 압축 인터뷰 + 목록형 산출물을 지목 |

### 왜 이 표를 CI로 자동화하지 않는가

실제 라우팅은 LLM이 각 스킬의 `description`을 읽고 판단하는 시점에 일어난다. 결정적 스크립트가
검사할 수 있는 건 "트리 텍스트 안에 기대 스킬 문자열이 있는가" 정도이고, 이건 런타임에 여전히
잘못된 스킬로 갈 때도 통과한다 — 잡으려던 회귀를 정확히 통과시키는 테스트다. 그래서 이 표는 사람이
읽고 판단하는 문서 린트로 남긴다.

## 참조

- [common-schema.md](common-schema.md) — findings/blindspots 어휘의 공통 출처
- `thinking-tools/skills/build-spec/SKILL.md` Phase 1 Refine mode (A3) — UD 발견의 복귀 배관
- `thinking-tools/skills/unknown-discovery/SKILL.md` Phase 0 Seed Detection / Phase 3 Post-Discovery — 다리의 진입/출구
