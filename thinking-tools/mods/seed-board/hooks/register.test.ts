// `claude plugin test thinking-tools/mods/seed-board`
//
// The hooks the test registers stand beneath the plugin, as the engine does: they answer the Bash
// tool call with scripted output and record `prompt.fill` / `ui.open`. Every file, process, model,
// agent and network call has no implementation here, so a mod that made one would see the call
// rejected and the test fail (checked by temporarily adding an `$.fs` call to a handler).
// A hook that throws is skipped by the engine and the tool result goes on unchanged, so the
// malformed-input test can show "unchanged, no throw" but cannot tell the mod's own try/catch
// from the engine's skip; the try/catch is there to keep the transcript free of fault lines.
import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { parseWalk } from './parse'

const SURFACES = ['terminal', 'desktop'] as const
const PLUGIN = 'seed-board'
const PANE = {
  title: 'Seed board',
  isFocused: false,
  bodyColumns: 100,
  placement: 'dock',
  scroll: { offset: 0, bodyRows: 30 },
  view: {},
} as const
const VIEWPORT = { columns: 100, rows: 40, isFullscreen: true }

const A = 'docs/specs/a.yaml'
const PARENT = 'docs/specs/parent.yaml'
const CHILD = 'docs/specs/child.yaml'
const PRE = 'docs/specs/pre.yaml'
const OUTSIDE = 'other-repo:docs/specs/x.yaml'

type WalkOpts = { id: string; at: string; start?: string; fingerprint?: string }

const walkText = ({ id, at, start = A, fingerprint = 'fp1' }: WalkOpts): string =>
  [
    `WALK\tid=${id}\tat=${at}\tstart=${start}\tmax_depth=3\tmax_nodes=25\tfingerprint=${fingerprint}`,
    `NODE\t0\tstart\t${start}\tok\tvia=-\ttarget=-\trefines=-\tlink_reason=미확인\tsource=미확인`,
    `NODE\t1\tancestor\t${PARENT}\tok\tvia=parent>${PARENT}\ttarget=c1\trefines=c1,c2\tlink_reason=상위 목표를 쪼갬\tsource=#701`,
    `NODE\t1\tdescendant\t${CHILD}\tok\tvia=child>${CHILD}\ttarget=ac1\trefines=-\tlink_reason=미확인\tsource=미확인`,
    `NODE\t1\tpredecessor\t${PRE}\tnotfound\tvia=predecessor>${PRE}\ttarget=-\trefines=-\tlink_reason=미확인\tsource=미확인`,
    `NODE\t2\tpredecessor\t${OUTSIDE}\texternal\tvia=predecessor>${PRE}>predecessor>${OUTSIDE}\ttarget=-\trefines=-\tlink_reason=다른 레포\tsource=#9`,
    `ITEM\t${PARENT}\tc1\trefined_by=${start}`,
    `ITEM\t${PARENT}\tc2\trefined_by=(none)`,
    `DUP\t${CHILD}\trefines\t${PARENT}`,
    `CYCLE\t${CHILD}\tparent\t${start}`,
    `STOP\t${CHILD}\tchild\tdocs/specs/deep.yaml\treason=depth`,
    `FAILED\t${PRE}\tcannot read`,
    'SUMMARY\tvisited=5\tstopped=1\tfailed=1\tcycles=1\texternal=1\tnotfound=1',
  ].join('\n')

