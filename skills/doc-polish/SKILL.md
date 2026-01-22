---
name: doc-polish

description: |
  Validate and improve existing Markdown documents through 3-layer quality analysis.
  Acts as an Editor (not Writer) - preserves content while enhancing expression quality.

  Use when the user requests document quality check, linting, or expression improvement
  on existing MD files.

  Trigger when user mentions: 검사해줘, 다듬어줘, 품질 검사, polish, lint, 교정, 검토,
  or requests: "이 문서 검사해줘", "README 다듬어줘", "품질 체크해줘",
  "polish this document", "lint my markdown".

  Skip for: content creation (use doc-concretize), simple questions, non-MD files.
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
- (Optional) `--report` flag for detailed quality report

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

### Layer 2: Linguistic (Detect + Suggest)

Expression quality analysis:

| Check | Detection Target | Output |
|-------|-----------------|--------|
| LLM Trace | Blacklisted expressions | Alternative suggestions |
| Term Consistency | "사용자/유저" mixing | Unification candidates |
| Sentence Quality | >50 char (KO) / >35 words (EN) | Split suggestions |
| Tone Uniformity | 존댓말/반말 mixing | Inconsistency locations |

**Reference**: See [llm-expression-blacklist](../../reference/llm-expression-blacklist.md)

### Layer 3: Semantic (Warning)

Content quality warnings:

| Check | Detection Target | Output |
|-------|-----------------|--------|
| Vague Claims | "약 80%", "many", "various" | Specificity recommendation |
| Outdated Info | Version numbers, years | Currency check request |
| Unexplained Terms | Undefined acronyms/jargon | Explanation recommendation |
| Missing Context | References without explanation | Clarification recommendation |

**Note**: Layer 3 issues are warnings only - requires human judgment.

## Workflow

```
Input: MD file path + options

Phase 1: Mechanical Check
├── Run markdownlint
├── Validate links (internal → external)
├── Check code blocks
└── Output: Auto-fixed file or issue list

Phase 2: Linguistic Analysis
├── Scan for LLM expressions
├── Check term consistency
├── Analyze sentence quality
└── Output: Suggestions with locations

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
Layer 2 (Linguistic): 5 suggestions
Layer 3 (Semantic): 2 warnings

Run with --fix to apply auto-corrections.
Run with --report for detailed analysis.
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
- Line 30: LLM expression "매우 중요한" → suggest "핵심적인"
- Line 52: Sentence exceeds 50 chars → suggest splitting
```

### Report Mode (`--report`)

Generates detailed quality report. See [templates/POLISH_REPORT.md](templates/POLISH_REPORT.md).

## Integration with doc-concretize

After `doc-concretize` generates a document:

```
doc-concretize output → doc-polish --fix → Final polished document
```

Recommended workflow:
1. `doc-concretize`: Create structured content
2. `doc-polish --fix`: Auto-fix mechanical issues
3. `doc-polish --report`: Review remaining suggestions
4. Manual review of semantic warnings

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
- **Report template**: See [templates/POLISH_REPORT.md](templates/POLISH_REPORT.md)
- **LLM expressions**: See [llm-expression-blacklist](../../reference/llm-expression-blacklist.md)

## Quick Start

```
User: "이 README.md 품질 검사해줘"

→ Layer 1: Markdown lint + link check
→ Layer 2: LLM expression scan + consistency check
→ Layer 3: Vague claims + outdated info warnings
→ Output: Summary with actionable suggestions
```
