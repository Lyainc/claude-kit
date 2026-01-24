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

심층 인터뷰를 통해 사용자의 Unknown Unknowns(모르는 것조차 모르는 영역)를 발견하는 스킬.

## When to Use

- 프로젝트/기획안의 blind spot을 찾고 싶을 때
- 의사결정 전 놓친 고려사항을 확인하고 싶을 때
- 전략/계획의 암묵적 가정을 검증하고 싶을 때
- 리스크나 트레이드오프를 체계적으로 탐색하고 싶을 때

## Prerequisites

- 분석 대상 (프로젝트/기획안/결정/아이디어)
- (Optional) 현재까지의 가정이나 고려사항

## Core Workflow

### Phase 0: Context Analysis

1. 대상 분석 (프로젝트/문서/아이디어)
2. 도메인 추론 → AskUserQuestion으로 확인
3. 질문 영역 프리셋 선택 (Tech/Biz/Creative/Custom)
4. 인터뷰 계획 수립

**Domain Presets**:

| Preset | Focus Areas | Specialized Questions |
|--------|-------------|----------------------|
| **Tech** | Edge Cases, Dependencies | Performance, scalability, security |
| **Biz** | Stakeholders, Trade-offs | ROI, market, competition, legal |
| **Creative** | Assumptions, Counterfactual | Originality, acceptance, trends |
| **Custom** | User-defined | User-specified areas |

### Phase 1: Iterative Interview Loop

**Core 4 Areas** (Required):

| Area | Purpose | Question Pattern |
|------|---------|-----------------|
| **Assumptions** | Uncover implicit premises | "What assumptions must be true for this to work?" |
| **Trade-offs** | Explore sacrificed values | "What are you giving up with this choice?" |
| **Edge Cases** | Explore extreme scenarios | "What happens at 10x scale?" |
| **Blindspots** | Meta-cognition | "What important question haven't I asked?" |

**Extended 4 Areas** (Optional):

| Area | Question Pattern |
|------|-----------------|
| **Feasibility** | "What's the biggest technical/resource barrier?" |
| **Stakeholders** | "Who might oppose this decision?" |
| **Counterfactual** | "What completely different approach could work?" |
| **Dependencies** | "If this fails, what else breaks?" |

**Interview Rules**:

1. **Why Chain**: After each answer, ask "Why do you think so?" (1x mandatory)
2. **Adaptive Selection**: On uncertainty signals (hedging, avoidance), dive deeper
3. **Checkpoint**: After completing each Core area OR every 4-5 questions, summarize and confirm
4. **Progress Display**: Show `[Area 2/4 | Q5]` format

### Phase 2: Synthesis

1. Organize discovered Unknown Unknowns
2. Tag priorities using decision tree:
   - **Critical**: Would this cause project failure if unaddressed?
   - **Important**: Would this significantly impact timeline/quality/cost?
   - **Nice-to-have**: Is this an optimization or enhancement?
3. Extract key insights

### Phase 3: Documentation

1. Generate Discovery Report
2. Derive recommended action items
3. Record interview metadata

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Explicit Done** | "done", "stop", "enough", "완료", "충분해", "끝", "그만" | Proceed to Phase 2 |
| **Saturation** | 3 consecutive: short response + repetition + avoidance | "Covered core areas" + confirm |
| **Depth Limit** | Each Core 4 area at 2-depth | Ask about Extended areas |
| **Gap Check** | End of Phase 1 | "Anything important we haven't covered?" |

**Soft Landing**: Summary → Confirm → Close (3-step)

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
- Examples: brand names, document body, discussion conclusions

**Exceptions**:
- Original source already contains special characters
- User explicitly requests emoji/special characters

### Report Template

See [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md)

```markdown
# Unknown Unknowns Discovery Report

**Target**: [Analysis Target]
**Date**: YYYY-MM-DD
**Domain**: [Tech/Biz/Creative]

## 1. Discovered Unknown Unknowns

### Critical
- [ ] [Finding 1]: [Description] → **Action**: [Recommended action]

### Important
- [ ] [Finding 2]: [Description] → **Action**: [Recommended action]

### Nice-to-have
- [ ] [Finding 3]: [Description]

## 2. Key Insights

1. [Insight 1]
2. [Insight 2]

## 3. Recommended Follow-ups

| # | Action | Priority | Owner |
|---|--------|----------|-------|
| 1 | | | |
```

## References

- **Design document**: See [/docs/UNKNOWN_DISCOVERY_DESIGN.md](/docs/UNKNOWN_DISCOVERY_DESIGN.md)
- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder

## Quick Start

```text
User: "새로운 결제 시스템 도입을 검토해줘. 놓친 게 있는지 봐줘."

→ Phase 0: Domain 확인 (Tech? Biz?) → "Biz" 선택
→ Phase 1: Iterative Interview
   Q1: "이 결제 시스템이 성공하려면 어떤 전제가 필요한가요?" (Assumptions)
   Q2: "왜 그 전제가 맞다고 생각하시나요?" (Why chain)
   Q3: "이 선택으로 포기하게 되는 것은?" (Trade-offs)
   ...
   [Checkpoint at Q4]: "지금까지 가정과 트레이드오프를 다뤘습니다. 계속할까요?"
   ...
→ Phase 2: 발견된 6개 blind spots 정리, 우선순위 태깅
→ Phase 3: Discovery Report 생성

Output:
- Critical: 기존 고객 이탈 리스크 미고려
- Important: 법적 규제 확인 필요
- Nice-to-have: 경쟁사 대응 전략
```

## Privacy Note

This interview may surface sensitive business information (strategy, financials, internal concerns). Claude does not store conversations beyond the session. Save outputs explicitly if needed for future reference.
