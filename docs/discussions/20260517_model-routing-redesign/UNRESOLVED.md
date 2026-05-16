# Model Routing Redesign Expert Panel - Unresolved Issues

**Date**: 2026-05-17
**Related**: [SUMMARY.md](SUMMARY.md)

---

## Issue 1: 커스텀 플러그인 에이전트 fork 동작 검증

> **폐기됨 (2026-05-17)** — SKILL.md `model:` frontmatter 발견(SUMMARY.md Addendum)으로 fork 기반 접근 자체가 불필요해짐. 확정 설계는 `docs/plans/model-routing-2026-05-17.md`(스킬별 `model:` 직접 지정). 아래 내용은 의사결정 trail 보존용.

**Origin**: Topic 1, Topic 4
**Status**: 폐기 — fork 미사용으로 무효

**문제**: `context: fork + agent: <name>` 메커니즘의 기존 사례는 `obsidian-vault-manager/skills/context/SKILL.md`의 `agent: Explore` 하나뿐이며, `Explore`는 Claude Code 내장 에이전트다. 커스텀 플러그인 에이전트(vault-file-organizer, vault-knowledge-manager, thinking-facilitator 등)를 `agent:` 값으로 지정했을 때 fork가 정상 동작하는지 검증된 바 없다.

**검증 방법**:
1. 단일 skill(예: archive)에 `context: fork` + `agent: vault-file-organizer`를 시범 적용
2. 해당 skill 호출 시 실제로 vault-file-organizer 에이전트(haiku)에서 실행되는지 확인
3. fork된 에이전트가 skill 본문 + 에이전트 fixed instruction을 모두 받는지 확인
4. cross-plugin 참조(`../../reference/`)가 fork 후 어느 `CLAUDE_PLUGIN_ROOT` 기준으로 해석되는지 확인

**실패 시 영향**: 트랙 B(fork-worthiness 라우팅) 전체 폐기. 트랙 A(facilitator model 변경)는 fork를 사용하지 않으므로 무영향.

**다음 단계**: Action Item #1. 다른 모든 트랙 B 작업의 선행 게이트.

---

## Issue 2: capture URL 캡처 비율 (p) 미측정

> **폐기됨 (2026-05-17)** — fork-worthiness 계산 자체가 무효(`model:` 직접 지정으로 전환). capture는 `model: haiku`로 확정. 아래 내용은 의사결정 trail 보존용.

**Origin**: Topic 2
**Status**: 폐기 — fork-worthiness 무효

**문제**: capture skill의 fork-worthiness는 URL 캡처 비율 p에 좌우된다 (`p·G > (1-p)·C_o`). p가 미지수인 한 capture를 always-fork할지, main context에 둘지 확정 불가. 잠정안은 always-fork to haiku.

**측정 제약**: telemetry `meta`에 URL 플래그를 넣는 것은 schema 변경이므로 W1 Phase Gate와 충돌(Topic 3 합의). telemetry 경로 사용 불가.

**대안**: `~/vault/00_Inbox/`의 기존 `capture-*.md` 파일을 1회 표본조사하여 본문이 URL 캡처인지 텍스트 메모인지 분류, p 추정.

**다음 단계**: Action Item #4.

---

## Issue 3: facilitator Haiku 라우팅 정확도 검증

**Origin**: Topic 4 / 2026-04-16 cost-optimization-panel UNRESOLVED Issue 2에서 승계
**Status**: 테스트 완료 (2026-05-17) — FAIL. facilitator는 sonnet 유지.

**문제**: thinking-facilitator를 sonnet→haiku로 다운그레이드하기 전, 경계 케이스에서의 라우팅 정확도를 검증해야 한다. 2026-04-16 패널에서 정의됐으나 미실행 상태로 남아 있다.

