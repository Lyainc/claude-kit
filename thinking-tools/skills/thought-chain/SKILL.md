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
allowed-tools: Skill Read AskUserQuestion
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
- (Optional) `--autopilot` to skip all checkpoints and run the full pipeline unattended
- (Optional) `--auto-vault plan|session` to auto-save to vault at end (requires `--autopilot`)

**Flag validation**:
- `--auto-vault` without `--autopilot` → error: `"--auto-vault는 --autopilot과 함께만 사용할 수 있어요."`
- Unknown `--auto-vault` value → error: `"--auto-vault 값은 plan 또는 session이어야 해요."`

## Pipeline Stages

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌────────────────┐   ┌────────────┐
│ unknown-discovery │──▶│adversarial-review│──▶│ expert-panel │──▶│ doc-concretize │──▶│ doc-polish │
│  Blind Spot Scan  │   │  Claim Attack    │   │ Expert Debate│   │  Documentation │   │  Quality QA│
└──────────────────┘   └──────────────────┘   └──────────────┘   └────────────────┘   └────────────┘
       Stage 1                Stage 2               Stage 3            Stage 4             Stage 5
```

### Stage 1: Discovery (`unknown-discovery`)

**Input**: User's analysis target
**Output**: Discovery Report with prioritized findings (Critical/Important/Nice-to-have)
**Inter-stage handoff**: Critical findings → Stage 2 claims list; Important findings → Stage 3 topics

- If `--quick` flag: use `--quick` mode (5-7 questions)
- User may stop pipeline here via checkpoint

**Stage 1 empty guard**: If Stage 1 yields zero Critical findings, Stage 2 is auto-skipped.
Stage 2 only accepts Critical findings as claims (see Stage 2 Input contract below),
so Important findings cannot substitute.
```
Critical 발견이 없어 Stage 2 (Adversarial Review)를 건너뜁니다.
→ 다음으로 어떻게 진행할까요?
1. 계속 (Stage 3: Expert Panel로)
2. 멈추고 vault 저장
3. 그냥 멈춤
```

### Stage 2: Adversarial Review (`adversarial-review`)

**Input**: Critical findings from Stage 1 → converted to claims list
**Output**: Adversarial Review Report (survived/collapsed/pending per claim)
**Inter-stage handoff**: survived + pending claims become expert-panel topics; collapsed claims noted as resolved

- Each Critical finding becomes one claim (title as claim statement)
- Run with default mode (no `--quick`); Steelman each claim before attacking
- `--skip adversarial-review` flag: skip this stage entirely, pass Critical findings directly to Stage 3
- User may stop pipeline here via checkpoint

### Stage 3: Expert Debate (`expert-panel`)

**Input**: survived + pending claims from Stage 2 (or Critical/Important findings if Stage 2 skipped)
**Output**: SUMMARY.md with consensus items, dissenting views, action items
**Inter-stage handoff**: Consensus items + action items become doc-concretize input

- Expert panel composition auto-derived from finding domains
- If findings span 1-2 domains → 3 experts
- If findings span 3+ domains → 5 experts (capped at 7)
- User may stop pipeline here via checkpoint

### Stage 4: Documentation (`doc-concretize`)

**Input**: Expert panel consensus + action items + original target context
**Output**: Structured document covering analysis results
**Inter-stage handoff**: Generated document passed to doc-polish

- If `--quick` flag and document < 2000 chars: use Quick Mode
- Document structure follows expert panel topic organization

### Stage 5: Quality Assurance (`doc-polish`)

**Input**: Document from Stage 4
**Output**: Polished document with quality report
**Final**: Pipeline complete

- Runs with `--fix` mode by default (auto-correct mechanical issues)
- Reports remaining Layer 2/3 issues for user review

## Pre-Pipeline Gate Check

Run once before Stage 1. Silent — never surface to user at this point.

1. Read `.vault-link` (if present):
   - Parse `vault_path`, `snapshot_export` (also honor `auto_capture` alias)
   - `vault_linked = true` if file found, `false` otherwise
2. If `vault_linked`:
   - Read `~/vault/{vault_path}/_index.md` (best-effort; default `import_allowed = false` on read failure)
   - Parse `snapshot_import` (also honor `auto_capture` alias) → `import_allowed`
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
| adversarial-review | 더 공격 |
| expert-panel | 더 토론 |
| doc-concretize | 더 구체화 |
| doc-polish | 더 다듬기 |

**Checkpoint option semantics**:

| Option | Behavior |
|--------|----------|
| 다음 단계로 | Pass current output to next stage. |
| {deepen label} | Re-invoke current stage with prior output + deepen instruction. Increment `deepen_counts[stage]`. |
| 재실행 | Discard current stage output. Re-run stage from clean state with original input. 재실행 선택 시 해당 stage의 deepen_counts는 0으로 초기화. |
| 멈추고 vault 저장 | Stop pipeline. Run mid-stop polish if before Stage 4. Trigger vault destination question. |
| 그냥 멈춤 | Stop pipeline. Print current output to terminal. No vault write. |

**After Stage 4 (end-of-pipeline)**: trigger vault destination question directly (no checkpoint).

## Deepen Mechanics

When the user picks the deepen option:

1. Increment `deepen_counts[stage]`.
2. If `deepen_counts[stage]` ≤ 3: re-invoke the current stage's skill via Skill tool, passing the prior output as context plus a deepen instruction:
   - `unknown-discovery`: additional interview rounds on existing findings; raise depth
   - `expert-panel`: additional debate rounds; attack unresolved dissent; re-synthesize
   - `doc-concretize`: expand sections, add recursive depth one level deeper
   - `doc-polish`: stricter Layer 2/3 quality pass
3. After the deepened pass, surface the same checkpoint again.

**Deepen cap (hard limit: 3 per stage)**. On the 4th attempt, replace the standard checkpoint with a friction prompt:

```
이 단계에서 이미 3번 심화했어요. 결과가 충분하지 않다면 재실행이 나을 수도 있어요.

