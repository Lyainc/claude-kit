# Issue Authoring — Reference

## 1. Field Mapping

The template discovered in Phase 0 is the single source of sections. These tables record the
*content* mapping this skill applies once a template's sections are known — not a second
heading list to keep in sync.

**They are this repo's templates, shown as a worked example of the mapping's shape — not a
spec.** On any other repo the section names differ (`## Describe the bug`, `## What happened?`,
`## Steps to reproduce`), and there the job is the same one these tables demonstrate: match each
source field to the section whose *question* it answers, in the template's own order, and leave
a section out only when it is optional and nothing answers it. Re-derive from Phase 0's section
list; never map onto a heading named here that the live template doesn't have.

### Seed handoff → a proposal template (this repo: `feature.md`)

| Seed field | heading in this repo's `feature.md` |
|---|---|
| `goal.statement` | `## 무엇을 / 왜` |
| `constraints[]` (description, `hard` first) + `success_criteria[]` (as a checklist) | `## 제안 (선택)` |
| `context.integration_points` | `## 영향 범위 (선택)` |
| `context.backlog_scan` (Seed's own) + this skill's own Phase 1 result + `context.dependencies` | `## 관련 이슈·문서 (선택)` |

This repo's `feature.md` has no dedicated Acceptance/success-criteria heading — this is the
honest consequence of reading the template as the single source rather than inventing one.
Success criteria fold into `## 제안` as a checklist under the proposal instead. That folding
generalizes: a Seed field with no matching section goes into the closest section that can
carry it, never into a heading this skill adds.

### Freeform defect → a defect template (this repo: `bug.md`)

| Source | heading in this repo's `bug.md` |
|---|---|
| user's report | `## 증상` |
| reproduction steps (ask if not given) | `## 재현 절차` |
| log/error/command output (ask if not given) | `## 실증` |
| expected behavior | `## 기대 동작` |
| affected plugin/skill/component | `## 스코프` |
| Claude Code version, OS, etc. | `## 환경 (선택)` |

## 2. Title Convention

**A template's own `title:` prefix is a floor, not the whole shape.** It is the convention the
repo *declared*, and the web UI pre-fills exactly that string for every issue filed through the
browser — `gh issue create` does not, so an issue filed by this skill without at least that
prefix is the odd one out in the list. But a human filer types the rest of the title after that
pre-fill, and on this repo the rest routinely adds a scope segment the bare prefix doesn't carry
(`bug.md` declares `title: "fix: "`; the repo's actual issues read
`fix(vault-bridge): 매니페스트가 archived 노트를 올린다`). Applying only the declared prefix would
ship a title *less* specific than what this repo's own history shows, in the one case
(`fix(vault-bridge): ...`) this section exists to protect — so the survey below still runs
even when a template prefix exists, specifically to catch a scope segment the prefix lacks.

`gh issue create --title "{slug}"` (a bare slug) reads wrong on this repo: titles here carry
type and scope instead of relying on labels, because `gh issue create` does not inherit a
template's `labels:` frontmatter — most issues ship unlabeled, so the title prefix is the real
type signal (issue #502's own evidence survey, 100-issue sample). Reading the repo's own last 10
titles before proposing one keeps this skill correct on any repo it runs in, including ones with
a different convention or no template at all, without a second code path — and avoids a
validating hook: a prior project-scoped prototype tried a title-format guard hook and its only
real catch was a build-spec-internal title defect, while the hook itself produced a
quote-mention false positive. Following the convention at *generation* time catches the same
class without a second failure mode.

## 3. Phase 0 detail (moved from SKILL.md, verbatim)

Template discovery (step 2): `issue-template.py --list` resolves the three directories GitHub itself
resolves, reads Markdown templates and `.yml` issue forms alike, and reports each one's kind,
section count, optional-section count, title prefix, and labels. Pick the entry whose `kind`
matches step 1; several of the same kind, or only `other` → one `AskUserQuestion` over the listed
paths. Never guess a filename — `bug.md` here, `bug_report.md` on a repo scaffolded by GitHub,
`bug_report.yml` on one using issue forms.

Section list (step 3): that output is the **only** section list this skill assembles against, and it
is also Phase 2.5's `--template` input, so a `.yml` form passes the same guard as a `.md`
template with no second code path. If the template changes shape, this skill's output
changes with it, with zero code edit. Exit 1 here (a template with zero sections) is not
the same failure as step 2's `--list` finding no template at all — treat it the same way
regardless: take step 4's plain-prose path (§4 has the detail).

No template at all (step 4): the repo chose not to impose a structure, so do not invent one. Write
a title plus plain prose covering what the source data actually says, skip Phase 2.5 (there is
nothing to conform to), and say so in the Output Format's 템플릿 field. Inventing headings here
would ship a body shaped like this repo's conventions into someone else's tracker.

Required-ness (step 5): a `.yml` form's `--headings` output carries no inline optional marker the
way a Markdown template's trailing parenthetical does, so pull the per-section `optional` flag from
`--list --json` instead: find the array entry whose `path` matches the template chosen in step 2,
then read that entry's own `sections[]` array and match each section by `name` against the heading
text printed by `--headings` in step 3.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue-template.py" --list --json
```

Never guess required-ness from the marker style (`(선택)`/`(optional)`) alone — a `.yml`
form states it formally as `validations.required: false` (or, for `checkboxes`, per-option
under `attributes.options[]`), which `--json`'s `optional` flag already resolves for you.

Duplicate check (Phase 1): the prefilter is the same call Phase 2.5's conformance check and Phase 3's
`gh issue create` also go through. Never reimplement this scan. A `[backlog-scan SKIPPED]` line is
shown verbatim, never dropped. Same for a `[backlog-scan PARTIAL]` line (#561) — one side's fetch
failed while the other rendered normally, so the `{backlog-prefilter 요약 한 줄}` in Output Format
must fold that warning in, not compress it away; that side's "0 hits" is unconfirmed, not clean. If
the target already has a Seed with its own `context.backlog_scan`, run this anyway — Phase 0's scan
ran before the issue title existed, and title terms sharpen the match.

## 4. Known Limitations (moved from SKILL.md, verbatim)

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
- **The Seed→proposal-template mapping is one fixed shape** (§1 shows it against
  this repo's template; the shape, not the heading names, is what carries over); a Seed whose content is
  actually a defect report is out of scope — build-spec crystallizes things to build, not bugs.
- **Heading conformance check (Phase 2.5) is a plain regex diff, not a markdown parser** — a
  `## ` inside a fenced code block in the draft (e.g. pasted code with a comment that starts
  with `## `) would be read as a heading. Templates carry no code fences today, so this hasn't
  fired in practice; a draft that legitimately needs one is the case to watch (#563).

## 5. Phase 2.5 detail (moved from SKILL.md, verbatim)

`--template` is Phase 0's normalized section list, not the raw template path — that is what
makes a `.yml` issue form checkable at all (a form carries no `## ` headings, so pointing
this at the raw file would compare against zero sections and pass anything).
`--optional-from` is the raw template path Phase 0 chose: it lets the checker read the same
`optional` flags `issue-template.py --list --json` reports, which a `.yml` form needs because
its section list carries no inline `(선택)` marker (a `.md` template's marker is recognized
without it).

**What passes.** Headings must equal the template's in text and order, except that a heading
Phase 0 reported **optional** may be absent — that is exactly Phase 2's "skip an empty optional
section", so a draft that left one out passes without being padded. A required heading
missing, any reorder, an extra heading, or reworded text (a dropped `(선택)` marker counts —
the #562 case) still fails, and each is reported as that one problem rather than as every
later heading shifting.

Never skip this — Phase 2 only *instructs* headings be copied verbatim; nothing before this
step mechanically confirms they were (#563; observed live in #562, where the template's
`## 제안 (선택)` was assembled as `## 제안`, the `(선택)` marker silently dropped).
**Skipped only when Phase 0 found no template**; say so rather than passing an empty file.

Exit 1: each printed line names the problem and heading (required heading missing / text changed /
out of order / extra / duplicate). Re-run the same command against the new draft — do not proceed
to Phase 3 on an unverified re-render, or the marker-drop failure mode can slip through a second
time undetected. Exit 2 is a plumbing failure, and re-rendering the body fixes nothing here.

## 6. Phase 3 title and labels detail (moved from SKILL.md, verbatim)

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

Labels: `gh issue create` does not inherit them from template frontmatter, so on a repo that
triages by label (rather than by title prefix, as this one does) an issue filed here would
otherwise land untriaged. A label the repo doesn't define makes `gh` fail the whole create; on that
error retry once without `--label` and say which labels were dropped.
