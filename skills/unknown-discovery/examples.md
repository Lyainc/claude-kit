# Unknown Discovery - Examples

세 가지 도메인별 실제 사용 예시.

## Example 1: Tech Domain - 마이크로서비스 아키텍처 검토

### 상황

```text
User: "우리 팀이 모놀리식에서 마이크로서비스로 전환하려고 해.
      놓치고 있는 게 있는지 검토해줘."
```

### Phase 0: Context Analysis

```text
Claude: 마이크로서비스 전환 계획을 검토하겠습니다.

[AskUserQuestion]
질문: "이 프로젝트의 도메인을 확인해주세요."
→ User: "Tech"

Claude: Tech 도메인으로 진행합니다. Edge Cases와 Dependencies에 특히 집중하겠습니다.
```

### Phase 1: Iterative Interview

```text
[Assumptions - Q1]
Claude: "마이크로서비스 전환이 성공하려면 어떤 전제가 필요한가요?"

User: "팀이 분산 시스템을 다룰 수 있고, 인프라가 준비되어 있어야 해."

[Why Chain - Q2]
Claude: "팀이 분산 시스템을 다룰 수 있다고 생각하시는 근거는요?"

User: "음... 사실 아직 경험이 많지 않아. 학습하면서 진행하려고."

→ [발견] 팀 역량 관련 위험 가정 식별

[Assumptions - Q3]
Claude: "인프라가 준비되어 있다는 것은 구체적으로 무엇을 의미하나요?"

User: "쿠버네티스 클러스터가 있고, CI/CD 파이프라인도 구축되어 있어."

[Why Chain - Q4]
Claude: "현재 인프라가 마이크로서비스 운영에 충분하다고 보시나요?"

User: "글쎄... 모니터링이나 로깅은 아직 고민 중이야."

→ [발견] 운영 인프라 미완성

[Checkpoint at Q4]
Claude: "[영역 1/4 | 질문 4]
지금까지 발견:
- 팀 분산 시스템 경험 부족 (Critical)
- 모니터링/로깅 인프라 미정 (Important)

계속할까요?"
→ User: "계속"

[Edge Cases - Q5]
Claude: "서비스가 10배 트래픽을 받으면 어떤 문제가 생길까요?"

User: "각 서비스별로 스케일링하면 되지 않을까?"

[Why Chain - Q6]
Claude: "서비스 간 통신도 10배가 되면 어떻게 되나요?"

User: "아... 네트워크 병목이 생길 수 있겠네. 그건 생각 못했어."

→ [발견] 서비스 간 통신 병목 미고려

[Dependencies - Q7]
Claude: "인증 서비스가 다운되면 다른 서비스들은 어떻게 되나요?"

User: "모든 서비스가 인증 서비스를 호출하니까... 전체가 멈추겠네."

→ [발견] 단일 장애점(SPOF) 존재

[Checkpoint at Q8]
Claude: "[영역 3/4 | 질문 8]
지금까지 발견:
- 팀 역량 갭 (Critical)
- 운영 인프라 (Important)
- 네트워크 병목 (Important)
- 인증 서비스 SPOF (Critical)

다음으로 Blindspots 영역을 탐색하겠습니다. 계속할까요?"
→ User: "네"

[Blindspots - Q9]
Claude: "아직 제가 질문하지 않은 것 중 중요한 것이 있을까요?"

User: "데이터 일관성? 트랜잭션이 여러 서비스에 걸쳐 있으면 어떻게 하지..."

→ [발견] 분산 트랜잭션 미고려

[Gap Check - Q10]
Claude: "마지막으로, 이 전환에서 가장 걱정되는 부분은요?"

User: "롤백. 문제가 생기면 모놀리식으로 돌아갈 수 있을지..."

→ [발견] 롤백 전략 부재
```

### Phase 2: Synthesis

```text
Claude: 인터뷰 결과를 정리합니다.

발견된 Unknown Unknowns:

Critical:
1. 팀 분산 시스템 경험 부족 - 학습 곡선으로 인한 지연/품질 위험
2. 인증 서비스 단일 장애점 - 전체 시스템 다운 가능성

Important:
3. 모니터링/로깅 인프라 미정 - 운영 중 문제 감지 어려움
4. 서비스 간 통신 병목 - 스케일링 시 성능 저하
5. 분산 트랜잭션 처리 방안 미정 - 데이터 일관성 문제

Nice-to-have:
6. 롤백 전략 - 실패 시 복구 계획
```

### Phase 3: Output

