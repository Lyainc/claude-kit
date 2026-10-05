---
name: distill
description: "Discover user-confirmed reusable procedural techniques from this session and emit a proposal; it neither writes nor places the policy. Trigger: 증류, 증류해줘, 이 기법 남길까, 재사용 기법 추출, distill, distill this technique, is this technique worth keeping, /distill. Routing: use vault-save for facts and add-policy to land a confirmed rule."
model: inherit
allowed-tools: Read Bash Grep AskUserQuestion
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion prompts,
confirmations, reports) MUST be in Korean. Instructions below are English for LLM parsing.

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first. Use Phases 1–3 below, with these replacements: the already-landed duplicate check reads
the current conversation, native user/project AGENTS.md, and relevant installed skills,
never `~/.claude`; follow only the chosen catalogue's detail links, without a recursive sweep; confirmation
is a normal user turn. For every confirmed proposal, continue with `add-policy`'s Codex storage
branch in the current context, preserving the complete proposal object and its inviolability
judgment. `add-policy` owns a separate one-click confirmation before any write. Do not read
Claude settings or emit a Claude slash-command handoff. Claude Code ignores this section.

# distill — retrospective discovery of procedural techniques

Asks of **this session's procedure**: is there a *class-level reusable technique* worth keeping?
Origin (SIS port), MECE boundaries ①/②, retro history and scope rationale: [reference.md](reference.md).

- **Procedural only.** Declarative knowledge (what we decided, what happened) is not distill's: route
  it to `/vault-save` and stop. Print this boundary to the user once.
- **Discovery only.** distill emits a proposal; it never places, authors or writes (no Write/Edit
  tools), adds zero hooks (CON-2), and leaves no working-tree changes. Landing (classification,
  necessity gate, authoring) is the sibling `add-policy`'s, which may delegate a non-trivial
  new-skill body to `skill-creator`.

**Proposal object** (natural language): **what** (the technique in one line), **why** (what is
lost if not captured), **session provenance** (the session pattern it was observed in),
**inviolability judgment** (if it patches an existing skill X, is X user-authored, hence
inviolable? `add-policy` enforces the block; distill only supplies the judgment). Do NOT fill the
classification grid (layer/scope/tier/channel) or name the placement action
(patch/extend/reference/new): those are `add-policy`'s.

## Pipeline: SCAN → PROPOSE → GATE → HANDOFF

### Phase 1 — SCAN (anti-capture filter)

Look back for **reusable procedural anchors**: a multi-step procedure that worked and would
plausibly recur (a debugging route, a build/verify sequence, a refactor recipe, a research
sweep). DROP a candidate that is:

- **one-off narrative**: specific to this task, not a repeatable method;
- **environment-dependent workaround**: tied to this machine/repo state, won't transfer;
- **negative tool claim**: "tool X doesn't work / isn't available" (a transient fact);
- **seen once**: the **recurrence floor** is two or more separated points in the conversation;
  twice inside one turn counts as one. A single sighting is an *instance*, not a *class*, and a
  class-level claim is what this skill makes. A valuable one-off is not lost: the user can state it
  outright, and a stated rule goes straight to `add-policy`'s explicit path;
- **default behavior**: a competent agent would do it anyway; a rule that changes no behavior costs
  context and buys nothing;
- **already landed**: it already lives in a loaded reminder, an existing skill, a reference doc or
  the vault. Do not assert this from memory: check with the read-only `Bash`/`Grep` this skill
  holds, over a **fixed** target list: `~/.claude/rules/README.md`, the detail directory that index
  links to, `~/.claude/CLAUDE.md`, and the project CLAUDE.md. No recursive sweep. This is the only
  place a pre-landing duplicate is caught: `add-policy`'s §6 conflict check scans only the ONE
  site it already chose.

"Capturing nothing is a normal, valid outcome." If every candidate is filtered out, report ONE
Korean line with the reason and STOP; do not manufacture a skill to have something to show.

### Phase 2 — PROPOSE (read-only)

For each survivor, build the proposal object, with two judgments:

- **Inviolability**: if the technique plausibly refines an existing skill, `Read` its frontmatter
  and judge whether it is user-authored. Advisory: flag the risk; do not select the target.
- **Audience / placement fit**: would the intended audience actually read the technique where it
  is likely to land? A rule whose reader never sees it is a wasted capture. Inspect the candidate
  target read-only with `Bash`/`Grep` (e.g. a target skill's provenance, or that a location is
  one the harness loads).

### Phase 3 — GATE (user-confirmed, silent distillation forbidden)

AskUserQuestion (Korean), multi-select: per candidate show the technique, why it is worth keeping,
a proposed `name` (a **proposal label**, class-level, naming the situation/capability, e.g.
`flaky-test-triage`; `add-policy` holds final naming authority and may rename it) and a
situation-first one-line `description`. The single question is the **discovery gate**: "shall we
hand this proposal to the landfill engine?" The user picks which to forward, or skips all.
Placement (site, patch vs new) is NOT asked here; that is `add-policy`'s 1-click gate. Never
forward without explicit confirmation.

### Phase 4 — HANDOFF (confirmed only)

For each confirmed proposal, surface the proposal object as a ready-to-run `/add-policy`
invocation for the user; never run it inline. distill's responsibility ends there.

**Inviolability is non-negotiable**: "user-authored skills are inviolable / never overwrite" must
survive the handoff: distill supplies the judgment, `add-policy` the mechanism.

## Rules

- Procedural technique ONLY; declarative knowledge goes to `/vault-save`.
- The recurrence floor is a DROP condition, not a preference: seen at fewer than two separated
  points in the conversation → drop it. One sighting is an instance, not a class.
- Discovery only: emit a proposal, never write; placement and authoring are `add-policy`'s.
- User-confirmed always; silent distillation is FORBIDDEN. Capturing nothing is valid.
- The proposal carries the inviolability judgment; the engine enforces the block.
- Zero hooks; validation is the in-skill discovery-face self-check.
