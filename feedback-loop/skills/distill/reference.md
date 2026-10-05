# distill — reference

Background moved out of `SKILL.md` (#750) so the skill body fits Codex's 8,000-byte invoked-skill
limit. Everything below is the **pre-trim wording, verbatim**: rationale, history and boundary
discussion. The runnable procedure, every gate and the proposal contract stay in `SKILL.md`; if the
two disagree, `SKILL.md` wins.

## distill — retrospective discovery of procedural techniques (layer ⑤)

`distill` closes a different half of the measure→improve loop than `retro`: where
`retro` acts on what the leaf layers measured (telemetry waste),
`distill` looks at **this session's procedure** and asks "is there a *class-level
reusable technique* here worth keeping?" It is the **retrospective discovery
layer** that the now-removed OMC `learner`/`skillify` used to occupy. It ports the
*prompt assets* (not code) of
[claude-self-improving-skills](https://github.com/UniM0cha/claude-self-improving-skills)
(SIS, Hermes Agent).

### Discovery ↔ landfill boundary (DISCOVER-LANDFILL-BOUNDARY)

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

### MECE boundaries (do not blur — print boundary ① to the user once)

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

### No new hook surface

`distill` adds **zero hooks** (harness hook surface stays flat — CON-2). All
validation is an in-skill self-check, never a registered hook.

### retro connection (historical — removed in #639)

Before #639, `retro`'s rule branch surfaced a `/distill` invocation the same way its
now-removed memory branch surfaced `/vault-save` — a ready-to-run slash command for the
USER to invoke, never inline. That branch was a pure pass-through: a pattern only `retro`
observed had been judged worth keeping by nobody, and `distill` is the skill that makes
that judgment, so removing the branch lost no capability. `distill` is its own
user-initiated skill and does its own worth-keeping judgment regardless of who noticed
the pattern; `retro` no longer runs or embeds this procedure at all.

### Scope rationale (thin-gate)

`distill` sits OUTSIDE the ⑤-harness two-gap list of #132 (slice→skill routing
+ invariant enforcement; that harness was itself withdrawn in #282/#283, so the
gap list survives only as the admission argument here). It is admitted not as ⑤
orchestration but as a **measure→improve family extension** — the same family and
home as `retro` (#123 precedent), which is why it ships in `feedback-loop`. Deferred
companions (recorded in #202, not built): a retro **curation phase** (stale/archive
of unused distilled skills, symmetric to PROMOTE — blocked on cross-project
visibility, since telemetry Option A cannot see out-of-repo use) and a Stop-hook
distill nudge.
