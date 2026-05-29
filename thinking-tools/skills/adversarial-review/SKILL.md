---
name: adversarial-review

description: |
  Stress-test claims through structured adversarial battle rounds with quantified Survival Score.
  Runs 1:1 attacker-vs-defender battle across 4 vectors and produces a per-claim verdict
  (survived / collapsed / pending). Starts with Steelman Construction before attacking.

  Trigger when user mentions: 반증해줘, 주장 반박, 약점 찾아줘, 논리적 허점 찾아줘, 살아남을 수 있어?,
  devil's advocate, adversarial review, claim attack, survival score, steelman and attack.

allowed-tools: AskUserQuestion Read Write Agent
---

# Adversarial Review

> **Reference files (load on demand)**: [reference/patterns.md](reference/patterns.md) (attack templates, judge score mapping, termination priority, report formats, round display) · [examples/sample.md](examples/sample.md) (full Phase 0 → Phase 1 → Phase 2 session example). Read these explicitly when the corresponding section is reached; they are not auto-loaded with SKILL.md.

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

This skill is **standalone**, not embedded in any pipeline. `thought-chain` (4-stage analysis) does not include adversarial-review; for claim validation, invoke this skill directly.

## Execution Modes

| Flag | Behavior |
|------|----------|
| _(default)_ | Interactive: AskUserQuestion collects user defense each round |
| `--auto` | Automated: Agent generates Defender response instead of prompting the user |
| `--deep` | Judge spawned as a separate Agent subagent (stronger isolation) |
| `--brief` | Skip full report; output verdict-only summary |
| `--quick` | Skip Steelman; run 2 attack rounds per claim |

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

Per-vector template text: [reference/patterns.md](reference/patterns.md#attack-templates)

**Judge Rubric** (3 elements per round): Relevance (0–10), Substance (0–10), Completeness (0–10).
Score delta: 25–30 → +15%, 18–24 → +8%, 10–17 → 0%, 0–9 → −10% per dimension.

### Survival Score

Weighted average of 4 dimension scores (each 0–100%):

```
Survival Score = (Logical Integrity × 0.30) + (Evidence × 0.25) + (Counter-resilience × 0.25) + (Scope Robustness × 0.20)
```

All dimensions start at 50%. Score updates after every Judge evaluation. Display as `Weighted Score: {value}%` in STATE block.

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

Priority order (first match wins): Explicit Done > Vulnerability Detected > Round Limit > Survival Gate > Saturation > Attack Exhaustion > Soft Checkpoint.
Steelman v2 rules and priority examples: [reference/patterns.md](reference/patterns.md#termination-priority-order)

### Phase 2: Verdict and Export

**Per-claim verdict**:
- `survived`: Weighted Score ≥ 60% at termination
- `collapsed`: Weighted Score ≤ 25% at termination, or user skipped claim
- `pending`: Score 26–59% at termination (inconclusive)

Full report template and `--brief` format: [reference/patterns.md](reference/patterns.md#final-report-template)
**Export option**: After report, offer to save via Write tool to `docs/adversarial-review/{date}-{topic}.md`.

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

Compaction: restore all dimension scores and round counters; default missing scores to 50%; resume from indicated round.

## Output Format

### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed): footer separators (`───`), metadata tables, STATE blocks.
**Content Layer** (Unicode/ASCII decorative elements prohibited): attack/defense text, Judge evaluations, report body.
**Exceptions**: original source contains special characters; user explicitly requests emoji/special characters.

### Persona Labels (English)

| Persona | Role |
|---------|------|
| Steelman Coach | Facilitates Phase 0 steelman construction |
| Attacker | Presents adversarial attacks in Phase 1 |
| Judge | Independent evaluation of defense quality |

Round header: `[Round {r}/5 — {Vector}] Claim {idx}/{N} | Weighted Score: {score}%`.
Full round display format with Judge scoring line: [reference/patterns.md](reference/patterns.md#round-display-format)

## Additional Resources

- [Attack patterns, templates & report formats](reference/patterns.md)
- [Session example (Phase 0 → Phase 1 → Phase 2)](examples/sample.md)

## Korean I/O Directive

모든 사용자 대면 출력(공격 텍스트, 질문, Judge 평가, 리포트)은 **한국어**로 작성합니다.
페르소나 레이블(Attacker, Judge, Steelman Coach)과 STATE 블록 키는 영어를 유지합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