const walkJson = ({ id, at, start = A, fingerprint = 'fp1' }: WalkOpts): string =>
  JSON.stringify({
    walk: { id, at, start, max_depth: 3, max_nodes: 25, fingerprint },
    nodes: [
      { key: start, depth: 0, relation: 'start', status: 'ok', via: [], target: null, refines: [], link_reason: '미확인', source: '미확인' },
      { key: PARENT, depth: 1, relation: 'ancestor', status: 'ok', via: [['parent', PARENT]], target: 'c1', refines: ['c1', 'c2'], link_reason: '상위 목표를 쪼갬', source: '#701' },
      { key: CHILD, depth: 1, relation: 'descendant', status: 'ok', via: [['child', CHILD]], target: 'ac1', refines: [], link_reason: '미확인', source: '미확인' },
      { key: PRE, depth: 1, relation: 'predecessor', status: 'notfound', via: [['predecessor', PRE]], target: null, refines: [], link_reason: '미확인', source: '미확인' },
      { key: OUTSIDE, depth: 2, relation: 'predecessor', status: 'external', via: [['predecessor', PRE], ['predecessor', OUTSIDE]], target: null, refines: [], link_reason: '다른 레포', source: '#9' },
    ],
    items: [
      { owner: PARENT, id: 'c1', refined_by: [start] },
      { owner: PARENT, id: 'c2', refined_by: [] },
    ],
    dups: [{ from: CHILD, edge: 'refines', to: PARENT }],
    cycles: [{ from: CHILD, edge: 'parent', to: start }],
    stops: [{ from: CHILD, edge: 'child', target: 'docs/specs/deep.yaml', reason: 'depth' }],
    failures: [{ key: PRE, error: 'cannot read' }],
    summary: { visited: 5, stopped: 1, failed: 1, cycles: 1, external: 1, notfound: 1 },
  })

const WALK_CMD = `python3 thinking-tools/scripts/seed-relations.py walk ${A}`
const WALK_JSON_CMD = `python3 thinking-tools/scripts/seed-relations.py walk ${A} --json`

type Pick = { title: string; via: string }
type JudgeOpts = { walkId: string | null; pick: Pick | null; alts?: { title: string; via: string; decision: string }[]; handoff?: string; seed?: string | null; unverified?: string[] }

const judgeCmd = ({ walkId, pick, alts = [], handoff = 'named', seed = A, unverified = [] }: JudgeOpts): string =>
  [
    'python3 thinking-tools/scripts/next-goal-render.py <<\'JSON\'',
    JSON.stringify({
      seed,
      walk_id: walkId,
      handoff,
      pick:
        pick === null
          ? null
          : { ...pick, targets: ['c1'], evidence: 'c1 아직 안 닫힘', startable: 'yes', startable_reason: '입력이 다 있어요', user_change: '없음' },
      alternatives: alts.map(a => ({ ...a, reason: `${a.title} 이유` })),
      unverified,
    }),
    'JSON',
  ].join('\n')

const judgeOut = (pick: Pick | null): string =>
  [
    pick === null ? 'NEXT 후보 없음' : `NEXT ${pick.title}`,
    pick === null ? 'FROM -' : `FROM ${A} > ${pick.via}`,
    'SKIPPED 다른 후보는 이유가 있어요',
    'TRACE walk visited=5',
  ].join('\n')

type Bench = {
  out: { text: string; isError: boolean; gate?: Promise<void>; started?: () => void }
  fills: { text: string; mode?: string }[]
  opens: { id: string; title?: string }[]
  forbidden: string[]
  fill: { isFilled: boolean }
}

const bench = (on: On): Bench => {
  const b: Bench = { out: { text: '', isError: false }, fills: [], opens: [], forbidden: [], fill: { isFilled: true } }
  mock.clock(on, { now: 1_000 })
  on('tool.call', { tool: 'Bash' }, async () => {
    const out = b.out
    out.started?.()
    if (out.gate) await out.gate
    return out.isError
      ? ({ isError: true, result: out.text, text: out.text } as never)
      : ({ result: { stdout: out.text, stderr: '', interrupted: false }, text: out.text } as never)
  })
  on('prompt.fill', (_$, e) => {
    b.fills.push({ text: e.text, mode: e.mode })
    return { isFilled: b.fill.isFilled }
  })
  on('ui.open', (_$, e) => {
    b.opens.push({ id: e.id, title: e.title })
    return { value: { isPlaced: true as const } }
  })
  const refuse = (noun: string) => {
    b.forbidden.push(noun)
    throw new Error(`seed-board must not call ${noun}`)
  }
  on('fs.*', () => refuse('fs'))
  on('process.*', () => refuse('process'))
  on('model.*', () => refuse('model'))
  on('agent.*', () => refuse('agent'))
  on('http.*', () => refuse('http'))
  return b
}

