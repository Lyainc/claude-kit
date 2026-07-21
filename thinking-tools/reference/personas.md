# Thinking-Tools — Shared Persona Pool

A default pool of **domain-expert personas** shared by `expert-panel` (panel composition) and
`adversarial-review` (Attacker's domain angle). Selection is **deterministic tag matching**, so the
same topic text yields the same persona set on every run — that reproducibility is the whole point
of this file.

**Scope**: domain experts only. `expert-panel`'s fixed Moderator / Optimistic Practitioner /
Critical Practitioner and `adversarial-review`'s fixed Attacker / Judge / Steelman Coach are
**role** labels, not domain personas — they stay in their own SKILL.md and are never selected from
here. `adversarial-review`'s contact point with this pool is *which angle the Attacker attacks
from*, not who attacks.

**The pool is a default, not a closed list.** A topic outside every entry's tags proceeds with
ad-hoc personas (see [Selection Rule](#selection-rule) step 4) — the skill must never refuse a
topic because it is off-pool.

## Pool

Each entry carries a **distinct evaluation criterion** (a different measurable axis). Two experts
sharing a criterion collapse into one opinion, which is why the axes below never overlap. Tags are
matched case-insensitively as literal substrings.

| ID | Label | Stance | Evaluation criterion (the measurable axis) | Voice | Tags |
|----|-------|--------|--------------------------------------------|-------|------|
| `P1` | Security Expert | Assumes an adversary is already inside | Threat model coverage, attack surface, CVSS severity | Suspicious, worst-case-first | security, 보안, auth, 인증, 암호, encryption, vulnerability, 취약점, 권한, permission, privacy, 개인정보, 토큰, token |
| `P2` | Performance Expert | Every abstraction has a runtime bill | p99 latency, throughput, complexity class (O(n)) | Measurement-demanding, numeric | performance, 성능, latency, 지연, throughput, 처리량, 속도, 부하, load, 캐시, cache, 최적화, optimization |
| `P3` | UX Expert | The user's confusion is the system's defect | Task-completion rate, error rate, time-to-first-success | User-anecdotal, concrete | ux, ui, 사용성, usability, 사용자, user, 인터페이스, interface, 디자인, design, 접근성, accessibility, 온보딩, onboarding |
| `P4` | Reliability Expert | Assumes it will fail in production at 3am | Error budget / SLO burn, blast radius, MTTR | Incident-driven, procedural | 안정성, reliability, 장애, incident, 운영, ops, 배포, deploy, 롤백, rollback, 모니터링, monitoring, 가용성, availability, 재시도, retry |
| `P5` | Data Expert | Bad data outlives the code that wrote it | Schema integrity, migration reversibility, consistency guarantees | Precise, invariant-focused | 데이터, data, db, 데이터베이스, database, 스키마, schema, 마이그레이션, migration, 정합성, consistency, 쿼리, query, 인덱스, index |
| `P6` | Maintainability Expert | Optimizes for the next person to open this file | Change cost, coupling/fan-out, review-diff size | Dry, structure-first | 유지보수, maintainability, 리팩터, refactor, 아키텍처, architecture, 구조, 기술부채, tech debt, 복잡도, complexity, 테스트, test, 모듈, module |
| `P7` | Cost Expert | Nothing is free at scale | Unit cost, TCO, spend per request/token | Budget-anchored, blunt | 비용, cost, 예산, budget, 가격, pricing, 요금, infra, 인프라, roi, 과금, billing |
| `P8` | Legal/Compliance Expert | The regulator reads it differently than you do | Regulatory exposure, license terms, audit-trail completeness | Formal, precedent-citing | 법무, legal, 규제, regulation, compliance, 라이선스, license, 약관, terms, 감사, audit, gdpr, 계약, contract, 저작권, copyright |
| `P9` | Product Strategy Expert | Shipping the wrong thing well is still failure | Adoption/retention, differentiation, opportunity cost | Big-picture, trade-off-framing | 전략, strategy, 제품, product, 시장, market, 경쟁, competition, 우선순위, priority, 로드맵, roadmap, 가치, value, 채택, adoption |
| `P10` | Communication Expert | If it is misread, it is mis-written | Misread rate, audience fit, time-to-comprehension | Plain-spoken, editing-minded | 문서, doc, 글, writing, 카피, copy, 메시지, message, 설명, explain, 네이밍, naming, 톤, tone, 콘텐츠, content, 번역, translation |

## Selection Rule

Deterministic — no free LLM choice at any step. Given the topic text (for `expert-panel`, the topic
title + statement; for `adversarial-review`, the finalized Steelman):

1. **Normalize**: lowercase the topic text. This is the match string.
2. **Score**: for each pool entry, `hits` = the number of its distinct tags occurring as substrings
   in the match string. `hits = 0` means unmatched.
3. **Rank** the matched entries by `hits` descending, then by ID ascending (`P1` before `P2`). Ties
   are broken by ID only — never by judgment.
4. **Cut**, by how many entries matched:

   | Matched | Take |
   |---------|------|
   | ≥ 3 | the first `min(5, matched)` ranked entries — 6+ matches truncate to 5 |
   | 1–2 | all matched entries, plus `3 − matched` ad-hoc personas to reach the 3-expert floor |
   | 0 | 3 ad-hoc personas; no pool entry is used |

   The 5-entry ceiling is the per-session cost bound; the 3-entry floor is `expert-panel`'s existing
   minimum-3-experts rule.

5. **Label** ad-hoc personas as `{Domain} Expert (ad-hoc)` and give each a criterion axis that does
   not duplicate any selected pool entry's. Ad-hoc personas are session-local — do **not** append
   them to this file.

**Single-persona consumers** (`adversarial-review`'s Attacker angle) take **rank 1 only** — the
top-ranked entry, or one ad-hoc persona when nothing matched. Since rank 1 is always inside the
`expert-panel` cut for the same topic text, the two skills provably point at the same pool entry.

## Reporting the Selection

The selection must be visible in the consuming skill's STATE block, so a second run can be compared
against the first and the ad-hoc fallback is never silent:

```
Personas: [P1 P4 P6] adhoc:0
Personas: [P3] adhoc:2
Personas: [] adhoc:3
```

IDs are listed in the ranked order from step 3. `adhoc:{n}` is required even when `0`.
