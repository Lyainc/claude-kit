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
allowed-tools: Read Grep Write AskUserQuestion Agent Bash
effort: high
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

**Important — role-prompt differentiation is the diversity source** (not extra spawns/temperature): every role needs a **distinct stance**, **distinct evaluation criteria**, and a **distinct voice** — pre-differentiated for variable roles by the shared pool ([personas.md](../../reference/personas.md)), so an ad-hoc persona is the only place this has to be authored per session. Easy agreement between roles may be conformity, not aligned evidence — re-validate against each role's own criteria (Anti-conformity directive, [Phase 1](#phase-1-topic-rounds)). Full rationale + the rejected full-spawn-default alternative: [reference.md](reference.md).

### Expert Selection Guide

The Selection Rule produces the panel outright; there is no judgment step here — the single
departure is an explicit user override. **Apply § Expert Selection Guide: what the Selection Rule
enforces in [reference.md](reference.md) as written — that section is the binding contract** for
panel size (3–5), domain overlap, perspective balance and rotation, including the standing ban on
topping up a panel that merely *looks* implementation-heavy (#423). This paragraph is a locator,
not a summary you may act from alone, and this whole section is pinned VERBATIM by
`_SKILL_SELECTION_SECTION` in `thinking-tools/scripts/test/test-mode-compose.py`.

**When to add experts mid-discussion**: If a topic reveals an uncovered domain (e.g., legal implications emerge during a technical review), Moderator may propose adding a domain expert — **user confirmation required**, asked via AskUserQuestion and recorded in `adhoc:{n}`. This is the user-override path, not a selection judgment: without the user's explicit yes the rule's output stands unchanged.

## Citation Contract

When an expert states a **numeric or factual claim** (statistics, performance figures, failure rates, legal citations, precedents), it must cite exactly one grounding source:

1. **Preferred**: call `vault-searcher` (Agent tool, Mode 3 — Keyword Search) once per topic to surface relevant past decisions or notes. Cache returned excerpts for reuse within the same topic — do NOT re-query per round. Search target: user's vault `notes/`, preferring `type: decision`.
2. **Fallback**: cite a named document or file already in scope via Read/Grep (e.g., a design doc the user provided for this session).
3. **Inline fallback**: if vault-searcher is unavailable / returns 0 relevant results / the Agent call fails or returns no response, fall back to the existing inline behavior — the expert states the claim as a domain judgment. Do NOT announce the fallback to the user; session behavior must look identical. A subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback (#647) — never wait on it further.

**Token budget**: vault-searcher call + section-only excerpts + max 3 results keeps this step within **~+1500 tokens** of per-topic overhead (mirrors the adversarial-review grounding budget precedent). Never re-query per rebuttal exchange, never request full notes.

**Citation-coverage escalation signal**: a consensus topic recorded `Citation: unverified` (grounding attempted, none found) escalates/deepens instead of being marked easy — catches false-consensus. Fires only on `unverified`, never on `skipped` (an unavailable vault-searcher must not make standalone sessions silently longer). Field semantics: [reference.md → STATE Block 복원 상세](reference.md).

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
2. **Backlog prefilter scan (#524)**: use Bash to run the prefilter once, before any expert speaks, on the user's original topic text (before splitting):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog-prefilter.py" --intent "{review target text}"
   ```
   `[backlog-scan SKIPPED]` output → record `Backlog: skipped`, carry that line verbatim into Phase 2. A `[backlog-scan PARTIAL]` prefix (#561 — one side's `gh` fetch failed while the other rendered normally) → record `Backlog: partial`, carry that line verbatim into Phase 2 too, and still give the rendered digest below it to every expert — PARTIAL means one side is unconfirmed, not that nothing rendered. Otherwise record `Backlog: scanned` and give the digest to every expert as grounding, same status as [Citation Contract](#citation-contract) sources — never a verdict the panel is bound to. Rationale + zero-cost note: [reference.md](reference.md).
3. Run the [personas.md](../../reference/personas.md) Selection Rule on each topic's text → panel composition (confirm with the user only when they asked to pick the experts themselves)
4. Generate discussion agenda

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
Backlog: {scanned|partial|skipped}
Personas: [{P-id} ...] adhoc:{n}
Independent: {k}/{N}
Rebuttal: [t{n}:e{i}:{k}/{N}]
Topic-status: [t{n}:{pending|thesis-reached|antithesis-reached|synthesis-reached|consensus-reached|tie-broken}] ...
Citation: [t{n}:{grounded|unverified|skipped}] ...
Votes: [{expert}:{option}:{High|Medium|Low}] ...
Tie-break: [used:{yes|no}] [margin:{n|—}]
<!-- /STATE -->
```

**Field semantics, isolated-mode multi-round loop tracking, and compaction-restore defaults**: see [reference.md → STATE Block 복원 상세](reference.md) — load it before resuming a compacted isolated-mode session. Load-bearing invariants (kept here so restore is safe even before that load): `Rebuttal` is the authoritative isolated-mode loop cursor and **wins over `Independent` on any divergence**; on compaction, restore from the most recent STATE block, defaulting missing fields to the low-loss side — Mode flags → `off` (full output), Backlog → `skipped`, Citation → `skipped`, Topic-status → `pending`, Votes → no-consensus, `Independent → 0` (re-collect) **only while `Rebuttal` is at `e1`** (at `e2`/`e3` independent collection is already done — re-running E1 would discard rebuttal progress). A missing `Personas` field is recovered by re-running the Selection Rule on the same topic text — it is deterministic, so recomputation returns the identical set (ad-hoc personas are the exception: they are session-local, so recover those from the transcript instead).

**Tie-Breaking Mechanism**:
When consensus cannot be reached after 3 rounds:
1. **Weighted Vote**: Each expert votes with confidence level (High/Medium/Low)
   - High confidence = 3 points, Medium = 2, Low = 1
   - Option with highest total points wins
2. **Moderator Summary**: Record the majority position AND dissenting rationale
3. **Conditional Approval**: If vote margin < 2 points, mark as "Conditional — requires validation"
4. **Document**: All tie-break decisions recorded in SUMMARY.md with vote breakdown

### Isolated Execution: Rebuttal Exchanges

Isolated execution replaces inline mode's *simulated* debate (one model scripting all voices in one response) with real multi-turn **exchanges** inside a single topic round's Q&A/Rebuttal step (step 3 above). An "exchange" is one synchronous fan-out across all experts (not per-expert) — it is NOT a topic round. The loop runs **1 independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)**, capped at 3 exchanges total — independent of the 3 topic-round ceiling and its tie-break trigger.

**Orchestrator vs. Moderator**: the mechanical work — spawning experts, assembling per-expert prompt packets, relaying between exchanges, and judging the stop condition — is done by the **parent orchestrator** (the facilitating main context), NOT by the Moderator subagent, which stays visibility-limited (position summaries only) and is spawned only for Synthesis/Conclusion.

**Apply § Isolated execution: exchange-loop contract in [reference.md](reference.md) as written — that section is the binding contract** for the E1/E2 packet composition, both stop conditions (the 2-rebuttal cap and the *no new argument* test), the degenerate cases, and the per-topic **Cost** including **Recovery cost**. Load it before running isolated mode; the two paragraphs above are a locator, not a summary you may act from alone. This whole section is pinned VERBATIM by `_SKILL_ISOLATED_SECTION` in `thinking-tools/scripts/test/test-mode-compose.py`: the always-loaded body outranks an on-demand doc at runtime, so it may not drift from the section it points at.

### Phase 2: Recording

After all topics are discussed, produce output according to session scope:

**Lightweight / single-topic sessions** (default path when none of the triggers below apply):
- Produce an **inline SUMMARY** in the current conversation — consensus items, recommendations, action items, unresolved issues. No files written.
- This is sufficient for quick, single-topic reviews and avoids unnecessary file I/O for routine use.

**Backlog scan carry-over (#524)**: state the Phase 0 backlog result in the output — the
`[backlog-scan SKIPPED]` line verbatim if skipped, else one line naming conflicts or a no-conflict
statement. An empty field is not a pass (mirrors `build-spec`'s `context.backlog_scan`, #489).

**Full 3-file generation** is required when ANY of the following apply:
- Session covers **multiple topics** (2+)
- User explicitly requests file output ("저장해줘", "파일로", "transcript 남겨줘", etc.)
- Unresolved issues are substantial enough to warrant a persistent UNRESOLVED.md record
- Session used isolated execution mode (real turn exchanges justify persistent transcripts)

When full generation is required, Write each of these three files:

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