```markdown
# Unknown Unknowns Discovery Report

**대상**: 마이크로서비스 전환 프로젝트
**일시**: 2025-01-15
**도메인**: Tech

---

## 1. 발견된 Unknown Unknowns

### Critical

- [ ] **팀 역량 갭**: 분산 시스템 경험 부족으로 학습 곡선 발생
  → **액션**: 전환 전 팀 교육 또는 외부 전문가 컨설팅 검토

- [ ] **인증 서비스 SPOF**: 모든 서비스가 의존하여 단일 장애점 형성
  → **액션**: Circuit breaker 패턴 또는 토큰 캐싱 방안 설계

### Important

- [ ] **운영 인프라 미완성**: 모니터링/로깅 체계 부재
  → **액션**: 전환 전 관측성(Observability) 스택 구축

- [ ] **네트워크 병목**: 서비스 간 통신 증가로 인한 성능 저하 가능성
  → **액션**: 비동기 통신, 이벤트 기반 아키텍처 검토

- [ ] **분산 트랜잭션**: 여러 서비스 걸친 트랜잭션 처리 방안 미정
  → **액션**: Saga 패턴 또는 이벤트 소싱 적용 검토

### Nice-to-have

- [ ] **롤백 전략**: 전환 실패 시 복구 계획 부재
  → **액션**: Strangler Fig 패턴으로 점진적 전환 고려

## 2. 핵심 인사이트

1. 기술적 준비보다 **팀 역량과 운영 준비**가 더 큰 리스크
2. **분산 시스템 특유의 복잡성**(SPOF, 트랜잭션, 통신)에 대한 고려 부족

## 3. 권장 후속 조치

| # | 조치 | 우선순위 | 기한 제안 |
|---|------|---------|----------|
| 1 | 팀 분산 시스템 교육 | Critical | 전환 시작 전 |
| 2 | 관측성 스택 구축 | Critical | 전환 시작 전 |
| 3 | Circuit breaker 설계 | High | 1차 서비스 분리 전 |
| 4 | Saga 패턴 PoC | Medium | 데이터 관련 서비스 분리 전 |

───
*10개 질문 · 4개 영역 완료 · 6개 Unknown Unknowns 발견*

<details>
<summary>상세 메타데이터</summary>

- 질문 수: 10
- 완료 영역: Assumptions, Edge Cases, Dependencies, Blindspots
- 포화 도달: No
- 체크포인트: 2회

</details>
```

---

## Example 2: Biz Domain - 구독 모델 도입 검토

### 상황

```text
User: "우리 SaaS 제품에 구독 모델을 도입하려고 해.
      현재는 일회성 라이선스 판매야. 빠진 게 있을까?"
```

### Phase 0: Context Analysis

```text
[AskUserQuestion]
질문: "도메인을 확인해주세요."
→ User: "Biz"

Claude: Biz 도메인으로 진행합니다. Stakeholders와 Trade-offs에 집중하겠습니다.
```

### Phase 1: Interview (핵심 발췌)

```text
[Assumptions - Q1]
Claude: "구독 모델이 성공하려면 어떤 전제가 필요한가요?"

User: "기존 고객들이 구독으로 전환할 거라고 봐."

[Why Chain - Q2]
Claude: "기존 고객이 전환할 것이라는 근거는요?"

User: "음... 솔직히 확인은 안 해봤어. 제품에 만족하니까 당연히 그럴 줄 알았는데."

→ [발견] 고객 전환 의향 미검증

[Stakeholders - Q5]
Claude: "이 결정에 반대할 수 있는 이해관계자는요?"

User: "영업팀이 반대할 수도 있겠다. 일회성 큰 계약 수수료가 없어지니까."

→ [발견] 영업팀 인센티브 구조 충돌

[Trade-offs - Q7]
Claude: "구독 모델로 전환하면 포기하게 되는 것은요?"

User: "초기 캐시플로우가 줄어들겠지. 그리고... 일회성 구매 선호하는 고객을 잃을 수도."

→ [발견] 캐시플로우 영향, 고객 세그먼트 이탈

[Blindspots - Q9]
Claude: "아직 논의하지 않았지만 걱정되는 부분이 있나요?"

User: "가격 책정... 월 얼마로 해야 할지 감이 안 와.
      그리고 해지율(churn)을 어떻게 관리할지도."

→ [발견] 가격 전략 미정, 해지율 관리 방안 부재
```

### Phase 2-3: Output (요약)

