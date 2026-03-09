# Unknown Discovery - Examples

Workflow examples demonstrating the full interview process across different domains.

---

## Example 1: Tech Domain - Microservice Architecture Review

### Situation

A team transitioning from monolith to microservices.
"놓치고 있는 게 있는지 검토해줘."

### Phase 0: Context Analysis
```
[Context Analysis]
대상: 모놀리식 → 마이크로서비스 전환 프로젝트
도메인 확인이 필요합니다.

> AskUserQuestion: "이 프로젝트는 어떤 도메인에 해당하나요?"
> Options: Tech / Biz / Creative / Custom
> User: "Tech"

Domain: Tech → Edge Cases, Dependencies에 특히 집중
인터뷰를 시작하겠습니다.
```

### Phase 1: Iterative Interview

```
[Assumptions - Q1]
"마이크로서비스 전환이 성공하려면 어떤 전제가 필요한가요?"
→ "팀이 분산 시스템을 다룰 수 있고, 인프라가 준비되어 있어야 해."

[Assumptions - Q2 (Why Chain)]
"팀이 분산 시스템을 다룰 수 있다고 생각하시는 근거는?"
→ "사실 아직 경험이 많지 않아."
→ *발견: 팀 역량 갭 (Critical)*

[Assumptions - Q3]
"인프라 준비 상태는 구체적으로 어떤가요? CI/CD, 모니터링, 서비스 메시 등."
→ "CI/CD는 있는데 모니터링은 기본적인 것만..."
→ *발견: 운영 인프라 미완성 (Important)*
```

```
<!-- STATE:CHECKPOINT -->
Target: 마이크로서비스 전환 | Domain: Tech | Phase: 1
Progress: [assumptions:done] [trade-offs:pending] [edge-cases:pending] [blindspots:pending]
Q: 3 | CP: 1

Discoveries:
1. [C] 팀 역량 갭 — 분산 시스템 경험 부족
2. [I] 운영 인프라 미완성 — 모니터링 기본 수준
<!-- /STATE -->
```

```
[Trade-offs - Q4]
"마이크로서비스로 얻는 것과 포기하는 것은 각각 뭔가요?"
→ "독립 배포가 가능해지지만... 운영 복잡도가 올라가겠죠."

[Trade-offs - Q5]
"운영 복잡도 증가를 어떻게 관리할 계획인가요?"
→ "아직 구체적인 계획은 없어요."
→ *발견: 운영 복잡도 관리 계획 부재 (Important)*

[Edge Cases - Q6]
"서비스가 10배 트래픽을 받으면 어떻게 되나요?"
→ "각 서비스별로 스케일링하면 되지 않을까?"

[Edge Cases - Q7 (Why Chain)]
"서비스 간 통신도 10배가 되면?"
→ "네트워크 병목이 생길 수 있겠네."
→ *발견: 네트워크 병목 미고려 (Important)*

[Edge Cases - Q8]
"인증 서비스가 다운되면 다른 서비스들은 어떻게 되나요?"
→ "다 못 쓰게 되겠네... 그건 생각 못 했어요."
→ *발견: 인증 서비스 SPOF (Critical)*
```

```
<!-- STATE:CHECKPOINT -->
Target: 마이크로서비스 전환 | Domain: Tech | Phase: 1
Progress: [assumptions:done] [trade-offs:done] [edge-cases:done] [blindspots:pending]
Q: 8 | CP: 2

Discoveries:
1. [C] 팀 역량 갭 — 분산 시스템 경험 부족
2. [I] 운영 인프라 미완성 — 모니터링 기본 수준
3. [I] 운영 복잡도 관리 계획 부재
4. [I] 네트워크 병목 미고려 — 서비스 간 통신 급증 시
5. [C] 인증 서비스 SPOF — 단일 장애 지점
<!-- /STATE -->
```

