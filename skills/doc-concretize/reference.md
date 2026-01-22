# Document Concretization - Reference

Detailed procedures and guidelines.

## Table of Contents

- [Phase 1: Concept Analysis Details](#phase-1-concept-analysis-details)
- [Phase 2: Structure Design Details](#phase-2-structure-design-details)
- [Phase 3: Content Build Details](#phase-3-content-build-details)
- [Phase 4: Completeness Check Details](#phase-4-completeness-check-details)
- [Threshold Criteria](#threshold-criteria)
- [State Tracking JSON Schema](#state-tracking-json-schema)

---

## Phase 1: Concept Analysis Details

### Semantic Unit Identification Criteria

| Criterion | Description | Example |
|-----------|-------------|---------|
| Independent concept | Unit that can stand alone | "Customer focus" vs "Fast execution" |
| Logical transition | Point where topic or perspective shifts | Cause→Effect, Present→Future |
| Structural division | Units separated by document format | Background/Body/Conclusion |

### Concept Decomposition

**Breaking complex concepts into atomic units**:
- Identify core vs supporting concepts
- Separate definition from explanation
- Distinguish mechanism from outcome
- Isolate assumptions from conclusions

**Atomic unit criteria**:
- Can be understood without external context
- Represents single logical idea
- Has clear boundaries
- Can be referenced independently

### Dependency Mapping

**Prerequisite relationships**:
- Concept A must be explained before concept B
- Foundation → Building blocks → Advanced concepts
- Track which concepts require prior knowledge

**Cause-effect chains**:
- Identify causal relationships between concepts
- Map input → process → output flows
- Track conditions and consequences

**Sequential dependencies**:
- Process steps that must occur in order
- Temporal relationships (before/after)
- Logical progression (necessary sequence)

### Chunk Count Guidelines

| Estimated Length | Recommended Chunks |
|------------------|-------------------|
| 800-1,200 chars | 3 |
| 1,200-2,000 chars | 4-5 |
| 2,000+ chars | 5-7 |

---

## Phase 2: Structure Design Details

### Ordering Patterns

1. **Deductive**: Principle → Details → Examples
2. **Inductive**: Observation → Analysis → Principle derivation
3. **Chronological**: Past → Present → Future
4. **Priority**: Core → Secondary → Optional

### Document Architecture Patterns

**Problem-Solution structure**:
- State problem clearly
- Explain why it matters
- Present solution systematically
- Show evidence of effectiveness

**Compare-Contrast structure**:
- Establish comparison criteria
- Present option A characteristics
- Present option B characteristics
- Synthesize differences and implications

**Hierarchical breakdown**:
- Start with overview/big picture
- Decompose into major components
- Break components into sub-elements
- Maintain consistent depth level

### Argument Structure

**Claim-Evidence-Example pattern**:
```
1. Make clear claim
2. Provide supporting evidence
3. Illustrate with concrete example
4. Connect back to main thesis
```

**Logical flow validation**:
- Each paragraph advances the argument
- No circular reasoning
- Conclusions follow from premises
- Counterarguments acknowledged

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

## Phase 3: Content Build Details

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

## Phase 4: Completeness Check Details

### Gap Detection

**Missing logical steps**:
- Check if conclusions follow from premises
- Identify unstated assumptions
- Find missing explanatory links
- Detect jumps in reasoning

**Questions to ask**:
```
1. Can reader follow the logic without filling in blanks?
2. Are there unexplained transitions between ideas?
3. What background knowledge is assumed but not stated?
4. Which terms are used without definition?
```

### Contradiction Detection

**Find conflicting statements**:
- Same concept described differently
- Numbers or facts that don't align
- Recommendations that oppose each other
- Definitions that conflict

**Validation checklist**:
```
□ All instances of key terms used consistently
□ Numerical data cross-checked
□ Claims don't contradict in different sections
□ Cause-effect relationships don't reverse
```

### Coverage Verification

**All key points addressed**:
```
1. Compare final content against initial request
2. Check all concepts from analysis phase included
3. Verify promised topics were covered
4. Ensure argument structure is complete
```

**Depth check**:
- Core concepts: Fully explained with examples
- Supporting concepts: Adequately covered
- Minor points: Mentioned or justified omission

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

### doc-polish Integration

**After completeness check passes, recommend doc-polish for**:
- Expression quality improvement
- LLM cliche removal
- Sentence rhythm and flow
- Language-specific polish

**Note**: doc-concretize focuses on content quality (logic, structure, completeness).
doc-polish focuses on expression quality (style, clarity, readability).

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
