# thought-chain 파이프라인 4단계 회귀 결정

**Date**: 2026-05-25
**Decision type**: Architectural alignment (vault-spec ↔ main code coherence)
**Status**: Approved
**Authority**: User-confirmed (deep-interview 7-round consensus)

---

## 결정 (Decision)

**thought-chain의 기본 파이프라인을 5단계 → 4단계로 회귀하고, adversarial-review는 독립 스킬로 유지한다.**

### 확정 파이프라인 (4-stage)

```
unknown-discovery → expert-panel → doc-concretize → doc-polish
       Stage 1          Stage 2         Stage 3        Stage 4
```

### adversarial-review의 위치

- thought-chain에서 제거
- 독립 스킬로 유지 (`thinking-tools/skills/adversarial-review/`)
- `thinking-facilitator` 라우팅을 통해 신호 감지 시 호출
- A 타입(클레임 검증) 사용 맥락에서만 어울리는 것으로 합의

---

## 배경 (Context)

### 충돌 상태

| 위치 | 단계 | 출처 |
|------|------|------|
| `thought-chain/SKILL.md` (origin/main) | **5단계** (Stage 2 = adversarial-review) | PR #78 (2026-05-20) |
| `thought-chain/reference.md` (origin/main) | **4단계** (Stage 2 = expert-panel) | PR #72 잔존, 미동기화 |
| **vault `plan-2026-05-23-thought-chain-checkpoint-vault-integration.md`** | **4단계 고정** | 공식 결정 |
| `plan-2026-04-19-thinking-tools-ouroboros-execution.md` §8.1 | 5단계 (with adversarial-review) | 4월 시점 설계 (구버전) |

→ **main 자체가 incoherent**. PR #78이 사실상 vault 결정과 어긋난 채 머지됐고, reference.md는 미동기화 상태로 남음.

### 타임라인 정리

| 일자 | 사건 | 결과 |
|------|------|------|
| 2026-04-13 | adversarial-review 스킬 설계 (plan-2026-04-13) | 독립 스킬 의도 |
| 2026-04-19 | ouroboros 실행 계획 (plan-2026-04-19) | thought-chain에 adversarial-review 편입 제안 (5단계) |
| 2026-05-12 | checkpoint-vault 설계 (plan-2026-05-12) | 4단계 유지로 결정 |
| 2026-05-16 | PR #72 머지 | 4단계 checkpoint 구현, reference.md 작성 |
| 2026-05-20 | PR #78 머지 | SKILL.md를 5단계로 확장 — **reference.md 미동기화** |
| 2026-05-23 | vault plan-2026-05-23 갱신 | "4단계 고정" 명시 |
| 2026-05-25 | 본 결정 | 4단계 회귀로 정합성 회복 |

### PR 79~81과 ouroboros의 관계 (사실 확인)

PR 79~81은 thought-chain/adversarial-review와 무관:

- PR #79: vault-bridge `disable-model-invocation` + hook path quoting
- PR #80: agent `<example>` 블록 docs (Stage 3 PR-C)
- PR #81: vault-bridge `userConfig.vault_path`

→ ouroboros의 직계 산출물은 **PR #72, PR #78**. PR 79~81은 별도 vault-bridge 트랙이었음.

---

## 근거 (Rationale)

### Deep-interview 7라운드 합의 통찰

**Round 2** — adversarial-review의 적합 영역
- A 타입 (클레임/주장 검증): 어울림
- B 타입 (연구·문서화): 어울리지 않음

**Round 4** — thought-chain의 진짜 메리트
- 자동 핸드오프 (콜드스타트 비용 제거)
- 체크포인트 핀포인트 보장
- BUT: 5단계는 무거움

**Round 5** — 운용 현실 (결정적)
- 사용자는 플래그 옵션을 실제로 잘 안 씀
- chain임을 감안해도 지나치게 복잡

