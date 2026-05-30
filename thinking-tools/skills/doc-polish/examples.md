# Document Polish - Examples

Real usage examples demonstrating the verification system.

---

## Example 1: Basic Quality Check

### Input

````
User: "이 README.md 품질 검사해줘"

[README.md content]
# My Project

This is a very important project that leverages various technologies.

##Features

- Feature 1: 매우 효과적으로 작동합니다
- Feature 2: 다양한 방법으로 활용 가능

Check our [guide](docs/guide.md) for more info.

```
const x = 1
```
````

### Processing

*[Internal: Layer 1 - Mechanical Check]*

**Findings**:
- Line 7: Heading hierarchy issue (## without space)
- Line 14: Code block missing language tag → detected as javascript
- Link check: `docs/guide.md` - file exists ✓

*[Internal: Layer 2 - Consistency Check]*

**Findings**:
- Term check: No mixed terms detected
- Sentence quality: No issues
- Note: "very important", "leverages" 등 AI 표현은 Layer 2 범위 밖 — 전용 휴머나이저(Humanize KR 등) 대상

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

Layer 2 (Consistency): No consistency issues

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

Layer 2 - Consistency: No issues

Layer 3 - Semantic (1 warning):
  Line 3: Vague technologies claim
    → Specify which technologies are used

To undo changes: restore from README.md.bak
```

---

## Example 3: doc-concretize → doc-polish Pipeline

### Scenario

User created a document with doc-concretize, now wants to polish it.

### Input

```
User: "방금 만든 core-values.md 다듬어줘 --fix"
```

### Processing

*[Internal: Recognizing pipeline context]*

Note: Document was recently created by doc-concretize.
Focus on structure and consistency while preserving the content.

*[Internal: Layer 1 check]*
- Formatting: Clean (doc-concretize handles basics)
- Links: None to check

*[Internal: Layer 2 check]*
- Term consistency: "실천" / "수행" mixed in 3 places

*[Internal: Layer 3 check]*
- Content is fresh, no outdated info concerns

### Output

```
[Document Polish - Fix Applied]

File: core-values.md
Context: Post doc-concretize polish

Layer 1: All clear (doc-concretize output is well-formatted)

Layer 2 - Consistency (1 issue):
  Lines 15, 23, 31: Term inconsistency "실천" / "수행"
    → Unify to "실천" (more frequent in document)

Layer 3: No warnings (fresh content)

Pipeline tip: doc-concretize focuses on structure and content.
doc-polish catches formatting and consistency issues.
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
