// seed-board: an optional, read-only board over what the Seed skills already print.
//
// Rules this module keeps (the README says why):
//  - It only OBSERVES. The tool.call hook awaits `next(e)` first and never denies or rewrites the
//    call; every parse sits in try/catch and a failure returns the tool result untouched.
//  - No $.fs / $.process / $.model / $.agent / $.http anywhere, and the render hook only reads
//    $.state. The only things it does besides state writes: register one command, open the pane
//    when the person asks, and fill (never submit) the prompt box when they press a button.
//  - It judges nothing: candidates, reasons and order come from next-goal's judgment as given.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type {
  SeedBoardJudgment,
  SeedBoardNode,
  SeedBoardWalk,
} from '../types/index'
import {
  compareAt,
  extractHeredoc,
  isRenderCommand,
  isWalkCommand,
  parseJudgment,
  parseWalk,
  renderedLines,
  walkFor,
} from './parse'

const PANE = 'seed-board'
const MAX_WALKS = 12

const walksA = atom({ plugin: 'seed-board', key: 'walks' } as const, {} as Record<string, SeedBoardWalk>)
const judgmentA = atom({ plugin: 'seed-board', key: 'judgment' } as const, null as SeedBoardJudgment | null)
const pendingA = atom(
  { plugin: 'seed-board', key: 'pending' } as const,
  null as { title: string; via: string; walk_id: string | null; requestedAt: number; seq?: number } | null,
)
const lastSwitchA = atom(
  { plugin: 'seed-board', key: 'lastSwitch' } as const,
  null as { title: string; via: string; result: 'applied' | 'not-applied'; at: number } | null,
)
const expandedA = atom({ plugin: 'seed-board', key: 'expanded' } as const, {} as Record<string, true>)
const seqA = atom({ plugin: 'seed-board', key: 'seq' } as const, 0)

type Dollar = Pick<EngineInterface, 'state' | 'clock'>

const REL_ORDER = ['start', 'ancestor', 'ancestor-child', 'descendant', 'predecessor'] as const
const REL_KO: Record<string, string> = {
  start: '출발',
  ancestor: '조상',
  'ancestor-child': '조상의 자식',
  descendant: '하위',
  predecessor: '선행',
  external: '다른 레포',
  other: '기타',
}
const DECISION_KO: Record<string, string> = {
  held: '보류',
  'below-floor': '바닥 미달',
  done: '이미 충족',
  external: '다른 레포 — 링크만',
  unverified: '미확인',
}
const NO_SWITCH = ['external', 'done']

export const STALE_BADGE = '근거가 바뀐 이전 판단 — next-goal 재실행 필요'
export const EMPTY_TEXT = '아직 Seed 탐색 결과가 없어요. next-goal이 Seed를 탐색하면 여기에 보여요.'
export const HANDOFF_MISSING = 'Seed 경로 인계 누락 — 후보 없음과 달라요'
export const PENDING_TEXT = '반영 대기 — 프롬프트를 보내면 next-goal이 다시 판단해요'
export const APPLIED_TEXT = '반영 완료'
export const NOT_APPLIED_TEXT = '반영 안 됨 — next-goal이 원래 후보를 유지했어요 (FROM/SKIPPED 이유 참고)'
export const SWITCH_LABEL = '이 후보로 바꾸기'

const keepNewest = (walks: Record<string, SeedBoardWalk>): Record<string, SeedBoardWalk> => {
  const all = Object.values(walks)
  if (all.length <= MAX_WALKS) return walks
  const keep = all.sort((a, b) => b.seq - a.seq).slice(0, MAX_WALKS)
  return Object.fromEntries(keep.map(w => [w.start, w]))
}

// `seq` is taken when the renderer call STARTS, so it is the run's start order, not the order its
// result arrives in. A result is applied only if no later-started run's result is already shown.
const isNewer = (j: SeedBoardJudgment, cur: SeedBoardJudgment): boolean => {
  // Different Seeds have no walk time to compare: start order alone decides, so a late result of an
  // earlier run for another Seed cannot cover the newer screen.
  if (cur.seed !== j.seed) return j.seq > cur.seq
  if (cur.walkAt !== null && j.walkAt !== null) {
    const c = compareAt(j.walkAt, cur.walkAt)
    if (c !== 0) return c > 0
  }
  // The shown judgment rests on the latest walk and this one does not: it is a late older run,
  // so it must not cover the newer screen.
  if (cur.walkAt !== null && j.walkAt === null) return false
  return j.seq > cur.seq
}

