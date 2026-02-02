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
<!-- Active during Phase 0 only -->

1. 대상 분석 (프로젝트/문서/아이디어)
2. 도메인 확인 (Tech/Biz/Creative/Custom) → AskUserQuestion으로 사용자 확인
3. 인터뷰 계획 수립

### Phase 1: Iterative Interview Loop
<!-- Active during Phase 1 only -->

**순회 순서** (고정):

| # | Area | 기본 질문 패턴 | 질문 수 |
|---|------|---------------|---------|
| 1 | Assumptions | "이것이 성립하려면 어떤 전제가 필요한가요?" | 2-3 |
| 2 | Trade-offs | "이 선택으로 포기하게 되는 것은?" | 2-3 |
| 3 | Edge Cases | "10배 규모/최악의 시나리오에서 어떻게 되나요?" | 2-3 |
| 4 | Blindspots | "아직 질문하지 않은 것 중 중요한 것은?" | 2-3 |

**Interview Rules**:

1. 영역당: 기본 질문 1 → 후속 질문 1 → Why chain 1 (총 3Q)
2. Checkpoint: 매 영역 완료 시 진행 상황 요약 + STATE 블록 출력
3. 불확실성 신호 감지 시 해당 영역 1Q 추가 (상세: [reference.md](reference.md) §3)
4. Core 4 완료 후: Extended 영역 진입 여부를 사용자에게 확인

**Extended Areas** (사용자 선택 시):
- Feasibility | Stakeholders | Counterfactual | Dependencies

### Phase 2: Synthesis
<!-- Active during Phase 2 only -->

1. 발견된 Unknown Unknowns 정리
2. 우선순위 태깅 (Critical / Important / Nice-to-have):
   - **Critical**: 프로젝트 실패 가능성이 있는가?
   - **Important**: 타임라인/품질/비용에 영향을 주는가?
   - **Nice-to-have**: 최적화/개선 기회인가?
3. 핵심 인사이트 추출

### Phase 3: Documentation
<!-- Active during Phase 3 only -->

1. Discovery Report 생성 (템플릿: [templates/DISCOVERY_REPORT.md](templates/DISCOVERY_REPORT.md))
2. 권장 액션 아이템 도출
3. 인터뷰 메타데이터 기록

## Termination Conditions

| Condition | Detection | Action |
|-----------|-----------|--------|
| **Explicit Done** | "done", "stop", "enough", "완료", "충분해", "끝", "그만" | Proceed to Phase 2 |
| **Saturation** | 3 consecutive: short response + repetition + avoidance | "Covered core areas" + confirm |
| **Depth Limit** | Each Core 4 area at 2-depth | Ask about Extended areas |
| **Gap Check** | End of Phase 1 | "Anything important we haven't covered?" |

**Soft Landing**: Summary → Confirm → Close (3-step)

## State Management

매 Checkpoint마다 STATE 블록을 출력하여 진행 상태를 기록한다.
Compaction 발생 시 가장 최근 STATE 블록에서 상태를 복원한다.

```
<!-- STATE:CHECKPOINT -->
Target: {name} | Domain: {domain} | Phase: {phase}
Progress: [assumptions:{status}] [trade-offs:{status}] [edge-cases:{status}] [blindspots:{status}]
Q: {count} | CP: {count}

Discoveries:
1. [{C|I|N}] {finding} — {description}
<!-- /STATE -->
```

상세 형식: [templates/INTERVIEW_STATE.md](templates/INTERVIEW_STATE.md)

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

- **판단 기준 가이드**: See [reference.md](reference.md)
- **워크플로우 예시**: See [examples.md](examples.md)
- **출력 템플릿**: See `templates/` folder

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
