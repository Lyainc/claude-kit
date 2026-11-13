// seed-board's state contract (PluginState). Walk fields are camelCase (normalized from the text
// and JSON forms of `seed-relations.py walk`); judgment fields keep the snake_case of
// next-goal's judgment JSON, which the mod stores as given. Values are JSON: absent is `null`.

export type SeedBoardVia = [edge: string, key: string]

export type SeedBoardNode = {
  key: string
  depth: number
  relation: string
  status: string
  via: SeedBoardVia[]
  target: string | null
  refines: string[]
  linkReason: string
  source: string
  /** Observed walk metadata, never authority for selecting a candidate. */
  lifecycle?: { state: 'active' | 'paused' | 'closed' | 'unknown'; outcome: 'completed' | 'discontinued' | null; reason: string | null }
  eligibility?: { eligible: boolean; reason: string; excludedItems: string[]; reviewRequired: boolean }
}

export type SeedBoardItem = { owner: string; id: string; refinedBy: string[] }
export type SeedBoardEdge = { from: string; edge: string; to: string }
export type SeedBoardStop = { from: string; edge: string; target: string; reason: string }
export type SeedBoardFailure = { key: string; error: string }

export type SeedBoardSummary = {
  visited: number
  stopped: number
  failed: number
  cycles: number
  external: number
  notfound: number
}

export type SeedBoardWalk = {
  id: string
  at: string
  start: string
  maxDepth: number
  maxNodes: number
  fingerprint: string
  nodes: SeedBoardNode[]
  items: SeedBoardItem[]
  dups: SeedBoardEdge[]
  cycles: SeedBoardEdge[]
  stops: SeedBoardStop[]
  failures: SeedBoardFailure[]
  summary: SeedBoardSummary
  /** Arrival order, set by the mod. */
  seq: number
}

export type SeedBoardPick = {
  title: string
  via: string
  targets: string[]
  evidence: string
  startable: string
  startable_reason: string
  user_change: string
  note: string | null
}

export type SeedBoardAlternative = {
  title: string
  via: string
  decision: string
  reason: string
}

export type SeedBoardJudgment = {
  seed: string | null
  walk_id: string | null
  handoff: 'named' | 'missing' | 'none'
  pick: SeedBoardPick | null
  alternatives: SeedBoardAlternative[]
  unverified: string[]
  /** Optional STOP assertions validated by the renderer against the fresh walk. */
  walk_stops: SeedBoardStop[]
  /** The rendered NEXT/FROM/SKIPPED/TRACE lines, verbatim. */
  lines: string[]
  /** `at` of the stored walk this judgment references, when that walk was known on arrival. */
  walkAt: string | null
  /** Arrival order, set by the mod. */
  seq: number
}

export type SeedBoardPending = {
  title: string
  via: string
  walk_id: string | null
  requestedAt: number
}

export type SeedBoardLastSwitch = {
  title: string
  via: string
  result: 'applied' | 'not-applied'
  at: number
}

export type SeedBoardIndexEdge = {
  from: string
  to: string
  /** The target's classification as `index` printed it (indexed, notfound, external, ...). */
  target: string
  /** Item ids the edge names (`depends_on` item, replaces/transfers/provenance items). */
  items: string[]
  commit: string | null
}

export type SeedBoardIndexSeed = {
  path: string
  /** Unique row key: `path`, or `path#N` (1-based) when several Seeds share a path; those get no edge rows. */
  key: string
  title: string
  goal: string
  created: string | null
  /** Observed lifecycle as `index` printed it; never authority for selecting a candidate. */
  lifecycle: NonNullable<SeedBoardNode['lifecycle']>
  eligibility: NonNullable<SeedBoardNode['eligibility']> & { heldItems: string[] }
  source: string | null
  tracking: string[]
  /** The fields below come with `--full` only; a plain index leaves them empty. */
  refines: string[]
  linkReason: string | null
  refinesMap: string[]
  evidence: { commit: string | null; items: { id: string; refs: string[] }[] }
  acceptance: { id: string; satisfied: boolean; outOfScope: string | null }[]
  openQuestions: string[]
  blindspots: { area: string; question: string }[]
  /** Lowercased path, title, goal and issue text, built once for the search box. */
  search: string
}

export type SeedBoardIndex = {
  generatedAt: string
  /** `seed-index-full/1` (`--full`) when true; the lighter shape otherwise. */
  isFull: boolean
  seeds: SeedBoardIndexSeed[]
  /** Edges per type (parent, children, depends_on, and with `--full` replaces, transfers, provenance). */
  edges: Record<string, SeedBoardIndexEdge[]>
  /** The same edges keyed by `from`, as `[type, edge]` in print order. */
  edgesByFrom: Record<string, [string, SeedBoardIndexEdge][]>
  errors: { path: string; error: string }[]
}

declare module 'claude-code' {
  interface PluginState {
    'seed-board': {
      /** Latest walk per start path. */
      walks: Record<string, SeedBoardWalk>
      /** Latest accepted judgment. */
      judgment: SeedBoardJudgment | null
      /** A candidate switch the person asked for and next-goal has not answered yet. */
      pending: SeedBoardPending | null
      /** How the last candidate switch ended. */
      lastSwitch: SeedBoardLastSwitch | null
      /** Expanded node keys (`node:<key>`), candidate titles (`cand:<title>`) and index rows (`seed:<key>`). */
      expanded: Record<string, true>
      /** Arrival counter for walks and judgments. */
      seq: number
      /** Latest repo-wide `seed-relations.py index --json` output. */
      index: SeedBoardIndex | null
      /** Which tab the pane draws. */
      view: 'walk' | 'index'
      /** The index tab's lifecycle filter (`open`, `all`, `active`, `paused`, `closed`, `unknown`). */
      filter: string
      /** The index tab's search text. */
      query: string
    }
  }
}
