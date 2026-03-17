# Unknown Discovery - Examples

Tech 도메인 예시를 통한 전체 워크플로우 데모.

## Example 1: Tech Domain - 마이크로서비스 아키텍처 검토

### 상황

모놀리식에서 마이크로서비스로 전환하려는 팀.
"놓치고 있는 게 있는지 검토해줘."

### Phase 0: Context Analysis

도메인 확인 → Tech 선택.
성숙도 확인 → Plan (구체적 마일스톤 존재).
가중치 조정: Trade-offs 0.30↑, Edge Cases 0.25.

### Phase 1: Iterative Interview (발췌)

**Round 1 | [Assumptions:0%] ← 첫 라운드 | Depth: 0%**

**[Assumptions - Q1]** "마이크로서비스 전환이 성공하려면 어떤 전제가 필요한가요?"
→ "팀이 분산 시스템을 다룰 수 있고, 인프라가 준비되어 있어야 해."

**[Why Chain - Q2]** "팀이 분산 시스템을 다룰 수 있다고 생각하시는 근거는?"
→ "사실 아직 경험이 많지 않아." → *발견: 팀 역량 갭 (Critical)*

**Checkpoint 1:**
```
Progress: [assumptions:active:45%] [trade-offs:pending:0%] [edge-cases:pending:0%] [blindspots:pending:0%]
Depth: 14%
```

**Round 3 | [Trade-offs:0%] ← 최저 영역 타겟팅 | Depth: 14%**

**[Trade-offs - Q3]** "마이크로서비스 전환으로 포기하게 되는 것은?"
→ "단순함? 모놀리스에서는 디버깅이 쉬운데..."

**[Inverter - Q4]** "지금까지의 흐름에서 잠시 관점을 바꿔보겠습니다. 만약 '마이크로서비스가 더 복잡하다'는 전제가 틀렸다면? 즉, 모놀리스가 오히려 더 복잡해지는 시점이 있다면?"
→ "팀이 20명 넘어가면 모놀리스 배포 충돌이 심해지긴 해." → *발견: 팀 규모와 아키텍처 결정의 상관관계 재검토 필요 (Important)*

**Round 5 | [Edge Cases:0%] ← 최저 영역 타겟팅 | Depth: 38%**

**[Edge Cases - Q5]** "서비스가 10배 트래픽을 받으면?"
→ "각 서비스별로 스케일링하면 되지 않을까?"
**[Why Chain - Q6]** "서비스 간 통신도 10배가 되면?"
→ "네트워크 병목이 생길 수 있겠네." → *발견: 통신 병목 미고려 (Important)*

**Checkpoint 2:**
```
Progress: [assumptions:done:75%] [trade-offs:active:55%] [edge-cases:active:50%] [blindspots:pending:0%]
Depth: 50%
Challenges: [inverter:done] [outsider:pending] [pre-mortem:pending]
```

**Round 7 | [Blindspots:0%] ← 최저 영역 타겟팅 | Depth: 50%**

**[Outsider - Q7]** "이 프로젝트를 처음 듣는 신입사원이 가장 먼저 던질 질문은?"
→ "왜 지금 해야 하는지? 비즈니스적 긴급성이 있는지?" → *발견: 전환 시점의 비즈니스 정당성 부재 (Important)*

**[Blindspots - Q8]** "아직 질문하지 않은 것 중 중요한 것은?"
→ "데이터 일관성... 분산 트랜잭션" → *발견: 분산 트랜잭션 미고려 (Important)*

**[Pre-mortem - Q9]** "1년 후 이 마이크로서비스 전환이 실패했다면, 가장 큰 원인은?"
→ "팀이 운영 복잡도를 감당 못 해서 결국 다시 합치는..." → *발견: 운영 복잡도 역전 리스크 (Critical)*

**Checkpoint 3:**
```
Progress: [assumptions:done:80%] [trade-offs:done:70%] [edge-cases:done:65%] [blindspots:active:55%]
Depth: 69%
Challenges: [inverter:done] [outsider:done] [pre-mortem:done]
```

**Depth ≥ 65% → Phase 2 진입 제안**

### Phase 2-3: Output (구조)

**Critical**: 팀 역량 갭, 인증 서비스 SPOF, 운영 복잡도 역전 리스크
**Important**: 통신 병목, 분산 트랜잭션, 전환 시점 비즈니스 정당성, 팀 규모-아키텍처 상관관계
**Nice-to-have**: 롤백 전략

핵심 인사이트: 기술 준비보다 팀 역량/운영 준비가 더 큰 리스크.

**Exploration Depth**: 69% (Assumptions 80%, Trade-offs 70%, Edge Cases 65%, Blindspots 55%)

**Post-Discovery**: 사용자가 "Expert Panel" 선택 → Critical 발견 3건에 대해 `/expert-panel`로 다관점 토론 진행.

---

## Example 2: Dynamic Targeting 동작 흐름

다음은 Dynamic Area Targeting이 점수 변화에 따라 영역을 전환하는 흐름:

```
Round 1: [Assumptions:0%] ← 첫 라운드 고정    | Depth: 0%
Round 2: [Assumptions:40%] → Why chain         | Depth: 12%
Round 3: [Trade-offs:0%] ← 최저 영역 전환      | Depth: 12%
Round 4: [Trade-offs:35%] + [Inverter] 발동    | Depth: 21%
Round 5: [Edge Cases:0%] ← Blindspots와 동점, 우선순위상 Edge Cases | Depth: 21%
Round 6: [Blindspots:0%] ← 최저 영역 전환      | Depth: 33%
  (불확실성 신호 → Blindspots 점수 25%-10%→15%; Depth 일시 감소는 페널티 반영)
Round 7: [Blindspots:15%] ← 차감 후 최저       | Depth: 30%
Round 8: [Edge Cases:30%] + [Pre-mortem] 발동  | Depth: 45%
...
```

