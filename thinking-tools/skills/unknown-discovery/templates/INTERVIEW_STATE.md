# Interview State

인터뷰 진행 중 상태를 STATE 블록으로 추적한다. STATE 블록의 정확한 필드는 [SKILL.md](../SKILL.md)의
State Management 섹션이 유일 소스다 — 필드가 바뀔 때마다 이 파일까지 고칠 필요가 없도록, 여기서는
필드를 다시 나열하지 않는다.

저장 트리거·복원 절차 등 `build-spec`과 공유하는 계약은
[../../../reference/interview-state.md](../../../reference/interview-state.md) 참고.

## Field Reference

| Field | Values |
|-------|--------|
| Phase | 0=Context, 1=Interview, 2=Synthesis, 3=Documentation |
| Status | `done`, `active`, `pending` |
| Score | 0-100 (Exploration Depth %, 상세: [reference.md](../reference.md) §6) |
| Depth | 가중 평균 Exploration Depth % |
| Maturity | `idea`, `plan`, `execution` (상세: [reference.md](../reference.md) §9) |
| Priority | `C`=Critical, `I`=Important, `N`=Nice-to-have |
| Challenge | `done`=사용됨, `pending`=미사용 |
| scoring_isolated | `true`=격리 채점(게이트 임박 라운드), `false`=인라인 채점(그 외 라운드, 또는 격리 실패) |

## Termination Signals

| Signal | Count toward saturation |
|--------|------------------------|
| Short response (< 20자) | +1 |
| Repetition (similar to previous) | +1 |
| Avoidance ("나중에", "괜찮아") | +1 |

**Saturation**: 3 consecutive signals → confirm termination with user.

## Termination Gate

- **Depth ≥ 65% AND 진입한 모든 Core 영역에서 D4=Y**: Phase 2 진입 가능 (사용자 동의 필요, 상세: [reference.md](../reference.md) §6)
- **Depth < 65% + Saturation**: 사용자에게 경고 후 진행 가능
- 기존 포화 감지는 보조 지표로 유지

## File Persistence (Optional)

### 저장 경로

```text
docs/discovery/{target-name}/state.md
```

`{target-name}`은 분석 대상을 kebab-case로 변환 (예: "결제 시스템 도입" → `payment-system`).

### 저장 파일 형식

```markdown
---
target: {name}
domain: {domain}
maturity: {idea|plan|execution}
saved_at: YYYY-MM-DD HH:MM
phase: {0|1|2|3}
---

<!-- STATE:CHECKPOINT -->
...세션의 현재 STATE 블록을 SKILL.md 형식 그대로 붙여넣는다 (필드를 여기서 다시 정의하지 않음)...
<!-- /STATE -->

## Interview History

| Round | Area | Question Summary | Key Finding |
|-------|------|-----------------|-------------|
| 1 | Assumptions | {summary} | {finding or —} |
| ... | ... | ... | ... |
```

### 재개 절차

저장 트리거·일반 복원 단계는 [../../../reference/interview-state.md](../../../reference/interview-state.md) 참고.
UD 고유: 복원 후 Interview History 테이블에서 이전 질문/발견 맥락도 함께 복원한다.
