# workflow-harness

claude-kit **layer ⑤ (execution / doing)** harness — a lightweight orchestration
plugin built **on top of Claude Code native primitives** (`/goal`, dynamic
Workflow, agents, hooks).

> **Status: v0.4.0 — thin scaffold + three skills + the #122-residual router.**
> This is still a *lightweight harness*, not the full OMC-strangler engine described
> in [#122](https://github.com/Lyainc/claude-kit/issues/122). It ships three layer ⑤
> skills: `retro` ([#123](https://github.com/Lyainc/claude-kit/issues/123)), which
> closes the measure→improve loop; `handoff-plan`
> ([#171](https://github.com/Lyainc/claude-kit/issues/171)), which chunks the open
> backlog into goal-doc slice bindings for the next session's `/goal`; and
> `slice-router` ([#183](https://github.com/Lyainc/claude-kit/issues/183)) — the
> #122-residual **4-way slice router + D5 invariant enforcement**, which routes an
> existing goal-doc to its slice sequence and enforces the constitutional invariants
> native cannot. Capability lands incrementally, route by route — never as a big-bang
> replacement.

## Why this plugin exists

claude-kit owns four leaf layers — ①인지, ②결정화·출력, ③딜리버리, ④지식베이스 —
as vendor-neutral plugins: `thinking-tools` (①), `obsidian-vault-manager` (②④),
`vault-bridge` (③). (A separate project-local `telemetry/` directory dogfoods
these plugins; it is **not** itself a plugin and not a leaf layer — see the
dependency note below.) Layer **⑤실행** is
*evolutionary*: today OMC (or Claude Code native) drives it, and claude-kit grows
a **native-substrate-based lightweight harness** that absorbs ⑤ responsibilities
**route by route (strangler pattern)** — not a from-scratch engine.

`workflow-harness` is that harness. v0.2.0 shipped its first consumer, `retro`
(reads leaf output — audit E8 findings, telemetry — and turns it into
user-confirmed actions); v0.3.0 added `handoff-plan`, which reads the open GitHub
backlog and emits goal-doc slice bindings the next session's `/goal` can run; v0.4.0
adds `slice-router`, the #122-residual router that takes an *existing* goal-doc and
binds its `work_type` to a slice sequence while enforcing the D5 constitutional
invariants. All three stay within the one-way layering rules below.

## Dependency direction — ONE-WAY (harness → leaf)

This plugin is bound by **CON-5** (the constitutional one-way dependency rule).
The single source of truth is
[`docs/design/claude-kit-boundary.md`](../docs/design/claude-kit-boundary.md) §3 / §5.

```
workflow-harness  ─────▶  vault-bridge            (leaf ③ delivery: memory branch via user-initiated slash)
   (harness, ⑤)   ─────▶  obsidian-vault-manager  (leaf ②④: E8 promotion findings / audit input)

                  ┄┄┄▶  telemetry/   (project-local measurement dogfooding output — NOT a plugin,
                                       NOT a leaf layer; read by `retro` for dedup history /
                                       retro meta when CLAUDE_KIT_TELEMETRY=1.)
```

The two solid edges are leaf-plugin dependencies. The dashed line to `telemetry/`
is a *measurement* read (realized by `retro`) — `telemetry/` is not a leaf plugin,
and the read is best-effort / opt-in, so the harness degrades gracefully without it.

- **Allowed:** `workflow-harness` invokes leaf-plugin capabilities (calls a slash
  command, reads an audit finding) and may read the local telemetry dogfooding
  output. The harness is Claude-Code-specific (it depends on native primitives);
  the leaves stay harness-neutral.
- **Forbidden (no reverse, no cycle):** a leaf plugin (①②③④) MUST NOT import,
  call, or assume any `workflow-harness` API or behavior. Leaves are
  independently installable and harness-neutral *by construction*. If you find a
  leaf reaching "up" into the harness, that is a CON-5 violation — fix the
  direction, do not add a back-edge.
- **Physical-location gate (#140):** where a future capability physically lives
  (② leaf vs. ⑤ harness) is decided at build time by the #140 gate — "issue
  reading → chunking" sits next to ② output, "slice loop" sits in ⑤ — always
  choosing the placement that keeps the dependency one-way.

## Native-substrate principle (#122)

The harness **delegates to native first** and only adds a thin layer for what
native cannot express:

1. **Slice → skill binding routing** — map a goal-doc slice to the right
   leaf skill / native agent.
2. **Constitutional invariant enforcement** — enforce the invariants native
   cannot guarantee (new-file-only vault writes, isolated critique /
   no self-approval, goal-doc as a stable harness-neutral contract, one-way
   dependency). See boundary doc §5 (CON-1 … CON-5).

Everything else (goal-doc parse/exec, the slice loop itself) is delegated to
Claude Code native `/goal`, Workflow, and agents wherever possible.

As of v0.4.0 these two gaps are realized by the **`slice-router`** skill backed by
two stdlib-only decision libraries — `scripts/slice_router.py` (the `work_type`→slice
binding, Gap-ROUTE) and `scripts/invariant_guard.py` (INV-4 schema / new-file-only /
isolated critique / one-way, Gap-INV). **Native-delegation boundary (the one line):
the harness self-builds ONLY Gap-ROUTE + Gap-INV; the execution loop, slice fan-out,
agent spawn, Write block, and reviewer summon all stay delegated to native** (`/goal`,
Workflow, Agent, PreToolUse hooks). They are *decision* libraries, not engines — and
any check native later enforces natively is retired, not kept (P6 reversible endpoint).

## Roadmap (incremental, route by route)

| Slice | Skill / capability | Issue | Status |
|-------|--------------------|-------|--------|
| 1 | thin scaffold | #122 | ✅ v0.1.0 |
| 2 | `retro` — E8 promotion + 3-branch output + dedup + budget | #123 | ✅ v0.2.0 |
| 3 | `handoff-plan` — open-issue chunking (dependency + domain) → user-confirmed epic candidates → goal-doc slice binding | #171 | ✅ v0.3.0 |
| 4 | `slice-router` — #122-residual 4-way slice router + D5 invariant enforcement | #183 | ✅ v0.4.0 |
| — | gate-chain orchestration (pre-commit / slice critique / pre-push quality / retro) | #134 | planned |

## Layout

```
workflow-harness/
├── .claude-plugin/
│   └── plugin.json        # manifest (v0.4.0)
├── scripts/
│   ├── slice_router.py    # #183 S1 — work_type → slice sequence binding (Gap-ROUTE)
│   ├── invariant_guard.py # #183 S2 — INV-4 / INV-1 / INV-2·3 / INV-5 (Gap-INV)
│   └── test/
│       ├── test-router.py     # 4-way routing + native-fallback
│       └── test-invariant.py  # one negative case per constitutional invariant
├── skills/
│   ├── retro/
│   │   └── SKILL.md       # #123 — E8 promotion + 3-branch output + dedup + budget
│   ├── handoff-plan/
│   │   └── SKILL.md       # #171 — backlog chunking → goal-doc slice binding
│   └── slice-router/
│       └── SKILL.md       # #183 — goal-doc → 4-way route + invariant gate (entrypoint)
└── README.md
```
