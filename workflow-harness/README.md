# workflow-harness

claude-kit **layer ⑤ (execution / doing)** harness — a lightweight orchestration
plugin built **on top of Claude Code native primitives** (`/goal`, dynamic
Workflow, agents, hooks).

> **Status: v0.1.0 thin scaffold.** This is the *minimal plugin shell*, not the
> full OMC-strangler engine described in [#122](https://github.com/Lyainc/claude-kit/issues/122).
> It exists so layer ⑤ skills (starting with `retro`, [#123](https://github.com/Lyainc/claude-kit/issues/123))
> have a home that satisfies claude-kit's boundary contract. Capability lands
> incrementally, route by route — never as a big-bang replacement.

## Why this plugin exists

claude-kit owns four leaf layers — ①인지, ②결정화·출력, ③딜리버리, ④지식베이스 —
as vendor-neutral plugins: `thinking-tools` (①), `obsidian-vault-manager` (②④),
`vault-bridge` (③). (A separate project-local `telemetry/` directory dogfoods
these plugins; it is **not** itself a plugin and not a leaf layer — see the
dependency note below.) Layer **⑤실행** is
*evolutionary*: today OMC (or Claude Code native) drives it, and claude-kit grows
a **native-substrate-based lightweight harness** that absorbs ⑤ responsibilities
**route by route (strangler pattern)** — not a from-scratch engine.

`workflow-harness` is that harness. v0.1.0 ships only the manifest + this README
so the first real consumer (`retro`) can move in without violating the layering
rules below.

## Dependency direction — ONE-WAY (harness → leaf)

This plugin is bound by **CON-5** (the constitutional one-way dependency rule).
The single source of truth is
[`docs/design/claude-kit-boundary.md`](../docs/design/claude-kit-boundary.md) §3 / §5.

```
workflow-harness  ─────▶  vault-bridge            (leaf ③ delivery: memory branch via user-initiated slash)
   (harness, ⑤)   ─────▶  obsidian-vault-manager  (leaf ②④: E8 promotion findings / audit input)

                  ┄┄┄▶  telemetry/   (project-local measurement dogfooding output — NOT a plugin,
                                       NOT a leaf layer; read by `retro` in slice 2 for dedup
                                       history / retro meta. No dependency edge exists at v0.1.0.)
```

The two solid edges are the leaf-plugin dependencies that land as skills move in.
The dashed line to `telemetry/` is a *measurement* read realized only when `retro`
(slice 2) arrives — it is not a leaf plugin and the v0.1.0 scaffold has no edge to it.

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

## Roadmap (incremental, route by route)

| Slice | Skill / capability | Issue | Status |
|-------|--------------------|-------|--------|
| 1 | thin scaffold (this) | #122 | ✅ v0.1.0 |
| 2 | `retro` — E8 promotion + 3-branch output + dedup + budget | #123 | next |
| 3 | `handoff` realization — issue chunking / epic proposal → goal-doc slice binding | #171 | planned |
| — | gate-chain orchestration (pre-commit / slice critique / pre-push quality / retro) | #134 | planned |

## Layout

```
workflow-harness/
├── .claude-plugin/
│   └── plugin.json        # manifest (v0.1.0)
├── skills/                # layer ⑤ skills land here (retro = first, #123)
└── README.md
```
