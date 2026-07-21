---
name: adversarial-review

description: |
  Stress-test claims via adversarial rounds and Survival Score.
  Runs 1:1 attacker-vs-defender battle. Starts with Steelman.

  Trigger when user mentions: 반증해줘, 주장 반박, 약점 찾아줘, 논리적 허점 찾아줘, 주장 검증, 살아남을 수 있어?,
  devil's advocate, adversarial review, claim attack, survival score, steelman and attack.
  Routing: 합의 도출·다관점은 expert-panel, 맹점 인터뷰는 unknown-discovery.

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

This skill is **standalone**; for claim validation, invoke it directly.

## Execution Modes

Express mode preferences in natural language — no flags needed:
- **자동 방어** ("내가 방어 안 할게", "자동으로 돌려줘"): Defender is spawned as a separate Agent subagent instead of prompting the user — same mechanical isolation as isolated Judge (independence rationale and cost note: see Phase 1 Automated Defense Quality Floor)
- **격리 실행** ("엄격하게", "격리해서"): Judge spawned as a separate Agent subagent (stronger isolation)
- **요약 출력** ("요약만"): Skip full report; output verdict-only summary
- **빠른 모드** ("빠르게", "간단히", "quick"): Skip Steelman; run 2 attack rounds per claim

All combinations compose silently — e.g., "빠르게 자동으로" activates quick mode + automated defense simultaneously. The 빠른 모드 phrase set ("빠르게"/"간단히"/"quick") is shared with unknown-discovery.

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

### Phase 0.5: Vault Decision Grounding (optional, between Phase 0 and Phase 1)

After the Steelman is finalized for a claim and **before Phase 1 begins**, attempt to ground the Evidence Attack (and, secondarily, the Counter-scenario) in the user's own past decision records stored in their Obsidian vault. This makes attacks context-tight — e.g. *"this claim conflicts with a decision you made 6 months ago in the opposite direction."*

