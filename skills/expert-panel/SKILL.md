---
name: expert-panel

description: |
  Facilitate structured expert panel discussions with dialectical analysis for decision-making.
  Simulates debates between optimistic practitioners, critical practitioners, and domain experts
  to reach consensus through thesis-antithesis-synthesis methodology.

  Use when reviewing proposals, designs, code, policies, or documents with multiple expert perspectives,
  or when the user mentions: expert panel, panel discussion, pros and cons, reach consensus,
  multi-perspective analysis, review meeting, design review, code review, trade-off analysis,
  stakeholder simulation.

  Korean triggers: 전문가 토론, 패널 논의, 찬반 토론, 합의 도출, 다관점 분석, 검토 회의, 리뷰 세션,
  장단점 분석, 트레이드오프 정리, 이해관계자 시뮬레이션.
---

# Expert Panel Discussion

Structured expert panel skill. Multiple domain experts conduct dialectical debates to reach consensus.

## Language Behavior

**Instructions**: Written in English for optimal model alignment.

**Output Language**: ALWAYS respond in the user's language.
- Detect language from user's input
- Generate all content (discussion, summaries, templates) in that language
- If ambiguous, use the language of the document being reviewed

## Participants

### Fixed (Always Present)

| Role | Description |
|------|-------------|
| **Moderator** | Facilitates discussion, controls opening/closing, requests fact-checks, records unresolved issues |
| **Optimistic Practitioner** | Advocates for proposal benefits and feasibility, suggests practical implementation approaches |
| **Critical Practitioner** | Identifies risks and limitations, provides alternative perspectives |

### Variable (User-specified)

| Role | Description |
|------|-------------|
| **Expert Panel** | 3+ domain experts specified by user (e.g., Security, UX, Performance, Legal, LLM) |

**Important**: Experts reason based on core mechanisms, metrics, and precedents of their domain (details: [reference.md](reference.md)).

## Consensus Rules

| Item | Rule |
|------|------|
| Principle | Unanimous consent (minority opinion of 1 allowed) |
| Moderator | No voting rights, facilitation authority only |
| Experts | Minimum 3 participants |
| Re-discussion | Re-discuss topic if 2+ experts oppose |

## Core Workflow

### Phase 0: Preparation
1. Analyze review target -> Split into topics
2. Confirm expert panel composition
3. Generate discussion agenda

### Phase 1: Topic Rounds
For each topic:
1. **Briefing**: Practitioners present pro/con perspectives
2. **Q&A**: Expert questions and answers
3. **Dialectic**: Thesis -> Antithesis -> Synthesis
4. **Conclusion**: Consensus or deferral decision

### Phase 2: Recording (MANDATORY)

After discussion ends, **MUST** generate the following documents:

1. **Raw Transcript**: `docs/discussions/{YYYYMMDD}_{name}/transcripts/{num}_{topic}.md`
   - Record all statements chronologically (template: `templates/TRANSCRIPT_TEMPLATE.md`)

2. **Summary**: `docs/discussions/{YYYYMMDD}_{name}/SUMMARY.md`
   - Agreed items, recommendations, action items (template: `templates/SUMMARY_TEMPLATE.md`)

3. **Unresolved Issues**: `docs/discussions/{YYYYMMDD}_{name}/UNRESOLVED.md`
   - Detailed record of deferred topics (template: `templates/UNRESOLVED_TEMPLATE.md`)

**Important**: Discussion cannot end without document generation. Proceed to Phase 2 immediately after all topics are discussed.

### Phase 3: Moderator Authority
- Request fact-checks from user when needed
- Force-close if no progress in discussion
- Record unresolved issues separately

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Conversation examples**: See [examples.md](examples.md)
- **Output templates**: See `templates/` folder

## Quick Start

```
User: "Review this API design from security/performance/UX expert perspectives"

-> Phase 0: Topic split (Authentication, Pagination, Error handling)
-> Phase 1: Pro/con debate for each topic
-> Phase 2: Record consensus and unresolved issues
-> Output: SUMMARY.md + transcripts/
```
