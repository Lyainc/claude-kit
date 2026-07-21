---
title: Thinking-Tools Improvement Matrix
type: living-reference
status: active
version: 0.2.0
schema_version: 1
last_reviewed: 2026-07-22
next_review: 2026-10-22
owners: [thinking-tools]
audiences:
  weaknesses: contributors
  directions: users + contributors
---

# Thinking-Tools Improvement Matrix

출처: ouroboros-integration 토론(2026-04-19 frozen, 비커밋 로컬 작업물) — 아래 W/M 표가 그 논의의 살아남은 기록이에요.

W(약점) 섹션은 contributor 전용 — 구현 부채 추적.
M(방향성) 섹션은 user + contributor — 중장기 전략 방향.

ID 재활용 금지. 항목 완료 시 `status: resolved`, `resolved_in:` 기재.

> **삭제된 문서 인용 주의**: 예전 `Phase D ↔ Matrix 매핑` 표와 각 행의 `phase 매핑` 열은
> dev-plan `docs/plans/thinking-tools-enhancement-2026-06-02.md`의 내부 단계 ID(A1·B4·C4·
> D1–D6·E2·E3 등)를 가리켰어요. 그 plan은 cf69c0c의 untrack 패스로 더 이상 추적되지 않아
> fresh clone에서 열리지 않고, 단계 ID에 대응하는 이슈 번호도 없어서 #413의 인용 복구 방식
> (경로 → 이슈 번호)을 적용할 대상이 없어요. 그래서 매핑 표와 `phase 매핑` 열을 **삭제**하고,
> 실제 근거는 아래 각 행의 `resolved_in` / `근거` 열에 이슈·PR 번호와 파일 위치로 직접 씁니다.

---

## W1-W8 — Weaknesses (contributor 전용)

