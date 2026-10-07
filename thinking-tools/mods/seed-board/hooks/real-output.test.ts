// Real `seed-relations.py walk` output (#792 fixture repo, start docs/specs/c1.yaml), captured
// verbatim so the parser is held to what the script prints, not to a hand-written imitation.
import { expect, test } from 'claude-code/testing'

import { parseWalk } from './parse'

const REAL_TEXT = "WALK\tid=local@6cbbc5f96218:docs/specs/c1.yaml#9b7bc11e.770ba239~d3n25\tat=2026-10-02T08:23:27Z\tstart=docs/specs/c1.yaml\tmax_depth=3\tmax_nodes=25\tfingerprint=770ba239be7a\nNODE\t0\tstart\tdocs/specs/c1.yaml\tok\tvia=-\ttarget=csv-parser\trefines=ac1\tlink_reason=부모 ac1의 파서 입력 형식을 정한다\tsource=#10\ttracking=#12\titems=ac1\tchildren=-\nNODE\t1\tancestor\tdocs/specs/p.yaml\tok\tvia=parent>docs/specs/p.yaml\ttarget=report-tool\trefines=-\tlink_reason=-\tsource=#10\ttracking=#11\titems=ac1,ac2,ac3\tchildren=docs/specs/c1.yaml,docs/specs/c2.yaml\nNODE\t2\tancestor-child\tdocs/specs/c2.yaml\tok\tvia=parent>docs/specs/p.yaml>children>docs/specs/c2.yaml\ttarget=report-writer\trefines=ac2\tlink_reason=미확인\tsource=미확인\ttracking=-\titems=ac1\tchildren=-\nNODE\t3\tpredecessor\tdocs/specs/pre.yaml\tok\tvia=parent>docs/specs/p.yaml>children>docs/specs/c2.yaml>depends_on>docs/specs/pre.yaml\ttarget=template-loader\trefines=-\tlink_reason=-\tsource=미확인\ttracking=-\titems=ac1\tchildren=-\nITEM\tdocs/specs/p.yaml\tac1\trefined_by=docs/specs/c1.yaml\nITEM\tdocs/specs/p.yaml\tac2\trefined_by=docs/specs/c2.yaml\nITEM\tdocs/specs/p.yaml\tac3\trefined_by=(none)\nSUMMARY\tvisited=4\tstopped=0\tfailed=0\tcycles=0\texternal=0\tnotfound=0"
const REAL_JSON = "{\"walk\": {\"id\": \"local@6cbbc5f96218:docs/specs/c1.yaml#9b7bc11e.770ba239~d3n25\", \"at\": \"2026-10-02T08:23:27Z\", \"start\": \"docs/specs/c1.yaml\", \"max_depth\": 3, \"max_nodes\": 25, \"fingerprint\": \"770ba239be7a\"}, \"nodes\": [{\"key\": \"docs/specs/c1.yaml\", \"depth\": 0, \"relation\": \"start\", \"status\": \"ok\", \"via\": [], \"target\": \"csv-parser\", \"parent\": \"docs/specs/p.yaml\", \"refines\": [\"ac1\"], \"link_reason\": \"부모 ac1의 파서 입력 형식을 정한다\", \"source\": \"#10\", \"tracking\": [\"#12\"], \"items\": [\"ac1\"], \"children\": []}, {\"key\": \"docs/specs/p.yaml\", \"depth\": 1, \"relation\": \"ancestor\", \"status\": \"ok\", \"via\": [[\"parent\", \"docs/specs/p.yaml\"]], \"target\": \"report-tool\", \"parent\": null, \"refines\": [], \"link_reason\": null, \"source\": \"#10\", \"tracking\": [\"#11\"], \"items\": [\"ac1\", \"ac2\", \"ac3\"], \"children\": [\"docs/specs/c1.yaml\", \"docs/specs/c2.yaml\"]}, {\"key\": \"docs/specs/c2.yaml\", \"depth\": 2, \"relation\": \"ancestor-child\", \"status\": \"ok\", \"via\": [[\"parent\", \"docs/specs/p.yaml\"], [\"children\", \"docs/specs/c2.yaml\"]], \"target\": \"report-writer\", \"parent\": \"docs/specs/p.yaml\", \"refines\": [\"ac2\"], \"link_reason\": null, \"source\": null, \"tracking\": [], \"items\": [\"ac1\"], \"children\": []}, {\"key\": \"docs/specs/pre.yaml\", \"depth\": 3, \"relation\": \"predecessor\", \"status\": \"ok\", \"via\": [[\"parent\", \"docs/specs/p.yaml\"], [\"children\", \"docs/specs/c2.yaml\"], [\"depends_on\", \"docs/specs/pre.yaml\"]], \"target\": \"template-loader\", \"parent\": null, \"refines\": [], \"link_reason\": null, \"source\": null, \"tracking\": [], \"items\": [\"ac1\"], \"children\": []}], \"items\": [{\"owner\": \"docs/specs/p.yaml\", \"id\": \"ac1\", \"refined_by\": [\"docs/specs/c1.yaml\"]}, {\"owner\": \"docs/specs/p.yaml\", \"id\": \"ac2\", \"refined_by\": [\"docs/specs/c2.yaml\"]}, {\"owner\": \"docs/specs/p.yaml\", \"id\": \"ac3\", \"refined_by\": []}], \"dups\": [], \"cycles\": [], \"stops\": [], \"failures\": [], \"summary\": {\"visited\": 4, \"stopped\": 0, \"failed\": 0, \"cycles\": 0, \"external\": 0, \"notfound\": 0}}"

