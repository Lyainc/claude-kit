# Expert Panel Summary — claude-kit Audit Critique

**Date**: 2026-05-10
**Target**: `~/vault/20_Projects/claude-kit/plan-2026-05-10-plugin-architecture-audit.md`
**Method**: 4-expert dialectical panel (Architecture / Token Economics / DX-UX / Pragmatic Maintainer) + Optimistic / Critical practitioners + Moderator

---

## Verdict

**Audit is meaningful but requires revision.** Direction correct, numerical estimates underspecified, action plan needs reordering.

| Question | Panel Consensus |
|---|---|
| Is the audit useful? | YES — direction validated against actual files |
| Is the "30~40% token compression" claim valid? | Partial — only valid if denominator is "description-layer subset", not full system prompt |
| Are P0 actions GO? | 4 of 5 GO, 1 demoted to P2, 1 new P0 added (net same count, composition changed) |
| Are P1 actions GO? | 5 of 7 GO, 1 partial GO, 1 demoted to P2 |
| Missing review areas? | 5 gaps identified (slash docs, env vars, pre-access load, manifest hit-rate, model distribution) |

---

## Topic-by-Topic Consensus

### Topic 1 — Token Compression Estimate (30~40%)

**Status**: Partial accept

The audit's claim is valid only within the description-layer subset (vault-searcher.md + plugin.json + thinking-tools SKILL frontmatters ≈ 4~5KB). Against the full system prompt, real impact is likely <5%. Reframe motivation from "token savings" to "routing-signal clarity + readability".

**Required revision**: audit must specify denominator before any P0 action proceeds.

### Topic 2 — vault-searcher Refactor Path (P0 #1, P1 #8)

**Status**: GO with split

P0 #1 (description compression 1247→~600 chars): GO. Verified bloat against actual file at `vault-bridge/agents/vault-searcher.md:3`.

P1 #8 must be split into two actions:
- **(a) Mode 4 reference extraction** → P1 GO (readability, no UX change)
- **(b) `/vault-write` slash separation** → P3 (blocked by missing data on external-project users without OVM)

Current P1 #8 wording ("또는") conflates these — net UX impact is opposite for each.

### Topic 3 — Hook Responsibility Overlap (P1 #6, #7)

**Status**: P0 escalation

Verified overlap: `plan-doc-sync.sh:38-66` (awk yaml parse + python3 realpath) duplicates `session-end-pre.sh:46-54` (anchored grep yaml parse). Both scan plan-doc candidates. SessionEnd prompt already touches `plan-doc-asked` flag → `plan-doc-sync.sh` SessionEnd path is **dead-code risk**.

**Action**: Promote `plan-doc-sync.sh` SessionEnd-path removal to **NEW P0 #6**. Original P1 #6 (SessionEnd prompt compression) remains P1 but blocked-by P0 #6.

Preserve PostToolUse(DEBUG) mode behind `VAULT_BRIDGE_PLAN_DOC_DEBUG=1`.

### Topic 4 — thinking-tools Trigger Cap (P0 #2)

**Status**: Demote to P2

"KR 4 + EN 3" cap has no empirical basis. Korean verb-ending diversity may require >4 patterns to maintain routing accuracy. Audit's own unresolved item #2 (no trigger statistics) blocks this decision.

P0 #4 (routing conflict patches: concretize/polish boundary, expert/adversarial Skip) is **independent** of cap and remains **GO** — this addresses trigger *quality*, not *quantity*.

**Action**: Demote P0 #2 → P2, conditional on dogfood data collection.

### Topic 5 — Cleanup-Critic Consistency + Missing Areas

**Status**: Apply same critic to audit itself

The 2026-05-10 cleanup session (held 6 of 7 candidates for "data missing"). Applying the same standard:

**Survives critic** (data sufficient or trivial):
- P0 #1, #3, #4, #5, new #6 (5 items)

**Demoted** (data missing):
- P0 #2 (trigger cap), P1 #10 (capture hybrid)

**Newly identified gaps** (P2):
1. vault-bridge slash command docs (`/vault-manifest-refresh`, `/vault-commit`, `/save-plan-doc`) — README missing
2. kill-switch / env-var table — `VAULT_BRIDGE_DISABLE`, `STRICT_NAMING`, `PLAN_DOC_DEBUG` underdocumented
3. `pre-access-guard.sh` invocation cost — jq×2 + python3 per Read/Grep/Glob, ~150ms × 100 calls/session
4. manifest.json cache hit-rate — 24h TTL value unverified
5. agent model distribution table (haiku/sonnet) + cost trade-off — not surfaced in README

