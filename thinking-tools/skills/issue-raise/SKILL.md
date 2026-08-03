---
name: issue-raise
description: |
  Author and file one GitHub issue from a single natural-language line, or from a build-spec
  Seed handoff — no Socratic interview, no Ambiguity gate. Reads the matching
  .github/ISSUE_TEMPLATE/ file for its headings at call time (never hardcoded), runs the
  backlog-prefilter duplicate check, and gates on user approval before `gh issue create`.

  Trigger when user mentions: 이슈 만들어줘, 이슈 저작, 버그 리포트 열어줘, 기능 제안 이슈 올려줘,
  file an issue, open a github issue, write this up as an issue.
  Routing: called directly for a one-line bug/feature request; build-spec sub-calls it
  automatically right after Seed Emit (no extra user call needed) when the user accepts the
  "이 Seed로 GitHub 이슈를 열까요?" offer. 명세부터 굳혀야 하면 build-spec을 먼저 쓰세요.
allowed-tools: Read Write Bash Glob AskUserQuestion
effort: low
---

# Issue Authoring

## Language Behavior

- **Instructions**: English (optimized for LLM parsing)
- **Output**: Korean by default; English if the user wrote in English

## Prerequisites

- A one-line bug report or feature idea, OR a Seed YAML path handed off by build-spec
  (`docs/specs/{slug}.yaml`)
- `gh` CLI authenticated against the repo (fallback in Phase 3 if absent)

## Core Workflow

### Phase 0: Entry + Template Selection

1. **Entry mode**:
   - **Seed handoff** — input names a Seed YAML path, or the caller is build-spec. `Read` the
     Seed; its `goal`/`constraints`/`success_criteria`/`context` fields are the source data.
     Template = `feature.md` (a Seed crystallizes something to build, never a defect).
   - **Freeform** — a natural-language line. Classify **defect** (something observed vs.
     expected mismatches) vs **proposal** (a capability that doesn't exist yet). Ambiguous →
     one `AskUserQuestion`.
   - Template = `.github/ISSUE_TEMPLATE/bug.md` for a defect, `feature.md` for a proposal.
2. **Read the chosen template file.** Its `## ` headings (frontmatter stripped) are the
   **only** section list this skill uses to assemble the body — never hardcode headings here;
   if the template file changes, this skill's output changes with it, with zero code edit.
3. **Gather missing content** for each non-`(선택)` heading the source data doesn't already
   cover, via `AskUserQuestion` (one round, batch the questions).

### Phase 1: Duplicate Check (mandatory, zero LLM cost)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog-prefilter.py" --intent "{title candidate + keywords}"
```

Never reimplement this scan. Show its result to the user before drafting the body — that
satisfies the record requirement without inventing a heading the template doesn't have. A
`[backlog-scan SKIPPED]` line is shown verbatim, never dropped. If the target already has a
Seed with its own `context.backlog_scan`, run this anyway — Phase 0's scan ran before the
issue title existed, and title terms sharpen the match. Conflicting candidates → confirm with
the user whether to proceed, dedupe against one, or link it (into `관련 이슈·문서`/`## 관련`
if the template carries that heading).

### Phase 2: Body Assembly

Map source fields onto each heading read in Phase 0, one paragraph per heading, in the
template's own order. Skip a heading only when it is marked `(선택)` **and** no source
content exists for it — never invent content for an empty optional heading, never invent a
heading the template doesn't have. Field-mapping detail: [reference.md](reference.md) §1.

### Phase 3: Title + Create

Follow the repo's live convention, not a fixed pattern — `gh issue list --state all --limit 10
--json title` and match the observed `type(scope): ...` shape (rationale: [reference.md](reference.md)
§2). No separate title-format guard hook: a prior prototype's guard reproduced a quote-mention
false positive and was scrapped for it — this skill only *follows* the convention at generation
time.

Show the assembled title + body. `AskUserQuestion` for approval before creating anything.
- Approved → write the body to a temp file, `gh issue create --title "{title}" --body-file
  <path>`. Report the returned URL.
- `gh` absent or no GitHub remote → write the body to `docs/specs/{slug}-issue.md` (freeform:
  a scratch slug) and say so. Never create an issue without the approval step.

## Output Format

```
## 이슈 저작 완료

**템플릿**: `.github/ISSUE_TEMPLATE/{bug|feature}.md`
**중복 검사**: {backlog-prefilter 요약 한 줄}
**URL**: {gh issue create 반환 URL, 또는 폴백 파일 경로}

───
*issue-raise 완료*
```

## Known Limitations

- **Template drift is structural, not a bug**: if `.github/ISSUE_TEMPLATE/*.md` changes shape,
  this skill's output changes with it automatically — but a template with zero `## ` headings
  produces an empty body. That is a template authoring error, not something this skill
  recovers from.
- **Duplicate check inherits the prefilter's ceiling**: term-overlap scoring, closed candidates
  ranked by title only — see `backlog-prefilter.py`'s own docstring.
- **Seed→feature.md mapping is one fixed shape** (reference.md §1); a Seed whose content is
  actually a defect report is out of scope — build-spec crystallizes things to build, not bugs.

## References

- **Field mapping + title convention rationale**: [reference.md](reference.md)
- **Backlog scan script**: `../../scripts/backlog-prefilter.py` (shared with build-spec, #489)
- **Common output schema**: [../../reference/common-schema.md](../../reference/common-schema.md)

## Korean I/O Directive

모든 사용자 대면 출력(중복 검사 결과, 초안, 승인 질문, 완료 요약)은 **한국어**로 작성합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
