---
name: diverse-sampling

description: |
  Generate diverse responses using Verbalized Sampling (VS) technique to overcome mode collapse.
  Two modes: Mode A (Explore) produces multiple alternative outputs with a probability
  distribution and selects one by strategy; Mode B (Enhance) channels the same
  anti-mode-collapse diversity into authored prose, then sub-calls doc-concretize
  (intra-plugin) to crystallize the chosen direction into a structured document.

  Trigger when user mentions: 다양한 아이디어, 브레인스토밍, 대안 제시, 창의적 답변, VS 기법으로,
  diverse ideas, brainstorming, alternatives, verbalized sampling,
  글로 발전시켜줘, 더 구체적으로 작성해줘, enhance, 작성 다양성.

  Routing: factual questions, single-answer tasks, and code debugging fall outside both
  modes — recommend a standard response instead.
model: sonnet
allowed-tools: AskUserQuestion Skill
---

# Diverse Sampling

Generate diverse responses using Verbalized Sampling technique to overcome LLM mode collapse.

## Modes

This skill operates in two modes, both driven by the same VS anti-mode-collapse core:

| Mode | Purpose | Output |
|------|---------|--------|
| **A — Explore** | Ideation, alternatives, brainstorming (the original default behavior) | One selected alternative (or all / best) |
| **B — Enhance** | Diversity-driven *authoring* — avoid mode collapse in prose, then crystallize | A structured document authored by `doc-concretize` from the selected direction |

Mode A's Phases 1–3 are unchanged. Mode B reuses Phase 1 (diverse generation) to produce
distinct *authoring directions*, then hands the chosen direction to the intra-plugin
`doc-concretize` skill for structured authoring. Both modes share the same Use Case
Boundaries — factual, single-answer, and debugging tasks are excluded from either mode.

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match input language
  - Korean input → Korean output
  - English input → English output
  - Mixed input → follow dominant language

## Prerequisites

- Creative or open-ended query requiring diverse outputs
- "all" mode: say "전부 보여줘" or "all" to show all generated responses
- "best" mode: say "제일 나은 것" or "best" to select highest probability response
- Count: say "N개 만들어줘" to generate N responses (range: 3-10, clamping rules unchanged)
  - If N < 3, clamp to 3 with notice. If N > 10, clamp to 10 with notice. If non-numeric, ignore and use default 5.

## Invocation Detection

Detect the **mode** first (Explore vs Enhance), then the invocation type. The Explicit /
Implicit tables below govern **Mode A (Explore)**; **Mode B (Enhance)** detection follows in
its own subsection.

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
| "여러 대안" | "여러 대안을 만들어줘" |
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

### Mode B — Enhance (Requires Confirmation)

| Trigger | Example |
|---------|---------|
| "글로 발전시켜줘" | "이 초안 글로 발전시켜줘" |
| "더 구체적으로 작성해줘" | "이 아이디어 더 구체적으로 작성해줘" |
| "enhance" | "enhance this rough draft into a full section" |
| "작성 다양성" | "작성 다양성 살려서 정리해줘" |

Mode B triggers are implicit — confirm before running, since Mode B consumes more tokens
(diverse generation + doc-concretize authoring).

**Mode B Confirmation Prompt** (via AskUserQuestion):
```
작성 다양성 향상(Verbalized Sampling → doc-concretize)을 적용할까요?

- 다양한 작성 방향을 생성한 뒤 선택된 방향을 구조화 문서로 구체화합니다
- 창의·개방형 작성에 효과적이지만 토큰 소비가 높습니다

Options:
1. 적용 (Apply Enhance)
2. 일반 응답 (Standard response)
```

## Core Workflow

### Phase 0: Preparation

1. **Mode Determination**
   - Mode B trigger detected (글로 발전시켜줘 / 더 구체적으로 작성해줘 / enhance / 작성 다양성) → **Mode B (Enhance)**
   - Explore trigger or `/diverse-sampling` → **Mode A (Explore)**
   - Ambiguous (e.g. "다양하게 써줘") → ask via AskUserQuestion which mode fits

2. **Invocation Type Check**
   - Explicit trigger detected → proceed to generation (Mode A → Phase 1)
   - Implicit trigger or Mode B trigger detected → call AskUserQuestion for confirmation
   - Ambiguity resolved in step 1 → treat as the chosen mode's implicit path (confirm before running)
   - User declines → generate standard response and exit

3. **Language Detection**
   - Analyze input language
   - Select appropriate VS prompt template (EN/KO)

4. **Use Case Validation** (both modes)
   - Creative/open-ended task → proceed
   - Factual question, code debugging, single-answer task → recommend standard response
     (applies to Mode A and Mode B alike — neither runs VS generation nor the
     doc-concretize sub-call for excluded inputs)

**Quality Gate**: Mode determined + confirmation received (if implicit/Mode B) + appropriate
use case → proceed (Mode A → Phase 1; Mode B → Phase 1-B in the Mode B Branch below)

### Phase 1: VS Generation

1. **Apply VS Prompt Template** (see [reference.md](reference.md) for templates)
   - Inject user query into template
   - Request k responses with probability distribution (k = count from "N개 만들어줘", default 5)
   - Specify tail sampling (probability < 0.10)

2. **Generate Responses**
   - Model produces k `<response>` blocks
   - Each contains `<text>` and `<probability>`

3. **Parse Output**
   - Extract all response blocks
   - Parse probability values
   - **On parse failure → Fallback**

**Quality Gate**: k valid responses parsed (k = count from "N개 만들어줘", default 5) → proceed to Phase 2

### Phase 2: Selection

