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

  Routing: factual questions, single-answer tasks, and code/query work (debugging OR
  enhancement) fall outside both modes — Mode B authors prose, not code — so recommend a
  standard response instead. For plain concretization without diverse framing, use
  doc-concretize directly; Mode B is for when multiple authoring directions should be
  explored first.
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

**Confirmation Prompt**: fire the **Mode A** prompt (via AskUserQuestion) — see
[reference.md → Confirmation Prompts](reference.md#confirmation-prompts).

### Mode B — Enhance (Requires Confirmation)

| Trigger | Example |
|---------|---------|
| "글로 발전시켜줘" | "이 초안 글로 발전시켜줘" |
| "더 구체적으로 작성해줘" | "이 아이디어 더 구체적으로 작성해줘" |
| "enhance" | "enhance this rough draft into a full section" — but a code target ("이 쿼리 enhance해줘") routes to Exclude, not Mode B |
| "작성 다양성" | "작성 다양성 살려서 정리해줘" |

Mode B triggers are implicit — confirm before running, since Mode B consumes more tokens
(diverse generation + doc-concretize authoring).

> **On the broad `enhance` trigger**: `enhance` is a common English verb, so it can match
> code/structure requests too. This is safe **by design** — Mode B has no explicit
> immediate-execution path, so every match is confirmation-gated, and Phase 0's Use Case
> Validation routes clear code targets to a standard response *before* any prompt. A broad
> match therefore costs at most a decline-able confirmation, never a wrong action. The
> `enhance` trigger is intentional (required by the Mode B spec); the implicit gating is the
> safeguard that makes its breadth harmless.

**Mode B Confirmation Prompt** and **Mode Disambiguation Prompt** (for ambiguous input like
"다양하게 써줘" — its pick resolves the mode AND doubles as confirmation, so Phase 0 step 4 does
not prompt again): see [reference.md → Confirmation Prompts](reference.md#confirmation-prompts).

## Core Workflow

### Phase 0: Preparation

1. **Mode Determination**
   - Mode B trigger detected (글로 발전시켜줘 / 더 구체적으로 작성해줘 / enhance / 작성 다양성) → **Mode B (Enhance)**
   - Explore trigger or `/diverse-sampling` → **Mode A (Explore)**
   - Ambiguous (e.g. "다양하게 써줘") → ask via the **Mode Disambiguation Prompt** (above) — a
     single AskUserQuestion offering Mode A vs Mode B that also states Mode B's higher token
     cost. The user's pick resolves the mode **and doubles as confirmation** — do not prompt
     again in step 4.

2. **Language Detection**
   - Analyze input language
   - Select appropriate VS prompt template (EN/KO)

3. **Use Case Validation** (both modes — runs BEFORE confirmation)
   - Creative/open-ended task → proceed
   - Factual question, code debugging/enhancement, single-answer task → recommend a standard
     response **immediately, with no confirmation prompt** (applies to Mode A and Mode B alike
     — neither runs VS generation nor the doc-concretize sub-call for excluded inputs).
     Gating here, before step 4, means an excluded input never triggers a wasted confirmation.
   - Ambiguous target type (README, JSON/SQL schema, outline — prose or structure?) → do NOT
     auto-exclude; let step 4's confirmation prompt disambiguate (Mode B = prose authoring; if
     the user wants structural/code edits instead, they decline → standard response)

4. **Invocation Type Check / Confirmation**
   - Explicit Mode A trigger (`/diverse-sampling`, "VS 기법으로", …) → proceed to Phase 1
   - Implicit Mode A trigger → call AskUserQuestion for confirmation
   - Mode B trigger → call AskUserQuestion for Mode B confirmation
   - Mode already resolved via step 1's disambiguation question → already confirmed; proceed
     with no second prompt
   - User declines any confirmation → generate standard response and exit

**Quality Gate**: Mode determined + appropriate use case (validated before asking) +
confirmation received (if implicit/Mode B) → proceed (Mode A → Phase 1; Mode B → Phase 1-B
in the Mode B Branch below)

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
  - **Template adaptation**: reuse the Phase 1 VS template (see [reference.md](reference.md)),
    but instruct each `<text>` to hold a *one-paragraph approach/outline* (framing + section
    skeleton), not a finished answer. Probability and tail-sampling mechanics are unchanged.
  - **k**: same count rule as Mode A ("N개 만들어줘" → default 5, range 3–10).
- Parse the k directions exactly as Phase 1, with the same Fallback Mechanism on parse
  failure.

### Phase 2-B: Direction Selection

- Apply the selection strategy: weighted random by default; "제일 나은 것" picks the
  highest-probability direction; "전부 보여줘" (or the Mode B confirmation's "방향 직접 선택"
  option) presents all k directions as a table **and then asks which one to author** — unlike
  Mode A's "Show All" (which displays and stops), Mode B must converge on a single direction
  for the doc-concretize handoff.

  **Direction-pick prompt** (after "전부 보여줘", via AskUserQuestion):
```
어느 방향으로 작성할까요?

1. {direction 1 한 줄 요약}
2. {direction 2 한 줄 요약}
... ({k}개 방향)
```
- The selected direction becomes the seed for authoring.

### Phase 3-B: Concretization Handoff

- Sub-call the intra-plugin **`doc-concretize`** skill (same plugin — see
  [doc-concretize](../doc-concretize/SKILL.md)) via the **Skill** tool. Pass the selected
  direction's outline text as doc-concretize's input — its Prerequisites accept an "abstract
  concept or idea to concretize" as free-form text (plain text, ≤1 paragraph; optionally
  append a format/structure hint). doc-concretize then authors the full structured document
  through its recursive-concretization workflow.
- This is a one-way ①→② handoff: diverse-sampling (① cognition — diversity generation) feeds
  doc-concretize (② output — authored markdown). diverse-sampling does **not** edit the
  produced document; doc-concretize owns authoring.
- **Output**: the structured document returned by doc-concretize, followed by a pinned
  one-line footer (mirroring Mode A's pinned footers; abbreviate `{selected}` to its first
  phrase or ~15–20 chars (Korean) with an ellipsis — a word/phrase boundary, not a hard char
  cut, so Korean text is not split mid-morpheme):

```
───
*작성 다양성: {k}개 방향 중 "{selected}" 선택 → doc-concretize 구체화*
```

**Mode B Fallback**: if the doc-concretize sub-call cannot run (e.g. Skill 도구 에러 또는
doc-concretize 미설치 시), emit the selected direction as a standard structured response
(no sub-call) and note the fallback to the user.

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
- Code/query/logic enhancement or optimization (e.g. "이 쿼리 enhance해줘") — Mode B authors
  prose, not code, so a bare "enhance" on a code target routes here
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
