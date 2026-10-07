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
      /** Expanded node keys (`node:<key>`) and candidate titles (`cand:<title>`). */
      expanded: Record<string, true>
      /** Arrival counter for walks and judgments. */
      seq: number
    }
  }
}