```
[Blindspots - Q9]
"아직 질문하지 않은 것 중 중요한 것은 뭔가요?"
→ "데이터 일관성... 분산 트랜잭션을 어떻게 처리할지."
→ *발견: 분산 트랜잭션 미고려 (Important)*

[Blindspots - Q10]
"롤백이 필요한 상황에서 각 서비스의 데이터를 어떻게 원복하나요?"
→ "사가 패턴을 쓸 수 있겠지만, 아직 경험이 없어요."
→ *발견: 롤백 전략 미수립 (Nice-to-have)*

[Gap Check]
"혹시 아직 다루지 못한 중요한 부분이 있으신가요?"
→ "충분히 다룬 것 같아요."
```

### Phase 2: Synthesis

```
[Discovery Summary]

**Critical** (즉시 대응 필요):
1. 팀 역량 갭 — 분산 시스템 경험 부족, 교육/채용 필요
2. 인증 서비스 SPOF — 단일 장애 지점, 이중화 필수

**Important** (계획 수정 권장):
3. 운영 인프라 미완성 — 모니터링, 로깅, 알림 체계 구축 필요
4. 운영 복잡도 관리 계획 부재 — 런북, 온콜 체계 수립
5. 네트워크 병목 미고려 — 서비스 메시, 회로 차단기 도입 검토
6. 분산 트랜잭션 미고려 — 사가 패턴 PoC 필요

**Nice-to-have** (개선 기회):
7. 롤백 전략 미수립 — 사가 패턴 경험 축적 후 수립

핵심 인사이트: 기술 준비보다 팀 역량과 운영 준비가 더 큰 리스크.
마이크로서비스 전환 전 팀 교육과 인프라 정비를 우선 권장.
```

### Phase 3: Documentation

```
→ docs/discoveries/20260306_microservice-review/DISCOVERY_REPORT.md 생성
→ 액션 아이템: 팀 교육 프로그램(2주 내), 인증 서비스 이중화 설계(1주 내), 모니터링 체계 구축(3주 내)
```

---

## Example 2: Biz Domain - Market Entry Strategy

### Situation

A startup planning to enter the food delivery market.
"배달 앱 시장 진출을 준비하고 있는데, 놓치고 있는 게 있는지 봐줘."

### Phase 0: Context Analysis

```
[Context Analysis]
대상: 배달 앱 시장 진출 전략
> AskUserQuestion: "이 프로젝트는 어떤 도메인에 해당하나요?"
> User: "Biz"

Domain: Biz → Stakeholders, Trade-offs에 특히 집중
```

### Phase 1: Iterative Interview

```
[Assumptions - Q1]
"이 시장에 진입할 수 있다고 판단하신 근거는 뭔가요?"
→ "기존 앱들이 배달료가 비싸서 저렴한 대안이 먹힐 거라고 봤어요."

[Assumptions - Q2 (Why Chain)]
"저렴한 배달료가 가능한 구조적 이유는 뭔가요?"
→ "음... 처음에는 손해를 보더라도 물량을 확보하면..."
→ *발견: 수익 모델의 지속가능성 미검증 (Critical)*

[Trade-offs - Q3]
"저가 전략으로 포기하게 되는 것은 뭔가요?"
→ "마진이 낮으니까 서비스 품질 투자가 어려울 수 있어요."
→ *발견: 가격-품질 트레이드오프 미검토 (Important)*

[Trade-offs - Q4]
"기존 대형 플랫폼이 가격을 맞추면 어떻게 하시나요?"
→ "그건... 차별화 포인트가 필요하겠네요."
→ *발견: 가격 경쟁 대응 전략 부재 (Critical)*

[Edge Cases - Q5]
"라이더 수급이 갑자기 부족해지면?"
→ "주말이나 우천 시에는 확실히 문제가 될 수 있어요."
→ *발견: 피크 타임 수급 리스크 (Important)*

[Edge Cases - Q6]
"음식 사고(위생, 오배달)가 발생하면 책임 구조는?"
→ "아직 그 부분은 법률 검토를 안 했어요."
→ *발견: 법적 책임 구조 미정립 (Critical)*
```