const bash = ($: Engine, b: Bench, command: string, text: string, isError = false) => {
  b.out = { text, isError }
  return $.tool.call({ tool: 'Bash', command })
}

const mountPane = ($: Engine, surface: (typeof SURFACES)[number]) =>
  $.ui.mount({ plugin: PLUGIN, surface, component: 'Pane', requestId: PLUGIN, props: PANE, viewport: VIEWPORT })

const texts = async (ui: { findAll: (q: { type: string }) => Promise<{ text: string }[]> }, type = 'Text') =>
  (await ui.findAll({ type })).map(x => x.text)

// What the pane shows, without the per-mount press handles that `drawn()` carries.
const shape = async (ui: Parameters<typeof texts>[0]) => ({
  texts: await texts(ui),
  buttons: await texts(ui, 'Button'),
})

for (const surface of SURFACES) {
  test(`1 walk text output becomes state and the pane shows nodes (${surface})`, async ($, on) => {
    const b = bench(on)
    const ran = await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    expect(ran.text).toBe(walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))

    const ui = await mountPane($, surface)
    const all = await texts(ui)
    expect(all).toContain(`Seed: ${A}`)
    expect(all).toContain('walk w1 · 2026-10-01T10:00:00Z · fingerprint fp1')
    expect(all).toContain('방문 5 · 중단 1 · 실패 1 · 순환 1 · 외부 1 · 없음 1')
    // Nodes are grouped: relation groups first, external node last.
    expect(all).toContain('출발 (1)')
    expect(all).toContain('조상 (1)')
    expect(all).toContain('하위 (1)')
    expect(all).toContain('선행 (1)')
    expect(all).toContain('다른 레포 (1)')
    const buttons = (await ui.findAll({ type: 'Button' })).map(x => x.key)
    expect(buttons).toEqual([A, PARENT, CHILD, PRE, OUTSIDE].map(k => `node:${k}`))

    // Expanding is a state write: the details appear, nothing else happens.
    await ui.press({ key: `node:${PARENT}` })
    const open = await texts(ui)
    expect(open).toContain('경로: parent → docs/specs/parent.yaml')
    expect(open).toContain('대상: c1')
    expect(open).toContain('refines: c1, c2')
    expect(open).toContain('링크 이유: 상위 목표를 쪼갬')
    expect(open).toContain('출처: #701')
    expect(open).toContain(`c1 → refined by ${A}`)
    expect(open).toContain('c2 → refined by (none)')
    await ui.press({ key: `node:${CHILD}` })
    const child = await texts(ui)
    expect(child).toContain('링크 이유: 미확인')
    expect(child).toContain('멈춤: child → docs/specs/deep.yaml (reason=depth)')
    expect(child).toContain(`순환: parent → ${A}`)
    expect(child).toContain(`중복: refines → ${PARENT}`)
    await ui.press({ key: `node:${PRE}` })
    expect(await texts(ui)).toContain('실패: cannot read')
    await ui.press({ key: `node:${PARENT}` })
    expect(await texts(ui)).not.toContain('대상: c1')
    expect(b.forbidden).toEqual([])
    await ui.unmount()
  })

  test(`2 JSON walk output gives the same nodes as the text form (${surface})`, async ($, on) => {
    const b = bench(on)
    const opts = { id: 'w1', at: '2026-10-01T10:00:00Z' }
    expect(parseWalk(walkJson(opts))).toEqual(parseWalk(walkText(opts)))

    await bash($, b, WALK_CMD, walkText(opts))
    const ui = await mountPane($, surface)
    await ui.press({ key: `node:${PARENT}` })
    await ui.press({ key: `node:${CHILD}` })
    await ui.press({ key: `node:${PRE}` })
    const fromText = await shape(ui)
    await ui.unmount()

    await bash($, b, WALK_JSON_CMD, walkJson(opts))
    const again = await mountPane($, surface)
    expect(await shape(again)).toEqual(fromText)
    await again.unmount()
  })

  test(`3 a rendered judgment is stored and the pane shows its lines verbatim (${surface})`, async ($, on) => {
    const b = bench(on)
    await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    const pick = { title: 'c1 닫기', via: PARENT }
    // Rendered output without the heredoc in the command: nothing is stored.
    await bash($, b, 'python3 thinking-tools/scripts/next-goal-render.py', judgeOut(pick))
    const ui0 = await mountPane($, surface)
    expect(await texts(ui0)).toContain('아직 next-goal 판단이 없어요.')
    await ui0.unmount()

    await bash($, b, judgeCmd({ walkId: 'w1', pick, alts: [{ title: '대안 하나', via: 'backlog', decision: 'held' }] }), judgeOut(pick))
    const ui = await mountPane($, surface)
    const all = await texts(ui)
    for (const line of judgeOut(pick).split('\n')) expect(all).toContain(line)
    expect(all).not.toContain('근거가 바뀐 이전 판단 — next-goal 재실행 필요')
    const buttons = (await ui.findAll({ type: 'Button' })).map(x => x.key)
    expect(buttons).toContain('cand:c1 닫기')
    expect(buttons).toContain('cand:대안 하나')
    // Candidate details come from the judgment only.
    await ui.press({ key: 'cand:c1 닫기' })
    const open = await texts(ui)
    expect(open).toContain('근거: c1 아직 안 닫힘')
    expect(open).toContain('착수 가능: yes — 입력이 다 있어요')
    await ui.press({ key: 'cand:대안 하나' })
    expect(await texts(ui)).toContain('결정: 보류 (held)')
    await ui.unmount()
  })

  test(`4 a late older walk does not overwrite a newer one (${surface})`, async ($, on) => {
    const b = bench(on)
    await bash($, b, WALK_CMD, walkText({ id: 'w2', at: '2026-10-01T12:00:00Z', fingerprint: 'new' }))
    await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z', fingerprint: 'old' }))
    const ui = await mountPane($, surface)
    const all = await texts(ui)
    expect(all).toContain('walk w2 · 2026-10-01T12:00:00Z · fingerprint new')
    expect(all).not.toContain('walk w1 · 2026-10-01T10:00:00Z · fingerprint old')
    // An equal-or-newer walk for the same start does replace it; another start stays.
    await bash($, b, WALK_CMD, walkText({ id: 'w3', at: '2026-10-01T12:00:00Z', fingerprint: 'same-at' }))
    expect(await texts(ui)).toContain('walk w3 · 2026-10-01T12:00:00Z · fingerprint same-at')
    await bash($, b, WALK_CMD, walkText({ id: 'x1', at: '2026-10-01T09:00:00Z', start: 'docs/specs/z.yaml' }))
    const both = await texts(ui)
    expect(both).toContain('walk x1 · 2026-10-01T09:00:00Z · fingerprint fp1')
    expect(both).toContain('다른 Seed 탐색 1개는 판단이 가리킬 때 보여요')
    await ui.unmount()
  })

  test(`5 a judgment on a different walk shows the stale badge (${surface})`, async ($, on) => {
    const b = bench(on)
    const pick = { title: 'c1 닫기', via: PARENT }
    await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    await bash($, b, judgeCmd({ walkId: 'w0', pick }), judgeOut(pick))
    const ui = await mountPane($, surface)
    expect(await texts(ui)).toContain('근거가 바뀐 이전 판단 — next-goal 재실행 필요')
    // The stale judgment is shown, not hidden.
    expect(await texts(ui)).toContain(`NEXT ${pick.title}`)

    await bash($, b, judgeCmd({ walkId: 'w1', pick }), judgeOut(pick))
    expect(await texts(ui)).not.toContain('근거가 바뀐 이전 판단 — next-goal 재실행 필요')

    // A late judgment from the older walk w0 must not cover the current one on w1.
    const old = { title: '옛 판단', via: CHILD }
    await bash($, b, judgeCmd({ walkId: 'w0', pick: old }), judgeOut(old))
    expect(await texts(ui)).toContain(`NEXT ${pick.title}`)
    expect(await texts(ui)).not.toContain(`NEXT ${old.title}`)

    // A newer walk later turns the same judgment stale.
    await bash($, b, WALK_CMD, walkText({ id: 'w9', at: '2026-10-01T11:00:00Z' }))
    expect(await texts(ui)).toContain('근거가 바뀐 이전 판단 — next-goal 재실행 필요')
    await ui.unmount()
  })

  test(`6 switching a candidate fills the prompt, waits, then resolves (${surface})`, async ($, on) => {
    const b = bench(on)
    const first = { title: 'c1 닫기', via: PARENT }
    const alt = { title: 'ac1 하기', via: CHILD }
    await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    await bash(
      $,
      b,
      judgeCmd({
        walkId: 'w1',
        pick: first,
        alts: [
          { ...alt, decision: 'held' },
          { title: '밖의 일', via: OUTSIDE, decision: 'external' },
          { title: '이미 끝난 일', via: A, decision: 'done' },
        ],
      }),
      judgeOut(first),
    )
    const ui = await mountPane($, surface)
    // Only a non-external, non-done alternative has the button; the pick itself never does.
    const keys = (await ui.findAll({ type: 'Button' })).map(x => x.key)
    expect(keys).toContain('switch:0')
    expect(keys).not.toContain('switch:1')
    expect(keys).not.toContain('switch:2')

    // The box refuses the text: nothing is pending.
    b.fill.isFilled = false
    await ui.press({ key: 'switch:0' })
    expect(b.fills).toHaveLength(1)
    expect(await texts(ui)).not.toContain(`반영 대기 — 프롬프트를 보내면 next-goal이 다시 판단해요 (${alt.title})`)

    b.fill.isFilled = true
    await ui.press({ key: 'switch:0' })
    expect(b.fills).toHaveLength(2)
    expect(b.fills[1]).toEqual({ text: `next-goal: 후보를 ${alt.title} (via ${alt.via})로 바꿔줘 [walk w1]`, mode: 'replace' })
    expect(await texts(ui)).toContain(`반영 대기 — 프롬프트를 보내면 next-goal이 다시 판단해요 (${alt.title})`)
    expect(b.opens).toEqual([])

    // next-goal picks the requested candidate: applied.
    await bash($, b, judgeCmd({ walkId: 'w1', pick: alt, alts: [{ ...first, decision: 'held' }] }), judgeOut(alt))
    const done = await texts(ui)
    expect(done).toContain(`반영 완료 — ${alt.title}`)
    expect(done.some(t => t.startsWith('반영 대기'))).toBe(false)

    // Ask for the first one back; next-goal keeps `alt`: not applied.
    await ui.press({ key: 'switch:0' })
    expect(b.fills[2]?.text).toBe(`next-goal: 후보를 ${first.title} (via ${first.via})로 바꿔줘 [walk w1]`)
    expect(await texts(ui)).not.toContain(`반영 완료 — ${alt.title}`)
    await bash($, b, judgeCmd({ walkId: 'w1', pick: alt, alts: [{ ...first, decision: 'held' }] }), judgeOut(alt))
    const kept = await texts(ui)
    expect(kept).toContain(
      `반영 안 됨 — next-goal이 원래 후보를 유지했어요 (FROM/SKIPPED 이유 참고) (${first.title})`,
    )
    expect(kept.some(t => t.startsWith('반영 대기'))).toBe(false)

    // A different candidate on the same via (another item of the same Seed) is not the switch.
    const sibling = { title: 'c2 닫기', via: alt.via }
    await ui.press({ key: 'switch:0' })
    await bash($, b, judgeCmd({ walkId: 'w1', pick: sibling, alts: [{ ...first, decision: 'held' }] }), judgeOut(sibling))
    expect(await texts(ui)).toContain(
      `반영 안 됨 — next-goal이 원래 후보를 유지했어요 (FROM/SKIPPED 이유 참고) (${first.title})`,
    )
    // The mod never submits or runs anything else.
    expect(b.forbidden).toEqual([])
    await ui.unmount()
  })

  test(`handoff missing is shown apart from no candidate (${surface})`, async ($, on) => {
    const b = bench(on)
    await bash($, b, judgeCmd({ walkId: null, seed: null, pick: null, handoff: 'missing' }), judgeOut(null))
    const ui = await mountPane($, surface)
    const all = await texts(ui)
    expect(all).toContain('Seed 경로 인계 누락 — 후보 없음과 달라요')
    expect(all).not.toContain('고른 후보가 없어요.')
    await ui.unmount()
  })

  test(`no pick retains unevaluated scope without a Seed (${surface})`, async ($, on) => {
    const b = bench(on)
    const gap = '열린 이슈 비교: GitHub 리모트가 없어 조회 못 함'
    const output = [
      'NEXT     · 없음',
      'FROM     · 선택 없음 — 미평가 영역이 남아 후보 부재는 확정 못 함',
      'SKIPPED  · 없음',
      `TRACE    · Seed 탐색 없음 · 미확인: ${gap}`,
    ]
    await bash($, b, judgeCmd({ walkId: null, seed: null, pick: null, handoff: 'none', unverified: [gap] }), output.join('\n'))
    const ui = await mountPane($, surface)
    const all = await texts(ui)
    for (const line of output) expect(all).toContain(line)
    expect(all).toContain(`미확인: ${gap}`)
    expect(all).toContain('선택한 후보 없음 — 검토 범위와 미확인은 FROM/TRACE 참고')
    expect(all).not.toContain('Seed 경로 인계 누락 — 후보 없음과 달라요')
    await ui.unmount()
  })

  test(`9 expanding nodes and candidates calls no model, file or process API (${surface})`, async ($, on) => {
    const b = bench(on)
    const pick = { title: 'c1 닫기', via: PARENT }
    await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    await bash($, b, judgeCmd({ walkId: 'w1', pick, alts: [{ title: '대안', via: CHILD, decision: 'held' }] }), judgeOut(pick))
    const ui = await mountPane($, surface)
    for (const key of [A, PARENT, CHILD, PRE, OUTSIDE]) await ui.press({ key: `node:${key}` })
    await ui.press({ key: 'cand:c1 닫기' })
    await ui.press({ key: 'cand:대안' })
    expect(b.forbidden).toEqual([])
    expect(b.fills).toEqual([])
    expect(b.opens).toEqual([])
    await ui.unmount()
  })

  test(`empty pane says there is nothing yet (${surface})`, async ($, on) => {
    bench(on)
    const ui = await mountPane($, surface)
    expect(await texts(ui)).toEqual(['아직 Seed 탐색 결과가 없어요. next-goal이 Seed를 탐색하면 여기에 보여요.'])
    await ui.unmount()
  })
}

