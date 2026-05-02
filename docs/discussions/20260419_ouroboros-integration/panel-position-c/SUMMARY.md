# Expert Panel SUMMARY — Position C 검증

**Date**: 2026-04-19
**Objective**: Position C(문서 수명 기준 분리) 제안 검증. 3개 토픽 다관점 평가.
**Panel**: Moderator, Optimistic Practitioner, Critical Practitioner, Technical Documentation Expert, Open Source Maintainer Expert, Plugin Ecosystem Expert (총 6명)
**Source**: [`../analysis.md`](../analysis.md), [`../dev-plan.md`](../dev-plan.md)

## Topics & Outcome

| # | Topic | Outcome |
|---|-------|---------|
| 1 | 문서 수명 기준 분리 원칙의 정당성 | 합의 (조건부) |
| 2 | improvement-matrix.md 경로·거버넌스·업데이트 | 합의 (조건부) |
| 3 | dev-plan.md 스코프 축소 부작용 | 합의 (조건부) |

합의 실패 0건. Critical Practitioner 우려는 절차적 조건으로 흡수.

## Final Recommendation

| 항목 | 결정 |
|------|------|
| 채택 입장 | **Position C** — 문서 수명 기준 분리 |
| 동결 문서 | `docs/discussions/20260419_ouroboros-integration/analysis.md`, `dev-plan.md` |
| 신규 living 문서 | `thinking-tools/docs/improvement-matrix.md` |
| 매트릭스 ID 네임스페이스 | **M1-M5** (dev-plan Phase D와 충돌 회피) |
| 매핑 표 | dev-plan ↔ matrix 양쪽 문서에 명시 |
| Forward pointer | dev-plan.md frontmatter에 `tracking_continued_in:` 추가 |
| 거버넌스 | frontmatter 스키마 + ID 재활용 금지 + CODEOWNERS + CHANGELOG 트리거 |
| W vs D 섹션 분리 | W(약점)=contributor 전용, D(방향성)=user-facing |

## Action Items

### A1. Frozen 문서 마커 추가

`docs/discussions/20260419_ouroboros-integration/analysis.md`와 `dev-plan.md` 상단 frontmatter에 다음 추가:

```yaml
---
status: frozen
frozen_at: 2026-04-19
tracking_continued_in: thinking-tools/docs/improvement-matrix.md
note: "본 문서는 토론 시점 스냅샷. 진행 상태는 매트릭스 참조."
---
```

### A2. dev-plan.md 스코프 명시

dev-plan.md에 다음 섹션 추가:

```markdown
## Scope Note (frozen)

본 dev-plan은 **Ouroboros 통합 작업 한정** (Phase A-E). thinking-tools 전반의 
구조적 개선(W1-W8 약점, M1-M5 차별화 전략)은 `thinking-tools/docs/improvement-matrix.md` 참조.

### Phase D ↔ Matrix M 매핑

| dev-plan Phase D | matrix M |
|------------------|----------|
| D1 diverse-sampling 개선 | M2 발산 전략 승격 (부분) |
| D4 expert-panel sub-agent | M1 페르소나 라이브러리 (의존) |
| D5 adversarial-review Judge 분리 | (별도 수렴) |
| D6 facilitator 등록 fix | M5 facilitator 오케스트레이터화 (전제) |
```

### A3. improvement-matrix.md 신설

경로: `thinking-tools/docs/improvement-matrix.md`

Frontmatter 스키마:
```yaml
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
  weaknesses: contributors      # W 섹션
  directions: users + contributors  # M 섹션
---
```

내용 구조:
- **W1-W8 (Weaknesses)**: contributor 전용 — 자가검증 순환, 게이트 수학 약함, 상태 휘발성, 출력 조합성, 실행 연계 부재, 진화 메커니즘 부재, 코드베이스 블라인드, 페르소나 라이브러리 부재
- **M1-M5 (Strategic Directions)**: user + contributor — 페르소나 라이브러리, 발산 전략, 비-코딩 영역, 투명성 기능화, facilitator 오케스트레이터화
- 각 항목: `id`, `status: open|in-progress|resolved|wontfix`, `priority`, `resolved_in: <version>`, `supersedes: <id>`, `notes`

### A4. CONTRIBUTING.md 갱신

다음 1단락 추가:

```markdown
## 문서 수명 관리

- `docs/discussions/YYYYMMDD_*/`: **frozen artifacts**. 토론 시점 기록, 이후 수정 안 함. 
  후속 변경은 `tracking_continued_in:` 필드로 living 문서를 가리킴.
- `{plugin}/docs/`: **living references**. 주기적 업데이트, semver 관리, ID 재활용 금지.
- `Status: Frozen` (기본) → 후속 생기면 `Status: Superseded by {path}` 전환.
- 매트릭스 항목 진척 시: 해당 PR이 `{plugin}/docs/improvement-matrix.md` 동시 갱신 + CHANGELOG.md 엔트리 추가.
```

### A5. CODEOWNERS 추가

```
thinking-tools/docs/  @maintainer
```

## Phase D ↔ Matrix M 매핑 결과

기존 dev-plan Phase D는 **구체 실행 작업**, matrix M은 **cross-cutting 전략 방향성**. 추상화 레벨이 다름. 충돌 회피 위해 ID 네임스페이스 분리 (D vs M).

| Phase D (실행) | Matrix M (전략) | 관계 |
|---------------|-----------------|------|
| D1 diverse-sampling | M2 발산 전략 | M2의 일부 작업 |
| D2 doc-concretize | (cross-cut M4 투명성) | 간접 |
| D3 doc-polish | (cross-cut M4) | 간접 |
| D4 expert-panel | M1 페르소나 라이브러리 | M1 활용 작업 |
| D5 adversarial-review | M1 (Attacker persona) | M1 활용 |
| D6 facilitator | M5 오케스트레이터 | M5의 1단계 |

매핑상 D는 M의 구체 인스턴스이거나 직접 활용 작업. 중복 아닌 의존 관계.

## Phase 2 Documents

- Transcripts: [`transcripts/`](./transcripts/)
- Unresolved: [`UNRESOLVED.md`](./UNRESOLVED.md)

───
*3개 토픽 논의 완료 · 3개 합의 (조건부) · 0개 보류*
