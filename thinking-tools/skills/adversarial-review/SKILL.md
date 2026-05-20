---
name: adversarial-review

description: |
  Stress-test claims through structured adversarial battle rounds with quantified Survival Score.
  Structure: binary Attacker↔Defender | Orchestration: sequential battle rounds | Output: survived/collapsed/pending verdict | Input: one or more claims
  Runs 1:1 attacker-vs-defender battle across 4 vectors (logical integrity, evidence, counter-scenario, scope boundary)
  and produces a final per-claim verdict (survived / collapsed / pending).

  Use when validating proposals, decisions, architectural choices, or any claim that must withstand scrutiny.
  Starts with Steelman Construction (Rapoport 3-step) before attacking.

  Trigger when user mentions: 반증, 공격, 검증, 주장 반박, 약점 찾기, 1:1 debate, claim attack, adversarial, survival score,
  steelman, 악마의 변호인, 논리 검증, 가설 테스트, 주장 검증, 논거 공격, 반론 테스트,
  or requests: "이 주장의 약점을 찾아줘", "반증해줘", "검증해줘", "공격해봐", "살아남을 수 있어?",
  "devil's advocate", "adversarial review해줘", "claim을 테스트해줘", "논리적 허점 찾아줘",
  "steelman하고 공격해줘", "survival score 측정해줘".

  Skip for: consensus-building, multi-stakeholder alignment (use expert-panel), or blind-spot discovery interviews (use unknown-discovery).

allowed-tools: AskUserQuestion Read Write Agent
---

# Adversarial Review

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: Korean by default
  - If user writes in English → English output
  - Persona labels: use English labels (Attacker, Judge, Steelman Coach)

## Overview

Stress-test one or more claims through adversarial attack rounds. Quantify resilience via Survival Score (0–100%).
The skill does NOT seek consensus — it seeks to break claims and measure how well they survive.

## MECE Positioning

| Skill | Mode | Goal |
|-------|------|------|
| `expert-panel` | Consensus-oriented multi-panel | Reach agreement through dialectic |
| `unknown-discovery` | Socratic blind-spot interview | Find what the user doesn't know they're missing |
| `adversarial-review` | 1:1 adversarial battle | Break claims, measure survival, produce verdict |

## Execution Modes

| Flag | Behavior |
|------|----------|
| _(default)_ | Interactive: AskUserQuestion collects user defense each round |
| `--auto` | Automated: Agent generates Defender response instead of prompting the user |
| `--deep` | Judge spawned as a separate Agent subagent (stronger isolation) |
| `--brief` | Skip full report; output verdict-only summary |
| `--quick` | Skip Steelman; run 2 attack rounds per claim (pre-existing flag) |

Flags are combinable. `--auto --deep`: Defender Agent subagent and Judge Agent subagent are both active simultaneously.

## Prerequisites

- One or more claims / propositions / theses to test
- (Optional) Supporting evidence or context the user provides

## Core Workflow

### Phase 0: Steelman Construction

Before attacking, build the strongest possible version of the claim.

**Rapoport 3-step** (apply to each claim):
1. **Restate**: Paraphrase the claim in your own words until the user confirms accuracy
2. **Agreement Points**: List where you agree or find the claim reasonable
3. **Learned Points**: Identify what is genuinely insightful or valuable in the claim

**Steelman Candidate Generation** (diverse-sampling approach):
- Generate 3 Steelman candidates with distinct framings (e.g., pragmatic framing, principled framing, empirical framing)
- Present candidates using AskUserQuestion with diff-style options — do NOT use simple y/n
- User selects or edits the strongest version; that version becomes the Attack Target

**Multi-claim handling**: If 2+ claims are submitted, process them sequentially. Confirm order with user before proceeding.

### Phase 1: Attack Rounds

Cycle through 4 attack vectors in order. Each round:

**Role Visibility Contract** (information asymmetry by design):
- **Attacker** receives: claim text + steelman only (no defense history, no prior round results)
- **Defender** (user or `--auto` agent) receives: claim text + steelman + current round attack only
- **Judge** receives: current round attack + defense only (full conversation history blocked by default)

In `--deep` mode, Judge is spawned as a separate Agent subagent; pass `{current round attack + defense text only}` as the subagent prompt.
In default mode, visibility is best-effort (prompt contract only — the LLM shares full conversation history across personas; `--deep` provides mechanical isolation via subagent context boundaries).

1. **Attacker** persona presents the attack
2. **AskUserQuestion** collects user defense (always show "skip this claim" as an option); in `--auto` mode, Agent generates Defender response
3. **Judge** persona evaluates defense
4. Update Survival Score and output STATE block