test('a long walk is capped to the viewport and says how many nodes are left', async ($, on) => {
  const b = bench(on)
  const many = Array.from({ length: 40 }, (_, i) =>
    `NODE\t1\tdescendant\tdocs/specs/n${i}.yaml\tok\tvia=child>docs/specs/n${i}.yaml\ttarget=-\trefines=-\tlink_reason=미확인\tsource=미확인`,
  )
  const lines = walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }).split('\n')
  await bash($, b, WALK_CMD, [...lines.slice(0, 1), ...many, ...lines.slice(1)].join('\n'))
  const ui = await mountPane($, 'terminal')
  const buttons = await ui.findAll({ type: 'Button' })
  expect(buttons.length).toBeLessThan(40)
  const note = (await texts(ui)).find(t => t.startsWith('… 노드 '))
  expect(note).toBeDefined()
  // 40 generated nodes plus the 5 of the fixture: shown + "N more" accounts for all of them.
  expect(buttons.length + Number((note ?? '').replace(/\D/g, ''))).toBe(45)
  await ui.unmount()
})

for (const surface of SURFACES) {
  test(`closed and review-required Seeds stay discoverable with observed lifecycle details (${surface})`, async ($, on) => {
    const b = bench(on)
    const text = walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }).split('\n').map(line => {
      if (line.includes(`\t${PARENT}\tok\t`)) return `${line}\tlifecycle_state=closed\tlifecycle_outcome=discontinued\tlifecycle_reason=방향 변경\teligible=false\teligibility_reason=closed: discontinued\texcluded_items=c1\treview_required=false`
      if (line.includes(`\t${CHILD}\tok\t`)) return `${line}\tlifecycle_state=active\tlifecycle_outcome=-\tlifecycle_reason=-\teligible=false\teligibility_reason=parent discontinued; child review required\texcluded_items=ac1\treview_required=true`
      return line
    }).join('\n')
    await bash($, b, WALK_CMD, text)
    const ui = await mountPane($, surface)
    await ui.press({ key: `node:${PARENT}` })
    await ui.press({ key: `node:${CHILD}` })
    const all = await texts(ui)
    expect(all).toContain('상태: closed · 결과: discontinued · 이유: 방향 변경')
    expect(all).toContain('후보 자격: 보류 · 이유: closed: discontinued')
    expect(all).toContain('제외 항목: c1 · 검토 필요: 아니요')
    expect(all).toContain('제외 항목: ac1 · 검토 필요: 예')
    expect(b.forbidden).toEqual([])
    expect(b.fills).toEqual([])
    await ui.unmount()
  })
}