Apply selection strategy based on option:

| Option | Strategy | Description |
|--------|----------|-------------|
| (default) | Weighted Random | Sample from distribution proportional to probabilities |
| 전부/all | Show All | Display all 5 responses with probabilities |
| 제일 나은 것/best | Highest Probability | Select response with highest probability |

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
*{k}개 대안 중 다양성 기반 선택 · 전체 보기: "전부 보여줘"*
```

**"전부 보여줘" Output** (all responses):
```
## 생성된 대안들

| 순위 | 선호도 | 아이디어 |
|:---:|:------:|----------|
| 1 | 100% | 첫 번째 아이디어 설명 |
| 2 | 71% | 두 번째 아이디어 설명 |
| 3 | 57% | 세 번째 아이디어 설명 |
| 4 | 34% | 네 번째 아이디어 설명 |
| 5 | 23% | 다섯 번째 아이디어 설명 |

───
*다양성 기법으로 {k}개 대안 생성*
```

**"제일 나은 것" Output**:
```
**Inkwell** ★

A classic writing reference that evokes craftsmanship.

───
*{k}개 대안 중 가장 선호되는 옵션*
```

## Mode B Branch: Enhance (Authoring Diversity)

Mode B reuses VS generation to diversify the *authoring approach*, then delegates the actual
writing to `doc-concretize`. It runs after Phase 0 determines Mode B (replacing Phases 1–3).

### Phase 1-B: Diverse Direction Generation

- Apply the VS prompt template to generate k distinct **authoring directions** for the
  writing task (framing, structure, angle, tone) — not finished prose, but distinct
  approaches — each with a probability via tail sampling (same mechanism as Phase 1).
- Parse the k directions exactly as Phase 1, with the same Fallback Mechanism on parse
  failure.

### Phase 2-B: Direction Selection

- Apply the selection strategy: weighted random by default; "제일 나은 것" picks the
  highest-probability direction; "전부 보여줘" presents all k directions as a table **and then
  asks which one to author** — unlike Mode A's "Show All" (which displays and stops), Mode B
  must converge on a single direction for the doc-concretize handoff.
- The selected direction becomes the seed for authoring.

### Phase 3-B: Concretization Handoff

- Sub-call the intra-plugin **`doc-concretize`** skill (same plugin — see
  [doc-concretize](../doc-concretize/SKILL.md)) via the **Skill** tool, passing the selected
  direction as the seed/topic. doc-concretize authors the full structured document through
  its recursive-concretization workflow.
- This is a one-way ①→② handoff: diverse-sampling (① cognition — diversity generation) feeds
  doc-concretize (② output — authored markdown). diverse-sampling does **not** edit the
  produced document; doc-concretize owns authoring.
- **Output**: the structured document returned by doc-concretize, followed by a pinned
  one-line footer (mirroring Mode A's pinned footers):

```
───
*작성 다양성: {k}개 방향 중 "{selected}" 선택 → doc-concretize 구체화*
```

**Mode B Fallback**: if the doc-concretize sub-call cannot run, emit the selected direction
as a standard structured response (no sub-call) and note the fallback to the user.

## Structured Output Handling

Regardless of model: structured data (XML/JSON `<response>` blocks with `<text>` and `<probability>`) is internal processing only.
- Never expose raw XML/JSON to the user — emit converted natural language only.
- On parse failure, apply the Fallback Mechanism below.

## Fallback Mechanism

**Trigger Conditions**:
- XML parsing failure
- Fewer than expected valid responses
- Probability values not parseable

**Fallback Strategy** (cascading):
```
1. XML parse failed → retry with JSON format prompt
2. JSON parse failed → extract responses via regex pattern matching
3. All structured parsing failed → generate standard response
```

**JSON Fallback Prompt** (injected on XML failure):
```
Respond in JSON array format:
[{"text": "response text", "probability": 0.35}, ...]
```

**Final Fallback**:
```
1. Log warning (Korean): "구조화 파싱 실패. 일반 응답으로 대체되었습니다." | (English): "Structured parsing failed. Falling back to standard response."
2. Generate standard response to original query
3. Return standard response
```

## Use Case Boundaries

### Apply — Mode A (Explore)

- Brainstorming, ideation
- Creative writing (stories, poems, jokes, marketing copy)
- Alternative/option generation
- Synthetic data generation
- Dialogue simulation
- Exploring multiple perspectives

### Apply — Mode B (Enhance)

- Long-form / structured authoring where mode collapse flattens the result
  (essays, documentation, narrative sections, marketing long-form)
- Turning a chosen idea or rough draft into a fully developed document
- Open-ended authoring tasks that benefit from a diverse framing before concretization

### Exclude (Not Recommended — both modes)

- Factual questions ("What is the capital of Korea?")
- Code debugging/fixing
- Tasks with single correct answer
- Precise calculations/analysis
- Security-sensitive operations

For excluded inputs, **both Mode A and Mode B** recommend a standard response and skip VS
generation and the doc-concretize sub-call entirely.

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Implicit (Mode A) or Mode B trigger confirmation | "Apply VS technique?" / "작성 다양성 적용할까요?" |
| Skill (`doc-concretize`) | Mode B Phase 3-B — author the selected direction into a structured document | Skill tool invokes the intra-plugin `doc-concretize` skill with the selected direction as seed |

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)
- **Mode B authoring skill**: [doc-concretize](../doc-concretize/SKILL.md) (intra-plugin; sub-called in Mode B Phase 3-B)
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
*{k}개 대안 중 다양성 기반 선택 · 전체 보기: "전부 보여줘"*
```
