// Real `seed-relations.py walk` output (#792 fixture repo, start docs/specs/c1.yaml), captured
// verbatim so the parser is held to what the script prints, not to a hand-written imitation.
import { expect, test } from 'claude-code/testing'

import { isIndexCommand, parseIndex, parseJudgment, parseWalk } from './parse'

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

test('judgment prose collapses to one line like the renderer', () => {
  const j = parseJudgment(JSON.stringify({
    handoff: 'none',
    pick: { title: '첫 줄\n\n  둘째 줄', via: 'session', evidence: 'e\r\nf', startable: 'yes', startable_reason: 'r', user_change: 'u' },
    alternatives: [{ title: '외부\r\n선행', via: 'backlog', decision: 'held', reason: 'ready\n과 실제 증거' }],
    unverified: ['미확인\n외부'],
  }))
  expect(j.pick?.title).toBe('첫 줄 둘째 줄')
  expect(j.pick?.evidence).toBe('e f')
  expect(j.alternatives[0]?.title).toBe('외부 선행')
  expect(j.alternatives[0]?.reason).toBe('ready 과 실제 증거')
  expect(j.unverified).toEqual(['미확인 외부'])
})

test('STOP assertions use the same normalized judgment fields as the renderer', () => {
  const stop = { from: 'docs/specs/p.yaml\n', edge: 'children', target: 'docs/specs/x.yaml', reason: 'depth' }
  const root = { handoff: 'named', pick: null, walk_stops: [stop] }
  expect(parseJudgment(JSON.stringify(root)).walk_stops).toEqual([{ ...stop, from: 'docs/specs/p.yaml' }])
  expect(parseJudgment('{"handoff":"none"}').walk_stops).toEqual([])
  expect(() => parseJudgment(JSON.stringify({ ...root, handoff: 'none' }))).toThrow()
  for (const unverified of [[null], [42], [' \n '], 'gap']) {
    expect(() => parseJudgment(JSON.stringify({ handoff: 'none', unverified }))).toThrow()
  }
  expect(() => parseJudgment('{"handoff":"named","walk_stops":null}')).toThrow()
})

