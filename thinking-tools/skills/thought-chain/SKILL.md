---
name: thought-chain

description: |
  Orchestrate thinking-tools skills into a 4-stage pipeline for comprehensive analysis.
  Chains unknown-discovery → expert-panel → doc-concretize → doc-polish
  in sequence, passing outputs between stages automatically.

  Trigger when user mentions: 종합 분석, 깊이 있는 분석, 체계적 분석 후 문서화, 전체 파이프라인,
  end-to-end 분석, full analysis pipeline, thought-chain.
allowed-tools: Skill Read AskUserQuestion
---

# Thought Chain — Skill Orchestration Pipeline

Orchestrate thinking-tools skills into an end-to-end analysis pipeline.

> **Reference files (load on demand)**: [reference.md](reference.md) (per-stage deepen prompts) · [reference/pipeline-examples.md](reference/pipeline-examples.md) (partial pipeline, vault destination question, metadata schema, output formats, quick start). Read these explicitly when the corresponding section is reached; they are not auto-loaded with SKILL.md.

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
- (Optional) `--autopilot` to skip all checkpoints and run the full pipeline unattended
- (Optional) `--auto-vault plan|session` to auto-save to vault at end (requires `--autopilot`)

**Flag validation**:
- `--auto-vault` without `--autopilot` → error: `"--auto-vault는 --autopilot과 함께만 사용할 수 있어요."`
- Unknown `--auto-vault` value → error: `"--auto-vault 값은 plan 또는 session이어야 해요."`

## Pipeline Stages

```
┌──────────────────┐   ┌──────────────┐   ┌────────────────┐   ┌────────────┐
│ unknown-discovery │──▶│ expert-panel │──▶│ doc-concretize │──▶│ doc-polish │
│  Blind Spot Scan  │   │ Expert Debate│   │  Documentation │   │  Quality QA│
└──────────────────┘   └──────────────┘   └────────────────┘   └────────────┘
       Stage 1               Stage 2            Stage 3            Stage 4
```

### Stage 1: Discovery (`unknown-discovery`)

**Input**: User's analysis target
**Output**: Discovery Report with prioritized findings (Critical/Important/Nice-to-have)
**Inter-stage handoff**: Critical + Important findings → Stage 2 panel topics

- If `--quick` flag: use `--quick` mode (5-7 questions)
- User may stop pipeline here via checkpoint

**Stage 1 empty guard**: If Stage 1 yields zero Critical findings AND zero Important findings, Stage 2 has no panel input.
```
발견된 항목이 없어 Stage 2 (Expert Panel)에 전달할 토픽이 없어요.
→ 다음으로 어떻게 진행할까요?
1. Stage 1 재실행 (다른 각도로 다시 탐색)
2. 멈추고 vault 저장 (현 결과만)
3. 그냥 멈춤
```

For **claim validation** (1:1 attacker-vs-defender), invoke `adversarial-review` as a **standalone skill** outside this pipeline. thought-chain does not embed claim-attack rounds.

### Stage 2: Expert Debate (`expert-panel`)

**Input**: Critical + Important findings from Stage 1 (Critical → primary topics, Important → secondary)
**Output**: SUMMARY.md with consensus items, dissenting views, action items
**Inter-stage handoff**: Consensus items + action items become doc-concretize input

- Expert panel composition auto-derived from finding domains
- If findings span 1-2 domains → 3 experts
- If findings span 3+ domains → 5 experts (capped at 7)
- User may stop pipeline here via checkpoint

### Stage 3: Documentation (`doc-concretize`)

**Input**: Expert panel consensus + action items + original target context
**Output**: Structured document covering analysis results
**Inter-stage handoff**: Generated document passed to doc-polish

- If `--quick` flag and document < 2000 chars: use Quick Mode
- Document structure follows expert panel topic organization

### Stage 4: Quality Assurance (`doc-polish`)

**Input**: Document from Stage 3
**Output**: Polished document with quality report

- Runs with `--fix` mode by default (auto-correct mechanical issues)
- Reports remaining Layer 2/3 issues for user review

## Pre-Pipeline Gate Check

Run once before Stage 1. Silent — never surface to user at this point.

1. Read `.vault-link` (if present): parse `vault_path`, `snapshot_export` (also honor `auto_capture` alias). `vault_linked = true` if file found, `false` otherwise.
2. If `vault_linked`: read `~/vault/{vault_path}/_index.md` (best-effort; default `import_allowed = false` on read failure). Parse `snapshot_import` → `import_allowed`.
3. Hold `{vault_linked, vault_path, snapshot_export, import_allowed}` in pipeline session memory.

This state is reused at every vault prompt. No upfront question.

## Checkpoint System

After each stage, display a progress summary and confirm continuation.
If `--autopilot` is active, skip this section and auto-select "다음 단계로".