test('real walk text and JSON parse to the same walk', () => {
  const fromText = parseWalk(REAL_TEXT)
  expect(parseWalk(REAL_JSON)).toEqual(fromText)
  expect(fromText.nodes.map(n => [n.key, n.relation, n.depth])).toEqual([
    ['docs/specs/c1.yaml', 'start', 0],
    ['docs/specs/p.yaml', 'ancestor', 1],
    ['docs/specs/c2.yaml', 'ancestor-child', 2],
    ['docs/specs/pre.yaml', 'predecessor', 3],
  ])
})

// The same fixture after `seed-id-migrate.py --apply` (#805): new-form ids and the `item_desc` field
// the walk gained. The capture above stays as the legacy-id regression.
const REAL_TEXT_MIGRATED = "WALK\tid=local@d5bafc1dd481:docs/specs/c1.yaml#6fbeaf66.49d26613~d3n25\tat=2026-10-06T02:37:00Z\tstart=docs/specs/c1.yaml\tmax_depth=3\tmax_nodes=25\tfingerprint=49d266130363\nNODE\t0\tstart\tdocs/specs/c1.yaml\tok\tvia=-\ttarget=csv-parser\trefines=acceptance-1\tlink_reason=부모 acceptance-1의 파서 입력 형식을 정한다\tsource=#10\ttracking=#12\titems=acceptance-1\tchildren=-\nNODE\t1\tancestor\tdocs/specs/p.yaml\tok\tvia=parent>docs/specs/p.yaml\ttarget=report-tool\trefines=-\tlink_reason=-\tsource=#10\ttracking=#11\titems=acceptance-1,acceptance-2,acceptance-3\tchildren=docs/specs/c1.yaml,docs/specs/c2.yaml\nNODE\t2\tancestor-child\tdocs/specs/c2.yaml\tok\tvia=parent>docs/specs/p.yaml>children>docs/specs/c2.yaml\ttarget=report-writer\trefines=acceptance-2\tlink_reason=미확인\tsource=미확인\ttracking=-\titems=acceptance-1\tchildren=-\nNODE\t3\tpredecessor\tdocs/specs/pre.yaml\tok\tvia=parent>docs/specs/p.yaml>children>docs/specs/c2.yaml>depends_on>docs/specs/pre.yaml\ttarget=template-loader\trefines=-\tlink_reason=-\tsource=미확인\ttracking=-\titems=acceptance-1\tchildren=-\nITEM\tdocs/specs/p.yaml\tacceptance-1\trefined_by=docs/specs/c1.yaml\nITEM\tdocs/specs/p.yaml\tacceptance-2\trefined_by=docs/specs/c2.yaml\nITEM\tdocs/specs/p.yaml\tacceptance-3\trefined_by=(none)\nSUMMARY\tvisited=4\tstopped=0\tfailed=0\tcycles=0\texternal=0\tnotfound=0"
const REAL_JSON_MIGRATED = "{\"walk\": {\"id\": \"local@d5bafc1dd481:docs/specs/c1.yaml#6fbeaf66.49d26613~d3n25\", \"at\": \"2026-10-06T02:37:00Z\", \"start\": \"docs/specs/c1.yaml\", \"max_depth\": 3, \"max_nodes\": 25, \"fingerprint\": \"49d266130363\"}, \"nodes\": [{\"key\": \"docs/specs/c1.yaml\", \"depth\": 0, \"relation\": \"start\", \"status\": \"ok\", \"via\": [], \"target\": \"csv-parser\", \"parent\": \"docs/specs/p.yaml\", \"refines\": [\"acceptance-1\"], \"link_reason\": \"부모 acceptance-1의 파서 입력 형식을 정한다\", \"source\": \"#10\", \"tracking\": [\"#12\"], \"items\": [\"acceptance-1\"], \"item_desc\": {\"acceptance-1\": \"결과 1\"}, \"children\": []}, {\"key\": \"docs/specs/p.yaml\", \"depth\": 1, \"relation\": \"ancestor\", \"status\": \"ok\", \"via\": [[\"parent\", \"docs/specs/p.yaml\"]], \"target\": \"report-tool\", \"parent\": null, \"refines\": [], \"link_reason\": null, \"source\": \"#10\", \"tracking\": [\"#11\"], \"items\": [\"acceptance-1\", \"acceptance-2\", \"acceptance-3\"], \"item_desc\": {\"acceptance-1\": \"결과 1\", \"acceptance-2\": \"결과 2\", \"acceptance-3\": \"결과 3\"}, \"children\": [\"docs/specs/c1.yaml\", \"docs/specs/c2.yaml\"]}, {\"key\": \"docs/specs/c2.yaml\", \"depth\": 2, \"relation\": \"ancestor-child\", \"status\": \"ok\", \"via\": [[\"parent\", \"docs/specs/p.yaml\"], [\"children\", \"docs/specs/c2.yaml\"]], \"target\": \"report-writer\", \"parent\": \"docs/specs/p.yaml\", \"refines\": [\"acceptance-2\"], \"link_reason\": null, \"source\": null, \"tracking\": [], \"items\": [\"acceptance-1\"], \"item_desc\": {\"acceptance-1\": \"결과 1\"}, \"children\": []}, {\"key\": \"docs/specs/pre.yaml\", \"depth\": 3, \"relation\": \"predecessor\", \"status\": \"ok\", \"via\": [[\"parent\", \"docs/specs/p.yaml\"], [\"children\", \"docs/specs/c2.yaml\"], [\"depends_on\", \"docs/specs/pre.yaml\"]], \"target\": \"template-loader\", \"parent\": null, \"refines\": [], \"link_reason\": null, \"source\": null, \"tracking\": [], \"items\": [\"acceptance-1\"], \"item_desc\": {\"acceptance-1\": \"결과 1\"}, \"children\": []}], \"items\": [{\"owner\": \"docs/specs/p.yaml\", \"id\": \"acceptance-1\", \"refined_by\": [\"docs/specs/c1.yaml\"]}, {\"owner\": \"docs/specs/p.yaml\", \"id\": \"acceptance-2\", \"refined_by\": [\"docs/specs/c2.yaml\"]}, {\"owner\": \"docs/specs/p.yaml\", \"id\": \"acceptance-3\", \"refined_by\": []}], \"dups\": [], \"cycles\": [], \"stops\": [], \"failures\": [], \"summary\": {\"visited\": 4, \"stopped\": 0, \"failed\": 0, \"cycles\": 0, \"external\": 0, \"notfound\": 0}}"

