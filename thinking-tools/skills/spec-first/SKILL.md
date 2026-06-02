---
name: spec-first
description: |
  Crystallize vague ideas into machine-readable Seed specs via Socratic interview
  and Ambiguity gating. Vendor-neutral Ouroboros-style workflow.

  Trigger when user mentions: spec-first, 명세 만들기, 아이디어를 스펙으로, 요구사항 명확화, 아이디어를 명세로,
  seed 생성, ambiguity gate, requirements crystallize.
  Routing: 단순 문서 구체화는 doc-concretize, YAML Seed 스펙이 필요할 때만 spec-first.
allowed-tools: AskUserQuestion Read Write Glob Skill
model: sonnet
---

# Spec First

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: Korean by default
  - If user writes in English → English output
  - Persona labels and STATE block keys: English

## MECE Positioning

| Skill | Mode | When |
|-------|------|------|
| unknown-discovery | Diagnostic — find blind spots in existing plans | Plan/idea already exists |
| **spec-first** | **Constructive — clarify vague idea into structured spec** | **No plan yet** |
| diverse-sampling | Creative — generate diverse alternatives | Exploring multiple directions |
| expert-panel | Evaluative — multi-perspective debate | Options exist, need judgment |
| adversarial-review | Attack — stress-test a specific claim | Claim/proposal exists |

## Prerequisites

- A vague idea, feature request, or requirement to crystallize
- Quick mode: include "빠르게", "스펙만", or "quick" at the start of your request (selects the compressed interview before Phase 1 begins)
- Brownfield repo: detected automatically via Glob; name the project/repo root in prose if needed
- Refine existing spec: say "이 스펙 다듬어줘" with the prior seed file path

## Quick Mode

"빠르게"/"스펙만"/"quick" activates Quick Mode **only at the start** (Phase 0). Mid-interview, these phrases are ignored — to cut an in-progress interview short, use the Early-exit triggers ("결과로", "지금 끝내줘", "이대로 진행").

Compressed interview for time-constrained use:

1. **Phase 0**: context analysis only (skip brownfield detection)
2. **Phase 1**: 3-5 questions targeting Goal dimension only
3. **Phase 2**: gate check on Goal dimension (floor 0.75)
4. **Phase 3**: emit abbreviated Seed (Goal + best-effort Constraints)

Quick Mode output format:
```
## Quick Seed — {target}

**Goal**: {statement}
### Constraints identified
{list}

───
*Quick Mode 완료 · 전체 인터뷰로 재실행*
```

## Core Workflow

### Phase 0: Context Analysis

1. **Domain detection**: infer Tech/Biz/Creative from user input; confirm via AskUserQuestion if unclear
2. **Brownfield auto-detection (A2)**:
   ```
   Glob(pattern="{README.md,package.json,plugin.json,pyproject.toml,CLAUDE.md,requirements.txt,Cargo.toml,go.mod}")
   ```
   - If ≥1 file found → AskUserQuestion: "기존 프로젝트에 추가하는 건가요, 새 프로젝트인가요?"
     - Brownfield confirmed → activate Context Clarity dimension (weight 0.15)
     - Greenfield → Context Clarity inactive
   - If user explicitly points to a repository root or project directory in prose (a project root, not merely a source file they want analyzed) → Read README.md, plugin.json/package.json (whichever exists) → inject summary into Phase 1 context
     - e.g. "이 플러그인 레포에 기능 추가하려고" / "~/projects/foo 프로젝트에" → brownfield detected
     - but "이 login.ts 동작을 명세로" → a single source file, not a repo root → greenfield default
   - If no files found → greenfield default (no question)
3. **Maturity**: always starts at Idea level (the point of spec-first is to move from idea to spec)
4. **Set dimension weights** (see Ambiguity Scoring below)
5. **Load question template** based on domain: `templates/questions/{domain}.md`

### Phase 1: Interview Loop

Iterative Socratic interview to raise clarity across all active dimensions.

**Starting order**:
- First question: always Goal (foundation of everything else)
- Subsequent: lowest-clarity dimension (ties: Goal > Constraint > Success > Context)

