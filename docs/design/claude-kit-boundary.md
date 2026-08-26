# claude-kit ↔ harness 경계 (진화형 경계 A) + Design Principles 단일 출처

**Status**: design (foundation) · **Created**: 2026-06-04 · **Issue**: #99 · **Epic**: #108
**Source**: #108 레이어 재설계 논의 (C-1 · U-5) + harness-ownership 어드버서리얼 리뷰(2026-06-03) — 두 근거 문서 모두 로컬 작업물이라 비커밋

> **이 문서는 단일 출처(single source of truth)예요.** claude-kit↔harness 경계, 5-레이어 모델, 의존 방향, 그리고 아래 `## Design Principles`의 **헌법(constitutional) / 정책(policy) 규칙 목록**은 여기서만 *정의*돼요. 다른 문서·이슈(#125 3-tier 규칙 등)는 이 목록을 **참조만** 하고 재정의하지 않아요. CLAUDE.md operating_principles의 "State each rule once" 원칙을 이 문서가 구현해요. 규칙이 두 곳에 적히면 drift·모순이 나거든요.

---

## Design Principles

### 1. 경계 A (진화형) — 책임 분담 (수평축)

claude-kit은 **①인지 ②결정화·출력 ③딜리버리 ④지식베이스**를 소유해요. **⑤실행(doing/오케스트레이션)**은 정적 "⑤=OMC"가 아니라 **진화형**이에요:

> **현재** OMC(또는 Claude Code 네이티브)가 ⑤를 담당하나, claude-kit은 Claude Code 네이티브 기능(dynamic Workflow, `/goal`, agents, hooks)을 **substrate로 한 경량 하네스**로 ⑤를 **strangler 점진(route-by-route) 이관**하는 트랙을 갖는다.

방향 근거: harness-ownership 어드버서리얼 리뷰(2026-06-03, 비커밋 로컬 작업물)에서 strong-form(전면 OMC 자체 대체 = 옵션 B)이 기각된 뒤 채택된 narrow path예요. 자체 빌드는 native가 강제 못 하는 invariant(헌법) enforcement에 한정돼요(아래 §4 헌법 블록). 동작 중인 OMC를 from-scratch 엔진으로 전면 교체하는 건 lock-in 실측 증거 0건 + native supersession 매몰비용으로 기각됐어요.

> **갱신 (2026-06-29 CUT)**: ⑤를 흡수하려던 자체 경량 하네스(goal-doc#100 스키마 + `slice-router` 라우터, `dev-harness` 플러그인)는 dogfood에서 **실사용 부적합**으로 철회됐어요 — 손으로 쓴 goal-doc이 INV-4 스키마를 통과 못 했거든요(slice-router는 실제 goal을 한 번도 라우팅 못 함). ⑤ 실행은 이제 native `/goal`이 직접 담당하고, 슬라이스 계획은 narrative START-PROMPT(session-close ④), 각 인지·출력 작업은 leaf 스킬 관례 호출이에요. strangler 결론 = native 위임으로 충분, 자체 하네스 불요. 전말: 트래킹 이슈 #282 + PR #283 (discussion 노트는 .gitignore상 비커밋이라 정본은 GitHub 이슈).

### 2. 5-레이어 모델

| 레이어 | 동작 | claude-kit 매핑 | 소유 |
|--------|------|----------------|------|
| **①인지** | reasoning 조작 | diverse-sampling · unknown-discovery · expert-panel · adversarial-review | claude-kit (leaf) |
| **②결정화·출력** | 포맷·목적별 산출물 | build-spec(seed) · doc-concretize · doc-polish · graphify(html) · note · issue · next-goal(`/goal` 완료조건) | claude-kit (leaf) |
| **③딜리버리** | vault 운반 | vault-bridge | claude-kit (leaf) |
| **④지식베이스** | vault 상주 관리 | obsidian-vault-manager | claude-kit (leaf) |
| **⑤실행(doing)** | debug · quality · retro · 슬라이스 루프 · 오케스트레이션 | **native `/goal` + Workflow + agents가 직접 담당** (슬라이스 루프 = narrative START-PROMPT를 읽는 native `/goal`; leaf 스킬 관례 호출). measure→improve = `feedback-loop`(외부 배포 ⑤, retro+telemetry). 자체 흡수 하네스(`dev-harness`)는 2026-06-29 CUT으로 철회. | native + feedback-loop |

claude-kit은 ①②③④를 leaf로 소유하고, ⑤ 실행은 native(`/goal`·Workflow·agents·hooks)가 직접 담당해요 — 자체 흡수 하네스는 2026-06-29 CUT으로 철회됐어요(위 §1 갱신).

> **③↔④ 경계 판정 기준 (#304, 2026-07-02 · 배포 축 개정 #645, 2026-08-20)**: 레이어 번호는 "누가 뭘
> 하나"를 안 알려줘서, 사서/브리지 한 줄 테스트를 판정 기준으로 채택했어요 — **"이게 프로젝트가
> 존재한다는 걸 알아야 하나?"** 몰라도 됨 → **사서(④ OVM)**, 볼트 코퍼스만 다뤄요. 한쪽에 프로젝트가
> 없으면 무의미 → **브리지(③ vault-bridge)**, 프로젝트↔볼트 양쪽 레퍼런스를 동시에 쥔 유일한
> 컴포넌트예요. wiki의 U7 route(다른 레포에서도 참인가 라우팅)는 크로싱 판단=③ 브리지 로직,
> compile/dedup=④ 사서 코어인 **합법적 straddler**로 명시해요. 그리고 A-only 재설계 이후 브리지
> 정체성은 **pull-mostly**로 바뀌어요 — repo→vault로 문서를 복사해 나르는 ferry(원본이 바뀌면 drift하는
> stale 원인, G21/G24/G26으로 이미 대부분 철거)는 금지, repo-세션에서 사실을 우려내는 wiki
> compile(mirror가 없어 구조상 drift 불가)은 유지, A↔B(wiki↔second brain) 연동은 링크only(복사
> 금지)예요. 근거: #304 (판정 근거였던 `vault-role-redefinition-draft.md`는 승격 완료 후 삭제 — 이
> 문서가 SSOT).
>
> **`/wiki` 배포 단위 = ③ vault-bridge (개정, #645)**. 위 straddler 분류는 **레이어 축 판정이고 그대로
> 유효**해요 — 바뀐 건 *어느 플러그인에 실려야 호출 가능한가*라는 별개 축이에요. 한 줄 테스트를 그
> 축에 적용하면 `/wiki`는 작업 세션에서 알게 된 걸 컴파일하니까 입력이 프로젝트 세션이고, U7
> 라우팅("다른 레포에서도 참인가")도 레포 개념이 있어야 성립해서, 프로젝트 존재를 **알아야 하는**
> 쪽이에요. 이 레포는 이미 같은 구분을 써요(CLAUDE.md의 feedback-loop = "외부 배포지만 ⑤ 계열,
> **배포단위≠레이어**"). 이관 자산은 쓰기 경로만(`skills/wiki/`·`manifest-wiki-match.py`·
> `reference/obsidian-format.md`), 읽기·감사(audit E12)는 OVM 잔류 — 감사는 저자를 안 따지거든요.
> 실측: `/wiki` 호출이 claude-kit 24 · PhototicketMaker 10 · **`~/vault` 0회**, provenance가 vault
> 세션인 wiki 페이지 0개. 그리고 OVM **단독 설치는 0곳**이라 §3 독립설치성은 안 깨져요 — 오히려
> `wiki/SKILL.md`가 vault-bridge 소유 manifest를 읽던 크로스 의존이 2건에서 1건으로 줄어요.
>
> 이 개정은 **2026-08-18 "현행 유지" 판정을 파기**해요. 그 판정의 근거 3개 중 둘이 무너졌어요 —
> (1) "OVM이 프로젝트에 깔린 실측"은 #477 사후 정정 2(2026-08-02)가 이미 **플러그인 MECE 위반**으로
> 기각해둔 상태였고(실측은 무엇이 *일어났는지*를 말하지 무엇이 *허용됐는지*를 말하지 못해요),
> (2) "leaf 독립설치성 역전"의 전제인 OVM 단독 설치는 census 결과 0곳이에요. 08-18 판정문 본문은
> 여기 남기지 않아요 — 정정을 아래에 계속 덧붙이면 이 문서가 스스로 선언한 "State each rule once"가
> 깨지거든요(§5 선례 편철 ③). 이유 전문은 #645 코멘트(2026-08-20)에 인라인으로 있어요.
>
> **`/vault-link` 판정 (#304 L1)**: **유지한다 (제거하지 않음)**. 애초 가설은 "서브폴더 배치용이라
> 사서 관심사, 진짜 볼트-선택 라우팅은 미구현이라 A-only엔 불필요"였지만, 코드 확인 결과 틀렸어요 —
> `.vault-link`는 `vault-searcher`의 recall scoping(세션 복원 + 도메인 컨텍스트 모드의 search_root
> 결정)에 쓰이는 살아있는 브리지 기능이고, 실제로 `claude-kit`·`PhototicketMaker` 두 프로젝트가 지금
> 이 스코핑에 걸려 있어요. 제거하면 두 프로젝트의 recall이 전체 vault 스캔으로 퇴화해 다른 프로젝트
> 노트가 섞이는 실제 회귀가 나요. 이 스코핑은 B(second brain)에만 걸리고 A(wiki)는 `.vault-link`
> 스코핑과 무관하게 항상 recall에 포함되므로(#272 예외), 유지 여부가 #267 B-probation 판정
> (~2026-07-13)과 엮이지 않아요 — 유지 비용이 0이라 그 판정을 기다릴 필요 없이 지금 확정. 실제
> defer 대상은 원래부터 미구현이던 세션-레벨 다중 vault-ROOT 셀렉터(여러 독립 볼트 중 선택)뿐이고,
> 이건 YAGNI로 계속 defer해요.
>
> **재정정 (D1, 2026-07-08)**: `/vault-link` 존속 판정(위)은 그대로 유효하지만, 같은 #304 논의에서
> 나왔던 "`/save-session`은 B층 자기 목적으로 독자 생존한다"는 별도 결론은 **뒤집혔어요** — owner
> 승인(#331 배경 문단 — 원 스펙 c9)으로 `/save-session`이 session-note 저작을
> 그만두고 session 요약을 `type:capture`로 `sources/`에 적재하는 캡처 문으로 재목적화됐어요(`/capture`와
> 동일한 원석 산출물). 상세 근거·재정정 텍스트: #304 논의 + 위 spec c9. 출력 어댑터 매핑도 같이 갱신됨 — `docs/design/output-adapter-contract.md` §2 row #5.

**§2.5 — ⑤ 슬라이스 루프 완료조건 계약 (#285)**: 슬라이스 루프 입력인 START-PROMPT(session-close ④가 저작, 이 레포 외부)는 native `/goal` 평가자가 판정해요. 그 평가자는 **대화에 surfaced된 증거로만 완료를 판정**하고 파일·명령을 독립 실행하지 않아요([공식](https://code.claude.com/docs/en/goal)). 따라서 START-PROMPT의 `완료조건`은 surfaced-evidence 3레버(L1 단일 도구호출 반증 · L2 독립 리뷰 게이트 · L3 auto mode+턴 상한)를 만족해야 평가 가능해요 — 표준 정본은 #285.

**§2.5-1 — on-the-loop 게이트 (#309 P3)**: 위 3레버는 완료조건 *판정*을 다루고, 이 게이트는 판정 도중의 *비가역 액션*(merge·삭제·배포·이슈 종료 등)을 다뤄요. 무인/headless 실행이라고 확인 체크포인트가 자동 생략되면 안 돼요 — 정본은 local-harness `rules/README.md` **P6**.

> **재정정 (2026-07-30)**: 이 줄은 정본을 `P7`로 가리켰는데, 그 번호는 2026-07-23에 은퇴했어요 — 내용은 **P6**로 갔고 번호는 P9로 흡수됐어요. `policies/P9.md`가 은퇴 당시 "nothing referenced it correctly"로 기록했지만 그 감사는 local-harness 내부만 봤고, 이 인용을 7일간 놓쳤어요. 교훈은 번호 체계가 아니라 검색 범위예요 — 카탈로그를 인용하는 소비자 레포까지 훑어야 은퇴가 끝나요(local-harness `c52ffde`에 같은 정정).

> **BUDGET·stall 레버 (#309 P1·P2) 재판정 (2026-07-30)**: "실제 폭주·정체 증거가 나올 때까지 gated"라는 이전 서술은 폐기해요 — 텔레메트리가 opt-in(`CLAUDE_KIT_TELEMETRY=1`)이라 그 증거를 모으는 장치가 기본으로 꺼져 있어서, 영원히 안 채워지는 조건이었어요. 재판정 결과는 갈려요. **P1(BUDGET)은 네이티브가 흡수** — Workflow의 토큰 예산이 하드 실링이라(`budget.total` 도달 시 `agent()`가 예외) 별도 표준을 세울 표면이 없어요. **P2(stall 탐지)만 실제 갭** — 동일 실패 N회·empty-diff 정지는 native도 `session-close` ④ 저작 체크리스트도 안 갖고 있어요. 증거 대기가 아니라 착수 대상이에요.

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
| CON-5 | **dependency direction: harness → leaf only, no reverse** | §3 단방향. intra-leaf 호출은 면제(§3 규율 범위). |

> **CON-1 status-machine note** (carve-out, ratified 2026-06-08): CON-1의 "new-file-only / 덮어쓰기 금지"는 **content·whole-file 클로버링**을 금지하는 것이지, frontmatter `status:` 전이를 막는 게 아니에요. v4 status machine(raw→draft→evergreen→archived, `vault-second-brain-v4.md` §3.3)은 설계상 `status:` 필드를 in-place 전이시키므로, **frontmatter-only + user-confirmed + 메인 컨텍스트** status 패치는 CON-1 *안*이에요. 이 carve-out은 (a) leaf write로는 OVM `audit` E2 OPTIONAL-FIX가 이미 행사하고, (b) **harness write로는 `feedback-loop` retro(#123, #217로 workflow-harness에서 분리)가 최초**예요 — 둘 다 frontmatter-only·user-confirmed·non-subagent(pre-write-guard 통과) 조건에 한해 허용돼요. body·파일명·경로 변경, 또는 silent(미확인) 패치는 여전히 금지.

#### Policy rules (harness-overridable / config-gated)

| # | 규칙 | override 경로 |
|---|------|--------------|
| POL-1 | **`VAULT_BRIDGE_WRITE_CONTRACT`** (warn / enforce / off) | 환경변수 / project-local |
| POL-2 | **`VAULT_BRIDGE_STRICT_NAMING`** strictness | 환경변수 / project-local |
| POL-3 | **model routing defaults** (haiku / sonnet / opus) | user-global / project-local |
| POL-4 | **Stop hook closing-keyword list** | user-global / project-local |
| ~~POL-5~~ | ~~**`snapshot_export` / `snapshot_import` opt-in gates**~~ — **OBSOLETE (G21 cut)**: the `/save-plan-doc` "③ delivery" intake (dual-source antipattern, telemetry 3-week zero) was removed, so these gates no longer exist. | — |

#### 플러그인 설치 규범 (#477 사후 정정 2, 2026-08-02 · 여기로 편철 #645)

**OVM은 볼트에 깔리는 플러그인이고, 프로젝트 레포에 통째로 설치하지 않아요.** OVM 전체가 프로젝트에
깔리면 `/audit`·`/base`가 따라오고, "프로젝트를 몰라도 되는 것만 OVM"이라는 §2 한 줄 테스트의 성격
규정이 첫 액션에서 깨지거든요. 프로젝트 세션에서 볼트를 건드려야 하면 그 경로는 ③ vault-bridge예요.

이 규범이 #477 코멘트에만 있고 이 문서에 없어서 실제로 사고가 났어요 — **같은 사실**(PhototicketMaker에
OVM이 깔려 있었다는 실측)이 2026-08-02에는 *기각 사유*였다가 2026-08-18에는 *승인 근거*로 인용됐어요.
실측은 무엇이 **일어났는지**를 말할 뿐 무엇이 **허용됐는지**를 말하지 못해요. 그 텔레메트리가 증명한 건
"규범이 거짓"이 아니라 "규범이 잠시 위반됐다"였고요. 그래서 판정에 실측을 인용할 땐 **수집 조건과 반증
조건을 같이 적어요** — "이 설정은 커밋 안 되는 쪽에만 있었다" 한 줄이 붙어 있었다면 그 근거는 규범을
뒤집는 데 쓰이는 대신 검증 대상이 됐을 거예요.

> **계측 한계 (같이 적어두는 수집 조건)**: 설치 census(2026-08-20)는 **이 머신 한 대**의 사실이에요 —
> 프로젝트 7곳 + `~/vault` 기준 vault-bridge 8곳 / OVM 2곳(claude-kit, `~/vault`) / **OVM 단독 0곳**.
> 외부 마켓플레이스 설치 인구는 계측 수단이 없어 포함되지 않아요. `/wiki` 배포 개정을 되돌릴 조건은
> **OVM 단독 설치가 실제로 존재하고 거기서 `/wiki` 호출이 관측되는 것** — census가 0이 아니게 되는 때예요.

#### 선례 편철 (#645, 2026-08-20)

`/wiki` 배포 귀속은 다섯 번 논의됐고 그중 두 번은 **이미 답이 나와 있던 규범을 못 찾아서** 다시 열렸어요.
2026-08-18 판정은 #477(2026-08-02)의 설치 규범을 참조하지 않은 채 내려졌는데, #477은 숨어 있지 않았어요 —
`vault-second-brain-v5.md:3`의 "최종 개정: 2026-08-04(#477)"이 가리키고 있었고, 그 판정이 개정한 §9가 바로
그 파일 안이었어요. 필요했던 확인은 한 파일 3행이었고요. 그래서 탐색 범위를 규칙으로 고정해요:

1. **읽을 의무**: 이 문서군의 규칙을 개정하는 판정은 **개정 대상 문서의 `최종 개정` 헤더와 개정 대상 절
   제목에 인용된 이슈 번호**를 선례 집합으로 삼아 그 본문·코멘트를 읽고, 동일 쟁점을 심리한 것이 있으면
   판정문에서 **인용해 구별하거나 파기**해요.
2. **찾아 나설 의무는 없음**: 그 집합 *밖*의 이슈까지 뒤질 의무는 없어요. 이게 무한 탐색을 막아요.
3. **편철할 의무**: 어떤 이슈에서 이 문서군의 규칙을 뒤집거나 제약하는 결론이 나오면, **해당 절 머리말에
   그 이슈 번호를 한 줄 추가하는 것이 그 이슈의 종결 요건**이에요. 편철되지 않은 규범은 후속 판정에
   대항하지 못해요. ③이 유실을 막고 ②가 탐색 폭주를 막아요.

**라벨은 두 종류만**: **개정**(선행 판정을 무효화함) / **보강**(무효화 아님). "갱신·재확인·재정정·재판정"은
안 써요 — 이 레포에서 "재확인"은 두 번 다 *답해졌다*가 아니라 **답 없이 닫혔다**의 표식으로 기능했어요
(08-10 종결 → 5일 뒤 #645 개설, 08-18 재확인 → 2일 뒤 근거 붕괴).

**정정은 덧붙이지 말고 교체**: 한 규칙의 현재 상태는 한 블록으로 읽혀야 해요. 아래에 정정 블록을 계속
쌓으면 독자가 어느 게 살아 있는지 판별해야 하고, 실제로 그렇게 됐었어요(§2에 사후 블록이 쌓여 순서마저
비시간순이었음). 파기된 판정의 *본문*은 지우고, 파기 사실과 이유 소재만 남겨요.

---

## claude-kit ↔ local-harness 경계 (§0 — 이식성)

**이 경계는 위 harness↔leaf 경계와 별개**예요. local-harness는 개인 머신 정책 베이스(머신 스코프, claude-kit *밖* 별도 프로젝트 — #229)이고, claude-kit은 공개 마켓플레이스(레포 스코프)예요. 둘 사이엔 단 하나의 불변식만 둬요:

> **§0 — claude-kit 레포는 local-harness에 런타임/빌드 의존이 0이다.** 그래야 공개 clone이 어느 머신에서나 빌드·실행돼요. (work-rule 레이어 형태는 `rules/RULES.md` §0.)

- **"자족(self-contained)"의 정확한 뜻**: claude-kit은 자기가 필요로 하는 정책의 *구체 형태*를 **스스로** 보유해요. 이건 머신 레벨 추상의 **구체화(concretization)**지 *동일 복제*도 *런타임 fetch*도 아니에요. 추상과의 연결은 **지적 계보(intellectual lineage)** + `feedback-loop`의 느슨한 넛지 다리일 뿐, 코드/빌드 의존이 아니에요. §0의 "의존"은 런타임/빌드를 뜻하지 지적 계보가 아니에요(#229, discovery f15).
- **상속 = 추상/구체 분해 (동일 복제 금지)**: 같은 정책을 양쪽에 동일 텍스트로 두면 상속이 아니라 중복(DRY 위반)이에요. 로컬 = 추상(what+why), claude-kit = 구체(how) — 고도(altitude)로 구분해요.
- **워크드 예제 (레포 빌드 결정론 가드)**: 루트 `scripts/`의 `check-version-sync`·`check-type-optin`·`check-language-policy`·`check-banned-words`는 *이 레포 자체*를 검증하는 *구현체*라 추상화할 거리가 없어 **claude-kit 자족 잔류**(local-harness 이관 0). 유일한 진짜 *추상* 상향은 **서브에이전트 git 부작용 계약(#209)** — 광의 what+why는 머신 레벨 work-rule(`~/.claude/rules/` P3)로 올라가고 구체 강제는 claude-kit에 자족으로 남아요.
- **느슨한 연결 — `feedback-loop` 넛지(상향)**: 프로젝트 반복 패턴을 "로컬 rules로 올릴래요?" user-confirmed 넛지로 승격 제안하는 게 유일한 다리예요. 코드 의존이 아니라 telemetry 데이터 계약이에요.
- **추가 범용 후보 (#229 1(a) — 아직 *후보*, 리프트 미실행)**: #209 git 계약처럼 *지적 계보가 머신 레벨로 향하는* 항목이 둘 더 있어요. (1) **#211 서브에이전트 반환 계약** — "마지막 메시지만 반환된다"는 모든 스폰 지점(스킬·워크플로·네이티브 에이전트)에 걸리는 범용 패턴이라, claude-kit엔 이미 범용 규칙으로 **자족 보유**(`rules/RULES.md` §1 + 각 에이전트의 Final Response Contract)해요. 머신 레벨 추상 리프트는 #209가 그랬듯 *재발이 증명되면* 올리는 **deferred 후보**고요. (2) **#202 distill** — 컴포넌트 이동이 아니라 **`feedback-loop` 넛지의 *증류 경로* 그 자체**예요: 세션의 재사용 가능한 *절차* 기법을 개인 스킬(`~/.claude/skills/`)로 증류하는 채널이고, 그 증류물이 위 넛지를 타고 머신 레벨 베이스로 올라갈 수 있는 상향 다리의 구체 메커니즘이에요(distill 빌드 자체는 별도 트랙 #202). 둘 다 *런타임 의존이 아니라 계보*라는 점은 #209와 같아서 §0 불변식은 안 깨져요.

---

## W5 reframe 교차 참조

`thinking-tools/docs/improvement-matrix.md`의 W5("사고 도구가 실행 도구와 단절")는 *약점이 아니라* 이 경계 A의 **의도된 design boundary**예요. leaf(①②)가 harness(⑤ 실행)와 단방향으로만 결합하고 역방향 의존을 갖지 않는 건 §3 규율의 직접 귀결이에요. improvement-matrix W5 행은 이 사실을 reframe로 반영해요(행·ID 보존).

---

## 후속 의존 (이 문서를 전제로 착수)

- **#101** (출력 어댑터 계약): ②출력 레이어 귀속(issue-skill=②, diverse-sampling Mode B 합성 허용)이 §3 규율 범위에 근거.
- **#125** (3-tier 규칙): §5 헌법/정책 *목록*을 참조만. 재정의 금지.
- **#170** (4-flow 카탈로그): 물리 재편 없이 `docs/design/4-flow-catalog.md`에서 5-레이어 직교 매핑만 정의.
