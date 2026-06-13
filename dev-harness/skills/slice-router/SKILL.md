---
name: slice-router
description: "Goal-doc execution router for the ⑤ harness: parse a goal-doc, validate it against the #100 schema (INV-4), bind its work_type to a slice sequence (feature-full → spec→impl→critique / decision-only / doc-only, or bug-light = goal-doc absence → debug direct), and enforce the constitutional invariants native can't (new-file-only vault writes, isolated critique / no self-approval, one-way dependency). Delegates the actual loop to native /goal + Workflow + agents — it only owns the routing decision and the invariant judgment. feature-full DELEGATE uses the workflow script (workflows/feature-full.js, #201) when available: structural CON-3 via separate agent() stages, behind a user-confirmed cost gate. Trigger: 슬라이스 라우팅, goal-doc 실행, 라우터, 워크타입 라우팅, 골닥 실행, 인바리언트 검사, slice route, route goal-doc, execute goal-doc, slice router, invariant check. Routing: goal-doc GENERATION (backlog → slice binding) is handoff-plan; this skill ROUTES an existing goal-doc for execution. Example: '/slice-router docs/plans/goal-docs/G16-...md' or 'goal-doc 라우팅해줘'."
model: inherit
allowed-tools: Read Bash Grep Glob Agent AskUserQuestion Workflow
---

**User language: Korean.** All user-facing output (status lines, the routing plan,
confirmation messages) MUST be in Korean. Instructions below are English for LLM parsing.

# slice-router — goal-doc → 4-way slice binding + invariant gate (layer ⑤)

`slice-router` is the ⑤ harness's **Gap-ROUTE + Gap-INV** entrypoint
(`omc-to-native-substrate.md` §4). Given a goal-doc, it (1) validates the schema
(INV-4), (2) binds `work_type` to a slice sequence and each slice to a skill
(goal-doc-spec §3.6), and (3) enforces the constitutional invariants native cannot.
It is the counterpart to `handoff-plan`: `handoff-plan` *writes* a goal-doc from the
backlog (② output-adjacent), `slice-router` *routes an existing goal-doc for
execution* (⑤ slice loop). **Distinct roles — no overlap.**

## Native-delegation boundary (the #122 thin principle — DO read before running)

The harness **delegates to native first**. It builds ONLY the two things native
cannot express; everything else is native's job. This boundary is the whole point of
the plugin — never reimplement the right column.

| Harness owns (self-built — native ungoverned gap) | Delegated to native |
|---|---|
| **Gap-ROUTE** — `work_type` → slice sequence + per-slice binding decision (`scripts/slice_router.py`) | the goal-doc **execution loop** itself → native **`/goal`** (session-autonomous run + Stop-hook completion) |
| **Gap-INV** — INV-4 schema / INV-1 new-file-only / INV-2·3 isolated critique / INV-5 one-way (`scripts/invariant_guard.py`) | slice **fan-out / pipeline** → native **Workflow** (`parallel()`/`pipeline()`) |
| | subagent **spawn + model routing** → native **Agent / `agentType`** (executor, code-reviewer, …) |
| | the actual **Write block** → native **PreToolUse hook** (vault-bridge `pre-write-guard`) |
| | reviewer **summon** → native Workflow **verify stage** |

The two scripts are *decision libraries*, not runtime engines: they return a verdict
/ a plan, and native does the doing. If a future native release enforces one of these
invariants natively, the matching self-built check is *retired*, not kept (P6
reversible endpoint — boundary §1, substrate §5). The self-build is bounded to the
gap, by design.