// Real `seed-relations.py index docs/specs --json [--full]` output (#897), captured verbatim from
// three claude-kit Seeds (paused, closed/completed, active) so the parser is held to what the script
// prints. The fixture has no declared edges; the register tests cover edge rows.
const REAL_INDEX_FULL = "{\"schema_version\": 1, \"generated_at\": \"2026-11-13T01:32:13Z\", \"seeds\": [{\"path\": \"docs/specs/build-spec-workflow-integration.yaml\", \"title\": \"build-spec-workflow-integration\", \"goal\": \"build-spec이 백로그 조회·독립 게이트 판정·맹점 패스로 포터블 Seed를 저작하고, 사용자 요청에 따라 issue-raise가 이를 GitHub 이슈 본문으로 내보내게 한...\", \"lifecycle\": {\"state\": \"paused\", \"outcome\": null, \"reason\": \"저작 소유권과 로컬 보조 도구는 확인했다. 실제 승인된 이슈 생성 URL·본문·백로그·STATE 검증이 남아 있고 외부 생성은 현재 로컬 수정 범위 밖이므로 보류한다.\", \"evidence\": {\"commit\": null, \"items\": [{\"id\": \"constraint-1\", \"refs\": [\"thinking-tools/skills/build-spec/SKILL.md\", \"thinking-tools/skills/issue-raise/SKILL.md\"]}, {\"id\": \"constraint-3\", \"refs\": [\"thinking-tools/skills/issue-raise/SKILL.md\", \"thinking-tools/skills/issue-raise/reference.md\"]}]}}, \"reason\": \"저작 소유권과 로컬 보조 도구는 확인했다. 실제 승인된 이슈 생성 URL·본문·백로그·STATE 검증이 남아 있고 외부 생성은 현재 로컬 수정 범위 밖이므로 보류한다.\", \"eligibility\": {\"eligible\": false, \"reason\": \"paused\", \"excluded_items\": [], \"review_required\": false, \"held_items\": [], \"errors\": []}, \"relations\": {\"parent\": null, \"refines\": [], \"depends_on\": [], \"children\": [], \"replaces\": [], \"transfers\": [], \"provenance\": [], \"link_reason\": null, \"refines_map\": []}, \"acceptance\": [{\"id\": \"acceptance-1\", \"satisfied\": false, \"out_of_scope\": null}, {\"id\": \"acceptance-2\", \"satisfied\": false, \"out_of_scope\": null}, {\"id\": \"acceptance-3\", \"satisfied\": false, \"out_of_scope\": null}, {\"id\": \"acceptance-4\", \"satisfied\": false, \"out_of_scope\": null}, {\"id\": \"acceptance-5\", \"satisfied\": false, \"out_of_scope\": null}], \"open_questions\": [], \"blindspots\": [], \"issues\": {\"source\": null, \"tracking\": []}, \"created\": \"2026-07-21\"}, {\"path\": \"docs/specs/claude-kit-work-rules.yaml\", \"title\": \"claude-kit-work-rules\", \"goal\": \"claude-kit 작업 시 지킬 규칙을, 새 플러그인/스킬/OMC 의존 없이 기존 native substrate (Claude Code hooks + scripts/check-*...\", \"lifecycle\": {\"state\": \"closed\", \"outcome\": \"completed\", \"reason\": \"철회하지 않은 constraint 7개와 success_criteria 5개가 지정 커밋에서 모두 충족됐다.\", \"evidence\": {\"commit\": \"b476edc72152d8a20cde8af70c30bb8cb0cda37f\", \"items\": [{\"id\": \"constraint-1\", \"refs\": [\"rules/RULES.md:14-24\"]}, {\"id\": \"constraint-2\", \"refs\": [\"rules/RULES.md:309\", \"#216 구현 커밋 02ad24a가 추가한 plugin.json·SKILL.md 0건(git show --diff-filter=A --name-only 02ad24a)\"]}, {\"id\": \"constraint-3\", \"refs\": [\"git grep -n -i -w -E 'omc|oh-my-claudecode' b476edc -- . ':!docs/specs' ':!docs/validation-*' ':!docs/design': 의존·import·경로 사용 0건, 매치 5건은 모두 설명 문장(.gitignore:52 무시 규칙, feedback-loop/README.md:5, feedback-loop/skills/distill/reference.md:14, thinking-tools/agents/thinking-facilitator.md:153, docs/native-instruction-risk-review.md:21)\"]}, {\"id\": \"constraint-4\", \"refs\": [\"scripts/run-linters.py:1-9\", \"ruff.toml:1-12\"]}, {\"id\": \"constraint-5\", \"refs\": [\"rules/RULES.md:204-222\", \"scripts/rules-checklist-hook.sh:39-44\"]}, {\"id\": \"constraint-6\", \"refs\": [\"rules/RULES.md:150\", \"ruff.toml:7-12\"]}, {\"id\": \"constraint-7\", \"refs\": [\"rules/rca-checklist.md:3-6\", \"rules/rca-checklist.md:37\"]}, {\"id\": \"acceptance-1\", \"refs\": [\"rules/RULES.md:299-317\"]}, {\"id\": \"acceptance-2\", \"refs\": [\"python3 scripts/check-test-exitcode.py: exit 0, 180개 등록 명령 전부 exit 0, 문서화된 stdout 전부 일치\", \"python3 scripts/check-banned-words.py --self-test: exit 0 (심은 위반 차단 + clean fixture)\", \"python3 scripts/check-type-optin.py --self-test: exit 0\", \"python3 scripts/test/test-rules-checklist-hook.py: exit 0 (작업끝 soft 리마인드)\"]}, {\"id\": \"acceptance-3\", \"refs\": [\"scripts/run-linters.py:1-9\", \"rules/RULES.md:314\"]}, {\"id\": \"acceptance-4\", \"refs\": [\"git grep -n -E 'line-length|quote-style|indent-width|max-line' b476edc -- scripts/: 스타일 상수 0건(scripts/check-hooks-installed.py:224는 설명 주석)\", \"ruff.toml:1-12\"]}, {\"id\": \"acceptance-5\", \"refs\": [\"git grep -n -i -w -E 'omc|oh-my-claudecode' b476edc -- . ':!docs/specs' ':!docs/validation-*' ':!docs/design': 의존·import·경로 사용 0건, 매치 5건은 모두 설명 문장(.gitignore:52 무시 규칙, feedback-loop/README.md:5, feedback-loop/skills/distill/reference.md:14, thinking-tools/agents/thinking-facilitator.md:153, docs/native-instruction-risk-review.md:21)\", \"#216 구현 커밋 02ad24a가 추가한 plugin.json·SKILL.md 0건(git show --diff-filter=A --name-only 02ad24a)\"]}]}}, \"reason\": \"철회하지 않은 constraint 7개와 success_criteria 5개가 지정 커밋에서 모두 충족됐다.\", \"eligibility\": {\"eligible\": false, \"reason\": \"lifecycle unverifiable\", \"excluded_items\": [], \"review_required\": true, \"held_items\": [], \"errors\": [\"evidence commit unverifiable: b476edc72152d8a20cde8af70c30bb8cb0cda37f (not a git repository)\"]}, \"relations\": {\"parent\": null, \"refines\": [], \"depends_on\": [], \"children\": [], \"replaces\": [], \"transfers\": [], \"provenance\": [], \"link_reason\": null, \"refines_map\": []}, \"acceptance\": [{\"id\": \"acceptance-1\", \"satisfied\": true, \"out_of_scope\": null}, {\"id\": \"acceptance-2\", \"satisfied\": true, \"out_of_scope\": null}, {\"id\": \"acceptance-3\", \"satisfied\": true, \"out_of_scope\": null}, {\"id\": \"acceptance-4\", \"satisfied\": true, \"out_of_scope\": null}, {\"id\": \"acceptance-5\", \"satisfied\": true, \"out_of_scope\": null}], \"open_questions\": [], \"blindspots\": [], \"issues\": {\"source\": \"#216\", \"tracking\": [\"#899\"]}, \"created\": \"2026-06-12\"}, {\"path\": \"docs/specs/expert-panel-delegated-mode.yaml\", \"title\": \"expert-panel 위임 실행 모드\", \"goal\": \"expert-panel 패널 실행에, 긴 토론 내용을 메인 문맥에서 분리하는 단일 worker 위임 경로를 선언된 모드로 제공한다. 패널 전체를 서브에이전트 한 개 안에서 돌리고 ...\", \"lifecycle\": {\"state\": \"active\", \"outcome\": null, \"reason\": \"위임·반환 계약, 정적 검사, 실제 worker 반환·호출자 relay·파일 작성은 확인했다. 메인 직접 실행과의 동일 조건 총비용·품질 비교(acceptance-1)가 남아 있어 활성 상태를 유지한다.\", \"evidence\": {\"commit\": \"61a808c7d435e26a30b0e335492c4d6a0eeb42c2\", \"items\": [{\"id\": \"constraint-1\", \"refs\": [\"thinking-tools/skills/expert-panel/SKILL.md:30\", \"thinking-tools/scripts/test/test-mode-compose.py:121\"]}, {\"id\": \"constraint-2\", \"refs\": [\"thinking-tools/agents/expert-panel-worker.md:67\"]}, {\"id\": \"constraint-5\", \"refs\": [\"thinking-tools/agents/expert-panel-worker.md:13\", \"scripts/check-agent-tools-field.py\"]}, {\"id\": \"acceptance-2\", \"refs\": [\"https://github.com/Lyainc/claude-kit/issues/864#issuecomment-6789912455\"]}, {\"id\": \"acceptance-3\", \"refs\": [\"thinking-tools/scripts/test/test-mode-compose.py\", \"scripts/check-agent-tools-field.py\", \"scripts/check-agent-tools-usage.py\", \"scripts/check-skill-token-budget.py\", \"scripts/check-version-sync.py\", \"vault-bridge/scripts/test/check-trigger-regression.py\"]}]}}, \"reason\": \"위임·반환 계약, 정적 검사, 실제 worker 반환·호출자 relay·파일 작성은 확인했다. 메인 직접 실행과의 동일 조건 총비용·품질 비교(acceptance-1)가 남아 있어 활성 상태를 유지한다.\", \"eligibility\": {\"eligible\": false, \"reason\": \"lifecycle unverifiable\", \"excluded_items\": [], \"review_required\": true, \"held_items\": [], \"errors\": [\"evidence commit unverifiable: 61a808c7d435e26a30b0e335492c4d6a0eeb42c2 (not a git repository)\"]}, \"relations\": {\"parent\": null, \"refines\": [], \"depends_on\": [], \"children\": [], \"replaces\": [], \"transfers\": [], \"provenance\": [], \"link_reason\": null, \"refines_map\": []}, \"acceptance\": [{\"id\": \"acceptance-1\", \"satisfied\": false, \"out_of_scope\": null}, {\"id\": \"acceptance-2\", \"satisfied\": true, \"out_of_scope\": null}, {\"id\": \"acceptance-3\", \"satisfied\": true, \"out_of_scope\": null}], \"open_questions\": [], \"blindspots\": [{\"area\": \"assumptions\", \"question\": \"위임 모드가 기존 넷과 나란히 추가되는 opt-in 불릿이라면, 트리거를 쓰지 않은 기본 호출은\\n여전히 메인 컨텍스트 비용을 그대로 지불하는가 — 즉 기본 경로를 위임으로 바꿀 것인가?\"}, {\"area\": \"trade-offs\", \"question\": \"위임이 세션당 1회성 호출이라면, 서브에이전트 캐시 TTL을 올려서 얻는 읽기 절감이 실현되는\\n호출 패턴은 어떤 것인가 — 그 패턴이 실제로 존재하는지 무엇으로 확인하는가?\"}, {\"area\": \"edge-cases\", \"question\": \"SKILL.md가 \\\"Modes compose silently with each other\\\"를 선언하는데, 위임 + 격리처럼 의미가\\n서로 부딪히는 조합의 실행 결과는 어떻게 정의되는가 — 트리거 충돌 가드는 문구만 보므로\\n의미 합성은 누가 막는가?\"}], \"issues\": {\"source\": \"#768\", \"tracking\": [\"#864\"]}, \"created\": \"2026-09-22\"}], \"edges\": {\"parent\": [], \"children\": [], \"depends_on\": [], \"replaces\": [], \"transfers\": [], \"provenance\": []}, \"errors\": [], \"schema\": \"seed-index-full/1\"}"
const REAL_INDEX_LIGHT = "{\"schema_version\": 1, \"generated_at\": \"2026-11-13T01:32:13Z\", \"seeds\": [{\"path\": \"docs/specs/build-spec-workflow-integration.yaml\", \"title\": \"build-spec-workflow-integration\", \"goal\": \"build-spec이 백로그 조회·독립 게이트 판정·맹점 패스로 포터블 Seed를 저작하고, 사용자 요청에 따라 issue-raise가 이를 GitHub 이슈 본문으로 내보내게 한...\", \"lifecycle\": {\"state\": \"paused\", \"outcome\": null, \"reason\": \"저작 소유권과 로컬 보조 도구는 확인했다. 실제 승인된 이슈 생성 URL·본문·백로그·STATE 검증이 남아 있고 외부 생성은 현재 로컬 수정 범위 밖이므로 보류한다.\"}, \"reason\": \"저작 소유권과 로컬 보조 도구는 확인했다. 실제 승인된 이슈 생성 URL·본문·백로그·STATE 검증이 남아 있고 외부 생성은 현재 로컬 수정 범위 밖이므로 보류한다.\", \"eligibility\": {\"eligible\": false, \"reason\": \"paused\", \"excluded_items\": [], \"review_required\": false, \"held_items\": [], \"errors\": []}, \"relations\": {\"parent\": null, \"refines\": [], \"depends_on\": [], \"children\": []}}, {\"path\": \"docs/specs/claude-kit-work-rules.yaml\", \"title\": \"claude-kit-work-rules\", \"goal\": \"claude-kit 작업 시 지킬 규칙을, 새 플러그인/스킬/OMC 의존 없이 기존 native substrate (Claude Code hooks + scripts/check-*...\", \"lifecycle\": {\"state\": \"closed\", \"outcome\": \"completed\", \"reason\": \"철회하지 않은 constraint 7개와 success_criteria 5개가 지정 커밋에서 모두 충족됐다.\"}, \"reason\": \"철회하지 않은 constraint 7개와 success_criteria 5개가 지정 커밋에서 모두 충족됐다.\", \"eligibility\": {\"eligible\": false, \"reason\": \"lifecycle unverifiable\", \"excluded_items\": [], \"review_required\": true, \"held_items\": [], \"errors\": [\"evidence commit unverifiable: b476edc72152d8a20cde8af70c30bb8cb0cda37f (not a git repository)\"]}, \"relations\": {\"parent\": null, \"refines\": [], \"depends_on\": [], \"children\": []}}, {\"path\": \"docs/specs/expert-panel-delegated-mode.yaml\", \"title\": \"expert-panel 위임 실행 모드\", \"goal\": \"expert-panel 패널 실행에, 긴 토론 내용을 메인 문맥에서 분리하는 단일 worker 위임 경로를 선언된 모드로 제공한다. 패널 전체를 서브에이전트 한 개 안에서 돌리고 ...\", \"lifecycle\": {\"state\": \"active\", \"outcome\": null, \"reason\": \"위임·반환 계약, 정적 검사, 실제 worker 반환·호출자 relay·파일 작성은 확인했다. 메인 직접 실행과의 동일 조건 총비용·품질 비교(acceptance-1)가 남아 있어 활성 상태를 유지한다.\"}, \"reason\": \"위임·반환 계약, 정적 검사, 실제 worker 반환·호출자 relay·파일 작성은 확인했다. 메인 직접 실행과의 동일 조건 총비용·품질 비교(acceptance-1)가 남아 있어 활성 상태를 유지한다.\", \"eligibility\": {\"eligible\": false, \"reason\": \"lifecycle unverifiable\", \"excluded_items\": [], \"review_required\": true, \"held_items\": [], \"errors\": [\"evidence commit unverifiable: 61a808c7d435e26a30b0e335492c4d6a0eeb42c2 (not a git repository)\"]}, \"relations\": {\"parent\": null, \"refines\": [], \"depends_on\": [], \"children\": []}}], \"edges\": {\"parent\": [], \"children\": [], \"depends_on\": []}, \"errors\": []}"