const observeWalk = async ($: Dollar, text: string): Promise<void> => {
  const parsed = parseWalk(text)
  const seq = await update($, seqA, n => n + 1)
  const walk: SeedBoardWalk = { ...parsed, seq }
  await update($, walksA, walks => {
    const prev = walks[walk.start]
    if (prev !== undefined && compareAt(prev.at, walk.at) > 0) return walks
    return keepNewest({ ...walks, [walk.start]: walk })
  })
}

const observeJudgment = async ($: Dollar, command: string, text: string, seq: number): Promise<void> => {
  const parsed = parseJudgment(extractHeredoc(command))
  const known = walkFor(await read($, walksA), parsed.seed)
  const j: SeedBoardJudgment = {
    ...parsed,
    lines: renderedLines(text),
    walkAt: known !== undefined && known.id === parsed.walk_id ? known.at : null,
    seq,
  }
  const verdict = { isAccepted: false }
  await update($, judgmentA, cur => {
    verdict.isAccepted = cur === null || isNewer(j, cur)
    return verdict.isAccepted ? j : cur
  })
  if (!verdict.isAccepted) return

  const pending = await read($, pendingA)
  if (pending === null) return
  // A run that started before the switch was requested cannot be its answer, even if it is shown.
  // A pending stored without `seq` (older state) keeps the earlier behaviour.
  if (pending.seq !== undefined && j.seq <= pending.seq) return
  // Title and via together: several candidates share one via (every item of one Seed, every
  // `session`/`backlog` candidate), so a via match alone would confirm a switch that did not happen.
  const isApplied = j.pick !== null && j.pick.title === pending.title && j.pick.via === pending.via
  const at = await $.clock.now()
  await update($, lastSwitchA, () => ({
    title: pending.title,
    via: pending.via,
    result: isApplied ? ('applied' as const) : ('not-applied' as const),
    at,
  }))
  await update($, pendingA, () => null)
}