**Attack Vector Rotation**:

| Vector | Attack Pattern | Survival Dimension |
|--------|---------------|-------------------|
| Logical Integrity | Premise-conclusion gap, circular reasoning, fallacy identification | Logical Integrity (weight 0.30) |
| Evidence Attack | Evidence sufficiency, representativeness, source reliability | Evidence (weight 0.25) |
| Counter-scenario | 10x scale / worst-case / external-change collapse test | Counter-resilience (weight 0.25) |
| Scope Boundary | Generalization limits, exception domains, boundary conditions | Scope Robustness (weight 0.20) |

**Attack Templates**:

```
[Logical Integrity]
"이 주장은 '{premise}'에서 '{conclusion}'을 도출합니다.
그런데 {gap/fallacy}가 있어 추론이 성립하지 않습니다. 왜냐하면 {reason}."

[Evidence Attack]
"제시된 증거 '{evidence}'는 {충분하지 않다/대표적이지 않다/신뢰성이 낮다}.
{counter_evidence_or_missing_data}를 고려하면 주장이 흔들립니다."

[Counter-scenario]
"'{scenario}' 상황(예: 10배 규모/최악의 경우/외부 환경 변화)에서
이 주장은 {어떻게 붕괴하는지}. 이 반례를 어떻게 방어하시겠습니까?"

[Scope Boundary]
"이 주장은 '{domain}'에서는 성립하지만 '{exception_domain}'에서는 성립하지 않습니다.
일반화의 한계를 어떻게 설명하시겠습니까?"
```

**Judge Rubric** (3 elements, per round):
1. **Relevance**: Does the defense address the specific attack vector? (0–10)
2. **Substance**: Does the defense provide new evidence, logic, or reframing? (0–10)
3. **Completeness**: Does the defense fully resolve the attack or leave residuals? (0–10)

Judge scores each element and maps total (0–30) to dimension score delta:
- 25–30: +15% to dimension score
- 18–24: +8%
- 10–17: no change
- 0–9: -10% to dimension score

### Survival Score

Weighted average of 4 dimension scores (each 0–100%):

```
Survival Score = (Logical Integrity × 0.30) + (Evidence × 0.25) + (Counter-resilience × 0.25) + (Scope Robustness × 0.20)
```

- All dimensions start at 50% (neutral baseline)
- Score updates after every Judge evaluation
- Display as `Weighted Score: {value}%` in STATE block

### Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| Survival Gate | Score ≥ 60% after 3+ additional attack rounds post-gate | Propose Phase 2 entry |
| Vulnerability Detected | Score ≤ 25% for 2 consecutive rounds | 3-choice: Steelman v2 (max 1 time) / skip claim / Phase 2 |
| Round Limit | 5 rounds per claim reached | Force Phase 2 |
| Soft Round Checkpoint | 3 rounds completed | AskUserQuestion: continue or Phase 2? |
| Attack Exhaustion | ≥ 3 of 4 vectors yield no new attacks | Propose early termination |
| Saturation | 3 consecutive short + repetitive + evasive defenses | Depth warning + confirm |
| Explicit Done | "충분해", "그만", "done", "stop", "enough" | Proceed to Phase 2 |

**Steelman v2** (Vulnerability path): If triggered, rebuild Steelman once with the attack history as context, then resume Phase 1 from the failed dimension. Maximum 1 rebuild per claim.

**Priority order when multiple conditions fire in the same round** (highest first; the first match wins, do not evaluate lower-priority conditions):

1. **Explicit Done** — user override beats every internal heuristic.
2. **Vulnerability Detected** — score ≤ 25% (2 consecutive). Forcing this over the Round Limit ensures the user sees the 3-choice prompt before Phase 2 is forced.
3. **Round Limit** — 5 rounds reached. Hard cap; nothing below this row can override it.
4. **Survival Gate** — score ≥ 60% with 3+ post-gate rounds. Only meaningful when Round Limit is not yet reached.
5. **Saturation** — 3 consecutive low-quality defenses. Warns then confirms; user can override.
6. **Attack Exhaustion** — ≥ 3 of 4 vectors stalled. Proposes early termination but does not force it.
7. **Soft Round Checkpoint** — 3 rounds completed without higher-priority termination. Asks the user; default is to continue.

Concretely: at round 3 with score 58%, none of #1–#5 fire, Soft Round Checkpoint (#7) wins → ask user. At round 5 with score 22%, Vulnerability Detected (#2) wins over Round Limit (#3). At round 5 with score 70% and post-gate=3, Round Limit (#3) wins over Survival Gate (#4) → force Phase 2 (the score still becomes the "survived" verdict via §Phase 2).

