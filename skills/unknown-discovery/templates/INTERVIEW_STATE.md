# Interview State

인터뷰 진행 중 상태를 STATE 블록으로 추적한다.

## STATE Block Format

매 체크포인트마다 다음 형식을 출력:

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Domain: {domain} | Phase: {0|1|2|3}
Progress: [assumptions:{done|active|pending}] [trade-offs:{status}] [edge-cases:{status}] [blindspots:{status}]
Q: {total_count} | CP: {checkpoint_count}

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
| Priority | `C`=Critical, `I`=Important, `N`=Nice-to-have |

## Termination Signals

| Signal | Count toward saturation |
|--------|------------------------|
| Short response (< 20자) | +1 |
| Repetition (similar to previous) | +1 |
| Avoidance ("나중에", "괜찮아") | +1 |

**Saturation**: 3 consecutive signals → confirm termination with user.

## Compaction Recovery

Compaction 발생 시, 가장 최근 STATE 블록에서 상태를 복원하여 인터뷰를 이어간다.
