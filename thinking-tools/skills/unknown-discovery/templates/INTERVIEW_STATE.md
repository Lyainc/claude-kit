# Interview State

인터뷰 진행 중 상태를 STATE 블록으로 추적한다.

## STATE Block Format

매 체크포인트마다 다음 형식을 출력:

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Domain: {domain} | Maturity: {idea|plan|execution} | Phase: {0|1|2|3}
Progress: [assumptions:{status}:{score}%] [trade-offs:{status}:{score}%] [edge-cases:{status}:{score}%] [blindspots:{status}:{score}%]
Depth: {weighted_avg}% | Q: {total_count} | CP: {checkpoint_count}
Challenges: [inverter:{done|pending}] [outsider:{done|pending}] [pre-mortem:{done|pending}]

Discoveries:
1. [{C|I|N}] {finding title} — {one-line description}
2. ...
<!-- /STATE -->
```

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

## Termination Signals

| Signal | Count toward saturation |
|--------|------------------------|
| Short response (< 20자) | +1 |
| Repetition (similar to previous) | +1 |
| Avoidance ("나중에", "괜찮아") | +1 |

**Saturation**: 3 consecutive signals → confirm termination with user.

## Termination Gate

- **Depth ≥ 65%**: Phase 2 진입 가능 (사용자 동의 필요)
- **Depth < 65% + Saturation**: 사용자에게 경고 후 진행 가능
- 기존 포화 감지는 보조 지표로 유지

## Compaction Recovery

Compaction 발생 시, 가장 최근 STATE 블록에서 상태를 복원하여 인터뷰를 이어간다.
복원 시 Depth 점수와 Challenge Mode 상태도 함께 복원한다.

## File Persistence (Optional)

사용자 요청 시 인터뷰 상태를 파일로 저장하여 세션 간 재개를 지원한다.

### 저장 경로

```text
docs/discovery/{target-name}/state.md
```

`{target-name}`은 분석 대상을 kebab-case로 변환 (예: "결제 시스템 도입" → `payment-system`).

### 저장 트리거

- 사용자 명시적 요청: "저장해줘", "save state", "나중에 이어하자"
- Phase 2 진입 전 사용자에게 저장 여부 확인 (선택)

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
Target: {name} | Domain: {domain} | Maturity: {maturity} | Phase: {phase}
Progress: [assumptions:{status}:{score}%] [trade-offs:{status}:{score}%] [edge-cases:{status}:{score}%] [blindspots:{status}:{score}%]
Depth: {weighted_avg}% | Q: {total_count} | CP: {checkpoint_count}
Challenges: [inverter:{done|pending}] [outsider:{done|pending}] [pre-mortem:{done|pending}]

Discoveries:
1. [{C|I|N}] {finding title} — {one-line description}
<!-- /STATE -->

## Interview History

| Round | Area | Question Summary | Key Finding |
|-------|------|-----------------|-------------|
| 1 | Assumptions | {summary} | {finding or —} |
| ... | ... | ... | ... |
```

### 재개 절차

1. 새 세션에서 사용자가 "이어서 해줘", "resume", "이전 인터뷰 계속" 등 요청
2. `docs/discovery/` 하위 디렉토리에서 저장된 state 파일 탐색
3. STATE 블록에서 Phase, Depth, Progress, Challenges 복원
4. Interview History에서 이전 질문/발견 맥락 복원
5. 복원된 상태를 사용자에게 요약 후 인터뷰 재개
