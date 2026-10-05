---
name: doc-concretize

description: |
  Create a new structured Markdown document through recursive concretization and a separate
  final check. Use doc-polish for inspecting existing docs, ordinary editing for substantive
  rewrites, and build-spec for YAML specs. A request to clarify an answer or edit configuration
  does not invoke this document workflow.

  Trigger when user mentions: 구체화, 문서화, 체계적 정리, 개념 정리, 아이디어 문서화, 글로 정리,
  doc-concretize, concretize, "이 개념을 문서로 정리해줘".
allowed-tools: Read AskUserQuestion WebFetch Agent
---

# Document Concretization

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Its Codex rules override Claude-only mechanics below; Claude Code ignores this section.

Transform abstract concepts into concrete, well-structured documentation through recursive writing and rigorous verification.

## Language Behavior

Output MUST match the input language (mixed input follows the dominant language); if the user
provides a reference document, match its language and tone.

## Prerequisites

- Abstract concept or idea to concretize
- (Optional) Reference document for style matching
- (Optional) Specific format/structure request

## Core Workflow

### Phase 1: Concept Analysis

1. Decompose core concepts and identify relationships between them
2. Identify semantic units (3-7 chunks) for document structure
3. Determine logical order and dependencies
4. Estimate output length:
      - If < 800 chars → switch to standard writing (skip this skill)
      - If 800-2000 chars → **Quick Mode**: compress to Phase 1 → Phase 3 (skip Phase 2, Phase 4 reduced to single review pass)
      - If > 2000 chars → **Full Mode**: execute all phases
5. If reference document exists, analyze and record its style

**Mandatory State Tracking** *(Internal Only, not shown to users)*: keep a JSON object with
`segments` (`id`, `name`, `status`, `depends_on`), `current`, `style_ref`, and `quality_gate`
(schema: `reference.md` §State Tracking JSON Schema).

**Quality Gate**: Concepts decomposed + relationships mapped + segments defined → proceed

### Quick Mode (800-2000 chars)

Phase 1, then Phase 3 (no Phase 2: use linear ordering; the isolated final Verify still runs after
assembly), then a Phase 4 single completeness review pass (no adversarial check or self-critique
questions), then Phase 5 Basic Polish.

### Phase 2: Structure Design

Plan the hierarchy (sections, subsections, flow), the ordering strategy (chronological,
priority-based, conceptual progression), and resolve dependencies so prerequisites precede
dependents. **Quality Gate**: structure and ordering defined → Phase 3.

### Phase 3: Content Build

For each segment:

```
[Build]
1. Load context from previous sections
2. Draft current section
   - One idea per sentence
   - No detail omission
   - Clear subject-predicate structure
   - Fact uncertain → call AskUserQuestion or WebFetch
```

A per-segment self-check on top of this draft would be written and checked by the same context —
exactly the self-verification loop that lets a draft pass its own bar. So drafting stops at
[Build]; verification happens once, below, over the assembled whole.

**Isolated final Verify** (required before the document is handed to the user): once all segments
are drafted, run this 4-item checklist over the whole document in a **separate Agent subagent** —
pass only `{the assembled document + the intent/audience one-liner + the 4 Verify items}`, and
never the drafting rationale:

```
□ Logical connection between sections?
□ No contradictions or redundancy?
□ Consistent tone and manner?
□ Reference style maintained? (if applicable)
```

Prefix each segment in that document with its own marker — `[S1] {segment title}`,
`[S2] ...` — because without them the subagent guesses segment boundaries from headings, which is
not the same partition. It returns pass/fail per `S{n}` plus the failing line. One call per
document, not per segment. **Agent call fails / no response** → verify inline against the same
checklist and tell the user the final pass was not isolated. A subagent that returns only idle
notifications and no final text after one re-request counts as unavailable and takes this same
fallback (#647) — never wait on it further.

**[Reflect]** — fires only on an isolated-Verify failure, never per segment:
- All `S{n}` passed → document is done
- 1-2 `S{n}` failed → revise the failing segment(s) and re-run the isolated Verify (max 3 attempts)
- 3+ `S{n}` failed → rewrite the failing segment(s) entirely

**Critical Issues** (require user approval):
- Core premise has multiple interpretations
- Conflicting information discovered
- Sensitive claims or judgments involved

**Quality Gate**: All segments drafted + isolated Verify passed for all `S{n}` → proceed

### Phase 4: Completeness Check

1. **Full Read**: Review entire document from start to end
2. **Self-Critique**: Answer these mandatory questions:
   - What claims lack sufficient evidence?
   - What important perspectives or counterarguments are missing?
   - What parts are unnecessarily long or repetitive?
   - What content diverges from the original request?
3. **Logical Gap Detection**: Identify missing connections, unsupported claims, or contradictions
4. **Adversarial Check**: Generate at least one counter-argument to main claims
5. **Intent Verification**: Confirm alignment with original request
6. **Missing Content Check**: Ensure all core concepts are covered

**Quality Gate**: All logical gaps addressed + no contradictions + all critical content present → proceed

### Phase 5: Basic Polish

**Grammar & Spelling** (mandatory):
- Fix spacing, spelling, particle errors

**Reference Style Maintenance** (if applicable):
- Reflect user's tone and style from reference document
- Confirm with user if tone change is necessary

**Quality Gate**: No grammar errors + reference style maintained → complete

## Tool Usage

AskUserQuestion clarifies ambiguous concepts and Critical Issues; WebFetch fact-checks numbers,
quotes, and external info; Agent runs the isolated final Verify over the assembled document
(document + 4 Verify items in, per-segment pass/fail out); Read loads a reference document.

## Output Format

```
[Completed Document]

───
*N개 섹션 작성 완료 · 검토 통과*
```

**Conditional Footer Variants**:

- With style reference: `*N개 섹션 작성 완료 · 검토 통과 · 스타일: [reference]*`
- With revisions: `*N개 섹션 작성 완료 · 검토 통과 (N회 수정)*`

**Fallback Output** (if process fails):

- Korean: `일반 응답으로 대체되었습니다.`
- English: `Falling back to standard response.`

## Expression Quality Enhancement

`doc-concretize` is the Writer (content: logic, structure, completeness); for expression quality
run `doc-polish` afterwards.

## References

- **Detailed procedures**: See [reference.md](reference.md)
- **Examples**: See [examples.md](examples.md)
