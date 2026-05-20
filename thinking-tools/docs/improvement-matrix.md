---
title: Thinking-Tools Improvement Matrix
type: living-reference
status: active
version: 0.1.0
schema_version: 1
last_reviewed: 2026-04-19
next_review: 2026-07-19
owners: [thinking-tools]
source_discussions:
  - docs/discussions/20260419_ouroboros-integration/
audiences:
  weaknesses: contributors
  directions: users + contributors
---

# Thinking-Tools Improvement Matrix

tracking_continued_from: `docs/discussions/20260419_ouroboros-integration/` (frozen 2026-04-19)

W(약점) 섹션은 contributor 전용 — 구현 부채 추적.
M(방향성) 섹션은 user + contributor — 중장기 전략 방향.

ID 재활용 금지. 항목 완료 시 `status: resolved`, `resolved_in:` 기재.

---

## Phase D ↔ Matrix 매핑

dev-plan Phase D(실행 작업)와 Matrix M(전략 방향)의 관계:

| Phase D (실행) | Matrix M (전략) | 관계 |
|---------------|-----------------|------|
| D1 diverse-sampling 개선 | M2 발산 전략 승격 | M2의 부분 작업 |
| D2 doc-concretize | M4 투명성 기능화 | 간접 |
| D3 doc-polish | M4 투명성 기능화 | 간접 |
| D4 expert-panel sub-agent | M1 페르소나 라이브러리 | M1 활용 작업 |
| D5 adversarial-review Judge 분리 | M1 페르소나 라이브러리 | M1 활용 |
| D6 facilitator 등록 fix | M5 facilitator 오케스트레이터화 | M5의 1단계 |

D는 M의 구체 인스턴스이거나 직접 활용 작업. 중복 아닌 의존 관계.

---

## W1-W8 — Weaknesses (contributor 전용)

| ID | 약점 | 설명 | affected skills | Status | Priority | phase 매핑 | resolved_in |
|----|------|------|-----------------|--------|----------|------------|-------------|
| W1 | 자가검증 순환 | Verify 단계를 같은 컨텍스트·모델이 수행 — "65% 찍고 넘어가자" 유혹, blind spot 미탐지 | doc-concretize, unknown-discovery | open | P1 | D2a | — |
| W2 | 게이트 수학 약함 | Depth/Ambiguity 게이트 점수를 LLM이 자가 평가 — 일관성 보장 없음, 근거 미기록 | unknown-discovery, spec-first | open | P2 | B4, A1 | — |
| W3 | 상태 휘발성 | STATE 블록이 컨텍스트 compaction 시 손실 위험, 스킬마다 포맷 상이 | 전 스킬 | open | P1 | E3 | — |
| W4 | 출력 조합성 | Markdown 서사체 출력 — 후속 스킬 파싱 어려움, 스킬 체이닝 비친화적 | unknown-discovery, adversarial-review | open | P2 | E2, A2(unknown) | — |
| W5 | 실행 연계 부재 | 사고 도구가 실행 도구(OMC ralph)와 단절 — Seed → 빌드 루프 수동 이어야 | spec-first, thought-chain | open | P1 | C | — |
| W6 | 진화 메커니즘 부재 | 한 번 생성한 Seed/Report가 실행 결과로 갱신되지 않음 — Ouroboros Evolve 대비 열위 | spec-first | open | P3 | C4 | — |
| W7 | 코드베이스 블라인드 | 순수 대화 인터뷰 — 실제 repo 맥락 미반영, 추상적 blind spot만 탐지 | unknown-discovery, spec-first | open | P2 | A3(unknown), A2(spec-first) | — |
| W8 | 페르소나 라이브러리 부재 | expert-panel·adversarial-review가 매번 페르소나를 즉석 생성 — 재현성·일관성 저하 | expert-panel, adversarial-review | open | P2 | M1 | — |

---

## M1-M5 — Strategic Directions (user + contributor)

| ID | 방향 | 설명 | Status | Priority | 관련 W | phase 매핑 | notes |
|----|------|------|--------|----------|--------|------------|-------|
| M1 | 페르소나 라이브러리 | 재사용 가능 전문가 페르소나 풀 정의 — expert-panel·adversarial-review 공유 사용, temperature variation으로 진짜 다양성 확보 | open | P2 | W8 | D4, D5 | sub-agent spawn 플랫폼 지원 전제 |
| M2 | 발산 전략 승격 | diverse-sampling을 단순 대안 생성에서 tournament·mutation 기반 창의적 탐색으로 — Ouroboros Contrarian 패턴 도입 | open | P2 | — | D1 | D1a(중복필터), D1b(tournament) |
| M3 | 비-코딩 영역 | Biz/Creative 도메인에서 질문 패턴·채점 루브릭 전문화 — 현재 Tech 편향 | in-progress | P3 | — | B(spec-first) | spec-first Biz/Creative question banks shipped (PR #78); 채점 루브릭 도메인 전문화는 다음 단계 |
| M4 | 투명성 기능화 | STATE 블록·채점 근거를 사용자 가시 출력으로 표준화 — `--show-scores` 모드, diff-preview 등 | open | P2 | W3 | D2, D3 | doc-polish D3a(diff-preview), doc-concretize D2a |
| M5 | facilitator 오케스트레이터화 | thinking-facilitator가 복합 의도를 감지해 멀티-스킬 파이프라인을 자동 구성 — "대안 생성 후 공격" → diverse-sampling + adversarial-review 자동 체인 | open | P2 | — | D6 | D6 registration step done (PR #78 — facilitator routes spec-first + adversarial-review); 자동 체이닝 로직 미구현 |

---

## Governance

- **ID 재활용 금지**: W/M ID는 영구 고유 식별자. resolved 후에도 ID 유지.
- **항목 진행 시**: 해당 PR이 본 파일 `status` 갱신 + CHANGELOG.md 엔트리 추가.
- **새 항목 추가**: W9+, M6+ 순번 연속 배정.
- **supersedes**: 기존 항목을 대체할 경우 `supersedes: W_` 기재 후 원본 status → `wontfix`.

---

*Source: `docs/discussions/20260419_ouroboros-integration/analysis.md` + `panel-position-c/SUMMARY.md` (frozen 2026-04-19)*
