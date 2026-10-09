// Pure parsers for what the skills already print. No `$`, no state: text in, plain data out.
// Anything that does not look right throws; the caller (register.tsx) turns a throw into
// "leave the tool result alone".
import type {
  SeedBoardAlternative,
  SeedBoardEdge,
  SeedBoardFailure,
  SeedBoardItem,
  SeedBoardJudgment,
  SeedBoardNode,
  SeedBoardPick,
  SeedBoardStop,
  SeedBoardSummary,
  SeedBoardVia,
  SeedBoardWalk,
} from '../types/index'

export type ParsedWalk = Omit<SeedBoardWalk, 'seq'>
export type ParsedJudgment = Omit<SeedBoardJudgment, 'seq' | 'walkAt' | 'lines'>

export const UNVERIFIED = '미확인'

const WALK_CMD = /seed-relations\.py["']?\s+walk\b/
const RENDER_CMD = /next-goal-render\.py/

export const isWalkCommand = (command: string): boolean => WALK_CMD.test(command)
export const isRenderCommand = (command: string): boolean => RENDER_CMD.test(command)

type Obj = Record<string, unknown>

const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)

const str = (v: unknown, fallback = ''): string =>
  typeof v === 'string' ? v : typeof v === 'number' ? String(v) : fallback

const need = (v: unknown, what: string): string => {
  const s = str(v).trim()
  if (s === '') throw new Error(`seed-board: ${what} is empty`)
  return s
}

const num = (v: unknown, fallback = 0): number => {
  const n = typeof v === 'number' ? v : Number(str(v))
  return Number.isFinite(n) ? n : fallback
}

const dash = (v: unknown): string | null => {
  const s = str(v).trim()
  return s === '' || s === '-' ? null : s
}

const textOrUnverified = (v: unknown): string => dash(v) ?? UNVERIFIED

const strList = (v: unknown): string[] =>
  Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []

const csv = (v: unknown): string[] => {
  const s = str(v).trim()
  return s === '' || s === '-' || s === '(none)' ? [] : s.split(',').map(x => x.trim()).filter(Boolean)
}

// Old or malformed observations remain visible but cannot imply candidate eligibility.
const lifecycleOf = (v: unknown): NonNullable<SeedBoardNode['lifecycle']> => {
  const o = isObj(v) ? v : {}
  const state = o.state === 'active' || o.state === 'paused' || o.state === 'closed' ? o.state : 'unknown'
  const outcome = o.outcome === 'completed' || o.outcome === 'discontinued' ? o.outcome : null
  return { state, outcome, reason: dash(o.reason) }
}

const eligibilityOf = (v: unknown): NonNullable<SeedBoardNode['eligibility']> => {
  const o = isObj(v) ? v : {}
  const valid = typeof o.eligible === 'boolean' && typeof o.review_required === 'boolean'
    && Array.isArray(o.excluded_items) && o.excluded_items.every(x => typeof x === 'string')
  return {
    eligible: valid && o.eligible === true && o.review_required === false,
    reason: textOrUnverified(o.reason),
    excludedItems: strList(o.excluded_items),
    reviewRequired: !valid || o.review_required !== false,
  }
}

const textBool = (v: unknown): boolean | undefined =>
  v === 'true' ? true : v === 'false' ? false : undefined

/** `edge>key>edge>key`, or `-` for none. An odd tail is kept as an edge with an empty key. */
const parseVia = (v: unknown): SeedBoardVia[] => {
  if (Array.isArray(v)) {
    return v.flatMap((p): SeedBoardVia[] =>
      Array.isArray(p) && typeof p[0] === 'string' ? [[p[0], str(p[1])]] : [],
    )
  }
  const s = str(v).trim()
  if (s === '' || s === '-') return []
  const parts = s.split('>')
  const out: SeedBoardVia[] = []
  for (let i = 0; i < parts.length; i += 2) out.push([parts[i] ?? '', parts[i + 1] ?? ''])
  return out
}

/** `name=value` segments; a segment with no known-looking `name=` continues the previous value. */
const kv = (segments: string[]): Record<string, string> => {
  const out: Record<string, string> = {}
  let last = ''
  for (const seg of segments) {
    const at = seg.indexOf('=')
    const name = at > 0 ? seg.slice(0, at) : ''
    if (/^[a-z_]+$/.test(name)) {
      out[name] = seg.slice(at + 1)
      last = name
    } else if (last !== '') {
      out[last] = `${out[last] ?? ''} ${seg}`
    }
  }
  return out
}

const edgeOf = (a: unknown): SeedBoardEdge => {
  if (Array.isArray(a)) return { from: str(a[0]), edge: str(a[1]), to: str(a[2]) }
  const o = isObj(a) ? a : {}
  return { from: str(o.from), edge: str(o.edge), to: str(o.to ?? o.target) }
}

const stopOf = (a: unknown): SeedBoardStop => {
  if (Array.isArray(a)) return { from: str(a[0]), edge: str(a[1]), target: str(a[2]), reason: str(a[3]) }
  const o = isObj(a) ? a : {}
  return { from: str(o.from), edge: str(o.edge), target: str(o.target ?? o.to), reason: str(o.reason) }
}

