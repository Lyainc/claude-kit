# Adversarial Review — Attack Patterns & Templates

Reference document for attack templates, report formats, round display, and termination logic.
See the main [SKILL.md](../SKILL.md) for the core workflow.

---

## Attack Templates

Use these templates per vector in Phase 1. Adapt bracketed values to the claim under review.

Every bracketed slot is filled from the Attacker's **domain angle** — the rank-1 entry of
[../../../reference/personas.md](../../../reference/personas.md) selected once per claim (see
[SKILL.md → Phase 1](../SKILL.md#phase-1-attack-rounds)). That entry's evaluation criterion decides
*what kind* of gap, evidence, scenario, or boundary is asked for: a `P1` angle demands threat-model
evidence and a worst-case breach scenario, a `P7` angle demands unit-cost evidence and a 10x-spend
scenario. The vectors and role labels are unchanged — only the angle varies by claim.

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

### Evidence Attack — `{counter_evidence_or_missing_data}` sourcing

The Evidence Attack's `{counter_evidence_or_missing_data}` slot has two fill modes,
selected by the outcome of Phase 0.5 Vault Decision Grounding (see [SKILL.md](../SKILL.md)).
Vault access is **exclusively** via the `vault-searcher` Agent call — direct Grep/Read of the
vault is forbidden (MECE: searching = vault-searcher, critiquing = adversarial-review).

- **Vault-grounded mode** (≥ 1 relevant past decision was cached in Phase 0.5):
  fill the slot with the user's own prior decision excerpt, framing the conflict explicitly.

  ```
  [Evidence Attack — vault-grounded]
  "제시된 증거 '{evidence}'만으로는 부족합니다.
  과거 '{decision_date}'에 작성하신 결정 기록을 보면 — '{decision_excerpt}' —
  지금 주장과 {반대 방향/충돌}하는 판단을 내리셨습니다.
  그때의 {근거/문제}를 지금은 어떻게 다르게 보시는지 설명하지 않으면 주장이 흔들립니다."
  ```

  `{decision_excerpt}` is drawn ONLY from the cached `## 결정` / `## 근거` / `## 문제`
  sections returned by vault-searcher (max 3 decisions, section-only excerpts).
  Counter-scenario MAY reuse a `status: archived` decision from the same cache to make the
  worst-case concrete — but ONLY when it carries an explicit failure/reversal signal (a
  non-empty `## 문제` section or a reversal note). A plain `archived` (successfully completed
  and shelved) is NOT a worst-case source.

- **Generic mode** (0 results, vault-bridge absent, or vault-searcher call failed):
  use the base `[Evidence Attack]` template above unchanged. This is a **transparent fallback** —
  do not mention the vault, the search, or the fallback to the user.

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

Used in Phase 2 (standard mode). Skipped in summary output mode ("요약만", "간단히").

The frontmatter block is required on every export — it is what makes the report machine-readable
for a downstream skill (schema: [../../../reference/common-schema.md](../../../reference/common-schema.md)).

```markdown
---
# Output conforms to thinking-tools/reference/common-schema.md
skill: adversarial-review
schema_version: 1
version: {skill-version}
generated: {YYYY-MM-DD}
input:
  target: {review target name}
  options: []              # modes used, e.g. ["빠른 모드", "자동 방어"]
output:
  type: review
  structure: reference/patterns.md#final-report-template
claims_tested: {N}
verdicts:
  survived: {N}
  collapsed: {N}
  pending: {N}
angle: {P-id|adhoc}        # Attacker domain angle — thinking-tools/reference/personas.md rank 1
backlog_scan: {scanned|skipped}  # Phase 0 backlog-prefilter result, #524
---

## Adversarial Review Report

**Date**: {date}
**Claims tested**: {N}

---

### Claim {idx}: {claim text}

**Backlog scan**: {`[backlog-scan SKIPPED]` line verbatim, or conflicting issue(s)/no-conflict statement}

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

Used instead of the full report in summary output mode ("요약만", "간단히"):

```
| Claim | Verdict | Resilience |
|-------|---------|------------|
| {claim text} | survived / collapsed / pending | 탄탄 / 보통 / 취약 |

**Backlog scan**: {`[backlog-scan SKIPPED]` line verbatim, or conflicting issue(s)/no-conflict statement — per claim, #524}

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

After user defense (or the auto-generated Defender response in 자동 방어 mode):

```
**[Judge — {Vector}]**: Relevance {r}/10 · Substance {s}/10 · Completeness {c}/10 → Score delta: {delta}

<!-- STATE:CHECKPOINT -->
Target: {name} | Claims: {N} | Phase: 1
Current Claim: {idx}/{N} | Round: {r}/5
Survival: [logic:{score}%] [evidence:{score}%] [counter:{score}%] [scope:{score}%]
Resilience: {탄탄|보통|취약} | Weighted Score: {weighted_avg}% | Attacks: {count} | Defenses: {success}/{total}
Verdict-so-far: [claim1:survived|collapsed|pending] ...
<!-- /STATE -->
```
