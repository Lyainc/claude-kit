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
- [ ] Post-Discovery 옵션 제시

## 6. Exploration Depth Scoring

매 체크포인트마다 4개 Core Area의 탐색 깊이를 0-100%로 평가한다.
이 점수는 (1) 사용자에게 진행 현황을 투명하게 보여주고, (2) 다음 질문의 타겟 영역을 결정하며, (3) 종료 판정의 객관적 기준이 된다.

### 점수 산정 기준

| 구간 | 기준 | 전형적 상황 |
|------|------|------------|
| **0-30%** | 질문 미시작 또는 1Q 진행, 표면적 답변만 | 영역 진입 직후 |
| **30-60%** | 기본 질문 완료, 답변에 구체성 있음 | Why chain 전 |
| **60-80%** | Why chain 완료, 구체적 발견 1개 이상 도출 | 심화 탐색 완료 |
| **80-100%** | 구체적 발견 + 불확실성 신호 없음 + 사용자 자체 인사이트 발현 | 영역 포화 |

### 가중치

기본 가중치 (성숙도별 조정은 §9 참조):

| Dimension | 가중치 | 근거 |
|-----------|--------|------|
| Assumptions | 0.30 | 가정 오류가 가장 큰 리스크 |
| Trade-offs | 0.25 | 의사결정의 기회비용 |
| Edge Cases | 0.25 | 실행 시 예상 밖 상황 |
| Blindspots | 0.20 | 메타 영역, 다른 영역에서 간접 커버 |

### 전체 Depth 계산

```
Depth = Σ (dimension_score × weight) × 100%
```

### Termination Gate

- **Depth ≥ 65%**: Phase 2 진입 가능 (사용자 동의 필요)
- **Depth < 65%**: 가장 낮은 영역에 추가 질문 권장
- 기존 포화 감지(3연속 신호)는 **보조 지표**로 유지: 점수가 65% 미만이어도 포화 시 사용자에게 확인 후 진행 가능

### 점수 하락 조건

불확실성 신호 감지 시 해당 영역 점수를 **10% 차감**하여 재탐색을 유도한다.
(예: Hedging 감지 → 해당 영역 점수 60% → 50%로 하락)

## 7. Dynamic Area Targeting

고정 순서 대신, 매 라운드마다 Exploration Depth가 가장 낮은 영역을 자동으로 타겟팅한다.

### 알고리즘

```
1. 첫 라운드: 항상 Assumptions (모든 발견의 기초)
2. 이후 라운드:
   a. 각 영역의 현재 Exploration Depth 점수 확인
   b. 가장 낮은 점수의 영역을 타겟
   c. 동점 시: Assumptions > Trade-offs > Edge Cases > Blindspots 순
3. 불확실성 신호가 감지된 영역: 점수 차감(§6) 후 재평가
```

### 전환 표시

영역이 전환될 때 사용자에게 자연스럽게 알린다:

```
[Trade-offs → Edge Cases] 트레이드오프는 충분히 살펴본 것 같습니다.
이제 극단적 상황에서의 리스크를 살펴보겠습니다.
```

매 질문 앞에 `[영역명]` 태그를 유지하여 현재 위치를 명확히 한다.

## 8. Challenge Modes

인터뷰 중 특정 시점에 관점 전환 질문을 삽입하여 사고 패턴을 흔든다.
각 모드는 인터뷰당 **1회만** 사용하며, **1-2Q**로 제한한다.

### 모드 정의

| Mode | 진입 조건 | 목적 | 질문 패턴 |
|------|----------|------|----------|
| **Inverter** | 라운드 3+ | 핵심 가정 뒤집기 | "만약 {핵심 가정}이 틀렸다면 어떻게 되나요?" |
| **Outsider** | 라운드 5+ | 외부자 시각 확보 | "이 분야를 전혀 모르는 사람이 보면 가장 이상한 점은?" |
| **Pre-mortem** | 라운드 7+ 또는 Depth 60%+ | 미래 실패 역추적 | "1년 후 이것이 실패했다면, 가장 큰 원인은 무엇일까요?" |

### 질문 예시

**Inverter**:
- "지금까지 {X}가 전제라고 하셨는데, 만약 {X}가 아니라면 이 계획은 어떻게 달라지나요?"
- "경쟁사가 같은 전제를 두고 실패했다면, 그 이유가 뭘까요?"

**Outsider**:
- "이 프로젝트를 처음 듣는 신입사원에게 설명한다면, 그 사람이 가장 먼저 던질 질문은?"
- "다른 산업(예: 항공/의료)에서 비슷한 문제를 어떻게 풀었을까요?"

**Pre-mortem**:
- "프로젝트 사후 분석에서 '이걸 미리 알았어야 했다'고 할 만한 것은?"
- "최악의 시나리오가 현실이 됐을 때, 가장 먼저 무너지는 부분은?"

### 전환 문구

Challenge Mode 진입 시 자연스러운 전환:

```
[Inverter] 지금까지의 흐름에서 잠시 관점을 바꿔보겠습니다.
핵심 가정을 뒤집어서 생각해 볼게요.
```

### 발동 추적

STATE 블록에 사용된 Challenge Mode를 기록:
```
Challenges: [inverter:done] [outsider:pending] [pre-mortem:pending]
```

## 9. Maturity Detection

Phase 0에서 대상의 성숙도를 감지하여 인터뷰 전략을 조정한다.
Domain(Tech/Biz/Creative)과 독립적으로 작동하는 직교 축이다.

### 성숙도 단계

| 성숙도 | 감지 신호 | 인터뷰 특성 |
|--------|----------|------------|
| **Idea** | 구체적 수치/일정 없음, "~할 것 같다" 표현, 비교 대상 부재 | 탐색적, 가능성 중심 |
| **Plan** | 마일스톤/리소스/일정 언급, 구체적 선택지 존재 | 검증적, 트레이드오프 중심 |
| **Execution** | 진행 상황/이슈/메트릭 언급, 실제 데이터 참조 | 진단적, 리스크 중심 |

### 가중치 조정

| Dimension | Idea | Plan | Execution |
|-----------|------|------|-----------|
| Assumptions | **0.35** | 0.30 | 0.25 |
| Trade-offs | 0.25 | **0.30** | 0.25 |
| Edge Cases | 0.20 | 0.25 | **0.30** |
| Blindspots | 0.20 | 0.15 | 0.20 |

### Phase 0 질문

Domain 확인 후, 성숙도를 AskUserQuestion으로 확인:

```
현재 단계가 어디에 해당하나요?

1. 아이디어 단계 — 아직 구체적 계획 없이 방향을 탐색 중
2. 계획 단계 — 구체적 일정/리소스/마일스톤이 있음
3. 실행 단계 — 이미 진행 중이며 중간 점검이 필요
```

## 10. Domain-Specific Question Banks

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

## 11. Output Terminology

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
