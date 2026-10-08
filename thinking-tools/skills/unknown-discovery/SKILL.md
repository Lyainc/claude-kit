---
name: unknown-discovery

description: |
  Discover Unknown Unknowns through iterative Socratic interviews. Systematically uncover
  blind spots in projects/plans — the answer comes out as a list of what's unknown, not a
  spec of what to build (that's build-spec). Has a Quick Discovery Mode (5-7 questions).

  Trigger when user mentions: 맹점, 놓친 것, 빠진 것, 심층 분석, 인터뷰해줘, 누락된 것, 맹점 검토,
  blind spot, unknown unknown, "내가 놓치고 있는 게 뭐야?", "이 기획에서 빠진 게 있을까?",
  빠르게 맹점만, 간단히 맹점, quick discovery.
  Routing: 만들 대상이 정해져 있고 명세로 굳혀야 하면 build-spec, 1:1 주장 공격은 adversarial-review,
  다관점 합의는 expert-panel.
allowed-tools: AskUserQuestion Read Write Agent Grep Glob Bash
effort: high
---

# Unknown Discovery

## Codex Portability

Codex: read [the native question contract](../../reference/codex-portability.md) first; await replies.

## Overview

Discover Unknown Unknowns by interview; match input language (mixed: dominant). Detail: reference.md §16.
Quick triggers: '빠르게', '간단히', 'quick'.

## Quick Discovery Mode

5-7 questions: Phase 0 without maturity detection (default Plan); Phase 1 one pass on ONE area (highest-risk, default Assumptions), 3 core + 2-4 follow-up questions, no Challenge Modes or Extended Areas, scoring that area only; Phase 2 top 3-5 findings; Phase 3 inline summary, no full template. Before emitting Quick Mode output, read reference.md §16 (Quick Discovery Mode): it defines the required output block (binding).

## Core Workflow

### Phase 0: Context Analysis

1. Analyze the target (project / document / idea).
2. Confirm the domain (Tech/Biz/Creative/Custom) via AskUserQuestion.
   - **Repo Context Intake** (target is a codebase or an idea about one): `Glob` README/CLAUDE.md/manifests, `Grep` hits for the target's keywords, ground questions in them ([reference.md](reference.md) §15); no hits → skip silently.
   - **Seed Detection**: `Glob("docs/specs/*.yaml")`; matched target → `Bash` run
     `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seed-relations.py" metadata <seed> --json` first.
     No Seed `Read`/cat before metadata; no bulk discovery reads. Unknown needs approval; paused/closed/withdrawn content
     is history, never automatically resumed. Active applies only within this request. Before
     reuse read `../../reference/seed-lifecycle.md`; closed requires a new Seed. No match → skip.
3. Detect maturity (Idea/Plan/Execution) from the input signals first ([reference.md](reference.md) §9); only when unclear, confirm via AskUserQuestion.
4. Adjust Depth weights by maturity; build the interview plan.

### Phase 1: Iterative Interview Loop

Each round targets the lowest-Depth area ([reference.md](reference.md) §7); first round is always Assumptions; ties: Assumptions > Trade-offs > Edge Cases > Blindspots. Show `[Round N] Area: {current_area}` each question (soft limit 12-15, hard 20).

**Core Areas** (2-3 questions each): Assumptions, Trade-offs, Edge Cases, Blindspots; base Korean question patterns: [reference.md](reference.md) §16.

**Interview Rules**: (1) per area: base question → follow-up → Why chain (3Q); (2) after each area, output a progress summary + STATE block; (3) an uncertainty signal marks that area's depth-check-5 as N and adds 1Q ([reference.md](reference.md) §3, §6); (4) when the Core 4 clear the Depth Gate (≥ 65% **and** depth-check-4 = Y in every entered area, §6), ask the user whether to enter Extended areas ([reference.md](reference.md) §12).

**Exploration Depth Scoring**: at each checkpoint score the just-completed area with the **6-item Y/N checklist** in [reference.md](reference.md) §6 (`area_score = Σ weight of Y items`, never a free 0-100% judgement), recording each item's Y/N plus a one-line reason in STATE `scoring_rationale`. Scoring is inline by default (`scoring_isolated: false`). **Gate-imminent round** (inline scores already satisfy the Depth Gate): re-score the same checklist in a **separate Agent subagent**, since the interviewer scoring its own interview is self-verification bias. Pass it `{each entered Core area's Q&A transcript + the §6 checklist + the findings claimed per area}`; its Y/N marks, reasons and area scores, not the inline ones, open the gate. Agent call fails / unavailable / no response (including a policy denial) → score inline, keep `scoring_isolated: false`, and add one line `[격리 채점 실패 — 자체 채점, 신뢰도 낮음]` before the progress summary (no new round, no `AskUserQuestion`), then proceed exactly as isolated mode would (#433). A subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback (#647) — never wait on it further.

**Challenge Modes** (once each, 1-2Q, [reference.md](reference.md) §8): Inverter (Round 3+), Outsider (Round 5+), Pre-mortem (Round 7+ / Depth 60%+).

### Phase 2: Synthesis

Organize the Unknown Unknowns, tag each Critical (could cause project failure) / Important (affects timeline, quality or cost) / Nice-to-have (optimization or improvement), extract key insights.

### Phase 3: Documentation & Bridge

1. 보고서 생성 ([템플릿](templates/DISCOVERY_REPORT.md)): YAML frontmatter 먼저, 서사체 본문 다음 (frontmatter 누락 시 YAML 블록을 따로 출력하고 "보고서 앞에 붙이세요" 안내). Depth 요약, 권장 액션, 인터뷰 메타데이터 포함.
2. **Post-Discovery Options** (AskUserQuestion): **Expert Panel** (Critical 발견 → `/expert-panel`), **Action Plan**, **Deep Dive** (Critical 항목으로 새 세션), **Export** (`Write`로 저장), **Seed로 넘기기** (대상 Seed가 있을 때만: 리포트 저장 후 다음 세션에서 Seed 경로 + 리포트를 `build-spec` refine mode에 넘기도록 안내; 같은 세션 왕복 금지).

## Termination Conditions

**Depth Gate** (primary): Depth ≥ 65% AND depth-check-4 = Y in every entered Core area → propose Phase 2 (user consent required). **Explicit Done** ("done", "stop", "enough", "완료", "충분해", "끝", "그만") → Depth warning if under 65%, then Phase 2. **Saturation** (3 consecutive: short response + repetition + avoidance) → show Depth + confirm. **Depth Limit** (each Core area at 2-depth) → ask about Extended areas. **Gap Check** (end of Phase 1): "Anything important we haven't covered?" **Early Exit** ("skip to results", "요약해줘", "결과만") → save state, Phase 2 with current findings. Soft Landing: Depth summary → Confirm → Close.

## State Management

Core rules: `../../reference/state-contract.md`. Numeric Depth/score fields serve compaction restoration and gate logic only; user-facing checkpoints show qualitative progress (충분/진행 중), never the raw percentage. Save state to `docs/discovery/{target}/state.md` only on user request (`templates/INTERVIEW_STATE.md`; legacy-block restore: reference.md §16).

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Domain: {domain} | Maturity: {idea|plan|execution} | Phase: {phase}
Progress: [assumptions:{status}:{score}%] [trade-offs:{status}:{score}%] [edge-cases:{status}:{score}%] [blindspots:{status}:{score}%]
Depth: {weighted_avg}% | Q: {count} | CP: {count}
Challenges: [inverter:{done|pending}] [outsider:{done|pending}] [pre-mortem:{done|pending}]
scoring_isolated: {true|false}
scoring_rationale:
  assumptions: "[depth-check-1:Y]…[depth-check-6:N] — {one-line reason}"
  trade-offs|edge-cases|blindspots: "{same shape}"

Discoveries:
1. [{C|I|N}] {finding} — {description}
<!-- /STATE -->
```

## Output Format

No decoration in generated content or results users use directly (separators, metadata tables and progress indicators are fine), unless the source has special characters or the user asks. Report template: [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md).
