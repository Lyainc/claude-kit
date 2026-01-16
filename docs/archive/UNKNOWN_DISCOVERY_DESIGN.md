# Unknown Discovery Skill 설계 문서

> AskUserQuestion 기반 심층 인터뷰로 Unknown Unknowns를 발견하는 스킬

## 1. 배경 및 목적

### 1.1 문제 정의

"Unknown Unknowns"란 Rumsfeld의 인식론적 분류에서 유래한 개념으로, **모르고 있다는 사실조차 모르는 영역**을 의미합니다.

프로젝트, 기획, 의사결정에서 가장 위험한 것은:

- Known Unknowns (알지만 모르는 것) - 질문할 수 있음
- **Unknown Unknowns (모르는 것조차 모름)** - 질문조차 못함

이 스킬은 체계적인 인터뷰를 통해 사용자가 놓치고 있는 영역을 발견합니다.

### 1.2 핵심 가치

| 가치 | 설명 |
|------|------|
| 완전성 | 의사결정에 필요한 고려사항 누락 방지 |
| 리스크 감소 | 사전에 blind spot 발견으로 실패 확률 감소 |
| 품질 향상 | 다각도 검토를 통한 결과물 고도화 |

## 2. 이론적 기반

### 2.1 참조 연구

| 연구/기술 | 핵심 기여 | 적용 포인트 |
|----------|----------|------------|
| [Socratic Prompting](https://arxiv.org/abs/2303.08769) | 6가지 질문 기법 (Definition, Elenchus, Dialectic, Maieutics, Generalization, Counterfactual) | 질문 taxonomy 설계 |
| [Devil's Advocate](https://arxiv.org/abs/2405.16334) | 사전 성찰(anticipatory reflection)로 45% 효율 향상 | Why 체인 필수화 |
| [U2F Framework](https://arxiv.org/html/2511.03517) | Discovery/Exploration/Integration 3단계 에이전트 | Phase 구조 설계 |
| [LLMREI](https://arxiv.org/html/2507.02564v1) | LLM 기반 요구사항 도출 인터뷰 자동화 | 인터뷰 루프 구조 |
| [Anthropic Interviewer](https://www.anthropic.com/news/anthropic-interviewer) | 1,250명 대규모 적응형 인터뷰 | 체크포인트 패턴 |
| [Lisa Plugin](https://github.com/blencorp/lisa) | Stop Hook 기반 지속 인터뷰 | 종료 조건 설계 |
| [SocraticAI](https://princeton-nlp.github.io/SocraticAI/) | 다중 에이전트 대화로 숨겨진 지식 추출 | 적응형 질문 선택 |

### 2.2 전문가 토론 결과 반영

2025-01-15 전문가 패널 토론 (Prompt Engineering / UX-Cognitive / Requirements Engineering) 합의사항:

| 토픽 | 합의 내용 |
|------|----------|
| 질문 생성 | Core 4 + Extended 4 계층화, 적응형 선택, Why 체인 필수 |
| 루프 구조 | 프롬프트 지속 + 체크포인트, 진행률 표시, 다양한 탈출 키워드 |
| 종료 조건 | 포화 휴리스틱 3종, Soft Landing, 갭 체크리스트 |
| 도메인 적응 | LLM 추론 + 사용자 확인, 3종 프리셋 + Custom |
| 출력물 | 3단 구조 + 우선순위 태그, 즉시 활용 가능한 액션 중심 |

## 3. 아키텍처

### 3.1 Phase 구조

```text
Phase 0: Context Analysis
    ├─ 대상 분석 (프로젝트/문서/아이디어)
    ├─ 도메인 추론 → AskUserQuestion으로 확인
    ├─ 질문 영역 프리셋 선택
    └─ 인터뷰 계획 수립

Phase 1: Iterative Interview Loop
    ┌─────────────────────────────────────────┐
    │  1. Core 4 영역 순회                     │
    │  2. 각 질문 후 Why 체인 (1회 필수)       │
    │  3. 적응형 선택 (불확실성 신호 감지)     │
    │  4. 체크포인트 (4개 질문마다)            │
    │  5. Extended 4 영역 (필요 시)            │
    └─────────────────────────────────────────┘

Phase 2: Synthesis
    ├─ 발견된 Unknown Unknowns 정리
    ├─ 우선순위 태깅
    └─ 핵심 인사이트 추출

Phase 3: Documentation
    ├─ Discovery Report 생성
    ├─ 권장 액션 아이템 도출
    └─ 인터뷰 메타데이터 기록
```

### 3.2 질문 Taxonomy

#### Core 4 (필수)

| 카테고리 | 목적 | 질문 패턴 | Why 체인 |
|----------|------|----------|----------|
| **Assumptions** | 암묵적 전제 발굴 | "이것이 성립하려면 어떤 전제가 필요한가?" | "왜 그 전제가 맞다고 생각하시나요?" |
| **Trade-offs** | 희생 가치 탐색 | "이 선택으로 포기하게 되는 것은?" | "왜 그 희생이 감수할 만하다고 보시나요?" |
| **Edge Cases** | 극단 상황 탐색 | "10배 규모가 되면 어떤 문제가 생기나?" | "왜 그 상황이 발생할 수 있다고 생각하시나요?" |
| **Blindspots** | 메타 인지 | "아직 질문하지 않은 것 중 중요한 것은?" | "왜 그것이 중요하다고 느끼시나요?" |

#### Extended 4 (선택)

| 카테고리 | 목적 | 질문 패턴 |
|----------|------|----------|
| **Feasibility** | 실현 가능성 검증 | "가장 큰 기술적/자원적 장벽은?" |
| **Stakeholders** | 이해관계자 관점 | "이 결정에 반대할 사람은 누구인가?" |
| **Counterfactual** | 대안 탐색 | "완전히 다른 접근법이 있다면?" |
| **Dependencies** | 숨겨진 의존성 | "이것이 실패하면 어디가 영향받나?" |

### 3.3 도메인 프리셋

| 프리셋 | 우선 영역 | 특화 질문 |
|--------|----------|----------|
| **Tech** | Edge Cases, Dependencies | 성능, 확장성, 보안, 기술 부채 |
| **Biz** | Stakeholders, Trade-offs | ROI, 시장, 경쟁, 법적 리스크 |
| **Creative** | Assumptions, Counterfactual | 독창성, 수용성, 트렌드 |
| **Custom** | 사용자 지정 | 사용자 정의 영역 |

### 3.4 종료 조건

| 조건 | 감지 방법 | 액션 |
|------|----------|------|
| **명시적 완료** | "done", "완료", "충분해" 키워드 | 즉시 Phase 2로 전환 |
| **포화 상태** | 짧은 응답 + 반복 표현 + 회피 표현 3회 연속 | "핵심 영역을 다뤘습니다" + 계속 여부 확인 |
| **깊이 한계** | Core 4 영역 각 2-depth 완료 | Extended 영역 진행 여부 확인 |
| **갭 체크** | Phase 1 종료 시 | "아직 다루지 않은 중요한 것?" 최종 질문 |

**Soft Landing 프로세스**: 요약 → 확인 → 종료 (3단계)

### 3.5 상태 추적

```json
{
  "target": "분석 대상명",
  "domain": "tech|biz|creative|custom",
  "current_phase": 0,
  "interview": {
    "questions_asked": 0,
    "current_area": "assumptions",
    "areas_completed": [],
    "checkpoint_count": 0
  },
  "discoveries": [
    {
      "id": 1,
      "area": "assumptions",
      "finding": "발견 내용",
      "priority": "critical|important|nice-to-have",
      "why_chain": "후속 질문 응답"
    }
  ],
  "saturation_signals": {
    "short_responses": 0,
    "repetition": 0,
    "avoidance": 0
  },
  "status": "in_progress|saturated|completed"
}
```

### 3.6 적응형 질문 선택

**불확실성 신호 감지 시 해당 영역 심화**:

| 신호 유형 | 감지 패턴 | 액션 |
|----------|----------|------|
| Hedging | "아마", "글쎄", "잘 모르겠지만" | 해당 영역 후속 질문 |
| 회피 | "나중에", "별로 중요하지 않아" | Why 체인 강화 |
| 짧은 응답 | < 20자 응답 | 구체화 요청 |

## 4. 출력물 구조

### 4.1 Discovery Report

```markdown
# Unknown Unknowns Discovery Report

**대상**: [분석 대상]
**일시**: YYYY-MM-DD
**도메인**: [Tech/Biz/Creative]

---

## 1. 발견된 Unknown Unknowns

### Critical

- [ ] [발견 1]: [설명] → **권장 액션**: [액션]

### Important

- [ ] [발견 2]: [설명] → **권장 액션**: [액션]

### Nice-to-have

- [ ] [발견 3]: [설명]

## 2. 핵심 인사이트

1. [인사이트 1]
2. [인사이트 2]

## 3. 권장 후속 조치

| # | 조치 | 우선순위 | 담당 |
|---|------|---------|------|
| 1 | | | |

---

<details>
<summary>Interview Metadata</summary>

- 질문 수: N
- 완료 영역: [areas]
- 포화 도달: Yes/No
- 소요 체크포인트: N

</details>
```

## 5. 사용 시나리오

### 5.1 Tech 도메인 예시

```text
User: "새로운 마이크로서비스 아키텍처를 검토해줘"

→ Phase 0: Tech 프리셋 선택
→ Phase 1:
   - Assumptions: "서비스 간 통신이 항상 성공한다고 가정하나요?"
   - Edge Cases: "트래픽이 10배 증가하면?"
   - Dependencies: "인증 서비스가 다운되면?"
→ Phase 2: 발견된 blind spots 정리
→ Phase 3: Discovery Report 생성
```

### 5.2 Biz 도메인 예시

```text
User: "신규 구독 모델 도입을 검토해줘"

→ Phase 0: Biz 프리셋 선택
→ Phase 1:
   - Assumptions: "기존 고객이 구독으로 전환할 것이라고 가정하나요?"
   - Stakeholders: "이 변경에 반대할 이해관계자는?"
   - Trade-offs: "일회성 구매 고객을 잃을 위험은?"
→ Phase 2: 발견된 blind spots 정리
→ Phase 3: Discovery Report 생성
```

## 6. 참고 자료

### 학술 논문

- [Prompting LLMs with the Socratic Method](https://arxiv.org/abs/2303.08769) - Chang (2023)
- [Devil's Advocate: Anticipatory Reflection](https://arxiv.org/abs/2405.16334) - Wang et al. (2024)
- [LLM-Powered Devil's Advocate for Group Decision](https://dl.acm.org/doi/10.1145/3640543.3645199) - IUI 2024

### 실무 구현체

- [Lisa Plugin](https://github.com/blencorp/lisa) - Claude Code 인터뷰 워크플로우
- [Anthropic Interviewer](https://www.anthropic.com/news/anthropic-interviewer) - 대규모 정성 연구
- [SocraticAI](https://princeton-nlp.github.io/SocraticAI/) - Princeton NLP
