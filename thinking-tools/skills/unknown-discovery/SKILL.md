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
allowed-tools: AskUserQuestion Read Write Agent Grep Glob
effort: high
---

# Unknown Discovery

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match input language
  - Korean input → Korean interview questions and report
  - English input → English interview questions and report
  - Mixed input → follow dominant language

Discover user's Unknown Unknowns (things they don't know they don't know) through deep iterative interviews.

## When to Use

- Finding blind spots in projects or proposals
- Verifying overlooked considerations before decision-making
- Validating implicit assumptions in strategies or plans
- Systematically exploring risks and trade-offs

## Prerequisites

- Analysis target (project/proposal/decision/idea)
- (Optional) Current assumptions or considerations
- Quick Discovery mode: include '빠르게', '간단히', or 'quick' in your request

## Quick Discovery Mode

Compressed interview for time-constrained analysis (5-7 questions total):

1. **Phase 0**: Context Analysis (same, but skip maturity detection — default to Plan)
2. **Phase 1**: Single-pass interview targeting ONE area:
   - Auto-select highest-risk area based on context (default: Assumptions)
   - 3 core questions + 2-4 follow-up questions
   - No Challenge Modes, no Extended Areas
   - Depth scoring for targeted area only
3. **Phase 2**: Quick synthesis (top 3-5 findings only)
4. **Phase 3**: Abbreviated report (no full template, inline summary)

Quick Mode output format:
```
## Quick Discovery — {target}

**Area**: {targeted area} | **Questions**: {count} | **Status**: 충분/진행 중

### Findings
1. [{C|I|N}] {finding}
2. [{C|I|N}] {finding}
...

───
*Quick Discovery 완료 · 전체 분석으로 재실행*
```

## Core Workflow

### Phase 0: Context Analysis
<!-- Active during Phase 0 only -->

1. Analyze the target (project / document / idea).
2. Confirm the domain (Tech/Biz/Creative/Custom) → confirm with the user via AskUserQuestion.
2a. **Repo Context Intake** (when the target is a codebase / an idea about one): `Glob("{README.md,CLAUDE.md,package.json,pyproject.toml,plugin.json,go.mod,Cargo.toml}")`, then `Grep` the hits for the target's own keywords. Feed what you find into the interview as *grounded* questions ("README says X is the only supported path — what happens when Y?") instead of abstract ones. Detail: [reference.md](reference.md) §15. No hits / not a codebase → skip silently, interview proceeds as a pure conversation.
2b. **Seed Detection** (bridge from `build-spec`): `Glob("docs/specs/*.yaml")`. If the user's target names or matches an existing Seed file (by slug or explicit path), `Read` it and treat that Seed as the interview target — its `goal`/`constraints`/`success_criteria` anchor the interview, and each area's questions probe against fields the Seed already committed to instead of starting from a blank context. Findings from this interview are meant to fold into that Seed's `blindspots[]` later via a `build-spec` refine-mode session (see [../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md)). No match → skip silently, interview proceeds as normal.
3. Detect maturity (Idea/Plan/Execution):
   - **Auto-detect first**: infer maturity from signals in the user's input context (detail: [reference.md](reference.md) §9)
     - No concrete numbers/timeline, "~할 것 같다" hedging → Idea
     - Milestones / resources / schedule mentioned → Plan
     - Progress / issues / metrics mentioned → Execution
   - **Only when unclear**, confirm with the user via AskUserQuestion.
4. Adjust Exploration Depth weights based on maturity.
5. Build the interview plan.

### Phase 1: Iterative Interview Loop
<!-- Active during Phase 1 only -->

**Dynamic Area Targeting**: each round auto-targets the area with the lowest Exploration Depth (detail: [reference.md](reference.md) §7).

**Round Counter Display**: Each interview round shows explicit progress:
```
[Round N] Area: {current_area}
```
- Round count is approximate (soft limit 12-15, hard limit 20)
- Display updates at every question transition

- First round: always Assumptions (the basis of every finding)
- After: target the lowest-scoring area
- On a tie: Assumptions > Trade-offs > Edge Cases > Blindspots

**Core Areas** (question patterns — the Korean prompts below are user-facing):

| Area | Base question pattern (user-facing) | Q count |
|------|---------------|---------|
| Assumptions | "이것이 성립하려면 어떤 전제가 필요한가요?" | 2-3 |
| Trade-offs | "이 선택으로 포기하게 되는 것은?" | 2-3 |
| Edge Cases | "10배 규모/최악의 시나리오에서 어떻게 되나요?" | 2-3 |
| Blindspots | "아직 질문하지 않은 것 중 중요한 것은?" | 2-3 |

**Interview Rules**:

