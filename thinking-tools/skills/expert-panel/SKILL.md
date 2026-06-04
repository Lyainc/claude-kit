---
name: expert-panel

description: |
  Facilitate structured expert panel discussions with dialectical analysis for decision-making.
  Simulates domain-specialist debates (thesis-antithesis-synthesis) and produces consensus + action items.

  Trigger when user mentions: 전문가 토론, 찬반 토론, 다관점 분석, 합의 도출, 트레이드오프 정리,
  expert panel, multi-perspective review, "전문가 관점에서 검토해줘", "다양한 관점에서 평가해줘".
  Routing: 1:1 단일 주장 공격은 adversarial-review, 맹점 발견 인터뷰는 unknown-discovery.
allowed-tools: Read Write AskUserQuestion Agent
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

All combinations compose silently.

## Participants

### Fixed (Always Present)

| Role | Description |
|------|-------------|
| **Moderator** | Facilitates discussion, open/close authority, fact-check requests, unresolved issue tracking |
| **Optimistic Practitioner** | Advocates proposal benefits and feasibility, proposes realistic implementation paths |
| **Critical Practitioner** | Identifies risks and limitations, provides alternative perspectives |

### Variable (User-specified)

| Role | Description |
|------|-------------|
| **Expert Panel** | 3+ domain experts specified by user (e.g., Security, UX, Performance, Legal, LLM) |

**Important**: Experts reason based on core mechanisms, metrics, and precedents from their domain (details: [reference.md](reference.md)).

### Expert Selection Guide

| Criteria | Recommendation |
|----------|---------------|
| Topic count | Min 3 experts, max 7 (diminishing returns beyond 7) |
| Domain overlap | At least 1 expert per major topic area |
| Perspective balance | Include at least 1 implementation-focused + 1 strategy-focused expert |
| Rotation | For 5+ topics, rotate 1-2 experts per topic to maintain focus |

**When to add experts mid-discussion**: If a topic reveals an uncovered domain (e.g., legal implications emerge during a technical review), Moderator may propose adding a domain expert with user confirmation.

## Consensus Rules

| Item | Rule |
|------|------|
| Principle | Unanimity (allows up to 1 minority dissent) |
| Moderator | No voting rights, facilitation authority only |
| Experts | Minimum 3 experts required |
| Re-discussion | Re-discuss topic if 2+ experts object |

## Core Workflow

### Phase 0: Preparation
1. Analyze the review target → split into topics
2. Confirm expert panel composition
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

Output a STATE block at the end of each topic round and at every checkpoint.
On context compaction, restore state from the most recent STATE block.

**The entire STATE block is internal restoration scaffolding — never rendered to the user.**
Never store thesis/antithesis/synthesis prose in the block — only the closed-enum status below;
dialectic prose lives in Phase 2 files (`docs/discussions/.../transcripts/`). This keeps the block bounded.

```
<!-- STATE:CHECKPOINT -->
Topic: {idx}/{total} | Phase: {0|1|2} | Round: {r}/3
Mode: [isolated:{on|off}] [summary-only:{on|off}]
Independent: {k}/{N}
Rebuttal: [t{n}:e{i}:{k}/{N}]
Topic-status: [t{n}:{pending|thesis-reached|antithesis-reached|synthesis-reached|consensus-reached|tie-broken}] ...
Votes: [{expert}:{option}:{High|Medium|Low}] ...
Tie-break: [used:{yes|no}] [margin:{n|—}]
<!-- /STATE -->
```

**Field write/read points**:
- `Mode` — set at Phase 0 (mode detection); read at Phase 2 item 1 (transcript skip in summary-only mode).
- `Independent` — updated during Phase 1 Independent Statements; `k==N` means collection complete (single format; no separate "complete" token).
- `Rebuttal` (isolated mode only) — topic `n`, exchange index `e{i}` (`e1` = independent, `e2`/`e3` = up to 2 rebuttal exchanges), and `{k}/{N}` experts collected in the current exchange — updated after each expert is collected, so `k` may be partial mid-exchange (e.g. `e1:1/3` after the first of three). Bounded counters only — never statement prose. Empty/omitted in inline mode. In isolated mode the `Rebuttal` cursor is the authoritative loop-position source — recorded in the STATE block in **all** modes (including isolated + summary-only, since it is not a transcript); `Independent` is the inline-mode tracker and only a redundant mirror at `e1`. On any divergence (e.g. a partial write interrupted by compaction), `Rebuttal` wins (it also distinguishes `e2`/`e3`).
- `Votes` — populated only by the Tie-Breaking Mechanism (after round 3); empty before tie-break.
- `Topic-status` — closed enum, exactly these 6 values; no free-text. `tie-broken` = resolved via the Tie-Breaking Mechanism (weighted vote always yields a winner; a margin < 2 is recorded as "Conditional" in SUMMARY.md but the status stays `tie-broken`). There is no separate `deadlock` value — the vote is total, so a topic never ends unresolved.

