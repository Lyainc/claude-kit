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

## 6. Domain-Specific Question Banks

### Tech Domain

| Area | Deep-Dive Questions |
|------|-------------------|
| Architecture | "If this component fails at 3 AM, what's the blast radius?" / "Which service is the single point of failure?" |
| Scale | "At 10x current load, which component breaks first?" / "What's your data growth rate and when do you hit storage limits?" |
| Security | "Who has admin access? What's the attack surface for this API?" / "How do you handle secrets rotation?" |
| Operations | "What's your deployment rollback procedure?" / "How do you detect silent failures?" |
| Dependencies | "Which third-party service going down blocks your users?" / "What's your SDK/library upgrade strategy?" |

### Biz Domain

| Area | Deep-Dive Questions |
|------|-------------------|
| Market | "Who are the indirect competitors you haven't considered?" / "What's the customer switching cost?" |
| Stakeholders | "Who loses if this succeeds? Were they consulted?" / "Who has veto power you haven't identified?" |
| Finance | "What's the true total cost including hidden costs?" / "What's the revenue model under pessimistic assumptions?" |
| Legal/Compliance | "Which regulations apply across all target markets?" / "What if the regulatory environment changes?" |
| Timing | "Why now? What happens if you're 6 months late?" / "Is there a market window you'd miss?" |

### Creative Domain

| Area | Deep-Dive Questions |
|------|-------------------|
| Audience | "Who is NOT the target audience, and why might they object?" / "How does the target demographic consume this type of content?" |
| Sustainability | "Can this concept scale beyond the initial launch?" / "What's the maintenance burden post-release?" |
| Originality | "What's this most similar to in the market?" / "How do you differentiate from [closest competitor]?" |
| Trends | "Is this riding a trend or creating one? What happens when the trend fades?" |

## 7. Uncertainty Signal Response Examples

### Hedging Signal

> **Q**: "이 아키텍처가 트래픽 급증을 감당할 수 있을까요?"
> **A**: "아마... 대부분은 괜찮을 거예요."
> **Follow-up**: "어떤 부분이 '대부분'에 해당하고, 어떤 부분이 불확실한가요?"
> *Detection*: "아마" = hedging → drill deeper into the uncertain area

### Short Response Signal

> **Q**: "데이터 백업 전략은 어떻게 되어 있나요?"
> **A**: "있어요."
> **Follow-up**: "구체적으로 어떤 주기로, 어디에, 어떤 방식으로 백업하고 있나요?"
> *Detection*: Response < 20 chars → probe for specifics

### Avoidance Signal

> **Q**: "경쟁사 대비 가격 전략은 어떤가요?"
> **A**: "그건 나중에 정하면 될 것 같아요."
> **Follow-up**: "왜 나중에 정해도 된다고 생각하시나요? 지금 정하지 않으면 어떤 리스크가 있을까요?"
> *Detection*: "나중에" + topic change = avoidance → Why chain

### Repetition Signal

> **Q**: "다른 관점에서 보면 어떤 리스크가 있을까요?"
> **A**: "아까 말한 것처럼 인프라가 좀 부족한 게..."
> **Follow-up**: [Area transition] "인프라 관련은 충분히 논의한 것 같습니다. 다른 영역으로 넘어가 볼까요?"
> *Detection*: Overlaps with prior answer → saturation count +1, transition to next area

## 8. Extended Areas Procedure

### Entry Criteria

- All Core 4 areas (Assumptions, Trade-offs, Edge Cases, Blindspots) explored at minimum 1-depth
- Ask user: "핵심 4개 영역 탐색을 마쳤습니다. 추가 영역도 살펴볼까요?"

### Available Extended Areas

| Area | Focus | Question Count |
|------|-------|---------------|
| Feasibility | Resource, timeline, technical constraints | 2-3 |
| Stakeholders | Decision-makers, affected parties, influencers | 2-3 |
| Counterfactual | "What if you did nothing?" / "What if you chose the opposite?" | 2 |
| Dependencies | External dependencies, blocking factors, critical path | 2-3 |

### Procedure

1. Present extended area options to user (AskUserQuestion, multiSelect)
2. For each selected area: ask 2-3 focused questions
3. Why chain is optional for extended areas (only if uncertainty signal detected)
4. No checkpoint required between extended areas
5. After all selected areas → proceed to Phase 2

### Skip Conditions

- User declines extended exploration
- Total question count already exceeds 15
- User shows fatigue signals (consecutive short answers)

## 9. Interview Flow Control

### Depth vs Breadth Balance

| Signal | Action |
|--------|--------|
| User gives detailed, enthusiastic responses | Go deeper (add Why chain) |
| User gives brief but clear responses | Move to next question in same area |
| User gives vague or deflective responses | Note as finding, move to next area |
| User explicitly asks to move on | Transition immediately |

### Fatigue Management

- **Question budget**: Soft limit of 12-15 questions for Core 4 areas
- **Engagement check**: After 8+ questions, assess response quality trend
- **Fatigue signals**: Decreasing response length, increasing "I don't know", longer pauses
- **Response**: "지금까지 좋은 인사이트들이 나왔습니다. 계속 진행할까요, 아니면 여기서 정리할까요?"

### Topic Transition

- Summarize current area findings before moving
- Use bridging phrases: "이 영역은 충분히 다룬 것 같습니다. 다음으로..."
- Never abruptly change topics without acknowledgment

### Recovery Strategies

- If user seems confused: simplify question and provide concrete example
- If answers become circular: reframe from different angle
- If user pushes back on question: acknowledge and offer to skip

## 10. Output Terminology

### Priority Labels

| Internal | Korean Report | English Report |
|----------|-------------|---------------|
| Critical | 즉시 대응 필요 | Requires immediate action |
| Important | 계획 수정 권장 | Plan adjustment recommended |
| Nice-to-have | 개선 기회 | Improvement opportunity |

### Finding Types

| Internal | Korean Report | English Report |
|----------|-------------|---------------|
| Assumption gap | 검증되지 않은 가정 | Unverified assumption |
| Blind spot | 미인지 영역 | Unrecognized area |
| Trade-off missed | 미고려 트레이드오프 | Unconsidered trade-off |
| Edge case | 극단적 시나리오 | Extreme scenario |
| Dependency risk | 의존성 리스크 | Dependency risk |

### Interview Status

| Internal | Korean Display | English Display |
|----------|-------------|---------------|
| Saturation | 탐색 완료 | Exploration complete |
| In progress | 진행 중 | In progress |
| Skipped | 건너뜀 | Skipped |
| Depth limit | 깊이 한도 도달 | Depth limit reached |
