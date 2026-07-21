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
| W1 | 자가검증 순환 | Verify 단계를 같은 컨텍스트·모델이 수행 — "65% 찍고 넘어가자" 유혹, blind spot 미탐지 | doc-concretize, unknown-discovery | open | P1 | — | doc-concretize의 Build→Verify→Reflect와 unknown-discovery의 Depth 채점이 여전히 같은 컨텍스트에서 돌아요. 격리 실행은 expert-panel(#270)·adversarial-review(#115, PR #403)에만 들어갔고 W1이 지목한 두 스킬은 못 받았어요 |
| W2 | 게이트 수학 약함 | Depth/Ambiguity 게이트 점수를 LLM이 자가 평가 — 일관성 보장 없음, 근거 미기록 | unknown-discovery, build-spec | open | P2 | — | build-spec 쪽은 해소 — Y/N 이진 체크리스트로 `clarity = Y수/문항수`를 계산하고 `scoring_rationale`에 근거를 남겨요(`build-spec/SKILL.md` §Ambiguity Scoring). unknown-discovery의 Exploration Depth는 아직 LLM이 0–100%를 자유 채점해서 일관성 보장이 없어요 |
| W3 | 상태 휘발성 | STATE 블록이 컨텍스트 compaction 시 손실 위험, 스킬마다 포맷 상이 | 전 스킬 | resolved | P1 | PR #179 | `reference/state-contract.md`가 compaction 복원 규칙과 `<!-- STATE:CHECKPOINT -->` 마커를 단일화했고, adversarial-review·unknown-discovery·expert-panel이 이 파일을 인용해요. build-spec만 같은 규칙을 자체 사본으로 들고 있는데 포맷은 동일이라 잔여 부채는 중복뿐이에요 |
| W4 | 출력 조합성 | Markdown 서사체 출력 — 후속 스킬 파싱 어려움, 스킬 체이닝 비친화적 | unknown-discovery, adversarial-review | open | P2 | — | unknown-discovery는 `templates/DISCOVERY_REPORT.md`에 common-schema frontmatter를 붙였지만, adversarial-review의 SKILL.md엔 common-schema 인용이 0건이라 리뷰 출력이 아직 파싱 불가한 서사체예요 |
| W5 | 실행 연계 = 의도된 경계 (reframed) | **약점 아님 — 경계 A의 의도된 design boundary.** leaf(사고 도구)가 harness(⑤실행)와 단방향(harness→leaf)으로만 결합하고 역방향 의존을 갖지 않는 게 규율(`docs/design/claude-kit-boundary.md` §3). Seed→빌드 연계는 harness(`/goal`·Workflow)가 leaf를 호출하는 단방향으로 성립 — leaf가 harness를 import·assume하면 오히려 CON-5 위반 | build-spec | reframed | P1 | — | 재프레이밍 유지. thought-chain은 #105(PR #323)로 완전 해체돼 더 이상 대상이 아니에요 |
| W6 | 진화 메커니즘 부재 | 한 번 생성한 Seed/Report가 실행 결과로 갱신되지 않음 — Ouroboros Evolve 대비 열위 | build-spec | open | P3 | — | build-spec에 refine 모드(`refine_generation`·`refine_source`·`refine_feedback`)가 있지만 갱신 트리거가 사용자 피드백이지 실행 결과가 아니에요. 실행 결과를 되먹이려면 leaf가 harness를 알아야 해서 W5가 세운 CON-5 단방향 경계와 정면 충돌해요 — 착수 전에 그 경계부터 다시 정해야 해요 |
| W7 | 코드베이스 블라인드 | 순수 대화 인터뷰 — 실제 repo 맥락 미반영, 추상적 blind spot만 탐지 | unknown-discovery, build-spec | open | P2 | — | unknown-discovery의 `allowed-tools`가 아직 `AskUserQuestion Read Write`뿐이라 Grep/Glob이 없고, build-spec은 Glob만 있어 repo 맥락 인테이크 단계 자체가 없어요 |
| W8 | 페르소나 라이브러리 부재 | expert-panel·adversarial-review가 매번 페르소나를 즉석 생성 — 재현성·일관성 저하 | expert-panel, adversarial-review | open | P2 | — | `thinking-tools/reference/`에 공유 페르소나 풀 파일이 없고, 두 스킬이 각자 SKILL.md 안에서 페르소나를 그때그때 만들어요 (M1과 같은 항목의 W쪽 표기) |

---

## M1-M5 — Strategic Directions (user + contributor)

| ID | 방향 | 설명 | Status | Priority | 관련 W | 근거 (2026-07-22 대조) |
|----|------|------|--------|----------|--------|------------------------|
| M1 | 페르소나 라이브러리 | 재사용 가능 전문가 페르소나 풀 정의 — expert-panel·adversarial-review 공유 사용, temperature variation으로 진짜 다양성 확보 | open | P2 | W8 | 전제로 걸어둔 sub-agent spawn 지원은 해소됐어요(expert-panel 격리 실행 #270, adversarial-review 자동 방어 격리 #115/PR #403). 라이브러리 자체는 미착수 |
| M2 | 발산 전략 승격 | diverse-sampling을 단순 대안 생성에서 tournament·mutation 기반 창의적 탐색으로 — Ouroboros Contrarian 패턴 도입 | open | P2 | — | `diverse-sampling/`에 tournament·mutation 관련 서술이 0건 — 미착수. (repo 전역 `mutation` grep은 retro·audit 스킬의 "state mutation"에 걸리는데 M2와 무관한 용례예요) |
| M3 | 비-코딩 영역 | Biz/Creative 도메인에서 질문 패턴·채점 루브릭 전문화 — 현재 Tech 편향 | in-progress | P3 | — | 질문 뱅크는 도메인별로 존재(`build-spec/templates/questions/{tech,biz,creative}.md`, PR #78). 채점 루브릭(Y/N 체크리스트)은 아직 도메인 구분 없이 공용이라 여기가 남은 절반 |
| M4 | 투명성 기능화 (reframed) | **절반은 반대 방향으로 결정됨.** 점수 노출은 의도적으로 안 하기로 정리됐어요 — unknown-discovery는 수치 Depth를 compaction 복원·게이트 로직 전용으로 두고 사용자에겐 정성 표기만 보여주고(`unknown-discovery/SKILL.md` State Management), adversarial-review도 Survival Score를 수치가 아닌 정성 밴드(탄탄/보통/취약)로만 기록해요. 남은 건 diff-preview 쪽뿐 | reframed | P2 | W3 | `--show-scores`·diff-preview 모두 repo 히트 0건. 점수 노출 절반은 미착수가 아니라 폐기, diff-preview 절반만 살아있는 open 항목이에요 |
| M5 | facilitator 오케스트레이터화 | thinking-facilitator가 복합 의도를 감지해 멀티-스킬 파이프라인을 자동 구성 — "대안 생성 후 공격" → diverse-sampling + adversarial-review 자동 체인 | in-progress | P2 | — | facilitator에 Multi-Skill Detection(2개/3개+ 감지 → 순서 확인 후 순차 실행)이 들어갔고, diverse-sampling Mode B → doc-concretize Skill 서브콜은 실제로 도는 체인이에요. 다만 체이닝이 사용자 확인을 거치는 순차 실행이라 "자동 구성"까지는 아직 |

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
