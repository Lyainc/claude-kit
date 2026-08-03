---
name: doc-polish

description: |
  Validate and improve EXISTING Markdown documents: fix formatting, consistency, and flag quality concerns.
  Output-layer md-edit adapter (format=md × intent=edit): acts as an Editor (not Writer) —
  requires an existing MD file as input; preserves content while improving structure and readability.
  AI 표현(LLM trope, delve/grandiose nouns 등) 제거는 doc-polish 범위 밖 — Humanize KR 같은 전용 휴머나이저를 쓰세요.

  Trigger when user mentions: 검사해줘, 다듬어줘, 품질 검사, 교정, 다듬기,
  polish, lint, "이 문서 검사해줘", "README 다듬어줘".
  Routing: 새 콘텐츠를 처음부터 작성하는 건 doc-concretize (doc-polish는 기존 MD 파일 편집 전용).
effort: medium
allowed-tools: Read Edit Grep Glob Bash WebFetch
---

# Document Polish

Validate and improve existing Markdown documents while preserving original content and structure.

## Core Principle

**Editor, not Writer**: This skill NEVER changes content meaning or structure.
- ✅ Fix expression quality, consistency, formatting
- ❌ Add new content, reorganize structure, change meaning

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: MUST match document's original language
- **Report language**: Match dominant language of document

## Prerequisites

- Existing Markdown file(s) to analyze
- (Optional) `--fix` flag for auto-correction

## 3-Layer Verification Structure

### Layer 1: Mechanical (Auto-fix)

Automatically correctable issues:

| Check | Tool | Action |
|-------|------|--------|
| Markdown Lint | markdownlint rules | Auto-fix formatting |
| Link Validation | Internal/External check | Report broken links |
| Code Block Syntax | Language tag verification | Suggest missing tags |
| Whitespace | Trailing spaces, line endings | Auto-fix |
| Heading Structure | Hierarchy validation | Report issues |

**Auto-fix scope**: Formatting only, never content.

### Layer 2: Consistency & Readability

| Check | Detection Target | Output |
|-------|-----------------|--------|
| Term Consistency | "사용자/유저" mixing | Unification candidates |
| Sentence Quality | >50 char (KO) / >35 words (EN) | Split suggestions |
| Tone Uniformity | 존댓말/반말 mixing | Inconsistency locations |

### Layer 3: Semantic (Warning)

Content quality warnings:

| Check | Detection Target | Output |
|-------|-----------------|--------|
| Vague Claims | "약 80%", "many", "various" | Specificity recommendation |
| Outdated Info | Version numbers, years | Currency check request |
| Unexplained Terms | Undefined acronyms/jargon | Explanation recommendation |
| Missing Context | References without explanation | Clarification recommendation |

**Auto-Suggestions**: Layer 3 issues include actionable recommendations:

| Issue Type | Auto-Suggestion |
|------------|----------------|
| Vague Claims | "약 80%" → Ask: "정확한 수치를 확인할 수 있나요? (예: 78.3%)" |
| Outdated Info | Version/year detected → "현재 최신 버전을 확인해주세요" + WebFetch offer |
| Unexplained Terms | First occurrence without definition → "첫 등장 시 간단한 설명을 추가하세요" |
| Missing Context | Reference without explanation → "이 참조의 배경을 1-2문장으로 추가하세요" |

**Note**: Layer 3 auto-suggestions are recommendations — final judgment requires human review.

## Workflow

```
Input: MD file path + options

Phase 1: Mechanical Check
├── Run markdownlint
├── Validate links (internal → external)
├── Check code blocks
└── Output: Auto-fixed file or issue list

Phase 2: Consistency Check
├── Check term consistency
├── Analyze sentence quality
└── Output: Consistency issues + suggestions

Phase 3: Semantic Review
├── Flag vague claims
├── Identify potential outdated info
├── Find unexplained terms
└── Output: Warnings with recommendations

Output: Fixed file and/or Quality Report
```

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| Read | Load target MD file | Read file content |
| Bash | Run markdownlint | `markdownlint --fix file.md` |
| WebFetch | Validate external links | Check URL accessibility |
| Edit | Apply auto-fixes | Fix formatting issues |

## Output Modes

### Default Mode
```
[Document Polish Summary]

File: path/to/document.md

Layer 1 (Mechanical): 3 issues found, 2 auto-fixed
Layer 2 (Consistency): Term consistency: 1 issue, Sentence quality: 2 suggestions
Layer 3 (Semantic): 2 warnings

Run with --fix to apply auto-corrections.
```

### Fix Mode (`--fix`)
```
[Document Polish - Fix Applied]

File: path/to/document.md

Auto-fixed:
- Line 15: Fixed trailing whitespace
- Line 23: Added language tag to code block
- Line 45: Fixed heading hierarchy

Remaining issues (require manual review):
- Line 30: Term inconsistency "사용자/유저" → unify to "사용자"
- Line 52: Sentence exceeds 50 chars → suggest splitting
```

> **Removed**: `--report` 플래그(상세 리포트 모드)는 더 이상 지원하지 않아요. AI 표현(LLM trope) 감사가 필요하면 Humanize KR 같은 전용 휴머나이저를 쓰세요.

## Integration with doc-concretize

After `doc-concretize` generates a document:

```
doc-concretize output → doc-polish --fix → Final polished document
```

Recommended workflow:
1. `doc-concretize`: Create structured content
2. `doc-polish --fix`: Auto-fix mechanical issues
3. Manual review of remaining suggestions

## Boundaries

| Aspect | doc-polish Does | doc-polish Does NOT |
|--------|-----------------|---------------------|
| Formatting | ✅ Fix markdown syntax | |
| Expression | ✅ Suggest alternatives | ❌ Rewrite content |
| Structure | ✅ Report issues | ❌ Reorganize sections |
| Content | ✅ Flag concerns | ❌ Add/remove content |
| Links | ✅ Validate & report | ❌ Update URLs |
| Style | ✅ Ensure consistency | ❌ Impose new style |

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)

## Quick Start

```
User: "이 README.md 품질 검사해줘"

→ Layer 1: Markdown lint + link check
→ Layer 2: Consistency + readability check
→ Layer 3: Vague claims + outdated info warnings
→ Output: Summary with actionable suggestions
```