1. Per area: base question 1 → follow-up 1 → Why chain 1 (3Q total)
2. Checkpoint: on completing each area, output a progress summary + STATE block (including Exploration Depth)
3. On detecting an uncertainty signal, mark that area's checklist item D5 as N (that is the 10% deduction) and add 1Q (detail: [reference.md](reference.md) §3, §6)
4. When the Core 4 clear the Depth Gate (≥ 65% **and** D4 = Y in every entered area — [reference.md](reference.md) §6), ask the user whether to enter Extended areas

**Exploration Depth Scoring** (checklist-based): at each checkpoint, score the just-completed area via the **6-item Y/N checklist** in [reference.md](reference.md) §6 — `area_score = Σ(weight of each Y item)`, never a free 0-100% judgement — and record each item's Y/N plus a one-line reason in the STATE block's `scoring_rationale`. Scoring stays inline by default; only a **gate-imminent round** escalates to isolated re-scoring — same cheap-by-default shape as `build-spec` Phase 2 (`build-spec/reference.md` §2).

**Gate-imminent round**: the checkpoint whose own inline scores already satisfy the Depth Gate (Depth ≥ 65% AND D4=Y in every entered Core area — [reference.md](reference.md) §6) — the same test as the Termination Gate itself, evaluated one step early against inline numbers.