**Round 7** — 단일 채널 합의
- 사용자는 thought-chain을 직접 호출하지 않음
- thinking-facilitator가 진입점, 시퀀스 결정도 facilitator
- thought-chain은 facilitator의 한 호출 대상(다중 스킬 시퀀스 템플릿)

### Clarity Breakdown

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal | 0.90 | 0.35 | 0.315 |
| Constraints | 0.85 | 0.25 | 0.213 |
| Success Criteria | 0.85 | 0.25 | 0.213 |
| Context | 0.80 | 0.15 | 0.120 |
| **Ambiguity** | | | **14%** ≤ threshold 20% |

---

## 적용 계획 (Implementation Plan)

### 작업 단위: PR `feat/stage4-pd` (Stage 4 PR-D: Progressive Disclosure)

vault `plan-2026-05-23-plugin-spec-improvement-execution.md`의 Stage 4 PR-D와 동일 식별자.

**변경 내용:**

1. `thought-chain/SKILL.md`:
   - 5단계 → 4단계로 회귀
   - Stage 2 `adversarial-review` 제거, 번호 재조정
   - `--skip adversarial-review`, `--start adversarial-review` 플래그 제거
   - Stage 1 empty guard 단순화 (Stage 2가 adversarial-review가 아니므로)
   - 사이드카 분리 (pipeline-examples.md)

2. `thought-chain/reference/pipeline-examples.md`:
   - 4단계 기준 신규 작성
   - quick-start 예시, partial pipeline, metadata schema 모두 4단계 반영
   - `stages_run`에서 `adversarial-review` 제외

3. `thought-chain/reference.md`:
   - 기존 그대로 (이미 4단계, 동기화됨)

4. `adversarial-review/SKILL.md` + `reference/patterns.md` + `examples/sample.md`:
   - 사이드카 분리 (322줄 → 192줄)
   - **adversarial-review 스킬 자체는 변경 없음**, thought-chain과의 관계만 변경

5. `thinking-facilitator.md`:
   - skills 리스트에 adversarial-review 유지 (독립 스킬로 보존)
   - 라우팅 로직 그대로 (3+ skills detected → thought-chain은 4단계 기준)

6. 버전 범프:
   - `thinking-tools/plugin.json`: 1.9.1 → 1.9.2
   - `marketplace.json` 동기화

### 비변경 (Non-Goals)

- adversarial-review 스킬 자체 제거 (독립 스킬로 유지)
- thinking-facilitator 라우팅 로직 재설계 (현재 구조로 충분)
- 다른 스킬 (spec-first, diverse-sampling 등) 영향
- expert-panel 사이드카 분리 (201줄로 임계값 미달)

---

## 폐기된 브랜치 (Deprecated branches)

- `feat/stage4-sidecar` (commit 1237b96): **5단계 기준** 사이드카 분리 작업. vault 결정과 충돌하여 폐기.
  - 백업 태그: `backup/feat-stage4-sidecar-20260525`
  - 새 브랜치 `feat/stage4-pd`로 대체

- `Lyainc/kanban-status-board-design`: 4단계 회귀 구현을 가진 워크트리 브랜치. 환경 정리 시 삭제됨. 본 PR이 그 의도를 계승.

---

## 참조 (References)

- vault plan: `~/vault/20_Projects/claude-kit/plan-2026-05-23-plugin-spec-improvement-execution.md` (Stage 4 PR-D)
- vault plan: `~/vault/20_Projects/claude-kit/plan-2026-05-23-thought-chain-checkpoint-vault-integration.md` (4단계 결정)
- 폐기된 ouroboros: `~/vault/20_Projects/claude-kit/plan-2026-04-19-thinking-tools-ouroboros-execution.md` §8.1 (5단계 제안, 무효화됨)
- adversarial-review 스킬 설계: `~/vault/20_Projects/claude-kit/plan-2026-04-13-adversarial-review-skill.md` (독립 스킬 의도)
