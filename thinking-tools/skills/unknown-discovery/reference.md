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

### 신호별 대응 예시

**Hedging**:
> **Q**: "이 아키텍처가 트래픽 급증을 감당할 수 있을까요?"
> **A**: "아마... 대부분은 괜찮을 거예요."
> **Follow-up**: "어떤 부분이 '대부분'에 해당하고, 어떤 부분이 불확실한가요?"

**짧은 응답**:
> **Q**: "데이터 백업 전략은 어떻게 되어 있나요?"
> **A**: "있어요."
> **Follow-up**: "구체적으로 어떤 주기로, 어디에, 어떤 방식으로 백업하고 있나요?"

**회피**:
> **Q**: "경쟁사 대비 가격 전략은 어떤가요?"
> **A**: "그건 나중에 정하면 될 것 같아요."
> **Follow-up**: "왜 나중에 정해도 된다고 생각하시나요? 지금 정하지 않으면 어떤 리스크가 있을까요?"

**반복**:
> **Q**: "다른 관점에서 보면 어떤 리스크가 있을까요?"
> **A**: "아까 말한 것처럼 인프라가 좀 부족한 게..."
> **Follow-up**: [영역 전환] "인프라 관련은 충분히 논의한 것 같습니다. 다른 영역으로 넘어가 볼까요?"

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

매 체크포인트마다 4개 Core Area의 탐색 깊이를 아래 **Y/N 이진 체크리스트**로 판정한다.
자유 채점(0-100% 임의 부여)은 금지 — 점수는 항상 Y 항목 가중치의 합이고, 그래서 같은 인터뷰는 몇 번을 채점해도 같은 점수가 나온다.
이 점수는 (1) 다음 질문의 타겟 영역을 결정하고, (2) 종료 판정의 객관적 기준이 된다. 사용자에게는 수치가 아니라 정성 표기(충분/진행 중)만 보인다.

**채점은 기본적으로 인라인이다.** 격리 Agent 채점은 **게이트 임박 라운드**에서만 돈다 —
`build-spec`(`build-spec/reference.md` §2)과 같은 이유로, 매 체크포인트마다 서브에이전트를
부르는 건 바뀌지도 않을 결과에 매번 비용을 쓰는 것이다.

**게이트 임박 라운드의 정의**: 방금 계산한 인라인 점수가 이미 아래 Termination Gate 조건
(`Depth ≥ 65% AND 진입한 모든 Core 영역에서 D4 = Y`)을 만족하는 체크포인트 — 인라인 숫자로
게이트가 열리는 바로 그 라운드다. 거기서만 같은 체크리스트를 격리 재채점해서, 실제로 게이트를
여는 건 인라인 값이 아니라 이 재채점 결과다.

**격리 채점**: 게이트 임박 라운드에서만, 이 체크리스트를 인터뷰를 진행한 컨텍스트가 아니라
별도 Agent 서브에이전트에서 판정한다. 서브에이전트에 넘기는 입력은
`{진입한 각 Core 영역의 Q&A 전문 + 이 체크리스트 + 그 영역에서 주장된 발견 목록}`뿐이고,
받는 출력은 `{항목별 Y/N + 한 줄 근거 + 영역 점수}`(영역별로 하나씩)다. 그 외 라운드는 같은
체크리스트로 인라인 채점하고 STATE에 `scoring_isolated: false`를 기록한다 (실패가 아니라
설계상 인라인). 게이트 임박 라운드에서 Agent 호출이 실패하면 같은 값(`false`)을 기록하되
SKILL.md가 지정한 1줄 경고(`[격리 채점 실패 — 자체 채점, 신뢰도 낮음]`)를 출력한다.

**재드리프트 방지**: 이 정책이 `build-spec`과 계속 같은 모양을 유지하는지는 CI가 보장하지
않는다 — 자동 검증 없음, 사람이 두 스킬을 나란히 리뷰할 때 지키는 수동 규율이다
([../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md) 참고).