```markdown
# Unknown Unknowns Discovery Report

**대상**: SaaS 구독 모델 전환
**도메인**: Biz

## 1. 발견된 Unknown Unknowns

### Critical

- [ ] **고객 전환 의향 미검증**: 기존 고객의 구독 선호도 확인 안 됨
  → **액션**: 주요 고객 5-10개사 인터뷰 진행

- [ ] **가격 전략 부재**: 월간/연간 가격 책정 기준 없음
  → **액션**: 경쟁사 벤치마킹 + 고객 지불 의향 조사

### Important

- [ ] **영업 인센티브 충돌**: 영업팀 보상 구조 재설계 필요
  → **액션**: 구독 기반 인센티브 모델 설계

- [ ] **캐시플로우 영향**: 초기 매출 감소 예상
  → **액션**: 재무 시뮬레이션 및 브릿지 플랜 수립

- [ ] **해지율 관리**: Churn 모니터링/대응 체계 없음
  → **액션**: 고객 성공팀 구성 또는 역할 정의
```

---

## Example 3: Creative Domain - 브랜드 리뉴얼 검토

### 상황

```text
User: "10년 된 우리 브랜드를 리뉴얼하려고 해.
      로고, 컬러, 메시지 전체를 바꿀 생각이야."
```

### Phase 0: Context Analysis

```text
[AskUserQuestion]
→ User: "Creative"

Claude: Creative 도메인으로 진행합니다. Assumptions와 Counterfactual에 집중하겠습니다.
```

### Phase 1: Interview (핵심 발췌)

```text
[Assumptions - Q1]
Claude: "브랜드 리뉴얼이 성공하려면 어떤 전제가 필요한가요?"

User: "새 브랜드가 기존 고객에게도 받아들여지고, 새 고객도 끌어들여야지."

[Why Chain - Q2]
Claude: "기존 고객이 새 브랜드를 받아들일 것이라는 근거는요?"

User: "음... 그냥 더 현대적이니까? 사실 물어본 적은 없어."

→ [발견] 기존 고객 반응 미검증

[Counterfactual - Q5]
Claude: "완전한 리뉴얼 대신 다른 접근법이 있다면요?"

User: "부분 리뉴얼? 로고만 바꾸거나... 근데 그러면 일관성이 없을 것 같아서."

→ [발견] 점진적 전환 옵션 미고려

[Trade-offs - Q7]
Claude: "10년 된 브랜드를 바꾸면 잃게 되는 것은요?"

User: "브랜드 인지도... 오랫동안 쌓아온 건데.
      그리고 기존 마케팅 자산들도 다 새로 만들어야 하고."

→ [발견] 기존 자산 활용 방안 미고려

[Blindspots - Q9]
Claude: "아직 고려하지 않았지만 중요할 수 있는 것은요?"

User: "경쟁사들 반응? 그리고 내부 직원들...
      오래된 직원들은 기존 브랜드에 애착이 있을 텐데."

→ [발견] 내부 변화 관리, 경쟁 대응
```

### Phase 2-3: Output (요약)

```markdown
# Unknown Unknowns Discovery Report

**대상**: 브랜드 리뉴얼 프로젝트
**도메인**: Creative

## 1. 발견된 Unknown Unknowns

### Critical

- [ ] **기존 고객 반응 미검증**: 충성 고객의 리뉴얼 수용도 확인 안 됨
  → **액션**: 핵심 고객 그룹 FGI(Focus Group Interview) 진행

### Important

- [ ] **점진적 전환 미고려**: All-or-nothing 접근의 리스크
  → **액션**: 단계별 롤아웃 시나리오 검토

- [ ] **기존 자산 활용**: 마케팅 자산 재작업 비용/시간 미산정
  → **액션**: 자산 인벤토리 및 전환 비용 산출

- [ ] **내부 변화 관리**: 직원 브랜드 애착도 고려 안 됨
  → **액션**: 내부 브랜드 앰배서더 프로그램 검토

### Nice-to-have

- [ ] **경쟁 대응**: 리뉴얼 시점의 경쟁사 반응 예측
  → **액션**: 경쟁사 모니터링 계획 수립
```

---

## 공통 패턴 요약

| 단계 | 핵심 액션 |
|------|----------|
| Phase 0 | 도메인 확인, 맥락 파악 |
| Phase 1 | Core 4 순회 + Why 체인 + 체크포인트 |
| Phase 2 | 우선순위 태깅 + 인사이트 추출 |
| Phase 3 | 액션 중심 리포트 생성 |

| 도메인 | 주요 발견 패턴 |
|--------|---------------|
| **Tech** | 가정 검증 부족, 운영 고려 미흡, 장애 시나리오 |
| **Biz** | 이해관계자 누락, 재무 영향, 고객 반응 미검증 |
| **Creative** | 수용성 미검증, 변화 관리, 기존 자산 활용 |