1. 그래도 한 번 더 (강제 deepen, cap 해제)
2. 다음 단계로
3. 재실행
4. 멈추고 vault 저장
5. 그냥 멈춤
```

Forcing past the cap (option 1) is allowed but requires explicit selection.

## Mid-Stop Polish Guarantee

When "멈추고 vault 저장" is selected before Stage 4 completes:

| Stop point | Action |
|------------|--------|
| After Stage 1 | Package discovery findings as a markdown document → invoke `doc-polish` via Skill |
| After Stage 2 | Package adversarial review report as a markdown document → invoke `doc-polish` via Skill |
| After Stage 3 | Package consensus + dissents as a markdown document → invoke `doc-polish` via Skill |
| After Stage 4 | Invoke `doc-polish` on the concretized document via Skill |
| After Stage 5 | Save directly (already polished) |

**Invariant**: vault never receives a non-polished artifact.

## Vault Destination Question

Surfaced after "멈추고 vault 저장" (post mini-polish) OR after Stage 4 completes.

If `--autopilot` with `--auto-vault` is active, skip this question and route per the flag value.

**Option visibility rules** (based on gate state from Pre-Pipeline Gate Check):

| Gate state | Plan doc option | Session note option |
|------------|-----------------|---------------------|
| `vault_linked = false` | Hidden | Hidden |
| `vault_linked = true`, `snapshot_export = false` | Hidden | Visible |
| `vault_linked = true`, `snapshot_export = true`, `import_allowed = false` | Visible (with warning) | Visible |
| Both gates open | Visible (recommended) | Visible |

**When options are hidden** (vault_linked = false), append hint:
```
vault 저장을 원하시면 먼저 `/vault-link`로 프로젝트를 바인딩하세요.
Plan doc 저장에는 추가로 `.vault-link`의 `snapshot_export: true` 및
vault `_index.md`의 `snapshot_import: true`가 필요해요.
```

**Question options** (show applicable subset):
```
분석 결과를 어떻게 저장할까요?

1. 터미널만 — 출력만, vault에 남기지 않음 (기본)
2. Plan doc로 vault에 저장   [conditional]
3. Session note로 vault에 저장  [conditional]
4. 종료 — 출력 없이 끝
```

**Routing**:
- "Plan doc로 vault에 저장" → invoke `vault-bridge:save-session` with argument `plan` (type:plan override, skip mode tier routing). Pass polished document + `thought_chain:` frontmatter metadata in the invocation context.
- "Session note로 vault에 저장" → invoke `vault-bridge:save-session` (record mode). Embed polished document in session body.
- "터미널만" → print full polished document to terminal.
- "종료" → no output, exit cleanly.

**Frontmatter injection**: save-session 호출 시 문서 본문 맨 앞에 YAML frontmatter 블록 전체(--- 구분자 포함)를 직접 작성해서 넘길 것. save-session은 이를 그대로 파일 frontmatter로 사용함.

## Autopilot Flag

`--autopilot` skips all checkpoints:
- Every checkpoint auto-selects "다음 단계로".
- No deepen, no re-run.
- After Stage 4: end-state follows `--auto-vault` value if set; otherwise "터미널만".

`--auto-vault plan`:
- End-of-pipeline auto-answers "Plan doc로 vault에 저장".
- If gate closed at end (vault_linked=false OR snapshot_export=false OR gate check fails): fall back to terminal output + single warning line: `"(vault 게이트가 닫혀 있어 터미널 출력으로 대체했어요)"`

`--auto-vault session`:
- End-of-pipeline auto-answers "Session note로 vault에 저장".
- If `vault_linked = false`: fall back to terminal with warning. `"(vault 게이트가 닫혀 있어 터미널 출력으로 대체했어요)"` (plan과 동일 문구 사용)

## Metadata Aggregation

Track throughout the pipeline. Include in vault save frontmatter when writing to vault.

**Fields collected**:

| Field | Collection point |
|-------|-----------------|
| `stages_run` | Append stage name on each stage completion |
| `deepen_counts` | Increment per deepen invocation, keyed by stage name |
| `stopped_at` | Set to last completed stage name (or "polish" for full pipeline) |
| `quality_score` | Extract from doc-polish quality report (integer) |
| `tags` | Auto-extract from discovery domains + panel expert specializations; deduplicate; prepend "thought-chain" |

**Frontmatter block** (injected when saving to vault):

```yaml
thought_chain:
  stages_run: [discovery, adversarial-review, panel, concretize, polish]
  deepen_counts:
    discovery: 2
    adversarial-review: 0
    panel: 1
    concretize: 0
    polish: 0
  stopped_at: polish
  quality_score: 92