---

## Revised Action Plan

### P0 — Immediate (1 day)

| # | Action | File | Status vs audit |
|---|---|---|---|
| 1 | vault-searcher description 1247→~600 chars | `vault-bridge/agents/vault-searcher.md:3` | GO (unchanged) |
| 3 | README skill-count sync (6→7, 8→9) | `obsidian-vault-manager/README.md:18`, `vault-audit/SKILL.md:3` | GO (unchanged) |
| 4 | Routing description patches (concretize/polish, expert/adversarial Skip, unknown narrowing) | thinking-tools 4 SKILL frontmatters | GO (unchanged) |
| 5 | facilitator trigger condition explicit | `thinking-facilitator.md:3` | GO (unchanged) |
| **6 NEW** | **Remove `plan-doc-sync.sh` SessionEnd path; route through `session-end-pre.sh`** | `vault-bridge/hooks/plan-doc-sync.sh`, `plugin.json:48-62` | NEW (escalated from P1 #7) |

**Demoted from P0**: #2 (trigger cap) → P2.

### P1 — Short-term (1 week)

| # | Action | Status vs audit |
|---|---|---|
| 6 | SessionEnd prompt compression to ≤1KB (after new P0 #6) | GO, blocked-by P0 #6 |
| 7 | (merged into P0 #6) | — |
| 8a | vault-searcher Mode 4 → reference/ extraction | GO (split from "또는") |
| 8b | vault-searcher Mode 4 → `/vault-write` slash | DEMOTED to P3 |
| 9 | vault-audit error pseudocode → `reference/vault-audit-rules.md` | GO (unchanged) |
| 10 | capture hybrid (slash + scripts/capture.sh) | DEMOTED to P2 (effect unmeasured) |
| 11 | keywords SEO cleanup (-8 vault-bridge, -6 OVM) | GO (unchanged) |
| 12 | pre-access-guard cap + invocation cost measurement | GO + extended scope |

### P2 — Medium-term (data collection required)

| # | Action | Origin |
|---|---|---|
| 2 | thinking-tools trigger cap | DEMOTED from P0 |
| 10 | capture hybrid | DEMOTED from P1 |
| 13 | vault-file-organizer call-site audit | unchanged |
| 14 | inbox-review → note AskUserQuestion cap simulation | unchanged |
| 15 | context skill ↔ vault-searcher Mode 2 routing | unchanged |
| 16 | thinking-tools `/think-*` slash commands | unchanged |
| 17 | vault-bridge README hook keyword tables | unchanged |
| 18 | root README hello-world examples | unchanged |
| 19 | expert/adversarial output language unification | unchanged |
| **N1** | **vault-bridge slash command README docs** | NEW (panel) |
| **N2** | **kill-switch / env-var table** | NEW (panel) |
| **N3** | **pre-access-guard invocation cost data** | NEW (panel) |
| **N4** | **manifest cache hit-rate measurement** | NEW (panel) |
| **N5** | **agent model distribution table** | NEW (panel) |

### P3 — Long-term / Held

- pre-access-guard structural redesign (data-dependent)
- plan-doc-syncer.py `_glob_to_regex` comment cleanup
- vault-knowledge-manager `memory: project` schema validation
- **vault-searcher Mode 4 `/vault-write` slash separation** (DEMOTED from P1, blocked by external-user data)

---

## Risk Note

**P0 sequencing matters**: P0 #4 (routing patches) and P2 #2 (trigger cap, demoted) interact — if both ran simultaneously, routing-accuracy regression cause becomes ambiguous. **Run P0 #4 alone first, observe routing for 1 week, then start data collection for P2 #2.**

---

## Recommendations

1. **Update audit document** (`plan-2026-05-10-plugin-architecture-audit.md`):
   - Specify token-compression denominator explicitly
   - Replace "또는" in P1 #8 with two distinct sub-actions
   - Mark P0 #2 as "blocked-by data collection"
   - Add new P0 #6 (plan-doc-sync.sh SessionEnd removal)

2. **Begin execution**: P0 #1, #3, #5, #6 are independent and can ship in parallel. P0 #4 ships separately to allow isolated effect measurement.

3. **Schedule data collection** for P2 #2 (trigger statistics) and P3 (external-user analytics) — both block downstream decisions.

---

*5 topics discussed · 5 consensus reached · 0 dissent · 4 expert panel + 2 fixed practitioners*