**Per-dimension question pattern**:
- Core question (1): open-ended, domain-appropriate (load from question template)
- Follow-up (1): narrow based on answer ("구체적으로 어떤 상황에서?", "왜 그 제약이 중요한가요?")
- Clarification (0-1): only if answer is still ambiguous ("예를 들어 말씀해주시면?")

**After each answer**: run Ambiguity scoring (A1) immediately.

**Round display**:
```
[Round N] Dimension: {current}
```

**Refine mode (A3)**: If user says '이 스펙 다듬어줘' with a prior seed file path:
- Read `<prev-seed-path>` → restore dimension scores and goal/constraints/success
- Skip Phase 0 (reuse domain, brownfield status)
- Phase 1 starts from the dimension with the lowest clarity score
- Inject `<feedback>` as Phase 1 preamble context
- STATE block records `refine_generation: N`

### Ambiguity Scoring (A1 — Y/N Checklist)

After each answer, score the relevant dimension using Y/N checklist from `reference.md`.

**Scoring mechanics**:
- Each dimension has 3-5 binary checklist questions (see `reference.md`)
- clarity = (Y count) / (total questions) for that dimension
- Record answers + one-line rationale in STATE block `scoring_rationale`
- Never round to 0.0 or 1.0 — floor at 0.1, cap at 0.9 (partial credit always possible)

**Dimension weights**:

| Dimension | Greenfield weight | Brownfield weight | Floor |
|-----------|------------------|------------------|-------|
| Goal Clarity | 0.40 | 0.34 | 0.75 |
| Constraint Clarity | 0.30 | 0.26 | 0.65 |
| Success Criteria | 0.30 | 0.25 | 0.70 |
| Context Clarity | — | 0.15 | 0.60 |

**Gate formula**:
```
Ambiguity = 1 - Σ(clarity_i × weight_i)
Gate: Ambiguity ≤ 0.2 AND all active dimensions ≥ floor AND achieved for 2 consecutive rounds
```

### Phase 2: Gate Check

Run after each interview round. Display current scores.

```
[Gate Check] 게이트: {all active dims ✓ → "통과 임박" | else "진행 중 — ✗ 항목 보완 필요"}
  Goal: {'✓' if ≥ floor else '✗'} | Constraint: {'✓' if ≥ floor else '✗'}
  Success: {'✓' if ≥ floor else '✗'} | Context: {'✓' if ≥ floor else '✗'} (brownfield only)
```

The ✓/✗ per dimension is the user-facing progress signal — it shows *which* dimensions still fall short without exposing the underlying numeric scores.

**Gate open**: Ambiguity ≤ 0.20 + all floors met + 2 consecutive rounds.
**Gate closed**: continue interview. Auto-select lowest-clarity dimension.

### Phase 3: Seed Emit

When gate opens OR user explicitly exits:

1. Synthesize all interview answers into Seed spec fields
2. Write YAML Seed spec to `docs/specs/{slug}.yaml`
   - `{slug}` = kebab-case of target name, e.g., `task-cli-tool`
   - If file exists: append `-v2`, `-v3`
3. Display summary and file path
4. The Seed file is the terminal deliverable — downstream execution handoff is out of scope

**Seed spec schema**: see `templates/SEED_SPEC.yaml`

### Phase 4: Handoff (out of scope)

The Seed YAML is the terminal deliverable. spec-first crystallizes *what* to build
(goal / constraints / success-criteria); *how* to build it — slice ordering, execution
loop, E2E verification — belongs to whatever tool consumes the Seed. The Seed is a
portable, vendor-neutral artifact: hand it to an agent, a build loop, or a human
implementer. spec-first does not invoke or assume any specific execution runtime.

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Gate open** | Ambiguity ≤ 0.20 + all floors + 2 consecutive | Proceed to Phase 3 |
| **Explicit done** | "done", "stop", "충분해", "그만", "끝" | Gate warning if not passed → Phase 3 anyway |
| **Round limit** | 12 rounds reached | Force Phase 3 with current scores |
| **Saturation** | 3 consecutive minimal-new-info answers | Warn + confirm continue or Phase 3 |
| **Early exit** | mid-interview only: "결과로", "지금 끝내줘", "이대로 진행" | AskUserQuestion: skip to Phase 3 now? |

