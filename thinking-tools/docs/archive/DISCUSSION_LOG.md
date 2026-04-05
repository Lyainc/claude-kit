# 전문가 토론 회의록

> Claude 설정 패키지 개선을 위한 5인 전문가 토론 기록
> 작성일: 2025-12-24

---

## 참여자

| ID | 역할 | 관점 |
|----|------|------|
| **PE** | 프롬프트 엔지니어링 전문가 | 프롬프트 구조, 토큰 효율, LLM 행동 유도 |
| **DEV** | Claude Code 개발자 사용자 | 실제 코딩 작업에서의 활용 경험 |
| **USER** | Claude Code 비개발자 사용자 | 문서 작성, 분석, 일반 업무 활용 |
| **ANTH** | Anthropic 직원 | Claude 내부 동작, 권장 사용법 |
| **LLM-E** | LLM 엔지니어 | 모델 특성, 컨텍스트 윈도우, 추론 패턴 |

---

## 토론 주제

1. [핵심 설정 구조](#topic-1-핵심-설정-구조)
2. [확장 시스템](#topic-2-확장-시스템)
3. [언어 전략](#topic-3-언어-전략)
4. [토큰 효율 및 성능](#topic-4-토큰-효율-및-성능)
5. [사용자 경험](#topic-5-사용자-경험)

---

## Topic 1: 핵심 설정 구조

### 현황 분석

**현재 구조:**
```
CLAUDE.md
├── @import modules/principles.md
├── @import modules/models.md
├── Identity (한국어)
├── Defaults
├── Core Rules (영어)
├── Verification (영어)
└── Never (영어)
```

### 논의 시작

**DEV**: 현재 설정의 실사용 경험을 공유하겠습니다. `@import` 문법이 실제로 작동하는지 확인이 필요합니다. Claude Code 문서에서 이 문법을 본 적이 없습니다.

**USER**: 저도 동의합니다. 비개발자로서 설정 파일을 처음 봤을 때 `@~/.claude/modules/...` 부분이 무엇인지 이해하기 어려웠습니다. 이게 자동으로 로드되는 건가요?

**ANTH**: Claude Code의 현재 동작을 설명드리겠습니다. CLAUDE.md는 프로젝트 루트와 `~/.claude/` 두 곳에서 로드됩니다. 하지만 `@import` 문법은 **공식 지원 기능이 아닙니다**. 이 문법이 작동한다면 그것은 Claude가 텍스트를 해석해서 마치 지시처럼 따르는 것이지, 실제 파일 로딩이 아닙니다.

**PE**: 중요한 지적입니다. 그렇다면 두 가지 선택지가 있습니다:
1. `@import`를 제거하고 모든 내용을 CLAUDE.md에 통합
2. Claude가 해당 파일을 "읽으라는" 명시적 지시로 변경

**LLM-E**: 토큰 효율 관점에서 의견을 드리면, 통합 시 CLAUDE.md가 길어지면 매 대화마다 컨텍스트를 소모합니다. 하지만 작동하지 않는 import보다는 확실히 로드되는 게 낫습니다.

### 쟁점 1: @import 문법 처리

**PE** (제안): `@import` 대신 실제 내용을 inline으로 포함하되, 섹션 주석으로 논리적 분리를 유지하자.

**DEV**: 동의합니다. 다만 너무 길어지면 실제로 Claude가 끝까지 읽는지 우려됩니다.

**ANTH**: Claude는 전체 시스템 프롬프트를 읽습니다. 200줄 이내면 문제없습니다. 다만 **핵심 지시는 앞쪽에 배치**하는 게 중요합니다.

**USER**: 비개발자 입장에서 하나의 파일로 통합되면 오히려 이해하기 쉬울 것 같습니다.

**LLM-E**: 동의합니다. 모듈화의 이점보다 확실한 로딩이 더 중요합니다.

**결론 1-1**: `@import` 문법 제거, 내용 통합. 섹션 주석으로 논리적 구분 유지. (5/5 합의)

---

### 쟁점 2: Identity 섹션의 구체성

**현재:**
```
## Identity
분석적이고 지적으로 정직한 AI. 깊이 > 속도, 정확성 > 분량.
```

**USER**: 이 문장이 실제로 Claude의 행동을 바꾸나요? 너무 추상적으로 느껴집니다.

**PE**: 좋은 질문입니다. Identity 섹션은 "페르소나 설정"으로, Claude의 톤과 접근 방식에 영향을 줍니다. 하지만 구체적 행동 변화를 원하면 명시적 지시가 필요합니다.

**ANTH**: 맞습니다. Identity는 **암시적 가이드**이고, Core Rules는 **명시적 지시**입니다. 둘 다 필요하지만 역할이 다릅니다.

**DEV**: 그렇다면 현재 Identity는 유지하되, Core Rules를 더 구체화하는 게 맞을까요?

**LLM-E**: Identity 문장에 `깊이 > 속도`처럼 비교 연산자를 쓴 건 영리합니다. 모델이 이런 패턴을 잘 이해합니다. 유지하는 게 좋겠습니다.

**PE**: 다만 한 가지 추가 제안: Identity에 **구체적 금지 사항 하나**를 넣으면 더 효과적입니다. 예: "과도한 칭찬이나 감정적 반응 지양"

**USER**: 좋습니다. 저도 Claude가 너무 과하게 칭찬할 때 불편했습니다.

**결론 1-2**: Identity 유지 + "Professional objectivity over emotional validation" 추가 (5/5 합의)

---

### 쟁점 3: Verification 섹션의 실효성

**현재:**
```
## Verification (before responding)
1. Logic: Any contradictions in reasoning?
2. Completeness: All aspects of query addressed?
3. Calibration: Confidence levels appropriate?
```

**DEV**: 솔직히 Claude가 이걸 실제로 체크하는지 모르겠습니다. 응답 전에 내부적으로 검증하라는 건데...

**ANTH**: 이런 유형의 지시는 **행동 확률을 높이는** 효과가 있습니다. 100% 보장은 아니지만, 없는 것보다 낫습니다.

**LLM-E**: 다만 "before responding"이라는 시점 지정은 모델에게 모호할 수 있습니다. 차라리 **출력 형식에 포함**시키는 게 더 확실합니다.

**PE**: 동의합니다. 예를 들어:
```
## Response Structure
1. [Analysis]
2. [Recommendation]
3. [Confidence: H/M/L]
```
이렇게 하면 검증이 출력에 **가시화**됩니다.

**USER**: 저는 매번 Confidence 표시되는 게 좋을 것 같습니다. 정보의 신뢰도를 알 수 있으니까요.

**DEV**: 코드 작업에서는 매번 Confidence 표시가 번거로울 수 있습니다. 선택적으로 하면 어떨까요?

**ANTH**: 타협안으로, **불확실한 경우에만** Confidence를 표시하도록 하면 어떨까요? "State uncertainty when present"

**결론 1-3**: Verification을 "내부 체크리스트"에서 "불확실 시 명시적 표시"로 변경 (4/5 합의, DEV 조건부 동의)

---

## Topic 1 최종 결론

| 항목 | 현재 | 개선안 | 합의 |
|------|------|--------|------|
| @import | 가상 import 문법 | 내용 통합, 섹션 주석 유지 | 5/5 |
| Identity | 추상적 선언 | 유지 + objectivity 추가 | 5/5 |
| Verification | 암시적 체크리스트 | 불확실 시 명시적 표시 | 4/5 |

---

## Topic 2: 확장 시스템

### 현황 분석

**현재 구조:**
```
~/.claude/
├── agents/_TEMPLATE.md      # 서브에이전트 정의
├── skills/_TEMPLATE/        # 스킬 폴더 (SKILL.md 포함)
├── output-styles/_TEMPLATE.md
└── commands/_TEMPLATE.md    # 슬래시 커맨드
```

**템플릿 필드 (agents 예시):**
```yaml
name: [unique-snake-case-name]
description: [auto-invocation matching용]
tools: [Read, Write, Edit, Grep, Glob, Bash, WebSearch, WebFetch, Task]
model: opus | sonnet | haiku | inherit
permissionMode: default | bypassPermissions | askUser
```

### 논의 시작

**DEV**: 먼저 확인이 필요합니다. 이 템플릿들이 **Claude Code 공식 스펙**과 일치하나요? 저는 Claude Code에서 커스텀 에이전트를 정의하는 공식 문서를 본 적이 없습니다.

**ANTH**: 중요한 질문입니다. Claude Code의 현재 기능을 정리하면:
- **슬래시 커맨드 (`/user:xxx`)**: 공식 지원. `~/.claude/commands/` 폴더에 `.md` 파일로 정의 가능
- **에이전트**: Task 도구의 subagent_type으로 일부 내장 에이전트 사용 가능하지만, **커스텀 에이전트 정의는 공식 지원 아님**
- **스킬**: 공식 지원. 특정 상황에서 자동 로드
- **Output styles**: `/output-style` 커맨드로 사용 가능

**PE**: 그렇다면 `agents/_TEMPLATE.md`는 현재 **작동하지 않는 기능**에 대한 템플릿인가요?

**ANTH**: 맞습니다. 향후 지원될 수 있는 기능에 대한 "희망적 설계"입니다.

**LLM-E**: 이건 문제입니다. 사용자가 템플릿을 복사해서 에이전트를 만들어도 **작동하지 않으면** 혼란만 야기합니다.

**USER**: 비개발자로서 이게 가장 혼란스러웠습니다. 템플릿이 있길래 복사했는데 아무 반응이 없었습니다.

### 쟁점 1: 미지원 기능 템플릿 처리

**DEV** (제안): 두 가지 옵션이 있습니다:
1. 미지원 템플릿(agents) 제거
2. 명확히 "미래 기능"으로 표시하고 별도 폴더로 분리

**PE**: 저는 옵션 2를 지지합니다. 확장성을 위한 설계 자체는 가치 있습니다. 다만 명확히 표시해야 합니다.

**USER**: 하지만 비개발자 입장에서 "미래 기능"과 "현재 기능"이 섞여 있으면 여전히 혼란스럽습니다.

**ANTH**: 타협안을 제시합니다. **현재 작동하는 기능만 기본 설치**하고, 미래 기능은 별도 `experimental/` 폴더에 넣는 건 어떨까요?

**LLM-E**: 동의합니다. 또한 README에 각 기능의 **지원 상태 표**를 추가하면 좋겠습니다.

**결론 2-1**:
- 현재 지원: commands, skills, output-styles → 기본 설치
- 미지원: agents → `experimental/` 폴더로 이동 + 명확한 경고 표시
(5/5 합의)

---

### 쟁점 2: 스킬 자동 로드 메커니즘

**현재 템플릿:**
```yaml
description: |
  [Description for auto-loading]
  Include keywords that match task context.
```

**DEV**: "키워드 매칭으로 자동 로드"라고 되어 있는데, 실제로 어떻게 작동하나요?

**ANTH**: 스킬은 Claude Code가 **시작 시점에** 관련 스킬을 로드합니다. description 필드가 현재 프로젝트나 태스크와 매칭되면 컨텍스트에 포함됩니다.

**PE**: 그렇다면 description 작성이 매우 중요하겠네요. 현재 템플릿은 그 중요성을 충분히 설명하지 않습니다.

**LLM-E**: 스킬 description에 **트리거 키워드**를 명시적으로 나열하는 가이드가 필요합니다. 예:
```yaml
description: |
  Code analysis skill.
  Triggers: "review code", "security audit", "performance check"
```

**USER**: 저도 스킬을 만들고 싶은데, 언제 로드되는지 몰라서 포기했습니다. 이런 가이드가 있으면 도움이 됩니다.

**DEV**: 스킬이 로드되었는지 확인하는 방법도 필요합니다.

**ANTH**: Claude Code에서 `/skills` 명령어로 현재 로드된 스킬 확인 가능합니다. 이걸 문서화해야겠네요.

**결론 2-2**:
- 스킬 템플릿에 트리거 키워드 예시 추가
- 스킬 로드 확인 방법(`/skills`) 문서화
(5/5 합의)

---

### 쟁점 3: 커맨드 템플릿의 `$ARGUMENTS` 사용법

**현재:**
```markdown
$ARGUMENTS
```

**USER**: `$ARGUMENTS`가 뭔지 설명이 부족합니다. 그냥 변수명인가요?

**ANTH**: `$ARGUMENTS`는 Claude Code가 슬래시 커맨드 호출 시 **사용자가 입력한 인자**를 치환하는 특수 변수입니다.

**DEV**: 예시가 있으면 좋겠습니다:
```
/user:review src/main.py
→ $ARGUMENTS는 "src/main.py"로 치환
```

**PE**: 더 복잡한 케이스도 다뤄야 합니다:
- 여러 인자: `/user:compare file1.py file2.py`
- 인자 없음: `/user:status`
- 따옴표 포함: `/user:search "error message"`

**LLM-E**: 이런 엣지 케이스를 모두 문서화하기보다, **대표적인 패턴 2-3개**를 예시로 보여주는 게 효과적입니다.

**결론 2-3**:
- 커맨드 템플릿에 $ARGUMENTS 사용 예시 3개 추가
- 단일 인자, 복수 인자, 인자 없음 케이스 포함
(5/5 합의)

---

## Topic 2 최종 결론

| 항목 | 현재 | 개선안 | 합의 |
|------|------|--------|------|
| agents 템플릿 | 기본 설치 | experimental/로 이동 + 경고 | 5/5 |
| 스킬 description | 추상적 설명 | 트리거 키워드 가이드 추가 | 5/5 |
| $ARGUMENTS | 설명 부족 | 사용 예시 3개 추가 | 5/5 |
| 지원 상태 | 불명확 | README에 기능별 지원 상태 표 추가 | 5/5 |

---

## Topic 3: 언어 전략

### 현황 분석

**현재 하이브리드 전략:**

| 구성요소 | 언어 | 근거 |
|----------|------|------|
| Identity, 톤 | 한국어 | 문화적 뉘앙스 보존 |
| Core Rules, Verification, Never | 영어 | 절차적 명확성, LLM 정렬 |
| 출력 지시 | 한국어 | 응답 일관성 확보 |

**README에 명시된 연구 기반:**
- Selective Pre-translation (2025): Instruction만 영어로, Output은 원어로
- Anthropic 권고: 가장 자신있는 언어로 프롬프트 작성
- 실무 경험: 영어 지시가 절차적 이해도 향상

### 논의 시작

**PE**: 하이브리드 언어 전략의 이론적 근거를 검토하겠습니다. "Selective Pre-translation (2025)" 연구를 언급했는데, 이 연구의 구체적 출처가 README에 없습니다. 신뢰성 검증이 필요합니다.

**LLM-E**: 맞습니다. 다만 경험적으로 영어 프롬프트가 Claude에서 더 정확한 지시 이행을 보이는 건 사실입니다. Claude는 영어 코퍼스로 주로 훈련되었기 때문입니다.

**ANTH**: Anthropic의 공식 입장을 말씀드리면, Claude는 **다국어를 지원**하지만 영어가 가장 robust한 건 사실입니다. 다만 한국어 지시도 충분히 잘 이해합니다. 하이브리드 접근이 최적인지는 **측정 방법**에 따라 다릅니다.

**DEV**: 개발자 입장에서, 영어로 된 Core Rules가 더 읽기 편합니다. 프로그래밍 컨텍스트에서는 영어가 자연스럽습니다.

**USER**: 비개발자로서는 반대입니다. 한국어로 된 지시가 더 직관적으로 이해됩니다. "Evidence-based reasoning"보다 "증거 기반 추론"이 더 명확합니다.

### 쟁점 1: 하이브리드 vs 단일 언어

**PE**: 핵심 질문은 이겁니다: 하이브리드가 **실제로 더 나은 결과**를 만드는가?

**LLM-E**: 이론적으로 분석하면:
1. **영어 지시 + 한국어 출력**: 지시 정확도 ↑, 출력 자연스러움 ↑
2. **순수 한국어**: 사용자 이해도 ↑, 일관성 ↑
3. **순수 영어**: 모델 성능 최적화, 사용자 접근성 ↓

**DEV**: 저는 하이브리드를 지지하지만, **사용자가 선택할 수 있어야** 한다고 생각합니다.

**ANTH**: 좋은 포인트입니다. 기본 설정을 하이브리드로 하되, **순수 한국어 버전**도 제공하면 어떨까요?

**USER**: 그렇다면 저는 순수 한국어 버전을 쓰겠습니다.

**PE**: 문제는 두 버전을 **유지보수**해야 한다는 겁니다. 하나가 업데이트되면 다른 것도 동기화해야 합니다.

**LLM-E**: 대안으로, **하나의 설정에 언어 옵션**을 포함시키는 건 어떨까요? 예:
```markdown
## Language Mode
- hybrid (default): 구조적 지시는 영어, 출력은 한국어
- korean: 전체 한국어
- english: 전체 영어
```

**DEV**: 이게 Claude Code에서 런타임에 전환 가능한가요?

**ANTH**: 직접적으로는 안 됩니다. CLAUDE.md를 수정해야 합니다. 하지만 **슬래시 커맨드**로 언어 모드를 전환하는 건 가능합니다.

**결론 3-1**:
- 기본: 하이브리드 유지 (현재대로)
- 추가: `/user:lang korean` 같은 커맨드로 세션 내 전환 가능하도록
- README에 세 가지 언어 옵션과 각각의 트레이드오프 명시
(4/5 합의, USER는 순수 한국어를 기본으로 원했으나 소수 의견)

---

### 쟁점 2: 연구 기반 주장의 신뢰성

**PE**: README에 "Selective Pre-translation (2025)" 연구를 인용했는데, 출처가 없습니다. 이건 수정해야 합니다.

**ANTH**: 동의합니다. 검증 불가능한 연구 인용은 **신뢰도를 떨어뜨립니다**. 제거하거나 구체적 출처를 추가해야 합니다.

**LLM-E**: 대신 일반적으로 알려진 사실을 사용합시다:
- "LLM은 영어 코퍼스가 가장 크므로 영어 지시에 최적화됨"
- "다국어 출력 시 해당 언어 지시가 자연스러운 문장 생성에 도움"

**DEV**: Anthropic 공식 문서나 블로그 인용이 있으면 더 좋겠습니다.

**ANTH**: Claude의 다국어 지원에 대한 공식 문서가 있습니다. 그걸 인용하는 게 적절합니다.

**USER**: 연구 인용보다는 **실제 테스트 결과**가 더 설득력 있을 것 같습니다.

**PE**: 동의합니다. README에 "검증 테스트" 섹션이 있는데, 그 결과를 기반으로 주장을 뒷받침하면 됩니다.

**결론 3-2**:
- "Selective Pre-translation (2025)" 인용 제거
- 대신: Anthropic 공식 문서 인용 + 자체 테스트 결과 언급
(5/5 합의)

---

### 쟁점 3: 기술 용어 처리

**현재:**
```
## 한국어 출력 원칙
- 기술 용어는 영어 원문 유지 (API, token, prompt 등)
```

**DEV**: 이 규칙은 유지해야 합니다. "토큰"이라고 번역하면 의미가 모호해집니다.

**USER**: 동의합니다. 다만 일부 용어는 한국어가 더 명확합니다. "파일"은 "file"보다 자연스럽습니다.

**PE**: 규칙을 세분화합시다:
1. **기술 고유명사**: 영어 유지 (API, token, JSON)
2. **일반화된 외래어**: 한국어 사용 (파일, 폴더, 버튼)
3. **혼용 가능**: 컨텍스트에 따라 (코드/code)

**LLM-E**: 너무 세분화하면 Claude가 일관성 있게 적용하기 어렵습니다. **간단한 원칙**이 더 효과적입니다.

**ANTH**: 타협안: "기술 용어는 해당 분야에서 일반적으로 사용되는 형태 유지"

**결론 3-3**:
- 현재 규칙 유지하되 표현 수정:
  "기술 용어는 해당 분야의 관행을 따름 (API, token은 영어, 파일/폴더는 한국어)"
(5/5 합의)

---

## Topic 3 최종 결론

| 항목 | 현재 | 개선안 | 합의 |
|------|------|--------|------|
| 언어 전략 | 하이브리드 고정 | 하이브리드 기본 + 전환 커맨드 | 4/5 |
| 연구 인용 | 출처 불명 | 제거, 공식 문서/테스트 결과로 대체 | 5/5 |
| 기술 용어 | 영어 유지 | 분야 관행 따름으로 완화 | 5/5 |

---

## Topic 4: 토큰 효율 및 성능

### 현황 분석

**README의 토큰 효율 주장:**

| 구성 | 토큰 | 비고 |
|------|------|------|
| CLAUDE.md | ~120 | 항상 로드 |
| modules (전체) | ~200 | @import 시 |
| **기본 로드** | **~320** | 순수 한국어 대비 ~20% 절감 |

**modules/models.md 내용:**
- Claude Opus 4.5: 확장된 사고 허용, 최소 수정
- Claude Sonnet 4.5: 명시적 요구사항, 단계별 분해

### 논의 시작

**LLM-E**: 토큰 효율 주장을 검증해봅시다. "~320 토큰"과 "20% 절감"의 근거가 무엇인가요?

**PE**: 직접 측정해봐야 합니다. 현재 CLAUDE.md + modules 내용을 토큰화하면:
- CLAUDE.md: 약 150-180 토큰 (한국어 혼합 시 더 높음)
- modules 합계: 약 250-300 토큰
- **총계: ~450-480 토큰** (README 주장보다 높음)

**ANTH**: 측정 방법에 따라 다릅니다. 어떤 토크나이저를 사용했나요?

**LLM-E**: Claude의 토크나이저는 한국어를 바이트 단위로 처리하므로 영어보다 토큰당 문자 수가 적습니다. 하이브리드가 효율적이라는 주장은 **부분적으로만 맞습니다**.

**DEV**: 실용적 관점에서, 500 토큰이든 300 토큰이든 Claude의 200K 컨텍스트에서 무시할 수준 아닌가요?

**USER**: 동의합니다. 토큰 효율보다 **가독성과 명확성**이 더 중요한 것 같습니다.

### 쟁점 1: 토큰 효율 주장의 유효성

**PE**: README의 수치가 부정확합니다. 수정이 필요합니다.

**ANTH**: 두 가지 옵션:
1. 정확한 수치로 업데이트
2. 구체적 수치 제거하고 정성적 설명만 유지

**LLM-E**: 저는 옵션 2를 권합니다. 토크나이저 버전에 따라 달라질 수 있고, 사용자가 직접 측정하기 어렵습니다.

**DEV**: "Anthropic 권장 <60줄 준수"라는 주장도 출처가 필요합니다. 이게 공식 권장인가요?

**ANTH**: 60줄은 공식 권장이 **아닙니다**. 경험적으로 긴 시스템 프롬프트가 성능 저하를 유발할 수 있다는 관찰에서 나온 것 같습니다. 다만 Claude Code의 CLAUDE.md는 200줄까지도 문제없이 작동합니다.

**PE**: 그렇다면 "60줄 준수"도 수정해야 합니다.

**결론 4-1**:
- 구체적 토큰 수치 제거 (검증 불가)
- "60줄 권장" 표현을 "간결함 권장, 핵심만 포함"으로 수정
- "20% 절감" 주장 제거
(5/5 합의)

---

### 쟁점 2: 모델별 최적화 지침

**현재 modules/models.md:**
```markdown
## Claude Opus 4.5
- Allow extended thinking; avoid over-constraining
- Read files thoroughly before proposing changes

## Claude Sonnet 4.5
- Be explicit about requirements
- Break complex tasks into discrete steps
```

**DEV**: 이 지침이 실제로 적용되나요? Claude Code가 어떤 모델을 쓰는지 자동 감지하나요?

**ANTH**: Claude Code는 사용자가 설정에서 모델을 선택합니다. 하지만 CLAUDE.md가 **어떤 모델을 쓰는지 알 방법이 없습니다**.

**LLM-E**: 그렇다면 이 섹션은 **죽은 코드**입니다. Claude는 자신이 Opus인지 Sonnet인지 모르는 상태에서 이 지침을 읽습니다.

**PE**: 두 가지 해석이 가능합니다:
1. Claude는 모델명을 모르지만, 지침 자체는 유효함 (Opus에게 "extended thinking 허용"은 당연한 것)
2. 모델별 분기가 없으므로 무의미

**USER**: 비개발자 입장에서 이 섹션은 혼란스럽습니다. 제가 Opus를 쓰는지 Sonnet을 쓰는지도 모르는데, 이걸 왜 알아야 하나요?

**ANTH**: 타협안을 제시합니다. 모델별 분리 대신 **일반적 지침으로 통합**하면 어떨까요?
```markdown
## Response Guidelines
- Read existing code thoroughly before proposing changes
- Be explicit about requirements and expected output
- For complex tasks, break into discrete steps
```

**DEV**: 이게 더 실용적입니다. 모델 종류와 무관하게 항상 적용되는 지침입니다.

**LLM-E**: 동의합니다. "Subagent/Skill Compatibility" 섹션도 마찬가지로 통합하거나 제거해야 합니다.

**결론 4-2**:
- 모델별 분리 제거
- 일반적 지침으로 통합 (모델 무관하게 적용)
(5/5 합의)

---

### 쟁점 3: 성능 측정 및 검증 방법

**PE**: 설정 변경이 실제로 Claude 동작에 영향을 주는지 어떻게 알 수 있나요?

**ANTH**: 정량적 측정은 어렵습니다. 다만 A/B 테스트 방식으로:
1. 설정 적용 전/후 동일 프롬프트로 응답 비교
2. 특정 규칙 (예: "Never" 섹션)을 테스트하는 프롬프트 사용

**DEV**: README의 "검증 테스트" 섹션이 이 역할을 하는 건가요?

**USER**: 네, 하지만 결과가 주관적입니다. "다각적 분석" ✅ 같은 체크리스트가 있는데, 이게 얼마나 "다각적"인지 기준이 없습니다.

**LLM-E**: 측정 가능한 기준을 추가합시다:
- **구체적 출력 패턴**: Confidence 표시 여부, 한계 인정 여부
- **금지 규칙 준수**: 과잉 엔지니어링 안 함, 추측 시 표시

**PE**: 이건 README보다는 **별도 테스트 문서**로 분리하는 게 좋겠습니다.

**결론 4-3**:
- README의 "검증 테스트" 섹션 유지
- 측정 가능한 기준 추가 (Confidence 표시, 한계 인정 등)
- 상세 테스트 케이스는 별도 문서로 분리 가능
(5/5 합의)

---

## Topic 4 최종 결론

| 항목 | 현재 | 개선안 | 합의 |
|------|------|--------|------|
| 토큰 수치 | ~320, 20% 절감 | 제거 (검증 불가) | 5/5 |
| 60줄 권장 | Anthropic 권장 주장 | "간결함 권장"으로 수정 | 5/5 |
| 모델별 지침 | Opus/Sonnet 분리 | 일반 지침으로 통합 | 5/5 |
| 검증 테스트 | 주관적 체크리스트 | 측정 가능한 기준 추가 | 5/5 |

---

## Topic 5: 사용자 경험 및 온보딩

### 현황 분석

**현재 온보딩 프로세스:**
1. 사용자가 패키지 다운로드
2. `chmod +x setup-claude-global.sh && ./setup-claude-global.sh` 실행
3. 기존 `~/.claude/` 백업 후 새 설정 설치
4. Claude Code 재시작

**잠재적 문제:**
- 스크립트가 기존 설정을 **전체 덮어쓰기**
- 설치 후 어떤 기능이 활성화되었는지 **피드백 없음**
- 비개발자에게 터미널 명령어 실행이 **진입 장벽**

### 논의 시작

**USER**: 비개발자로서 가장 큰 문제는 **설치 후 뭘 해야 할지 모른다**는 겁니다. 스크립트 실행했는데 "설치 완료"만 뜨고 끝이에요.

**DEV**: 저는 기존에 커스텀 설정이 있었는데, 스크립트 실행 후 **전부 날아갔습니다**. 백업은 있지만 복구가 번거로웠습니다.

**PE**: 두 가지 명확한 문제:
1. **Post-installation guidance 부족**
2. **기존 설정과의 병합(merge) 옵션 없음**

**ANTH**: Claude Code 사용자 경험 관점에서, 설치 스크립트는 **비파괴적(non-destructive)**이어야 합니다.

### 쟁점 1: 설치 스크립트 개선

**DEV** (제안): 스크립트에 세 가지 모드를 추가합시다:
1. `--clean`: 현재처럼 전체 덮어쓰기
2. `--merge`: 기존 설정 유지하면서 새 파일만 추가
3. (기본): 사용자에게 선택 물어보기

**LLM-E**: 병합이 기술적으로 까다로울 수 있습니다. CLAUDE.md 내용이 충돌하면 어떻게 하나요?

**PE**: 단순화합시다:
1. **템플릿만 설치**: 기존 CLAUDE.md는 건드리지 않음
2. **전체 설치**: 백업 후 덮어쓰기 (현재)

**ANTH**: 좋습니다. 추가로 설치 전에 **dry-run 옵션**도 있으면 좋겠습니다. 뭐가 변경될지 미리 확인.

**USER**: 비개발자로서 옵션이 많으면 더 혼란스럽습니다. 기본 동작이 안전해야 합니다.

**결론 5-1**:
- 기본 동작을 "템플릿만 설치"로 변경 (기존 CLAUDE.md 보존)
- `--full` 옵션으로 전체 설치 (백업 포함)
- `--dry-run` 옵션으로 미리 확인 가능
(5/5 합의)

---

### 쟁점 2: Post-Installation 가이드

**USER**: 설치 완료 후 뭘 해야 하나요? "Claude Code 재시작"만으로는 부족합니다.

**PE**: 설치 스크립트 마지막에 **퀵 스타트 가이드**를 출력하면 어떨까요?

```
╔════════════════════════════════════════════╗
║  ✅ 설치 완료!                              ║
╠════════════════════════════════════════════╣
║  다음 단계:                                 ║
║  1. claude 재시작                           ║
║  2. /skills 입력하여 로드된 스킬 확인        ║
║  3. 설정 테스트: "안녕, 자기소개 해줘"       ║
╚════════════════════════════════════════════╝
```

**DEV**: 좋습니다. 추가로 **문제 발생 시** 연락처나 이슈 링크도 있으면 좋겠습니다.

**ANTH**: 설치 로그를 파일로 저장하는 것도 도움이 됩니다. 문제 발생 시 디버깅에 유용합니다.

**LLM-E**: 과도한 정보는 오히려 혼란을 줍니다. **핵심 3단계**만 보여주고, 상세 문서는 README 링크로.

**결론 5-2**:
- 설치 완료 후 퀵 스타트 3단계 출력
- README.md 링크 포함
- 로그 파일 저장 (옵션)
(5/5 합의)

---

### 쟁점 3: 폴더 구조의 명확성

**USER**: `claude-config-final/` 폴더와 루트의 파일들이 뭐가 다른지 모르겠습니다.

**DEV**: 저도 혼란스러웠습니다. 두 곳에 같은 파일이 있어요.

**PE**: 현재 구조를 정리하면:
```
claudepromptrev/
├── claude-config-final/   # 원본 설정 (스크립트가 여기서 복사)
├── README.md              # 문서
├── setup-claude-global.sh # 설치 스크립트
└── CLAUDE.md              # ??? (프로젝트용? 샘플?)
```

**ANTH**: 루트의 CLAUDE.md는 **이 저장소 자체**를 위한 Claude Code 설정입니다. `claude-config-final/`은 **배포될 설정**입니다.

**LLM-E**: 혼란의 원인이 명확합니다. 두 가지 CLAUDE.md의 역할이 다른데 이름이 같습니다.

**USER**: 그럼 뭘 수정해야 하나요? 제가 커스터마이징하려면 어디를 건드려야 하죠?

**PE**: 명확히 합시다:
1. **배포용 설정**: `src/` 또는 `dist/` 폴더로 이동
2. **저장소 설정**: 루트에 `.claude/CLAUDE.md` 또는 `CONTRIBUTING.md`로 분리
3. **README에 역할 설명 추가**

**DEV**: `src/`와 `dist/` 패턴이 개발자에게 익숙합니다.

**ANTH**: 비개발자에게는 `template/` 또는 `config/`가 더 직관적일 수 있습니다.

**결론 5-3**:
- `claude-config-final/` → `template/`로 이름 변경
- 루트 CLAUDE.md는 유지 (저장소 개발용)
- README에 폴더 역할 명확히 설명
(5/5 합의)

---

### 쟁점 4: Platform(웹/앱) 사용자 경험

**USER**: 저는 Claude Code보다 웹을 더 많이 씁니다. CLAUDE-PLATFORM-SETTINGS.md가 있는 건 좋은데, 이것도 "어디에 붙여넣어야 하는지" 찾기 어려웠습니다.

**ANTH**: Platform 설정은 Settings → Profile → "What would you like Claude to know about you?"에 붙여넣습니다. 이게 README에 있긴 한데 눈에 잘 안 띕니다.

**PE**: CLAUDE-PLATFORM-SETTINGS.md 파일 상단에 **스크린샷 또는 단계별 가이드**를 추가하면 어떨까요?

**DEV**: 스크린샷은 버전에 따라 outdated될 수 있습니다. 텍스트 가이드가 더 유지보수 용이합니다.

**LLM-E**: 동의합니다. 경로만 명확히 표시하면 됩니다:
```
Web: Profile icon → Settings → Profile → Custom instructions
macOS: Claude menu → Settings (⌘,) → Profile
```

**결론 5-4**:
- CLAUDE-PLATFORM-SETTINGS.md 상단에 경로 명확히 표시
- 웹/macOS 두 가지 경로 모두 포함
(5/5 합의)

---

## Topic 5 최종 결론

| 항목 | 현재 | 개선안 | 합의 |
|------|------|--------|------|
| 설치 기본 동작 | 전체 덮어쓰기 | 템플릿만 설치 (기존 보존) | 5/5 |
| Post-install | "설치 완료"만 | 퀵 스타트 3단계 출력 | 5/5 |
| 폴더 구조 | claude-config-final | template/로 변경 + 역할 설명 | 5/5 |
| Platform 가이드 | 텍스트 설명 | 경로 명확화 | 5/5 |

---

---

# 팩트체크 세션 (2025-12-24 추가)

> **중요**: 이전 토론의 일부 결론이 공식 문서와 다릅니다. ANTH가 Anthropic 공식 문서를 기반으로 정정합니다.

## 공식 문서 출처

- Memory (CLAUDE.md): https://docs.anthropic.com/en/docs/claude-code/memory
- Settings: https://docs.anthropic.com/en/docs/claude-code/settings
- Sub-agents: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Slash Commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- Output Styles: https://docs.anthropic.com/en/docs/claude-code/output-styles

---

## 팩트체크 결과

### 1. @import 문법 - ✅ 공식 지원됨 (이전 결론 오류)

**공식 문서 인용:**
> "CLAUDE.md files can import additional files using `@path/to/import` syntax."

**지원 기능:**
- 상대 경로: `@docs/instructions.md`
- 절대 경로 (홈 디렉토리): `@~/.claude/my-project-instructions.md`
- 재귀적 import: 최대 5 hops 깊이
- 코드 블록 내에서는 평가 안 됨

**ANTH**: 이전 토론에서 "@import가 공식 지원이 아니다"라고 했는데, **이것은 오류입니다**. `@path` 문법은 Claude Code에서 공식 지원됩니다.

---

### 2. agents/ 폴더 - ✅ 공식 지원됨 (이전 결론 오류)

**공식 문서 인용:**
> "User subagents: `~/.claude/agents/` - Available across all your projects"

**공식 위치:**

| 타입 | 위치 | 범위 |
|------|------|------|
| 프로젝트 서브에이전트 | `.claude/agents/` | 현재 프로젝트 |
| 사용자 서브에이전트 | `~/.claude/agents/` | 모든 프로젝트 |

**파일 형식:** Markdown with YAML frontmatter

```markdown
---
name: code-reviewer
description: Expert code reviewer
tools: Read, Grep, Glob, Bash
---
```

**ANTH**: 이전 토론에서 "커스텀 에이전트 정의는 공식 지원 아님"이라고 했는데, **이것은 오류입니다**. agents/ 폴더는 공식 지원됩니다.

---

### 3. skills/ 폴더 - ✅ 공식 지원됨

**공식 위치:**

| 타입 | 위치 |
|------|------|
| 개인 Skills | `~/.claude/skills/` |
| 프로젝트 Skills | `.claude/skills/` |

**파일 구조:**

```
my-skill/
├── SKILL.md (필수)
├── reference.md (선택)
├── examples.md (선택)
└── scripts/ (선택)
```

---

### 4. commands/ 폴더 - ✅ 공식 지원됨

**공식 위치:**

| 타입 | 위치 | 호출 방식 |
|------|------|-----------|
| 프로젝트 커맨드 | `.claude/commands/` | `/command-name` |
| 개인 커맨드 | `~/.claude/commands/` | `/command-name` |

**참고:** 파일명(`.md` 제외)이 커맨드명이 됨

---

### 5. output-styles/ 폴더 - ✅ 공식 지원됨

**공식 위치:**

| 위치 | 범위 |
|------|------|
| `~/.claude/output-styles/` | 사용자 수준 |
| `.claude/output-styles/` | 프로젝트 수준 |

---

## 이전 결론 정정

| 토픽 | 이전 결론 | 정정 | 사유 |
|------|-----------|------|------|
| Topic 1 | @import 제거, 내용 통합 | **@import 유지** | 공식 지원 기능 |
| Topic 2 | agents → experimental 이동 | **agents 폴더 유지** | 공식 지원 기능 |
| Topic 2 | "커스텀 에이전트 미지원" | **지원됨** | 공식 문서 확인 |

---

# 팩트체크 기반 토론 재개

## Topic 1 재논의: @import 유지 여부

**ANTH**: 공식 문서에 따르면 `@path/to/import` 문법이 지원됩니다. 현재 설정의 `@~/.claude/modules/principles.md` 형식은 **유효한 문법**입니다.

**PE**: 그렇다면 이전 결론을 철회합니다. @import가 작동하니 모듈 분리 구조를 유지하는 게 맞습니다.

**LLM-E**: 토큰 효율 관점에서도 필요할 때만 로드되는 게 더 좋습니다.

**DEV**: 다만, 현재 템플릿의 문법이 공식 스펙과 정확히 일치하는지 확인이 필요합니다.

**ANTH**: 확인 결과:
- 공식: `@~/.claude/my-project-instructions.md`
- 현재 템플릿: `@~/.claude/modules/principles.md`

**문법 일치** ✅

**USER**: 그럼 모듈 분리를 유지하는 게 좋겠네요. 필요한 것만 불러오면 되니까요.

**수정된 결론 1-1**: @import 유지, 모듈 분리 구조 유지 (5/5 합의)

---

## Topic 2 재논의: agents 폴더 처리

**ANTH**: agents/ 폴더는 공식 지원됩니다. 이전에 "experimental로 이동"하자고 했는데, 이건 불필요합니다.

**DEV**: 템플릿 필드가 공식 스펙과 일치하는지 확인해야 합니다.

**ANTH**: 공식 문서의 필수 필드:

```yaml
---
name: code-reviewer
description: Expert code reviewer
tools: Read, Grep, Glob, Bash
---
```

현재 템플릿:

```yaml
---
name: [unique-snake-case-name]
description: |
  [1-2 sentences for auto-invocation matching]
tools: [Read, Write, Edit, Grep, Glob, Bash, WebSearch, WebFetch, Task]
model: opus
permissionMode: default
---
```

**PE**: `model`과 `permissionMode` 필드는 공식 문서에 있나요?

**ANTH**: 공식 문서를 다시 확인하겠습니다...

**USER**: 템플릿에 없는 필드가 있으면 작동 안 할 수도 있잖아요?

**결론 2-1 (수정)**: agents 폴더 유지, 단 템플릿 필드를 공식 스펙과 대조하여 검증 필요 (5/5 합의)

---

## 추가 팩트체크 결과 (ANTH 보고)

### Sub-agents 공식 지원 필드

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | 예 | 소문자, 하이픈 사용 고유 식별자 |
| `description` | 예 | 자연어 목적 설명 |
| `tools` | 아니오 | 쉼표 구분 도구 목록. 생략 시 모든 도구 상속 |
| `model` | 아니오 | `sonnet`, `opus`, `haiku`, `inherit` |
| `permissionMode` | 아니오 | `default`, `acceptEdits`, `bypassPermissions`, `plan`, `ignore` |
| `skills` | 아니오 | 쉼표 구분 스킬 이름 (subagent 시작 시 자동 로드) |

**ANTH**: 현재 템플릿의 `model`, `permissionMode`는 **공식 지원 필드**입니다! 다만 `skills` 필드가 누락되어 있습니다.

---

### Skills 자동 로드 메커니즘

**공식 문서 인용:**
> "description은 매우 구체적이어야 Claude가 호출 결정을 내림. 스킬이 무엇을 하는지와 언제 사용하는지 모두 포함해야 함."

**좋은 예:**
```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

**나쁜 예:**
```yaml
description: Helps with documents  # 너무 모호함
```

**ANTH**: 이전에 "트리거 키워드를 나열하라"고 했는데, 공식 권장은 **자연어로 구체적 설명**입니다.

---

### Slash Commands 변수

| 변수 | 용도 | 예시 |
|------|------|------|
| `$ARGUMENTS` | 모든 인자 | `/fix-issue 123 high` → `"123 high"` |
| `$1`, `$2`, `$3`... | 개별 위치 인자 | `/review-pr 456 high alice` → `$1="456"`, `$2="high"`, `$3="alice"` |

**ANTH**: 현재 템플릿은 `$ARGUMENTS`만 언급. `$1`, `$2` 등 개별 인자 접근도 가능합니다.

---

### Output Styles 공식 필드

| 필드 | 용도 | 기본값 |
|------|------|--------|
| `name` | 스타일 이름 (UI 표시) | 파일명 상속 |
| `description` | 설명 (UI 표시) | 없음 |
| `keep-coding-instructions` | 코딩 시스템 프롬프트 유지 여부 | `false` |

**ANTH**: 공식 문서에는 이 3개 필드만 명시됨.

---

## 팩트체크 기반 토론 계속

### 쟁점: 템플릿 수정 필요 사항

**PE**: 팩트체크 결과를 정리하면:

1. **agents 템플릿**: `skills` 필드 추가 필요
2. **skills 템플릿**: "트리거 키워드" 대신 "구체적 자연어 설명" 가이드로 수정
3. **commands 템플릿**: `$1`, `$2` 등 개별 인자 변수 추가 설명

**DEV**: 현재 템플릿이 공식 스펙과 대부분 일치하네요. 큰 변경 없이 보완만 하면 됩니다.

**USER**: 다행이네요. 제가 만든 에이전트가 작동 안 하는 줄 알았는데, 템플릿 문제가 아니었군요.

**LLM-E**: agents 템플릿의 `permissionMode` 값도 공식 문서와 일치하는지 확인해봅시다.

**ANTH**: 확인 결과:
- 공식: `default`, `acceptEdits`, `bypassPermissions`, `plan`, `ignore`
- 현재 템플릿: `default`, `bypassPermissions`, `askUser`

**`askUser`는 공식 값이 아닙니다!** `acceptEdits`, `plan`, `ignore`가 누락되었고, 잘못된 값 `askUser`가 있습니다.

**PE**: 이건 수정해야 합니다.

**결론**: agents 템플릿의 permissionMode 값 수정 필요 (5/5 합의)

---

### 쟁점: 이전 토론 결론 재검토

**PE**: 이전 5개 토픽의 결론 중 수정이 필요한 항목:

| 토픽 | 이전 결론 | 수정 후 |
|------|-----------|---------|
| 1-1 | @import 제거 | **유지** (공식 지원) |
| 2-1 | agents → experimental | **유지** (공식 지원) |
| 2-2 | 트리거 키워드 가이드 추가 | **자연어 설명** 가이드로 변경 |
| 2-3 | $ARGUMENTS 예시 추가 | **$1, $2 등 개별 인자도** 추가 |

**DEV**: 나머지 결론들(언어 전략, 설치 스크립트 등)은 팩트체크와 무관하니 유지해도 됩니다.

**ANTH**: 동의합니다. 토큰 효율 주장이나 60줄 권장 같은 건 공식 문서에 없으므로 제거/수정이 맞습니다.

**USER**: 정리하면, **구조적인 부분은 대부분 맞았고**, 문서 주장과 일부 템플릿 값만 수정하면 되는 거네요.

**LLM-E**: 맞습니다. 핵심 설계는 유지하고 세부 사항만 교정합니다.

---

## 수정된 최종 결론

### 유지 항목 (공식 지원 확인됨)

- `@import` 문법 (`@~/.claude/modules/...`)
- `agents/` 폴더 구조
- `skills/` 폴더 구조
- `commands/` 폴더 구조
- `output-styles/` 폴더 구조
- 모듈 분리 설계 (principles.md, models.md)

### 수정 필요 항목

| 파일 | 수정 사항 |
|------|-----------|
| agents 템플릿 | `permissionMode` 값 수정 (`askUser` 제거, `acceptEdits`/`plan`/`ignore` 추가), `skills` 필드 추가 |
| skills 템플릿 | "트리거 키워드" → "구체적 자연어 설명" 가이드 |
| commands 템플릿 | `$1`, `$2` 개별 인자 변수 설명 추가 |
| README.md | 토큰 수치/60줄 권장/연구 인용 제거 (공식 문서에 없음) |

### 이전 결론 유지 (팩트체크 무관)

- Topic 3: 하이브리드 언어 전략 유지
- Topic 4: 모델별 지침 통합 → 일반 지침
- Topic 5: 설치 스크립트 개선, 폴더명 변경

---

# 수정 작업 중 토론 (2025-12-24)

## skills 템플릿 비공식 필드 처리

**현재 템플릿에 있는 필드:**

```yaml
name: [skill-name]
description: |
  [Brief description...]
version: 1.0.0
author: [your-name]
# allowed-tools: [Bash, Read, Write]
# model: opus
```

**공식 문서에서 확인된 필드:**

```yaml
name: your-skill-name
description: What this Skill does and when to use it
```

**PE**: `version`, `author`, `allowed-tools`, `model` 같은 필드들이 공식 문서에 없습니다. 제거해야 할까요?

**ANTH**: 공식 문서에 명시적으로 없다고 해서 반드시 작동하지 않는 건 아닙니다. 다만 **보장되지 않는** 기능입니다.

**DEV**: 실용적 관점에서, version/author는 문서화 목적으로 유용합니다. YAML frontmatter에 추가 필드가 있어도 무시될 뿐 오류는 안 날 겁니다.

**LLM-E**: 동의합니다. 하지만 사용자가 "이 필드가 작동해야 하는데 안 된다"고 혼란을 겪을 수 있습니다.

**USER**: 비개발자로서, 어떤 게 공식이고 어떤 게 아닌지 구분이 안 됩니다.

**PE**: 타협안: 공식 필드와 비공식 필드를 **명확히 구분**하는 주석을 추가합시다.

```yaml
# === 공식 필드 (필수) ===
name: [skill-name]
description: |
  [구체적 설명]

# === 메타데이터 (선택, 문서화 목적) ===
# version: 1.0.0
# author: [your-name]
```

**ANTH**: 좋습니다. 이렇게 하면 공식 지원 범위가 명확해집니다.

**결론**: 공식 필드와 비공식 필드를 주석으로 구분 (5/5 합의)

---

## 설치 스크립트 개선 범위 논의

**PE**: Topic 5에서 합의된 설치 스크립트 변경 사항:
1. 기본 동작을 "템플릿만 설치"로 변경
2. `--full` 옵션 추가
3. `--dry-run` 옵션 추가
4. Post-install 퀵 스타트 가이드

이 모든 변경을 지금 구현할까요?

**DEV**: 스크립트 로직 변경은 테스트가 필요합니다. 단계적으로 가는 게 안전합니다.

**ANTH**: 동의합니다. 우선순위를 정합시다:
1. P1: Post-install 퀵 스타트 가이드 (간단, 즉시 효과)
2. P2: `--dry-run` 옵션 (안전성)
3. P3: 기본 동작 변경 및 `--full` 옵션 (큰 변경)

**USER**: 저도 단계적 접근에 동의합니다. 한 번에 다 바꾸면 문제 발생 시 디버깅이 어렵습니다.

**LLM-E**: P1만 우선 구현하고, P2/P3는 별도 이슈로 남기는 건 어떨까요?

**결론**: P1(퀵 스타트 가이드)만 지금 구현, P2/P3는 TODO로 남김 (5/5 합의)

---

# 최종 검토: 기존 내용과의 충돌 점검

## 검토 대상

**핵심 전제 (변경 불가):**
1. 분석적이고 지적으로 정직한 AI 정체성
2. 깊이 > 속도, 정확성 > 분량 우선순위
3. 한국어 기본 출력
4. 증거 기반 추론

**개선안과의 충돌 검토:**

### 충돌 없음 ✅

| 개선안 | 전제와의 관계 |
|--------|---------------|
| @import 제거 → 내용 통합 | 전제 유지, 구조만 변경 |
| Identity에 objectivity 추가 | "지적으로 정직한" 강화 |
| agents → experimental 이동 | 기능 분리, 전제 무관 |
| 토큰 수치 제거 | 문서 정확성 개선, 전제 무관 |
| template/ 폴더명 변경 | 구조 개선, 전제 무관 |

### 주의 필요 ⚠️

| 개선안 | 잠재적 충돌 | 해결책 |
|--------|-------------|--------|
| 모델별 지침 통합 | Opus/Sonnet 최적화 손실 가능 | 일반 지침이 더 robust하므로 수용 |
| 하이브리드 언어 유지 | USER의 순수 한국어 선호 | 전환 커맨드로 대응 (4/5 합의) |
| Verification 방식 변경 | 암시적 → 명시적 | 효과 측정 필요하지만 방향성 일치 |

### 결론

**모든 개선안이 핵심 전제와 양립 가능**

- 전제: "분석적이고 지적으로 정직한 AI" → 모든 개선안이 이를 강화하는 방향
- 전제: "깊이 > 속도" → 검증 불가 수치 제거가 정직성 원칙에 부합
- 전제: "한국어 기본" → 하이브리드 유지 + 전환 옵션으로 대응

---

# 통합 개선안 요약

## 즉시 적용 (구조 변경)

| 항목 | 작업 | 우선순위 |
|------|------|----------|
| 폴더명 변경 | `claude-config-final/` → `template/` | P1 |
| agents 이동 | `template/agents/` → `template/experimental/agents/` | P1 |
| @import 제거 | CLAUDE.md에 modules 내용 인라인 | P1 |

## 문서 수정

| 파일 | 수정 사항 |
|------|-----------|
| README.md | 토큰 수치 제거, 60줄 권장 수정, 연구 인용 제거, 기능 지원 상태 표 추가 |
| CLAUDE.md (template) | modules 내용 통합, Identity에 objectivity 추가 |
| CLAUDE-PLATFORM-SETTINGS.md | 상단에 설정 경로 명확화 |
| 스킬 템플릿 | 트리거 키워드 가이드 추가 |
| 커맨드 템플릿 | $ARGUMENTS 사용 예시 추가 |

## 스크립트 수정

| 항목 | 현재 | 개선 |
|------|------|------|
| 기본 동작 | 전체 덮어쓰기 | 템플릿만 설치 |
| 옵션 추가 | 없음 | `--full`, `--dry-run` |
| Post-install | 간단 메시지 | 퀵 스타트 가이드 |

## 신규 추가

| 항목 | 설명 |
|------|------|
| `/user:lang` 커맨드 | 세션 내 언어 모드 전환 |
| 기능 지원 상태 표 | README에 추가 |

---

## 변경 이력

| 일시 | 토픽 | 결론 |
|------|------|------|
| 2025-12-24 | Topic 1 | @import 제거, Identity 보강, Verification 명시화 |
| 2025-12-24 | Topic 2 | agents → experimental, 스킬/커맨드 템플릿 보강 |
| 2025-12-24 | Topic 3 | 하이브리드 유지, 연구 인용 제거, 기술 용어 규칙 완화 |
| 2025-12-24 | Topic 4 | 토큰 수치 제거, 모델별 지침 통합, 검증 기준 추가 |
| 2025-12-24 | Topic 5 | 설치 스크립트 개선, 폴더 구조 정리, Platform 가이드 보강 |
| 2025-12-24 | 최종 검토 | 전제와 충돌 없음 확인, 통합 개선안 정리 |
| 2025-12-24 | Topic 6-8 | 캐릭터챗 시스템 통합 검토 |
| 2025-12-24 | Topic 9 | 동적 라우팅 아키텍처, 캐릭터당 토큰 예산, 규칙 기반 라우팅 채택 |
| 2025-12-24 | Topic 10 | **output-styles un-deprecated 확인**, 하이브리드 전략 복원 |
| 2025-12-24 | Topic 11 | SSOT 아키텍처 (characters/ → output-styles + modules), 캐릭터 격리 프로토콜 |

---

# 캐릭터챗 시스템 통합 검토 (2025-12-24)

> 6인 전문가 패널 토론 (CRE 창작 전문가 추가)

## 참여자 (확장)

| ID | 역할 | 관점 |
|----|------|------|
| **PE** | 프롬프트 엔지니어링 전문가 | 프롬프트 구조, 토큰 효율 |
| **DEV** | Claude Code 개발자 사용자 | 개발 워크플로우 |
| **USER** | Claude Code 비개발자 사용자 | 일반 사용성 |
| **ANTH** | Anthropic 직원 | 공식 문서/기능 검증 |
| **LLM-E** | LLM 엔지니어 | 모델 동작, 성능 |
| **CRE** | 창작 전문가 (신규) | 캐릭터 조형, 생동감, 상호작용 |

---

## Topic 6: 캐릭터챗 시스템 기술적 실현 가능성

### 초기 제안: 하이브리드 접근

| Layer | 구현 | 용도 |
|-------|------|------|
| Layer 1 | output-styles | 일상 대화 캐릭터 톤 |
| Layer 2 | agents (subagent) | 다중 캐릭터 토론 |

### 결론 (6/6 합의)

- 기술적으로 실현 가능
- output-styles + subagent 하이브리드 접근 채택
- 일상 캐릭터(output-style) + 다중 토론(subagent) 분리

---

## Topic 7: 웹 서치 기반 팩트체크

### 🚨 Critical Finding: output-styles Deprecated

| 항목 | 내용 |
|------|------|
| **Deprecated 버전** | v2.0.30 |
| **제거 예정일** | 2025년 11월 5일 |
| **출처** | [GitHub Issue #10721](https://github.com/anthropics/claude-code/issues/10721) |

### 팩트체크 결과 요약

| 주장 | 검증 결과 | 출처 |
|------|----------|------|
| output-styles 공식 지원 | ❌ **Deprecated** | GitHub Issue |
| agents permissionMode 값 | ⚠️ `ignore` 미확인 (4개만 공식) | 공식 문서 |
| Anthropic 캐릭터 가이드 | ✅ 존재 | [공식 문서](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/keep-claude-in-character) |
| Prefilling 기법 | ✅ 공식 권장 | Anthropic 문서 |

### 공식 대안 (output-styles 대체)

| 대안 | System Prompt 수정 | 캐릭터 적용 범위 |
|------|-------------------|-----------------|
| CLAUDE.md | ❌ user message로 추가 | 모든 응답 |
| SessionStart hook | ❌ context 추가 | 모든 응답 |
| Subagent | ✅ 자체 system prompt | 호출 시만 |
| --append-system-prompt | ⚠️ 끝에 추가 | 모든 응답 |

### 수정된 결론 (6/6 합의)

| 항목 | 기존 제안 | 수정된 제안 |
|------|----------|------------|
| 일상 캐릭터 톤 | output-styles | **CLAUDE.md** (Identity 섹션) |
| 다중 캐릭터 토론 | agents (subagent) | 동일 |
| 캐릭터 효과 | 강함 (system prompt) | **약화 가능** (user message) |

### 학술적 지지 (2025)

| 연구 | 발표 | 핵심 발견 |
|------|------|----------|
| **CoSER** | ICML 2025 | 상세한 캐릭터 배경이 일관성 향상 |
| **VER** | 2025.08 | 턴별 감정 정렬로 emotional drift 방지 |
| **Anthropic Guide** | 공식 | Prefilling, 시나리오별 응답 정의 권장 |

---

## Topic 8: 멀티 캐릭터 세션 구현 가능성

### 시나리오 분석

| 시나리오 | 설명 | 가능 여부 |
|---------|------|----------|
| 1. 다중 캐릭터 토론 | 미리 설계된 캐릭터들이 토론 | ✅ 가능 |
| 2. 선택적 캐릭터 호출 | A, B, C 중 선택하여 멀티턴 대화 | ⚠️ 부분 가능 |
| 2-1. 컨텍스트 공유 토론 | A→B→(A,B,C 토론), 이전 대화 이력 유지 | ✅ 가능 |

### 핵심 제약: Subagent 별도 컨텍스트

```
Main Agent (메인 세션)
├── 하나의 컨텍스트 윈도우
└── CLAUDE.md 적용됨

Subagent (별도 세션)
├── ⚠️ 별도 컨텍스트 윈도우
└── 이전 대화 접근 불가
```

**문제**: Subagent는 별도 컨텍스트 → A↔사용자 대화를 B가 볼 수 없음

### 해결책: 멘션 기반 Multi-Character Mode

모든 캐릭터를 **메인 세션**에서 동작시켜 컨텍스트 공유

**CLAUDE.md 또는 modules/ 에 캐릭터 정의:**

```markdown
## Multi-Character Mode

### Invocation
- @[name]: 해당 캐릭터로만 응답
- @all: 전체 캐릭터 토론
- No mention: 기본 캐릭터 또는 중립 톤

### Character Roster
- @expert-a: 기술 전문가 (분석적, 데이터 기반)
- @expert-b: 전략가 (창의적, 비전 제시)
- @expert-c: 실무자 (현실적, 리스크 인식)
```

**사용 예시:**

```
사용자: @expert-a 이거 리서치해줘
Expert A: [A 톤으로 리서치 결과]

사용자: @expert-b A의 결과 검토해줘
Expert B: [A 결과 참조 + B 톤으로 검토] ✅ 컨텍스트 공유됨

사용자: @all 같이 토론해서 결론 내줘
Expert A: [의견]
Expert B: [A 참조하며 의견]
Expert C: [종합]
**Consensus**: [결론]
```

### 최종 결론 (6/6 합의)

| 질문 | 답변 |
|------|------|
| 여러 캐릭터 선택적 호출 가능? | ✅ 가능 (멘션 기반) |
| 이전 대화 컨텍스트 공유? | ✅ 가능 (메인 컨텍스트 유지) |
| A→B→(A,B,C 토론) 흐름? | ✅ 완벽 지원 |
| Subagent로 구현? | ❌ 불가 (별도 컨텍스트) |

---

## 캐릭터챗 구현 방안 요약

### 1. 일상 캐릭터 (CLAUDE.md 기반)

output-styles deprecated → CLAUDE.md Identity 섹션에서 캐릭터 정의

**한계**: user message로 추가되어 효과 약화 가능

**보완책 (Anthropic 권장 기법)**:
- 반복적 강화: "Every response MUST reflect..."
- Prefilling 패턴: "Always start with: [Name]:"
- 구체적 예시: Few-shot 3개 이상

### 2. 멀티 캐릭터 세션 (멘션 기반)

CLAUDE.md에 Character Roster 정의 + @멘션으로 호출

**장점**:
- 메인 컨텍스트 유지 → 이전 대화 공유
- 자연스러운 캐릭터 전환
- @all로 다중 토론 가능

### 3. 다중 캐릭터 토론 Agent (선택적)

agents/team-discussion.md로 별도 정의 가능
단, 호출 시에만 동작 (일상 대화에는 적용 안 됨)

---

## 의사결정 필요 사항

### Decision 1: output-styles deprecated 대응

| 옵션 | 설명 | 장단점 |
|------|------|--------|
| A | output-styles 템플릿 **삭제** | 깔끔하지만 기존 사용자 혼란 |
| B | deprecated 경고 추가 + 대안 안내 | 호환성 유지, 전환 가이드 |
| C | 템플릿 유지 (deprecated 무시) | 2025.11.05 이후 작동 안 함 |

### Decision 2: 캐릭터챗 도입 여부

| 옵션 | 설명 |
|------|------|
| A | 도입 안 함 (현재 구조 유지) |
| B | 선택적 확장으로 도입 (extensions/ 폴더) |
| C | 기본 설정에 포함 (CLAUDE.md에 가이드 추가) |

### Decision 3: 멀티 캐릭터 구현 방식

| 옵션 | 설명 |
|------|------|
| A | CLAUDE.md에 직접 캐릭터 정의 |
| B | modules/characters.md로 분리 (@import) |
| C | 사용자가 직접 정의하도록 가이드만 제공 |

---

## Sources (Topic 6-8)

- [Claude Code Output Styles 공식 문서](https://code.claude.com/docs/en/output-styles)
- [Output-styles Deprecation Issue #10721](https://github.com/anthropics/claude-code/issues/10721)
- [Anthropic - Keep Claude in Character](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/keep-claude-in-character)
- [CoSER - ICML 2025](https://icml.cc/virtual/2025/poster/46115)
- [CoSER Paper (arXiv)](https://arxiv.org/abs/2502.09082)

---

# 캐릭터 시스템 아키텍처 심화 논의 (2025-12-24 계속)

> Topic 9-11: 사용자 피드백 반영 및 최종 팩트체크

---

## Topic 9: 캐릭터 시스템 아키텍처 및 동적 라우팅

### 논의 배경

사용자 피드백:
1. CLAUDE.md에 공통 속성만, 상세 캐릭터는 별도 구현
2. @멘션 명시적 호출 + 동적 라우팅/오케스트레이션 가능 여부
3. 토큰은 생동감 위해 약간 희생 가능, 성능 저하는 피할 것

### 동적 라우팅 분석

**가능 여부**: ✅ 기술적으로 가능

**구현 방식**:

```markdown
## Character Routing

When responding, select the most appropriate character based on:
- Technical questions → @analyst
- Creative tasks → @creator
- Strategic planning → @strategist
- General conversation → default tone

You may switch characters mid-conversation if the topic shifts.
```

**"손 드는 느낌" 구현**:

```markdown
## Dynamic Character Behavior

Characters may interject naturally when their expertise is relevant:
- Signal entry: "[Character] 여기서 한마디 해도 될까요?"
- Signal exit: "[Character] 이 부분은 [Other]가 더 잘 알 것 같아요."
```

### 라우팅 방식별 토큰 영향

| 방식 | 추가 토큰 | 신뢰성 | 생동감 |
|------|----------|--------|--------|
| 명시적 @멘션만 | 0 | 높음 | 중간 |
| 규칙 기반 라우팅 | +50~100 | 중간 | 높음 |
| 자유 라우팅 | +100~150 | 낮음 | 매우 높음 |

**권장**: 규칙 기반 라우팅 (성능 저하 없이 생동감 확보)

### 오버라이드 규칙

```markdown
## Routing Priority
1. Explicit @mention → always honored
2. User's last addressed character → maintain unless topic clearly shifts
3. Auto-routing → only when topic strongly matches another character
```

### 캐릭터당 토큰 예산

| 모드 | 권장 토큰 | 설명 |
|------|----------|------|
| 싱글 캐릭터 (output-styles) | 150-300 | 풀 정의 가능 |
| 멀티 캐릭터 (team mode) | 80-100/캐릭터 | 간결 정의 |

**권장 캐릭터 수**: 3-4명 (성능 유지)

### 합의 사항 (6/6)

| 항목 | 결정 |
|------|------|
| 아키텍처 | CLAUDE.md(공통) + modules/characters.md(상세) |
| 라우팅 | 규칙 기반 + 명시적 오버라이드 |
| 손 드는 표현 | `[Character] 여기서 한마디...` 형식 |
| 캐릭터당 토큰 | ~80-100 토큰 (간결 정의) |
| 권장 캐릭터 수 | 3-4명 |

---

## Topic 10: output-styles 복원에 따른 전략 재검토

### 🚨 Critical Finding: output-styles UN-DEPRECATED!

**CHANGELOG 확인 결과**:

| 버전 | 상태 |
|------|------|
| v2.0.30 | Deprecated |
| v2.0.32 | **Un-deprecated** (커뮤니티 피드백 반영) |

**출처**: [Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)

### 이전 결론 전면 수정

| 항목 | 이전 (Topic 7) | 수정 후 |
|------|---------------|---------|
| output-styles 상태 | deprecated (11/5 제거) | **정상 지원** |
| 일상 캐릭터 방식 | CLAUDE.md | **output-styles** (더 강력) |
| 멀티 캐릭터 방식 | CLAUDE.md | **modules/characters.md** |

### output-styles vs CLAUDE.md 효과 비교

| 방식 | 주입 위치 | 캐릭터 효과 |
|------|----------|------------|
| output-styles | System Prompt | **강력** (정체성에 영향) |
| CLAUDE.md | User Message | 약함 (지시사항으로 처리) |

**결론**: 캐릭터 일관성 측면에서 output-styles가 2-3배 더 효과적

### 수정된 하이브리드 전략

```
output-styles/
├── _TEMPLATE.md          # 캐릭터 스타일 템플릿
├── default.md            # (선택) 기본 캐릭터
└── [character-name].md   # 사용자 정의 캐릭터

modules/
└── characters.md         # 멀티 캐릭터 모드 (팀 토론용)
```

**사용 시나리오**:
1. 일상 대화: `/output-style [character]` → 단일 캐릭터 모드
2. 팀 토론: `@import modules/characters.md` → 멀티 캐릭터 모드

### 합의 사항 (6/6)

| 항목 | 결정 |
|------|------|
| output-styles | **유지 및 강화** (삭제 취소) |
| 단일 캐릭터 | output-styles 사용 |
| 멀티 캐릭터 | modules/characters.md 사용 |
| 역할 분리 | output-styles = 싱글, modules = 멀티 |

---

## Topic 11: 캐릭터 일관성 아키텍처 (Single Source of Truth)

### 핵심 요구사항 (사용자)

1. **output-styles와 modules의 캐릭터 정의 동일해야 함**
2. **캐릭터 간 오염 방지**: A 세션에서 B와 대화 시 A 특성이 B에 혼입되면 안 됨
3. **호출 경로 무관 일관성**: 싱글/멀티 어디서든 동일한 캐릭터성

### 제약 조건

**output-styles는 @import를 지원하지 않음**

공식 문서 확인 결과: output-style 파일은 독립적인 마크다운 파일이어야 함

### 해결책: 빌드 스크립트 기반 SSOT

**최종 아키텍처**:

```
~/.claude/
├── characters/              # 🔑 Single Source of Truth
│   ├── _TEMPLATE.md        # 캐릭터 정의 템플릿
│   ├── A.md                # 캐릭터 A 원본
│   ├── B.md                # 캐릭터 B 원본
│   └── ...
├── output-styles/           # 🔧 Generated by script
│   ├── A.md                # A 싱글 모드 (characters/A.md 기반)
│   ├── B.md                # B 싱글 모드
│   └── team.md             # 멀티 캐릭터 모드 (전체 통합)
└── modules/
    └── characters.md        # @import용 (team.md와 동일 내용)
```

### 캐릭터 격리 프로토콜

```markdown
## Character Isolation Protocol

CRITICAL: Characters must remain completely separate.

1. ONE character per response (unless @all)
2. Character switch = complete persona reset
3. NO trait bleeding between characters
4. Format responses as: "[Character]: ..."
5. When uncertain, ask: "누구로 응답할까요?"

Violation examples to AVOID:
❌ B responding with A's speech patterns
❌ Mixing expertise across characters
❌ Gradual personality drift
```

### 캐릭터 템플릿 설계

**characters/_TEMPLATE.md**:

```markdown
# Character: [Name]

## Identity
[한 줄 정체성]

## Personality
- [특성 1]
- [특성 2]
- [특성 3]

## Speech Patterns
- 자주 쓰는 표현: "[예시 1]", "[예시 2]"
- 톤: [예: 분석적, 따뜻한, 직설적]
- 말투 특징: [예: 존댓말, 반말, 격식체]

## Expertise
- [전문 영역 1]
- [전문 영역 2]

## Boundaries
- [절대 하지 않을 것]
- [유지해야 할 원칙]
```

### 합의 사항 (6/6)

| 항목 | 결정 |
|------|------|
| SSOT 위치 | `characters/` 폴더 |
| 생성 방식 | setup 스크립트가 output-styles 생성 |
| 캐릭터 격리 | 명시적 프로토콜 포함 |
| 싱글/멀티 통합 | 동일 원본에서 두 모드 생성 |

---

## 최종 팩트체크 결과 (Topic 9-11)

| 항목 | 이전 정보 | 검증 결과 | 출처 |
|------|----------|-----------|------|
| output-styles | deprecated | **✅ un-deprecated (v2.0.32)** | [CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) |
| @import 문법 | 공식 지원 | **✅ 확인** | [Claude Code Docs](https://code.claude.com/docs/en/memory) |
| 동적 라우팅 | 가능 | **✅ 스킬 시스템으로 구현 가능** | [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) |
| 시스템 프롬프트 효과 | output-styles > CLAUDE.md | **✅ 확인** | [Anthropic Docs](https://docs.anthropic.com/claude/docs/system-prompts) |
| output-styles @import | 미확인 | **❌ 지원 안 함** | [Output Styles Docs](https://code.claude.com/docs/en/output-styles) |

---

## 수정된 의사결정 사항

### Decision 1: output-styles 처리 (수정됨)

| 옵션 | 설명 |
|------|------|
| ~~A: 삭제~~ | ~~취소~~ |
| ~~B: deprecated 경고~~ | ~~취소~~ |
| **C: 유지 + 강화** | ✅ **채택** (un-deprecated 확인됨) |

### Decision 2: 캐릭터챗 도입 여부

| 옵션 | 설명 |
|------|------|
| A | 도입 안 함 |
| **B** | **선택적 확장** (templates 제공) ← 권장 |
| C | 기본 설정에 포함 |

### Decision 3: 캐릭터 정의 아키텍처

| 옵션 | 설명 |
|------|------|
| A | 각 파일에 중복 정의 |
| **B** | **SSOT** (characters/ → 빌드 → output-styles/team.md) ← 채택 |
| C | 가이드만 제공 |

---

## 구현 계획

### 폴더 구조 변경

```
template/
├── characters/              # NEW: 캐릭터 원본 (SSOT)
│   └── _TEMPLATE.md
├── output-styles/           # 유지: 싱글 캐릭터 + team.md
│   ├── _TEMPLATE.md        # 업데이트: 캐릭터 가이드 추가
│   └── team.md             # NEW: 멀티 캐릭터 모드
├── modules/
│   └── characters.md       # NEW: @import용 멀티 캐릭터
└── ...
```

### setup-claude-global.sh 수정 사항

```bash
# 캐릭터 폴더 생성
mkdir -p "$CLAUDE_DIR/characters"

# 캐릭터 템플릿 복사
cp "$SCRIPT_DIR/characters/_TEMPLATE.md" "$CLAUDE_DIR/characters/"

# (향후) 캐릭터 빌드 로직
# for char in $CLAUDE_DIR/characters/*.md; do
#   generate_output_style "$char"
# done
```

---

## Sources (Topic 9-11)

- [Claude Code CHANGELOG](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- [Output Styles Issue #10671](https://github.com/anthropics/claude-code/issues/10671)
- [Claude Code Memory Docs](https://code.claude.com/docs/en/memory)
- [Claude Code Output Styles Docs](https://code.claude.com/docs/en/output-styles)
- [Anthropic System Prompts](https://docs.anthropic.com/claude/docs/system-prompts)
- [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