| ID | 약점 | 설명 | affected skills | Status | Priority | resolved_in | 근거 (2026-07-22 대조) |
|----|------|------|-----------------|--------|----------|-------------|------------------------|
| W1 | 자가검증 순환 | Verify 단계를 같은 컨텍스트·모델이 수행 — "65% 찍고 넘어가자" 유혹, blind spot 미탐지 | doc-concretize, unknown-discovery | resolved | P1 | PR #416 | 두 스킬 다 격리 실행을 받았어요. unknown-discovery는 Depth 채점 + 발견 검증(D4)을 별도 Agent 서브에이전트에서 하고(`unknown-discovery/SKILL.md` §Exploration Depth Scoring, `reference.md` §6 격리 채점), doc-concretize는 조립된 문서 전체에 대해 격리된 최종 Verify 1회를 돌려요(`doc-concretize/SKILL.md` §Isolated final Verify). 세그먼트별 인라인 루프는 빠른 로컬 반복용으로 남겼고, 사용자에게 나가는 산출물은 격리 통과가 필수예요. 패턴 출처는 expert-panel(PR #77·#145)·adversarial-review(#115, PR #403) |
| W2 | 게이트 수학 약함 | Depth/Ambiguity 게이트 점수를 LLM이 자가 평가 — 일관성 보장 없음, 근거 미기록 | unknown-discovery, build-spec | resolved | P2 | PR #416 | 두 스킬 다 Y/N 이진 체크리스트 + 근거 기록으로 통일됐어요. build-spec은 `clarity = Y수/문항수` + STATE `scoring_rationale`(§Ambiguity Scoring), unknown-discovery는 D1–D6 6항목 가중치 합산(`area_score = Σ Y 항목 가중치`, `reference.md` §6) + STATE `scoring_rationale`. 기존 "불확실성 신호 10% 차감"은 D5 항목으로 흡수돼 별도 클램핑이 사라졌어요. Depth Gate에는 D4(발견 1건 이상) 하드 전제가 붙어요 — D1+D2+D3가 정확히 65라 합산만으로는 발견 0건에도 게이트가 열리거든요(build-spec의 dimension floor와 같은 구조) |
| W3 | 상태 휘발성 | STATE 블록이 컨텍스트 compaction 시 손실 위험, 스킬마다 포맷 상이 | 전 스킬 | resolved | P1 | PR #179 | `reference/state-contract.md`가 compaction 복원 규칙과 `<!-- STATE:CHECKPOINT -->` 마커를 단일화했고, adversarial-review·unknown-discovery·expert-panel이 이 파일을 인용해요. build-spec만 같은 규칙을 자체 사본으로 들고 있는데 포맷은 동일이라 잔여 부채는 중복뿐이에요 |
| W4 | 출력 조합성 | Markdown 서사체 출력 — 후속 스킬 파싱 어려움, 스킬 체이닝 비친화적 | unknown-discovery, adversarial-review | resolved | P2 | #418 | 두 스킬 다 common-schema frontmatter를 내보내요. unknown-discovery는 `templates/DISCOVERY_REPORT.md`에, adversarial-review는 `reference/patterns.md` Final Report Template에 공통 블록 + `claims_tested`/`verdicts`/`angle` 확장을 붙였고 SKILL.md Phase 2 Export가 그 스키마를 인용해요(`../../reference/common-schema.md`). `angle`은 새 확장 필드라 common-schema.md의 adversarial-review 블록에도 같이 등록했어요 |
| W5 | 실행 연계 = 의도된 경계 (reframed) | **약점 아님 — 경계 A의 의도된 design boundary.** leaf(사고 도구)가 harness(⑤실행)와 단방향(harness→leaf)으로만 결합하고 역방향 의존을 갖지 않는 게 규율(`docs/design/claude-kit-boundary.md` §3). Seed→빌드 연계는 harness(`/goal`·Workflow)가 leaf를 호출하는 단방향으로 성립 — leaf가 harness를 import·assume하면 오히려 CON-5 위반 | build-spec | reframed | P1 | — | 재프레이밍 유지. thought-chain은 #105(PR #323)로 완전 해체돼 더 이상 대상이 아니에요 |
| W6 | 진화 메커니즘 부재 | 한 번 생성한 Seed/Report가 실행 결과로 갱신되지 않음 — Ouroboros Evolve 대비 열위 | build-spec | open | P3 | — | build-spec에 refine 모드(`refine_generation`·`refine_source`·`refine_feedback`)가 있지만 갱신 트리거가 사용자 피드백이지 실행 결과가 아니에요. 실행 결과를 되먹이려면 leaf가 harness를 알아야 해서 W5가 세운 CON-5 단방향 경계와 정면 충돌해요 — 착수 전에 그 경계부터 다시 정해야 해요 |
| W7 | 코드베이스 블라인드 | 순수 대화 인터뷰 — 실제 repo 맥락 미반영, 추상적 blind spot만 탐지 | unknown-discovery, build-spec | resolved | P2 | PR #416 | unknown-discovery는 `allowed-tools`에 Agent·Grep·Glob이 들어갔고 Phase 0에 Repo Context Intake 단계가 생겼어요(`reference.md` §15 — Glob으로 README/매니페스트 잡고 주제 키워드로 Grep해 질문을 접지). build-spec은 Grep 추가 + brownfield content intake — 매니페스트 존재는 brownfield 판정까지만이고, X1–X3(통합 지점·영향 컴포넌트·충돌)은 코드를 읽어야 Y를 줄 수 있어서요. 둘 다 repo가 없으면 조용히 건너뛰고 기존 순수 대화로 진행 |
| W8 | 페르소나 라이브러리 부재 | expert-panel·adversarial-review가 매번 페르소나를 즉석 생성 — 재현성·일관성 저하 | expert-panel, adversarial-review | resolved | P2 | #418 | `thinking-tools/reference/personas.md`(도메인 전문가 10개 + 결정론 태그 매칭 Selection Rule)를 두 스킬이 인용해요. expert-panel은 토픽별로 rank 상위 3–5개를 뽑아 STATE `Personas`에 기록하고, adversarial-review는 rank 1을 Attacker의 도메인 *각도*로만 써요(고정 역할 레이블 Attacker/Judge/Steelman Coach는 풀 밖 유지 — Seed c4). rank 1은 항상 expert-panel 컷 안이라 같은 주제에서 두 스킬이 같은 풀 항목을 가리켜요. 태그 0건이면 즉석 페르소나 + `adhoc:{n}` 표기, 6건 이상이면 (hits desc, ID asc) 정렬로 5개 절단 (M1과 같은 항목의 W쪽 표기) |

---

## M1-M5 — Strategic Directions (user + contributor)

