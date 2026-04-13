---
name: thought-chain

description: |
  Orchestrate thinking-tools skills into a pipeline for comprehensive analysis.
  Chains multiple skills (unknown-discovery → expert-panel → doc-concretize → doc-polish)
  in sequence, passing outputs between stages automatically.

  Use when a topic requires end-to-end deep analysis: discover blind spots,
  debate with experts, then produce polished documentation.

  Trigger when user mentions: 종합 분석, 전체 파이프라인, 깊이 있는 분석, end-to-end 분석,
  체계적 분석 후 문서화, 완전한 검토, full analysis pipeline,
  or requests: "이 주제를 처음부터 끝까지 분석해줘", "블라인드스팟 찾고 전문가 토론 후 문서화해줘",
  "종합적으로 분석하고 결과를 문서로 만들어줘".

  Skip for: single-skill tasks, quick questions, already-structured analysis.
allowed-tools: Skill Read Write AskUserQuestion
---

# Thought Chain — Skill Orchestration Pipeline

Orchestrate thinking-tools skills into an end-to-end analysis pipeline.

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match input language
  - Korean input → Korean output
  - English input → English output

## Prerequisites

- Analysis target (project/proposal/decision/strategy)
- (Optional) `--skip {skill}` to skip specific pipeline stages
- (Optional) `--start {skill}` to begin from a specific stage (uses existing inputs)
- (Optional) `--quick` to use quick modes where available

## Pipeline Stages

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐     ┌────────────┐
│ unknown-discovery│ ──▶ │ expert-panel │ ──▶ │ doc-concretize │ ──▶ │ doc-polish │
│  Blind Spot Scan │     │ Expert Debate│     │  Documentation │     │  Quality QA│
└─────────────────┘     └──────────────┘     └────────────────┘     └────────────┘
      Stage 1                Stage 2              Stage 3              Stage 4
```

### Stage 1: Discovery (`unknown-discovery`)

**Input**: User's analysis target
**Output**: Discovery Report with prioritized findings (Critical/Important/Nice-to-have)
**Handoff**: Critical and Important findings become expert-panel topics

- If `--quick` flag: use `--quick` mode (5-7 questions)
- User may stop pipeline here via checkpoint confirmation

### Stage 2: Expert Debate (`expert-panel`)

**Input**: Critical/Important findings from Stage 1
**Output**: SUMMARY.md with consensus items, dissenting views, action items
**Handoff**: Consensus items + action items become doc-concretize input

- Expert panel composition auto-derived from finding domains
- If findings span 1-2 domains → 3 experts
- If findings span 3+ domains → 5 experts (capped at 7)
- User may stop pipeline here via checkpoint confirmation

### Stage 3: Documentation (`doc-concretize`)

**Input**: Expert panel consensus + action items + original target context
**Output**: Structured document covering analysis results
**Handoff**: Generated document passed to doc-polish

- If `--quick` flag and document < 2000 chars: use Quick Mode
- Document structure follows expert panel topic organization

### Stage 4: Quality Assurance (`doc-polish`)

**Input**: Document from Stage 3
**Output**: Polished document with quality report
**Final**: Pipeline complete

- Runs with `--fix` mode by default (auto-correct mechanical issues)
- Reports remaining Layer 2/3 issues for user review

## Checkpoint System

After each stage, display progress and confirm continuation:

```
───
✓ Stage 1: Discovery 완료 — Critical 2건, Important 3건 발견
→ Stage 2: Expert Panel 진행할까요?

Options:
1. 계속 (Continue to next stage)
2. 이 단계 결과만 사용 (Stop here)
3. 이 단계 다시 실행 (Re-run current stage)
```

## Partial Pipeline

Users can run subset pipelines:

| Command | Pipeline |
|---------|----------|
| `--skip discovery` | expert-panel → doc-concretize → doc-polish |
| `--skip panel` | unknown-discovery → doc-concretize → doc-polish |
| `--start concretize` | doc-concretize → doc-polish (requires existing input) |
| `--start polish` | doc-polish only (requires existing document) |

**Alias mapping**: `discovery` = unknown-discovery, `panel` = expert-panel, `concretize` = doc-concretize, `polish` = doc-polish

**Validation**: Invalid stage name in `--skip`/`--start` → warn "Unknown stage: {name}. Valid: discovery, panel, concretize, polish." and ignore the flag.

## Inter-Skill Data Flow

Each stage produces a conceptual handoff (managed as natural language internally, not literal JSON):

```json
// Conceptual schema — not a literal output format
{
  "stage": "discovery",
  "findings": [...],
  "metadata": { "depth": "72%", "questions": 14 },
  "next_stage_input": { "topics": [...], "experts_suggested": [...] }
}
```

Data flow is managed internally — users see natural language summaries at checkpoints.

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Checkpoint confirmations, stage-specific questions | "Continue to Stage 2?" |

Each stage uses its own skill's tool set internally.

## Output Format

### Final Output (all stages complete)
```
# Thought Chain Analysis — {target}

## Pipeline Summary
- Discovery: {N} findings ({critical} Critical, {important} Important)
- Expert Panel: {topics} topics discussed, {consensus} consensus reached
- Document: {sections} sections, {chars} characters
- Polish: Quality score {score}, {fixes} auto-fixed

## Document
{polished document content}

───
*Thought Chain 완료 · 4단계 파이프라인 · {total_time}*
```

## References

- **Pipeline skills**: [unknown-discovery](../unknown-discovery/SKILL.md), [expert-panel](../expert-panel/SKILL.md), [doc-concretize](../doc-concretize/SKILL.md), [doc-polish](../doc-polish/SKILL.md)
- **Related skill**: [diverse-sampling](../diverse-sampling/SKILL.md) (not in pipeline, but can feed options into expert-panel)

## Quick Start

```
User: "새 결제 시스템 도입안을 종합 분석해줘"

→ Stage 1 (Discovery): 블라인드스팟 인터뷰 → Critical 2건, Important 4건
→ Checkpoint: "Stage 2 진행할까요?" → 계속
→ Stage 2 (Expert Panel): 보안/성능/UX 전문가 토론 → 합의 3건, 보류 1건
→ Checkpoint: "Stage 3 진행할까요?" → 계속
→ Stage 3 (Doc-Concretize): 분석 결과 문서화 (4개 섹션)
→ Stage 4 (Doc-Polish): 품질 검사 + 자동 수정
→ Output: 완성된 분석 문서

───
*Thought Chain 완료 · 4단계 파이프라인*
```
