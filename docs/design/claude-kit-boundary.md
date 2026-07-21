# claude-kit ↔ harness 경계 (진화형 경계 A) + Design Principles 단일 출처

**Status**: design (foundation) · **Created**: 2026-06-04 · **Issue**: #99 · **Epic**: #108
**Source**: `docs/discussions/20260602_claude-kit-layer-redesign/` (SUMMARY.md C-1, UNRESOLVED.md U-5) + `docs/adversarial-review/2026-06-03-harness-ownership.md`

> **이 문서는 단일 출처(single source of truth)예요.** claude-kit↔harness 경계, 5-레이어 모델, 의존 방향, 그리고 아래 `## Design Principles`의 **헌법(constitutional) / 정책(policy) 규칙 목록**은 여기서만 *정의*돼요. 다른 문서·이슈(#125 3-tier 규칙 등)는 이 목록을 **참조만** 하고 재정의하지 않아요. CLAUDE.md operating_principles의 "State each rule once" 원칙을 이 문서가 구현해요. 규칙이 두 곳에 적히면 drift·모순이 나거든요.

---

## Design Principles

### 1. 경계 A (진화형) — 책임 분담 (수평축)

claude-kit은 **①인지 ②결정화·출력 ③딜리버리 ④지식베이스**를 소유해요. **⑤실행(doing/오케스트레이션)**은 정적 "⑤=OMC"가 아니라 **진화형**이에요:

> **현재** OMC(또는 Claude Code 네이티브)가 ⑤를 담당하나, claude-kit은 Claude Code 네이티브 기능(dynamic Workflow, `/goal`, agents, hooks)을 **substrate로 한 경량 하네스**로 ⑤를 **strangler 점진(route-by-route) 이관**하는 트랙을 갖는다.

방향 근거: `docs/adversarial-review/2026-06-03-harness-ownership.md`에서 strong-form(전면 OMC 자체 대체 = 옵션 B)이 기각된 뒤 채택된 narrow path예요. 자체 빌드는 native가 강제 못 하는 invariant(헌법) enforcement에 한정돼요(아래 §4 헌법 블록). 동작 중인 OMC를 from-scratch 엔진으로 전면 교체하는 건 lock-in 실측 증거 0건 + native supersession 매몰비용으로 기각됐어요.

> **갱신 (2026-06-29 CUT)**: ⑤를 흡수하려던 자체 경량 하네스(goal-doc#100 스키마 + `slice-router` 라우터, `dev-harness` 플러그인)는 dogfood에서 **실사용 부적합**으로 철회됐어요 — 손으로 쓴 goal-doc이 INV-4 스키마를 통과 못 했거든요(slice-router는 실제 goal을 한 번도 라우팅 못 함). ⑤ 실행은 이제 native `/goal`이 직접 담당하고, 슬라이스 계획은 narrative START-PROMPT(session-close ④), 각 인지·출력 작업은 leaf 스킬 관례 호출이에요. strangler 결론 = native 위임으로 충분, 자체 하네스 불요. 전말: 트래킹 이슈 #282 + PR #283 (discussion 노트는 .gitignore상 비커밋이라 정본은 GitHub 이슈).

### 2. 5-레이어 모델

| 레이어 | 동작 | claude-kit 매핑 | 소유 |
|--------|------|----------------|------|
| **①인지** | reasoning 조작 | diverse-sampling · unknown-discovery · expert-panel · adversarial-review | claude-kit (leaf) |
| **②결정화·출력** | 포맷·목적별 산출물 | build-spec(seed) · doc-concretize · doc-polish · graphify(html) · note · issue | claude-kit (leaf) |
| **③딜리버리** | vault 운반 | vault-bridge | claude-kit (leaf) |
| **④지식베이스** | vault 상주 관리 | obsidian-vault-manager | claude-kit (leaf) |
| **⑤실행(doing)** | debug · quality · retro · 슬라이스 루프 · 오케스트레이션 | **native `/goal` + Workflow + agents가 직접 담당** (슬라이스 루프 = narrative START-PROMPT를 읽는 native `/goal`; leaf 스킬 관례 호출). measure→improve = `feedback-loop`(외부 배포 ⑤, retro+telemetry). 자체 흡수 하네스(`dev-harness`)는 2026-06-29 CUT으로 철회. | native + feedback-loop |

claude-kit은 ①②③④를 leaf로 소유하고, ⑤ 실행은 native(`/goal`·Workflow·agents·hooks)가 직접 담당해요 — 자체 흡수 하네스는 2026-06-29 CUT으로 철회됐어요(위 §1 갱신).

> **③↔④ 경계 판정 기준 (2026-07-02, #304)**: 레이어 번호는 "누가 뭘 하나"를 안 알려줘서, 사서/브리지
> 한 줄 테스트를 판정 기준으로 채택했어요 — **"이게 프로젝트가 존재한다는 걸 알아야 하나?"** 몰라도
> 됨 → **사서(④ OVM)**, 볼트 코퍼스만 다뤄요. 한쪽에 프로젝트가 없으면 무의미 → **브리지(③ vault-bridge)**,
> 프로젝트↔볼트 양쪽 레퍼런스를 동시에 쥔 유일한 컴포넌트예요. wiki의 U7 route(다른 레포에서도
> 참인가 라우팅)는 크로싱 판단=③ 브리지 로직, compile/dedup=④ 사서 코어인 **합법적 straddler**로
> 명시해요. 그리고 A-only 재설계 이후 브리지 정체성은 **pull-mostly**로 바뀌어요 — repo→vault로
> 문서를 복사해 나르는 ferry(원본이 바뀌면 drift하는 stale 원인, G21/G24/G26으로 이미 대부분 철거)는
> 금지, repo-세션에서 사실을 우려내는 wiki compile(mirror가 없어 구조상 drift 불가)은 유지, A↔B(wiki↔
> second brain) 연동은 링크only(복사 금지)예요. 근거: #304 (판정 근거였던
> `vault-role-redefinition-draft.md`는 승격 완료 후 삭제 — 이 문서가 SSOT).
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
> 그만두고 session 요약을 `type:capture`로 `inbox/`에 적재하는 캡처 문으로 재목적화됐어요(`/capture`와
> 동일한 원석 산출물). 상세 근거·재정정 텍스트: #304 논의 + 위 spec c9. 출력 어댑터 매핑도 같이 갱신됨 — `docs/design/output-adapter-contract.md` §2 row #5.

**§2.5 — ⑤ 슬라이스 루프 완료조건 계약 (#285)**: 슬라이스 루프 입력인 START-PROMPT(session-close ④가 저작, 이 레포 외부)는 native `/goal` 평가자가 판정해요. 그 평가자는 **대화에 surfaced된 증거로만 완료를 판정**하고 파일·명령을 독립 실행하지 않아요([공식](https://code.claude.com/docs/en/goal)). 따라서 START-PROMPT의 `완료조건`은 surfaced-evidence 3레버(L1 단일 도구호출 반증 · L2 독립 리뷰 게이트 · L3 auto mode+턴 상한)를 만족해야 평가 가능해요 — 표준 정본은 #285.

**§2.5-1 — on-the-loop 게이트 (#309 P3)**: 위 3레버는 완료조건 *판정*을 다루고, 이 게이트는 판정 도중의 *비가역 액션*(merge·삭제·배포·이슈 종료 등)을 다뤄요. 무인/headless 실행이라고 확인 체크포인트가 자동 생략되면 안 돼요 — 정본은 local-harness `rules/README.md` P7. #309의 BUDGET·stall 레버(P1·P2)는 실제 폭주·정체 증거가 나오기 전까진 backlog(gated) 그대로예요.

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
