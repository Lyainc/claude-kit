---
name: distill
description: "User-confirmed distillation of REUSABLE PROCEDURAL TECHNIQUES from the current session into a personal skill (~/.claude/skills/<name>/SKILL.md). Judges what is class-level reusable, whether an existing skill should be patched instead, or whether nothing is worth capturing — then authors only on explicit confirmation. SIS-derived (claude-self-improving-skills). Trigger: 증류, 증류해줘, 이 기법 스킬로, 재사용 기법 추출, distill, distill this technique, extract a skill, /distill. Routing: declarative knowledge (facts/decisions/session records) = vault /capture or /note, NOT distill; mechanical skill authoring after you've decided = skill-creator; this skill is the RETROSPECTIVE JUDGMENT layer that decides whether/what to distill. Example: '/distill' or '이 세션 기법 증류해줘'."
model: inherit
allowed-tools: Read Write Edit Bash Glob Grep AskUserQuestion
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion prompts, confirmation messages, reports) MUST be in Korean. Instructions below are English for LLM parsing.

# distill — retrospective distillation of procedural techniques (layer ⑤)

`distill` closes a different half of the measure→improve loop than `retro`: where
`retro` acts on what the leaf layers measured (audit E8, telemetry waste),
`distill` looks at **this session's procedure** and asks "is there a *class-level
reusable technique* here worth keeping as a skill?" It is the **retrospective
judgment layer** that the now-removed OMC `learner`/`skillify` used to occupy. It
ports the *prompt assets* (not code) of
[claude-self-improving-skills](https://github.com/UniM0cha/claude-self-improving-skills)
(SIS, Hermes Agent).

## Discovery ↔ landfill boundary (DISCOVER-LANDFILL-BOUNDARY)

distill is the **DISCOVERY half** of the recursive-improvement loop (#251): it judges
*what* is a class-level reusable technique and emits a **natural-language proposal**
(what / why / session-provenance / inviolability judgment — see §"output contract"
below). Deciding *where and how* to embed — placement classification
(patch>extend>reference>new) and authoring — is the **landfill responsibility** of
the general engine (G19, add-policy lineage), NOT distill **in the target state**
(the transition caveat is below). The proposal is the engine's input interface.

**Output contract** (C2 — format is G19-deferred; content is specified now):

A distill proposal is a natural-language object carrying:
- **what**: the reusable procedural technique in one line — the rule/technique content.
- **why**: what is lost if not captured — the reuse value. (Mirrors add-policy §5
  entry template What/Why.)
- **session provenance**: which session pattern this was repeatedly observed in.
- **inviolability judgment** (C4): if the proposal patches an existing skill X, is X
  user-authored (inviolable)? This judgment is **discovery's responsibility** — the
  proposal carries it so the landfill engine never overwrites what it must not.

distill does NOT fill the **classification grid** — the four slots
layer/scope/tier/channel, the embedding engine's *placement schema* (add-policy §1/§2;
lineage-only, CON-5 self-contained). This holds even during the transition: unlike the
patch>extend>new placement-action choice (Phase 2, provisionally retained), the grid is
never distill's to fill — pre-filling it would usurp landfill responsibility (C5).

During the transition (G19 not yet built) distill provisionally retains the
placement-action choice (Phase 2/3) and WRITE (Phase 4) behind the sealed markers in
those phases, so discovery stays non-regressing until the landfill engine absorbs them.
This is a *managed* transition, not the terminus — those blocks are named G19 removal
targets (C6).

## MECE boundaries (do not blur — print boundary ① to the user once)

- **Boundary ① — procedural only.** `distill` captures *reusable procedural
  technique* (a how-to that recurs across tasks). **Declarative knowledge** — facts,
  decisions, session records — is NOT distill's domain; it belongs in the vault via
  `/capture` (raw) or `/note` (evergreen). If the candidate is "what we decided" or
  "what happened", route it to the vault and stop. (Co-evolution note #215: the
  vault side of this line — `/capture`·`/note` wording — tracks the ④ vault
  redesign; the *procedural-technique* side of the boundary is stable.)
- **Boundary ② — vs `skill-creator`.** `distill` is the **retrospective judgment**
  ("is this worth a skill, and which existing skill should absorb it instead?").
  `skill-creator` is the **intentional authoring tool** (mechanical creation +
  evals *after* you've decided to build). They are complementary: once `distill`
  decides a NEW skill is warranted and the body is non-trivial, it MAY hand the
  mechanical authoring to `skill-creator`. `distill` never duplicates
  skill-creator's eval/optimization machinery.

## No new hook surface

`distill` adds **zero hooks** (harness hook surface stays flat — CON-2). All
validation is an in-skill self-check (Phase 5), never a registered hook.

## Pipeline: SCAN → PRIORITIZE → GATE → WRITE → SELF-CHECK

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
- **already documented** — the procedure already lives in an existing skill,
  CLAUDE.md, a reference doc, or the vault.

**"Capturing nothing is a normal, valid outcome."** If every candidate is
filtered out, report ONE Korean line with the reason and STOP — do not
manufacture a skill to have something to show.

### Phase 2 — PRIORITIZE (suppress skill proliferation)

> **Boundary note**: placement decision (patch>extend>reference>new) is **landfill
> responsibility** (G19, add-policy §3 placement rules); provisionally retained here
> during transition. This block is a G19 named removal target (C6, T2).

For each surviving candidate, choose the **least-proliferating** action, in this
strict order (scan `~/.claude/skills/*/SKILL.md` first to know what exists):

1. **Patch** an existing skill — the technique refines a skill that already covers
   this area. Prefer editing its body over creating a sibling.
2. **Extend an umbrella skill** — fold it into a broader existing skill as a new
   section rather than a standalone.
3. **Add a reference** — append a pointer/example to an existing skill's reference
   material.
4. **Create new** — ONLY when 1–3 genuinely do not fit. A new skill is the last
   resort, not the default.

### Phase 3 — GATE (user-confirmed, silent forbidden)

> **Boundary split** (C5): "shall we proceed with this proposal at all?" is the
> **discovery gate** (distill's responsibility, retained here). "Which action
> (patch/extend/new) and which target?" is the **landfill decision gate** (G19
> 1-click gate); provisionally presented together during transition. The two faces
> are co-resident here until the landfill engine exists.

Present each candidate via AskUserQuestion (Korean): the technique, the chosen
action (patch/extend/reference/new + target skill), the proposed `name`
(class-level — name the *situation/capability*, e.g. `flaky-test-triage`, not
`fix-the-thing-from-today`), and a situation-first one-line `description`. The user
picks which to apply (multi-select) or skips all. **Never write without explicit
confirmation.** Distilling is opt-in exactly like `retro`'s memory/rule branches.

### Phase 4 — WRITE (confirmed only)

> **PROVISIONAL (transition)**: WRITE is **landfill responsibility** (actual
> authoring = placement + Edit/Write). G19 removes this phase once the landfill
> engine absorbs authoring. Until then it is retained so discovery stays
> non-regressing. **This block is a named G19 removal target (C6).**

For each confirmed candidate:

- **Patch/extend/reference** → `Edit` the existing skill (frontmatter or body as
  scoped above).
- **New** → `Write` `~/.claude/skills/<name>/SKILL.md` with:
  - `name` (kebab-case, class-level), situation-first `description` (when to reach
    for it, with trigger phrasing), `allowed-tools`.
  - **`metadata.provenance: distilled`** — the marker that this skill was
    machine-distilled. **User-authored skills are inviolable**: if a target skill's
    frontmatter carries `provenance: user-authored` (or no provenance marker that
    you did not write), NEVER overwrite its body — propose a sibling or a reference
    instead. (SIS `created_by` tiering: distilled skills may be revised by distill;
    user-authored ones may not.)
  - For a non-trivial body, you MAY delegate the mechanical authoring to
    `skill-creator` (Boundary ②) — but the provenance marker and the distill
    judgment stay here.

> **Inviolability judgment (C4 — discovery responsibility)**: before writing,
> distill must determine whether the target skill is user-authored (inviolable). This
> *judgment* ("is X inviolable?") is the discovery half's responsibility and is
> carried in the proposal object. Only the mechanical provenance marker write is
> landfill work. The safety invariant — "user-authored skills are inviolable / never
> overwrite" — is non-negotiable and must not be lost when G19 absorbs authoring.

### Phase 5 — SELF-CHECK (in-skill, no hook)

> **Boundary split** (C3): two distinct faces with different owners.
>
> - **Artifact verification** ("frontmatter parses, name is kebab, body non-empty") —
>   **landfill face**: these checks validate the *written artifact* produced by Phase 4
>   (landfill work) and follow as a landfill sub-step. They stay here provisionally
>   during transition but are a named G19 removal target.
> - **Placement verification** ("is this the place that actually gets read?") —
>   **discovery face** (retained here permanently): did the write land in a location
>   that the harness actually loads? This is the seed of SUMMARY §5(c)
>   post-embedding verification. It stays in distill because it is a *judgment* about
>   whether the discovery reached its audience — not a mechanical artifact check.

After each write, verify deterministically (report failures in Korean, do not
leave a malformed skill):

**Artifact checks (landfill face — provisional, G19 removal target):**
- frontmatter parses and carries `name`, `description`, `allowed-tools`;
- `name` is kebab-case and matches the directory name;
- body is non-empty (more than the frontmatter);
- `metadata.provenance` is present on a newly created skill.

**Placement check (discovery face — retained):**
- the written path (`~/.claude/skills/<name>/SKILL.md`) is within a directory that
  Claude Code actually loads skills from; warn in Korean if the path looks wrong.

```bash
# Example self-check for a freshly written skill (best-effort, Korean report on fail):
SKILL_PATH="$HOME/.claude/skills/<name>/SKILL.md"
[ -s "$SKILL_PATH" ] && grep -q '^name:' "$SKILL_PATH" && grep -q '^description:' "$SKILL_PATH" \
  && grep -q 'provenance:' "$SKILL_PATH" && echo "self-check OK" || echo "self-check FAILED"
```

## retro connection (propose-only, NOT a 4th inline branch)

`retro` may **surface** a `/distill` suggestion the same way it surfaces the memory
branch's `/capture` — as a ready-to-run slash command for the USER to invoke, never
inline. `distill` is its own user-initiated skill; `retro` does not run it and does
not embed this procedure. (This keeps retro's 3-branch output unchanged; distill is
a sibling, not a fourth always-on branch.)

## Scope rationale (thin-gate)

`distill` sits OUTSIDE the `omc-to-native-substrate.md` §4 two-gap list
(slice→skill routing + invariant enforcement). It is admitted not as ⑤
orchestration but as a **measure→improve family extension** — the same family and
home as `retro` (#123 precedent), which is why it ships in `feedback-loop`. Deferred
companions (recorded in #202, not built): a retro **curation phase** (stale/archive
of unused distilled skills, symmetric to PROMOTE — blocked on cross-project
visibility, since telemetry Option A cannot see out-of-repo use) and a Stop-hook
distill nudge.

## Rules

- Procedural technique ONLY; declarative knowledge → vault (`/capture`·`/note`).
- Suppress proliferation: patch > extend > reference > new (new is last resort).
- User-confirmed always; silent distillation is FORBIDDEN. Capturing nothing is valid.
- `provenance: distilled` on created skills; user-authored skills are inviolable.
- Zero hooks; validation is the in-skill Phase-5 self-check.
- Mechanical authoring may delegate to `skill-creator`; the judgment stays here.
