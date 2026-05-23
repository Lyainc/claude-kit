# Adversarial Review — Attack Patterns & Templates

Reference document for attack templates, report formats, round display, and termination logic.
See the main [SKILL.md](../SKILL.md) for the core workflow.

---

## Attack Templates

Use these templates per vector in Phase 1. Adapt bracketed values to the claim under review.

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

---

## Judge Score Delta Mapping

Judge scores each element (Relevance, Substance, Completeness, 0–10 each) and maps total to dimension score delta:

| Total (0–30) | Dimension Score Delta |
|-------------|----------------------|
| 25–30 | +15% |
| 18–24 | +8% |
| 10–17 | no change |
| 0–9 | −10% |

---

## Termination Priority Order

When multiple conditions fire in the same round, apply the **first match** (highest priority wins):

1. **Explicit Done** — user signals ("충분해", "그만", "done", "stop", "enough") beats all internal heuristics
2. **Vulnerability Detected** — Weighted Score ≤ 25% for 2 consecutive rounds → show 3-choice prompt
3. **Round Limit** — 5 rounds reached, hard cap; nothing below can override
4. **Survival Gate** — Score ≥ 60% with 3+ post-gate rounds → propose Phase 2 (only meaningful if Round Limit not reached)
5. **Saturation** — 3 consecutive short/repetitive/evasive defenses → depth warning + confirm (user can override)
6. **Attack Exhaustion** — ≥ 3 of 4 vectors stalled → propose early termination, does not force
7. **Soft Round Checkpoint** — 3 rounds completed without higher-priority condition → ask user

**Concrete examples:**
- Round 3, score 58%: none of #1–#5 fire → Soft Checkpoint (#7) asks user
- Round 5, score 22%: Vulnerability Detected (#2) wins over Round Limit (#3) → 3-choice prompt shown first
- Round 5, score 70%, post-gate=3: Round Limit (#3) wins over Survival Gate (#4) → force Phase 2 (score still yields "survived" verdict)

**Steelman v2** (Vulnerability Detected path): Rebuild Steelman once with the full attack history as context, then resume Phase 1 from the failed dimension. Maximum 1 rebuild per claim.

---

## Final Report Template

Used in Phase 2 (default mode). Skipped in `--brief` mode.

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

---

## Brief Mode Output Format

Used instead of the full report when `--brief` flag is active:

```
| Claim | Verdict | Weighted Score |
|-------|---------|----------------|
| {claim text} | survived / collapsed / pending | {score}% |

**Recommendations**: {action items for collapsed/pending claims}
```

---

## Round Display Format

Output at the start of each attack round:

```
[Round {r}/5 — {Vector}] Claim {idx}/{N} | Weighted Score: {score}%

**[Attacker]**: {attack text}

---
```

After user defense (or `--auto` Defender response):

```
**[Judge — {Vector}]**: Relevance {r}/10 · Substance {s}/10 · Completeness {c}/10 → Score delta: {delta}

<!-- STATE:CHECKPOINT -->
Target: {name} | Claims: {N} | Phase: 1
Current Claim: {idx}/{N} | Round: {r}/5
Survival: [logic:{score}%] [evidence:{score}%] [counter:{score}%] [scope:{score}%]
Weighted Score: {weighted_avg}% | Attacks: {count} | Defenses: {success}/{total}
Verdict-so-far: [claim1:survived|collapsed|pending] ...
<!-- /STATE -->
```
