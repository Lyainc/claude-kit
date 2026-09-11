---
name: issue-raise
description: |
  Author and file one GitHub issue from a single natural-language line, or from a build-spec
  Seed handoff — no Socratic interview, no Ambiguity gate. Discovers whatever issue template
  the repo actually ships (Markdown template, `.yml` issue form, or none) and reads its
  sections at call time — never a hardcoded filename — runs the backlog-prefilter duplicate
  check, and gates on user approval before `gh issue create`.

  Trigger when user mentions: 이슈 만들어줘, 이슈 저작, 버그 리포트 열어줘, 기능 제안 이슈 올려줘,
  file an issue, open a github issue, write this up as an issue.
  Routing: called directly for a one-line bug/feature request; build-spec sub-calls it
  automatically right after Seed Emit (no extra user call needed) when the user accepts the
  "이 Seed로 GitHub 이슈를 열까요?" offer. 명세부터 굳혀야 하면 build-spec을 먼저 쓰세요.
allowed-tools: Read Write Bash AskUserQuestion
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

**Nothing about the repo's issue conventions is assumed.** Template filenames, section
headings, the optional-section marker, label names, and the title shape all come from what
the repo ships, read at call time — a repo with GitHub's own `bug_report.md` scaffold, one
with `.yml` issue forms, and one with no template at all are all first-class here. Never
hardcode a template path or heading into this skill.

## Core Workflow

### Phase 0: Entry + Template Selection

