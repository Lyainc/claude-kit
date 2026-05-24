# Thought Chain — Pipeline Examples & Reference

Detailed reference for partial pipelines, metadata aggregation, inter-skill data flow, and output formats.
See the main [SKILL.md](../SKILL.md) for the core 4-stage workflow.

---

## Deepen Cap — Friction Prompt

When `deepen_counts[stage]` reaches 4 (hard limit exceeded), replace the standard checkpoint with:

```
이 단계에서 이미 3번 심화했어요. 결과가 충분하지 않다면 재실행이 나을 수도 있어요.

1. 그래도 한 번 더 (강제 deepen, cap 해제)
2. 다음 단계로
3. 재실행
4. 멈추고 vault 저장
5. 그냥 멈춤
```

Forcing past the cap (option 1) is allowed but requires explicit selection. After selection, increment `deepen_counts[stage]` and surface the same checkpoint again.

---

## Vault Destination Question

Triggered after "멈추고 vault 저장" (post mini-polish) or after Stage 3 completes.
If `--autopilot` with `--auto-vault` is active, skip and route per the flag value.

**Option visibility rules** (based on gate state from Pre-Pipeline Gate Check):

| Gate state | Plan doc option | Session note option |
|------------|-----------------|---------------------|
| `vault_linked = false` | Hidden | Hidden |
| `vault_linked = true`, `snapshot_export = false` | Hidden | Visible |
| `vault_linked = true`, `snapshot_export = true`, `import_allowed = false` | Visible (with warning) | Visible |
| Both gates open | Visible (recommended) | Visible |

When all vault options are hidden (`vault_linked = false`), append hint:
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
- "Plan doc로 vault에 저장" → invoke `vault-bridge:save-session` with argument `plan` (type:plan override, skip mode tier routing); pass polished document + `thought_chain:` frontmatter metadata in the invocation context
- "Session note로 vault에 저장" → invoke `vault-bridge:save-session` (record mode); embed polished document in session body
- "터미널만" → print full polished document to terminal
- "종료" → no output, exit cleanly

**Frontmatter injection**: save-session 호출 시 문서 본문 맨 앞에 YAML frontmatter 블록 전체(--- 구분자 포함)를 직접 작성해서 넘길 것. save-session은 이를 그대로 파일 frontmatter로 사용함.

---

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
  stages_run: [discovery, panel, concretize, polish]
  deepen_counts:
    discovery: 2
    panel: 1
    concretize: 0
    polish: 0
  stopped_at: polish
  quality_score: 92
```

---

## Partial Pipeline Reference

**Commands**:

| Command | Resulting Pipeline |
|---------|--------------------|
| `--skip discovery` | expert-panel → doc-concretize → doc-polish (requires existing topics/findings) |
| `--skip panel` | unknown-discovery → doc-concretize → doc-polish (findings used directly as doc input) |
| `--start panel` | expert-panel → doc-concretize → doc-polish (requires existing findings) |
| `--start concretize` | doc-concretize → doc-polish (requires existing input) |
| `--start polish` | doc-polish only (requires existing document) |

**Fallback input contracts** (when an upstream stage is skipped):

| Downstream stage | Normal input | Fallback input when prior stage skipped |
|------------------|-------------|----------------------------------------|
| doc-concretize (with `--skip panel`) | panel consensus + action items | discovery findings directly: Critical → primary sections, Important → secondary, Nice-to-have → "considered alternatives" |
| expert-panel (with `--start panel`) | discovery findings | user-provided topics list (free-form, no Stage 1 metadata) |

**Alias mapping**: `discovery` = unknown-discovery, `panel` = expert-panel, `concretize` = doc-concretize, `polish` = doc-polish.

**Validation**: Invalid stage name in `--skip`/`--start` → warn "Unknown stage: {name}. Valid: discovery, panel, concretize, polish." and ignore the flag.

**Note**: For claim validation (1:1 attack/rebuttal), `adversarial-review` is a **standalone skill outside this pipeline**. It is not a thought-chain stage and cannot be inserted via `--skip` or `--start`. Invoke it directly when needed.

---

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

**Tool usage per role**:

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Checkpoint confirmations, vault destination question | "다음으로 어떻게 진행할까요?" |
| Read | Pre-pipeline gate check (`.vault-link`, vault `_index.md`) | Silent gate state load |
| Skill | Stage invocations, deepen re-invocations, mini-polish pass, vault save dispatch | invoke `vault-bridge:save-session` with argument `plan` |

Each stage uses its own skill's tool set internally. Vault writes are delegated entirely to `save-session`.

---

## Final Output Format

When all stages complete and "터미널만" is selected:

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
*Thought Chain 완료 · 4단계 파이프라인*
```

When vault save is selected, `save-session` handles file creation. The polished document is passed as the body, and the `thought_chain:` frontmatter metadata block is included in the invocation context for embedding in the saved file.

---

## Quick Start Example

```
User: "새 결제 시스템 도입안을 종합 분석해줘"

→ Gate Check: .vault-link 상태 확인 (silent)
→ Stage 1 (Discovery): 블라인드스팟 인터뷰 → Critical 2건, Important 4건
→ Checkpoint: "다음으로 어떻게 진행할까요?" → 다음 단계로
→ Stage 2 (Expert Panel): 보안/성능/UX 전문가 토론 → 합의 3건, 보류 1건
→ Checkpoint: "다음으로 어떻게 진행할까요?" → 더 토론 → 심화 후 → 다음 단계로
→ Stage 3 (Doc-Concretize): 분석 결과 문서화 (4개 섹션)
→ Stage 4 (Doc-Polish): 품질 검사 + 자동 수정 (score: 91)
→ Vault Destination: "Plan doc로 vault에 저장" → save-session plan 호출
→ Output: vault에 plan-YYYY-MM-DD-결제시스템-도입안.md 저장

───
*Thought Chain 완료 · 4단계 파이프라인 (panel 1회 심화)*
```

---

## Note on Claim Validation

The previous 5-stage variant (PR #78, 2026-05-20) embedded `adversarial-review` as Stage 2. This was reverted in feat/stage4-pd (2026-05-25) per the vault decision recorded in `plan-2026-05-23-thought-chain-checkpoint-vault-integration.md` (status: 4-stage fixed).

For claim validation needs in an analysis flow:
- Run `unknown-discovery` first to surface findings
- Invoke `adversarial-review` standalone on specific claims if needed
- Then continue with `expert-panel` for stakeholder consensus

`thinking-facilitator` agent routes multi-skill signals automatically; when 3+ thinking-tools triggers fire it proposes thought-chain, otherwise it sequences invocations directly.
