---
name: unknown-discovery

description: |
  Discover Unknown Unknowns through iterative deep interviews using AskUserQuestion.
  Systematically uncover blind spots in projects, plans, or decisions through
  Socratic questioning and adaptive follow-up.

  Use when reviewing projects, proposals, strategies, or decisions to find
  what the user might be missing or overlooking.

  Trigger when user mentions: blind spot, unknown unknown, 맹점, 놓친 것, 빠진 것, 맹점 검토,
  인터뷰해줘, 심층 분석, 누락된 것, 고려하지 못한 것,
  or requests: "내가 놓치고 있는 게 뭐야?", "이 기획에서 빠진 게 있을까?",
  "blind spot을 찾아줘", "심층 인터뷰해줘", "Unknown unknowns를 발견해줘".

  Skip for: simple Q&A, factual queries, code review (delegate to a code-reviewer agent),
  document quality review (use doc-polish), 1:1 claim attack (use adversarial-review),
  or when user wants quick answers.
allowed-tools: AskUserQuestion Read Write
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
- (Optional) `--quick` flag for Quick Discovery mode (5-7 questions, single area focus)

## Quick Discovery Mode (`--quick`)

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

**Area**: {targeted area} | **Questions**: {count} | **Depth**: {score}%

### Findings
1. [{C|I|N}] {finding}
2. [{C|I|N}] {finding}
...

───
*Quick Discovery 완료 · 전체 분석: `--quick` 없이 재실행*
```

## Core Workflow

### Phase 0: Context Analysis
<!-- Active during Phase 0 only -->

1. 대상 분석 (프로젝트/문서/아이디어)
2. 도메인 확인 (Tech/Biz/Creative/Custom) → AskUserQuestion으로 사용자 확인
3. 성숙도 감지 (Idea/Plan/Execution):
   - **자동 감지 우선**: 사용자 입력 컨텍스트에서 성숙도 신호를 분석하여 자동 판별 (상세: [reference.md](reference.md) §9)
     - 구체적 수치/일정 없음, "~할 것 같다" → Idea
     - 마일스톤/리소스/일정 언급 → Plan
     - 진행 상황/이슈/메트릭 언급 → Execution
   - **불명확 시에만** AskUserQuestion으로 사용자에게 확인
4. 성숙도에 따라 Exploration Depth 가중치 조정
5. 인터뷰 계획 수립

### Phase 1: Iterative Interview Loop
<!-- Active during Phase 1 only -->

**Dynamic Area Targeting**: 매 라운드 Exploration Depth가 가장 낮은 영역을 자동 타겟팅한다 (상세: [reference.md](reference.md) §7).

**Round Counter Display**: Each interview round shows explicit progress:
```
[Round N/~12] Area: {current_area} ({score}%) | Overall Depth: {weighted_avg}%
```
- Round count is approximate (soft limit 12-15, hard limit 20)
- Display updates at every question transition

- 첫 라운드: 항상 Assumptions (모든 발견의 기초)
- 이후: 점수 기반 최저 영역 타겟
- 동점 시: Assumptions > Trade-offs > Edge Cases > Blindspots

**Core Areas** (질문 패턴):

| Area | 기본 질문 패턴 | 질문 수 |
|------|---------------|---------|
| Assumptions | "이것이 성립하려면 어떤 전제가 필요한가요?" | 2-3 |
| Trade-offs | "이 선택으로 포기하게 되는 것은?" | 2-3 |
| Edge Cases | "10배 규모/최악의 시나리오에서 어떻게 되나요?" | 2-3 |
| Blindspots | "아직 질문하지 않은 것 중 중요한 것은?" | 2-3 |

**Interview Rules**:

1. 영역당: 기본 질문 1 → 후속 질문 1 → Why chain 1 (총 3Q)
2. Checkpoint: 매 영역 완료 시 진행 상황 요약 + STATE 블록 출력 (Exploration Depth 포함)
3. 불확실성 신호 감지 시 해당 영역 점수 10% 차감 + 1Q 추가 (상세: [reference.md](reference.md) §3, §6)
4. Core 4의 Depth ≥ 65% 도달 시: Extended 영역 진입 여부를 사용자에게 확인

**Exploration Depth Scoring**: 매 체크포인트마다 4개 영역의 탐색 깊이를 0-100%로 평가하고 가중 평균을 표시한다 (상세: [reference.md](reference.md) §6).

```
Round N | [Edge Cases:35%] ← 최저 영역 타겟팅 | Depth: 52%
```

**Challenge Modes**: 인터뷰 중 특정 시점에 관점 전환 질문을 삽입한다 (각 1회, 1-2Q). 상세: [reference.md](reference.md) §8.

| Mode | 진입 조건 | 목적 |
|------|----------|------|
| Inverter | 라운드 3+ | 핵심 가정 뒤집기 |
| Outsider | 라운드 5+ | 외부자 시각 확보 |
| Pre-mortem | 라운드 7+ / Depth 60%+ | 미래 실패 역추적 |

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
   - **Export**: 보고서를 파일로 저장

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Depth Gate** | Exploration Depth ≥ 65% | Phase 2 진입 제안 (사용자 동의 필요) |
| **Explicit Done** | "done", "stop", "enough", "완료", "충분해", "끝", "그만" | Depth 경고 표시 후 Phase 2 진행 |
| **Saturation** | 3 consecutive: short response + repetition + avoidance | Depth 표시 + confirm |
| **Depth Limit** | Each Core 4 area at 2-depth | Ask about Extended areas |
| **Gap Check** | End of Phase 1 | "Anything important we haven't covered?" |
| **Early Exit** | User says "skip to results", "요약해줘", "결과만" | Save state → skip to Phase 2 with current findings |

**Depth Gate가 주요 종료 기준**이며, Saturation은 보조 지표로 유지한다.
Explicit Done 시 Depth가 65% 미만이면 경고를 표시하되, 사용자 의사를 존중한다.

**Soft Landing**: Depth 요약 → Confirm → Close (3-step)

## State Management

Output a STATE block at every checkpoint to record progress.
On compaction, restore state from the most recent STATE block.

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

Discoveries:
1. [{C|I|N}] {finding} — {description}
<!-- /STATE -->
```

Detailed format: [templates/INTERVIEW_STATE.md](templates/INTERVIEW_STATE.md)

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Domain selection, each interview question, checkpoints | "Which domain best fits?" |
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
