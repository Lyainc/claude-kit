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
