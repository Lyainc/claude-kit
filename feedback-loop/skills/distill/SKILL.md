---
name: distill
description: "User-confirmed DISCOVERY of REUSABLE PROCEDURAL TECHNIQUES in the current session — the discovery half of the ⑤ self-improvement loop. Judges what is class-level reusable (vs a one-off), whether an existing skill already covers it, or whether nothing is worth capturing, and emits a natural-language proposal (what / why / session-provenance / inviolability judgment); placement and authoring are the sibling add-policy landfill engine's job, not distill's. SIS-derived (claude-self-improving-skills). Trigger: 증류, 증류해줘, 이 기법 남길까, 재사용 기법 추출, distill, distill this technique, is this technique worth keeping, /distill. Routing: declarative knowledge (facts/decisions/session records) = vault /vault-save, NOT distill; placing/authoring a confirmed rule = add-policy (sibling); mechanical skill authoring = skill-creator. Example: '/distill' or '이 세션 기법 증류해줘'."
model: inherit
allowed-tools: Read Bash Grep AskUserQuestion
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion prompts, confirmation messages, reports) MUST be in Korean. Instructions below are English for LLM parsing.

# distill — retrospective discovery of procedural techniques (layer ⑤)

`distill` closes a different half of the measure→improve loop than `retro`: where
`retro` acts on what the leaf layers measured (telemetry waste),
`distill` looks at **this session's procedure** and asks "is there a *class-level
reusable technique* here worth keeping?" It is the **retrospective discovery
layer** that the now-removed OMC `learner`/`skillify` used to occupy. It ports the
*prompt assets* (not code) of
[claude-self-improving-skills](https://github.com/UniM0cha/claude-self-improving-skills)
(SIS, Hermes Agent).

## Discovery ↔ landfill boundary (DISCOVER-LANDFILL-BOUNDARY)

distill is the **DISCOVERY half** of the recursive-improvement loop (#251): it judges
*what* is a class-level reusable technique and emits a **natural-language proposal**
(what / why / session-provenance / inviolability judgment — see the output contract
below). Deciding *where and how* to embed — placement classification
(patch>extend>reference>new) and the actual authoring — is the **landfill
responsibility** of the sibling engine `add-policy` (G19, now built). distill stops at
the proposal; it does not place, and it does not write. The proposal is the engine's
input interface.

**Output contract** — a distill proposal is a natural-language object carrying:

- **what**: the reusable procedural technique in one line — the rule/technique content.
- **why**: what is lost if not captured — the reuse value.
- **session provenance**: which session pattern this was repeatedly observed in.
- **inviolability judgment**: if the proposal patches an existing skill X, is X
  user-authored (inviolable)? This judgment is **discovery's responsibility** — the
  proposal carries it so the landfill engine never overwrites what it must not. The
  *mechanism* that enforces the block lives in `add-policy`; distill only supplies the
  *judgment*.

distill does NOT fill the **classification grid** — the four slots
layer/scope/tier/channel are the embedding engine's *placement schema* (`add-policy`).
Pre-filling them would usurp landfill responsibility: tier in particular is the engine's
to infer from the rule's what/why, and the placement action (patch/extend/new) is the
engine's 1-click gate. distill names neither.

## MECE boundaries (do not blur — print boundary ① to the user once)

- **Boundary ① — procedural only.** `distill` captures *reusable procedural
  technique* (a how-to that recurs across tasks). **Declarative knowledge** — facts,
  decisions, session records — is NOT distill's domain; it belongs in the vault via
  `/vault-save`. If the candidate is "what we decided" or
  "what happened", route it to the vault and stop. (Co-evolution note #215: the
  vault side of this line — `/vault-save` wording — tracks the ④ vault
  redesign; the *procedural-technique* side of the boundary is stable.)
- **Boundary ② — discovery vs landfill vs authoring.** `distill` is the
  **retrospective discovery judgment** ("is this worth keeping?"). `add-policy` (sibling)
  is the **landfill engine** that classifies and places a confirmed proposal.
  `skill-creator` is the **intentional authoring tool** (mechanical creation + evals).
  The flow is discovery → landfill → (optional) mechanical authoring: distill hands a
  confirmed proposal to `add-policy`, which decides placement and may itself delegate a
  non-trivial new-skill body to `skill-creator`. distill never places, authors, or
  duplicates skill-creator's eval/optimization machinery.

## No new hook surface

`distill` adds **zero hooks** (harness hook surface stays flat — CON-2). All
validation is an in-skill self-check, never a registered hook.

## Pipeline: SCAN → PROPOSE → GATE → HANDOFF

### Phase 1 — SCAN (identify candidates, anti-capture filter)

Look back over the session for **reusable procedural anchors**: a multi-step
procedure that worked and would plausibly recur (a debugging route, a
build/verify sequence, a refactor recipe, a research sweep). For each candidate,
apply the **anti-capture filter** — DROP it if it is any of:

- **one-off narrative** — a story specific to this task, not a repeatable method;
- **environment-dependent workaround** — a hack tied to this machine/repo state
  that won't transfer;
- **negative tool claim** — "tool X doesn't work / isn't available" (a transient
  fact, not a technique);
- **seen once** — the **recurrence floor**: the correction or procedure must be observed
  at **two or more separated points in the conversation**. Twice inside one turn counts as
  one. A single sighting is an *instance*, not a *class*, and a class-level claim is what
  this skill exists to make. A genuinely valuable one-off is not lost: the user can state it
  outright, and a stated rule goes straight to `add-policy`'s explicit path;
- **default behavior** — a competent agent would do it anyway without the rule. A rule that
  changes no behavior costs context and buys nothing;
- **already landed** — the procedure already lives in a loaded reminder, an existing skill,
  a reference doc, or the vault. Do not assert this from memory; **check with the read-only
  `Bash`/`Grep` this skill already holds**, over a **fixed** target list — `~/.claude/rules/README.md`,
  the detail directory that index links to, `~/.claude/CLAUDE.md`, and the project CLAUDE.md.
  No recursive sweep. This is the only place a *pre-landing* duplicate is caught:
  `add-policy`'s §6 conflict check runs only against the ONE site it has already chosen.

**"Capturing nothing is a normal, valid outcome."** If every candidate is
filtered out, report ONE Korean line with the reason and STOP — do not
manufacture a skill to have something to show.

### Phase 2 — PROPOSE (build the proposal object — discovery face)

For each surviving candidate, construct the natural-language proposal object (what /
why / session-provenance / inviolability judgment). Two discovery judgments are made
here with **read-only** tools — distill never writes:

- **Inviolability judgment**: if the technique plausibly refines an existing skill, use `Read`
  on that skill's frontmatter and judge whether it is user-authored (inviolable). Carry the
  judgment in the proposal; `add-policy` enforces the block. This is advisory — distill
  flags the risk, it does not *select* the placement target (that is `add-policy`'s).
- **Audience / placement-fit check (discovery seed)**: judge whether the technique's
  intended audience would actually read it where it is likely to land — the seed of
  post-embedding placement verification. A rule whose reader never sees it is a wasted
  capture. This is a *judgment* (does discovery reach its audience?), not a mechanical
  artifact check; the engine does the artifact verification after it writes. Use
  `Bash`/`Grep` read-only to inspect the candidate target (e.g. confirm a target skill's
  provenance, or that a target location is one the harness loads).

distill does NOT choose the placement action (patch/extend/reference/new) and does NOT
name the classification grid — those are `add-policy`'s.

### Phase 3 — GATE (user-confirmed, silent forbidden)

Present each candidate via AskUserQuestion (Korean): the technique, *why* it is worth
keeping, the proposed `name` (a **proposal label**, not a placement commitment — class-level,
naming the *situation/capability*, e.g. `flaky-test-triage`, not `fix-the-thing-from-today`), and a
situation-first one-line `description`. The `name` is only a proposal. `add-policy` holds final
naming authority and MAY rename it at placement time. The single question is the **discovery gate**: "shall we hand this
proposal to the landfill engine?" The user picks which proposals to forward
(multi-select) or skips all. **The placement decision (which site / patch vs new) is NOT
asked here — that is `add-policy`'s 1-click gate.** Distilling is opt-in exactly like
`retro`'s memory/rule branches; never forward without explicit confirmation.

### Phase 4 — HANDOFF (confirmed only)

For each confirmed proposal, hand the natural-language proposal object to the
`add-policy` landfill engine (surface it as a ready-to-run `/add-policy` invocation for
the user, the same propose-only way `retro` surfaces `/vault-save` — never run it inline).
`add-policy` classifies, conflict-checks, places, and authors; it enforces the
inviolability block the proposal carries. distill's responsibility ends at the confirmed
proposal — it leaves no working-tree changes of its own.

> **Inviolability is non-negotiable**: the safety invariant — "user-authored skills are
> inviolable / never overwrite" — must survive the handoff. distill supplies the
> judgment; `add-policy` implements the mechanism. Neither side may drop it.

## retro connection (propose-only, NOT a 4th inline branch)

`retro`'s **rule branch surfaces `/distill`** (#459) the same way its memory branch
surfaces `/vault-save` — a ready-to-run slash command for the USER to invoke, never
inline. It points here rather than at `add-policy` because a pattern only `retro`
observed has been judged worth keeping by nobody, and `add-policy` deliberately never
makes that judgment. `distill` is its own user-initiated skill; `retro` does not run
it and does not embed this procedure. (retro's output stays 3 branches; distill is
the rule branch's destination, not a fourth always-on branch.)

## Scope rationale (thin-gate)

`distill` sits OUTSIDE the ⑤-harness two-gap list of #132 (slice→skill routing
+ invariant enforcement; that harness was itself withdrawn in #282/#283, so the
gap list survives only as the admission argument here). It is admitted not as ⑤
orchestration but as a **measure→improve family extension** — the same family and
home as `retro` (#123 precedent), which is why it ships in `feedback-loop`. Deferred
companions (recorded in #202, not built): a retro **curation phase** (stale/archive
of unused distilled skills, symmetric to PROMOTE — blocked on cross-project
visibility, since telemetry Option A cannot see out-of-repo use) and a Stop-hook
distill nudge.

## Rules

- Procedural technique ONLY; declarative knowledge → vault (`/vault-save`).
- The recurrence floor is a DROP condition, not a preference: seen at fewer than two
  separated points in the conversation → drop it. One sighting is an instance, not a class.
- Discovery only: distill judges *what* is worth keeping and emits a proposal; placement
  and authoring are `add-policy`'s. distill never writes (no Write/Edit tools).
- User-confirmed always; silent distillation is FORBIDDEN. Capturing nothing is valid.
- The proposal carries the inviolability judgment; user-authored skills are inviolable
  (the engine enforces the block — the invariant must survive the handoff).
- Zero hooks; validation is the in-skill discovery-face self-check.
- Mechanical authoring is `add-policy`'s call (it may delegate to `skill-creator`); the
  discovery judgment stays here.
