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
- (Optional) `--with-repo <path>` — load repo context for brownfield detection
- (Optional) `--refine <prev-seed-path> <feedback>` — refine an existing Seed spec
- (Optional) `--with-ralph` — chain to OMC ralph after Seed emission
- (Optional) `--quick` — compressed interview (3-5 questions, Goal dimension only)

## Quick Mode (`--quick`)

Compressed interview for time-constrained use:

1. **Phase 0**: context analysis only (skip brownfield detection)
2. **Phase 1**: 3-5 questions targeting Goal dimension only
3. **Phase 2**: gate check on Goal dimension (floor 0.75)
4. **Phase 3**: emit abbreviated Seed (Goal + best-effort Constraints)

Quick Mode output format:
```
## Quick Seed — {target}

**Goal**: {statement}
**Ambiguity**: {overall} (Goal: {goal_score})

### Constraints identified
{list}

───
*Quick Mode 완료 · 전체 인터뷰: `--quick` 없이 재실행*
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
   - If `--with-repo <path>` → Read README.md, plugin.json/package.json (whichever exists) → inject summary into Phase 1 context
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
[Round N] Dimension: {current} ({clarity}%) | Ambiguity: {overall:.2f}
```

**`--refine` mode (A3)**: If `--refine <prev-seed-path> <feedback>` flag is set:
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
[Gate Check] Ambiguity: {value:.2f} (target ≤ 0.20)
  Goal: {score:.0%} {'✓' if ≥ floor else '✗'} | Constraint: {score:.0%} {'✓' if ≥ floor else '✗'}
  Success: {score:.0%} {'✓' if ≥ floor else '✗'} | Context: {score:.0%} {'✓' if ≥ floor else '✗'} (brownfield only)
```

**Gate open**: Ambiguity ≤ 0.20 + all floors met + 2 consecutive rounds.
**Gate closed**: continue interview. Auto-select lowest-clarity dimension.

### Phase 3: Seed Emit

When gate opens OR user explicitly exits:

1. Synthesize all interview answers into Seed spec fields
2. Write YAML Seed spec to `docs/specs/{slug}.yaml`
   - `{slug}` = kebab-case of target name, e.g., `task-cli-tool`
   - If file exists: append `-v2`, `-v3`
3. Display summary and file path
4. Offer Phase 4 only if `--with-ralph` flag is set (no environment probing)

**Seed spec schema**: see `templates/SEED_SPEC.yaml`

### Phase 4: Handoff (Optional, opt-in only)

**Trigger**: `--with-ralph` flag MUST be set. The skill does not probe the
environment for OMC — vendor neutrality requires the chain to be explicit.

If `--with-ralph` flag set:
```
AskUserQuestion: "OMC ralph로 반복 실행을 이어갈까요?"
Options:
  1. 네, ralph로 실행
  2. Seed 파일로만 저장하고 종료
```

If "네, ralph로":
- Convert Seed YAML → OMC PRD format (see mapping table in `reference.md`)
- Write to `.omc/specs/{slug}-prd.json`
- Invoke via Skill tool: `Skill(skill="oh-my-claudecode:ralph", args="<slug>")`

If `--with-ralph` absent: skip Phase 4 entirely, emit Seed only.

**Vendor neutrality**: Phase 4 only fires under explicit opt-in. Without
`--with-ralph`, the skill never references OMC and produces a portable Seed.

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Gate open** | Ambiguity ≤ 0.20 + all floors + 2 consecutive | Proceed to Phase 3 |
| **Explicit done** | "done", "stop", "충분해", "그만", "끝" | Gate warning if not passed → Phase 3 anyway |
| **Round limit** | 12 rounds reached | Force Phase 3 with current scores |
| **Saturation** | 3 consecutive minimal-new-info answers | Warn + confirm continue or Phase 3 |
| **Early exit** | "빠르게", "스펙만", "결과로" | AskUserQuestion: skip to Phase 3 now? |

**Explicit done before gate**: display warning:
```
아직 Ambiguity {value:.2f}로 게이트 기준(0.20)에 미달해요.
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
```

**Compaction restoration**: restore all scores and round counter from STATE block. If STATE missing (fresh session), start Phase 0.

**`--refine` STATE addition**: include `refine_source: {prev-seed-path}` and `refine_feedback: "{feedback}"` in STATE block.

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
**Ambiguity**: {value:.2f} ({'게이트 통과' if gate_passed else '조기 종료'})

### Goal
{goal statement}

### Key Constraints ({count}개)
{list}

### Success Criteria ({count}개)
{list}

───
*spec-first 완료 · Round {N} · Ambiguity {value:.2f}*
```

## Known Limitations

- **A6 `--strict-judge`**: deferred to Phase D. LLM self-scoring of Ambiguity may be inconsistent without an independent judge. Users can override scores by providing explicit corrections during the interview.
- **OMC handoff**: opt-in only via `--with-ralph` flag; no environment auto-detection.
- **Seed → ralph mapping**: PRD conversion is best-effort; review `.omc/specs/{slug}-prd.json` before running.

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
