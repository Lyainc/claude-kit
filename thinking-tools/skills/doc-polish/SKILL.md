---
name: doc-polish

description: |
  Inspect existing Markdown formatting, consistency, and repository-verifiable facts. Report
  by default; --fix applies mechanical/nonsemantic corrections only, preserving meaning and
  structure. Substantive rewriting is an ordinary editing task, not this skill; use
  doc-concretize for a new document.

  Trigger when user mentions: 검사해줘, 다듬어줘, 품질 검사, 교정, 다듬기, 문서 사실 확인, 내용이 최신인지,
  polish, lint, fact check this doc, "이 문서 검사해줘", "README 다듬어줘", "이 설계문서 아직 맞아?".
allowed-tools: Read Edit Bash WebFetch
---

# Document Polish

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Inspect existing Markdown documents; report by default. With --fix, apply only the
nonsemantic corrections permitted below. An explicit request to rewrite meaning or structure
uses ordinary editing, not this skill's restricted fix mode.

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

Layer 3 issues carry actionable recommendations (table: `reference.md` §Layer 3 Auto-Suggestions);
they are recommendations, so final judgment requires human review.

### Layer 4: Fact Cross-Check (Report-only)

Layer 3 asks whether a claim is *vague*; this layer asks whether it is *false*, for the whole
document. Before Layer 4, read `reference.md` §"Layer 4: Fact Cross-Check Details" (Gate, Checks, Reporting): it defines the
exact patterns and commands.

**Gate**: run only when a scan finds a checkable claim: issue/PR ref (`#N`), repo path (`/` plus
a file extension, or after an existing top-level repo dir), script/function/flag name, commit SHA
(7-40 hex chars with at least one `a`-`f`), or a status assertion ("미구현", "없음", "아직", "지원
안 함") that directly predicates a named target in the same sentence. Otherwise skip the layer and
omit its report line entirely, keeping `gh`/`git` cost off ordinary calls.

**Deterministic checks only**: `gh issue view N --json state` / `gh pr view`, a file-exists test,
`grep` for the name, `git log -1 <sha>`. A claim needing judgment (is a design right, does a
trade-off hold) is out of scope and belongs to `adversarial-review`.

**Command error vs. mismatch.** A check failing for an unrelated reason (`gh` auth/network) is
never 어긋남; it maps to 저장소로 확인 불가. `git log`'s `fatal: bad revision` on a well-formed
SHA is 어긋남 (the lookup ran and the commit isn't there), except on a shallow/partial clone
(`git rev-parse --is-shallow-repository` prints `true`, checked once per Layer 4 pass), where it
is 저장소로 확인 불가.

**Three verdicts, one reported**: 확인됨 / **어긋남** / 저장소로 확인 불가. Report only 어긋남,
with the line number, what the document asserts, and what the check returned.

**Never auto-fixed, and excluded from `--fix` by design.** A false fact means the *content* is
wrong, and "Editor, not Writer" forbids changing content: report the mismatch and stop.

## Workflow

1. Phase 1 Mechanical: markdownlint, links (internal then external), code blocks; auto-fix or list issues.
2. Phase 2 Consistency: term consistency, sentence quality; issues + suggestions.
3. Phase 3 Semantic: vague claims, possibly outdated info, unexplained terms; warnings.
4. Phase 4 Fact Cross-Check (skipped when no checkable claim is present): extract refs, paths,
   names, SHAs, status assertions; verify with gh / git / grep / file existence; report 어긋남 only.

Output: fixed file and/or quality report.

## Tool Usage

| Tool | When | Example |
|------|------|---------|
| Read | Load target MD file | Read file content |
| Bash | Run markdownlint | `markdownlint --fix file.md` |
| Bash | Layer 4 fact checks | `gh issue view 688 --json state`, `git log -1 <sha>`, `grep -rn <name>` |
| WebFetch | Validate external links | Check URL accessibility |
| Edit | Apply auto-fixes | Fix formatting issues (Layers 1-2 only — Layer 4 never edits) |

## Output Modes

Both modes open with `[Document Polish Summary]` (default) or `[Document Polish - Fix Applied]`
(`--fix`) and `File: <path>`. Full templates: `reference.md` §Output Modes.

- **Default**: one line per layer, `Layer 1 (Mechanical): N issues found, M auto-fixed`,
  `Layer 2 (Consistency): ...`, `Layer 3 (Semantic): N warnings`, and
  `Layer 4 (Fact): N mismatch` (omit this line when the gate did not fire), then
  "Run with --fix to apply auto-corrections (Layer 4 mismatches are never among them)."
- **Fix (`--fix`)**: an `Auto-fixed:` list (`Line N: ...`) then `Remaining issues (require manual
  review):` including any 어긋남 line such as `Line 61: 어긋남 — 문서는 #564를 "열려 있음"으로
  서술하지만 gh issue view 564는 CLOSED`.

`--report` is no longer supported; for an LLM-trope audit use a dedicated humanizer such as Humanize KR.

Integration: `doc-concretize` output → `doc-polish --fix` → manual review of remaining suggestions.

## Boundaries

| Aspect | doc-polish Does | doc-polish Does NOT |
|--------|-----------------|---------------------|
| Formatting | ✅ Fix markdown syntax | |
| Expression | ✅ Suggest alternatives | ❌ Rewrite content |
| Structure | ✅ Report issues | ❌ Reorganize sections |
| Content | ✅ Flag concerns | ❌ Add/remove content |
| Facts | ✅ Cross-check against the repo and report mismatches | ❌ Correct a wrong fact (content change) |
| Judgment claims | | ❌ Weigh whether a design or trade-off is right (→ `adversarial-review`) |
| Links | ✅ Validate & report | ❌ Update URLs |
| Style | ✅ Ensure consistency | ❌ Impose new style |

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)
