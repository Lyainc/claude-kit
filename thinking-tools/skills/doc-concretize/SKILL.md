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

### Phase 1: Concept Analysis

1. Decompose core concepts and identify relationships between them
2. Identify semantic units (3-7 chunks) for document structure
3. Determine logical order and dependencies
4. Estimate output length → if < 800 chars, switch to standard writing
5. If reference document exists, analyze and record its style

**Mandatory State Tracking** *(Internal Only - not shown to users)*:
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

**Quality Gate**: Concepts decomposed + relationships mapped + segments defined → proceed

### Phase 2: Structure Design

Plan document architecture and determine optimal ordering patterns:

1. **Architecture Planning**: Define hierarchy (sections, subsections, flow)
2. **Ordering Strategy**: Determine presentation order (chronological, priority-based, conceptual progression)
3. **Dependency Resolution**: Ensure prerequisites are addressed before dependent concepts

**Quality Gate**: Document structure defined + ordering determined → proceed to content build

### Phase 3: Content Build

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

### Phase 4: Completeness Check

1. **Full Read**: Review entire document from start to end
2. **Self-Critique**: Answer these mandatory questions:
   - What claims lack sufficient evidence?
   - What important perspectives or counterarguments are missing?
   - What parts are unnecessarily long or repetitive?
   - What content diverges from the original request?
3. **Logical Gap Detection**: Identify missing connections, unsupported claims, or contradictions
4. **Adversarial Check**: Generate at least one counter-argument to main claims
5. **Intent Verification**: Confirm alignment with original request
6. **Missing Content Check**: Ensure all core concepts are covered

**Quality Gate**: All logical gaps addressed + no contradictions + all critical content present → proceed

### Phase 5: Basic Polish

**Grammar & Spelling** (mandatory):
- Fix spacing, spelling, particle errors

**Reference Style Maintenance** (if applicable):
- Reflect user's tone and style from reference document
- Confirm with user if tone change is necessary

**Quality Gate**: No grammar errors + reference style maintained → complete

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| AskUserQuestion | Clarify ambiguous concepts, Critical Issues | "Did you mean X or Y?" |
| WebFetch | Fact-check (numbers, quotes, external info) | Verify statistics |

## Output Format

```
[Completed Document]

───
*N개 섹션 작성 완료 · 검토 통과*
```

**Conditional Footer Variants**:

- With style reference: `*N개 섹션 작성 완료 · 검토 통과 · 스타일: [reference]*`
- With revisions: `*N개 섹션 작성 완료 · 검토 통과 (N회 수정)*`

**Fallback Output** (if process fails):

- Korean: `일반 응답으로 대체되었습니다.`
- English: `Falling back to standard response.`

## Model Capabilities

### Extended Thinking (Opus)

- 구조화 데이터 처리를 thinking 단계에서 수행
- 출력에는 변환된 자연어만 포함
- 확률 calibration 더 정확

### Standard Mode (Sonnet)

- 명시적 지시로 구조화 데이터 은닉
- "NEVER output XML/JSON to user" 강조
- 파싱 실패 시 즉시 fallback

## Expression Quality Enhancement

`doc-concretize` focuses on **content creation** (logic, structure, completeness). For **expression quality** (clarity, readability, style refinement), run `doc-polish` as a follow-up step:

```
1. Complete doc-concretize (content creation)
2. Run doc-polish (expression refinement)
```

`doc-concretize` = Writer (creates content)
`doc-polish` = Editor (refines expression)

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)

## Quick Start

```
User: "Document our service's core values.
       Customer focus, fast execution, and transparency matter."

→ Phase 1: Concept Analysis - Decompose core values and identify relationships
→ Phase 2: Structure Design - Plan document architecture and ordering
→ Phase 3: Content Build - Build → Verify → Reflect cycle for each segment
→ Phase 4: Completeness Check - Review for logical gaps and missing content
→ Phase 5: Basic Polish - Fix grammar and maintain reference style
→ Output: Structured core values document (~1,500 chars)

───
*3개 섹션 작성 완료 · 검토 통과*

→ Optional: Run doc-polish for expression quality refinement
```
