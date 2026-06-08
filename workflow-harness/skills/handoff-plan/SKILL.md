---
name: handoff-plan
description: "Backlog handoff planner for the ⑤ execution loop: read open GitHub issues, chunk them by dependency + domain into single-session parallelizable units, propose epic candidates behind a user-confirmed gate, and emit goal-doc(#100) slice bindings the next session's /goal can run directly. Trigger: 핸드오프, 핸드오프 계획, 이슈 청킹, 백로그 정리, 에픽 묶기, 다음 세션 계획, 이슈 묶어줘, handoff, handoff plan, chunk issues, backlog triage, plan next session. Routing: this is the ⑤ harness backlog→goal-doc planner; the existing vault-bridge /handoff (③) stays the session continuation-prompt generator — distinct roles, no overlap. Example: '/handoff-plan' or '핸드오프 계획 짜줘'."
model: inherit
allowed-tools: Read Write Bash Grep Glob AskUserQuestion
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion
prompts, confirmation messages, the rendered plan) MUST be in Korean. Instructions
below are English for LLM parsing.

# handoff-plan — backlog → goal-doc slice binding (layer ⑤)

`handoff-plan` automates the single most expensive manual step of the user's dev
loop: *"gather the open issues → understand status → chunk them → bundle epics →
carve out what's parallelizable this session."* It reads the open GitHub backlog
(`gh`, external data), chunks it by **dependency + domain** into single-session
units, proposes **epic candidates behind a user-confirmed gate**, and emits each
chunk as a **goal-doc(#100) slice binding** that the next session's `/goal` can
run directly. It is the ⑤ harness counterpart to the leaf cognitive/output
skills — it *plans the loop*, it does not author content.

## Physical-location ruling (#140 gate — ratified at build, G15)

**This skill lives in ⑤ `workflow-harness`, not a ② leaf plugin.** Rationale (the
#140 one-line record): the deliverable's center of gravity is the **goal-doc slice
binding that feeds the slice loop** (next-session `/goal` entry) — that is ⑤ slice-loop
work, not ② output authoring. A ⑤ skill reading `gh` (external) and writing a
goal-doc (a ⑤ artifact) keeps the dependency one-way (CON-5): no leaf depends back
on it. The existing **vault-bridge `/handoff` (③ delivery)** stays the
*continuation-prompt generator* (session-to-session handoff); this skill is the
*backlog chunking → goal-doc* planner. **Distinct roles — no duplicate definition.**
(C-2 "no thin new plugin" does not apply: `workflow-harness` is the ⑤ home already
established in G14; this skill moves in there.)

## Boundary & safety (constitutional — do not relax)

Single source of truth: [`docs/design/claude-kit-boundary.md`](../../../docs/design/claude-kit-boundary.md) §5.

- **CON-5 one-way dependency**: `handoff-plan` (harness, ⑤) only *reads* external
  data (`gh` issues, repo goal-docs/specs) and *produces* a ⑤ artifact (a goal-doc
  draft). It NEVER modifies leaf-plugin code, and nothing in a leaf depends back on
  it. Native delegation first: issue I/O is `gh`, the produced goal-doc is executed
  by native `/goal` — the harness only adds the chunking + binding layer native
  cannot express.
- **CON-1 / Write Role Contract**: `handoff-plan` performs **NO vault write**. A
  goal-doc is a *repo artifact* under `docs/plans/goal-docs/`, not a vault note, so
  writing it is outside CON-1's scope entirely — but it is still gated: the file is
  written only after the user confirms (OUTPUT phase). If the user instead keeps the
  plan in-chat, nothing is written. The skill never touches `~/vault`.
- **CON-3 self-approval**: this is a *generation* skill, so the same-context
  self-approval ban does not apply to running it. But the goal-docs it emits MUST
  bind the critique slice of any `feature-full` chunk to a **separate** skill
  (`adversarial-review` | `code-reviewer`), never self-review — the emitted recipe
  carries CON-3 forward (goal-doc-spec §3.6).
- **User-confirmed gate (silent forbidden, #125 §2 safeguard)**: epic creation,
  epic↔issue linking, and any issue mutation are proposed as candidates and applied
  ONLY on explicit user confirmation via `gh`. Silent auto-create / auto-link /
  auto-edit is forbidden. Chunking and binding are read-only proposals until the
  user confirms an action.

## Pipeline: COLLECT → CHUNK → EPIC → BIND → OUTPUT

Phases 1–2 are zero-mutation analysis. Phase 3 (EPIC) and Phase 5 (OUTPUT file
write / issue mutation) are the only sites that change state, each behind a
user-confirmed gate.

---

## Phase 1 — COLLECT (gather the open backlog, zero mutation)

1. **Pre-flight**: confirm `gh` is available and authenticated. If not, emit a
   Korean note (`gh auth login` 안내) and stop — do not fabricate a backlog.
   ```bash
   gh auth status >/dev/null 2>&1 || echo "GH_UNAVAILABLE"
   ```
2. **Fetch open issues** with the fields chunking needs (number, title, labels,
   body for dependency extraction). Cap the body scan but never silently drop
   issues — report the count:
   ```bash
   gh issue list --state open --limit "${HANDOFF_ISSUE_LIMIT:-200}" \
     --json number,title,labels,body,milestone 2>/dev/null
   ```
3. **Optional scope filter**: if the user named a focus (an epic number, a label,
   a domain), narrow to it; otherwise take the whole open set. State which filter
   was applied.
4. **Extract dependency signals** per issue (read-only, from the body): `Deps`,
   `Refs #N`, `depends_on`, `Parent Epic: #N`, "선행", "후속", "blocked by". Build a
   lightweight `{issue → {refs:[...], epic:#N|null, domain, labels}}` map. Domain
   is inferred from labels + path hints in the body (e.g. `vault-bridge`,
   `workflow-harness`, `telemetry`, `obsidian-vault-manager`, `docs/design`).

**Output of this phase**: a deduped issue list with dependency/domain metadata.
No file is written, no issue is touched.

---

## Phase 2 — CHUNK (dependency + domain → single-session parallelizable units)

Group the collected issues so each chunk is something a *single session* can take
on without thrashing. The two grouping axes:

1. **Dependency order**: issues on a dependency chain (`A Refs B`, `depends_on`)
   go in sequence — never split a hard prerequisite from its dependent into
   "parallel" chunks. A chunk may contain a short dependency chain if it is small
   enough for one session.
2. **Domain cohesion**: issues touching the same plugin/subsystem cluster together
   (shared files, shared review surface) — co-editing them in one session avoids
   repeated context reload.

For each chunk produce:
- `title` — what the chunk accomplishes (work-type + deliverable visible).
- `issues[]` — the GitHub issue numbers it closes.
- `depends_on[]` — other chunks (by their goal_id, assigned in BIND) that must
  land first. **Namespace discipline (goal-doc-spec §1.4)**: `depends_on` is the
  `goal_id` space, `issues` is the GitHub-number space — keep them distinct.
- `parallelizable` — true when the chunk shares no unfinished prerequisite with
  another proposed chunk (so two sessions could run them concurrently).
- `work_type` — `feature-full` | `decision-only` | `doc-only` (goal-doc-spec
  §1.2; bug-light issues that need no goal-doc are flagged separately, §4.4 — they
  route to debug directly, no slice).
- `domain`, `recommended_model` (complexity-based: haiku/sonnet/opus).

**Present the chunking to the user (read-only) and let them adjust** before any
binding or epic action. Chunking is a proposal, not a decision.

---

## Phase 3 — EPIC (candidates, user-confirmed — silent forbidden)

1. **Identify epic candidates**: a set of chunks that share a parent goal and
   would benefit from a tracking epic (or an existing open epic they belong under).
   Reuse `Parent Epic:` / milestone signals from COLLECT — do NOT invent epics for
   one-off chunks.
2. **Propose, never auto-apply** (AskUserQuestion, Korean): for each candidate,
   show the chunks it would group + whether it is a *new* epic or a link under an
   *existing* one. Let the user pick: create / link / skip (multi-select). This is
   the #125 §2 confirm-gate — **silent epic registration is forbidden**.
3. **Apply only what the user confirmed**, via `gh` (issue creation / edit is
   outward-facing, so confirm first):
   ```bash
   # new epic (only if confirmed):
   gh issue create --title "<epic title>" --body "<chunk list + rationale>" --label epic
   # link an issue under an epic (only if confirmed) — a comment/reference, not a force:
   gh issue comment <epic#> --body "Sub-issue: #<n> (handoff-plan chunk: <title>)"
   ```
   Never edit issue state or labels that the user did not confirm. Report exactly
   what was created/linked. **The comment-based link is advisory-only by design** —
   a human-readable reference (matching #125's "candidate, not auto-apply" posture),
   NOT a machine-traversable parent↔child relationship. The emitted goal-doc also
   does not record the epic in frontmatter: `goal-doc-spec.md` defines no `epic:`
   field, so BIND stays spec-faithful and omits it. Epic membership therefore lives
   in `gh` (epic body + this reference comment), not in the goal-doc.

---

## Phase 4 — BIND (chunk → goal-doc slice binding, goal-doc-spec compliant)

Turn each confirmed chunk into a goal-doc that conforms to
[`docs/design/goal-doc-spec.md`](../../../docs/design/goal-doc-spec.md). This is
the deliverable's core — the binding the next-session `/goal` reads.

**Frontmatter** (spec §1.1 core 8 + §1.2 `work_type`, all required):
```yaml
goal_id: G<N>            # next free G-number (scan docs/plans/goal-docs/)
title: <chunk title>
issues: [<github numbers>]
wave: <ordinal or 독립/게이트 label>   # human schedule label, not a routing key (§1.5)
depends_on: [<goal_id…>]              # goal_id namespace, NOT issue numbers (§1.4)
recommended_model: haiku|sonnet|opus
status: ready                        # gated only for linchpin/high-risk chunks
work_type: feature-full|decision-only|doc-only
created: <today, YYYY-MM-DD>
```

**Body 5 sections in fixed order** (spec §2, all required):
1. **배경 / 목적** — why this chunk, cohesion rationale for the bundled issues.
2. **완료 조건 (Definition of Done)** — issue Acceptance as 1:1 checkboxes.
3. **쟁점과 트레이드오프** — options/recommendation; conditional-branch verdicts
   are recorded here (spec §3.4).
4. **슬라이스 순서** — each slice in spec §3.1 form:
   `N. **<name>** → 바인딩: <binding-expr> | 대상 파일: <path> | 산출: <…> | 검증: <…>`.
   Use the §3.6 default binding for the chunk's `work_type`:
   - `feature-full` → spec=`spec-first` → impl=`executor|native(#133)` →
     critique=`adversarial-review|code-reviewer(#133)` (**each a separate skill**,
     CON-3).
   - `decision-only` → `expert-panel | adversarial-review` (no implementation).
   - `doc-only` → `doc-concretize | doc-polish | spec-first`.
   Sequence `→` means output→input chaining (§3.5), not just ordering.
5. **E2E 자가검증** — a runnable bash block + pass criteria, 1:1 with the DoD.

**Constraints / safeguards** section (reference only, never redefine): cite
boundary §5 CON-1/CON-3/CON-5 and the #125 confirm gate, exactly as the existing
goal-docs do.

---

## Phase 5 — OUTPUT (deliver, user-confirmed file write)

Default: **render the goal-doc(s) in chat** so the user can read them. Then offer
to persist (AskUserQuestion, Korean):

| Option | Action |
|--------|--------|
| **채팅에만** (default) | Show the goal-doc(s) inline; write nothing. The user can copy or ask to save later. |
| **파일 저장** | `Write` each goal-doc to `docs/plans/goal-docs/G<N>-<slug>.md` (repo artifact — NOT vault). Confirmed only. |

- When saving, scan `docs/plans/goal-docs/` first so `G<N>` is the next free number
  and no existing file is overwritten (new-file-only, mirrors the vault new-file
  ethos even though goal-docs are repo files).
- Always print the next-session entry line so the loop continues:
  `다음 세션에서 \`/goal\`로 이어가세요: G<N> — <title>` (one per emitted goal-doc).
- If multiple chunks were bound, list them with their `parallelizable` flag so the
  user sees which can run concurrently next session.

---

## Configuration

| Env var | Default | Effect |
|---------|---------|--------|
| `HANDOFF_ISSUE_LIMIT` | `200` | max open issues fetched in COLLECT |
| `VAULT_BRIDGE_VAULT_ROOT` / `VAULT_BRIDGE_VAULT_PATH` | `~/vault` | only used to *confirm* the skill never writes there (it does not) |

## Rules

- Silent epic creation / issue linking / issue mutation is FORBIDDEN — all are
  user-confirmed via `gh` (#125 §2 safeguard).
- NO vault write, ever. The only file write is a user-confirmed goal-doc under
  `docs/plans/goal-docs/` (repo artifact, new-file-only).
- Emitted goal-docs MUST conform to `goal-doc-spec.md` (frontmatter §1, body 5
  sections §2, slice binding §3) so the next session's `/goal` parses them.
- A `feature-full` chunk's critique slice binds to a separate reviewer skill
  (CON-3 self-approval ban carried into the recipe).
- CON-5: read external/leaf artifacts and `gh` only; never modify leaf-plugin
  code; no reverse dependency. Delegate issue I/O to `gh` and execution to native
  `/goal` — the harness adds only the chunking + binding layer.
- Never split a hard dependency into "parallel" chunks; `depends_on` (goal_id)
  and `issues` (GitHub numbers) are distinct namespaces (goal-doc-spec §1.4).