const failureOf = (a: unknown): SeedBoardFailure => {
  if (Array.isArray(a)) return { key: str(a[0]), error: str(a[1]) }
  const o = isObj(a) ? a : {}
  return { key: str(o.key), error: str(o.error) }
}

const summarize = (
  nodes: SeedBoardNode[],
  stops: SeedBoardStop[],
  failures: SeedBoardFailure[],
  cycles: SeedBoardEdge[],
  given: Obj | undefined,
): SeedBoardSummary => ({
  visited: num(given?.visited, nodes.length),
  stopped: num(given?.stopped, stops.length),
  failed: num(given?.failed, failures.length),
  cycles: num(given?.cycles, cycles.length),
  external: num(given?.external, nodes.filter(n => n.status.startsWith('external')).length),
  notfound: num(given?.notfound, nodes.filter(n => n.status === 'notfound').length),
})

type RawWalk = {
  head: Obj
  nodes: SeedBoardNode[]
  items: SeedBoardItem[]
  dups: SeedBoardEdge[]
  cycles: SeedBoardEdge[]
  stops: SeedBoardStop[]
  failures: SeedBoardFailure[]
  summary: Obj | undefined
}

const finishWalk = (raw: RawWalk): ParsedWalk => ({
  id: need(raw.head.id, 'walk id'),
  at: need(raw.head.at, 'walk at'),
  start: need(raw.head.start, 'walk start'),
  maxDepth: num(raw.head.max_depth),
  maxNodes: num(raw.head.max_nodes),
  fingerprint: str(raw.head.fingerprint),
  nodes: raw.nodes,
  items: raw.items,
  dups: raw.dups,
  cycles: raw.cycles,
  stops: raw.stops,
  failures: raw.failures,
  summary: summarize(raw.nodes, raw.stops, raw.failures, raw.cycles, raw.summary),
})

/** The tab-separated records of `seed-relations.py walk` (lines it does not know are skipped). */
export const parseWalkText = (text: string): ParsedWalk => {
  const raw: RawWalk = {
    head: {}, nodes: [], items: [], dups: [], cycles: [], stops: [], failures: [], summary: undefined,
  }
  let isWalk = false
  for (const line of text.split(/\r?\n/)) {
    const f = line.split('\t')
    switch (f[0]) {
      case 'WALK':
        raw.head = kv(f.slice(1))
        isWalk = true
        break
      case 'NODE': {
        const o = kv(f.slice(5))
        raw.nodes.push({
          key: need(f[3], 'node key'),
          depth: num(f[1]),
          relation: need(f[2], 'node relation'),
          status: need(f[4], 'node status'),
          via: parseVia(o.via),
          target: dash(o.target),
          refines: csv(o.refines),
          linkReason: textOrUnverified(o.link_reason),
          source: textOrUnverified(o.source),
          lifecycle: lifecycleOf({ state: o.lifecycle_state, outcome: o.lifecycle_outcome, reason: o.lifecycle_reason }),
          eligibility: eligibilityOf({
            eligible: textBool(o.eligible), reason: o.eligibility_reason,
            excluded_items: o.excluded_items === undefined ? undefined : csv(o.excluded_items),
            review_required: textBool(o.review_required),
          }),
        })
        break
      }
      case 'ITEM': {
        const o = kv(f.slice(3))
        raw.items.push({ owner: need(f[1], 'item owner'), id: need(f[2], 'item id'), refinedBy: csv(o.refined_by) })
        break
      }
      case 'DUP':
        raw.dups.push({ from: str(f[1]), edge: str(f[2]), to: str(f[3]) })
        break
      case 'CYCLE':
        raw.cycles.push({ from: str(f[1]), edge: str(f[2]), to: str(f[3]) })
        break
      case 'STOP':
        raw.stops.push({ from: str(f[1]), edge: str(f[2]), target: str(f[3]), reason: str(kv(f.slice(4)).reason) })
        break
      case 'FAILED':
        raw.failures.push({ key: str(f[1]), error: f.slice(2).join(' ') })
        break
      case 'SUMMARY':
        raw.summary = kv(f.slice(1))
        break
      default:
        break
    }
  }
  if (!isWalk) throw new Error('seed-board: no WALK record')
  return finishWalk(raw)
}

/** `seed-relations.py walk --json`. */
export const parseWalkJson = (text: string): ParsedWalk => {
  const root: unknown = JSON.parse(text)
  if (!isObj(root) || !isObj(root.walk) || !Array.isArray(root.nodes)) throw new Error('seed-board: not a walk')
  const nodes = root.nodes.map((n): SeedBoardNode => {
    const o = isObj(n) ? n : {}
    return {
      key: need(o.key, 'node key'),
      depth: num(o.depth),
      relation: need(o.relation, 'node relation'),
      status: need(o.status, 'node status'),
      via: parseVia(o.via),
      target: dash(o.target),
      refines: strList(o.refines),
      linkReason: textOrUnverified(o.link_reason),
      source: textOrUnverified(o.source),
      lifecycle: lifecycleOf(o.lifecycle),
      eligibility: eligibilityOf(o.eligibility),
    }
  })
  const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
  return finishWalk({
    head: root.walk,
    nodes,
    items: list(root.items).map((i): SeedBoardItem => {
      const o = isObj(i) ? i : {}
      return { owner: need(o.owner, 'item owner'), id: need(o.id, 'item id'), refinedBy: strList(o.refined_by) }
    }),
    dups: list(root.dups).map(edgeOf),
    cycles: list(root.cycles).map(edgeOf),
    stops: list(root.stops).map(stopOf),
    failures: list(root.failures).map(failureOf),
    summary: isObj(root.summary) ? root.summary : undefined,
  })
}

