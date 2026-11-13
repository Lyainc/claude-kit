# seed-board

An **optional** Claude Code mod: a read-only pane that shows the Seed relation tree and
`next-goal`'s judgment and a repo-wide Seed list next to the terminal output. Issues #792, #897.

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
  Lifecycle, closure outcome/reason, excluded items and review holds come from the same walk.
  Closed Seeds stay visible as history; an older cache without lifecycle is shown as unknown.
- `next-goal-render.py` (its judgment JSON is read from the command's `<<'JSON'` heredoc):
  the rendered NEXT/FROM/SKIPPED/TRACE lines verbatim, the pick and the alternatives, each
  expandable. A judgment whose `walk_id` is not the latest walk of its Seed carries a badge
  ("근거가 바뀐 이전 판단 — next-goal 재실행 필요"). A missing Seed handoff is shown as such, apart from
  "no candidate". No-pick judgments retain FROM's reviewed-scope or unevaluated-scope conclusion
  and TRACE's gaps even without a Seed; STOP assertions are normalized from the same JSON,
  while their verification and the displayed visited/stopped records belong to the renderer.
- **이 후보로 바꾸기** on an alternative (not shown for `external`/`done`): fills the prompt box with a
  request for `next-goal`. It never submits it. The pane then shows 반영 대기, and 반영 완료 or
  반영 안 됨 once the next judgment arrives, so the person sees whether `next-goal` really changed
  its pick.

- `seed-relations.py index <dir>... --json [--full]` (the JSON form only): the **Seed 목록** tab.
  Whoever runs `index` (you or a skill) fills it; the pane never runs it, so it updates when
  `index` is run again, not when the pane opens. It shows the Seed count, the generation time
  (`· full` for `--full`), the count per lifecycle state (active, paused, closed with completed and
  discontinued, unknown), the Seeds that could not be read, and a list of the Seeds ordered by
  state. A **보기** select filters by the printed lifecycle state (`열림` = not closed, the
  default; `전체`; active; paused; closed; unknown) and a **검색** field matches path, title, goal
  and issue numbers (every word must match). Press a Seed to expand its printed detail: lifecycle,
  candidate eligibility, issues, relation edges with the target's classification, and with
  `--full` also acceptance fulfilment (충족, 미충족, 범위 밖), evidence, open questions and
  blindspots. Without `--full` the detail simply has fewer lines. The list draws only as many Seeds
  as fit the viewport (an opened Seed always shows whole; search reaches the rest), because one
  tree draws at most its first 100,000 characters.
  The tab bar (관계·판단 / Seed 목록) appears once an index was observed; a newer index replaces
  the stored one, an older one does not, and the latest observation (an index, a walk or a judgment)
  decides which tab is shown. An `index` run that exits 1 because a Seed could not be read is
  still observed. The mod only groups and matches the printed fields; it does not interpret
  lifecycle or relations.

A walk replaces the stored one for the same start only if its `at` is not older, so a slow older
run never overwrites a newer screen.

A judgment is ordered by when its renderer call started, not when it finished: a slower earlier run
(for the same Seed or another) never replaces the judgment of a run that started after it.

## What it does not do

- No judging, scoring or re-ranking: candidates, reasons and order are `next-goal`'s as printed.
- No file, process, network, model or agent calls (`$.fs`, `$.process`, `$.http`, `$.model`,
  `$.agent` are not used; `claude plugin validate` lists the calls the module makes).
- It never denies or rewrites a tool call. All parsing runs after the tool finished, inside
  try/catch; a malformed output is ignored and the tool result goes on unchanged.
- No graph, SVG, Mermaid, drag or zoom (the per-area flow graph stays in the HTML board). Only
  `Box`, `Text`, `Button`, `Input` and `Select`, which exist on both the terminal and desktop
  element tables. `claude plugin test` mounts the pane on both surfaces; the kit
  checks the returned tree, not the paint, so the desktop app's actual rendering is not verified here.

## Develop

```bash
claude plugin validate thinking-tools/mods/seed-board
claude plugin test thinking-tools/mods/seed-board
```

State is declared in `types/index.d.ts`; `hooks/parse.ts` holds the pure parsers and
`hooks/register.tsx` the hooks and the pane.