const groupNodes = (nodes: SeedBoardNode[]): { id: string; nodes: SeedBoardNode[] }[] => {
  const known: readonly string[] = REL_ORDER
  const isExternal = (n: SeedBoardNode): boolean => n.status.startsWith('external')
  const groups = [
    ...REL_ORDER.map(id => ({ id: id as string, nodes: nodes.filter(n => n.relation === id && !isExternal(n)) })),
    { id: 'other', nodes: nodes.filter(n => !known.includes(n.relation) && !isExternal(n)) },
    { id: 'external', nodes: nodes.filter(isExternal) },
  ]
  return groups.filter(g => g.nodes.length > 0)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'seed-board',
      description: 'Seed 관계 트리와 next-goal 판단을 패널로 보여줘요 (읽기 전용)',
    })

    return next(e)
  })

  // Asked for by the person: the pane is never opened unasked.
  on('command.run', { command: 'seed-board' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Seed board' })

    return { text: 'Seed board 패널을 열었어요.' }
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    // The ordering token is taken before the renderer call runs: the call may finish after a later
    // one, and only its start order says which judgment is newer. Other commands pay nothing.
    let startSeq: number | null = null
    if (isRenderCommand(e.command)) {
      try {
        startSeq = await update($, seqA, n => n + 1)
      } catch {
        // No token, no judgment for this run; the call itself still goes on untouched.
      }
    }
    const ran = await next(e)
    if (ran.deny !== undefined || ran.isError === true || ran.text === undefined) return ran
    const text = ran.text

    if (isWalkCommand(e.command)) {
      try {
        await observeWalk($, text)
      } catch {
        // A board fault must never break the session: the result goes on as it was.
      }
    }
    if (startSeq !== null && text.trimStart().startsWith('NEXT')) {
      try {
        await observeJudgment($, e.command, text, startSeq)
      } catch {
        // Same: a malformed heredoc or judgment is skipped, not raised.
      }
    }

    return ran
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const walks = await read($, walksA)
    const judgment = await read($, judgmentA)
    const pending = await read($, pendingA)
    const lastSwitch = await read($, lastSwitchA)
    const expanded = await read($, expandedA)

    const rows = e.viewport?.rows ?? 24
    const treeRoom = Math.max(8, rows - 16)
    const candRoom = Math.max(8, Math.floor(rows / 2))
    const toggle = (k: string) => () =>
      update($, expandedA, cur => {
        const next = { ...cur }
        if (next[k] === true) delete next[k]
        else next[k] = true
        return next
      })

    const requestSwitch = (title: string, via: string) => async () => {
      const walkId = judgment?.walk_id ?? null
      const suffix = walkId === null ? '' : ` [walk ${walkId}]`
      const filled = await $.prompt.fill({
        text: `next-goal: 후보를 ${title} (via ${via})로 바꿔줘${suffix}`,
        mode: 'replace',
      })
      if (!filled.isFilled) return
      const requestedAt = await $.clock.now()
      // Same counter as the renderer runs: only a run that starts after this token can answer it.
      const seq = await update($, seqA, n => n + 1)
      await update($, lastSwitchA, () => null)
      await update($, pendingA, () => ({ title, via, walk_id: walkId, requestedAt, seq }))
    }

    const judged = judgment === null ? undefined : walkFor(walks, judgment.seed)
    const shown = judged ?? Object.values(walks).sort((a, b) => b.seq - a.seq)[0]
    const isStale =
      judgment !== null && judgment.walk_id !== null && judged !== undefined && judged.id !== judgment.walk_id

    if (shown === undefined && judgment === null) {
      return (
        <Box flexDirection="column">
          <Text dimColor>{EMPTY_TEXT}</Text>
        </Box>
      )
    }

    // Header
    const header: JSX.Element[] = []
    if (shown !== undefined) {
      const s = shown.summary
      header.push(<Text bold>{`Seed: ${shown.start}`}</Text>)
      header.push(<Text>{`walk ${shown.id} · ${shown.at} · fingerprint ${shown.fingerprint}`}</Text>)
      header.push(
        <Text>{`방문 ${s.visited} · 중단 ${s.stopped} · 실패 ${s.failed} · 순환 ${s.cycles} · 외부 ${s.external} · 없음 ${s.notfound}`}</Text>,
      )
      const others = Object.keys(walks).length - 1
      if (others > 0) header.push(<Text dimColor>{`다른 Seed 탐색 ${others}개는 판단이 가리킬 때 보여요`}</Text>)
    } else {
      header.push(<Text dimColor>이 판단이 가리키는 Seed 탐색 결과를 아직 못 봤어요.</Text>)
    }

    // 판단 요약
    const summary: JSX.Element[] = []
    if (judgment === null) {
      summary.push(<Text dimColor>아직 next-goal 판단이 없어요.</Text>)
    } else {
      if (isStale) summary.push(<Text color="yellow" bold>{STALE_BADGE}</Text>)
      for (const line of judgment.lines.slice(0, 12)) summary.push(<Text>{line}</Text>)
    }

    // 관계 트리
    const tree: JSX.Element[] = []
    if (shown === undefined) {
      tree.push(<Text dimColor>{EMPTY_TEXT}</Text>)
    } else {
      let seen = 0
      let hidden = 0
      for (const group of groupNodes(shown.nodes)) {
        const header = <Text bold>{`${REL_KO[group.id] ?? group.id} (${group.nodes.length})`}</Text>
        let isHeaderDrawn = false
        for (const n of group.nodes) {
          const k = `node:${n.key}`
          const isOpen = expanded[k] === true
          // The cap counts nodes, not detail lines: an opened node always shows whole.
          if (seen >= treeRoom && !isOpen) {
            hidden += 1
            continue
          }
          seen += 1
          if (!isHeaderDrawn) {
            tree.push(header)
            isHeaderDrawn = true
          }
          tree.push(
            <Box paddingLeft={Math.min(n.depth, 4) * 2}>
              <Button key={k} plain label={`${isOpen ? '▾' : '▸'} ${n.key} [${n.status}]`} onPress={toggle(k)} />
            </Box>,
          )
          if (!isOpen) continue
          const pad = Math.min(n.depth, 4) * 2 + 2
          const d = (text: string) => (
            <Box paddingLeft={pad}>
              <Text dimColor>{text}</Text>
            </Box>
          )
          tree.push(d(`경로: ${n.via.length === 0 ? '(출발점)' : n.via.map(([edge, key]) => `${edge} → ${key}`).join(' · ')}`))
          tree.push(d(`대상: ${n.target ?? '-'}`))
          tree.push(d(`refines: ${n.refines.length === 0 ? '-' : n.refines.join(', ')}`))
          tree.push(d(`링크 이유: ${n.linkReason}`))
          tree.push(d(`출처: ${n.source}`))
          for (const item of shown.items.filter(i => i.owner === n.key)) {
            tree.push(d(`${item.id} → refined by ${item.refinedBy.length === 0 ? '(none)' : item.refinedBy.join(', ')}`))
          }
          for (const s of shown.stops.filter(x => x.from === n.key)) {
            tree.push(d(`멈춤: ${s.edge} → ${s.target} (reason=${s.reason})`))
          }
          for (const c of shown.cycles.filter(x => x.from === n.key)) tree.push(d(`순환: ${c.edge} → ${c.to}`))
          for (const c of shown.dups.filter(x => x.from === n.key)) tree.push(d(`중복: ${c.edge} → ${c.to}`))
          for (const f of shown.failures.filter(x => x.key === n.key)) tree.push(d(`실패: ${f.error}`))
        }
      }
      if (hidden > 0) tree.push(<Text dimColor>{`… 노드 ${hidden}개 더 있어요`}</Text>)
    }

    // 후보
    const cands: JSX.Element[] = []
    if (judgment === null) {
      cands.push(<Text dimColor>아직 next-goal 판단이 없어요.</Text>)
    } else {
      if (judgment.handoff === 'missing') cands.push(<Text color="yellow" bold>{HANDOFF_MISSING}</Text>)
      if (pending !== null) {
        cands.push(<Text color="yellow">{`${PENDING_TEXT} (${pending.title})`}</Text>)
      } else if (lastSwitch !== null) {
        cands.push(
          lastSwitch.result === 'applied' ? (
            <Text color="green">{`${APPLIED_TEXT} — ${lastSwitch.title}`}</Text>
          ) : (
            <Text color="yellow">{`${NOT_APPLIED_TEXT} (${lastSwitch.title})`}</Text>
          ),
        )
      }
      const detail = (k: string, lines: string[]) =>
        expanded[k] === true
          ? lines.map(text => (
              <Box paddingLeft={4}>
                <Text dimColor>{text}</Text>
              </Box>
            ))
          : []
      const pick = judgment.pick
      if (pick === null) {
        if (judgment.handoff !== 'missing') cands.push(<Text dimColor>고른 후보가 없어요.</Text>)
      } else {
        const k = `cand:${pick.title}`
        cands.push(
          <Button
            key={k}
            plain
            label={`${expanded[k] === true ? '▾' : '▸'} 후보: ${pick.title} (via ${pick.via})`}
            onPress={toggle(k)}
          />,
        )
        cands.push(
          ...detail(k, [
            `via: ${pick.via}`,
            `대상: ${pick.targets.length === 0 ? '-' : pick.targets.join(', ')}`,
            `근거: ${pick.evidence}`,
            `착수 가능: ${pick.startable}${pick.startable_reason === '' ? '' : ` — ${pick.startable_reason}`}`,
            `사용자 변경: ${pick.user_change}`,
            ...(pick.note === null ? [] : [`메모: ${pick.note}`]),
          ]),
        )
      }
      let hiddenAlts = 0
      judgment.alternatives.forEach((alt, i) => {
        const k = `cand:${alt.title}`
        // Same rule as the tree: the cap counts candidates, an opened one always shows whole.
        if (i + 1 >= candRoom && expanded[k] !== true) {
          hiddenAlts += 1
          return
        }
        const decision = DECISION_KO[alt.decision] ?? alt.decision
        cands.push(
          <Box flexDirection="row" gap={1}>
            <Button
              key={k}
              plain
              label={`${expanded[k] === true ? '▾' : '▸'} 대안: ${alt.title} (via ${alt.via}) · ${decision}`}
              onPress={toggle(k)}
            />
            {!NO_SWITCH.includes(alt.decision) && (
              <Button key={`switch:${i}`} label={SWITCH_LABEL} onPress={requestSwitch(alt.title, alt.via)} />
            )}
          </Box>,
        )
        cands.push(...detail(k, [`via: ${alt.via}`, `결정: ${decision} (${alt.decision})`, `이유: ${alt.reason}`]))
      })
      if (hiddenAlts > 0) cands.push(<Text dimColor>{`… 대안 ${hiddenAlts}개 더 있어요`}</Text>)
      for (const u of judgment.unverified) cands.push(<Text dimColor>{`미확인: ${u}`}</Text>)
    }

    return (
      <Box flexDirection="column">
        {header}
        <Text bold>판단 요약</Text>
        {summary}
        <Text bold>관계 트리</Text>
        {tree}
        <Text bold>후보</Text>
        {cands}
      </Box>
    )
  })
}