```
───
✓ Stage {N}: {StageName} 완료 — {brief summary of results}
→ 다음으로 어떻게 진행할까요?

1. 다음 단계로 (Stage {N+1}: {NextStageName})
2. {stage-specific deepen label} — 이 단계에 머무르며 결과 심화
3. 재실행 — 이 단계를 처음부터 다시
4. 멈추고 vault 저장
5. 그냥 멈춤
```

**Stage-specific deepen labels (option 2)**:

| Stage | Label |
|-------|-------|
| unknown-discovery | 더 인터뷰 |
| expert-panel | 더 토론 |
| doc-concretize | 더 구체화 |
| doc-polish | 더 다듬기 |

**Checkpoint option semantics**:

| Option | Behavior |
|--------|----------|
| 다음 단계로 | Pass current output to next stage |
| {deepen label} | Re-invoke current stage with prior output + deepen instruction; increment `deepen_counts[stage]` |
| 재실행 | Discard current output; re-run from clean state with original input; reset `deepen_counts[stage]` to 0 |
| 멈추고 vault 저장 | Stop pipeline; run mid-stop polish if before Stage 4; trigger vault destination question |
| 그냥 멈춤 | Stop pipeline; print current output; no vault write |

**After Stage 4 (end-of-pipeline)**: trigger vault destination question directly (no checkpoint).

## Deepen Mechanics

When user picks the deepen option:

1. Increment `deepen_counts[stage]`.
2. If `deepen_counts[stage]` ≤ 3: re-invoke the current stage's skill via Skill tool with prior output as context plus a deepen instruction:
   - `unknown-discovery`: additional interview rounds on existing findings; raise depth
   - `expert-panel`: additional debate rounds; attack unresolved dissent; re-synthesize
   - `doc-concretize`: expand sections, add recursive depth one level deeper
   - `doc-polish`: stricter Layer 2/3 quality pass
3. After deepened pass, surface the same checkpoint again.

**Hard limit: 3 deepens per stage.** On the 4th attempt, show friction prompt requiring explicit confirmation.
Friction prompt text and per-stage deepen prompts: [reference.md](reference.md), [reference/pipeline-examples.md](reference/pipeline-examples.md#deepen-cap--friction-prompt)

## Mid-Stop Polish Guarantee

When "멈추고 vault 저장" is selected before Stage 4 completes:

| Stop point | Action |
|------------|--------|
| After Stage 1 | Package discovery findings as markdown → invoke `doc-polish` via Skill |
| After Stage 2 | Package consensus + dissents as markdown → invoke `doc-polish` via Skill |
| After Stage 3 | Invoke `doc-polish` on the concretized document via Skill |
| After Stage 4 | Save directly (already polished) |

**Invariant**: vault never receives a non-polished artifact.

## Vault Destination Question

Triggered after "멈추고 vault 저장" (post mini-polish) or after Stage 4 completes.
Routes: "Plan doc" → `save-session plan`; "Session note" → `save-session` (record mode); "터미널만" → terminal print; "종료" → exit.
Option visibility depends on vault gate state (`vault_linked`, `snapshot_export`, `import_allowed`).
Full option list, visibility rules, routing details, frontmatter injection:
[reference/pipeline-examples.md](reference/pipeline-examples.md#vault-destination-question)

## Autopilot Flag

`--autopilot` skips all checkpoints (auto-selects "다음 단계로"). No deepen, no re-run.
After Stage 4: end-state follows `--auto-vault` value if set; otherwise "터미널만".

`--auto-vault plan`: auto-answers "Plan doc로 vault에 저장". Falls back to terminal with
`"(vault 게이트가 닫혀 있어 터미널 출력으로 대체했어요)"` if gate closed.
`--auto-vault session`: auto-answers "Session note로 vault에 저장". Same fallback if `vault_linked = false`.

## Partial Pipeline

Use `--skip {stage}` or `--start {stage}` for subset pipelines.
Alias mapping, fallback input contracts, validation rules:
[reference/pipeline-examples.md](reference/pipeline-examples.md#partial-pipeline-reference)

## References

- **Pipeline skills**: [unknown-discovery](../unknown-discovery/SKILL.md), [expert-panel](../expert-panel/SKILL.md), [doc-concretize](../doc-concretize/SKILL.md), [doc-polish](../doc-polish/SKILL.md)
- **Standalone validation skill**: [adversarial-review](../adversarial-review/SKILL.md) (claim attack — invoked separately, NOT part of this pipeline)
- **Vault save command**: [save-session](../../../vault-bridge/commands/save-session.md) (plan and session modes)
- **Related skill**: [diverse-sampling](../diverse-sampling/SKILL.md) (not in pipeline, but can feed options into expert-panel)
- **Per-stage deepen prompts**: [reference.md](reference.md)
- **Pipeline examples, metadata schema, output formats**: [reference/pipeline-examples.md](reference/pipeline-examples.md)
