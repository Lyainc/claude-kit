---
name: doc-concretize

description: |
  Transform abstract concepts into concrete, well-structured documentation
  through step-by-step recursive writing with verification at each step.

  Use when the user requests documentation of abstract ideas, strategies,
  or concepts requiring structured concretization (expected output > 800 characters).

  Trigger when user mentions: 구체화, 문서화, 체계적 정리, 개념 정리, 아이디어 문서화, 전략 문서, 글로 정리,
  or requests: "이 개념을 문서로 정리해줘", "아이디어를 체계적으로 구체화해줘",
  "전략을 상세 문서로 작성해줘", "비전을 실행 가능한 계획으로 풀어줘".

  Skip for: simple definitions, "짧게"/"간단히"/"briefly" requests, or already-structured content.
---

# Document Concretization

Transform abstract concepts into concrete, well-structured documentation through recursive writing and rigorous verification.

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match input language
  - Korean input → Korean output
  - English input → English output
  - Mixed input → follow dominant language
- **Style reference**: If user provides a reference document, match its language and tone

## Prerequisites

- Abstract concept or idea to concretize
- (Optional) Reference document for style matching
- (Optional) Specific format/structure request

## Core Workflow

### Phase 1: Segmentation

1. Analyze input → identify core semantic units (3-7 chunks)
2. Determine logical order and dependencies
3. Estimate output length → if < 800 chars, switch to standard writing
4. If reference document exists, analyze and record its style

**Mandatory State Tracking**:
```json
{
  "segments": [
    {"id": 1, "name": "segment_name", "status": "pending", "depends_on": []},
    ...
  ],
  "current": 0,
  "style_ref": "user_doc.md or null",
  "verify_count": {},
  "quality_gate": "pending"
}
```

**Quality Gate**: Segments defined + dependencies mapped → proceed

### Phase 2: Recursive Build

For each segment, execute **Build → Verify → Reflect** cycle:

```
[Build]
1. Load context from previous sections
2. Draft current section
   - One idea per sentence
   - No detail omission
   - Clear subject-predicate structure

[Verify] — ALL must pass
□ Logical connection with previous content?
□ No contradictions or redundancy?
□ Consistent tone and manner?
□ Reference style maintained? (if applicable)

[Reflect]
- All passed → proceed to next segment
- 1-2 failed → revise and re-verify (max 2 attempts)
- 3+ failed → rewrite entire segment
- Fact uncertain → call AskUserQuestion or WebFetch
```

**Critical Issues** (require user approval):
- Core premise has multiple interpretations
- Conflicting information discovered
- Sensitive claims or judgments involved

**Quality Gate**: All verify checks passed for current segment → proceed

### Phase 3: Final Review

1. **Full Read**: Review entire document from start to end
2. **Self-Critique**: Answer these mandatory questions:
   - What claims lack sufficient evidence?
   - What expressions could readers misunderstand?
   - What important perspectives or counterarguments are missing?
   - What parts are unnecessarily long or repetitive?
   - What content diverges from the original request?
3. **Adversarial Check**: Generate at least one counter-argument to main claims
4. **Intent Verification**: Confirm alignment with original request
5. **Gap Check**: Ensure no core content is missing

**Quality Gate**: All questions answered + counter-arguments addressed → proceed

### Phase 4: Polish

**Grammar & Spelling** (mandatory):
- Fix spacing, spelling, particle errors

**Style Refinement**:
- Remove LLM-specific expressions (see [reference.md](reference.md) for blacklist)
- Minimize unnecessary modifiers
- Balance sentence length
- Apply language-specific polish rules (see [reference.md](reference.md))

**Reference Style Maintenance** (if applicable):
- Reflect user's tone and style from reference document
- Confirm with user if tone change is necessary

**Quality Gate**: Zero blacklisted expressions remaining → complete

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Clarify ambiguous concepts, Critical Issues | "Did you mean X or Y?" |
| WebFetch | Fact-check (numbers, quotes, external info) | Verify statistics |

## Output Format

```
[Completed Document]

---
<details>
<summary>Writing Process</summary>

- Segments: N sections
- Verification passed: N/N
- Revisions: (if any)
- Style reference: (if any)
</details>
```

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)

## Quick Start

```
User: "Document our service's core values.
       Customer focus, fast execution, and transparency matter."

→ Phase 1: Segment into 3 chunks (customer focus / fast execution / transparency)
→ Phase 2: Recursive build + verify each segment
→ Phase 3: Full review, self-critique, adversarial check
→ Phase 4: Polish with language-specific rules
→ Output: Structured core values document (~1,500 chars)
```
