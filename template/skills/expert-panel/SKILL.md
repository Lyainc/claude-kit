---
name: expert-panel

description: |
  Facilitate structured expert panel discussions with dialectical analysis for decision-making.
  Simulates debates between optimistic practitioners, critical practitioners, and domain experts
  to reach consensus through thesis-antithesis-synthesis methodology.
  Use when reviewing proposals, designs, code, policies, or documents with multiple expert perspectives,
  or when the user mentions 전문가 토론, 패널 논의, 찬반 토론, 합의 도출, 다관점 분석, 검토 회의, 리뷰 세션.
---

# Expert Panel Discussion

전문가 패널 토론 스킬. 다양한 관점의 전문가들이 변증법적 토론을 통해 합의를 도출한다.

## When to Use This Skill

- 기획안/설계 문서에 대해 다양한 관점의 검토가 필요할 때
- 코드 리뷰에서 찬반 의견을 체계적으로 정리하고 싶을 때
- 정책/제도 변경 전 이해관계자 관점 시뮬레이션이 필요할 때
- 중요한 의사결정에서 장단점을 균형있게 분석하고 싶을 때
- 복잡한 트레이드오프를 구조화된 논의로 정리하고 싶을 때

## Participants

### Fixed (Always Present)

| Role | Description |
|------|-------------|
| **Moderator** | 토론 진행, 논의 개폐 권한, 팩트체크 요청, 미해결 이슈 기록 |
| **Optimistic Practitioner** | 제안의 장점과 실현 가능성 옹호, 현실적 구현 방안 제시 |
| **Critical Practitioner** | 리스크와 한계 지적, 대안적 관점 제공 |

### Variable (User-specified)

| Role | Description |
|------|-------------|
| **Expert Panel** | 유저가 지정하는 도메인 전문가 3명 이상 (예: 보안, UX, 성능, 법률, LLM 등) |

**중요**: 전문가는 해당 분야의 핵심 메커니즘, 측정 지표, 선례를 기반으로 사고합니다 (상세: [reference.md](reference.md)).

## Consensus Rules

| Item | Rule |
|------|------|
| Principle | 만장일치제 (1명 소수의견까지 인정) |
| Moderator | 투표권 없음, 진행 권한만 보유 |
| Experts | 최소 3명 이상 구성 |
| Re-discussion | 전문가 2명 이상 반대 시 해당 토픽 재논의 |

## Core Workflow

### Phase 0: Preparation
1. 검토 대상 분석 → 토픽 분할
2. 전문가 집단 구성 확인
3. 토론 아젠다 생성

### Phase 1: Topic Rounds
각 토픽에 대해:
1. **Briefing**: 실무자들이 찬반 관점 제시
2. **Q&A**: 전문가들의 질의응답
3. **Dialectic**: 정(Thesis) → 반(Antithesis) → 합(Synthesis)
4. **Conclusion**: 합의 또는 보류 결정

### Phase 2: Recording (MANDATORY)

토론 종료 후 **반드시** 다음 문서를 생성해야 합니다:

1. **미가공 속기록**: `docs/discussions/{YYYYMMDD}_{name}/transcripts/{순번}_{topic}.md`
   - 모든 발언을 시간순으로 기록 (템플릿: `templates/TRANSCRIPT_TEMPLATE.md`)

2. **요약본**: `docs/discussions/{YYYYMMDD}_{name}/SUMMARY.md`
   - 합의 사항, 권고사항, 액션 아이템 정리 (템플릿: `templates/SUMMARY_TEMPLATE.md`)

3. **미해결 이슈**: `docs/discussions/{YYYYMMDD}_{name}/UNRESOLVED.md`
   - 보류된 토픽 상세 기록 (템플릿: `templates/UNRESOLVED_TEMPLATE.md`)

**중요**: 문서 생성 없이 토론을 종료할 수 없습니다. 모든 토픽 논의 완료 즉시 Phase 2로 진행합니다.

### Phase 3: Moderator Authority
- 팩트체크 필요 시 유저에게 정보 요청
- 논의 발전 없음 판단 시 강제 종료
- 미해결 이슈 별도 기록

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Conversation examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder

## Quick Start

```
User: "이 API 설계 문서를 보안/성능/UX 전문가 관점에서 검토해줘"

→ Phase 0: 토픽 분할 (인증, 페이지네이션, 에러처리)
→ Phase 1: 각 토픽별 찬반 토론 진행
→ Phase 2: 합의사항 및 미해결 이슈 기록
→ Output: SUMMARY.md + transcripts/
```