**Explicit done before gate**: display warning:
```
아직 게이트 기준에 미달해요. (일부 항목이 ✗)
그래도 지금 스펙을 생성할까요? (품질이 낮을 수 있어요)
```

## STATE Block Contract

Output a STATE block after every interview round and at every gate check.

```
<!-- STATE:CHECKPOINT -->
skill: spec-first
phase: {0|1|2|3|4}
target: {name} | domain: {tech|biz|creative} | brownfield: {true|false}
round: {N} | refine_generation: {N or 0}
clarity: [goal:{score:.2f}] [constraint:{score:.2f}] [success:{score:.2f}] [context:{score:.2f}]
ambiguity: {value:.2f} | gate: {open|closed} | consecutive_gate: {0|1|2+}
scoring_rationale:
  goal: "{last rationale}"
  constraint: "{last rationale}"
  success: "{last rationale}"
  context: "{last rationale or N/A}"
<!-- /STATE -->
<!-- Internal restoration fields: ambiguity, clarity scores, consecutive_gate — not displayed to user -->
```

**Compaction restoration**: restore all scores and round counter from STATE block. If STATE missing (fresh session), start Phase 0.

**Refine mode STATE addition**: include `refine_source: {prev-seed-path}` and `refine_feedback: "{feedback}"` in STATE block.

## Output Format

### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Progress indicators (Gate Check display)
- STATE blocks

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Interview questions
- Seed YAML content
- User-facing summaries

**Exceptions**: original user input, user-requested emoji.

### Seed Emission Display

```
## Seed Spec 생성 완료

**파일**: `docs/specs/{slug}.yaml`
**상태**: {'게이트 통과' if gate_passed else '조기 종료'}

### Goal
{goal statement}

### Key Constraints ({count}개)
{list}

### Success Criteria ({count}개)
{list}

───
*spec-first 완료 · Round {N}*
```

## Known Limitations

- **Strict judge mode**: deferred to Phase D. LLM self-scoring of Ambiguity may be inconsistent without an independent judge. Users can override scores by providing explicit corrections during the interview.

## References

- **Scoring rubric**: [reference.md](reference.md)
- **Workflow examples**: [examples.md](examples.md)
- **Seed template**: [templates/SEED_SPEC.yaml](templates/SEED_SPEC.yaml)
- **Question templates**: [templates/questions/](templates/questions/)
- **Common output schema**: [../../reference/common-schema.md](../../reference/common-schema.md)

## Quick Start

```
User: "task CLI를 만들고 싶어. 뭐가 필요한지 모르겠어."

→ Phase 0: domain=Tech, greenfield (no project files), weight set
→ Phase 1 Round 1 [Goal]: "어떤 문제를 해결하려고 하나요?" → clarity 0.40
→ Phase 1 Round 2 [Goal]: "주요 사용자는 누구인가요?" → clarity 0.65
→ Phase 1 Round 3 [Constraint]: "기술 스택이나 환경 제약이 있나요?" → clarity 0.50
→ Phase 1 Round 4 [Success]: "어떤 상태가 되면 성공이라고 할 수 있나요?" → clarity 0.60
→ Phase 1 Round 5 [Goal]: "가장 핵심 기능 하나만 고른다면?" → clarity 0.80 ✓
→ Phase 1 Round 6 [Constraint]: → clarity 0.70 ✓ | [Success]: → 0.75 ✓ | Ambiguity: 0.18 ✓ (gate: 2회)
→ Phase 2: Gate open
→ Phase 3: Seed 생성 → docs/specs/task-cli-tool.yaml

Ambiguity 0.65 → 0.18 · Round 6
```

## Korean I/O Directive

모든 사용자 대면 출력(질문, Gate Check 표시, Seed 요약)은 **한국어**로 작성합니다.
STATE 블록 키와 YAML 필드명은 영어를 유지합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