> **ADR note (#201):** `workflows/feature-full.js` is an *authored handler ON the
> native substrate* — a declarative composition of native primitives (`agent()` /
> `pipeline()`), the same layer as hook handlers. It is NOT a reimplementation of
> the right column (the loop engine stays native Workflow).

## Boundary & safety (constitutional — do not relax)

Single source of truth: [`docs/design/claude-kit-boundary.md`](../../../docs/design/claude-kit-boundary.md) §5.
This skill **enforces** these (it does not redefine them):

- **CON-4 / INV-4 (goal-doc schema)**: `invariant_guard.validate_goal_doc` runs FIRST.
  A goal-doc that fails the schema is **never routed** — fix it before execution.
- **CON-3 / INV-2·3 (isolated critique, no self-approval)**: a `feature-full` route's
  critique slice binds to a reviewer **disjoint** from the authoring slices
  (`check_isolated_critique`). The critique subagent is spawned as a **separate**
  Agent context — the authoring context never approves its own output.
- **CON-1 / INV-1 (new-file-only)**: any vault write a slice emits must create a new
  file (`check_new_file_only`); the only in-place exception is a frontmatter-only
  status-machine transition (boundary §5 note). Subagent vault writes stay blocked
  by vault-bridge `pre-write-guard` (native).
- **CON-5 / INV-5 (one-way dependency)**: this skill only *reads* goal-docs/specs and
  *invokes* leaf skills / native agents downward. No leaf depends back on it; never
  add a reverse edge.

## Pipeline: VALIDATE → ROUTE → ENFORCE → DELEGATE

### Phase 1 — VALIDATE (INV-4, blocking)

Resolve the goal-doc the user named (a path arg, or the active `/goal`'s goal-doc).
If **no goal-doc exists**, this is **bug-light** (§4.4) — skip straight to a debug
route (Phase 2 handles it). Otherwise validate the schema:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/invariant_guard.py validate <goal-doc.md>
```

- Exit 0 → schema OK, proceed to ROUTE.
- Exit 1 → print the violations (Korean) and **STOP**. A malformed goal-doc is never
  routed; the user fixes it (or asks `handoff-plan` to regenerate it) first.

### Phase 2 — ROUTE (Gap-ROUTE, §3.6 + §4.4)

```bash
# goal-doc present → route by work_type
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slice_router.py <goal-doc.md>
# no goal-doc (bug-light) → debug direct, no slice
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slice_router.py
```

The JSON plan is the routing decision:

| `work_type` | route | slices / binding |
|---|---|---|
| `feature-full` | `spec→impl→critique` | spec=`spec-first` → impl=`executor\|native(#133)` → critique=`adversarial-review\|code-reviewer(#133)` — **each a separate skill** |
| `decision-only` | `decide-only` | `expert-panel\|adversarial-review` — 산출만, no implementation |
| `doc-only` | `output-only` | `doc-concretize\|doc-polish\|spec-first` — output only |
| *(bug-light)* | `debug-direct` | `debug(#133)` — goal-doc absent, no slice |

`→` is output→input chaining (§3.5): each slice's artifact feeds the next. Candidate-or
bindings (`executor|native(#133)`) defer the concrete skill to #133's inventory —
**native-delegation first**: prefer a native agent / existing leaf over building new.

### Phase 3 — ENFORCE (Gap-INV gate, before any execution)

Before delegating, gate the plan:

1. **Isolated critique (CON-3)**: confirm the routed plan passes
   `check_isolated_critique` — the critique binding must not overlap the authoring
   bindings. (The §3.6 default already satisfies this; a hand-edited goal-doc might
   not.) If it overlaps, STOP and report — never let an author approve itself.
2. **New-file-only (CON-1)**: any slice that writes a vault note must target a new
   path (or be a frontmatter-only status patch). Surface this as a constraint to the
   delegated slice; the native `pre-write-guard` is the hard block.

### Phase 4 — DELEGATE (to native — the harness does NOT run the loop)

Hand each slice to native in sequence, honoring the chaining (`→`):

- **feature-full**:
  1. **Spec slice in MAIN context first**: run `spec-first` (AskUserQuestion interview)
     in the current main context. Capture its artifact path. `spec-first` uses
     AskUserQuestion, which cannot run inside a workflow subagent — it MUST run here.
  2. **User-confirmed COST GATE** (Korean, AskUserQuestion): present the routed plan,
     the expected scale (2 subagents: impl executor + isolated critique reviewer), and
     the token-cost warning. **Silent invocation is FORBIDDEN** — the user must
     explicitly confirm before the Workflow tool is called (retro "Silent ... is
     FORBIDDEN" pattern).
  3. **On explicit confirmation only**: invoke the workflow script —
     ```
     Workflow({
       scriptPath: "${CLAUDE_PLUGIN_ROOT}/workflows/feature-full.js",
       args: {
         plan: <verbatim slice_router.py JSON routing plan>,
         goal_doc_path: <goal-doc path>,
         spec_artifact: <artifact path from step 1>,
         critique_payload: "diff" | "claim"
       }
     })
     ```
     Write `${CLAUDE_PLUGIN_ROOT}` literally — it is resolved at runtime by Claude Code.
     The script's default agentTypes are the #133 inventory tokens (`executor` /
     `code-reviewer`). If the environment's agent registry only resolves **qualified**
     names (dogfood 2026-06-10: `oh-my-claudecode:executor`), pass them via the
     `impl_agent_type` / `critique_agent_type` args overrides — the script's CON-3
     disjoint assert applies to the resolved pair either way, and an unresolvable
     agentType fails fast with the registry listing (0 tokens spent).
  4. **Fallback**: when the Workflow tool is unavailable in the environment, fall back
     to the existing native-Agent procedure: spawn the critique slice as a **separate
     Agent context** (`code-reviewer` / `adversarial-review`) — never the same context
     that authored (CON-3). This is the prose path proven in G4/#198. **Report the
     fallback explicitly** — no silent degradation (say "Workflow unavailable, using
     native-Agent fallback" in the output).
  5. A REJECT verdict goes back to the impl slice for a fix round — the loop is native
     `/goal`, not this skill.
- **decision-only**: run `expert-panel` / `adversarial-review` for the verdict; **no
  implementation** — the output is the decision artifact.
- **doc-only**: run `doc-concretize` / `doc-polish` / `spec-first`; **output only**.
- **bug-light**: no goal-doc, no slice — route straight to debug (`#133`). The loop
  itself (iterate-until-fixed) is native `/goal` + Workflow, not this skill.

The active agent under `/goal` performs the delegation; `slice-router` supplied the
*decision*. Report the routed plan + each slice's outcome (Korean). Never claim to
have "run" the loop — native ran it; the harness routed it.

## Configuration

| Env var | Default | Effect |
|---|---|---|
| `CLAUDE_PLUGIN_ROOT` | (set by Claude Code) | resolves the two decision scripts |

## Rules

- VALIDATE (INV-4) is blocking: a goal-doc failing the schema is never routed.
- The four routes are fixed by `work_type` (§3.6); bug-light is goal-doc ABSENCE
  (§4.4), never a `work_type` value.
- A `feature-full` critique slice binds to a **separate** reviewer and runs in a
  **separate** Agent context (CON-3 — no self-approval).
- Native-delegation first: own only Gap-ROUTE + Gap-INV; delegate the loop,
  fan-out, agent spawn, Write block, and reviewer summon to native. Never rebuild
  the right column of the boundary table.
- CON-5: read goal-docs/specs and invoke leaf skills downward only; no reverse
  dependency, ever.
- **feature-full DELEGATE rides the workflow script** (`workflows/feature-full.js`)
  when the Workflow tool is available — structural CON-3 (impl and critique are
  syntactically separate `agent()` calls). Silent Workflow invocation is forbidden;
  the user-confirmed cost gate in Phase 4 step 2 must fire first.
- **The script consumes the Phase-2 routing plan verbatim** (anti goal-drift). The
  plan JSON is forwarded unchanged into both the impl and critique prompts as the
  anti-drift anchor.
