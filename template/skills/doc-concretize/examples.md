# Document Concretization - Examples

Real usage examples with processing walkthrough.

---

## Example 1: Startup Core Values Documentation

### Input

```
User: "Document our startup's core values.
       Customer focus, fast execution, and transparency matter."
```

### Phase 1: Segmentation

**Analysis Result**:
- Abstract concept: Core values (philosophical)
- Documentation intent: "Document" keyword
- Estimated length: ~1,500 chars (3 values × 500 chars)

**Segment Division**:
```json
{
  "segments": [
    {"id": 1, "name": "Customer Focus", "status": "pending", "depends_on": []},
    {"id": 2, "name": "Fast Execution", "status": "pending", "depends_on": []},
    {"id": 3, "name": "Transparency", "status": "pending", "depends_on": []}
  ],
  "current": 1,
  "style_ref": null,
  "quality_gate": "passed"
}
```

### Phase 2: Recursive Build

**Segment 1: Customer Focus**

[Build]
```
Customer focus is the first question we ask in every decision.
"What value does this bring to our customers?"

We don't just collect customer feedback.
We treat feedback as the primary input for product improvement.
Quarterly customer interviews, weekly NPS reviews, and real-time support channel analysis
are the concrete methods that execute this principle.
```

[Verify]
- □ Logical connection: Passed (definition → execution method)
- □ No contradictions: Passed
- □ Tone and manner: Passed (plain declarative)

[Reflect]
- All passed → proceed to next segment

**Segment 2: Fast Execution**

[Build]
```
Fast execution means not waiting for perfection.
When we have 80% confidence, we start. We refine the rest while executing.

This principle doesn't mean recklessness.
We design experiments as minimal units to validate core hypotheses,
and quickly adjust direction based on results.
Weekly sprints and daily standups maintain this rhythm.
```

