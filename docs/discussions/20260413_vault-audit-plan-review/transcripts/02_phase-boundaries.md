# Transcript 02 — Phase Boundaries & Migration

## Briefing
- [Optimistic] Phase 0 → A → B 점진 확장
- [Critical] Phase A 전면 재작성 중 기능 퇴행 위험

## Q&A
- [DevEx] Feature branch 전략. 병렬 검증 + dogfood 후 merge.
- [Architecture] Claude Code skill은 파일명=트리거. v2 접미사 불가 → git branch로 분리 + 1주 dogfood.
- [Performance] Phase 0 MVP 축소 (Phase A에 필요한 것만). orphan/MOC/그래프는 Phase B로 연기.
- [UX] Phase A→B 이동 체크리스트 필요: JSON 스키마, AskUserQuestion 패턴, 출력 포맷, mark-clean 호출점.

## Dialectic
- Thesis: Phase 0 전부
- Antithesis: 핵심만
- Synthesis: MVP 축소 + feature branch + 5건 dogfood + 체크리스트

## Conclusion
계획서 반영: Phase 0 MVP 목록 명시, Phase B 확장 목록, `feature/inbox-review-pipeline` 브랜치, dogfood 기준, 이동 체크리스트 4항목.