1. **Entry mode** — decides the *kind*, never the filename:
   - **Seed handoff** — input names a Seed YAML path, or the caller is build-spec. `Read` the
     Seed; its `goal`/`constraints`/`success_criteria`/`context` fields are the source data.
     Kind = **proposal** (a Seed crystallizes something to build, never a defect).
   - **Freeform** — a natural-language line. Classify **defect** (something observed vs.
     expected mismatches) vs **proposal** (a capability that doesn't exist yet). Ambiguous →
     one `AskUserQuestion`.
2. **Discover what the repo actually ships:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue-template.py" --list
   ```

   It resolves the three directories GitHub itself resolves, reads Markdown templates and
   `.yml` issue forms alike, and reports each one's kind, section count, optional-section
   count, title prefix, and labels. Pick the entry whose `kind` matches step 1; several of the
   same kind, or only `other` → one `AskUserQuestion` over the listed paths. Never guess a
   filename — `bug.md` here, `bug_report.md` on a repo scaffolded by GitHub, `bug_report.yml`
   on one using issue forms.
3. **Read the chosen template's sections:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue-template.py" --headings {path} > {tmp}/tpl.md
   ```

   That output is the **only** section list this skill assembles against, and it is also
   Phase 2.5's `--template` input, so a `.yml` form passes the same guard as a `.md`
   template with no second code path. If the template changes shape, this skill's output
   changes with it, with zero code edit. Exit 1 here (a template with zero sections) is not
   the same failure as step 2's `--list` finding no template at all — treat it the same way
   regardless: take step 4's plain-prose path (Known Limitations has the detail).
4. **No template at all** (`--list` prints `[issue-template NONE]`, exit 1): the repo chose
   not to impose a structure, so do not invent one. Write a title plus plain prose covering
   what the source data actually says, skip Phase 2.5 (there is nothing to conform to), and
   say so in the Output Format's 템플릿 field. Inventing headings here would ship a body
   shaped like this repo's conventions into someone else's tracker.
5. **Gather missing content** for each *required* section the source data doesn't already
   cover, via `AskUserQuestion` (one round, batch the questions). A `.yml` form's `--headings`
   output carries no inline optional marker the way a Markdown template's trailing
   parenthetical does, so pull the per-section `optional` flag from `--list --json` instead:
   find the array entry whose `path` matches the template chosen in step 2, then read that
   entry's own `sections[]` array and match each section by `name` against the heading text
   printed by `--headings` in step 3.

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue-template.py" --list --json
   ```

   Never guess required-ness from the marker style (`(선택)`/`(optional)`) alone — a `.yml`
   form states it formally as `validations.required: false` (or, for `checkboxes`, per-option
   under `attributes.options[]`), which `--json`'s `optional` flag already resolves for you.

### Phase 1: Duplicate Check (mandatory, zero LLM cost)

Use Bash to run the shared prefilter — the same call Phase 2.5's conformance check and Phase 3's
`gh issue create` also go through:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog-prefilter.py" --intent "{title candidate + keywords}"
```

Never reimplement this scan. Show its result to the user before drafting the body — that
satisfies the record requirement without inventing a heading the template doesn't have. A
`[backlog-scan SKIPPED]` line is shown verbatim, never dropped. Same for a `[backlog-scan
PARTIAL]` line (#561) — one side's fetch failed while the other rendered normally, so the
`{backlog-prefilter 요약 한 줄}` in Output Format must fold that warning in, not compress it
away; that side's "0 hits" is unconfirmed, not clean. If the target already has a
Seed with its own `context.backlog_scan`, run this anyway — Phase 0's scan ran before the
issue title existed, and title terms sharpen the match. Conflicting candidates → confirm with
the user whether to proceed, dedupe against one, or link it (into `관련 이슈·문서`/`## 관련`
if the template carries that heading).

### Phase 2: Body Assembly

Map source fields onto each section read in Phase 0, one paragraph per section, in the
template's own order. Skip a section only when Phase 0 reported it **optional** *and* no
source content exists for it — never invent content for an empty optional section, never
invent a section the template doesn't have. Field-mapping detail: [reference.md](reference.md) §1.

### Phase 2.5: Heading Conformance Check (mandatory, zero LLM cost)

Write the assembled body to a temp file, then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-heading-match.py" --template {tmp}/tpl.md --draft {temp file path}
```

`--template` is Phase 0's normalized section list, not the raw template path — that is what
makes a `.yml` issue form checkable at all (a form carries no `## ` headings, so pointing
this at the raw file would compare against zero sections and pass anything).

Never skip this — Phase 2 only *instructs* headings be copied verbatim; nothing before this
step mechanically confirms they were (#563; observed live in #562, where the template's
`## 제안 (선택)` was assembled as `## 제안`, the `(선택)` marker silently dropped).
**Skipped only when Phase 0 found no template**; say so rather than passing an empty file.

- **Exit 0** → proceed to Phase 3 unchanged.
- **Exit 1** (heading mismatch) → the printed table names the exact heading and position.
  Re-render Phase 2's mapping against it, then **re-run this same command against the new
  draft** before moving on — do not proceed to Phase 3 on an unverified re-render, or the
  marker-drop failure mode can slip through a second time undetected. If Phase 0's source data
  legitimately changes a heading (not an assembly error), surface the mismatch inside Phase 3's
  approval prompt instead of silently overriding or silently proceeding.
- **Exit 2** (usage error — an unreadable template/draft path) → this is a plumbing failure,
  not a heading mismatch, and re-rendering the body fixes nothing here. Report the raw error to
  the user and stop; do not loop on Phase 2 trying to fix a path/I-O problem.

### Phase 3: Title + Create

**Title.** The template's own `title:` prefix (when Phase 0 reported one) is a floor, not the
whole shape — `gh issue list --state all --limit 10 --json title` still runs to check whether
the observed history adds a scope segment the bare prefix doesn't carry (rationale:
[reference.md](reference.md) §2):
1. Match the observed shape (e.g. `fix(scope): `) against the template's prefix. If the survey's
   type matches the prefix but adds a scope the prefix lacks (this repo: prefix `fix: `,
   observed `fix(vault-bridge): ...`), use the fuller observed shape — the template prefix is
   the minimum GitHub's web UI pre-fills, not a ceiling on what a human filer then adds, and
   dropping the scope regresses behind what the repo's issues actually look like.
