# Transcript 04 — Implementation Priority

## Briefing

**[Optimistic Practitioner]**: inbox-review 현재 사용 중. 먼저 개선 시 즉각 체감.

**[Critical Practitioner]**: (A) 리팩토링에 공통 프리미티브(scanner, audit-state) 선행 필요. 그 프리미티브는 (B) 설계 시 확정. 순서 역전 가능성.

## Q&A

**[Architecture Expert]**: 정확한 지적. Phase 0 추가: audit-state sidecar + 공통 프리미티브 선착공. 없이 (A) 리팩토링하면 두 번 수정.

**[UX Expert]**: (A)에서 AskUserQuestion·evidence·진행률 포맷 확정, (B)가 계승. 순서 타당.

**[PKM Expert]**: (C) graphify-vault는 nice-to-have. 볼트 사용자 대부분 graphify 모름. 후순위/백로그.

**[Performance Expert]**: 프리미티브 단계에서 측정 인프라(토큰 카운터, 스캔 시간) 동시 도입. (B)에서 "10x 현실성" 검증 가능.

## Dialectic

- Thesis: A→B→C
- Antithesis: Phase 0 선행 필요
- Synthesis: (0) 프리미티브 + 측정 → (A) inbox-review 리팩토링 → (B) vault-audit + 플래그 → (C) graphify-vault (백로그)

## Conclusion

**결론**: Phase 0 신설, (C) 선택적 백로그 강등.
