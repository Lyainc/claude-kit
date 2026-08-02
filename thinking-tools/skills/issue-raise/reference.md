# Issue Authoring — Reference

## 1. Field Mapping

The template file read in Phase 0 is the single source of headings. These tables record the
*content* mapping this skill applies once a template's headings are known — not a second
heading list to keep in sync. If a template file's headings change, re-derive the mapping from
its new `## ` list rather than trusting this table.

### Seed handoff → `feature.md`

| Seed field | `feature.md` heading |
|---|---|
| `goal.statement` | `## 무엇을 / 왜` |
| `constraints[]` (description, `hard` first) + `success_criteria[]` (as a checklist) | `## 제안 (선택)` |
| `context.integration_points` | `## 영향 범위 (선택)` |
| `context.backlog_scan` (Seed's own) + this skill's own Phase 1 result + `context.dependencies` | `## 관련 이슈·문서 (선택)` |

`feature.md` has no dedicated Acceptance/success-criteria heading — this is the honest
consequence of reading the template as the single source rather than inventing one. Success
criteria fold into `## 제안` as a checklist under the proposal instead.

### Freeform defect → `bug.md`

| Source | `bug.md` heading |
|---|---|
| user's report | `## 증상` |
| reproduction steps (ask if not given) | `## 재현 절차` |
| log/error/command output (ask if not given) | `## 실증` |
| expected behavior | `## 기대 동작` |
| affected plugin/skill/component | `## 스코프` |
| Claude Code version, OS, etc. | `## 환경 (선택)` |

## 2. Title Convention

`gh issue create --title "{slug}"` (a bare slug) reads wrong on this repo: titles here carry
type and scope (`fix(vault-bridge): 매니페스트가 archived 노트를 올린다`) instead of relying on
labels, because `gh issue create` does not inherit a template's `labels:` frontmatter — most
issues ship unlabeled, so the title prefix is the real type signal (issue #502's own evidence
survey, 100-issue sample). Reading the repo's own last 10 titles before proposing one keeps
this skill correct on any repo it runs in, including ones with a different convention, without
a second code path — and avoids a validating hook: a prior project-scoped prototype tried a
title-format guard hook and its only real catch was a build-spec-internal title defect, while
the hook itself produced a quote-mention false positive. Following the convention at
*generation* time catches the same class without a second failure mode.