test('7 malformed output or heredoc leaves the tool result unchanged and does not throw', async ($, on) => {
  const b = bench(on)
  const cases: [string, string][] = [
    [WALK_CMD, 'not a walk at all'],
    [WALK_CMD, 'WALK\tid=\tat=\tstart='],
    [WALK_JSON_CMD, '{ "walk": '],
    [WALK_JSON_CMD, '{"nope": true}'],
    ['python3 thinking-tools/scripts/next-goal-render.py <<\'JSON\'\n{"seed":\nJSON', 'NEXT x'],
    ['python3 thinking-tools/scripts/next-goal-render.py <<\'JSON\'\n{"handoff":"named"}', 'NEXT x'],
    ['python3 thinking-tools/scripts/next-goal-render.py <<\'JSON\'\n{"handoff":"sideways","alternatives":[]}\nJSON', 'NEXT x'],
    ['python3 thinking-tools/scripts/next-goal-render.py', 'NEXT x'],
  ]
  for (const [command, text] of cases) {
    const ran = await bash($, b, command, text)
    expect(ran.text).toBe(text)
    expect(ran.isError).toBeUndefined()
  }
  // A failed command is never parsed, even when it looks like a walk.
  const failed = await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }), true)
  expect(failed.isError).toBe(true)
  expect(failed.text).toBe(walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))

  const ui = await mountPane($, 'terminal')
  expect(await texts(ui)).toEqual(['아직 Seed 탐색 결과가 없어요. next-goal이 Seed를 탐색하면 여기에 보여요.'])
  await ui.unmount()
})

