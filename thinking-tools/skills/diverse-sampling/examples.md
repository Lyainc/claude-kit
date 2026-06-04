# Diverse Sampling - Examples

## Table of Contents

- [Explicit Invocation](#explicit-invocation)
- [Implicit Invocation with Confirmation](#implicit-invocation-with-confirmation)
- [Using --all Option](#using---all-option)
- [Using --best Option](#using---best-option)
- [Fallback Scenario](#fallback-scenario)
- [Use Case Examples](#use-case-examples)
- [Mode B — Enhance (Authoring Diversity)](#mode-b--enhance-authoring-diversity)

---

## Explicit Invocation

### Example 1: Korean Explicit Trigger

**User**:
```
/diverse-sampling 카페 이름 아이디어 좀 줘
```

**Assistant** (internal process):
```
Phase 0:
- Trigger: Explicit (/diverse-sampling)
- Language: Korean detected
- Use case: Creative naming → valid

Phase 1:
- Apply Korean VS template
- Generate 5 responses with probabilities

Phase 2:
- Selection: Weighted random
- Selected: Response #3 (probability 0.06)
```

**Output**:
```
**브루잉 포레스트 (Brewing Forest)**

커피가 숲처럼 천천히 우러나는 공간이라는 의미를 담았습니다.
자연 친화적이면서도 커피 문화를 강조하는 이름입니다.

───
*5개 대안 중 다양성 기반 선택 · 전체 보기: `--all`*
```

---

### Example 2: English Explicit Trigger

**User**:
```
/diverse-sampling Give me tagline ideas for a fitness app
```

**Assistant** (internal process):
```
Phase 0:
- Trigger: Explicit (/diverse-sampling)
- Language: English detected
- Use case: Creative copywriting → valid

Phase 1:
- Apply English VS template
- Generate 5 responses with probabilities

Phase 2:
- Selection: Weighted random
- Selected: Response #1 (probability 0.08)
```

**Output**:
```
**"Your body keeps score. Make it count."**

A tagline that acknowledges the connection between physical activity and mental well-being,
while motivating users to track their progress meaningfully.

───
*Diversity-based selection from 5 alternatives · Show all: `--all`*
```

---

## Implicit Invocation with Confirmation

### Example 3: Korean Implicit Trigger

**User**:
```
스타트업 피칭용 슬로건 다양한 아이디어 좀 내봐
```

**Assistant** (detects implicit trigger):
```
[AskUserQuestion]
다양성 향상 기법(Verbalized Sampling)을 적용할까요?

- 여러 대안을 생성하여 그 중 하나를 선택합니다
- 창의적 작업에 효과적이지만 토큰 소비가 높습니다

Options:
1. 적용 (Apply VS)
2. 일반 응답 (Standard response)
```

**User selects**: `1. 적용 (Apply VS)`

**Output**:
```
**"작은 시작, 큰 파장"**

스타트업의 초기 단계지만 시장에 미칠 영향력을 강조합니다.

───
*5개 대안 중 다양성 기반 선택 · 전체 보기: `--all`*
```

---

### Example 4: User Declines VS

**User**:
```
브레인스토밍 해보자. 새 프로젝트 이름 뭐가 좋을까?
```

**Assistant** (detects implicit trigger):
```
[AskUserQuestion]
다양성 향상 기법(Verbalized Sampling)을 적용할까요?
...
```

**User selects**: `2. 일반 응답 (Standard response)`

**Output** (standard response, no VS):
```
프로젝트 이름을 정하기 위해 몇 가지 방향을 제안드릴게요:

1. 프로젝트의 핵심 기능이나 목표는 무엇인가요?
2. 타겟 사용자층은 누구인가요?
3. 선호하는 분위기나 톤이 있나요? (전문적, 친근한, 혁신적 등)

이 정보를 알려주시면 더 적합한 이름을 제안해 드릴 수 있습니다.
```

---

## Using --all Option

### Example 5: Show All Responses

**User**:
```
/diverse-sampling --all 커피 농담 하나 해줘
```

**Output**:
```
## 생성된 대안들

| 순위 | 선호도 | 아이디어 |
|:---:|:------:|----------|
| 1 | 100% | 커피가 왜 경찰에 신고당했을까요? 자꾸 필터를 거쳤거든요. |
| 2 | 71% | 에스프레소가 친구한테 뭐라고 했을까요? "너 왜 그렇게 묽어?" |
| 3 | 57% | 커피콩의 좌우명은? "갈려야 빛난다!" |
| 4 | 34% | 디카페인 커피가 우울한 이유는? 존재의 이유를 잃어버려서요. |
| 5 | 23% | 라떼가 심리상담사가 된 이유는? 항상 거품만 빠지니까요. |

───
*다양성 기법으로 5개 대안 생성*
```

---

## Using --best Option

### Example 6: Select Highest Probability

**User**:
```
/diverse-sampling --best Suggest a name for my AI writing assistant
```

**Output**:
```
**Inkwell** ★

A classic writing reference that evokes craftsmanship and creativity,
while remaining modern and memorable.

───
*Most preferred from 5 alternatives*
```

---

## Fallback Scenario

### Example 7: Parse Failure

**User**:
```
/diverse-sampling 앱 아이콘 디자인 아이디어
```

**Internal Process** (parse failure occurs):
```
Phase 1:
- VS template applied
- Model response did not follow XML format correctly
- Parse attempt: Failed (no valid <response> blocks)

Fallback triggered:
- Warning logged
- Standard response generated
```

**Output**:
```
앱 아이콘 디자인 아이디어를 몇 가지 제안드릴게요:

1. **미니멀 심볼**: 앱의 핵심 기능을 단순한 기하학적 형태로 표현
2. **그라데이션 배경**: 두 가지 브랜드 컬러를 부드럽게 블렌딩
3. **네거티브 스페이스**: 빈 공간을 활용해 숨겨진 의미 표현
4. **아이소메트릭 스타일**: 3D 느낌의 평면 디자인

───
*일반 응답으로 대체되었습니다.*
```

---

## Use Case Examples

### Creative Writing

**User**:
```
/diverse-sampling 짧은 공포 이야기의 첫 문장을 써줘
```

**Output**:
```
**"매일 밤 11시 47분, 그 아이는 창문 밖에서 손을 흔들었다. 우리 집은 23층인데."**

───
*5개 대안 중 다양성 기반 선택 · 전체 보기: `--all`*
```

---

### Brainstorming

**User**:
```
/diverse-sampling --all 재택근무자를 위한 새로운 앱 기능 아이디어
```

**Output**:
```
## 생성된 대안들

| 순위 | 선호도 | 아이디어 |
|:---:|:------:|----------|
| 1 | 100% | "가상 출퇴근" - 집 주변을 걷는 동안 출근/퇴근 모드로 전환되는 기능. 물리적 경계를 만들어 워라밸 향상. |
| 2 | 71% | "침묵의 동료" - AI가 가끔 슬랙에 "커피 마실 사람?" 같은 메시지를 보내 고립감 해소. |
| 3 | 57% | "창문 동기화" - 전 세계 재택근무자들의 창문 뷰를 실시간으로 공유하는 소셜 기능. |
| 4 | 34% | "업무 환경 소음" - 사무실 백색소음(키보드, 커피머신, 대화)을 재현해 집중력 향상. |
| 5 | 23% | "점심시간 매칭" - 같은 시간에 점심 먹는 재택근무자끼리 화상 식사 연결. |

───
*다양성 기법으로 5개 대안 생성*
```

---

### Marketing Copy

**User**:
```
/diverse-sampling Write a headline for an eco-friendly water bottle brand
```

**Output**:
```
**"Every sip is a vote for the planet."**

A headline that transforms the simple act of drinking water into environmental activism,
creating emotional resonance with eco-conscious consumers.

───
*Diversity-based selection from 5 alternatives · Show all: `--all`*
```

---

## Mode B — Enhance (Authoring Diversity)

### Example 8: Diverse Framing → doc-concretize Handoff

**User**:
```
이 한 줄 아이디어 "원격근무 팀의 비동기 협업 문화" 글로 발전시켜줘
```

**Assistant** (detects Mode B trigger "글로 발전시켜줘"):
```
[AskUserQuestion — Mode B Confirmation]
작성 다양성 향상(Verbalized Sampling → doc-concretize)을 적용할까요?
...
```

**User selects**: `1. 적용 (Apply Enhance)`

**Assistant** (internal process):
```
Phase 0: Mode B (Enhance), Korean, open-ended authoring → valid
Phase 1-B: VS generates 5 distinct authoring directions, e.g.
  - 도입 사례 중심(구체 기업 일화로 시작)
  - 안티패턴 대조(동기 협업의 실패 → 비동기 처방)
  - 도구·의식(ritual) 체크리스트 구조
  - 신뢰·문서화 원리 중심
  - 시간대 분산 팀의 하루 타임라인 서사
Phase 2-B: Weighted random → "안티패턴 대조" 방향 선택
Phase 3-B: Sub-call doc-concretize (Skill tool) with the selected
           direction as seed → recursive-concretization authoring
```

**Output** (structured document authored by doc-concretize):
```
# 원격근무 팀의 비동기 협업 문화

## 동기 협업이 무너지는 지점
...(doc-concretize가 재귀적 구체화로 저작한 본문)...

───
*작성 다양성: 5개 방향 중 "안티패턴 대조" 선택 → doc-concretize 구체화*
```

---

### Example 9: Mode B Excludes Factual Input

**User**:
```
대한민국 인구 수 enhance해서 정리해줘
```

**Assistant** (Mode B trigger present, but use case is factual):
```
⚠️ 사실 단답형 입력은 Mode B(작성 다양성) 적용 대상이 아니에요.
VS 생성과 doc-concretize 하위호출 없이 일반 응답으로 답할게요.

일반 응답: 대한민국 인구는 약 5,100만 명입니다(통계청 기준 연도 확인 필요).
```

---

### Example 10: Mode B Excludes Code Target

**User**:
```
이 Python 함수 enhance해줘

def parse(data):
    return [x.strip() for x in data.split(",")]
```

**Assistant** (Mode B trigger "enhance" present, but the target is code):
```
⚠️ 코드 대상의 enhance는 Mode B(작성 다양성, prose 저작) 적용 범위 밖이에요.
VS 생성과 doc-concretize 하위호출 없이 일반 응답으로 코드를 개선할게요.

[표준 코드 개선 응답 — 빈 입력·공백 처리, 타입 힌트 추가 등]
```

---

## Anti-Patterns (When NOT to Use)

### Factual Questions

**User**:
```
/diverse-sampling 대한민국의 수도는?
```

**Assistant** (should warn):
```
⚠️ 이 질문은 사실 기반 질문으로, Verbalized Sampling에 적합하지 않습니다.
VS는 창의적/개방형 질문에 효과적입니다.

일반 응답: 대한민국의 수도는 서울입니다.
```

### Code Debugging

**User**:
```
/diverse-sampling 이 Python 코드의 버그를 찾아줘: [code]
```

**Assistant** (should warn):
```
⚠️ 코드 디버깅은 정확한 답이 필요한 작업으로, VS에 적합하지 않습니다.

일반 응답으로 버그를 분석하겠습니다:
[standard debugging response]
```
