---
name: issue-raise
description: |
  Author and file one GitHub issue from a natural-language request or build-spec Seed, using
  the repository template, duplicate check, and user approval. Use build-spec first when the
  requirements need crystallizing.

  Trigger when user mentions: 이슈 만들어줘, 이슈 저작, 버그 리포트 열어줘, 기능 제안 이슈 올려줘,
  file an issue, open a github issue, write this up as an issue.
allowed-tools: Read Write Bash AskUserQuestion
---

# Issue Authoring

## Codex Portability

Codex: read [the portability contract](../../reference/codex-portability.md) first. Keep Phase 3's
approval gate before `gh issue create`; use its native question path.

## Prerequisites

- Bug report, feature idea, or build-spec Seed path.
- Authenticated `gh` CLI; absent → Phase 3 fallback.

## Core Workflow

### Phase 0: Entry + Template Selection

1. **Entry mode** — decides the *kind*, never the filename:
   - **Seed handoff** — input names a Seed YAML path, or the caller is build-spec. First use
     `Bash`: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seed-relations.py" metadata <seed> --json`.
     No Seed `Read`/cat/Grep before success; failure holds intake. `walk`/`read` is no substitute.
     Follow [the lifecycle contract](../../reference/seed-lifecycle.md): unknown requirements need
     user confirmation before application, paused needs approved resume, and closed reuse needs a
     new approved Seed with pinned provenance. Naming a path does not authorize activation; do not
     apply withdrawn items or expand scope. `Read` only relevant fields; its
     `goal`/`constraints`/`success_criteria`/`context` are source data. List constraints and success criteria by full identifier
     (`<seed-slug>/constraint-1 · 설명`, convention: `reference/identifiers.md`), never with an invented issue number.
     Kind = **proposal** (a Seed crystallizes something to build, never a defect).
   - **Freeform** — a natural-language line. Classify **defect** (observed vs. expected
     mismatch) vs **proposal** (a capability that doesn't exist yet). Ambiguous → one
     `AskUserQuestion`.
2. **Discover what the repo ships:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue-template.py" --list
   ```

   Pick the entry whose `kind` matches step 1; several of that kind, or only `other` → one
   `AskUserQuestion` over the listed paths. Never guess a filename.
3. **Read the chosen template's sections:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/issue-template.py" --headings {path} > {tmp}/tpl.md
   ```

   That output is the **only** section list this skill assembles against, and Phase 2.5's
   `--template` input. Exit 1 (a template with zero sections) is handled like step 4.
4. **No template at all** (`--list` prints `[issue-template NONE]`, exit 1): do not invent a
   structure. Write a title plus plain prose covering what the source data says, skip Phase
   2.5, and say so in the Output Format's 템플릿 field.
5. **Gather missing content** for each *required* section the source data doesn't cover, via
   `AskUserQuestion` (one round, batch the questions). Take required-ness from
   `issue-template.py --list --json` (the matching entry's `sections[]` `optional` flag, matched
   by `name`), never from the `(선택)`/`(optional)` marker style alone. Detail:
   [reference.md](reference.md) §3.

### Phase 1: Duplicate Check (mandatory, zero LLM cost)

Use Bash to run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backlog-prefilter.py" --intent "{title candidate + keywords}"
```

Never reimplement it; show its result before drafting the body. A
`[backlog-scan SKIPPED]` line is shown verbatim, never dropped; a `[backlog-scan PARTIAL]` line
must be folded into the Output Format's `{backlog-prefilter 요약 한 줄}` (that side's "0 hits" is unconfirmed). Run it even if a Seed has its own `context.backlog_scan`.
Conflicting candidates → confirm with the user whether to proceed, dedupe against one, or link
it (into `관련 이슈·문서`/`## 관련` if the template carries that heading).

### Phase 2: Body Assembly

Map source fields onto each section read in Phase 0, one paragraph per section, in the
template's own order. Skip a section only when Phase 0 reported it **optional** *and* no
source content exists for it — never invent content for an empty optional section, never
invent a section the template doesn't have. Field-mapping detail: [reference.md](reference.md) §1.

### Phase 2.5: Heading Conformance Check (mandatory, zero LLM cost)

Write the body to a temp file, then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-heading-match.py" --template {tmp}/tpl.md --draft {temp file path} --optional-from {chosen template path}
```

`--template` is Phase 0's normalized section list (not the raw template path); `--optional-from`
is the raw template path Phase 0 chose. Headings must equal the template's in text and order
(a dropped `(선택)` marker fails), except that an **optional** heading may be absent. Never
skip this; skipped only when Phase 0 found no template — say so. Detail: [reference.md](reference.md) §5.

- **Exit 0** → proceed to Phase 3 unchanged.
- **Exit 1** (heading mismatch) → re-render Phase 2's mapping against the printed problems, then
  **re-run this same command against the new draft** before moving on. If source data
  legitimately changes a heading, surface the mismatch inside Phase 3's approval prompt instead
  of silently overriding or proceeding.
- **Exit 2** (usage error, unreadable path) → plumbing failure, not a mismatch. Report the raw
  error to the user and stop; do not loop on Phase 2.

### Phase 3: Title + Create

**Title.** The template's own `title:` prefix is a floor, not the whole shape —
`gh issue list --state all --limit 10 --json title` still runs to check whether the repo's
history adds a scope segment the prefix lacks (rationale: [reference.md](reference.md) §2):
1. Survey type matches the prefix but adds a scope (prefix `fix: `, observed
   `fix(vault-bridge): ...`) → use the fuller observed shape.
2. Otherwise prepend the template's prefix explicitly (`gh issue create` does not apply it).
3. No template prefix → the observed shape alone, or a bare slug if nothing is consistent.

**Labels.** Pass the template's `labels:` from Phase 0 as `--label` (`gh issue create` does not
inherit them). A label the repo doesn't define makes `gh` fail the whole create; on that error
retry once without `--label` and say which labels were dropped.

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

If `--list`'s section count disagrees with a `.yml` form, stop. A defect-report Seed is out of
scope. Form-scanner, template-drift and regex-diff limits: [reference.md](reference.md) §4.

## References

- [reference.md](reference.md): field mapping, title rationale and detail.

## Korean I/O Directive

모든 사용자 대면 출력(중복 검사 결과, 초안, 승인 질문, 완료 요약)은 **한국어**로 작성합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