/** Output of `walk` as the model read it: JSON when it opens with `{`, tab records otherwise. */
export const parseWalk = (text: string): ParsedWalk =>
  text.trimStart().startsWith('{') ? parseWalkJson(text) : parseWalkText(text)

/** The judgment JSON between a line ending `<<'JSON'` and a line that is exactly `JSON`. */
export const extractHeredoc = (command: string): string => {
  const lines = command.split(/\r?\n/)
  const open = lines.findIndex(l => l.trimEnd().endsWith("<<'JSON'"))
  if (open < 0) throw new Error('seed-board: no JSON heredoc')
  const close = lines.findIndex((l, i) => i > open && l === 'JSON')
  if (close < 0) throw new Error('seed-board: unterminated JSON heredoc')
  return lines.slice(open + 1, close).join('\n')
}

// Judgment prose collapses whitespace like next-goal-render.py, so pane labels and switch prompts stay one line.
const line = (v: unknown, fallback = ''): string => str(v, fallback).split(/\s+/).filter(Boolean).join(' ')
const needLine = (v: unknown, what: string): string => need(line(v), what)
const lineList = (v: unknown): string[] => strList(v).map(x => line(x))

const pickOf = (v: unknown): SeedBoardPick | null => {
  if (v === null || v === undefined) return null
  if (!isObj(v)) throw new Error('seed-board: pick is not an object')
  return {
    title: needLine(v.title, 'pick title'),
    via: needLine(v.via, 'pick via'),
    targets: strList(v.targets),
    evidence: line(v.evidence),
    startable: str(v.startable, 'unknown'),
    startable_reason: line(v.startable_reason),
    user_change: line(v.user_change),
    note: dash(line(v.note)),
  }
}

export const parseJudgment = (json: string): ParsedJudgment => {
  const root: unknown = JSON.parse(json)
  if (!isObj(root)) throw new Error('seed-board: judgment is not an object')
  const handoff = root.handoff
  if (handoff !== 'named' && handoff !== 'missing' && handoff !== 'none') {
    throw new Error('seed-board: judgment handoff is not named|missing|none')
  }
  // next-goal-render.py treats a missing list as empty; the board must read the same JSON the same way.
  const alternatives: unknown[] = root.alternatives === undefined ? [] : Array.isArray(root.alternatives) ? root.alternatives : []
  if (root.alternatives !== undefined && !Array.isArray(root.alternatives)) throw new Error('seed-board: judgment alternatives is not a list')
  return {
    seed: dash(root.seed),
    walk_id: dash(root.walk_id),
    handoff,
    pick: pickOf(root.pick),
    alternatives: alternatives.map((a): SeedBoardAlternative => {
      const o = isObj(a) ? a : {}
      return {
        title: needLine(o.title, 'alternative title'),
        via: needLine(o.via, 'alternative via'),
        decision: need(o.decision, 'alternative decision'),
        reason: line(o.reason),
      }
    }),
    unverified: lineList(root.unverified),
  }
}

/** The rendered lines (NEXT/FROM/SKIPPED/TRACE), kept as printed; only blank edges are dropped. */
export const renderedLines = (text: string): string[] => {
  const lines = text.split(/\r?\n/)
  while (lines.length > 0 && (lines[lines.length - 1] ?? '').trim() === '') lines.pop()
  while (lines.length > 0 && (lines[0] ?? '').trim() === '') lines.shift()
  return lines
}

/** ISO timestamps: later is greater. Falls back to string order when either does not parse. */
export const compareAt = (a: string, b: string): number => {
  const x = Date.parse(a)
  const y = Date.parse(b)
  if (Number.isFinite(x) && Number.isFinite(y)) return x === y ? 0 : x < y ? -1 : 1
  return a === b ? 0 : a < b ? -1 : 1
}

const norm = (p: string): string => p.replace(/^\.\//, '')

/** The stored walk a judgment's `seed` names: same path, or one is the tail of the other. */
export const walkFor = (
  walks: Record<string, SeedBoardWalk>,
  seed: string | null,
): SeedBoardWalk | undefined => {
  if (seed === null) return undefined
  const s = norm(seed)
  const exact = walks[seed] ?? walks[s]
  if (exact !== undefined) return exact
  return Object.values(walks).find(w => {
    const start = norm(w.start)
    return start.endsWith(`/${s}`) || s.endsWith(`/${start}`)
  })
}