[Verify]
- □ Logical connection: Passed (contrasts with previous section's deliberate approach)
- □ No contradictions: Passed
- □ Tone and manner: Passed

**Segment 3: Transparency**

[Build]
```
Transparency means information defaults to open.
If there's no reason to hide it, we share it.

Within the team, we share all meeting notes, decision backgrounds, and failure cases.
To customers, we publish our product roadmap, incident reports, and pricing change rationale.
This principle may cause short-term discomfort,
but it's the fastest path to building long-term trust.
```

[Verify]
- □ Logical connection: Passed
- □ No contradictions: Passed
- □ Tone and manner: Passed

### Phase 3: Final Review

**Self-Critique**:
1. Weak evidence claims? → "fastest path to building trust" - abstract but acceptable for values document
2. Misunderstandable expressions? → "80% confidence" - may need concrete criteria
3. Missing perspectives? → No priority when values conflict → consider adding

**Adversarial Check**:
- Claim: "Fast execution is essential"
- Counter: "Speed without validation can waste resources"
- Response: Document addresses this with "doesn't mean recklessness" caveat

**Intent Alignment**:
- Original request: Document 3 core values
- Written result: 3 values with definition + execution methods each
- Alignment status: Fulfilled

### Phase 4: Polish

**Before**:
> This principle may cause short-term discomfort, but it's the fastest path to building long-term trust.

**After**:
> Short-term discomfort is possible, but this builds trust fastest over time.

(Removed unnecessary "This principle", simplified structure)

### Final Output

```
# Our Core Values

## Customer Focus

Customer focus is the first question we ask in every decision.
"What value does this bring to our customers?"

We don't just collect customer feedback.
We treat feedback as the primary input for product improvement.
Quarterly customer interviews, weekly NPS reviews, and real-time support channel analysis
execute this principle in practice.

## Fast Execution

Fast execution means not waiting for perfection.
When we have 80% confidence, we start. We refine the rest while executing.

This doesn't mean recklessness.
We design experiments as minimal units to validate core hypotheses,
and quickly adjust direction based on results.
Weekly sprints and daily standups maintain this rhythm.

## Transparency

Transparency means information defaults to open.
If there's no reason to hide it, we share it.

Within the team, we share all meeting notes, decision backgrounds, and failure cases.
To customers, we publish our product roadmap, incident reports, and pricing change rationale.
Short-term discomfort is possible, but this builds trust fastest over time.

---
<details>
<summary>Writing Process</summary>

- Segments: 3 sections
- Verification passed: 3/3
- Revisions: Phase 4 style polish 1 item
- Style reference: None
</details>
```

---

## Example 2: Style Reference Matching

### Input

```
User: "Add 'Team Collaboration Principles' matching the style of my existing document.

[Existing Document]
We hate meetings. We only hold necessary ones.
Meetings never exceed 30 minutes.
No meeting without a decision."
```

### Phase 1: Segmentation

**Style Analysis**:
```json
{
  "style_ref": "user_input",
  "style_notes": {
    "endings": "plain declarative (firm tone)",
    "avg_sentence_length": 8,
    "characteristic_expressions": ["We hate...", "never exceed", "No... without"]
  }
}
```

**Segments**:
- Team collaboration core principles (1 chunk, short document)

### Phase 2: Recursive Build

[Build]
```
Team collaboration has rules too.
Work alone if you can do it alone.
Ask immediately when you need help. No hesitation.
Deliver feedback directly. No talking behind backs.
```

[Verify]
- □ Reference style maintained: Passed (short sentences, firm tone, negative emphasis)
- □ Tone and manner: Passed (matches assertiveness)

### Final Output

```
## Team Collaboration Principles

Team collaboration has rules too.
Work alone if you can do it alone.
Ask immediately when you need help. No hesitation.
Deliver feedback directly. No talking behind backs.
```

---

## Example 3: Critical Issue Handling

### Input

```
User: "Document our company's AI adoption strategy.
       The goal is efficiency improvement."
```

### Phase 2: Critical Issue Occurs

[Build - Segment 2]
```
The expected efficiency improvement from AI adoption is approximately 30%.
```

[Verify]
- □ Fact-check needed: **FAILED** - 30% has no stated basis

[Reflect - Critical Issue]

```
AskUserQuestion called:

"Do you have a target efficiency improvement figure?
Or is there benchmark data I can reference?

1. I have a specific target (e.g., 20% reduction in task time)
2. Not yet - use general phrasing instead
3. Find industry benchmarks for me"
```

**User Response**: "Not yet"

**Revised Build**:
```
We expect AI adoption to automate repetitive tasks and speed up decision-making.
Concrete impact will be measured after the pilot project.
```

---

## Example 4: Bypass Case

### Input

```
User: "Briefly explain what an API is"
```

### Judgment

- Abstraction: Technical term (O)
- Documentation intent: "explain" (definition request)
- **"Briefly" specified**: Bypass condition met

### Result

Skill not applied, standard response:

```
API (Application Programming Interface) is a protocol defining how programs communicate.
It allows one program to call another program's functions.
```

---

## Anti-Pattern Examples

### Anti-Pattern 1: Excessive Verification Loop

```
[Problem]
Segment 1 written → verify failed → revise → verify failed → revise → verify failed...

[Solution]
Max 2 re-verifications, then force proceed with issue marked
```

### Anti-Pattern 2: Ignoring Style Reference

```
[Reference Style] "~입니다/~합니다" (polite Korean)
[Written Result] "~다/~이다" (plain Korean)

→ Must correct in Phase 4
```

### Anti-Pattern 3: LLM Expression Overuse

```
[Problem]
"Through various highly effective methods, we can successfully achieve significant outcomes."

[Correction]
"We can achieve outcomes through these methods." (then specify methods)
```

### Anti-Pattern 4: Missing Adversarial Check

```
[Problem]
Document makes bold claims without considering counter-arguments

[Solution]
Phase 3 requires explicit counter-argument generation for each main claim
```

### Anti-Pattern 5: Skipping Quality Gates

```
[Problem]
Proceeding to next phase despite failed verification

[Solution]
Quality gate must show "passed" status before proceeding
```
