---
name: diverse-sampling

description: |
  Generate diverse responses using Verbalized Sampling (VS) technique to overcome mode collapse.
  Produces multiple alternative outputs with probability distribution, then selects based on strategy.

  Use when creative diversity is needed: brainstorming, ideation, alternative solutions,
  creative writing, synthetic data generation, or exploring multiple perspectives.

  Trigger when user mentions: 다양한 아이디어, 브레인스토밍, 대안 제시, 여러 관점, 창의적 답변,
  diverse ideas, brainstorming, alternatives, multiple options,
  or explicitly: "/diverse-sampling", "VS 기법으로", "verbalized sampling으로".

  Skip for: factual questions, code debugging, single correct answer tasks, precise calculations.
---

# Diverse Sampling

Generate diverse responses using Verbalized Sampling technique to overcome LLM mode collapse.

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match input language
  - Korean input → Korean output
  - English input → English output
  - Mixed input → follow dominant language

## Prerequisites

- Creative or open-ended query requiring diverse outputs
- (Optional) `--all` flag to show all generated responses
- (Optional) `--best` flag to select highest probability response

## Invocation Detection

### Explicit (Immediate Execution)

| Trigger | Example |
|---------|---------|
| `/diverse-sampling` | `/diverse-sampling 커피숍 이름 아이디어` |
| "VS 기법으로" | "VS 기법으로 마케팅 카피 만들어줘" |
| "verbalized sampling" | "verbalized sampling으로 브레인스토밍" |
| "diverse sampling으로" | "diverse sampling으로 대안 제시해줘" |

### Implicit (Requires Confirmation)

| Trigger | Example |
|---------|---------|
| "다양한 아이디어" | "다양한 아이디어 좀 내줘" |
| "브레인스토밍" | "브레인스토밍 해보자" |
| "여러 관점" | "여러 관점에서 분석해줘" |
| "alternatives" | "Give me some alternatives" |

**Confirmation Prompt** (via AskUserQuestion):
```
다양성 향상 기법(Verbalized Sampling)을 적용할까요?

- 여러 대안을 생성하여 그 중 하나를 선택합니다
- 창의적 작업에 효과적이지만 토큰 소비가 높습니다

Options:
1. 적용 (Apply VS)
2. 일반 응답 (Standard response)
```

## Core Workflow

### Phase 0: Preparation

1. **Invocation Type Check**
   - Explicit trigger detected → proceed to Phase 1
   - Implicit trigger detected → call AskUserQuestion for confirmation
   - User declines → generate standard response and exit

2. **Language Detection**
   - Analyze input language
   - Select appropriate VS prompt template (EN/KO)

3. **Use Case Validation**
   - Creative/open-ended task → proceed
   - Factual question, code debugging, single-answer task → recommend standard response

**Quality Gate**: Confirmation received (if implicit) + appropriate use case → proceed

### Phase 1: VS Generation

1. **Apply VS Prompt Template** (see [reference.md](reference.md) for templates)
   - Inject user query into template
   - Request 5 responses with probability distribution
   - Specify tail sampling (probability < 0.10)

2. **Generate Responses**
   - Model produces 5 `<response>` blocks
   - Each contains `<text>` and `<probability>`

3. **Parse Output**
   - Extract all response blocks
   - Parse probability values
   - **On parse failure → Fallback**

**Quality Gate**: 5 valid responses parsed → proceed to Phase 2

### Phase 2: Selection

Apply selection strategy based on option:

| Option | Strategy | Description |
|--------|----------|-------------|
| (default) | Weighted Random | Sample from distribution proportional to probabilities |
| `--all` | Show All | Display all 5 responses with probabilities |
| `--best` | Highest Probability | Select response with highest probability |

**Weighted Random Sampling**:
```
1. Normalize probabilities to sum to 1.0
2. Generate random value [0, 1)
3. Select response based on cumulative distribution
```

### Phase 3: Output

**Default Output** (single response):
```
**브루잉 포레스트 (Brewing Forest)**

커피가 숲처럼 천천히 우러나는 공간이라는 의미를 담았습니다.

───
*5개 대안 중 다양성 기반 선택 · 전체 보기: `--all`*
```

**--all Output** (all responses):
```
## 생성된 대안들

| 순위 | 선호도 | 아이디어 |
|:---:|:------:|----------|
| 1 | 78% | 첫 번째 아이디어 설명 |
| 2 | 68% | 두 번째 아이디어 설명 |
| 3 | 58% | 세 번째 아이디어 설명 |
| 4 | 48% | 네 번째 아이디어 설명 |
| 5 | 38% | 다섯 번째 아이디어 설명 |

───
*다양성 기법으로 5개 대안 생성*
```

**--best Output**:
```
**Inkwell** ★

A classic writing reference that evokes craftsmanship.

───
*5개 대안 중 가장 선호되는 옵션*
```

## Model Capabilities

### Extended Thinking (Opus)
- 구조화 데이터 처리를 thinking 단계에서 수행
- 출력에는 변환된 자연어만 포함
- 확률 calibration 더 정확

### Standard Mode (Sonnet)
- 명시적 지시로 구조화 데이터 은닉
- "NEVER output XML/JSON to user" 강조
- 파싱 실패 시 즉시 fallback

## Fallback Mechanism

**Trigger Conditions**:
- XML parsing failure
- Fewer than 5 valid responses
- Probability values not parseable

**Fallback Procedure**:
```
1. Log warning (Korean): "일반 응답으로 대체되었습니다." | (English): "Falling back to standard response."
2. Generate standard response to original query
3. Return standard response
```

## Use Case Boundaries

### Apply (Recommended)

- Brainstorming, ideation
- Creative writing (stories, poems, jokes, marketing copy)
- Alternative/option generation
- Synthetic data generation
- Dialogue simulation
- Exploring multiple perspectives

### Exclude (Not Recommended)

- Factual questions ("What is the capital of Korea?")
- Code debugging/fixing
- Tasks with single correct answer
- Precise calculations/analysis
- Security-sensitive operations

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Implicit trigger confirmation | "Apply VS technique?" |

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)
- **Research paper**: [arXiv:2510.01171](https://arxiv.org/abs/2510.01171)

## Quick Start

```
User: "/diverse-sampling 스타트업 이름 아이디어 좀 줘"

→ Phase 0: Explicit trigger → proceed, Korean detected
→ Phase 1: Apply Korean VS template, generate 5 responses
→ Phase 2: Weighted random sampling
→ Phase 3: Output selected response

Output:
**NexaFlow**

다음 단계로의 흐름을 의미

───
*5개 대안 중 다양성 기반 선택 · 전체 보기: `--all`*
```