**One-shot vault-searcher call** (Mode 3 — Keyword Search, via the Agent tool):
1. Call `vault-searcher` **exactly once per session** (not per round). Cache the returned excerpts and reuse them across rounds. Sized for the typical **single-claim** session; in a multi-claim session the cache reflects the **first** finalized Steelman's keywords, and the relevance gate (step 5) drops any cached decision unrelated to a later claim rather than re-querying — preserving the token budget at the cost of not surfacing claim-specific decisions for subsequent claims.
2. **Search target**: `notes/`, preferring `type: decision`. Tell vault-searcher to use the manifest `type` pre-filter when available, otherwise fall back to a `decision-` filename grep (this is vault-searcher's native Mode 3 behavior). Counter-scenario sourcing MAY additionally surface `status: archived` decisions as a secondary worst-case source — but ONLY those carrying an explicit failure/reversal signal (a non-empty `## 문제` section or a reversal note); a plain `archived` status can also mean "successfully completed and shelved", which is NOT a worst-case source.
3. **Query**: 2–3 core keywords distilled from the finalized Steelman.
4. **Result bound**: up to **3** relevant decisions. Instruct vault-searcher to excerpt **only** the `## 결정` / `## 근거` / `## 문제` sections (not the full note).
5. **Relevance gate**: drop any returned decision whose topic is not genuinely related to the claim — an irrelevant hit must not be used in any round.

**Graceful degrade** (no user notice, no broken experience):
- **≥ 1 relevant result** → vault-grounded mode: feed the excerpts into the Evidence Attack `{counter_evidence_or_missing_data}` slot (see [reference/patterns.md](reference/patterns.md#attack-templates)) when the Evidence vector comes up.
- **0 results / vault-bridge not installed / Agent call fails** → transparently fall back to the existing generic Evidence Attack. Do **not** announce the fallback to the user; the session must look identical to the non-vault path.

**Vault access policy (MECE — single source of truth)**: vault access happens **ONLY** through the `vault-searcher` Agent call described here. This skill MUST NOT directly `Read`, `Grep`, `Glob`, or `Bash`-grep any vault path (`~/vault/`, `.vault-link` targets, `.vault-bridge/manifest.json`, etc.). Searching is vault-searcher's job (MECE boundary); critiquing is this skill's job. Direct vault access is forbidden.

**Token budget**: haiku model + section-only excerpts + max 3 results + one-shot call after Steelman keeps this step within **≤ +1500 tokens** of Phase 1 overhead. Do not exceed this budget — never re-query per round, never request full notes.

### Phase 1: Attack Rounds

**Attacker domain angle** (selected once per claim, before Round 1): run the Selection Rule in
[../../reference/personas.md](../../reference/personas.md) on the finalized Steelman text and take
**rank 1** — that entry's evaluation criterion becomes the angle the Attacker attacks from, applied
across all 4 vectors (a Security-angle Evidence Attack asks for threat-model evidence; a Cost-angle
one asks for unit-cost evidence). Record the ID in the STATE block `Angle` field.

This is the **only** contact point with the shared pool. The fixed role labels below — Attacker,
Judge, Steelman Coach — are roles, not domain personas; they are never selected from the pool and
never change per topic. Because rank 1 is always inside `expert-panel`'s cut for the same text, both
skills provably point at the same pool entry for a given claim. When nothing matches, the Attacker
uses one ad-hoc angle and the STATE block records `adhoc` — the fallback is stated, never silent.

Cycle through 4 attack vectors in order. Each round:

**Role Visibility Contract** (information asymmetry by design):
- **Attacker** receives: claim text + steelman only (no defense history, no prior round results)
- **Defender** (user or automated defense agent) receives: claim text + steelman + current round attack only
- **Judge** receives: current round attack + defense only (full conversation history blocked by default)

In isolated execution mode, Judge is spawned as a separate Agent subagent; pass `{current round attack + defense text only}` as the subagent prompt.
In standard mode, visibility is best-effort (prompt contract only — the LLM shares full conversation history across personas; isolated execution mode provides mechanical isolation via subagent context boundaries).

**Automated Defense Quality Floor** (자동 방어 mode only):
Spawn Defender as a separate Agent subagent — not inline generation — regardless of the 격리 실행 toggle. An inline auto-defender shares context with the Attacker turn that just produced the attack, which biases it toward a generic, half-hearted rebuttal; a dedicated subagent call removes that bias the same way isolated Judge removes evaluation bias.
Pass `{claim text + full steelman (including Phase 0 Agreement Points + Learned Points) + current round attack only}` as the subagent prompt — the same inputs the Role Visibility Contract already grants Defender, just delivered via a dedicated call.
Prompt-quality floor: generate the strongest good-faith rebuttal a motivated defender would make — engage the attack's specific point directly, draw on the steelman's Agreement/Learned Points as ammunition, never concede or hedge prematurely. This keeps Survival Score reflecting the claim's actual strength rather than an under-motivated auto-defender's laziness.
**Cost note**: unlike Phase 0.5's one-shot vault-searcher call (bounded at ≤ +1500 tokens), 자동 방어 spawns a fresh Defender subagent every attack round — up to 5 rounds × N claims per session. No explicit token ceiling is enforced here; the isolation guarantee is worth the added subagent calls since 자동 방어 is opt-in.

1. **Attacker** persona presents the attack
2. **AskUserQuestion** collects user defense (always show "skip this claim" as an option); in automated defense mode, the Defender subagent generates the response instead (see Automated Defense Quality Floor above)
3. **Judge** persona evaluates defense
4. Update Survival Score and output STATE block

**Attack Vector Rotation**:

| Vector | Attack Pattern | Survival Dimension |
|--------|---------------|-------------------|
| Logical Integrity | Premise-conclusion gap, circular reasoning, fallacy identification | Logical Integrity (weight 0.30) |
| Evidence Attack | Evidence sufficiency, representativeness, source reliability (uses Phase 0.5 vault decision excerpts when available) | Evidence (weight 0.25) |
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

All dimensions start at 50%. Score updates after every Judge evaluation. Display as qualitative resilience band (탄탄/보통/취약) in STATE block.

Qualitative bands (mirroring verdict thresholds): **탄탄** (Survived, ≥60%) | **보통** (Pending, 26–59%) | **취약** (Collapsed, ≤25%)

### Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| Survival Gate | Score ≥ 60% after 3+ additional attack rounds post-gate | Propose Phase 2 entry |
| Vulnerability Detected | Score ≤ 25% for 2 consecutive rounds | 3-choice: Steelman v2 (max 1 time) / skip claim / Phase 2 |
| Round Limit | 5 rounds per claim reached | Force Phase 2 |
| Soft Round Checkpoint | 3 rounds completed | AskUserQuestion: continue or Phase 2? |
| Attack Exhaustion | ≥ 3 of 4 vectors yield no new attacks | Propose early termination |
| Saturation | 3 consecutive: short response + repetition + avoidance | Depth warning + confirm |
| Explicit Done | "충분해", "그만", "done", "stop", "enough" | Proceed to Phase 2 |

Priority order (first match wins): Explicit Done > Vulnerability Detected > Round Limit > Survival Gate > Saturation > Attack Exhaustion > Soft Checkpoint.
Steelman v2 rules and priority examples: [reference/patterns.md](reference/patterns.md#termination-priority-order)

### Phase 2: Verdict and Export

**Per-claim verdict**:
- `survived` (탄탄): Weighted Score ≥ 60% at termination
- `collapsed` (취약): Weighted Score ≤ 25% at termination, or user skipped claim
- `pending` (보통): Score 26–59% at termination (inconclusive)

Full report template and summary output mode format: [reference/patterns.md](reference/patterns.md#final-report-template)
**Export option**: After report, offer to save via Write tool to `docs/adversarial-review/{date}-{topic}.md`.

**Exported files carry the common output schema** ([../../reference/common-schema.md](../../reference/common-schema.md)): the report template's frontmatter emits the common block plus this skill's `claims_tested` / `verdicts` extension, so a downstream skill can read the verdict counts without parsing the prose body. `output.type` is `review`; `input.target` is the review target name. Emit the block on every export — an exported report without it is not machine-readable.

## STATE Block Contract

> **Core Rules**: See [../../reference/state-contract.md](../../reference/state-contract.md)
> **Additional trigger**: output a STATE block after every Judge evaluation (each Judge evaluation is a checkpoint).

Numeric fields (dimension scores, Weighted Score) serve compaction restoration and gate logic only; user-facing output shows the qualitative Resilience label (탄탄/보통/취약), never raw percentages.

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Claims: {N} | Phase: {0|1|2}
Current Claim: {idx}/{N} | Round: {r}/5 | Angle: {P-id|adhoc}
Survival: [logic:{score}%] [evidence:{score}%] [counter:{score}%] [scope:{score}%]
Resilience: {탄탄|보통|취약} | Weighted Score: {weighted_avg}% | Attacks: {count} | Defenses: {success}/{total}
Verdict-so-far: [claim1:survived|collapsed|pending] [claim2:...] ...
<!-- /STATE -->
```

Compaction: restore all dimension scores and round counters; default missing scores to 50%; resume from indicated round. A missing `Angle` is recovered by re-running the Selection Rule on the same Steelman text — it is deterministic, so recomputation returns the identical entry.

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

These three are **fixed roles, independent of the topic** — they are not domain personas and are not
drawn from [../../reference/personas.md](../../reference/personas.md). Only the Attacker's *domain
angle* comes from that pool (see [Phase 1](#phase-1-attack-rounds)); the label stays `Attacker`
regardless of which entry was selected.

Round header: `[Round {r}/5 — {Vector}] Claim {idx}/{N} | Resilience: {탄탄|보통|취약}`.
Full round display format with Judge scoring line: [reference/patterns.md](reference/patterns.md#round-display-format)

## Additional Resources

- [Attack patterns, templates & report formats](reference/patterns.md)
- [Session example (Phase 0 → Phase 1 → Phase 2)](examples/sample.md)
- [Shared persona pool (Attacker domain angle)](../../reference/personas.md)
- [Common output schema (export frontmatter)](../../reference/common-schema.md)

## Korean I/O Directive

모든 사용자 대면 출력(공격 텍스트, 질문, Judge 평가, 리포트)은 **한국어**로 작성합니다.
페르소나 레이블(Attacker, Judge, Steelman Coach)과 STATE 블록 키는 영어를 유지합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
