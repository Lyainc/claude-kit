---
name: expert-panel

description: |
  Facilitate expert panel discussions (thesis-antithesis-synthesis): multiple expert
  personas debate a decision, optionally each argued in an isolated subagent so positions
  are independently reasoned (not one model agreeing with itself), optionally grounded in
  vault citations, converging to consensus + action items. Use when a decision needs
  several perspectives weighed against each other, not a single answer.

  Trigger when user mentions: 전문가 토론, 찬반 토론, 다관점 분석, 합의 도출, 트레이드오프 정리,
  expert panel, multi-perspective review, "전문가 관점에서 검토해줘", "다양한 관점에서 평가해줘".
  Routing: 1:1 단일 주장 공격은 adversarial-review, 맹점 발견 인터뷰는 unknown-discovery.
allowed-tools: Read Grep Write AskUserQuestion Agent Bash
effort: high
---

# Expert Panel Discussion

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

## Execution Modes

Output Korean (English if the user writes English); moved detail: reference.md § Procedure Detail. Modes (natural language):
- **격리 실행** ("엄격하게", "격리해서"): experts and Moderator are separate Agent subagents
- **요약 출력** ("요약만", "transcript 없이"): no transcripts; SUMMARY.md + UNRESOLVED.md only

Modes compose silently with each other and citation grounding; Phase 2 then picks the inline-summary path or files (isolated: always files).

## Participants

Apply reference.md § Role Contract (binding): the **facilitator** (the orchestrator) owns selection, inputs, relay, records, the stop and user questions; the **Moderator** only synthesizes, no vote (independent subagent only in isolated mode); **Optimistic / Critical Practitioner** = implementation / failure review, not separate agents, outside votes and quorum. Experts: 3–5 per topic by the `../../reference/personas.md` Selection Rule on the **user's original topic text** alone; IDs in STATE `Personas`; no match or a user-named outsider → `{Domain} Expert (ad-hoc)`, counted in `adhoc:{n}`.

### Expert Selection Guide

**Apply § Expert Selection Guide: what the Selection Rule enforces in [reference.md](reference.md) as written — that section is the binding contract** for panel size (3–5) and the ban on topping up a panel that merely *looks* implementation-heavy (#423). This paragraph is a locator, not a summary you may act from alone.

**When to add experts mid-discussion**: for an uncovered domain, the facilitator may propose an expert — **user confirmation required**, asked via AskUserQuestion and recorded in `adhoc:{n}`; without an explicit yes the rule's output stands.

## Citation Contract

An expert's **numeric or factual claim** cites one source: `vault-searcher` (Agent, Mode 3) once per topic, else an in-scope document via Read/Grep, else — vault-searcher unavailable, no result, or no response — a stated domain judgment, silently. Never invent a figure: label it assumption or estimate. A subagent with only idle notifications and no final text after one re-request counts as unavailable (#647). `Citation: unverified` escalates/deepens the topic, never `skipped`.

## Core Workflow

### Phase 0: Preparation

1. Split the target into topics; generate the agenda.
2. **Backlog prefilter (#524)**: before any expert speaks, run once via Bash on the user's original topic text: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog-prefilter.py" --intent "{review target text}"`. `[backlog-scan SKIPPED]` / `[backlog-scan PARTIAL]` → `Backlog: skipped` / `partial` (digest still given), line carried verbatim into Phase 2; else `scanned`. The digest grounds, never binds, the panel.
3. Run the Selection Rule per topic (confirm only if the user picks experts).

### Phase 1: Topic Rounds

**Anti-conformity directive** (each turn): "You are not required to reach the same conclusions as other panel members. Maintain your position if your domain evidence supports it."

Per topic: (1) **Briefing**: neutral facts and constraints, no pro/con; (2) **Independent Statements** labeled **[{Expert} — independent]**, all collected before any expert sees another's; (3) **Q&A / Rebuttal**, opened by the practitioner review; (4) **Dialectic**; (5) **Conclusion** per Topic Conclusion. **Cycle Limits**: E1 + at most 2 rebuttal exchanges. There is no outer topic-round repeat; an early stop (no new argument) ends the debate, not the decision.

**STATE Block**: closed-enum status only, no debate prose. Before writing or restoring STATE, read [reference.md → STATE Block 복원 상세](reference.md): binding template, fields and restore defaults. A record under `Records` is written *before* `Collected`/`Rebuttal` update and wins over a counter, so an expert with no record is never counted as done by inference; `Rebuttal` wins over `Independent`; missing fields default to the low-loss side.

### Topic Conclusion

Each topic ends in exactly one outcome after the rebuttal stage stops:

1. **Consensus** — unanimity allowing up to 1 minority dissent → `consensus-reached`.
2. **Weighted vote** (no consensus): each valid expert votes High = 3, Medium = 2, Low = 1 points; `margin` = the top option's points minus the runner-up's. `margin ≥ 2` → the top option wins, `tie-broken`. `margin = 1` → `tie-broken`, and SUMMARY.md marks the winner "Conditional — requires validation".
3. **Hold** — no winner is invented: `held:tie` when `margin = 0`, `held:evidence` when the Moderator judges the deciding claims unverifiable without facts the user must supply ([Phase 3](#phase-3-authority)), `held:quorum` when fewer than 3 valid experts remain after retries — then no vote runs at all. A held topic is never recorded as `tie-broken` or Conditional.

SUMMARY.md records the outcome, vote breakdown and dissent; held topics also go to UNRESOLVED.md with the reason; STATE `Topic-status`, SUMMARY.md and UNRESOLVED.md name the same outcome.

### Isolated Execution: Rebuttal Exchanges

Isolated mode runs **1 independent exchange (e1) + up to 2 rebuttal exchanges (e2, e3)** in a topic's Q&A/Rebuttal step, capped at 3 exchanges total.

**Orchestrator vs. Moderator**: spawning experts, assembling packets, relaying between exchanges, and judging the stop condition is done by the **parent orchestrator**, NOT by the Moderator subagent, which sees final position summaries and the practitioner review only and is spawned only for Synthesis/Conclusion.

**Apply § Isolated execution: exchange-loop contract in [reference.md](reference.md) as written — that section is the binding contract** for packets, exchange records, stop conditions (2-rebuttal cap, *no new argument* test), degenerate cases and **Cost**. Load it before running isolated mode; the two paragraphs above are a locator, not a summary you may act from alone.

### Phase 2: Recording

Default (single topic): an **inline SUMMARY** in the conversation (conclusion, evidence, plan, failure/stop conditions, dissent, unresolved), no files. **Full 3-file generation** when ANY applies: 2+ topics; the user asks for files; substantial unresolved issues; isolated mode. Write under `docs/discussions/{YYYYMMDD}_{name}/` (`templates/`): `transcripts/{순번}_{topic}.md`, `SUMMARY.md`, `UNRESOLVED.md`.

Output states the Phase 0 backlog result (the `[backlog-scan SKIPPED]` line verbatim, else conflicts or no-conflict; empty is not a pass). For a GitHub-issue discussion, offer a SUMMARY comment with a `#N` backlink, posted only after user confirmation. Never end without output.

### Phase 3: Authority

Facilitator: asks the user for facts, logs unresolved issues; a topic ends only via stop conditions and Topic Conclusion. Moderator: may set `held:evidence`, never alters votes, re-runs or adds experts.