test('real index --json --full parses every field the detail view reads', () => {
  const index = parseIndex(REAL_INDEX_FULL)
  expect(index.isFull).toBe(true)
  expect(index.errors).toEqual([])
  expect(index.seeds.map(s => [s.path, s.lifecycle.state, s.lifecycle.outcome])).toEqual([
    ['docs/specs/expert-panel-delegated-mode.yaml', 'active', null],
    ['docs/specs/build-spec-workflow-integration.yaml', 'paused', null],
    ['docs/specs/claude-kit-work-rules.yaml', 'closed', 'completed'],
  ])
  const [active, paused, closed] = index.seeds
  expect(paused?.eligibility).toEqual({ eligible: false, reason: 'paused', excludedItems: [], reviewRequired: false, heldItems: [] })
  expect(closed?.source).toBe('#216')
  expect(closed?.tracking).toEqual(['#899'])
  expect(closed?.acceptance).toHaveLength(5)
  expect(closed?.acceptance.every(a => a.satisfied)).toBe(true)
  expect(closed?.evidence.items).toHaveLength(12)
  expect(active?.acceptance.filter(a => a.satisfied)).toHaveLength(2)
  expect(active?.blindspots).toHaveLength(3)
  expect(active?.evidence.commit).toMatch(/^[0-9a-f]{40}$/)
})

