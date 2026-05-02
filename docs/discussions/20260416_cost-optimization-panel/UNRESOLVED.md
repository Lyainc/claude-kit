# Cost Optimization Expert Panel - Unresolved Issues

**Date**: 2026-04-16
**Related**: [SUMMARY.md](SUMMARY.md)

---

## Issue 1: thought-chain Compaction Mechanism

**Origin**: Topic 3 토론에서 재정의됨
**Status**: Research needed

**문제**: thought-chain 4단계 파이프라인(unknown-discovery → expert-panel → doc-concretize → doc-polish)의 출력이 동일 컨텍스트에 누적되어 >150k context 도달. 특히 expert-panel 단계에서 대량의 토론 transcript가 생성됨.

**검토된 대안**:

| 대안 | 장점 | 단점 |
|------|------|------|
| 단계별 fork 분리 | context 누적 방지 | subagent 비용 4배 증가, 91% subagent-heavy 악화 |
| 단계 간 요약 전달 | context 절감 + subagent 비용 없음 | 정보 손실 리스크, 요약 품질 의존 |
| /compact 자동 호출 | 기존 메커니즘 활용 | 타이밍 제어 어려움, 중요 context 손실 가능 |

**다음 단계**: 세 가지 대안의 실제 token 소비량을 측정하고, 정보 손실 대비 비용 절감 트레이드오프를 정량화.

---

## Issue 2: Haiku Routing Accuracy Validation

**Origin**: Topic 1 합의 조건
**Status**: Validation needed

**문제**: thinking-facilitator를 Haiku로 다운그레이드하기 전, 경계 케이스에서의 라우팅 정확도를 검증해야 함.

**검증 필요 케이스**:
1. "이 설계를 여러 관점에서 깊이 분석해줘" → expert-panel vs thought-chain
2. "다양한 대안을 만들어줘" → diverse-sampling vs expert-panel
3. "이 문서 검토해줘" → doc-polish vs expert-panel
4. "블라인드스팟 찾고 문서화해줘" → thought-chain vs unknown-discovery + doc-concretize
5. 복합 신호: "브레인스토밍하면서 전문가 의견도 듣고 싶어"
6. 약신호: "이거 좀 봐줘" (모호한 요청)
7. 한국어/영어 혼용 트리거
8. 부정형: "전문가 토론 말고 다른 방법으로"
9. 연쇄 요청: "먼저 A하고 그다음 B해줘"
10. 무관한 요청: thinking-tools 범위 밖 요청의 적절한 거부

**기준**: 10개 중 9.5개 이상 정확 (95%), AskUserQuestion 안전장치 정상 작동 확인

---

## Issue 3: Subagent-Heavy Root Cause

**Origin**: 전체 토론 관통 이슈
**Status**: Analysis needed

**문제**: 91% subagent-heavy는 에이전트 모델 다운그레이드만으로 해결되지 않음. 근본 원인은 delegation 체인의 깊이와 빈도.

**가설**:
- 일반 코딩 세션에서 OMC 레이어가 자동으로 다수의 에이전트를 spawn (executor, verifier, code-reviewer 등)
- thinking-tools 사용 시 facilitator → skill → 내부 delegation의 3단 구조
- vault 작업 시 vault-searcher + vault-knowledge-manager + context fork의 동시 활성

**다음 단계**: 실제 세션 로그를 분석하여 subagent spawn 패턴과 빈도를 정량화. 어떤 워크플로우가 가장 많은 subagent를 생성하는지 식별.

---

*3개 미해결 이슈 -- 1개 Research, 1개 Validation, 1개 Analysis*
