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

| Flag | Behavior |
|------|----------|
| _(default)_ | Inline: all roles simulated in main context |
| `--deep` | Each expert and Moderator spawned as separate Agent subagents (stronger isolation) |
| `--brief` | Skip transcript generation (Phase 2 item 1); produce SUMMARY.md + UNRESOLVED.md only |

Flags are combinable (e.g., `--deep --brief`).

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
2. **Independent Statements**: Each expert generates a position statement independently — labeled **[{Expert} — independent]** — before seeing others' views. All independent statements are collected before any expert sees others' positions (prevents anchoring / echo chamber). In default (inline) mode this is best-effort via prompt contract; `--deep` enforces it mechanically via subagent context boundaries.
3. **Q&A**: Experts ask questions and exchange answers (max 2 exchanges per expert)
4. **Dialectic**: Thesis → Antithesis → Synthesis
5. **Conclusion**: Consensus or hold decision

**Round Limits**:
- Each topic has a maximum of 3 discussion rounds
- If no consensus after 3 rounds, Moderator escalates to tie-breaking
- A "round" = one complete Briefing → Independent Statements → Q&A → Dialectic → Conclusion cycle

**Tie-Breaking Mechanism**:
When consensus cannot be reached after 3 rounds:
1. **Weighted Vote**: Each expert votes with confidence level (High/Medium/Low)
   - High confidence = 3 points, Medium = 2, Low = 1
   - Option with highest total points wins
2. **Moderator Summary**: Record the majority position AND dissenting rationale
3. **Conditional Approval**: If vote margin < 2 points, mark as "Conditional — requires validation"
4. **Document**: All tie-break decisions recorded in SUMMARY.md with vote breakdown

### Phase 2: Recording (MANDATORY)

The following documents MUST be generated after discussion ends:

1. **Raw transcripts**: `docs/discussions/{YYYYMMDD}_{name}/transcripts/{순번}_{topic}.md`
   - All statements recorded chronologically (template: `templates/TRANSCRIPT_TEMPLATE.md`)
   - **Skipped in `--brief` mode**

2. **Summary**: `docs/discussions/{YYYYMMDD}_{name}/SUMMARY.md`
   - Consensus items, recommendations, action items (template: `templates/SUMMARY_TEMPLATE.md`)

3. **Unresolved issues**: `docs/discussions/{YYYYMMDD}_{name}/UNRESOLVED.md`
   - Detailed record of held topics (template: `templates/UNRESOLVED_TEMPLATE.md`)

**Important**: Discussion cannot end without document generation. Proceed to Phase 2 immediately after all topics are discussed.

**Note on `--brief` mode**: Item 1 (raw transcripts) is skipped. SUMMARY.md (item 2) and UNRESOLVED.md (item 3) are always generated regardless of mode.

### Moderator Visibility Contract

- **Default**: Moderator receives expert position summaries only (full Q&A transcript blocked during synthesis)
- **`--deep` mode**: Moderator spawned as separate Agent subagent; pass expert position summaries only as the subagent prompt (experts also spawned as subagents — see Execution Modes)

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