---

## Example 3: Biz Domain - 배달 앱 시장 진출

### 상황

스타트업이 배달 앱 시장 진출을 검토 중.
"이 사업 계획에서 놓치고 있는 게 뭔지 검토해줘."

### Phase 0: Context Analysis

도메인 확인 → Biz 선택.
성숙도 감지 → Plan (사업계획서, 투자 유치 일정 존재).
가중치 조정: Trade-offs 0.30↑, Assumptions 0.30.

### Phase 1: Iterative Interview (발췌)

**Round 1 | [Assumptions:0%] ← 첫 라운드 | Depth: 0%**

**[Assumptions - Q1]** "배달 앱이 성공하려면 어떤 전제가 필요한가요?"
→ "충분한 가맹점과 배달 라이더 확보가 핵심이에요."

**[Why Chain - Q2]** "가맹점과 라이더를 동시에 확보할 수 있다는 근거는?"
→ "사실 닭과 달걀 문제가 있긴 해요." → *발견: 양면시장 콜드스타트 미해결 (Critical)*

**Checkpoint 1:**
```
Progress: [assumptions:active:50%] [trade-offs:pending:0%] [edge-cases:pending:0%] [blindspots:pending:0%]
Depth: 15%
```

**Round 3 | [Trade-offs:0%] ← 최저 영역 타겟팅 | Depth: 15%**

**[Trade-offs - Q3]** "기존 배달 플랫폼 대비 차별화 전략의 대가는?"
→ "수수료를 낮추려면 초기 적자가 불가피해요."

**[Inverter - Q4]** "만약 '낮은 수수료가 가맹점을 끌어온다'는 전제가 틀렸다면?"
→ "배달 품질이나 주문량이 더 중요할 수도..." → *발견: 가격 외 경쟁 요소 미검토 (Important)*

**Round 5 | [Edge Cases:0%] ← Blindspots와 동점, 우선순위상 Edge Cases | Depth: 28%**

**[Edge Cases - Q5]** "주문량이 피크타임에 10배 집중되면?"
→ "라이더 수급이 안 될 수 있어요."
**[Why Chain - Q6]** "라이더 이탈이 발생하면 서비스 품질에 어떤 영향이?"
→ "배달 지연 → 고객 이탈 → 가맹점 이탈 악순환..." → *발견: 피크타임 라이더 수급 리스크 (Critical)*

**Checkpoint 2:**
```
Progress: [assumptions:done:70%] [trade-offs:active:55%] [edge-cases:active:45%] [blindspots:pending:0%]
Depth: 48%
Challenges: [inverter:done] [outsider:pending] [pre-mortem:pending]
```

**Round 7 | [Blindspots:0%] ← 최저 영역 타겟팅 | Depth: 48%**

**[Outsider - Q7]** "배달 업계를 전혀 모르는 사람이 이 사업 계획을 보면 가장 이상한 점은?"
→ "왜 이미 대형 플랫폼이 있는데 또 만드는지?" → *발견: 후발주자 진입 근거 부족 (Important)*

**[Blindspots - Q8]** "아직 다루지 않은 것 중 가장 중요한 것은?"
→ "노동법... 라이더 고용 형태 문제" → *발견: 라이더 고용 형태 법적 리스크 (Critical)*

**[Pre-mortem - Q9]** "2년 후 이 배달 앱이 실패했다면, 가장 큰 원인은?"
→ "자금 소진... 흑자 전환 전에 투자금이 바닥나서" → *발견: 번레이트 대비 흑자 전환 시점 미산정 (Critical)*

**Checkpoint 3:**
```
Progress: [assumptions:done:75%] [trade-offs:done:65%] [edge-cases:done:60%] [blindspots:active:50%]
Depth: 65%
Challenges: [inverter:done] [outsider:done] [pre-mortem:done]
```

**Depth ≥ 65% → Phase 2 진입 제안**

### Phase 2-3: Output (구조)

**Critical**: 양면시장 콜드스타트, 피크타임 라이더 수급, 라이더 고용 법적 리스크, 번레이트 대비 흑자 전환 시점
**Important**: 가격 외 경쟁 요소, 후발주자 진입 근거
**Nice-to-have**: 지역별 단계적 확장 전략

핵심 인사이트: 기술/서비스보다 양면시장 구조와 규제 리스크가 더 큰 사업 실패 요인.

**Exploration Depth**: 65% (Assumptions 75%, Trade-offs 65%, Edge Cases 60%, Blindspots 50%)

**Post-Discovery**: 사용자가 "Expert Panel" 선택 → Critical 발견 4건에 대해 `/expert-panel`로 다관점 토론 진행.

---

## Domain-specific Discovery Patterns

| 도메인 | 주요 발견 패턴 |
|--------|---------------|
| **Tech** | 가정 검증 부족, 운영 고려 미흡, 장애 시나리오 |
| **Biz** | 이해관계자 누락, 재무 영향, 고객 반응 미검증 |
| **Creative** | 수용성 미검증, 변화 관리, 기존 자산 활용 |

## 성숙도별 인터뷰 특성

| 성숙도 | 질문 톤 | 주요 발견 영역 |
|--------|--------|---------------|
| **Idea** | 탐색적 ("어떤 가능성이?") | Assumptions 위주 |
| **Plan** | 검증적 ("이 선택의 대가는?") | Trade-offs + Edge Cases |
| **Execution** | 진단적 ("지금 어디서 막히나?") | Edge Cases + Blindspots |