| ID | 방향 | 설명 | Status | Priority | 관련 W | resolved_in | 근거 (2026-07-22 대조) |
|----|------|------|--------|----------|--------|-------------|------------------------|
| M1 | 페르소나 라이브러리 | 재사용 가능 전문가 페르소나 풀 정의 — expert-panel·adversarial-review 공유 사용, temperature variation으로 진짜 다양성 확보 | resolved | P2 | W8 | #418 | 풀 자체는 `reference/personas.md`로 착수 완료(#418, 상세는 W8 행). 함께 적혀 있던 "temperature variation"은 **이 항목의 완료 조건이 아니에요** — 풀이 먼저 있어야 variation을 걸 대상이 생긴다는 순서 관계라 #418 범위 밖으로 명시 제외했고, 실제로 필요해지면 새 M 항목으로 올려요(ID 재활용 금지). 전제였던 sub-agent spawn 지원은 이미 해소돼 있었어요(expert-panel 격리 실행 PR #77·PR #145, adversarial-review 자동 방어 격리 #115/PR #403) |
| M2 | 발산 전략 승격 | diverse-sampling을 단순 대안 생성에서 tournament·mutation 기반 창의적 탐색으로 — Ouroboros Contrarian 패턴 도입 | open | P2 | — | — | `diverse-sampling/`에 tournament·mutation 관련 서술이 0건 — 미착수. (repo 전역 `mutation` grep은 retro·audit 스킬의 "state mutation"에 걸리는데 M2와 무관한 용례예요) |
| M3 | 비-코딩 영역 | Biz/Creative 도메인에서 질문 패턴·채점 루브릭 전문화 — 현재 Tech 편향 | in-progress | P3 | — | — | 질문 뱅크는 도메인별로 존재(`build-spec/templates/questions/{tech,biz,creative}.md`, PR #78). 채점 루브릭(Y/N 체크리스트)은 아직 도메인 구분 없이 공용이라 여기가 남은 절반 |
| M4 | 투명성 기능화 (reframed) | **절반은 반대 방향으로 결정됨.** 점수 노출은 의도적으로 안 하기로 정리됐어요 — unknown-discovery는 수치 Depth를 compaction 복원·게이트 로직 전용으로 두고 사용자에겐 정성 표기만 보여주고(`unknown-discovery/SKILL.md` State Management), adversarial-review도 Survival Score를 수치가 아닌 정성 밴드(탄탄/보통/취약)로만 기록해요. 남은 건 diff-preview 쪽뿐 | reframed | P2 | W3 | — | `--show-scores`·diff-preview 모두 repo 히트 0건. 점수 노출 절반은 미착수가 아니라 폐기, diff-preview 절반만 살아있는 open 항목이에요 |
| M5 | facilitator 오케스트레이터화 | thinking-facilitator가 복합 의도를 감지해 멀티-스킬 파이프라인을 자동 구성 — "대안 생성 후 공격" → diverse-sampling + adversarial-review 자동 체인 | in-progress | P2 | — | — | facilitator에 Multi-Skill Detection(2개/3개+ 감지 → 순서 확인 후 순차 실행)이 들어갔고, diverse-sampling Mode B → doc-concretize Skill 서브콜은 실제로 도는 체인이에요. 다만 체이닝이 사용자 확인을 거치는 순차 실행이라 "자동 구성"까지는 아직 |

---

## Governance

- **ID 재활용 금지**: W/M ID는 영구 고유 식별자. resolved 후에도 ID 유지.
- **항목 진행 시**: 해당 PR이 본 파일 `status` 갱신 + CHANGELOG.md 엔트리 추가.
- **새 항목 추가**: W9+, M6+ 순번 연속 배정.
- **supersedes**: 기존 항목을 대체할 경우 `supersedes: W_` 기재 후 원본 status → `wontfix`.
- **`근거` 열**: `last_reviewed` 시점에 실제 코드·머지된 이슈와 대조한 결과예요. status를 바꾸거나
  `last_reviewed`를 올릴 때는 전 행을 다시 대조하고 이 열도 같이 갱신해요 — 대조 없이 날짜만
  올리면 가짜 리뷰 기록이 돼요.

---

*Source: ouroboros-integration 토론의 analysis + panel-position-c SUMMARY (2026-04-19 frozen, 비커밋 로컬 작업물)*
