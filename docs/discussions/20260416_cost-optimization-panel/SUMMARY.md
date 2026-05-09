# Cost Optimization Expert Panel - Summary

**Date**: 2026-04-16
**Context**: claude-kit 사용 통계 분석 (91% subagent-heavy, 51% >150k context)
**Participants**: Moderator, Optimistic Practitioner, Critical Practitioner, Cost/Infra Expert, Plugin Architect, UX Expert

---

## Background

claude-kit 프로젝트의 비용 구조를 분석한 결과 두 가지 핵심 문제가 확인됨:
1. **91% subagent-heavy 세션**: 각 서브에이전트가 자체 request를 사용하여 비용 증가
2. **51% >150k context 세션**: 긴 세션으로 인한 캐시 미스 및 compaction 비용

이에 대해 5가지 개선안을 전문가 패널에서 평가함.

---

## Decision Matrix

| # | Topic | Decision | Priority | Risk | Impact |
|---|-------|----------|----------|------|--------|
| 1 | thinking-facilitator Haiku downgrade | Approved (conditional) | 1순위 | Low | High |
| 2 | vault-knowledge-manager Haiku downgrade | Hold | 보류 | High | Low |
| 3 | thought-chain delegation removal | Redefined | 3순위 | Medium | Medium |
| 4 | SKILL.md slimming | Hold | 보류 | Medium | Low |
| 5 | context skill fork removal | Rejected | 기각 | High | Negative |

---

## Consensus Items

### 1. thinking-facilitator Sonnet → Haiku (Approved)

**근거**: 결정 트리 기반 라우팅 전용 에이전트로, classification 작업은 Haiku의 강점 영역. 약신호 시 AskUserQuestion 안전장치가 있어 라우팅 실패 리스크 완화.

**조건**:
- 경계 케이스 10개(다중 신호, 모호한 요청) 테스트 후 라우팅 정확도 95% 이상 확인
- 실패 시 Sonnet 복귀 경로 확보 (frontmatter model 변경만으로 가능)

**예상 효과**: 세션당 ~60% 비용 절감 (facilitator 호출 부분), 91% 세션에 영향

### 2. vault-knowledge-manager Sonnet 유지 (Hold)

**근거**: 12개 도메인 분류법 기반 맥락 판단, MOC 링크 생성, project memory 활용 등 Sonnet 수준의 추론이 필요. Haiku 전환 시 도메인 분류 오류가 누적되는 "조용한 실패" 리스크. vault 세션 비율(~20-30%)을 감안하면 절대 절감액도 제한적.

### 3. thought-chain 파이프라인 재정의 (Redefined)

**핵심 발견**: 원래 제안("facilitator 재호출 제거")은 현재 구조에 해당 없음. thought-chain은 자체적으로 Skill 도구로 하위 스킬을 호출하며, facilitator는 초기 라우팅에서만 개입.

**실제 문제**: 4단계 스킬의 출력이 동일 컨텍스트에 누적되어 >150k 도달.

**대안 검토 필요**:
- 단계 간 출력 요약(compaction) 메커니즘 도입
- fork 전환은 subagent 비용 증가와 트레이드오프

### 4. SKILL.md 슬림화 불필요 (Hold)

**핵심 발견**: SKILL.md 200줄은 ~3-4K 토큰으로 전체 context 150K 대비 2-3%에 불과. reference.md는 이미 선택적 로드 구조. 슬림화의 비용 효과가 미미하고, 스킬 실행 품질 저하 리스크만 증가.

### 5. context skill fork 유지 (Rejected)

**핵심 발견**: fork 제거가 오히려 역효과. vault 탐색의 중간 결과가 부모 context를 오염시켜 >150k 문제를 악화. fork의 subagent 비용(~$0.01-0.03)은 context 보호 효과 대비 미미.

---

## Action Items

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | thinking-facilitator model: haiku 변경 | - | Pending |
| 2 | Haiku 라우팅 정확도 테스트 (경계 케이스 10개) | - | Pending |
| 3 | thought-chain compaction 메커니즘 설계 | - | Research |

---

## Key Insights

1. **비용의 실체**: 에이전트 모델 다운그레이드보다, 컨텍스트 누적이 >150k 문제의 주요 원인. SKILL.md 크기는 무시할 수준.
2. **fork의 이중성**: subagent 비용을 추가하지만 부모 context를 보호. 단순히 subagent 수를 줄이는 것이 항상 최적은 아님.
3. **조용한 실패 vs 시끄러운 실패**: 라우팅 오류(재시도 가능)보다 도메인 분류 오류(누적되는 조용한 실패)가 더 위험.
4. **구조 확인의 중요성**: 제안 3, 5번은 실제 구조를 확인한 결과 전제가 틀렸음. 최적화 전에 현행 구조를 정확히 파악해야 함.

---

*5개 토픽 논의 완료 -- 1개 승인, 1개 재정의, 2개 보류, 1개 기각*