2. Otherwise use the template's prefix as-is. It is the convention the repo *declared*, and
   `gh issue create` does not apply it the way the web UI does — so prepend it explicitly or
   issues filed by this skill drift from every issue filed through the browser.
3. No template prefix at all → the observed shape alone, or a bare slug if the survey finds
   nothing consistent.

No separate title-format guard hook: a prior prototype's guard reproduced a quote-mention
false positive and was scrapped for it — this skill only *follows* the convention at generation
time.

**Labels.** Pass the template's `labels:` from Phase 0 as `--label` — `gh issue create` does
not inherit them from template frontmatter, so on a repo that triages by label (rather than by
title prefix, as this one does) an issue filed here would otherwise land untriaged. A label the
repo doesn't define makes `gh` fail the whole create; on that error retry once without
`--label` and say which labels were dropped.

Show the assembled title + body. `AskUserQuestion` for approval before creating anything.
- Approved → write the body to a temp file, `gh issue create --title "{title}" --body-file
  <path> [--label ...]`. Report the returned URL.
- `gh` absent or no GitHub remote → write the body to `{slug}-issue.md` under `docs/specs/`
  if that directory already exists, else the repo root, and report the path. Never create a
  directory for the fallback, and never create an issue without the approval step.

## Output Format

```
## 이슈 저작 완료

**템플릿**: {Phase 0이 고른 실제 경로, 또는 `없음 — 평문 본문`}
**중복 검사**: {backlog-prefilter 요약 한 줄}
**라벨**: {붙인 라벨, 없으면 생략; 드롭됐으면 무엇이 왜}
**URL**: {gh issue create 반환 URL, 또는 폴백 파일 경로}

───
*issue-raise 완료*
```

## Known Limitations

- **Template drift is structural, not a bug**: if the repo's template changes shape, this
  skill's output changes with it automatically. A template that genuinely carries zero
  sections is reported by `issue-template.py --headings` as an error (exit 1), not silently
  assembled into an empty body — treat it as "no template" and take Phase 0 step 4's plain-prose
  path.
- **`.yml` issue forms are read for their section labels, not their input semantics**: a
  form's `dropdown` options, `checkboxes` items, and per-field `description` text are not
  carried into the body — the assembled issue answers each field's label in prose. A repo whose
  triage automation parses form answers by exact option string gets a body it can read but not
  machine-parse. Filing through the web UI is the answer there, not this skill.
- **Form parsing is an indentation scanner, not a YAML parser** (no PyYAML in this toolchain):
  a form using YAML anchors, folded multi-line labels, or flow mappings reads as fewer sections
  than it has. `--list`'s section count is the check — if it disagrees with the form, stop.
- **Duplicate check inherits the prefilter's ceiling**: term-overlap scoring, closed candidates
  ranked by title only — see `backlog-prefilter.py`'s own docstring.
- **The Seed→proposal-template mapping is one fixed shape** (reference.md §1 shows it against
  this repo's template; the shape, not the heading names, is what carries over); a Seed whose content is
  actually a defect report is out of scope — build-spec crystallizes things to build, not bugs.
- **Heading conformance check (Phase 2.5) is a plain regex diff, not a markdown parser** — a
  `## ` inside a fenced code block in the draft (e.g. pasted code with a comment that starts
  with `## `) would be read as a heading. Templates carry no code fences today, so this hasn't
  fired in practice; a draft that legitimately needs one is the case to watch (#563).

## References

- **Field mapping + title convention rationale**: [reference.md](reference.md)
- **Template discovery + section extraction**: `../../scripts/issue-template.py`
- **Backlog scan script**: `../../scripts/backlog-prefilter.py` (shared with build-spec, #489)
- **Heading conformance script**: `../../scripts/check-heading-match.py` (#563)
- **Common output schema**: [../../reference/common-schema.md](../../reference/common-schema.md)

## Korean I/O Directive

모든 사용자 대면 출력(중복 검사 결과, 초안, 승인 질문, 완료 요약)은 **한국어**로 작성합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