**검증 케이스** (2026-04-16 UNRESOLVED Issue 2에서 정의된 10개):
1. "이 설계를 여러 관점에서 깊이 분석해줘" → expert-panel vs thought-chain
2. "다양한 대안을 만들어줘" → diverse-sampling vs expert-panel
3. "이 문서 검토해줘" → doc-polish vs expert-panel
4. "블라인드스팟 찾고 문서화해줘" → thought-chain vs unknown-discovery + doc-concretize
5. 복합 신호: "브레인스토밍하면서 전문가 의견도 듣고 싶어"
6. 약신호: "이거 좀 봐줘" (모호한 요청)
7. 한국어/영어 혼용 트리거
8. 부정형: "전문가 토론 말고 다른 방법으로"
9. 연쇄 요청: "먼저 A하고 그다음 B해줘"
10. 무관한 요청: thinking-tools 범위 밖 요청의 적절한 거부

**기준**: 10개 중 9.5개 이상 정확 (95%).

**테스트 결과 (2026-05-17)**: 10개 경계케이스를 haiku(후보)·sonnet(현행) 블라인드 라우팅으로 대조.

| 모델 | 정확 | 판정 |
|------|------|------|
| haiku | 7/10 (70%) | 게이트 미달 |
| sonnet | 9/10 (90%) | 게이트 근접 (Case 1만 오답) |

haiku가 sonnet 대비 놓친 결정적 2건:
- **Case 4** "블라인드스팟 찾고 문서화" — `unknown-discovery`를 `doc-polish`로 오분류 (신호 키워드 자체를 틀림)
- **Case 8** "전문가 토론 *말고*" — 명시적 부정을 무시하고 `expert-panel`로 라우팅 (부정형 처리 실패)

**판정**: haiku 70% << 95% 게이트 → **다운그레이드 FAIL**. thinking-facilitator는 `model: sonnet` 유지, Phase 2 종료. (테스트는 모델당 1회 실행 — 70 vs 95 격차가 충분히 커 결론은 안정적.) Case 1은 haiku·sonnet 공통 오답 → 모델 문제가 아닌 facilitator 정의 결함(Issue 5 참조).

---

## Issue 4: fork 오버헤드 (C_o) 정량값 미확보

> **폐기됨 (2026-05-17)** — fork 미사용으로 오버헤드 측정 자체가 불필요. 아래 내용은 의사결정 trail 보존용.

**Origin**: Topic 2
**Status**: 폐기 — fork 미사용

**문제**: fork-worthiness 부등식의 비용항 C_o(subagent 초기화 + 시스템프롬프트 재로드 오버헤드)가 정량화되지 않았다. 벤치마크는 모델 델타(opus vs haiku)를 측정하지만, fork 자체의 고정 오버헤드는 별도 항목이다.

**검증 방법**: 동일 작업을 (a) main context 직접 실행 (b) fork 후 실행으로 비교. 차이가 C_o의 추정치. Issue 1의 fork PoC와 동일 작업에 측정 항목으로 포함 가능.

**다음 단계**: Action Item #1(fork PoC) + #3(벤치마크)에 통합 측정.

---

## Issue 5: facilitator decision tree의 expert-panel↔thought-chain 미구분

**Origin**: Issue 3 테스트 (2026-05-17), Case 1
**Status**: 열림 — 모델 티어와 무관한 정의 결함

**문제**: "이 설계를 여러 관점에서 깊이 분석해줘"(Case 1)에서 haiku·sonnet **둘 다** thought-chain으로 오답했다. "여러 관점" → expert-panel이라는 MECE 규칙은 claude-kit `CLAUDE.md`에는 있으나 `thinking-tools/agents/thinking-facilitator.md`의 decision tree에는 인코딩돼 있지 않다. "여러 관점"(expert-panel)과 "깊이 분석"(thought-chain 약신호)이 동시에 등장할 때 facilitator 정의가 우선순위를 끊어주지 못한다.

**해결 방향**: facilitator decision tree 또는 signal table에 "여러 관점 → expert-panel 우선" 규칙을 명시. 모델 다운그레이드와 독립적으로 적용 가능.

---

*5개 이슈 -- 3개 폐기(`model:` 발견으로 무효), 1개 테스트 완료(Issue 3 — FAIL), 1개 신규 열림(Issue 5)*