- **Gate-imminent round only**: re-score the same checklist in a **separate Agent subagent** — the interviewer scoring its own interview is the same self-verification bias that isolated Judge removes in `adversarial-review`. Pass the subagent `{each entered Core area's Q&A transcript + the §6 checklist + the findings claimed for each area}`; it returns the 6 Y/N marks, the reasons, and the area score, per area. The same call verifies the "발견 1건 이상 도출" item, so a claimed finding is confirmed by a context that never saw it being produced. It is this recomputed result, not the inline one, that actually opens the gate.
- Every other checkpoint: `scoring_isolated: false` in STATE — inline by design, not a failure.
- **Agent call fails / unavailable / no response at a gate-imminent round (including a policy denial)** → score inline against the same checklist and keep `scoring_isolated: false` in STATE. A subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback (#647) — never wait on it further. Add one line to the checkpoint output before the progress summary:
  `[격리 채점 실패 — 자체 채점, 신뢰도 낮음]`. One line, not a new round, no `AskUserQuestion` — then
  proceed exactly as isolated mode would (#433: a self-scored Depth and an isolated one differ in
  confidence and must not render identically; rationale for skipping the approval prompt: `reference.md` §6).

```
Round N | Area: {current_area} (targeting lowest area) | 진행 중/충분
```

**Challenge Modes**: insert a perspective-shift question at a specific point in the interview (once each, 1-2Q). Detail: [reference.md](reference.md) §8.

| Mode | Entry condition | Purpose |
|------|----------|------|
| Inverter | Round 3+ | Invert a core assumption |
| Outsider | Round 5+ | Gain an outsider's view |
| Pre-mortem | Round 7+ / Depth 60%+ | Back-trace a future failure |

**Extended Areas** (user-selected):
- Feasibility | Stakeholders | Counterfactual | Dependencies

### Phase 2: Synthesis
<!-- Active during Phase 2 only -->

1. Organize discovered Unknown Unknowns
2. Priority tagging (Critical / Important / Nice-to-have):
   - **Critical**: Could this cause project failure?
   - **Important**: Does this affect timeline/quality/cost?
   - **Nice-to-have**: Is this an optimization/improvement opportunity?
3. Extract key insights

### Phase 3: Documentation & Bridge
<!-- Active during Phase 3 only -->

1. Discovery Report 생성 (템플릿: [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md)) — YAML frontmatter 블록 선행 작성 후 서사체 본문 작성. frontmatter 누락 시: YAML 블록을 별도 출력하고 "보고서 앞에 붙이세요" 안내.
2. Exploration Depth 요약 포함
3. 권장 액션 아이템 도출
4. 인터뷰 메타데이터 기록
5. **Post-Discovery Options** 제시 (AskUserQuestion):
   - **Expert Panel**: Critical 발견에 대해 다관점 전문가 토론 (`/expert-panel` 연계)
   - **Action Plan**: 발견 기반 구체적 실행 계획 작성
   - **Deep Dive**: 특정 Critical 항목에 대해 새 인터뷰 세션 시작
   - **Export**: 보고서를 `Write`로 파일에 저장
   - **Seed로 넘기기** (대상 Seed가 있을 때만 노출 — Phase 0 Seed Detection §2b 참고): 리포트를 저장하고, 다음 세션에서 그 대상 Seed 경로 + 이 리포트를 `build-spec` refine mode(`"이 스펙 다듬어줘"`)에 넘기는 방법을 안내. 왕복은 같은 세션에서 하지 않는다 — [../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md) 세 경로 참고

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Depth Gate** | Exploration Depth ≥ 65% **AND** D4(발견 1건 이상 도출) = Y in every entered Core area | Phase 2 진입 제안 (사용자 동의 필요) |
| **Explicit Done** | "done", "stop", "enough", "완료", "충분해", "끝", "그만" | Depth 경고 표시 후 Phase 2 진행 |
| **Saturation** | 3 consecutive: short response + repetition + avoidance | Depth 표시 + confirm |
| **Depth Limit** | Each Core 4 area at 2-depth | Ask about Extended areas |
| **Gap Check** | End of Phase 1 | "Anything important we haven't covered?" |
| **Early Exit** | User says "skip to results", "요약해줘", "결과만" | Save state → skip to Phase 2 with current findings |

**Depth Gate가 주요 종료 기준**이며, Saturation은 보조 지표로 유지한다.
Explicit Done 시 Depth가 65% 미만이면 경고를 표시하되, 사용자 의사를 존중한다.

**Soft Landing**: Depth 요약 → Confirm → Close (3-step)

## State Management

> **Core Rules**: See [../../reference/state-contract.md](../../reference/state-contract.md)

Numeric Depth/score fields serve compaction restoration and gate logic only; user-facing checkpoints show qualitative progress (충분/진행 중), never the raw Depth percentage.

### Legacy Format Compatibility

기존 STATE 블록은 점수 없이 상태만 기록했다:
```
Progress: [assumptions:done] [trade-offs:pending]
```
새 포맷은 점수를 포함한다:
```
Progress: [assumptions:done:75%] [trade-offs:pending:0%]
```
컴팩션 복원 시 레거시 포맷을 만나면: 상태(`done/active/pending`)만 복원하고, 점수는 상태 기반으로 추정한다 (`done`→70%, `active`→40%, `pending`→0%).

### Optional File Persistence

사용자가 인터뷰 상태를 파일로 저장하여 세션 간 재개를 원할 경우:

1. **저장**: Phase 1 체크포인트에서 사용자 요청 시 `docs/discovery/{target}/state.md`에 STATE 블록 저장
2. **재개**: 새 세션에서 저장된 파일을 읽어 인터뷰 복원
3. **트리거**: "저장해줘", "save state", "나중에 이어하자" 등

저장 시 STATE 블록 + 발견 목록 + 메타데이터를 포함한다. 상세: [templates/INTERVIEW_STATE.md](templates/INTERVIEW_STATE.md)

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Domain: {domain} | Maturity: {idea|plan|execution} | Phase: {phase}
Progress: [assumptions:{status}:{score}%] [trade-offs:{status}:{score}%] [edge-cases:{status}:{score}%] [blindspots:{status}:{score}%]
Depth: {weighted_avg}% | Q: {count} | CP: {count}
Challenges: [inverter:{done|pending}] [outsider:{done|pending}] [pre-mortem:{done|pending}]
scoring_isolated: {true|false}
scoring_rationale:
  assumptions: "[D1:Y][D2:Y][D3:N][D4:Y][D5:Y][D6:N] — {one-line reason}"
  trade-offs: "{same shape}"
  edge-cases: "{same shape}"
  blindspots: "{same shape}"

Discoveries:
1. [{C|I|N}] {finding} — {description}
<!-- /STATE -->
```

Detailed format: [templates/INTERVIEW_STATE.md](templates/INTERVIEW_STATE.md)

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Domain selection, each interview question, checkpoints | "Which domain best fits?" |
| Agent | Isolated Depth scoring + finding verification, gate-imminent checkpoint only | Pass area Q&A + §6 checklist, get Y/N marks back |
| Glob / Grep | Phase 0 Repo Context Intake only (§15) | `Glob("{README.md,CLAUDE.md,...}")` → grep for target keywords |
| (None) | Deep thinking, synthesis | Internal processing |

## Output Format

### Output Integrity Principle

**Presentation Layer** (Unicode/ASCII decorative elements allowed):
- Footer separators (`───`)
- Metadata tables
- Progress/status indicators

**Content Layer** (Unicode/ASCII decorative elements prohibited):
- Generated text content itself
- Results that users will directly use

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

### Report Template

See [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md)

## References

- **Decision criteria guide**: See [reference.md](reference.md)
- **Workflow examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder
- **Role boundary vs build-spec**: [../../reference/ud-bs-boundary.md](../../reference/ud-bs-boundary.md)

## Quick Start

```text
User: "새로운 결제 시스템 도입을 검토해줘. 놓친 게 있는지 봐줘."

→ Phase 0: Domain "Biz" + Maturity "Plan" 확인
→ Phase 1: Assumptions(30%) → Trade-offs 타겟(25%) → [Inverter] → Edge Cases(20%) → ...
   매 체크포인트마다 Depth 표시, 최저 영역 자동 타겟팅
→ Phase 2: 발견된 blind spots 정리, 우선순위 태깅
→ Phase 3: Discovery Report + Exploration Depth 요약 + Next Steps 제안

Output: Depth 72% · Critical/Important/Nice-to-have 분류된 발견 보고서
```

## Privacy Note

This interview may surface sensitive business information (strategy, financials, internal concerns). Claude does not store conversations beyond the session. Save outputs explicitly if needed for future reference.
