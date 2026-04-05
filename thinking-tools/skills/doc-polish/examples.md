# Document Polish - Examples

Real usage examples demonstrating the 3-layer verification system.

---

## Example 1: Basic Quality Check

### Input

```
User: "이 README.md 품질 검사해줘"

[README.md content]
# My Project

This is a very important project that leverages various technologies.

##Features

- Feature 1: 매우 효과적으로 작동합니다
- Feature 2: 다양한 방법으로 활용 가능

Check our [guide](docs/guide.md) for more info.

```javascript
const x = 1
```
```

### Processing

*[Internal: Layer 1 - Mechanical Check]*

**Findings**:
- Line 7: Heading hierarchy issue (## without space)
- Line 14: Code block missing language tag → detected as javascript
- Link check: `docs/guide.md` - file exists ✓

*[Internal: Layer 2 - Linguistic Analysis]*

**Findings**:
- Line 3: "very important" - High severity LLM expression
- Line 3: "leverages various technologies" - High severity
- Line 9: "매우 효과적으로" - High severity
- Line 10: "다양한 방법으로" - High severity

*[Internal: Layer 3 - Semantic Review]*

**Findings**:
- Line 3: Vague claim "various technologies" - no specifics

### Output

```
[Document Polish Summary]

File: README.md

Layer 1 (Mechanical): 2 issues found
  - Line 7: Missing space after ## in heading
  - Line 14: Code block without language tag (suggest: javascript)

Layer 2 (Linguistic): 4 high-priority suggestions
  - Line 3: "very important" → "critical" or remove
  - Line 3: "leverages various technologies" → specify technologies
  - Line 9: "매우 효과적으로" → "효과적으로" or specify effect
  - Line 10: "다양한 방법으로" → list specific methods

Layer 3 (Semantic): 1 warning
  - Line 3: Vague claim - specify which technologies

Run with --fix to auto-correct Layer 1 issues.
```

---

## Example 2: Auto-fix Mode

### Input

```
User: "README.md --fix"
```

### Processing

*[Internal: Applying Layer 1 fixes]*

### Output

```
[Document Polish - Fix Applied]

File: README.md
Backup created: README.md.bak

Auto-fixed (2 items):
  ✓ Line 7: Added space after ## → "## Features"
  ✓ Line 14: (No auto-fix for language tag - requires verification)

Remaining issues requiring manual review:

Layer 2 - Linguistic (4 suggestions):
  Line 3: "very important"
    Current: "This is a very important project"
    Suggest: "This project is critical" or "This project"

  Line 3: "leverages various technologies"
    Current: "leverages various technologies"
    Suggest: "uses React, Node.js, and PostgreSQL" (specify actual tech)

  Line 9: "매우 효과적으로"
    Current: "매우 효과적으로 작동합니다"
    Suggest: "효과적으로 작동합니다" or specify the effect

  Line 10: "다양한 방법으로"
    Current: "다양한 방법으로 활용 가능"
    Suggest: "CLI, API, SDK로 활용 가능" (list actual methods)

Layer 3 - Semantic (1 warning):
  Line 3: Vague technologies claim
    → Specify which technologies are used

To undo changes: restore from README.md.bak
```

---

## Example 3: Detailed Report Mode

### Input

```
User: "docs/api-guide.md --report"
```

### Output

```markdown
# Document Polish Report

**File**: docs/api-guide.md
**Date**: 2024-01-15 14:30:00
**Mode**: report

## Executive Summary

- Total issues: 12
- Auto-fixable: 4
- Manual review needed: 8
- Quality score: 72/100

## Layer 1: Mechanical

### Auto-fixable (4)
| Line | Issue | Fix |
|------|-------|-----|
| 15 | Trailing whitespace | Remove |
| 23 | Missing blank line after heading | Add |
| 45 | Multiple blank lines | Reduce to one |
| 67 | No newline at end of file | Add |

### Requires Attention (1)
| Line | Issue | Recommendation |
|------|-------|----------------|
| 34 | Broken link: `../old-docs/ref.md` | Update path or remove |

## Layer 2: Linguistic

### High Priority (2)
| Line | Expression | Suggestion |
|------|------------|------------|
| 12 | "It is important to note that" | State directly |
| 28 | "다양한 API 엔드포인트" | List specific endpoints |

### Medium Priority (3)
| Line | Issue | Suggestion |
|------|-------|------------|
| 5, 18, 42 | Term inconsistency: "사용자" / "유저" | Unify to "사용자" (more frequent) |

### Low Priority (2)
| Line | Expression | Suggestion |
|------|------------|------------|
| 8 | "leverage" | "use" |
| 55 | "utilize" | "use" |

## Layer 3: Semantic

### Warnings (3)
| Line | Type | Issue | Recommendation |
|------|------|-------|----------------|
| 20 | Vague | "약 100ms 응답 시간" | Specify exact or range |
| 38 | Outdated | "v2.1.0 기준" | Verify current version |
| 52 | Unexplained | "JWT" first use | Add: "(JSON Web Token)" |

## Recommendations

1. **Immediate**: Fix broken link at line 34
2. **High**: Remove LLM expressions (lines 12, 28)
3. **Medium**: Unify terminology (사용자/유저)
4. **Optional**: Simplify vocabulary (leverage→use)

## Statistics

- Word count: 1,247
- Sentence count: 89
- Average sentence length: 14 words
- Heading count: 8
- Link count: 5 internal / 3 external
- Code block count: 6
```

---

## Example 4: doc-concretize → doc-polish Pipeline

### Scenario

User created a document with doc-concretize, now wants to polish it.

### Input

```
User: "방금 만든 core-values.md 다듬어줘 --fix"
```

### Processing

*[Internal: Recognizing pipeline context]*

Note: Document was recently created by doc-concretize.
Focus on expression quality while preserving the structured content.

*[Internal: Layer 1 check]*
- Formatting: Clean (doc-concretize handles basics)
- Links: None to check

*[Internal: Layer 2 check]*
- Found 2 LLM expressions from generation

*[Internal: Layer 3 check]*
- Content is fresh, no outdated info concerns

### Output

```
[Document Polish - Fix Applied]

File: core-values.md
Context: Post doc-concretize polish

Layer 1: All clear (doc-concretize output is well-formatted)

Layer 2 - Linguistic suggestions (2):

  Line 15: "다양한 방법으로 실천합니다"
    Current: 고객 중심을 다양한 방법으로 실천합니다
    Suggest: 고객 중심을 다음과 같이 실천합니다:
            - 분기별 고객 인터뷰
            - 주간 NPS 리뷰
            - 실시간 지원 채널 분석
    Note: Listing specific methods strengthens the document

  Line 28: "효과적으로 달성할 수 있습니다"
    Current: 목표를 효과적으로 달성할 수 있습니다
    Suggest: 목표를 달성할 수 있습니다
    Note: "효과적으로" adds no information

Layer 3: No warnings (fresh content)

Pipeline tip: doc-concretize focuses on structure and content.
doc-polish catches expression quality issues like these.
Consider running doc-polish after each doc-concretize session.
```

---

## Example 5: Structural Trope Detection + Density Score

### Input

```
User: "blog-post.md 다듬어줘 --report"

[blog-post.md content - ~800 words]
# Why AI-First Companies Will Define the Next Era

The AI revolution isn't just coming — it's already here. And it's not just a tool — it's a
platform that will fundamentally reshape how every industry operates.

## The Landscape is Shifting

Here's the thing: most companies are still thinking about AI the wrong way. They're treating
it as an add-on — a nice-to-have — when it should be the foundation of everything they do.

Think of it as building a house. You wouldn't add the foundation after the walls are up. The
same principle applies to AI integration — it needs to be baked in from day one.

The result? Companies that get this right will see unprecedented growth. Companies that don't?
They'll be left behind — wondering what happened — while their competitors reshape the market.

## Three Pillars of AI-First Strategy

The first pillar is **data infrastructure**. Without robust data pipelines — companies simply
can't leverage AI effectively. Building a comprehensive data strategy — from collection to
analysis — is the essential first step.

The second pillar is **talent acquisition**. Experts argue that the war for AI talent will
define the next decade. Organizations need to streamline their hiring — facilitate knowledge
transfer — and harness the power of interdisciplinary teams.

The third pillar is **cultural transformation**. It's not about technology — it's about
mindset. Companies need to fundamentally reimagine how they approach innovation.

## The Bottom Line

In conclusion, AI-first companies will define the next era of business. The landscape is
shifting, the stakes are high, and the time to act is now.

This isn't just an opportunity. It's a necessity.

And it starts today.
```

### Processing

*[Internal: Layer 2 - 6-Category Trope Scan]*

**Category A (Word Choice)**:
- Line 2: "fundamentally reshape" — A1 Magic Adverb + D6 Stakes Inflation (High)
- Line 16: "robust" — A2 Delve and Friends (High)
- Line 16: "leverage" — A2 (High)
- Line 17: "comprehensive" — A2 (High)
- Line 19: "streamline" — A2 (High)
- Line 19: "facilitate" — A2 (High)
- Line 19: "harness" — A2 (High)
- Line 22: "fundamentally reimagine" — A1 (High)
- Line 24: "unprecedented" — D6 (High)

**Category B (Sentence Structure)**:
- Line 2: "it's not just a tool — it's a platform" — B1 Negative Parallelism (High)
- Line 10: "The result? ... Companies that don't?" — B3 Rhetorical Q&A (High)
- Line 22: "It's not about technology — it's about mindset" — B1 (High)

**Category C (Paragraph Structure)**:
- Lines 27-29: "This isn't just an opportunity.\n\nIt's a necessity.\n\nAnd it starts today." — C1 Short Punchy Fragments (High)
- Lines 14-21: "The first pillar... The second pillar... The third pillar..." — C2 Listicle in Trench Coat (Medium)

**Category D (Tone Markers)**:
- Line 6: "Here's the thing" — D1 False Suspense (High)
- Line 8: "Think of it as building a house" — D2 Patronizing Analogies (Medium)
- Line 2: "fundamentally reshape" — D6 Stakes Inflation (High)
- Line 19: "define the next decade" — D6 (High)

**Category E (Formatting Signals)**:
- Document-wide: 10 em-dashes in ~800 words — E1 Em-Dash Addiction (High)
- Lines 14-21: Bold-first pattern on all list items — E2 Bold-First Bullets (High)

**Category F (Composition Tics)**:
- Lines 1-2 vs 24-25: Intro and conclusion both claim "define the next era" — F1 Fractal Summary (High)
- Line 24: "In conclusion" — F6 Signposted Conclusion (Medium)

*[Internal: Trope Density Calculation]*

```
Raw trope count: 22
Word count: ~800
Raw density: 27.5 / 1000 words

Weighted calculation:
  High tropes: 18 × 3 = 54
  Medium tropes: 4 × 2 = 8
  Low tropes: 0 × 1 = 0
  Weighted total: 62
  Weighted density: 62 / 800 × 1000 = 77.5 / 1000 words

Assessment: HIGH (threshold: >6.0)
```

*[Internal: Clustering Detection]*

```
Hotspot 1: Lines 2-10 (8 tropes across A, B, D categories)
Hotspot 2: Lines 14-22 (9 tropes across A, B, C, D, E categories)
Hotspot 3: Lines 24-29 (5 tropes across C, D, F categories)
```

### Output

```
[Document Polish Summary]

File: blog-post.md

Layer 1 (Mechanical): 0 issues
Layer 2 (Linguistic): 22 tropes found
  Trope Density: 77.5/1000 words (HIGH)
  Clustering: 3 hotspots detected

  Hotspot 1 (lines 2-10): 8 tropes — Word Choice + Structure + Tone
  Hotspot 2 (lines 14-22): 9 tropes — Word Choice + Structure + Paragraph + Tone + Formatting
  Hotspot 3 (lines 24-29): 5 tropes — Paragraph + Tone + Composition

  Top issues by category:
    A. Word Choice (9): "robust", "leverage", "comprehensive", "streamline",
       "facilitate", "harness", "fundamentally" ×2, "unprecedented"
       → Replace with specific terms or remove
    B. Sentence Structure (3): Negative parallelism ×2, Rhetorical Q&A ×1
       → Rewrite as direct statements
    C. Paragraph Structure (2): Short punchy fragments, Listicle-in-trench-coat
       → Combine fragments; convert to actual list
    D. Tone Markers (4): False suspense, Patronizing analogy, Stakes inflation ×2
       → Remove framing; reduce claims to evidence
    E. Formatting Signals (2): Em-dash overuse (10), Bold-first bullets
       → Reduce em-dashes to 2-3; vary list formatting
    F. Composition Tics (2): Fractal summary, Signposted conclusion
       → Remove "In conclusion"; differentiate ending from intro

  Term consistency: No issues
  Sentence quality: 2 sentences exceed 35 words

Layer 3 (Semantic): 3 warnings
  - Line 2: "every industry" — vague scope claim
  - Line 19: "Experts argue" — vague attribution (D8)
  - Line 24: "define the next era" — unsubstantiated prediction

Run with --report for full trope analysis with rewrite suggestions.
```

---

## Anti-Pattern Examples

### Anti-Pattern 1: Content Modification Attempt

```
[WRONG]
User: "이 문서 더 길게 만들어줘"

doc-polish response:
"doc-polish는 기존 콘텐츠를 수정하지 않습니다.
콘텐츠 추가가 필요하면 doc-concretize를 사용하세요."

[CORRECT SCOPE]
doc-polish only improves expression quality of existing content.
```

### Anti-Pattern 2: Over-fixing

```
[WRONG]
Original: "이 기능은 빠릅니다."
Over-fixed: "이 기능은 밀리초 단위의 응답 시간을 제공하는 고성능 처리 능력을 갖추고 있습니다."

[CORRECT]
Original: "이 기능은 빠릅니다."
Suggestion: Keep as-is, or if context requires: "이 기능은 10ms 이내로 응답합니다."

doc-polish suggests, doesn't impose.
```

### Anti-Pattern 3: Style Imposition

```
[WRONG]
Changing document's intentional informal tone to formal.
Original: "이거 진짜 좋아요!"
Wrong fix: "이것은 매우 우수합니다."

[CORRECT]
Flag tone inconsistency only if document mixes styles.
Preserve intentional stylistic choices.
```

### Anti-Pattern 4: Ignoring Context

```
[WRONG]
Flagging technical terms in a technical document.
"API mentioned without explanation" in an API reference doc.

[CORRECT]
Consider document type:
- README: Flag unexplained terms
- API Reference: Assume reader knows basics
- Tutorial: Flag all jargon
```

### Anti-Pattern 5: False Positives

```
[WRONG]
Flagging "다양한" in:
"Python의 다양한 버전 (3.8, 3.9, 3.10, 3.11) 지원"

[CORRECT]
"다양한" is justified here because versions ARE listed.
Only flag when specifics are missing.
```

---

## Edge Case Handling

### Mixed Language Document

```
Input: Document with Korean explanations and English code

[Processing]
- Apply Korean rules to Korean sections
- Apply English rules to English sections
- Don't flag intentional language switching
- Flag inconsistent mixing (한글 section suddenly switching to English mid-paragraph)
```

### Very Short Document

```
Input: Document < 100 characters

[Output]
Document Polish Summary

File: short.md
Note: Document is very short (45 characters)

Layer 1: 1 issue
  - Missing newline at end

Layers 2-3: Skipped (document too short for meaningful analysis)

Tip: For short documents, manual review is more efficient than automated polish.
```

### Code-Heavy Document

```
Input: Document where >50% is code blocks

[Output]
Document Polish Summary

File: code-examples.md
Note: Code-heavy document (65% code blocks)

Analysis focused on:
- Prose sections between code
- Code block language tags
- Link validation

Skipped:
- Sentence length analysis (not applicable to code comments)

Suggestion: Consider if this should be restructured as a code file with documentation.
```
