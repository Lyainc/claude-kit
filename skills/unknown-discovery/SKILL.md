---
name: unknown-discovery

description: |
  Discover Unknown Unknowns through iterative deep interviews using AskUserQuestion.
  Systematically uncover blind spots in projects, plans, or decisions through
  Socratic questioning and adaptive follow-up.

  Use when reviewing projects, proposals, strategies, or decisions to find
  what the user might be missing or overlooking.

  Trigger when user mentions: blind spot, unknown unknown, 맹점, 놓친 것, 빠진 것, 검토해줘,
  인터뷰해줘, 심층 분석, 누락된 것, 고려하지 못한 것,
  or requests: "내가 놓치고 있는 게 뭐야?", "이 기획에서 빠진 게 있을까?",
  "blind spot을 찾아줘", "심층 인터뷰해줘", "Unknown unknowns를 발견해줘".

  Skip for: simple Q&A, factual queries, or when user wants quick answers.
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

## Core Workflow

### Phase 0: Context Analysis
<!-- Active during Phase 0 only -->

1. Analyze target (project/document/idea)
2. Confirm domain (Tech/Biz/Creative/Custom) → verify with user via AskUserQuestion
3. Establish interview plan

### Phase 1: Iterative Interview Loop
<!-- Active during Phase 1 only -->

**Traversal Order** (fixed):

| # | Area | Base Question Pattern | Question Count |
|---|------|-----------------------|----------------|
| 1 | Assumptions | "What prerequisites must hold for this to succeed?" | 2-3 |
| 2 | Trade-offs | "What are you giving up with this choice?" | 2-3 |
| 3 | Edge Cases | "What happens at 10x scale or worst-case scenario?" | 2-3 |
| 4 | Blindspots | "What important thing haven't we asked about yet?" | 2-3 |

**Interview Rules**:

1. Per area: base question 1 → follow-up 1 → Why chain 1 (total 3Q)
2. Checkpoint: output progress summary + STATE block after each area completion
3. On uncertainty signal detection, add 1Q to that area (details: [reference.md](reference.md) §3)
4. After Core 4 complete: confirm with user whether to enter Extended areas

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

### Phase 3: Documentation
<!-- Active during Phase 3 only -->

1. Generate Discovery Report (template: [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md))
2. Derive recommended action items
3. Record interview metadata

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Explicit Done** | "done", "stop", "enough", "완료", "충분해", "끝", "그만" | Proceed to Phase 2 |
| **Saturation** | 3 consecutive: short response + repetition + avoidance | Confirm "Covered core areas" then transition |
| **Depth Limit** | Each Core 4 area at 2-depth | Ask about Extended areas |
| **Gap Check** | End of Phase 1 | "Anything important we haven't covered?" |

**Soft Landing**: Summary → Confirm → Close (3-step)

## State Management

Output a STATE block at every checkpoint to record progress.
On compaction, restore state from the most recent STATE block.

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Domain: {domain} | Phase: {phase}
Progress: [assumptions:{status}] [trade-offs:{status}] [edge-cases:{status}] [blindspots:{status}]
Q: {count} | CP: {count}

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

→ Phase 0: Domain 확인 → "Biz" 선택
→ Phase 1: Assumptions → Trade-offs → Edge Cases → Blindspots (각 2-3Q)
→ Phase 2: 발견된 blind spots 정리, 우선순위 태깅
→ Phase 3: Discovery Report 생성

Output: Critical/Important/Nice-to-have 분류된 발견 보고서
```

## Privacy Note

This interview may surface sensitive business information (strategy, financials, internal concerns). Claude does not store conversations beyond the session. Save outputs explicitly if needed for future reference.
