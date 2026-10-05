---
name: diverse-sampling

description: |
  Generate diverse prose with Verbalized Sampling: explore alternatives or enhance a chosen
  direction through doc-concretize only when alternative creative directions are requested.
  Plain expansion or structuring goes directly to doc-concretize or ordinary editing; not for
  factual, single-answer, or code/query work.

  Trigger when user mentions: 다양한 아이디어, 브레인스토밍, 대안 제시, 창의적 답변, VS 기법으로,
  diverse ideas, brainstorming, alternatives, verbalized sampling,
  작성 다양성, 여러 방향으로 글을 발전시켜줘.
allowed-tools: AskUserQuestion Skill Read
---

# Diverse Sampling

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Generate diverse responses with Verbalized Sampling (VS) to overcome LLM mode collapse.
Plain expansion or structuring routes to `doc-concretize` or ordinary editing.

- **Mode A (Explore)**: ideation/alternatives; output is one selected alternative (or all / best).
- **Mode B (Enhance)**: diverse authoring directions, then the chosen one is authored by
  `doc-concretize`.

## Language Behavior and Options

Output MUST match the input language (mixed: dominant language). Options: "전부 보여줘"/all,
"제일 나은 것"/best, "N개 만들어줘" (clamped to 3-10 with a notice; non-numeric ignored; default 5).

## Invocation Detection

Detect the **mode** first, then the invocation type.

- **Mode A explicit (run immediately)**: `/diverse-sampling`, "VS 기법으로", "verbalized
  sampling", "diverse sampling으로".
- **Mode A implicit (confirm)**: "다양한 아이디어", "브레인스토밍", "여러 대안", "alternatives".
  Fire the Mode A prompt via AskUserQuestion ([reference.md → Confirmation Prompts](reference.md#confirmation-prompts)).
- **Mode B (confirm)**: the user requests several creative authoring directions before expanding
  one ("여러 방향으로 글을 발전시켜줘", "explore alternative angles, then expand one"). A bare
  "enhance", "글로 발전시켜줘", or "더 구체적으로 작성해줘" does not: route new-document authoring
  to doc-concretize and existing-document rewrites to ordinary editing.
- **Ambiguous** ("다양하게 써줘"): fire the **Mode Disambiguation Prompt** (same reference
  section); its pick resolves the mode AND confirms, so Phase 0 step 4 does not prompt again.

## Core Workflow

### Phase 0: Preparation

1. **Mode**: alternatives then expansion of one → B; Explore trigger or `/diverse-sampling` → A;
   plain expansion/rewriting without alternatives → exit to ordinary editing or doc-concretize
   with no VS confirmation; ambiguous → the disambiguation AskUserQuestion (Mode A vs B, stating
   Mode B's higher token cost).
2. **Language**: select the EN/KO VS template.
3. **Use Case Validation** (both modes, BEFORE confirmation): creative/open-ended → proceed.
   Factual question, code debugging/enhancement, or single-answer task → recommend a standard
   response **immediately, with no confirmation prompt** (no VS generation or doc-concretize
   sub-call, in either mode). README, schema or outline edits without a request for creative
   alternatives → ordinary editing. Ambiguity about the edit does not establish a need for VS; clarify
   only what materially changes the requested edit, without a Mode B confirmation.
4. **Confirmation**: explicit Mode A → Phase 1; implicit Mode A or Mode B → AskUserQuestion; mode
   already resolved by disambiguation → no second prompt; user declines → standard response, exit.

**Quality Gate**: mode determined + appropriate use case + confirmation (if implicit/Mode B)
→ Mode A: Phase 1; Mode B: Phase 1-B.

### Phase 1: VS Generation

Apply the VS template ([reference.md](reference.md) → VS Prompt Templates): inject the query,
request k responses (k = "N개" count, default 5) each with `<text>` and `<probability>`, with
tail sampling (probability < 0.10). Parse all blocks; **on parse failure → Fallback Mechanism.** 
**Quality Gate**: k valid responses parsed → Phase 2.

### Phase 2: Selection

Default: weighted random (normalize probabilities to 1.0, draw [0, 1), pick by cumulative
distribution). "전부/all": display all k responses (default 5) with probabilities. "제일 나은 것/best": the
highest-probability response.

### Phase 3: Output

Natural language only, ending with a pinned footer ([examples](reference.md#output-examples-mode-a)): default
`*{k}개 대안 중 다양성 기반 선택 · 전체 보기: "전부 보여줘"*`; "전부 보여줘" (a `## 생성된 대안들`
table of 순위 | 선호도 | 아이디어) `*다양성 기법으로 {k}개 대안 생성*`; "제일 나은 것" (top response
marked ★) `*{k}개 대안 중 가장 선호되는 옵션*`. Each footer follows a `───` line.

## Mode B Branch: Enhance (Authoring Diversity)

### Phase 1-B: Diverse Direction Generation

Apply the VS template to generate k distinct **authoring directions** (framing, structure,
angle, tone), each `<text>` a one-paragraph approach/outline, not finished prose. Probability,
tail sampling, k, parsing, and Fallback are as in Phase 1.

### Phase 2-B: Direction Selection

Same strategies as Phase 2. "전부 보여줘" (or the confirmation's "방향 직접 선택" option) shows all
k directions as a table **and then asks which one to author** via AskUserQuestion ("어느 방향으로
작성할까요?", numbered one-line summaries; [reference.md](reference.md#output-examples-mode-a)),
because Mode B must converge on a single direction to seed authoring.

### Phase 3-B: Concretization Handoff

Sub-call the intra-plugin **`doc-concretize`** skill ([doc-concretize](../doc-concretize/SKILL.md))
via the **Skill** tool with the selected direction's outline as free-form input (plain text, at
most one paragraph; optionally a format hint). One-way handoff: diverse-sampling does **not**
edit the produced document; doc-concretize owns authoring. Output the returned document, then a
pinned footer (abbreviate `{selected}` to ~15-20 Korean chars at a word boundary, with an ellipsis):

```
───
*작성 다양성: {k}개 방향 중 "{selected}" 선택 → doc-concretize 구체화*
```

**Mode B Fallback**: if the doc-concretize sub-call cannot run (Skill error or not installed),
emit the selected direction as a standard structured response and tell the user.

## Fallback Mechanism

XML/JSON `<response>` blocks are internal only, in every phase and mode: never show raw XML/JSON.

On XML parse failure, too few valid responses, or unparseable probabilities: retry with a
JSON-format prompt, then regex extraction, then log the warning (Korean: "구조화 파싱 실패. 일반
응답으로 대체되었습니다." / English: "Structured parsing failed. Falling back to standard
response.") and return a standard response to the original query. Before retrying with JSON, read
[reference.md → Fallback Procedure](reference.md#fallback-procedure): it holds the exact JSON-format prompt.

## Use Case Boundaries

Apply: creative/open-ended work ([lists](reference.md#use-case-lists)). Exclude in both modes: factual questions,
code debugging/fixing, code/query/logic enhancement or optimization ("이 쿼리 enhance해줘"; Mode B authors prose),
single-answer tasks, precise calculations/analysis, security-sensitive operations. Excluded inputs
get a standard response and skip VS generation and the doc-concretize sub-call.

Tools: AskUserQuestion for every prompt; Skill (`doc-concretize`) in Phase 3-B; Read for reference.md.

## References

See [reference.md](reference.md), [examples.md](examples.md); paper arXiv:2510.01171.