test('real index --json (no --full) keeps the lifecycle and leaves the full-only fields empty', () => {
  const light = parseIndex(REAL_INDEX_LIGHT)
  const full = parseIndex(REAL_INDEX_FULL)
  expect(light.isFull).toBe(false)
  expect(light.seeds.map(s => [s.path, s.lifecycle, s.eligibility])).toEqual(
    full.seeds.map(s => [s.path, s.lifecycle, s.eligibility]),
  )
  expect(light.seeds.every(s => s.acceptance.length === 0 && s.blindspots.length === 0 && s.evidence.items.length === 0)).toBe(true)
})

test('an index with text around the JSON line (non-zero exit) still parses; other output does not', () => {
  expect(parseIndex(`Exit code 1\n${REAL_INDEX_LIGHT}\n`).seeds).toHaveLength(3)
  for (const bad of ['', 'no seeds here', '{"schema_version":2,"generated_at":"x","seeds":[]}', '{"schema_version":1,"seeds":[]}']) {
    expect(() => parseIndex(bad)).toThrow()
  }
  // A malformed seed row is dropped; the document itself still stands.
  expect(parseIndex('{"schema_version":1,"generated_at":"x","seeds":[{"title":"no path"}]}').seeds).toEqual([])
})

test('only the --json form of the index command is observed', () => {
  const base = 'python3 thinking-tools/scripts/seed-relations.py index docs/specs'
  expect(isIndexCommand(`${base} --json`)).toBe(true)
  expect(isIndexCommand(`${base} --json --full`)).toBe(true)
  expect(isIndexCommand(`${base} docs/other --full --json`)).toBe(true)
  expect(isIndexCommand(base)).toBe(false)
  expect(isIndexCommand('python3 thinking-tools/scripts/seed-relations.py walk docs/specs/a.yaml --json')).toBe(false)
})

test('index JSON with trailing text after it, and a malformed row, still parses the rest', () => {
  expect(parseIndex(`Exit code 1\n${REAL_INDEX_LIGHT}\nwarning: 1 Seed could not be read\n`).seeds).toHaveLength(3)
  const doc = JSON.parse(REAL_INDEX_FULL)
  doc.seeds.push({ title: 'no path' })
  doc.edges.replaces.push({ from: 'docs/specs/a.yaml' })
  const index = parseIndex(JSON.stringify(doc))
  expect(index.seeds).toHaveLength(3)
  expect(index.edges.replaces).toHaveLength(0)
})