test('real walk with migrated ids parses the same from text and JSON', () => {
  const fromText = parseWalk(REAL_TEXT_MIGRATED)
  expect(parseWalk(REAL_JSON_MIGRATED)).toEqual(fromText)
  expect(fromText.nodes.map(n => [n.key, n.relation, n.depth])).toEqual([
    ['docs/specs/c1.yaml', 'start', 0],
    ['docs/specs/p.yaml', 'ancestor', 1],
    ['docs/specs/c2.yaml', 'ancestor-child', 2],
    ['docs/specs/pre.yaml', 'predecessor', 3],
  ])
  expect(fromText.items.map(i => [i.owner, i.id])).toEqual([
    ['docs/specs/p.yaml', 'acceptance-1'],
    ['docs/specs/p.yaml', 'acceptance-2'],
    ['docs/specs/p.yaml', 'acceptance-3'],
  ])
})

test('legacy observations keep metadata but require lifecycle review', () => {
  const node = parseWalk(REAL_JSON).nodes[0]
  expect(node?.target).toBe('csv-parser')
  expect(node?.lifecycle).toEqual({ state: 'unknown', outcome: null, reason: null })
  expect(node?.eligibility).toEqual({ eligible: false, reason: '미확인', excludedItems: [], reviewRequired: true })
})

