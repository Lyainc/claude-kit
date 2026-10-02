# seed-board

An **optional** Claude Code mod: a read-only pane that shows the Seed relation tree and
`next-goal`'s judgment next to the terminal output. Issue #792.

It is a separate plugin of function hooks. The `thinking-tools` plugin manifest does not load it,
so Codex, older Claude Code builds and runs with no UI (`claude -p`) are unaffected: without this
mod everything works exactly as before.

## Enable it

Needs a Claude Code build with function hooks. Checked live: 2.1.287 loads it and lists
`/seed-board`; 2.1.263 lists the plugin but runs no module and the session continues normally,
so there is no pane there. It carries no `version`: it ships inside thinking-tools and is not a
marketplace entry, so the lockstep release has nothing to bump. Per session:

```bash
claude --plugin-dir <path-to>/thinking-tools/mods/seed-board
```

or, where no flag can be given (desktop app, SDK host):

```bash
export CLAUDE_CODE_PLUGIN_DIRS=<path-to>/thinking-tools/mods/seed-board
```

Then type `/seed-board` to open the pane. The mod never opens it on its own.

## What it shows

The mod only watches Bash output that the skills already produce:

- `seed-relations.py walk` (text records or `--json`): header (start Seed, walk id, time,
  fingerprint, visited/stopped/failed/cycles/external/notfound), and a relation tree grouped as
  start, ancestor, ancestor-child, descendant, predecessor, then external. Press a node to expand
  its path, target, refines, link reason (`미확인` when unknown), source, the items it owns and any
  stop/cycle/duplicate/failure records.
- `next-goal-render.py` (its judgment JSON is read from the command's `<<'JSON'` heredoc):
  the rendered NEXT/FROM/SKIPPED/TRACE lines verbatim, the pick and the alternatives, each
  expandable. A judgment whose `walk_id` is not the latest walk of its Seed carries a badge
  ("근거가 바뀐 이전 판단 — next-goal 재실행 필요"). A missing Seed handoff is shown as such, apart from
  "no candidate".
- **이 후보로 바꾸기** on an alternative (not shown for `external`/`done`): fills the prompt box with a
  request for `next-goal`. It never submits it. The pane then shows 반영 대기, and 반영 완료 or
  반영 안 됨 once the next judgment arrives, so the person sees whether `next-goal` really changed
  its pick.

A walk replaces the stored one for the same start only if its `at` is not older, so a slow older
run never overwrites a newer screen.

## What it does not do

- No judging, scoring or re-ranking: candidates, reasons and order are `next-goal`'s as printed.
- No file, process, network, model or agent calls (`$.fs`, `$.process`, `$.http`, `$.model`,
  `$.agent` are not used; `claude plugin validate` lists the calls the module makes).
- It never denies or rewrites a tool call. All parsing runs after the tool finished, inside
  try/catch; a malformed output is ignored and the tool result goes on unchanged.
- No graph, SVG, Mermaid, drag or zoom. Only `Box`, `Text` and `Button`, which exist on both the
  terminal and desktop element tables. `claude plugin test` mounts the pane on both surfaces; the kit
  checks the returned tree, not the paint, so the desktop app's actual rendering is not verified here.

## Develop

```bash
claude plugin validate thinking-tools/mods/seed-board
claude plugin test thinking-tools/mods/seed-board
```

State is declared in `types/index.d.ts`; `hooks/parse.ts` holds the pure parsers and
`hooks/register.tsx` the hooks and the pane.