**정책 차단도 "호출 실패"의 한 형태다** (#433 잔여 스코프): 세션 정책이 `Agent` 호출 자체를 막아도(예: "요청 없이는 서브에이전트 금지") 위 fallback을 그대로 탄다 — 인라인 채점 + 한 줄 고지, 승인을 다시 묻는 `AskUserQuestion`은 추가하지 않는다. 정책 차단은 harness 권한 게이트를 이미 한 번 거친 결과라 다시 물으면 방금 난 결정을 재확인하는 셈이고, 무인 실행 중엔 응답 없이 저위험 분기(=지금 동작)로 귀결되며(`P6`), `#430`이 못박은 인터뷰 길이 제약상 메타 질문도 라운드 하나를 늘리는 비용이다. `scoring_isolated`는 체크포인트 출력의 고지 한 줄로 이미 노출되므로, STATE 블록 외에 별도 표시(예: Depth 진행 표기줄)에 추가로 얹지 않는다 — 같은 정보를 두 번 보여줄 뿐이다.

### 점수 산정 체크리스트 (D1-D6)

| # | 체크 항목 | Y 판정 기준 | 가중치 |
|---|-----------|------------|--------|
| D1 | 기본 질문 완료 | 해당 영역의 base question이 모두 나갔고 답변을 받았다 | 30% |
| D2 | 구체적 답변 확보 | 답변에 숫자·고유명사·구체적 사례가 최소 1개 있다 (일반론만이면 N) | 15% |
| D3 | Why chain 완료 | "왜"를 최소 1회 되물었고 그에 대한 답을 받았다 | 20% |
| D4 | 발견 1건 이상 도출 | 사용자가 인터뷰 전에는 말하지 않았던 항목이 1건 이상 나왔다 (기존 진술 재서술은 N) | 15% |
| D5 | 불확실성 신호 없음 | 마지막 라운드에 §3 불확실성 신호가 없었다 (감지 시 N = 기존 10% 차감과 동일) | 10% |
| D6 | 사용자 자체 인사이트 발현 | 사용자가 질문받지 않은 함의를 스스로 꺼냈다 | 10% |

```
area_score = Σ (weight of items marked Y)     # 0% ~ 100%, 6개 다 Y면 100%
```

판정이 애매하면 **N**으로 둔다 — 과대 채점은 게이트를 조기에 열어 탐색을 끊지만, 과소 채점은 질문 한 라운드만 더 쓰게 할 뿐이다.

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

게이트는 **두 조건을 모두** 만족해야 열린다:

```
gate_open = (Depth ≥ 65%) AND (진입한 모든 Core 영역에서 D4 = Y)
```

- **둘 다 충족**: Phase 2 진입 가능 (사용자 동의 필요)
- **Depth 미달**: 가장 낮은 영역에 추가 질문 권장
- **D4 미충족**: Depth가 65%를 넘었더라도 D4가 N인 영역을 다시 타겟팅한다
- 기존 포화 감지(3연속 신호)는 **보조 지표**로 유지: 게이트가 닫혀 있어도 포화 시 사용자에게 확인 후 진행 가능. Explicit Done도 그대로 사용자 의사를 존중한다 (경고만 표시)
- Quick Discovery 모드는 타겟 영역 1개만 채점하므로, 그 영역에 대해서만 같은 두 조건을 본다

**D4를 별도 전제로 둔 이유**: D1(30) + D2(15) + D3(20) = 정확히 65%다. 가중치 합산만으로 게이트를 걸면 네 영역 전부가 "기본 질문 던지고, 구체적으로 들리는 답을 받고, 왜를 한 번 되물었다"만으로 65%에 도달해서, **발견이 0건인 채로** Phase 2 진입이 제안된다. Unknown Unknown을 찾는 게 목적인 스킬에서 그건 게이트가 아니라 통과 의식이라, D4는 가중치 항목이면서 동시에 하드 전제로 둔다 (build-spec의 dimension floor가 Ambiguity 합산과 별개로 하드 게이트인 것과 같은 구조).

**65% 임계값 근거**: D1+D2+D3에 해당하는 수준 — 기본 질문 완료, 구체적 답변 확보, Why chain 1회 완료 — 이 네 영역에 고르게 깔린 상태다. 여기에 D4 전제가 얹히므로 실제 게이트 통과 지점은 "모든 영역이 심화 탐색을 마쳤고, 각 영역에서 인터뷰 전에 없던 항목이 최소 1건씩 나왔다"가 된다.

### 점수 하락 조건

불확실성 신호 감지 시 **D5를 N으로 표시**한다 (= 기존의 10% 차감과 같은 효과).
체크리스트 합산이라 점수는 구조적으로 0% 미만이 될 수 없으므로 별도 클램핑이 필요 없다.

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

## 12. Extended Areas Procedure

### 진입 조건

- Core 4 영역(Assumptions, Trade-offs, Edge Cases, Blindspots) 모두 최소 1회 탐색 완료
- 사용자에게 확인: "핵심 4개 영역 탐색을 마쳤습니다. 추가 영역도 살펴볼까요?"

### 확장 영역

| 영역 | 초점 | 질문 수 |
|------|------|---------|
| Feasibility | 리소스, 일정, 기술적 제약 | 2-3 |
| Stakeholders | 의사결정자, 영향 받는 당사자, 영향력 행사자 | 2-3 |
| Counterfactual | "아무것도 안 하면?" / "반대를 선택하면?" | 2 |
| Dependencies | 외부 의존성, 블로킹 요소, 크리티컬 패스 | 2-3 |

### 절차

1. 확장 영역 옵션을 사용자에게 제시 (AskUserQuestion, multiSelect)
2. 선택된 각 영역: 2-3개 집중 질문
3. Why chain은 불확실성 신호 감지 시에만 수행
4. 확장 영역 간 체크포인트 불필요
5. 모든 선택 영역 완료 후 → Phase 2 진행

### Skip 조건

- 사용자가 확장 탐색을 거부
- 총 질문 수가 15개를 초과
- 사용자 피로 신호 (연속 짧은 답변)

## 13. Interview Flow Control

### Fatigue Management

- **질문 예산**: Core 4 영역 기준 12-15개 소프트 리밋
- **참여도 점검**: 8개 질문 이후, 응답 품질 추이 평가
- **피로 신호**: 응답 길이 감소, "모르겠어요" 증가
- **대응**: "지금까지 좋은 인사이트들이 나왔습니다. 계속 진행할까요, 아니면 여기서 정리할까요?"

### Recovery Strategies

| 상황 | 대응 |
|------|------|
| 사용자 혼란 | 질문을 단순화하고 구체적 예시 제공 |
| 답변 순환 | 다른 각도에서 재구성 |
| 질문에 반발 | 인정하고 건너뛰기 제안 |

## 14. Anti-Patterns

| Anti-Pattern | 문제점 | 올바른 접근 |
|---|---|---|
| 유도 질문 | 특정 답변으로 편향시킴 | 개방형 질문 사용 |
| Why chain 생략 | 표면적 답변을 수용 | 최소 1회 후속 질문 수행 |
| STATE 체크포인트 누락 | 컴팩션 시 진행 상태 유실 | 매 영역 완료 후 STATE 블록 출력 |
| 복수 질문 동시 제시 | 얕은 답변 유도 | 한 번에 하나씩 질문 |
| 불확실성 신호 무시 | 발견 기회 놓침 | 신호 감지 시 D5를 N으로 + 심화 (§3, §6) |
| 자기 인터뷰 자기 채점 | 자기 점수를 자기가 매겨 게이트가 조기 개방 | Depth 채점은 별도 Agent에서 (§6 격리 채점) |
| repo 무시하고 추상 질문 | 코드에 이미 답이 있는 걸 되물음 | Phase 0에서 repo 인테이크 먼저 (§15) |

---

## 15. Repo Context Intake (Phase 0)

대상이 코드베이스이거나 코드베이스에 대한 기획일 때만 수행한다. 아니면 조용히 건너뛴다.

1. `Glob("{README.md,CLAUDE.md,package.json,pyproject.toml,plugin.json,go.mod,Cargo.toml}")` — 우선순위는 README/CLAUDE.md > 매니페스트.
2. 히트한 파일을 Read하고, 대상 주제의 키워드로 `Grep`해서 실제 구현·제약이 어디에 있는지 확인한다.
3. 읽은 것에서 **인터뷰 질문을 접지**한다 — 추상 질문 대신 반증 가능한 질문으로:

| 접지 안 된 질문 (before) | 접지된 질문 (after) |
|---|---|
| "확장성은 고려하셨나요?" | "README는 단일 프로세스 전제로 쓰여 있는데, 워커를 늘리면 이 상태는 어디에 두나요?" |
| "의존성 리스크가 있을까요?" | "package.json에 X가 고정 버전으로 박혀 있던데, 그게 못 올라가면 이 계획은 어떻게 되나요?" |

**한계**: 인테이크는 Phase 0 1회, 파일 몇 개 수준이다. 전체 코드 감사가 아니고, repo가 없으면 인터뷰는 기존과 동일하게 순수 대화로 진행된다.

---

## 16. Procedure Detail

Step detail moved out of `SKILL.md` to fit Codex's 8,000-byte invoked-skill limit (#750). The text below is the pre-move SKILL.md prose, verbatim except that headings are demoted one level and the STATE template (which stays in `SKILL.md`) is omitted. `SKILL.md` carries the executable contract in compact form (gates, the isolated gate-imminent scoring requirement and its fallback, termination conditions); where the two overlap, this section is the long form. **Binding sections**: `Quick Discovery Mode` (the required Quick Mode output block, which SKILL.md tells you to read before emitting Quick Mode output) and the Phase 3 options; they are not rationale-only. Read the matching subsection when its step is reached: Quick Discovery output block, Phase 0 detail, Core Areas question patterns, Phase 3 options, state persistence and legacy restore, privacy.

### Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match input language
  - Korean input → Korean interview questions and report
  - English input → English interview questions and report
  - Mixed input → follow dominant language

Discover user's Unknown Unknowns (things they don't know they don't know) through deep iterative interviews.

### When to Use

- Finding blind spots in projects or proposals
- Verifying overlooked considerations before decision-making
- Validating implicit assumptions in strategies or plans
- Systematically exploring risks and trade-offs

### Prerequisites

- Analysis target (project/proposal/decision/idea)
- (Optional) Current assumptions or considerations
- Quick Discovery mode: include '빠르게', '간단히', or 'quick' in your request

### Quick Discovery Mode

Compressed interview for time-constrained analysis (5-7 questions total):

1. **Phase 0**: Context Analysis (same, but skip maturity detection — default to Plan)
2. **Phase 1**: Single-pass interview targeting ONE area:
   - Auto-select highest-risk area based on context (default: Assumptions)
   - 3 core questions + 2-4 follow-up questions
   - No Challenge Modes, no Extended Areas
   - Depth scoring for targeted area only
3. **Phase 2**: Quick synthesis (top 3-5 findings only)
4. **Phase 3**: Abbreviated report (no full template, inline summary)

Quick Mode output format:
```
## Quick Discovery — {target}

**Area**: {targeted area} | **Questions**: {count} | **Status**: 충분/진행 중

### Findings
1. [{C|I|N}] {finding}
2. [{C|I|N}] {finding}
...

───
*Quick Discovery 완료 · 전체 분석으로 재실행*
```

### Core Workflow

#### Phase 0: Context Analysis
<!-- Active during Phase 0 only -->

1. Analyze the target (project / document / idea).
2. Confirm the domain (Tech/Biz/Creative/Custom) → confirm with the user via AskUserQuestion.
2a. **Repo Context Intake** (when the target is a codebase / an idea about one): `Glob("{README.md,CLAUDE.md,package.json,pyproject.toml,plugin.json,go.mod,Cargo.toml}")`, then `Grep` the hits for the target's own keywords. Feed what you find into the interview as *grounded* questions ("README says X is the only supported path — what happens when Y?") instead of abstract ones. Detail: [reference.md](reference.md) §15. No hits / not a codebase → skip silently, interview proceeds as a pure conversation.
2b. **Seed Detection** (bridge from `build-spec`): `Glob("docs/specs/*.yaml")`. If the user's target names or matches an existing Seed file (by slug or explicit path), `Read` it and treat that Seed as the interview target — its `goal`/`constraints`/`success_criteria` anchor the interview, and each area's questions probe against fields the Seed already committed to instead of starting from a blank context. Findings from this interview are meant to fold into that Seed's `blindspots[]` later via a `build-spec` refine-mode session (see [../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md)). No match → skip silently, interview proceeds as normal.
3. Detect maturity (Idea/Plan/Execution):
   - **Auto-detect first**: infer maturity from signals in the user's input context (detail: [reference.md](reference.md) §9)
     - No concrete numbers/timeline, "~할 것 같다" hedging → Idea
     - Milestones / resources / schedule mentioned → Plan
     - Progress / issues / metrics mentioned → Execution
   - **Only when unclear**, confirm with the user via AskUserQuestion.
4. Adjust Exploration Depth weights based on maturity.
5. Build the interview plan.

#### Phase 1: Iterative Interview Loop
<!-- Active during Phase 1 only -->

**Dynamic Area Targeting**: each round auto-targets the area with the lowest Exploration Depth (detail: [reference.md](reference.md) §7).

**Round Counter Display**: Each interview round shows explicit progress:
```
[Round N] Area: {current_area}
```
- Round count is approximate (soft limit 12-15, hard limit 20)
- Display updates at every question transition

- First round: always Assumptions (the basis of every finding)
- After: target the lowest-scoring area
- On a tie: Assumptions > Trade-offs > Edge Cases > Blindspots

**Core Areas** (question patterns — the Korean prompts below are user-facing):

| Area | Base question pattern (user-facing) | Q count |
|------|---------------|---------|
| Assumptions | "이것이 성립하려면 어떤 전제가 필요한가요?" | 2-3 |
| Trade-offs | "이 선택으로 포기하게 되는 것은?" | 2-3 |
| Edge Cases | "10배 규모/최악의 시나리오에서 어떻게 되나요?" | 2-3 |
| Blindspots | "아직 질문하지 않은 것 중 중요한 것은?" | 2-3 |

**Interview Rules**:

1. Per area: base question 1 → follow-up 1 → Why chain 1 (3Q total)
2. Checkpoint: on completing each area, output a progress summary + STATE block (including Exploration Depth)
3. On detecting an uncertainty signal, mark that area's checklist item D5 as N (that is the 10% deduction) and add 1Q (detail: [reference.md](reference.md) §3, §6)
4. When the Core 4 clear the Depth Gate (≥ 65% **and** D4 = Y in every entered area — [reference.md](reference.md) §6), ask the user whether to enter Extended areas

**Exploration Depth Scoring** (checklist-based): at each checkpoint, score the just-completed area via the **6-item Y/N checklist** in [reference.md](reference.md) §6 — `area_score = Σ(weight of each Y item)`, never a free 0-100% judgement — and record each item's Y/N plus a one-line reason in the STATE block's `scoring_rationale`. Scoring stays inline by default; only a **gate-imminent round** escalates to isolated re-scoring — same cheap-by-default shape as `build-spec` Phase 2 (`build-spec/reference.md` §2).

**Gate-imminent round**: the checkpoint whose own inline scores already satisfy the Depth Gate (Depth ≥ 65% AND D4=Y in every entered Core area — [reference.md](reference.md) §6) — the same test as the Termination Gate itself, evaluated one step early against inline numbers.

- **Gate-imminent round only**: re-score the same checklist in a **separate Agent subagent** — the interviewer scoring its own interview is the same self-verification bias that isolated Judge removes in `adversarial-review`. Pass the subagent `{each entered Core area's Q&A transcript + the §6 checklist + the findings claimed for each area}`; it returns the 6 Y/N marks, the reasons, and the area score, per area. The same call verifies the "발견 1건 이상 도출" item, so a claimed finding is confirmed by a context that never saw it being produced. It is this recomputed result, not the inline one, that actually opens the gate.
- Every other checkpoint: `scoring_isolated: false` in STATE — inline by design, not a failure.
- **Agent call fails / unavailable / no response at a gate-imminent round (including a policy denial)** → score inline against the same checklist and keep `scoring_isolated: false` in STATE. A subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback (#647) — never wait on it further. Add one line to the checkpoint output before the progress summary:
  `[격리 채점 실패 — 자체 채점, 신뢰도 낮음]`. One line, not a new round, no `AskUserQuestion` — then
  proceed exactly as isolated mode would (#433: a self-scored Depth and an isolated one differ in
  confidence and must not render identically; rationale for skipping the approval prompt: `reference.md` §6).

```
Round N | Area: {current_area} (targeting lowest area) | 진행 중/충분
```

**Challenge Modes**: insert a perspective-shift question at a specific point in the interview (once each, 1-2Q). Detail: [reference.md](reference.md) §8.

| Mode | Entry condition | Purpose |
|------|----------|------|
| Inverter | Round 3+ | Invert a core assumption |
| Outsider | Round 5+ | Gain an outsider's view |
| Pre-mortem | Round 7+ / Depth 60%+ | Back-trace a future failure |

**Extended Areas** (user-selected):
- Feasibility | Stakeholders | Counterfactual | Dependencies

#### Phase 2: Synthesis
<!-- Active during Phase 2 only -->

1. Organize discovered Unknown Unknowns
2. Priority tagging (Critical / Important / Nice-to-have):
   - **Critical**: Could this cause project failure?
   - **Important**: Does this affect timeline/quality/cost?
   - **Nice-to-have**: Is this an optimization/improvement opportunity?
3. Extract key insights

#### Phase 3: Documentation & Bridge
<!-- Active during Phase 3 only -->

1. Discovery Report 생성 (템플릿: [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md)) — YAML frontmatter 블록 선행 작성 후 서사체 본문 작성. frontmatter 누락 시: YAML 블록을 별도 출력하고 "보고서 앞에 붙이세요" 안내.
2. Exploration Depth 요약 포함
3. 권장 액션 아이템 도출
4. 인터뷰 메타데이터 기록
5. **Post-Discovery Options** 제시 (AskUserQuestion):
   - **Expert Panel**: Critical 발견에 대해 다관점 전문가 토론 (`/expert-panel` 연계)
   - **Action Plan**: 발견 기반 구체적 실행 계획 작성
   - **Deep Dive**: 특정 Critical 항목에 대해 새 인터뷰 세션 시작
   - **Export**: 보고서를 `Write`로 파일에 저장
   - **Seed로 넘기기** (대상 Seed가 있을 때만 노출 — Phase 0 Seed Detection §2b 참고): 리포트를 저장하고, 다음 세션에서 그 대상 Seed 경로 + 이 리포트를 `build-spec` refine mode(`"이 스펙 다듬어줘"`)에 넘기는 방법을 안내. 왕복은 같은 세션에서 하지 않는다 — [../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md) 세 경로 참고

### Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Depth Gate** | Exploration Depth ≥ 65% **AND** D4(발견 1건 이상 도출) = Y in every entered Core area | Phase 2 진입 제안 (사용자 동의 필요) |
| **Explicit Done** | "done", "stop", "enough", "완료", "충분해", "끝", "그만" | Depth 경고 표시 후 Phase 2 진행 |
| **Saturation** | 3 consecutive: short response + repetition + avoidance | Depth 표시 + confirm |
| **Depth Limit** | Each Core 4 area at 2-depth | Ask about Extended areas |
| **Gap Check** | End of Phase 1 | "Anything important we haven't covered?" |
| **Early Exit** | User says "skip to results", "요약해줘", "결과만" | Save state → skip to Phase 2 with current findings |

**Depth Gate가 주요 종료 기준**이며, Saturation은 보조 지표로 유지한다.
Explicit Done 시 Depth가 65% 미만이면 경고를 표시하되, 사용자 의사를 존중한다.

**Soft Landing**: Depth 요약 → Confirm → Close (3-step)

### State Management

> **Core Rules**: See [../../reference/state-contract.md](../../reference/state-contract.md)

Numeric Depth/score fields serve compaction restoration and gate logic only; user-facing checkpoints show qualitative progress (충분/진행 중), never the raw Depth percentage.

#### Legacy Format Compatibility

기존 STATE 블록은 점수 없이 상태만 기록했다:
```
Progress: [assumptions:done] [trade-offs:pending]
```
새 포맷은 점수를 포함한다:
```
Progress: [assumptions:done:75%] [trade-offs:pending:0%]
```
컴팩션 복원 시 레거시 포맷을 만나면: 상태(`done/active/pending`)만 복원하고, 점수는 상태 기반으로 추정한다 (`done`→70%, `active`→40%, `pending`→0%).

#### Optional File Persistence

사용자가 인터뷰 상태를 파일로 저장하여 세션 간 재개를 원할 경우:

1. **저장**: Phase 1 체크포인트에서 사용자 요청 시 `docs/discovery/{target}/state.md`에 STATE 블록 저장
2. **재개**: 새 세션에서 저장된 파일을 읽어 인터뷰 복원
3. **트리거**: "저장해줘", "save state", "나중에 이어하자" 등

저장 시 STATE 블록 + 발견 목록 + 메타데이터를 포함한다. 상세: [templates/INTERVIEW_STATE.md](templates/INTERVIEW_STATE.md)

*(The STATE block template stays in SKILL.md § State Management only.)*

Detailed format: [templates/INTERVIEW_STATE.md](templates/INTERVIEW_STATE.md)

### Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Domain selection, each interview question, checkpoints | "Which domain best fits?" |
| Agent | Isolated Depth scoring + finding verification, gate-imminent checkpoint only | Pass area Q&A + §6 checklist, get Y/N marks back |
| Glob / Grep | Phase 0 Repo Context Intake only (§15) | `Glob("{README.md,CLAUDE.md,...}")` → grep for target keywords |
| (None) | Deep thinking, synthesis | Internal processing |

### Output Format

#### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Metadata tables
- Progress/status indicators

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Generated text content itself
- Results that users will directly use

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

#### Report Template

See [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md)

### References

- **Decision criteria guide**: See [reference.md](reference.md)
- **Workflow examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder
- **Role boundary vs build-spec**: [../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md)

### Quick Start

```text
User: "새로운 결제 시스템 도입을 검토해줘. 놓친 게 있는지 봐줘."

→ Phase 0: Domain "Biz" + Maturity "Plan" 확인
→ Phase 1: Assumptions(30%) → Trade-offs 타겟(25%) → [Inverter] → Edge Cases(20%) → ...
   매 체크포인트마다 Depth 표시, 최저 영역 자동 타겟팅
→ Phase 2: 발견된 blind spots 정리, 우선순위 태깅
→ Phase 3: Discovery Report + Exploration Depth 요약 + Next Steps 제안

Output: Depth 72% · Critical/Important/Nice-to-have 분류된 발견 보고서
```

### Privacy Note

This interview may surface sensitive business information (strategy, financials, internal concerns). Claude does not store conversations beyond the session. Save outputs explicitly if needed for future reference.
