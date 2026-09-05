---
name: doc-polish

description: |
  Validate and improve EXISTING Markdown documents: fix formatting, consistency, and flag quality concerns,
  and cross-check the document's repo-checkable factual claims (issue numbers and their state, file paths,
  script/function names, commit SHAs, "미구현"/"없음" status assertions) against the repository — report-only,
  never auto-fixed, since a wrong fact means the content must change and this skill does not write content.
  Output-layer md-edit adapter (format=md × intent=edit): acts as an Editor (not Writer) —
  requires an existing MD file as input; preserves content while improving structure and readability.
  AI 표현(LLM trope, delve/grandiose nouns 등) 제거는 doc-polish 범위 밖 — Humanize KR 같은 전용 휴머나이저를 쓰세요.

  Trigger when user mentions: 검사해줘, 다듬어줘, 품질 검사, 교정, 다듬기, 문서 사실 확인, 내용이 최신인지,
  polish, lint, fact check this doc, "이 문서 검사해줘", "README 다듬어줘", "이 설계문서 아직 맞아?".
  Routing: 새 콘텐츠를 처음부터 작성하는 건 doc-concretize (doc-polish는 기존 MD 파일 편집 전용).
effort: medium
allowed-tools: Read Edit Bash WebFetch
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

## 4-Layer Verification Structure

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

### Layer 4: Fact Cross-Check (Report-only)

Layer 3 asks whether a claim is *vague*. This layer asks whether it is *false* — the one question
no other skill answers for a whole document (`adversarial-review` works per claim, `audit` reads
vault structure and not prose). Design docs fall behind the decisions they describe, so this gap
widens with time rather than staying constant.

**Gate — runs only when the document actually contains something checkable.** Skip the layer
entirely, and omit its line from the report, when a scan finds none of the patterns below. This is
what keeps the added `gh`/`git` cost off every ordinary polish call; there is no flag to remember.

| Claim in the document | Deterministic check | Verdict |
|-----------------------|---------------------|---------|
| Issue/PR reference (`#N`) | `gh issue view N --json state` / `gh pr view` | state matches what the prose says about it |
| File or directory path | file exists at that path | exists as described |
| Script, function, or flag name | `grep` for the name in the repo | present as described |
| Commit SHA | `git log -1 <sha>` | resolves, and describes what the prose says |
| Status assertion ("미구현", "없음", "아직", "지원 안 함") | `grep`/`gh` for the thing asserted absent | still absent |

**Deterministic checks only.** A claim that needs judgment — whether a design is right, whether a
trade-off holds — is out of scope and belongs to `adversarial-review`. If settling it takes reading
and weighing rather than one `gh issue view`, `git log`, or `grep`, it is not this layer's business.

**Three verdicts, one of them reported**: 확인됨 / **어긋남** / 저장소로 확인 불가. Report only
어긋남, with the line number, what the document asserts, and what the check actually returned.
Silence on the other two is deliberate — a list of everything that checked out is noise.

**Never auto-fixed, and excluded from `--fix` by design.** A false fact means the *content* is
wrong, and changing content is the one thing "Editor, not Writer" forbids. So this layer reports
the mismatch and stops; the human decides what the document should say instead. That asymmetry is
the point of the layer, not a limitation of it.

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

Phase 4: Fact Cross-Check (skipped when no checkable claim is present)
├── Extract #N refs, paths, script/function names, SHAs, status assertions
├── Verify each with gh / git / grep / file existence
└── Output: 어긋남 only — never auto-fixed

Output: Fixed file and/or Quality Report
```

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| Read | Load target MD file | Read file content |
| Bash | Run markdownlint | `markdownlint --fix file.md` |
| Bash | Layer 4 fact checks | `gh issue view 123 --json state`, `git log -1 <sha>`, `grep -rn <name>` |
| WebFetch | Validate external links | Check URL accessibility |
| Edit | Apply auto-fixes | Fix formatting issues (Layers 1-2 only — Layer 4 never edits) |

## Output Modes

### Default Mode
```
[Document Polish Summary]

File: path/to/document.md

Layer 1 (Mechanical): 3 issues found, 2 auto-fixed
Layer 2 (Consistency): Term consistency: 1 issue, Sentence quality: 2 suggestions
Layer 3 (Semantic): 2 warnings
Layer 4 (Fact): 1 mismatch — omit this line entirely when the gate did not fire

Run with --fix to apply auto-corrections (Layer 4 mismatches are never among them).
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
- Line 61: 어긋남 — 문서는 #564를 "열려 있음"으로 서술하지만 `gh issue view 564`는 CLOSED
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
| Facts | ✅ Cross-check against the repo and report mismatches | ❌ Correct a wrong fact (content change) |
| Judgment claims | ✅ Point to `adversarial-review` | ❌ Weigh whether a design or trade-off is right (→ `adversarial-review`) |
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
→ Layer 4: Cross-check #N refs, paths, names, SHAs against the repo (skipped if none present)
→ Output: Summary with actionable suggestions
```
