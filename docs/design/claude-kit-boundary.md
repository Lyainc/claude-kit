# claude-kit ↔ harness 경계 (진화형 경계 A) + Design Principles 단일 출처

**Status**: design (foundation) · **Created**: 2026-06-04 · **Issue**: #99 · **Epic**: #108
**Source**: `docs/discussions/20260602_claude-kit-layer-redesign/` (SUMMARY.md C-1, UNRESOLVED.md U-5) + `docs/adversarial-review/2026-06-03-harness-ownership.md`

> **이 문서는 단일 출처(single source of truth)예요.** claude-kit↔harness 경계, 5-레이어 모델, 의존 방향, 그리고 아래 `## Design Principles`의 **헌법(constitutional) / 정책(policy) 규칙 목록**은 여기서만 *정의*돼요. 다른 문서·이슈(#100 goal-doc 스키마, #122 thin 하네스, #125 3-tier 규칙 등)는 이 목록을 **참조만** 하고 재정의하지 않아요. CLAUDE.md operating_principles의 "State each rule once" 원칙을 이 문서가 구현해요. 규칙이 두 곳에 적히면 drift·모순이 나거든요.

---

## Design Principles

### 1. 경계 A (진화형) — 책임 분담 (수평축)

claude-kit은 **①인지 ②결정화·출력 ③딜리버리 ④지식베이스**를 소유해요. **⑤실행(doing/오케스트레이션)**은 정적 "⑤=OMC"가 아니라 **진화형**이에요:

> **현재** OMC(또는 Claude Code 네이티브)가 ⑤를 담당하나, claude-kit은 Claude Code 네이티브 기능(dynamic Workflow, `/goal`, agents, hooks)을 **substrate로 한 경량 하네스**로 ⑤를 **strangler 점진(route-by-route) 이관**하는 트랙을 갖는다.

방향 근거: `docs/adversarial-review/2026-06-03-harness-ownership.md`에서 strong-form(전면 OMC 자체 대체 = 옵션 B)이 기각된 뒤 채택된 narrow path예요. 자체 빌드는 native가 강제 못 하는 invariant(헌법) enforcement에 한정돼요(아래 §4 헌법 블록). 동작 중인 OMC를 from-scratch 엔진으로 전면 교체하는 건 lock-in 실측 증거 0건 + native supersession 매몰비용으로 기각됐어요.

### 2. 5-레이어 모델

| 레이어 | 동작 | claude-kit 매핑 | 소유 |
|--------|------|----------------|------|
| **①인지** | reasoning 조작 | diverse-sampling · unknown-discovery · expert-panel · adversarial-review | claude-kit (leaf) |
| **②결정화·출력** | 포맷·목적별 산출물 | spec-first(goal-doc) · doc-concretize · doc-polish · graphify(html) · note · issue | claude-kit (leaf) |
| **③딜리버리** | vault 운반 | vault-bridge | claude-kit (leaf) |
| **④지식베이스** | vault 상주 관리 | obsidian-vault-manager | claude-kit (leaf) |
| **⑤실행(doing)** | debug · quality · retro · 슬라이스 루프 · 오케스트레이션 | **현재 OMC / 목표 native 기반 경량 하네스 / strangler 점진 이관** (정적 "⑤=OMC" 아님) | harness (CC 전용) |

claude-kit은 ①②③④를 leaf로 소유하고, ⑤는 native(`/goal`·Workflow·agents·hooks)를 substrate로 한 경량 하네스가 점진 흡수해요. ⑤의 native 위임 경계와 thin gap(정확히 2종 — 슬라이스→스킬 바인딩 라우팅 + 헌법 invariant enforcement)은 `docs/design/omc-to-native-substrate.md`가 확정해요.

### 3. 의존 방향 — 단방향 (harness → leaf)

- **harness → leaf만 허용.** harness(현재 OMC, 목표 native 기반 경량 하네스)가 claude-kit 스킬을 호출하는 leaf capability 관계예요.
- **역방향 무조건 금지.** leaf(①②③④)가 harness API·동작을 import·call·assume하지 않아요. leaf는 independently installable + harness-neutral by construction이에요(leaf 레벨 vendor-neutrality는 커밋 `7a94a34`에서 이미 달성).
- **B안 기각 1줄 기록**: 루프 전체를 from-scratch 자체 엔진으로 흡수하는 옵션 B는 — 동작 중인 OMC 전면 교체는 lock-in 실측 증거 0건이라 정당화 못 하고 native supersession 시 매몰비용 — 기각. 대신 **native 위임 우선 + strangler 점진**으로 재정의.

**규율 범위 (scope of "one-way")**: 이 단방향 규칙은 **harness↔leaf 경계에만** 적용돼요. leaf 내부 cognitive layer 간 호출(예: ①인지 스킬이 ②출력 스킬을 호출 — diverse-sampling Mode B → doc-concretize)은 ordinary module dependency로 **허용**돼요. 이게 issue-skill의 ②출력 leaf 귀속과 diverse-sampling Mode B 합성을 정당화하는 근거예요.

### 4. vault 철학 (수직축)

claude-kit의 vault 관련 동작 전체를 관통하는 두 원칙이에요. CLAUDE.md·플러그인 전반에 user-initiated / Write Role / type opt-in 패턴이 *암묵적으로만* 분산돼 있어서, OMC 제거 시 drift를 막으려고 여기 명시해요.

- **"Assist, never replace"**: claude-kit은 사용자의 vault를 *보조*하지 *대체*하지 않아요. vault writes는 new-file-only·user-initiated(슬래시 커맨드)이고, type opt-in이 없는 노트(일기·책 노트·자유 폴더)는 건드리지 않아요.
- **file-over-app**: 지식은 앱이 아니라 사용자 소유 파일(plain Markdown)에 상주해요. 이식성·장수성이 도구 종속보다 우선이에요. (출처: claude-kit 내부 v4 설계 `docs/design/vault-second-brain-v4.md`. origin 개념은 kepano/Obsidian의 file-over-app.)

### 5. 헌법 / 정책 분리 — 규칙 단일 출처

아래 두 목록이 claude-kit 동작 규칙의 **단일 출처**예요. #125(3-tier 규칙 시스템)는 이 목록을 *참조만* 하고 (1) 3-tier 레이어 구조 + (2) 안전판 4종만 별도로 다뤄요. 각 tier가 override 가능한 범위 = **정책(policy)** 항목에 한하고, **헌법(constitutional)** 항목은 어느 tier(default / user-global / project-local)도 override 불가예요.

#### Constitutional rules (immutable — harness·config 어느 쪽도 override 불가)

| # | 규칙 | 의미 |
|---|------|------|
| CON-1 | **vault writes: new-file-only, user-initiated slash command only** | vault 쓰기는 덮어쓰기 금지(새 파일만) + 메인 컨텍스트 슬래시 커맨드로만 개시. 서브에이전트 직접 write 금지(vault-bridge pre-write-guard Write Role Contract). *예외: frontmatter-only status-machine 전이(아래 CON-1 status-machine note).* |
| CON-2 | **deterministic hooks: zero per-turn LLM cost** | 훅은 결정적 셸 스크립트 — 턴마다 LLM 호출 0. (prompt 기반 훅의 무한 루프·토큰 비용 회피.) |
| CON-3 | **self-approval: prohibited in the same active context** | 저작 패스와 리뷰 패스 분리. 같은 액티브 컨텍스트가 자기 산출물을 승인 불가 — reviewer ≠ author. |
| CON-4 | **goal-doc schema: stable harness-neutral contract** | goal-doc은 harness가 바뀌어도 안정적인 중립 계약. 스키마 *세부*는 #100(`docs/design/goal-doc-spec.md`)이 정의하나, "stable harness-neutral contract여야 한다"는 *제약*은 여기 헌법으로 못박음. |
| CON-5 | **dependency direction: harness → leaf only, no reverse** | §3 단방향. intra-leaf 호출은 면제(§3 규율 범위). |

> CON-4 forward-ref: 스키마 자체는 #100 소관이지만, 그 스키마가 "stable harness-neutral contract"라는 제약 안에서 설계돼야 한다는 게 #100 → #99 의존의 실체예요. #100은 이 제약을 전제로 frontmatter·본문 섹션을 확정해요.

> **CON-1 status-machine note** (carve-out, ratified 2026-06-08): CON-1의 "new-file-only / 덮어쓰기 금지"는 **content·whole-file 클로버링**을 금지하는 것이지, frontmatter `status:` 전이를 막는 게 아니에요. v4 status machine(raw→draft→evergreen→archived, `vault-second-brain-v4.md` §3.3)은 설계상 `status:` 필드를 in-place 전이시키므로, **frontmatter-only + user-confirmed + 메인 컨텍스트** status 패치는 CON-1 *안*이에요. 이 carve-out은 (a) leaf write로는 OVM `audit` E2 OPTIONAL-FIX가 이미 행사하고, (b) **harness write로는 `workflow-harness` retro(#123)가 최초**예요 — 둘 다 frontmatter-only·user-confirmed·non-subagent(pre-write-guard 통과) 조건에 한해 허용돼요. body·파일명·경로 변경, 또는 silent(미확인) 패치는 여전히 금지.

#### Policy rules (harness-overridable / config-gated)

| # | 규칙 | override 경로 |
|---|------|--------------|
| POL-1 | **`VAULT_BRIDGE_WRITE_CONTRACT`** (warn / enforce / off) | 환경변수 / project-local |
| POL-2 | **`VAULT_BRIDGE_STRICT_NAMING`** strictness | 환경변수 / project-local |
| POL-3 | **model routing defaults** (haiku / sonnet / opus) | user-global / project-local |
| POL-4 | **Stop hook closing-keyword list** | user-global / project-local |
| POL-5 | **`snapshot_export` / `snapshot_import` opt-in gates** | `.vault-link` (project) + vault `_index.md` (vault owner) |

---

## W5 reframe 교차 참조

`thinking-tools/docs/improvement-matrix.md`의 W5("사고 도구가 실행 도구와 단절")는 *약점이 아니라* 이 경계 A의 **의도된 design boundary**예요. leaf(①②)가 harness(⑤ 실행)와 단방향으로만 결합하고 역방향 의존을 갖지 않는 건 §3 규율의 직접 귀결이에요. improvement-matrix W5 행은 이 사실을 reframe로 반영해요(행·ID 보존).

---

## 후속 의존 (이 문서를 전제로 착수)

- **#100** (goal-doc linchpin): CON-4 "stable harness-neutral contract" 제약 안에서 goal-doc 스키마 설계. `docs/design/goal-doc-spec.md`.
- **#101** (출력 어댑터 계약): ②출력 레이어 귀속(issue-skill=②, diverse-sampling Mode B 합성 허용)이 §3 규율 범위에 근거.
- **#122** (thin 하네스): §3 단방향 + strangler 원칙 + §5 헌법 invariant enforcement(D5).
- **#125** (3-tier 규칙): §5 헌법/정책 *목록*을 참조만. 재정의 금지.
- **#170** (4-flow 카탈로그): 물리 재편 없이 `docs/design/4-flow-catalog.md`에서 5-레이어 직교 매핑만 정의.