**Compaction restore fallback**: restore from the most recent STATE block. Defaults for missing fields —
Topic-status → `pending`; Votes → treat as no-vote / no-consensus; Independent → `0` (re-collect, preserves anti-anchoring);
Mode flags → both `off` (full output — over-producing transcripts is safer than losing user content).
In isolated mode the in-progress exchange is restored from the `Rebuttal` cursor — NOT from transcripts (those are written only in Phase 2, and skipped entirely in summary-only mode, so they do not exist mid-loop). When `Rebuttal` shows `e{i}` with `i>=2`, independent collection is already complete: do NOT apply the `Independent → 0` re-collect default above (that default applies only while the loop is still at `e1`) — re-running E1 would discard completed rebuttal progress. Conversely, when `Rebuttal` shows `e1`, independent collection is still in progress, so the `Independent → 0` re-collect default applies as usual — any partial e1 statements are re-collected from scratch, preserving anti-anchoring.

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

**Cost**: per topic, `(exchanges × experts)` expert subagents — `exchanges` = 1 (independent) + 1–2 (rebuttal), i.e. up to `3 × experts` when both rebuttal exchanges run, fewer when early-stop fires — plus 1 Moderator subagent for Synthesis. Choose isolated mode when independence and genuine turn exchange matter more than speed — inline mode stays the default for quick reviews.

### Phase 2: Recording (MANDATORY)

The following documents MUST be generated after discussion ends:

1. **Raw transcripts**: `docs/discussions/{YYYYMMDD}_{name}/transcripts/{순번}_{topic}.md`
   - All statements recorded chronologically (template: `templates/TRANSCRIPT_TEMPLATE.md`)
   - **Skipped in summary output mode**

2. **Summary**: `docs/discussions/{YYYYMMDD}_{name}/SUMMARY.md`
   - Consensus items, recommendations, action items (template: `templates/SUMMARY_TEMPLATE.md`)

3. **Unresolved issues**: `docs/discussions/{YYYYMMDD}_{name}/UNRESOLVED.md`
   - Detailed record of held topics (template: `templates/UNRESOLVED_TEMPLATE.md`)

**Important**: Discussion cannot end without document generation. Proceed to Phase 2 immediately after all topics are discussed.

**Note on summary output mode**: Item 1 (raw transcripts) is skipped. SUMMARY.md (item 2) and UNRESOLVED.md (item 3) are always generated regardless of mode.

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

### Discussion Style

Use clean, professional formatting without emoji:

| Element | Format | Example |
|---------|--------|---------|
| Topic header | `### TOPIC N: {title}` | `### TOPIC 1: 인증 방식` |
| Speaker | `**[Role]**:` | `**[Optimistic Practitioner]**:` |
| Conclusion | `**결론**:` or `**결론**: 보류` | `**결론**: JWT + Refresh Token 방식 합의` |
| Footer | `───` + metadata | `*3개 토픽 논의 완료 · 2개 합의, 1개 보류*` |

### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Metadata tables
- Progress/status indicators

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Generated text content itself
- Results that users will directly use
- Examples: brand names, document body, discussion conclusions

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

### Role Labels (English)

| Korean | English |
|--------|---------|
| 긍정적 실무자 | Optimistic Practitioner |
| 부정적 실무자 | Critical Practitioner |
| 모더레이터 | Moderator |
| 보안전문가 | Security Expert |
| 성능전문가 | Performance Expert |
| UX전문가 | UX Expert |
| (기타 도메인) | {Domain} Expert |

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Conversation examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder

## Quick Start

```
User: "이 API 설계 문서를 보안/성능/UX 전문가 관점에서 검토해줘"

→ Phase 0: 토픽 분할 (인증, 페이지네이션, 에러처리)
→ Phase 1: 각 토픽별 찬반 토론 진행
→ Phase 2: 합의사항 및 미해결 이슈 기록
→ Output: SUMMARY.md + transcripts/
```