test('8 a command that does not match is untouched', async ($, on) => {
  const b = bench(on)
  for (const command of ['ls -la', 'python3 other.py walk', 'echo seed-relations walk', 'cat next-goal-render.md']) {
    const ran = await bash($, b, command, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    expect(ran.text).toBe(walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
    expect(ran.deny).toBeUndefined()
    expect(ran.isError).toBeUndefined()
  }
  const ui = await mountPane($, 'terminal')
  expect(await texts(ui)).toEqual(['아직 Seed 탐색 결과가 없어요. next-goal이 Seed를 탐색하면 여기에 보여요.'])
  await ui.unmount()
})

test('the pane opens only when the person runs the command', async ($, on) => {
  const b = bench(on)
  on('command.register', () => ({ value: { command: PLUGIN } }))
  on('session.start', (_$, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/work', surface: 'terminal', isInteractive: true })
  expect(b.opens).toEqual([])

  const ran = await $.command.run({
    command: PLUGIN,
    args: '',
    origin: { kind: 'plugin', name: 'test' },
    presentation: { isFullscreen: true, columns: 100 },
  })
  expect(ran.text).toBe('Seed board 패널을 열었어요.')
  expect(b.opens).toEqual([{ id: PLUGIN, title: 'Seed board' }])
  expect(b.forbidden).toEqual([])
})

// A run that started earlier but finishes later is held open here; `b.out` is read when the
// renderer call starts, so the gate belongs to that run only.
const gatedRun = async ($: Engine, b: Bench, command: string, text: string) => {
  let release!: () => void
  let ready!: () => void
  const gate = new Promise<void>(r => {
    release = r
  })
  const entered = new Promise<void>(r => {
    ready = r
  })
  b.out = { text, isError: false, gate, started: ready }
  const done = $.tool.call({ tool: 'Bash', command })
  await entered
  return { release, done }
}

test('a late judgment of an earlier run for another Seed does not replace the newer judgment', async ($, on) => {
  const b = bench(on)
  const z = 'docs/specs/z.yaml'
  await bash($, b, WALK_CMD, walkText({ id: 'wa', at: '2026-10-01T10:00:00Z' }))
  await bash($, b, WALK_CMD, walkText({ id: 'wz', at: '2026-10-01T12:00:00Z', start: z }))
  const newer = { title: 'newer Z judgment', via: z }
  const older = { title: 'older A judgment', via: A }
  const late = await gatedRun($, b, judgeCmd({ walkId: 'wa', seed: A, pick: older }), judgeOut(older))
  await bash($, b, judgeCmd({ walkId: 'wz', seed: z, pick: newer }), judgeOut(newer))
  late.release()
  await late.done
  const ui = await mountPane($, 'terminal')
  expect(await texts(ui)).toContain('NEXT newer Z judgment')
  expect(await texts(ui)).not.toContain('NEXT older A judgment')
  await ui.unmount()
})

test('a late judgment of an earlier run for the same Seed does not replace the newer judgment', async ($, on) => {
  const b = bench(on)
  await bash($, b, WALK_CMD, walkText({ id: 'wa', at: '2026-10-01T10:00:00Z' }))
  const newer = { title: 'newer A judgment', via: A }
  const older = { title: 'older A judgment', via: A }
  const late = await gatedRun($, b, judgeCmd({ walkId: 'wa', seed: A, pick: older }), judgeOut(older))
  await bash($, b, judgeCmd({ walkId: 'wa', seed: A, pick: newer }), judgeOut(newer))
  late.release()
  await late.done
  const ui = await mountPane($, 'terminal')
  expect(await texts(ui)).toContain('NEXT newer A judgment')
  expect(await texts(ui)).not.toContain('NEXT older A judgment')
  await ui.unmount()
})

test('a run started before the switch request does not resolve the pending switch', async ($, on) => {
  const b = bench(on)
  const first = { title: 'c1 닫기', via: PARENT }
  const alt = { title: 'ac1 하기', via: CHILD }
  await bash($, b, WALK_CMD, walkText({ id: 'w1', at: '2026-10-01T10:00:00Z' }))
  await bash($, b, judgeCmd({ walkId: 'w1', pick: first, alts: [{ ...alt, decision: 'held' }] }), judgeOut(first))
  const ui = await mountPane($, 'terminal')
  const late = await gatedRun($, b, judgeCmd({ walkId: 'w1', pick: first, alts: [{ ...alt, decision: 'held' }] }), judgeOut(first))
  await ui.press({ key: 'switch:0' })
  late.release()
  await late.done
  await bash($, b, judgeCmd({ walkId: 'w1', pick: alt, alts: [{ ...first, decision: 'held' }] }), judgeOut(alt))
  const t = await texts(ui)
  expect(t).toContain(`반영 완료 — ${alt.title}`)
  expect(t.some(x => x.includes('반영 안 됨'))).toBe(false)
  await ui.unmount()
})