```
<!-- STATE:CHECKPOINT -->
Target: 배달 앱 시장 진출 | Domain: Biz | Phase: 1
Progress: [assumptions:done] [trade-offs:done] [edge-cases:done] [blindspots:pending]
Q: 6 | CP: 1

Discoveries:
1. [C] 수익 모델 지속가능성 미검증
2. [I] 가격-품질 트레이드오프 미검토
3. [C] 가격 경쟁 대응 전략 부재
4. [I] 피크 타임 수급 리스크
5. [C] 법적 책임 구조 미정립
<!-- /STATE -->
```

```
[Blindspots - Q7]
"기존 플랫폼과 가맹점 간 독점 계약이 있을 수 있나요?"
→ "확인해본 적 없어요."
→ *발견: 가맹점 확보 장벽 미조사 (Important)*

[Blindspots - Q8]
"혹시 다루지 못한 중요한 부분이 있으신가요?"
→ "충분한 것 같아요."

[Saturation detected: consecutive brief responses]
"핵심 영역을 충분히 다룬 것 같습니다. 정리해도 될까요?"
→ "네, 정리해주세요."
```

### Phase 2-3: Output

```
[Discovery Summary]

**Critical**:
1. 수익 모델 지속가능성 미검증 — 손실 보전 기간과 BEP 분석 필요
2. 가격 경쟁 대응 전략 부재 — 가격 외 차별화 포인트 필수
3. 법적 책임 구조 미정립 — 음식 사고 시 플랫폼/가맹점/라이더 책임 분배

**Important**:
4. 가격-품질 트레이드오프 — 저가 전략의 서비스 품질 영향 분석
5. 피크 타임 수급 리스크 — 라이더 인센티브 구조 설계
6. 가맹점 확보 장벽 — 독점 계약 등 진입 장벽 조사

핵심 인사이트: 가격 경쟁력만으로는 지속 가능한 시장 진입이 어려움.
법률 리스크와 수익 모델 검증이 시장 진입 전 필수 선행 과제.
```

---

## Example 3: Termination Scenarios

### Explicit Done

```
[Q9] "이 프로젝트에서 타임라인 리스크는 어떻게 보시나요?"
→ "그만해도 될 것 같아요. 충분히 파악했어요."

[Soft Landing]
"지금까지 발견된 사항을 정리해 드리겠습니다."
→ [Summary output]
"추가로 살펴볼 부분이 있으신가요?"
→ "아니요, 충분합니다."
→ [Close → Phase 2]
```

### Saturation Detection

```
[Q7] "다른 이해관계자 중 고려하지 않은 분이 있나요?"
→ "글쎄요."
[Q8] "외부 파트너나 규제 기관은요?"
→ "별로요."
[Q9] "그 외에 누락된 관계자는?"
→ "딱히 없어요."

[Saturation: 3 consecutive short/avoidance responses]
"이해관계자 영역은 충분히 다룬 것 같습니다. 다음 영역으로 넘어갈까요?"
→ User confirms → transition
```

### Gap Check

```
[After Core 4 complete]
"핵심 4개 영역을 모두 탐색했습니다. 혹시 저희가 다루지 못한 중요한 주제가 있으신가요?"
→ "데이터 마이그레이션 전략을 아직 안 봤네요."

[추가 탐색]
"데이터 마이그레이션에서 가장 걱정되는 부분은?"
→ "레거시 데이터 형식 호환..."
→ *발견: 데이터 마이그레이션 리스크 (Important)*

→ Proceed to Phase 2
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|---|---|---|
| Leading question: "이건 보안 문제가 있지 않나요?" | Biases the user toward a specific answer | Open-ended: "보안 측면에서 어떤 점을 고려하셨나요?" |
| Why chain skip | Accepts surface answer without probing deeper | Always follow up at least once: "그렇게 생각하시는 이유는?" |
| STATE checkpoint missing | No progress tracking, lost on compaction | Must output STATE block after each area completion |
| Multiple questions at once | Overwhelms user, gets shallow answers | One question at a time, wait for response |
| Ignoring uncertainty signals | Misses important discoveries | Monitor for hedging, short responses, avoidance |
