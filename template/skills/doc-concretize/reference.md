# Document Concretization - Reference

Detailed procedures and guidelines.

## Table of Contents

- [Phase 1: Segmentation Details](#phase-1-segmentation-details)
- [Phase 2: Recursive Build Details](#phase-2-recursive-build-details)
- [Phase 3: Final Review Details](#phase-3-final-review-details)
- [Phase 4: Polish Details](#phase-4-polish-details)
- [Language-Specific Polish](#language-specific-polish)
- [Threshold Criteria](#threshold-criteria)
- [State Tracking JSON Schema](#state-tracking-json-schema)

---

## Phase 1: Segmentation Details

### Semantic Unit Identification Criteria

| Criterion | Description | Example |
|-----------|-------------|---------|
| Independent concept | Unit that can stand alone | "Customer focus" vs "Fast execution" |
| Logical transition | Point where topic or perspective shifts | Cause→Effect, Present→Future |
| Structural division | Units separated by document format | Background/Body/Conclusion |

### Chunk Count Guidelines

| Estimated Length | Recommended Chunks |
|------------------|-------------------|
| 800-1,200 chars | 3 |
| 1,200-2,000 chars | 4-5 |
| 2,000+ chars | 5-7 |

### Ordering Patterns

1. **Deductive**: Principle → Details → Examples
2. **Inductive**: Observation → Analysis → Principle derivation
3. **Chronological**: Past → Present → Future
4. **Priority**: Core → Secondary → Optional

---

## Phase 2: Recursive Build Details

### Build Step

**Context loading requirements**:
- Last 2-3 sentences from previous section
- List of key terms used
- Established tone and manner (formal/informal, distance)

**Writing principles**:
```
1. One idea per sentence
2. Clear subject-predicate structure
3. Minimize modifiers
4. Explain technical terms on first appearance
```

### Verify Checklist

```
[Logical Connection]
□ Natural transitions/connectors with previous section
□ Clear cause-effect relationships between concepts
□ No logical leaps

[Contradiction Check]
□ No conflict with previously mentioned content
□ Consistent meaning of same terms
□ Numbers and facts match

[Tone and Manner]
□ Consistent sentence ending style
□ Unified formality level
□ Sentence length variance within ±10 chars
```

### Reflect Branching

```
Verify Result → Branch
├─ All passed → Next segment
├─ 1-2 failed → Revise and re-verify (max 2 attempts)
├─ 3+ failed → Rewrite entire segment
└─ Fact uncertain → Call tool or mark for later
```

### Critical Issue Judgment Criteria

| Situation | Action |
|-----------|--------|
| 2+ possible interpretations | Confirm via AskUserQuestion |
| External information needed | Try WebFetch, ask user if fails |
| Sensitive claim | State evidence + request user approval |
| Style mismatch with reference | Confirm which to follow |

---

## Phase 3: Final Review Details

### Self-Critique Questions (Mandatory)

```
1. Which claims in this document lack evidence?
2. What expressions could readers misunderstand?
3. What important perspectives or counterarguments are missing?
4. What parts are unnecessarily long or repetitive?
5. What content diverges from the original request?
```

### Adversarial Thinking (Mandatory)

For each main claim, generate at least one counter-argument:
```
Main claim: "Fast execution is essential for startup success"
Counter-argument: "Premature execution without validation can waste resources"
Response: Address in document or acknowledge as limitation
```

### Intent Alignment Check

```
Original request: [Quote user's original text]
Written result: [Summarize core content]

Alignment status:
□ Core request fulfilled
□ Scope appropriate (no excess/omission)
□ Tone matches
```

---

## Phase 4: Polish Details

### LLM Expression Blacklist

Mandatory removal or revision:

| Language | Remove/Revise | Alternative |
|----------|---------------|-------------|
| English | "very important" | "critical" or remove |
| English | "various ways" | Specify methods or remove |
| English | "effectively" | Remove or specify effect |
| English | "successfully achieved" | "achieved" |
| English | "in-depth analysis" | "analysis" |
| English | "widely utilized" | "used" |
| English | "It is important to..." | Direct statement |
| English | "In order to..." | "To..." |
| Korean | "매우 중요한" | "핵심적인" or remove |
| Korean | "다양한 방법으로" | Specify methods or remove |
| Korean | "효과적으로" | Remove or specify effect |
| Korean | "성공적으로 달성" | "달성" |
| Korean | "심층적으로 분석" | "분석" |
| Korean | "폭넓게 활용" | "활용" |
| Korean | "~하는 것이 중요합니다" | Direct statement |

### Sentence Length Guidelines

```
[Problem] Sentence over 50 chars (Korean) / 25 words (English)
→ Split into two sentences
→ Convert relative clauses to separate sentences

[Problem] Consecutive sentences under 10 chars (Korean) / 5 words (English)
→ Consider combining with adjacent sentences
```

---

## Language-Specific Polish

### Korean

**Sentence Endings**:
- Balance ~다/~이다 (plain) with ~습니다/~입니다 (polite)
- Match reference document if provided
- Default to ~다 체 for formal documents

**Expression Rules**:
- Remove: "매우", "정말", "확실히", "다양한" overuse
- Avoid: "~하는 것이 중요합니다" → prefer direct statements
- Fix: Spacing errors (띄어쓰기), particle usage (조사)

**Sentence Length**:
- Recommended: 15-30 characters
- Maximum: 50 characters before splitting

**Style Markers**:
- Identify user's preferred endings from reference
- Note frequent connectors: 그래서/따라서/하지만
- Preserve user's characteristic expressions

### English

**Voice**:
- Prefer active voice over passive
- Use passive only when actor is unknown or irrelevant

**Expression Rules**:
- Remove: "very", "really", "certainly", "various" overuse
- Avoid: "It is important to...", "In order to..."
- Avoid: Nominalizations when verbs work better

**Sentence Length**:
- Recommended: 10-25 words
- Maximum: 35 words before splitting

**Style Markers**:
- Match formality level of reference document
- Preserve technical terminology as used by user

### General (All Languages)

- Remove redundant modifiers
- One idea per sentence
- Consistent tone throughout
- No hedging without purpose ("perhaps", "maybe", "somewhat")
- Concrete over abstract

---

## Threshold Criteria

### 800-Character Threshold Rationale

| Length | Characteristics | Skill Application |
|--------|-----------------|-------------------|
| ~500 chars | Single concept, 1-2 paragraphs | Unnecessary |
| 500-800 chars | 2-3 paragraphs, simple structure | Optional |
| **800+ chars** | 3+ paragraphs, logical structure needed | **Recommended** |
| 2,000+ chars | Complex structure, multiple concepts | Required |

### Bypass Conditions

```
1. Explicit simplification request
   - "briefly", "simply", "in one sentence", "summarize"
   - "짧게", "간단히", "한 문장으로", "요약"

2. Already-structured input
   - User provided outline/structure
   - Simple translation/organization request

3. Simple definition/explanation
   - "What is X?", "Explain X"
   - Only definition needed
```

---

## State Tracking JSON Schema

```json
{
  "segments": [
    {
      "id": 1,
      "name": "segment_name",
      "status": "completed|in_progress|pending",
      "depends_on": [0]
    }
  ],
  "current": 1,
  "style_ref": "filename or null",
  "style_notes": {
    "endings": "plain ~다 or polite ~습니다",
    "avg_sentence_length": 20,
    "characteristic_expressions": ["term1", "term2"]
  },
  "issues": [
    {
      "segment": 1,
      "type": "critical|warning",
      "desc": "description",
      "resolved": false
    }
  ],
  "verify_count": {"1": 0, "2": 1},
  "quality_gate": "pending|passed|failed"
}
```

### Quality Gate Status Transitions

```
pending → passed (all checks passed)
pending → failed (max retries exceeded)
failed → passed (after user intervention or rewrite)
```