test('lifecycle and eligibility normalize identically from text and JSON', () => {
  const root = JSON.parse(REAL_JSON_MIGRATED)
  const statuses = [
    { lifecycle: { state: 'active', outcome: null, reason: null }, eligibility: { eligible: true, reason: 'active', excluded_items: ['acceptance-3'], review_required: false } },
    { lifecycle: { state: 'closed', outcome: 'completed', reason: 'verified' }, eligibility: { eligible: false, reason: 'closed: completed', excluded_items: [], review_required: false } },
    { lifecycle: { state: 'paused', outcome: null, reason: 'waiting' }, eligibility: { eligible: false, reason: 'paused', excluded_items: [], review_required: false } },
    { lifecycle: { state: 'active', outcome: null, reason: null }, eligibility: { eligible: false, reason: 'parent discontinued; child review required', excluded_items: ['acceptance-1'], review_required: true } },
  ]
  root.nodes.forEach((n: Record<string, unknown>, i: number) => Object.assign(n, statuses[i]))
  let index = 0
  const text = REAL_TEXT_MIGRATED.split('\n').map(line => {
    if (!line.startsWith('NODE\t')) return line
    const s = statuses[index++]!
    return `${line}\tlifecycle_state=${s.lifecycle.state}\tlifecycle_outcome=${s.lifecycle.outcome ?? '-'}\tlifecycle_reason=${s.lifecycle.reason ?? '-'}\teligible=${s.eligibility.eligible}\teligibility_reason=${s.eligibility.reason}\texcluded_items=${s.eligibility.excluded_items.join(',') || '-'}\treview_required=${s.eligibility.review_required}`
  }).join('\n')
  const fromText = parseWalk(text)
  expect(parseWalk(JSON.stringify(root))).toEqual(fromText)
  expect(fromText.nodes).toHaveLength(4)
  expect(fromText.nodes[1]?.lifecycle?.outcome).toBe('completed')
  expect(fromText.nodes[3]?.eligibility?.reviewRequired).toBe(true)
})

test('malformed eligibility never becomes selectable metadata', () => {
  const root = JSON.parse(REAL_JSON)
  root.nodes[0].eligibility = { eligible: 'true', excluded_items: [], review_required: false }
  expect(parseWalk(JSON.stringify(root)).nodes[0]?.eligibility?.eligible).toBe(false)
  expect(parseWalk(JSON.stringify(root)).nodes[0]?.eligibility?.reviewRequired).toBe(true)
})
