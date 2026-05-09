# Transcript 05 — Success Criteria & Baseline

## Briefing
- [Performance] "3~5x 감축"은 베이스라인 없이 무의미
- [UX] Phase A 완료는 기능 + 체감 혼합

## Q&A
- [Performance] 베이스라인 = 현 inbox-review 100노트 처리 시 토큰/시간/상호작용 실측. 목표 = 1/3~1/5. `metrics` 서브커맨드로 token_in/out 누적.
- [UX] Phase A 완료 기준: 5개 입력 문법 동등 + 토큰 ≥3x + 실사용 5건 중 4건 긍정.
- [Critical] 체감은 주관적 → 작업 완료 시간 + 상호작용 횟수로 보완.
- [Architecture] Phase B 완료: 합성 볼트 탐지율 ≥93% / FP <10% / 재스캔 50% 감축 / dry-run→apply 흐름.
- [DevEx] CI에서 자동 검증 가능한 항목만 공식 기준, 체감은 릴리스 노트 부가.

## Dialectic
- Thesis: 정성적 "더 나음"
- Antithesis: 정량만
- Synthesis: 정량 지표를 성공 기준, 정성 피드백은 보조. 베이스라인 선행 측정.

## Conclusion
계획서 반영: Phase 0에 `baseline-measure.sh` 추가 → `docs/baseline.md`. Phase A/B 완료 기준을 정량 수치로 명시.
