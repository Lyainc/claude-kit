# Skill ownership and routing boundaries

This is a maintainer audit map, not another runtime router. Skill descriptions are the
runtime discovery source; bodies own procedure and effects. Route by requested object,
operation and result. Shared vocabulary alone is insufficient. Composition is allowed when
one requested outcome genuinely needs multiple stages; do not invoke every adjacent skill.

Tracked in [#794](https://github.com/Lyainc/claude-kit/issues/794); personal instruction
adapters are tracked separately in [local-harness #23](https://github.com/Lyainc/local-harness/issues/23).

| Skill | Owns | Does not own / handoff |
|---|---|---|
| diverse-sampling | Alternative creative directions, then optionally expansion of a selected one | Plain expansion → ordinary writing/doc-concretize; evaluation → expert-panel |
| expert-panel | Weighing multiple positions for a decision | Idea generation → diverse-sampling; one-claim attack → adversarial-review |
| adversarial-review | Stress-testing a specific claim through adversarial rounds | Routine code review; multi-position consensus; whole-document mechanical checks |
| unknown-discovery | Surfacing unknowns and blind spots through interview | A settled build target's Seed → build-spec; every mention of “missing” |
| build-spec | Crystallizing a chosen build target into a YAML Seed | Open-ended discovery; prose document; implementation |
| doc-concretize | Authoring a new structured Markdown document | Existing-document inspection → doc-polish; substantive rewrite → ordinary editing |
| doc-polish | Inspecting existing Markdown; optional nonsemantic --fix | Rewriting meaning/structure; design verdicts; code/configuration changes |
| issue-raise | Authoring and filing one requested work issue | Spec discovery; retro's observed-waste issue workflow; filing without authority |
| next-goal | Selecting worthwhile follow-up and authoring its completion condition | Session cleanup, retro, implementing the selected goal |
| session-close (optional external skill) | Session reconciliation, authorized close/sweep; invokes next-goal | A next prompt alone → next-goal; automatically running retro/distill |
| retro | Observed session waste → deduplicated improvement issue | Vault structural audit; generic issue drafting; placing policies |
| distill | Reusable procedural technique proposal | Writing/placing the accepted rule → add-policy; declarative facts → vault-save |
| add-policy | Placing an accepted rule in reminder/hook/skill | Rediscovering its value; knowledge storage; owning all instruction-file edits |
| vault-save | Requested raw/source/authored reference capture | Compiled reusable domain knowledge → wiki; behavior rules → add-policy |
| wiki | Compiling and reconciling domain knowledge for recall | Raw clippings/session dumps → vault-save; corpus structural audit |
| audit | Vault-wide structural/metadata/link/wiki-health triage and authorized eligible fixes | Prose quality → doc-polish; session waste → retro |
| base | Generating an Obsidian .base view | Editing the notes that the view reads |
| vault-link | Binding a code repository to a vault project | Saving content; compiling knowledge |
| vault-manifest-refresh | Rebuilding the manifest cache | Editing corpus content or choosing what is worth keeping |
| vault-commit | An authorized Git commit of vault changes | Content creation/compilation; source-repository Git workflow |

The vault-save `--type discussion` path preserves a thinking-tools discussion artifact;
wiki compiles domain knowledge. Sharing wiki/ as a destination does not make these the same
operation. The manifest and Git helpers likewise compose with content work without owning it.

## Scenario checks for boundary changes

These are review cases, not claims of measured model behavior. Keep them alongside edits so
reviewers can evaluate plausible misroutes without relying on word-match tests.

| Request | Expected entry / reason |
|---|---|
| “다음 세션 프롬프트만 써줘” | next-goal; no cleanup authority |
| “세션 마무리하고 다음 목표도 정해줘” | session-close → next-goal |
| “이 초안 문단을 더 구체적으로 써줘” | ordinary editing; no alternative-generation request |
| “세 가지 다른 방향을 만들고 하나를 문서로 발전시켜줘” | diverse-sampling → doc-concretize |
| “README 링크와 사실이 맞는지 검사해줘” | doc-polish; report unless nonsemantic fixes authorized |
| “README 구조를 바꾸고 설치 설명을 다시 써줘” | ordinary editing; doc-polish cannot own substantive rewriting |
| “이 설정 파일을 정리해줘” | ordinary configuration work; no document workflow from “정리” |
| “이 규칙을 앞으로 적용하도록 저장해줘” | add-policy for an accepted reusable rule; not vault-save |
| “이 글을 report.md로 저장해줘” | explicit file destination; not implicit vault capture |
| “이 링크를 볼트에 저장해줘” | vault-save |
| “이번 반복 실패를 회고해줘” | retro; no automatic distill or session-close |
| “내 기획의 맹점을 찾아줘” | unknown-discovery; no Seed until a build target is selected |

## 2026-10-02 audit dispositions

- Narrowed diverse-sampling's generic enhancement entry and aligned its body; preserving
  creative generation does not require routing all prose expansion through two skills.
- Corrected doc-polish discovery to match existing --fix behavior: report by default,
  nonsemantic correction only with --fix. Substantive editing remains a native task.
- Distinguished doc-concretize's new-document output from answer clarification/config edits.
- Shortened audit discovery; detailed defect taxonomy remains in its body/reference.
- Narrowed vault-save's generic “save” triggers to an established vault intent. Its typed
  decision/discussion modes remain. Explicit destination and format always govern.
- session-close's prompt-only entry is assigned to next-goal in local-harness.
- Remaining skills already have distinct outputs/effects; no merger is justified by common
  words. Existing user changes to build-spec and next-goal were preserved during this audit.

Deployment note: these are plugin source changes. A source edit does not change a pinned
installed plugin. Use the normal tested release/update path; do not hand-edit cache files.
