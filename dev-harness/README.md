# dev-harness

claude-kit's **layer ⑤ (execution / doing) development-governance harness** — a
lightweight orchestration layer built **on top of Claude Code native primitives**
(`/goal`, dynamic Workflow, agents, hooks).

> **Dev-only — NOT a marketplace plugin.** `dev-harness` governs claude-kit's *own*
> development loop (goal-doc routing/validation, constitutional invariant
> enforcement, backlog→goal-doc handoff). It is **not registered in
> `marketplace.json`** and is never installed by external users. The
> **installer-facing** self-improvement loop (measure→review→keep: `retro` +
> telemetry) was split out to the **`feedback-loop`** plugin by
> [#217](https://github.com/Lyainc/claude-kit/issues/217); this directory keeps the
> dev-governance half.
>
> A `.claude-plugin/plugin.json` ships here only so contributors can optionally
> `/skill` auto-load these skills during local dev. CI tests run the scripts by
> plain path — no `--plugin-dir` is required.

## What it ships

- **`slice-router`** ([#183](https://github.com/Lyainc/claude-kit/issues/183)) — the
  #122-residual **4-way slice router + D5 invariant enforcement**: takes an existing
  goal-doc, validates it (INV-4), and binds its `work_type` to a slice sequence,
  enforcing the constitutional invariants native cannot.
- **`handoff-plan`** ([#171](https://github.com/Lyainc/claude-kit/issues/171)) —
  chunks the open GitHub backlog (by dependency + domain) into user-confirmed epic
  candidates and goal-doc slice bindings for the next session's `/goal`.
- **`workflows/feature-full.js`** ([#201](https://github.com/Lyainc/claude-kit/issues/201))
  — the feature-full DELEGATE carrier that makes CON-3 *structural*: impl and
  critique are separate `agent()` calls, so the authoring context approving its own
  output becomes syntactically impossible.

Capability lands incrementally, route by route — never as a big-bang replacement.

## Dependency direction — ONE-WAY (harness → leaf)

This harness is bound by **CON-5** (the constitutional one-way dependency rule).
The single source of truth is
[`docs/design/claude-kit-boundary.md`](../docs/design/claude-kit-boundary.md) §3 / §5.

```
dev-harness   ─────▶  vault-bridge            (leaf ③ delivery)
 (harness, ⑤)  ─────▶  obsidian-vault-manager  (leaf ②④: E8 / audit input)
              ─────▶  feedback-loop           (⑤ self-improvement: emits rule_fire to its
                                                telemetry schema — a data contract, no code import)
```

- **Allowed:** `dev-harness` invokes leaf-plugin capabilities (calls a slash command,
  reads an audit finding) and *emits* to feedback-loop's telemetry schema. The harness
  is Claude-Code-specific (it depends on native primitives); the leaves stay
  harness-neutral.
- **Forbidden (no reverse, no cycle):** a leaf plugin (①②③④) MUST NOT import, call, or
  assume any harness API or behavior. `dev-harness` and `feedback-loop` are both ⑤;
  the direction stays one-way (`dev-harness → feedback-loop`, never the reverse).
- **rule_fire boundary:** `dev-harness` work-rule checks may *emit* `rule_fire`
  telemetry events, whose schema `feedback-loop` owns (#216 c8). Emitting to a data
  contract is not a code dependency — `dev-harness` never imports `feedback-loop`.

## Portability — zero runtime dependency on local-harness (§0)

This harness is **self-contained**: it carries **zero runtime/build dependency** on the
developer's machine-level policy base (`~/.claude/rules/`, the *local-harness* MVP), so a
public clone builds and runs on any machine. Canonical statement of this boundary:
[`docs/design/claude-kit-boundary.md`](../docs/design/claude-kit-boundary.md)
(claude-kit ↔ local-harness §0); the work-rule-layer form is `rules/RULES.md` §0.

**"Self-contained" ≠ no shared ideas.** claude-kit holds its *own concrete form* of any
policy it needs — the **concretization of a machine-level abstract, not an identical copy and
not a runtime fetch**. The link to the abstract is intellectual lineage (plus the optional
`feedback-loop` nudge bridge), never a code/build dependency (#229, discovery f15).

**Component classification (#229 — policy vs implementation).** Decomposing the three
dev-harness components by the abstract(policy)/concrete(implementation) test:

| Component | Verdict | Destination |
|-----------|---------|-------------|
| `workflows/feature-full.js` (#201) | implementation | **claude-kit self-contained** — Claude-Code-Workflow-specific carrier; it *embodies* the #209 contract via prompt text, it is not that policy |
| `skills/handoff-plan` (#171) | implementation | **claude-kit self-contained** — inseparable from #100 goal-doc-spec + repo paths |
| `skills/slice-router` (#183) | implementation | **claude-kit self-contained** — Gap-ROUTE / Gap-INV bound to the #100 schema + the CON-1..5 constitution |

**No component moves** to local-harness: a move + runtime-consume would breach §0. The single
genuine *abstract* lift is the **subagent git side-effect contract** (#209) — its broad
*what + why* now lives as a machine-level work-rule (`~/.claude/rules/` P3, sibling to P1
worktree-isolation / P2 python→uv), while the concrete enforcement (`rules/RULES.md` §1, the
`feature-full.js` impl prompt, the §4 task-end self-check) stays here, self-contained. That is
the abstract/concrete *decomposition* — distinct altitudes, no identical duplication (f15).

**Deterministic guards stay too (#229 1(a)).** The same verdict covers the repo-build
deterministic guards — they are claude-kit-repo-specific (they validate *this* repo's
manifests, frontmatter, and constitution), so they are **claude-kit self-contained** and are
**not** lifted to local-harness:

| Guard | Lives in | Why it stays |
|-------|----------|--------------|
| `invariant_guard.py` (Gap-INV) | `dev-harness/scripts/` | enforces the CON-1..5 constitution + #100 INV-4 schema — meaningless off this repo |
| `check-version-sync.py` | repo-root `scripts/` | reconciles `plugin.json` ↔ `marketplace.json` (incl. the dev-drift fence) — marketplace governance, repo-only |
| `check-type-optin.py` · `check-language-policy.py` · `check-banned-words.py` | repo-root `scripts/` | enforce this repo's own doc/work-rule conventions (#216 minimal core) |

The table lists the **#229 1(a) set** specifically; the same verdict extends to the repo's
other build-only scripts (`check-ci-coverage.py`, `run-linters.py`, `check-test-exitcode.py`,
the release tooling) — all claude-kit self-contained for the identical reason. These are
repo-build infrastructure, not portable policy: there is nothing to abstract up, because
the *what + why* is "validate claude-kit itself." (Contrast the #209 lift above, whose what+why is
machine-general.) Note the root guards live in repo-root `scripts/`, not under `dev-harness/` — the
slimming verdict is about *destination* (claude-kit, never local-harness), not relocation within the
repo.

## Native-substrate principle (#122)

The harness **delegates to native first** and only adds a thin layer for what native
cannot express:

1. **Slice → skill binding routing** — map a goal-doc slice to the right leaf skill /
   native agent.
2. **Constitutional invariant enforcement** — enforce the invariants native cannot
   guarantee (new-file-only vault writes, isolated critique / no self-approval,
   goal-doc as a stable harness-neutral contract, one-way dependency). See boundary
   doc §5 (CON-1 … CON-5).

Everything else (goal-doc parse/exec, the slice loop itself) is delegated to Claude
Code native `/goal`, Workflow, and agents wherever possible.

These two gaps are realized by the **`slice-router`** skill backed by two stdlib-only
decision libraries — `scripts/slice_router.py` (the `work_type`→slice binding,
Gap-ROUTE) and `scripts/invariant_guard.py` (INV-4 schema / new-file-only / isolated
critique / one-way, Gap-INV). **Native-delegation boundary (the one line): the harness
self-builds ONLY Gap-ROUTE + Gap-INV; the execution loop, slice fan-out, agent spawn,
Write block, and reviewer summon all stay delegated to native** (`/goal`, Workflow,
Agent, PreToolUse hooks). They are *decision* libraries, not engines — and any check
native later enforces natively is retired, not kept (P6 reversible endpoint).

## Agent output contract (schema-first, final-message fallback)

**"Only the final message returns" is a property of *every* subagent** — native
`Agent`/`Task` and schema-less Workflow `agent()` alike. A subagent can do correct work
across many turns and then end with a content-free sign-off (`"Complete."`, `"done"`);
that sign-off — not the work — becomes the return value, and the real output is stranded
in the transcript. Any handler on this substrate that spawns subagents MUST defend
against this, in order of strength:

1. **Prefer a `schema`** (structural — what `feature-full.js` does). With a schema the
   subagent is *forced* to call `StructuredOutput`; the validated object returns, never a
   stray sign-off. `feature-full.js` carries `IMPL_REPORT_SCHEMA` + `VERDICT_SCHEMA` and
   additionally throws on a `null` return, so a missing deliverable fails loudly.
2. **When a schema is too rigid** (free-form reports), pin a final-message contract in
   the prompt (shape adapted from OMC `agents/code-reviewer.md`
   `<Final_Response_Contract>`):

   > Your LAST assistant message is the deliverable surfaced to the caller. It MUST
   > contain the full structured output. Never end with a content-free sign-off; a final
   > response without the structured deliverable violates this contract.

The rule of thumb: **if you `await agent(...)` and read the result, it needs a `schema`;
if you can only read prose, paste the contract above into the prompt.**

## feature-full Workflow Script (`workflows/feature-full.js`)

The **feature-full DELEGATE carrier** ([#201](https://github.com/Lyainc/claude-kit/issues/201)).
A plain-JS Claude Code dynamic Workflow script — an authored handler *on* the native
substrate (same layer as hook handlers), not a reimplementation of the loop engine.

### What it does

It splits the feature-full route's impl and critique into **two syntactically separate
`agent()` calls**, making CON-3 structural rather than prose-only:

```
Phase 1 — Impl:     agent(implPrompt, { agentType: "executor", schema: IMPL_REPORT_SCHEMA })
Phase 2 — Critique: agent(critiquePrompt, { agentType: "code-reviewer"|null, schema: VERDICT_SCHEMA })
```

The authoring context (Phase 1 executor) **cannot participate** in the approval decision
(Phase 2 critique) — they are separate `agent()` calls with separate, isolated contexts.

### CON-3 structural enforcement

- `IMPL_AGENT_TYPE = "executor"` — #133 §1 NATIVE verdict.
- `CRITIQUE_AGENT_TYPE_BY_PAYLOAD = { diff: "code-reviewer", claim: null }` — #133 §2.
- A runtime guard throws if `resolvedImplType === resolvedCritiqueType` — belt-and-
  suspenders CON-3 check on the script's own spawn parameters.
- Subagents leave all changes in the working tree — the main context owns git (no
  commit/push/PR from a subagent). This keeps the isolated-critique premise intact (the
  critique reviews an uncommitted diff).

### Output contract / cost gate / fallback

The critique stage carries `schema: VERDICT_SCHEMA` (substrate §4.2 N3) — the schema IS
the isolation proof (`APPROVE | REJECT` + structured `findings`). The user-confirmed cost
gate lives in `slice-router` SKILL.md Phase 4 (not in this script); when the `Workflow`
tool is unavailable, Phase 4 falls back to the native-Agent procedure and **reports it
explicitly** — no silent degradation.

### Args

| Arg | Type | Required | Description |
|-----|------|----------|-------------|
| `plan` | object | yes | Verbatim `slice_router.py` JSON routing plan (`work_type === "feature-full"`) |
| `goal_doc_path` | string | yes | Path to the goal-doc |
| `spec_artifact` | string | yes | Path to spec artifact produced by spec slice in main context |
| `critique_payload` | `"diff"` \| `"claim"` | no (default `"diff"`) | Review methodology |
| `impl_agent_type` | string | no | Registry-qualified override |
| `critique_agent_type` | string | no | Registry-qualified override |

Returns `{ goal_id, impl_report, verdict }`. REJECT handling belongs to the outer `/goal`
loop, not this script.

## Local dev — run the tests

```bash
python3 dev-harness/scripts/test/test-router.py      # 4-way routing + native-fallback (dogfoods real G16)
python3 dev-harness/scripts/test/test-invariant.py   # one negative case per invariant + #201 feature-full.js static checks
```

Goal-docs stay at the repo root (`docs/plans/goal-docs/`) as shared infra — the tests
resolve them via `_SCRIPTS.parents[1]` = repo root, unaffected by this directory's
location.

## Layout

```
dev-harness/
├── .claude-plugin/
│   └── plugin.json        # OPTIONAL manifest (dev-only, NOT in marketplace.json)
├── scripts/
│   ├── slice_router.py    # #183 — work_type → slice sequence binding (Gap-ROUTE)
│   ├── invariant_guard.py # #183 — INV-4 / INV-1 / INV-2·3 / INV-5 (Gap-INV)
│   └── test/
│       ├── test-router.py     # 4-way routing + native-fallback
│       └── test-invariant.py  # one negative case per constitutional invariant + #201 static checks
├── skills/
│   ├── handoff-plan/
│   │   └── SKILL.md       # #171 — backlog chunking → goal-doc slice binding
│   └── slice-router/
│       └── SKILL.md       # #183/#201 — goal-doc → 4-way route + invariant gate + feature-full workflow carrier
├── workflows/
│   └── feature-full.js    # #201 — feature-full DELEGATE carrier (impl→critique separate agent() stages, CON-3 structural)
└── README.md
```