### Phase 2: Verdict and Export

**Per-claim verdict**:
- `survived`: Weighted Score ≥ 60% at termination
- `collapsed`: Weighted Score ≤ 25% at termination, or user skipped claim
- `pending`: Score 26–59% at termination (inconclusive)

**Final Report** (Markdown) — **skipped in `--brief` mode** (verdict-only summary instead, see below):

```markdown
## Adversarial Review Report

**Date**: {date}
**Claims tested**: {N}

---

### Claim {idx}: {claim text}

**Steelman**: {steelman version used}

**Attack History**:
| Round | Vector | Attack Summary | Defense Summary | Score Delta |
|-------|--------|---------------|-----------------|-------------|
| 1 | Logical Integrity | ... | ... | +8% |
...

**Final Scores**:
- Logical Integrity: {score}% (×0.30)
- Evidence: {score}% (×0.25)
- Counter-resilience: {score}% (×0.25)
- Scope Robustness: {score}% (×0.20)
- **Weighted Score**: {score}%

**Verdict**: survived | collapsed | pending

**Key vulnerabilities identified**: {list}
**Surviving strengths**: {list}

---

### Overall Summary

| Claim | Verdict | Weighted Score |
|-------|---------|----------------|
| {claim 1} | survived | 72% |
| {claim 2} | collapsed | 18% |
...

**Recommendations**: {action items based on collapsed/pending claims}
```

**Export option**: After report generation, offer to save via Write tool to `docs/adversarial-review/{date}-{topic}.md`.

**Note on `--brief` mode**: Skip the full Final Report. Output a verdict-only summary:

| Claim | Verdict | Weighted Score |
|-------|---------|----------------|
| {claim text} | survived / collapsed / pending | {score}% |

**Recommendations**: {action items for collapsed/pending claims}

## STATE Block Contract

Output a STATE block after every Judge evaluation and at every checkpoint.
On context compaction, restore state from the most recent STATE block.

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Claims: {N} | Phase: {0|1|2}
Current Claim: {idx}/{N} | Round: {r}/5
Survival: [logic:{score}%] [evidence:{score}%] [counter:{score}%] [scope:{score}%]
Weighted Score: {weighted_avg}% | Attacks: {count} | Defenses: {success}/{total}
Verdict-so-far: [claim1:survived|collapsed|pending] [claim2:...] ...
<!-- /STATE -->
```

**Compaction restoration rules**:
- Restore all dimension scores and round counters from STATE block
- If STATE block is missing scores (legacy), default all dimensions to 50%
- Resume from the round indicated; do not re-run completed rounds

## Output Format

### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Metadata tables
- Progress/status indicators (STATE blocks)

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Attack and defense text
- Judge evaluations
- Report body

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

### Persona Labels (English)

| Persona | Role |
|---------|------|
| Steelman Coach | Facilitates Phase 0 steelman construction |
| Attacker | Presents adversarial attacks in Phase 1 |
| Judge | Independent evaluation of defense quality |

### Round Display Format

```
[Round {r}/5 — {Vector}] Claim {idx}/{N} | Weighted Score: {score}%

**[Attacker]**: {attack text}

---
```

After user defense:

```
**[Judge — {Vector}]**: Relevance {r}/10 · Substance {s}/10 · Completeness {c}/10 → Score delta: {delta}

<!-- STATE:CHECKPOINT -->
...
<!-- /STATE -->
```

## Quick Start

```
User: "마이크로서비스가 모놀리식보다 항상 낫다는 주장을 검증해줘"

→ Phase 0: Steelman 3개 후보 생성 → 사용자가 최강판 선택
→ Phase 1 Round 1 [Logical Integrity]: "항상"이라는 보편 주장의 논리적 비약 공격
→ Phase 1 Round 2 [Evidence Attack]: 반례 증거 (Majestic Monolith 사례) 제시
→ Phase 1 Round 3 [Counter-scenario]: 소규모 팀/초기 스타트업 시나리오에서 붕괴 테스트
→ Soft Checkpoint: 계속 여부 확인
→ Phase 1 Round 4 [Scope Boundary]: "항상"→"규모 X 이상의 팀에서는" 경계 제안
→ Phase 2: Verdict "pending" (Score 48%) — "항상"을 "특정 조건에서"로 수정 권고
```

## Korean I/O Directive

모든 사용자 대면 출력(공격 텍스트, 질문, Judge 평가, 리포트)은 **한국어**로 작성합니다.
페르소나 레이블(Attacker, Judge, Steelman Coach)과 STATE 블록 키는 영어를 유지합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
