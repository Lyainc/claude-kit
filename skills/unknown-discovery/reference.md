# Unknown Discovery - Reference Guide

상세 절차 및 판단 기준 가이드.

## 1. 대상 유형별 접근

| 유형 | 분석 포인트 | 초기 질문 방향 |
|------|------------|---------------|
| **프로젝트** | 목표, 범위, 제약조건 | 기술적 가정, 리소스 한계 |
| **기획안** | 핵심 가치, 타겟 사용자 | 시장 가정, 사용자 행동 예측 |
| **의사결정** | 선택지, 기준, 영향 범위 | 평가 기준의 완전성, 이해관계자 |
| **아이디어** | 핵심 컨셉, 차별점 | 실현 가능성, 수용성 |

## 2. Domain Presets

| Preset | Focus Areas | Specialized Questions |
|--------|-------------|----------------------|
| **Tech** | Edge Cases, Dependencies | Performance, scalability, security |
| **Biz** | Stakeholders, Trade-offs | ROI, market, competition, legal |
| **Creative** | Assumptions, Counterfactual | Originality, acceptance, trends |
| **Custom** | User-defined | User-specified areas |

## 3. 불확실성 신호 감지

| 신호 | 감지 기준 | 대응 |
|------|----------|------|
| **Hedging** | "아마", "글쎄", "확실하진 않은데" | 해당 영역 후속 질문으로 심화 |
| **짧은 응답** | < 20자 (한글) / < 10 words (영어) | "좀 더 구체적으로 말씀해주시겠어요?" |
| **회피** | "나중에 생각해볼게", "별로 중요하지 않아" | Why 체인 강화: "왜 중요하지 않다고 생각하시나요?" |
| **반복** | 이전 답변과 유사한 내용 | 다른 영역으로 전환 또는 포화 카운트 |

**포화 판정**: 3개 연속 신호 → 해당 영역 종료 확인 후 전환.

## 4. 우선순위 분류 기준

| 우선순위 | 기준 | 예시 |
|---------|------|------|
| **Critical** | 프로젝트 실패 가능성, 즉시 조치 필요 | 법적 리스크, 핵심 가정 오류 |
| **Important** | 품질/성과에 영향, 계획 수정 필요 | 누락된 이해관계자, 리소스 부족 |
| **Nice-to-have** | 개선 기회, 선택적 대응 | 추가 기능 아이디어, 최적화 포인트 |

## 5. Checklist

### Phase 0
- [ ] 분석 대상 명확히 정의
- [ ] 도메인 사용자와 확인

### Phase 1
- [ ] Core 4 영역 모두 최소 1회 탐색
- [ ] 각 질문에 Why 체인 수행
- [ ] 최소 2회 체크포인트 (STATE 블록 출력)
- [ ] 포화 신호 또는 명시적 완료 확인
- [ ] Gap check 질문 수행

### Phase 2
- [ ] 모든 발견에 우선순위 태깅
- [ ] 핵심 인사이트 최소 2개 추출

### Phase 3
- [ ] Discovery Report 생성
- [ ] Critical 항목에 액션 아이템 포함
