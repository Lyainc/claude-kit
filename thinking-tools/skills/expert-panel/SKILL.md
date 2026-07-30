---
name: expert-panel

description: |
  Facilitate expert panel discussions (thesis-antithesis-synthesis): multiple expert
  personas debate a decision, each argued in an isolated subagent so positions are
  independently reasoned (not one model agreeing with itself), optionally grounded in
  vault citations, converging to consensus + action items. Use when a decision needs
  several perspectives weighed against each other, not a single answer.

  Trigger when user mentions: 전문가 토론, 찬반 토론, 다관점 분석, 합의 도출, 트레이드오프 정리,
  expert panel, multi-perspective review, "전문가 관점에서 검토해줘", "다양한 관점에서 평가해줘".
  Routing: 1:1 단일 주장 공격은 adversarial-review, 맹점 발견 인터뷰는 unknown-discovery.
allowed-tools: Read Grep Write AskUserQuestion Agent
---

# Expert Panel Discussion

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: Korean by default (panel discussions use Korean)
  - If user writes in English → English output
  - Role labels: use English labels (see Role Labels table)

## Overview

Facilitate expert panel discussions where diverse specialists reach consensus through dialectical debate.

## Execution Modes

Express mode preferences in natural language — no flags needed:
- **격리 실행** ("엄격하게", "격리해서"): Each expert and Moderator spawned as separate Agent subagents (stronger isolation). Enables real multi-turn rebuttal — experts are re-spawned each round with prior statements injected, instead of one simulated pass (see [Isolated Execution: Rebuttal Exchanges](#isolated-execution-rebuttal-exchanges))
- **요약 출력** ("요약만", "transcript 없이"): Skip transcript generation; produce SUMMARY.md + UNRESOLVED.md only

All combinations compose silently — including any combination with citation grounding (see [Citation Contract](#citation-contract)) and the Phase 2 inline-summary path (see [Phase 2: Recording](#phase-2-recording)).

## Participants

### Fixed (Always Present)

| Role | Stance | Distinct evaluation criteria | Voice |
|------|--------|------------------------------|-------|
| **Moderator** | Neutral facilitation (no position) | Open/close authority, fact-check requests, unresolved-issue tracking | Procedural, summarizing |
| **Optimistic Practitioner** | Advocates benefits + feasibility | Implementation experience, delivery numbers ("3주 내 가능", "X% 개선") | Forward-leaning, solution-first |
| **Critical Practitioner** | Identifies risk + limitations, proposes alternatives | Failure precedents, risk probabilities, tech-debt cost | Skeptical, evidence-demanding |

### Variable (Selected from the shared pool)

| Role | Description |
|------|-------------|
| **Expert Panel** | 3–5 domain experts selected from [../../reference/personas.md](../../reference/personas.md) by that file's deterministic tag-matching Selection Rule — same topic text, same panel, every run |

Run the Selection Rule per topic in Phase 0 on the **user's original topic text** (title + statement
as submitted — the same input `adversarial-review` uses, which is what makes the two skills land on
the same entry) and record the resulting IDs in the STATE block
`Personas` field. The pool is a **default, not a closed list**: a topic matching no entry proceeds
with ad-hoc personas labeled `{Domain} Expert (ad-hoc)`, counted in `adhoc:{n}` so the fallback is
visible rather than silent. A user who names the experts explicitly overrides the rule — record
that as `adhoc:{n}` for any named expert absent from the pool.

**Important — role-prompt differentiation is the diversity source**: This panel's diversity comes from differentiated **role prompts**, not from extra spawns or higher temperature (rationale: [reference.md → 다양성 원천](reference.md)). Each role — fixed and variable — must carry a **distinct stance**, **distinct evaluation criteria** (a different measurable axis per role, e.g. Security→CVSS, Performance→p99/O(n), UX→task-completion rate), and a **distinct voice**. Roles that share the same criteria collapse into one opinion — for variable roles those three come pre-differentiated from the shared pool ([../../reference/personas.md](../../reference/personas.md)), so an ad-hoc persona is the only place the differentiation has to be authored per session. When two roles agree too readily, re-validate the conclusion against each role's *own* criteria — easy agreement may be conformity, not aligned evidence (see Anti-conformity directive in [Phase 1](#phase-1-topic-rounds) and isolated-mode early-stop). Full per-role differentiation guidance + the rejected full-spawn-default alternative: [reference.md](reference.md).

### Expert Selection Guide

The Selection Rule produces the panel outright; this guide only explains what it already enforces.
There is no judgment step here — the single departure is an explicit user override.

| Criteria | What the rule enforces |
|----------|---------------|
| Panel size | 3–5 (the Selection Rule's floor and ceiling); above 5 the added expert repeats an existing criterion |
| Domain overlap | Guaranteed by tag matching — each selected entry carries a distinct evaluation criterion |
| Perspective balance | Carried by the tags themselves — a topic with strategy vocabulary matches `P9`. Never top up the panel because the selection *looks* implementation-heavy: "is this implementation-focused" is an LLM judgment, and one applied inconsistently makes two runs of one topic emit different `adhoc:{n}` (#423) |
| Rotation | Automatic — the rule re-runs per topic, so a multi-topic session rotates experts by topic text, not by hand |

**When to add experts mid-discussion**: If a topic reveals an uncovered domain (e.g., legal implications emerge during a technical review), Moderator may propose adding a domain expert — **user confirmation required**, recorded in `adhoc:{n}`. This is the user-override path, not a selection judgment: without the user's explicit yes the rule's output stands unchanged.

## Citation Contract

When an expert states a **numeric or factual claim** (statistics, performance figures, failure rates, legal citations, precedents), it must cite exactly one grounding source:

1. **Preferred**: call `vault-searcher` (Agent tool, Mode 3 — Keyword Search) once per topic to surface relevant past decisions or notes. Cache returned excerpts for reuse within the same topic — do NOT re-query per round. Search target: user's vault `notes/`, preferring `type: decision`.
2. **Fallback**: cite a named document or file already in scope via Read/Grep (e.g., a design doc the user provided for this session).
3. **Inline fallback**: if vault-searcher is unavailable / returns 0 relevant results / the Agent call fails, fall back to the existing inline behavior — the expert states the claim as a domain judgment. Do NOT announce the fallback to the user; session behavior must look identical.

**Token budget**: vault-searcher call + section-only excerpts + max 3 results keeps this step within **~+1500 tokens** of per-topic overhead (mirrors the adversarial-review grounding budget precedent). Never re-query per rebuttal exchange, never request full notes.

**Citation-coverage escalation signal**: a consensus topic where grounding was *attempted but not found* is classified "검증 안 됨 (unverified)" and feeds the existing escalation/early-stop logic — the same signal path as topic conflict (see [Round Limits](#phase-1-topic-rounds)). Such a topic is NOT classified "쉬움 (easy)"; it escalates/deepens instead, catching false-consensus (experts agree but no evidence surfaced despite vault-searcher being available). **This fires ONLY on `unverified`, never on `skipped`.** When vault-searcher is unavailable (e.g. thinking-tools standalone, no vault-bridge) grounding is never attempted, the topic is recorded `skipped`, and the normal "no new argument" early-stop applies unchanged — escalating every topic merely because no vault exists would make standalone sessions silently longer, violating the "behavior must look identical" promise of inline fallback (Citation Contract step 3).

**Note on full-spawn-default**: citation grounding is a verification purpose — sourcing evidence to ground claims. It does NOT increase expert diversity and does NOT conflict with the spawn≠diversity / full-spawn-default ADR (see [reference.md → 다양성 원천](reference.md)). The diversity lever remains role-prompt differentiation only; citation is orthogonal.

| Item | Rule |
|------|------|
| Principle | Unanimity (allows up to 1 minority dissent) |
| Moderator | No voting rights, facilitation authority only |
| Experts | Minimum 3 experts required |
| Re-discussion | Re-discuss topic if 2+ experts object |

## Core Workflow

### Phase 0: Preparation
1. Analyze the review target → split into topics
2. Run the [personas.md](../../reference/personas.md) Selection Rule on each topic's text → panel composition (confirm with the user only when they asked to pick the experts themselves)
3. Generate discussion agenda

### Phase 1: Topic Rounds

**Anti-conformity directive** (applied to every expert turn): "You are not required to reach the same conclusions as other panel members. Maintain your position if your domain evidence supports it."

For each topic (max 3 rounds per topic):
1. **Briefing**: Practitioners present pro/con perspectives
2. **Independent Statements**: Each expert generates a position statement independently — labeled **[{Expert} — independent]** — before seeing others' views. All independent statements are collected before any expert sees others' positions (prevents anchoring / echo chamber). In default (inline) mode this is best-effort via prompt contract; isolated execution mode enforces it mechanically via subagent context boundaries.
3. **Q&A / Rebuttal**: Experts question and rebut each other. Inline mode renders this as one simulated pass; isolated mode runs it as a real exchange loop — 1 independent exchange + up to 2 rebuttal exchanges (see [Isolated Execution: Rebuttal Exchanges](#isolated-execution-rebuttal-exchanges))
4. **Dialectic**: Thesis → Antithesis → Synthesis
5. **Conclusion**: Consensus or hold decision

**Round Limits**:
- Each topic has a maximum of 3 discussion rounds
- If no consensus after 3 rounds, Moderator escalates to tie-breaking
- A "round" = one complete Briefing → Independent Statements → Q&A/Rebuttal → Dialectic → Conclusion cycle
- Early stop (isolated mode): within a topic round, the rebuttal *exchange* loop (the inner Q&A/Rebuttal loop, see [Isolated Execution: Rebuttal Exchanges](#isolated-execution-rebuttal-exchanges)) may stop after any rebuttal exchange that adds no new argument — before reaching the 2-rebuttal cap. This inner loop is distinct from the 3 topic-round ceiling above

**STATE Block Contract**:

> **Core Rules**: See [../../reference/state-contract.md](../../reference/state-contract.md)

Never store thesis/antithesis/synthesis prose in the block — only the closed-enum status below;
dialectic prose lives in Phase 2 files (`docs/discussions/.../transcripts/`). This keeps the block bounded.

```
<!-- STATE:CHECKPOINT -->
Topic: {idx}/{total} | Phase: {0|1|2} | Round: {r}/3
Mode: [isolated:{on|off}] [summary-only:{on|off}]
Personas: [{P-id} ...] adhoc:{n}
Independent: {k}/{N}
Rebuttal: [t{n}:e{i}:{k}/{N}]
Topic-status: [t{n}:{pending|thesis-reached|antithesis-reached|synthesis-reached|consensus-reached|tie-broken}] ...
Citation: [t{n}:{grounded|unverified|skipped}] ...
Votes: [{expert}:{option}:{High|Medium|Low}] ...
Tie-break: [used:{yes|no}] [margin:{n|—}]
<!-- /STATE -->
```

**Field semantics, isolated-mode multi-round loop tracking, and compaction-restore defaults**: see [reference.md → STATE Block 복원 상세](reference.md) — load it before resuming a compacted isolated-mode session. Load-bearing invariants (kept here so restore is safe even before that load): `Rebuttal` is the authoritative isolated-mode loop cursor and **wins over `Independent` on any divergence**; on compaction, restore from the most recent STATE block, defaulting missing fields to the low-loss side — Mode flags → `off` (full output), Citation → `skipped`, Topic-status → `pending`, Votes → no-consensus, `Independent → 0` (re-collect) **only while `Rebuttal` is at `e1`** (at `e2`/`e3` independent collection is already done — re-running E1 would discard rebuttal progress). A missing `Personas` field is recovered by re-running the Selection Rule on the same topic text — it is deterministic, so recomputation returns the identical set (ad-hoc personas are the exception: they are session-local, so recover those from the transcript instead).

**Tie-Breaking Mechanism**:
When consensus cannot be reached after 3 rounds:
1. **Weighted Vote**: Each expert votes with confidence level (High/Medium/Low)
   - High confidence = 3 points, Medium = 2, Low = 1
   - Option with highest total points wins
2. **Moderator Summary**: Record the majority position AND dissenting rationale
3. **Conditional Approval**: If vote margin < 2 points, mark as "Conditional — requires validation"
4. **Document**: All tie-break decisions recorded in SUMMARY.md with vote breakdown

### Isolated Execution: Rebuttal Exchanges

In default (inline) mode, an entire topic — every persona's turns — is produced in one model response: a *simulated* debate where a single model scripts all voices. It is fast, but it is not a real turn exchange, and personas drift toward a single voice.

Isolated execution replaces the simulated pass with real multi-turn **exchanges** inside a single topic round's Q&A/Rebuttal step (step 3 above). An "exchange" is one synchronous fan-out across all experts (not per-expert) — it is NOT a topic round. The loop runs **1 independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)**, capped at 3 exchanges total — independent of the 3 topic-round ceiling and its tie-break trigger.

**Orchestrator vs. Moderator**: in isolated mode the mechanical work — spawning experts, assembling per-expert prompt packets, relaying between exchanges, and judging the stop condition — is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator subagent. The Moderator subagent stays visibility-limited (position summaries only) and is spawned only for Synthesis/Conclusion. This keeps the Moderator Visibility Contract intact: the orchestrator already holds every statement, so it is the one allowed to summarize and relay.

**Exchange loop**:
1. **E1 — Independent** (anchoring-free): the orchestrator spawns each expert as a separate subagent with the topic + briefing only. No expert sees another's statement. The orchestrator collects all statements.
2. **E2/E3 — Rebuttal**: the orchestrator re-spawns all experts **in parallel**, each receiving a packet of — (a) its own prior-exchange position (a re-spawned subagent is stateless; without this it cannot "hold/defend"), (b) a *summary* of the other experts' **prior-exchange** statements (never within-exchange statements — parallel re-spawn means no expert sees another's current-exchange turn, preserving anti-anchoring), and (c) the re-applied **Anti-conformity directive** (defined at the top of [Phase 1: Topic Rounds](#phase-1-topic-rounds)). Each expert then (a) holds and defends, (b) rebuts a specific point with new evidence, or (c) revises.

**Stop conditions** (whichever comes first):
- The exchange loop reaches the 2-rebuttal cap (e3 completed), or
- **No new argument**: comparing the latest exchange to the immediately prior one, *no expert* introduced a new point or a new rebuttal — a new point requires new evidence (data, counterexample, or precedent) or a new argument structure; a restated prior point does not count. The orchestrator makes this call — it needs the full per-expert statements, which the visibility-limited Moderator subagent cannot see. The test is *new arguments*, not *agreement*: an exchange where experts only echo growing agreement without new reasoning is convergence-by-conformity and also stops the loop. This guards against both runaway cost and false consensus.

After the loop stops, the orchestrator spawns the Moderator subagent with the final exchange's position summaries to compute Synthesis → Conclusion.

**Degenerate cases**:
- An expert subagent that fails or returns empty is retried once; on a second failure the exchange proceeds with the remaining experts (recorded in the transcript — never silently dropped).
- An expert added mid-discussion (see Expert Selection Guide) first runs a catch-up E1 independent statement, then joins from the next rebuttal exchange.

**Cost**: per topic, `(exchanges × experts)` expert subagents — `exchanges` = 1 (independent) + 1–2 (rebuttal), i.e. up to `3 × experts` when both rebuttal exchanges run, fewer when early-stop fires — plus 1 Moderator subagent for Synthesis. **Recovery cost**: if Phase 2 produces only a compressed final message or a content-free sign-off (e.g. due to context pressure), the user must re-request the full record — add one full-panel context reload to the effective cost. This recovery overhead is avoided by the inline SUMMARY path (lightweight sessions) and by the full 3-file output (multi-topic sessions). Choose isolated mode when independence and genuine turn exchange matter more than speed — inline mode stays the default for quick reviews.

### Phase 2: Recording

After all topics are discussed, produce output according to session scope:

**Lightweight / single-topic sessions** (default path when none of the triggers below apply):
- Produce an **inline SUMMARY** in the current conversation — consensus items, recommendations, action items, unresolved issues. No files written.
- This is sufficient for quick, single-topic reviews and avoids unnecessary file I/O for routine use.

**Full 3-file generation** is required when ANY of the following apply:
- Session covers **multiple topics** (2+)
- User explicitly requests file output ("저장해줘", "파일로", "transcript 남겨줘", etc.)
- Unresolved issues are substantial enough to warrant a persistent UNRESOLVED.md record
- Session used isolated execution mode (real turn exchanges justify persistent transcripts)

When full generation is required, write:

1. **Raw transcripts**: `docs/discussions/{YYYYMMDD}_{name}/transcripts/{순번}_{topic}.md`
   - All statements recorded chronologically (template: `templates/TRANSCRIPT_TEMPLATE.md`)
   - **Skipped in summary output mode**

2. **Summary**: `docs/discussions/{YYYYMMDD}_{name}/SUMMARY.md`
   - Consensus items, recommendations, action items (template: `templates/SUMMARY_TEMPLATE.md`)

3. **Unresolved issues**: `docs/discussions/{YYYYMMDD}_{name}/UNRESOLVED.md`
   - Detailed record of held topics (template: `templates/UNRESOLVED_TEMPLATE.md`)

**`docs/discussions/` is a local working-draft location, not a canonical record** — whether it is git-tracked is project-specific (e.g. claude-kit gitignores it as of 2026-06-13, since GitHub issues are its canonical decision record). If the discussion is tied to a GitHub issue, propose also posting the SUMMARY as a comment on that issue with a `#N` backlink — with user confirmation before posting, since a comment on a shared issue is visible to others. That comment, once confirmed, is the durable, searchable record. The local files above remain useful as session-local working material either way.

Proceed to Phase 2 immediately after all topics are discussed. In the inline path, the inline SUMMARY replaces file generation — discussion does not end without some form of output.

**Note on summary output mode**: Item 1 (raw transcripts) is skipped. SUMMARY.md (item 2) and UNRESOLVED.md (item 3) are always generated regardless of mode when full generation is triggered.

### Moderator Visibility Contract

- **Default**: Moderator receives expert position summaries only (full Q&A transcript blocked during synthesis)
- **Isolated execution mode**: Moderator spawned as separate Agent subagent; pass expert position summaries only as the subagent prompt (experts also spawned as subagents — see Execution Modes)
- **Rebuttal relay (isolated)**: between exchanges the **orchestrator** (not the Moderator subagent) assembles and forwards per-expert summary packets; the Moderator subagent is spawned only for Synthesis and still sees position summaries only (see [Isolated Execution: Rebuttal Exchanges](#isolated-execution-rebuttal-exchanges))

This prevents the Moderator from being anchored by the Q&A thread and ensures independent synthesis.

### Phase 3: Moderator Authority
- Request information from user when fact-checking is needed
- Force-close discussion when no further progress is possible
- Record unresolved issues separately

## Output Format
### Output Format details

Discussion style, the output-integrity principle (no invented citations, no emoji), the
Korean→English role-label table, and the Quick Start example live in
[reference.md](reference.md) — read it when writing the output files. Conversation examples:
[examples.md](examples.md); output templates: `templates/`.
