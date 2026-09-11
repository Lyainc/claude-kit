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