```

## Partial Pipeline

Users can run subset pipelines:

| Command | Pipeline |
|---------|----------|
| `--skip adversarial-review` | unknown-discovery → expert-panel → doc-concretize → doc-polish |
| `--skip panel` | unknown-discovery → adversarial-review → doc-concretize → doc-polish |
| `--start adversarial-review` | adversarial-review → expert-panel → doc-concretize → doc-polish (requires existing Critical claims) |
| `--start panel` | expert-panel → doc-concretize → doc-polish (requires existing findings) |
| `--start concretize` | doc-concretize → doc-polish (requires existing input) |
| `--start polish` | doc-polish only (requires existing document) |

`--skip discovery` is not supported: adversarial-review consumes Critical findings
produced by discovery, so the chain has no claim source without it. To enter at
adversarial-review with pre-existing claims, use `--start adversarial-review`.

**Fallback input contracts (when an upstream stage is skipped)**:

| Downstream stage | Normal input | Fallback input when prior stage skipped |
|------------------|-------------|----------------------------------------|
| doc-concretize (with `--skip panel`) | panel consensus + action items | adversarial-review report: survived claims → consensus, pending claims → open items, collapsed claims → "considered alternatives" |
| expert-panel (with `--skip adversarial-review`) | survived + pending claims from Stage 2 | discovery findings directly (Critical → topics, Important → secondary topics) |

**Alias mapping**: `discovery` = unknown-discovery, `adversarial-review` = adversarial-review, `panel` = expert-panel, `concretize` = doc-concretize, `polish` = doc-polish

**Validation**: Invalid stage name in `--skip`/`--start` → warn "Unknown stage: {name}. Valid: discovery, adversarial-review, panel, concretize, polish." and ignore the flag.

## Inter-Skill Data Flow

Each stage produces a conceptual inter-stage handoff (managed as natural language internally, not literal JSON):

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
| AskUserQuestion | Checkpoint confirmations, vault destination question | "다음으로 어떻게 진행할까요?" |
| Read | Pre-pipeline gate check (`.vault-link`, vault `_index.md`) | Silent gate state load |
| Skill | Stage invocations, deepen re-invocations, mini-polish pass, vault save dispatch | invoke `vault-bridge:save-session` with argument `plan` |

Each stage uses its own skill's tool set internally. Vault writes are delegated entirely to `save-session`.

## Output Format

### Final Output (all stages complete, terminal only)

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
*Thought Chain 완료 · 5단계 파이프라인*
```

When the user picks a vault save destination, `save-session` handles file creation. The polished document is passed as the body, and the `thought_chain:` frontmatter metadata block is included in the invocation context for embedding in the saved file.

## References

- **Pipeline skills**: [unknown-discovery](../unknown-discovery/SKILL.md), [adversarial-review](../adversarial-review/SKILL.md), [expert-panel](../expert-panel/SKILL.md), [doc-concretize](../doc-concretize/SKILL.md), [doc-polish](../doc-polish/SKILL.md)
- **Vault save command**: [save-session](../../../vault-bridge/commands/save-session.md) (routed for both plan and session destinations; `plan` argument overrides type)
- **Related skill**: [diverse-sampling](../diverse-sampling/SKILL.md) (not in pipeline, but can feed options into expert-panel)
- **Design**: [thought-chain-checkpoint-vault-integration.md](../../../docs/design/thought-chain-checkpoint-vault-integration.md)

## Quick Start

```
User: "새 결제 시스템 도입안을 종합 분석해줘"

→ Gate Check: .vault-link 상태 확인 (silent)
→ Stage 1 (Discovery): 블라인드스팟 인터뷰 → Critical 2건, Important 4건
→ Checkpoint: "다음으로 어떻게 진행할까요?" → 다음 단계로
→ Stage 2 (Adversarial Review): Critical 2건 claim 변환 → 공격·방어 → survived 1건, pending 1건
→ Checkpoint: "다음으로 어떻게 진행할까요?" → 다음 단계로
→ Stage 3 (Expert Panel): 보안/성능/UX 전문가 토론 → 합의 3건, 보류 1건
→ Checkpoint: "다음으로 어떻게 진행할까요?" → 더 토론 → 심화 후 → 다음 단계로
→ Stage 4 (Doc-Concretize): 분석 결과 문서화 (4개 섹션)
→ Stage 5 (Doc-Polish): 품질 검사 + 자동 수정 (score: 91)
→ Vault Destination: "Plan doc로 vault에 저장" → save-session plan 호출
→ Output: vault에 plan-YYYY-MM-DD-결제시스템-도입안.md 저장

───
*Thought Chain 완료 · 5단계 파이프라인 (panel 1회 심화)*
```
