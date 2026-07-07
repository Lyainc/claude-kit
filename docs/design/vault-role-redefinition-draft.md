# vault 역할 재정의 초안 — 사서/브리지 + A-only 브리지 = pull-mostly

**Status**: retired (2026-07-02, #304) — 승격 완료, SSOT는 `claude-kit-boundary.md` §2 · **Created**: 2026-07-01 · **관련**: #215 · #94 · #267
**Source**: 이 세션 대화 3건(플러그인 합병 → 사서/브리지 metaphor → ferry/A-only) +
`docs/discovery/vault-role-redefinition/DISCOVERY_REPORT.md`(unknown-discovery + expert-panel)
**입력 설계**: `vault-second-brain-v5.md` · `20260612_vault-llm-wiki-redesign/RESOLUTIONS-draft.md`(U5) ·
`20260623_vault-debloat-reckoning/DECISION.md`

> 이 문서는 **retired**예요. `claude-kit-boundary.md`가 5-레이어·경계·의존방향의 단일 출처(SSOT)이고,
> 이 draft의 저위험 확정(§1~3) + linchpin L1·L2 판정이 전부 그 문서 §2에 승격 완료됐어요. 이 파일은
> 판정 근거(discovery·코드 확인 evidence trail)를 보존하는 참고 기록으로만 남아요.

---

## 0. 한 줄 요약

vault 두 플러그인은 합치지 않는다. 대신 경계 판정 기준을 레이어 번호(③/④)에서 **사서/브리지
metaphor의 한 줄 테스트**로 바꾸고, A-only 재설계에서 브리지를 **pull-mostly(recall) 방향**으로
재정의한다. repo→vault로 *문서를 복사해 나르는* ferry는 stale의 원인이라 제거하되, *사실을 우려내는*
wiki compile(distill)은 유지한다 — 이 둘은 다르다.

---

## 1. 플러그인 합병 질문 → 분리 유지

**판정: OVM + vault-bridge를 하나로 합치지 않는다.** 판별축은 "같은 도메인(둘 다 vault)"이 아니라
**레이어 + 런타임 프로파일**이다.

- vault-bridge = ③ delivery: 결정론 shell 훅, per-turn LLM 0, haiku 검색. 상시 인프라(SessionStart).
- OVM = ④ knowledge base: 온디맨드 sonnet 스킬 + audit 엔진. 호출형.
- manifest가 "OVM wiki용 recall 인덱스"인 건 **OUTPUT 소비**(CON-5 단방향)지 코드 의존이 아니다.
  vault-bridge는 OVM을 import하지 않는다 — 합병처럼 보이는 신호가 다 이 착시다.
- 합병 재검토를 정당화하는 **유일한 조건**: vault-bridge를 OVM 없이 단독 설치하는 실사용 신호가
  장기간 0. 지금은 그걸 측정 못 함(cross-project = telemetry Option B 의존, 미구현) → **default는 분리**.

이건 RESOLUTIONS-draft U5("신규 플러그인 0, OVM 확장 + vault-bridge I/O 재사용")와 정합. 재설계는
vault-bridge를 *넓힌* 게 아니라 *역할 좁히고 죽은 intake를 cut*한 방향이었다(G21 ~2,700줄, G24 자동
저장 훅, G26 /handoff).

---

## 2. 경계 재정의 — 사서/브리지 한 줄 테스트

레이어 번호는 "누가 뭘 하나"를 안 알려준다. metaphor는 알려준다:

> **판정 테스트: "이게 프로젝트가 존재한다는 걸 알아야 하나?"**
> - 몰라도 됨 → **사서(OVM)**. 볼트 코퍼스만 만진다. *머신에 코드 레포가 하나도 없어도 일이
>   똑같으면* 사서다.
> - 한쪽에 프로젝트가 없으면 무의미 → **브리지(vault-bridge)**. 프로젝트↔볼트 양쪽 레퍼런스를 동시에
>   쥔 유일한 컴포넌트.

현재 배치는 대부분 이 테스트를 이미 지킨다:

| 기능 | 프로젝트를 알아야? | 귀속 | 현재 위치 | 판정 |
|---|---|---|---|---|
| audit (볼트 결함 스캔) | 아니오 | 사서 | OVM | OK |
| base (뷰 생성) | 아니오 | 사서 | OVM | OK |
| note / capture 저작 | 아니오(내용 프로젝트-무관) | 사서 | OVM | OK |
| file-organizer / knowledge-manager | 아니오 | 사서 | OVM | OK |
| vault-searcher (검색→세션 전달) | 예 | 브리지 | vault-bridge | OK |
| pre-access / pre-write guard (세관) | 예 | 브리지 | vault-bridge | OK |
| manifest (프로젝트가 질의할 인덱스) | 예 | 브리지 | vault-bridge | OK |
| /vault-link (프로젝트↔볼트 바인딩) | 예(정의 자체) | 브리지 | vault-bridge | §4 참조 |
| /save-session (이 세션 기록 운반) | 예 | 브리지 | vault-bridge | OK |

**유일한 straddler = wiki의 U7 route.** wiki compile은 "이게 다른 레포에서도 참이면 볼트 wiki, 이
레포 구조면 AGENTS.md로" 라우팅하는데, 이 판단은 "지금 이 레포가 뭔지"를 알아야 한다 = 프로젝트-aware.
순수 사서엔 "네가 있는 레포" 개념이 없다. 즉 **write 경로가 두 단계로, 소유자가 다르다**:
- **크로싱 단계**(U7 route: 볼트냐 이 레포냐) → 본질이 브리지.
- **코퍼스 단계**(compile·dedup·compound·self-audit) → 본질이 사서.

현 설계는 이걸 Write Role Contract로 봉합한다(브리지 pre-write-guard가 크로싱을 막고, OVM 스킬이
통관 후 메인 컨텍스트에서 저작). capture/note엔 이 봉합이 맞고, wiki만 통관 후에도 U7이 프로젝트-
awareness를 계속 요구하는 **합법적 straddler**로 명시한다 — U7 route는 브리지에서 빌려온 로직,
compile/dedup은 사서 코어.

---

## 3. A-only에서 브리지 = pull-mostly, ferry는 제거

핵심 구분: **문서를 복사해 나르기(ferry) ≠ 사실을 우려내기(distill).**

| 종류 | 정체 | stale? | A-only에서 |
|---|---|---|---|
| repo 문서 **복사 운반** | 원본 mirror가 볼트에 복사됨 → 원본이 변하면 drift | **예 (매립 원인)** | **제거** — 이미 대부분 철거(G21/G24/G26) |
| repo-세션 **사실 증류**(wiki) | mirror 없는 증류 사실, U7이 repo-mirror는 AGENTS.md로 배제 | 구조상 drift 불가 | **유지** — ferry 아니라 authoring |
| vault→session **recall** | 필요할 때 꺼내오기(당김) | — | **살아남는 코어** (vault-searcher + manifest) |

따라서 브리지 정체성이 뒤집힌다: 원래 "바인딩 + 양방향 운반" → A-only에선 **거의 단방향 읽기(pull)
브리지**. 볼트로 밀어넣는 push는 게이트된 wiki-compile 하나로 쪼그라든다. 단 "순수 pull-only"는
아니다 — cache-type 페이지면 "recall이 재컴파일 push를 트리거"하는 하이브리드(아래 §5).

DECISION.md의 dual-source 금지("복사·동기화 금지, 단방향 promotion만")를 이 방향이 계승한다.

---

## 4. /vault-link + 바인딩 재판정

- 현 용도(notes/{project}/ 서브폴더 배치)는 **볼트 *안에서* 어디**라 사실 사서 관심사로 보였다 — 브리지
  도구가 사서 일에 쓰이고 있었다는 초기 가설.
- 진짜 브리지 액션인 "여러 볼트 중 이 프로젝트는 어느 볼트냐"(볼트 선택 라우팅)는 **코드상 미구현**:
  볼트 루트는 3단 우선순위(`VAULT_BRIDGE_VAULT_ROOT` → `VAULT_BRIDGE_VAULT_PATH` → `~/vault`)로
  단일 해석이다.
- A(wiki)는 레포-초월/전역이라 A-only에서 프로젝트 바인딩 자체가 불필요. 하나의 전역 wiki를 모든
  프로젝트가 똑같이 읽는다(`vault-searcher`가 `.vault-link` 스코핑과 무관하게 `wiki/`를 항상 포함,
  #272 예외).

⚠️ **판정 교정 (2026-07-02, #304 L1 owner 판정 — 코드 확인 결과)**: 위 첫 전제가 **틀렸다.**
`.vault-link`는 서브폴더 배치용 파일이 아니라 `vault-searcher.md`의 recall scoping(Mode 1 세션 복원 +
Mode 2 도메인 컨텍스트, search_root 결정)에 쓰이는 **살아있는 브리지 기능**이다 — "프로젝트를 알아야
하나?" 한 줄 테스트를 실제로 통과한다. 그리고 가정이 아니라 실측: `claude-kit`(`20_Projects/claude-kit`)과
`PhototicketMaker` 두 프로젝트가 지금 이 스코핑에 라이브로 걸려 있다(`find ~/dev -name .vault-link`로 확인).
제거하면 두 프로젝트의 recall이 전체 vault-wide 스캔으로 퇴화해 다른 프로젝트 노트가 섞여 노이즈가 는다 —
공짜 정리가 아니라 실제 회귀.

→ **`/vault-link`는 유지한다 (제거 철회).** 유지 비용은 0(이미 동작 중인 코드)이고 이 스코핑은 오직
B(second brain, 프로젝트별 세션/결정 노트)에만 걸려 있어 A(wiki)의 존속과 무관하다 — 그래서 #267
B-probation 판정(~2026-07-13)을 기다릴 필요 없이 지금 판정할 수 있다(아래 긴장 재조정 참조).
실제로 defer할 대상은 원래부터 미구현이던 **세션-레벨 다중 vault-ROOT 셀렉터**(여러 개의 독립 볼트
자체를 선택하는 기능, 업무 볼트 vs 개인 볼트 같은 축)뿐이며 이건 YAGNI로 계속 defer.

⚠️ **결론 교정 (discovery 발견 3)**: 원래 "vault-link·/save-session·notes/가 B-probation 커플드라
B와 함께 죽는다"는 **두-볼트 분리로 정정.** LLM Wiki(A)와 Second brain(B)은 목적이 다른 별개 공간이라,
`/save-session`이 인간 second-brain 입력이면 A와 무관하게 자기 목적으로 산다. 위 판정 교정으로 `/vault-link`
자체도 안 죽는다 — B-probation(L1)과의 긴장은 "제거를 늦추느냐"가 아니라 애초에 **제거하지 않는 것으로
해소**된다(B가 probation을 통과하든 archive되든 스코핑 코드를 유지하는 데 드는 비용이 없다).

⚠️ **재정정 (D1, 2026-07-08, owner 승인 — `docs/specs/save-session-ore-repurpose.yaml` c9)**: 위
"`/save-session`은 자기 목적으로 독자 생존한다"는 결론은 **뒤집혔다.** `/save-session`은 더 이상 session
note를 저작하지 않고 session 요약을 `type:capture`로 `inbox/`에 적재하는 캡처 문으로 재목적화됐다 —
`/capture`와 같은 원석 산출물이다. 같은 문단의 `/vault-link` 존속 판정(L1)은 이 재정정과 **무관하게
그대로 유효**하다(`/vault-link`는 recall scoping 기능이지 session-note 저작과 별개). 상세: `docs/design/
claude-kit-boundary.md` §2, `vault-bridge/commands/save-session.md`.

---

## 5. A staleness — 발굴이 연 미해결 crux

repo→vault ferry를 죽여도 stale은 사라지지 않고 **mirror 없는 A 내부로 이사**한다(감지 기준선 상실).
이게 세 결론 전부가 딛고 선 미해결이다.

- **분류축**: cache/store를 "체크 가능한 소스 앵커 유무"로 가른다(expert-panel 합의).
- **기각**: "분류기 하나가 staleness를 통합 해결"은 기각. staleness는 타입별 **3겹 방어**:
  1. 소스-앵커드 → **lazy mtime check**(변했을 때만 재컴파일; full re-fetch 아님 → ferry 부활 아님).
  2. 소스-프리 → 검증 불가 인정 + recall 시점 **나이 노출**로 LLM 헤지.
  3. 공통 → provenance + 최종검증일 메타.
- **미해결(owner 고민 필요)**: (a) 분류 단위 페이지 vs claim(실제 페이지 mixed), (b) source-free
  "최종검증일" 갱신 주체(인간=B 대역폭 재발, AI=자기검증 U3 순환).

---

## 6. 확정 / linchpin 구분

**저위험 확정 (owner 반대 없으면):**
- 플러그인 분리 유지(§1).
- 사서/브리지 한 줄 테스트를 경계 판정 기준으로 채택, wiki U7 = 합법적 straddler(§2).
- A↔B 연동 = 링크only, 복사 금지(§3, DECISION.md 계승).
- 브리지 = pull-mostly, ferry(문서 복사 운반) 제거(§3).

**linchpin (owner 판정 필요):**
- **L1**: ✅ **판정 완료 (2026-07-02, #304)** — `/vault-link` **유지**(제거 철회, §4 판정 교정 참조).
  근거는 recall-hit 측정(telemetry Option B, 미구현)이 아니라 **코드 확인**(`vault-searcher.md`의
  scoping 의존 + 실사용 2개 프로젝트) — 그래서 측정 게이트를 기다리지 않고도 트리거 가능했다.
  defer 대상은 세션-레벨 다중 vault-ROOT 셀렉터뿐(YAGNI 유지).
- **L2**: ✅ **판정 완료 (2026-07-02, #305)** — 3겹 방어 채택(§5 그대로), 분류 단위 = **페이지 +
  dominant-type**(경계 mixed는 claim 단위 승격으로 defer), 최종검증일 갱신 주체 = **자동 last-touched
  타임스탬프**(인간도 AI도 능동 갱신 안 함 — B 대역폭 재발도 U3 순환도 회피). `anchor:`/`verified:`
  필드로 `docs/design/vault-second-brain-v5.md` §4.1 + `obsidian-vault-manager/skills/wiki/SKILL.md`
  + `vault-bridge/agents/vault-searcher.md`에 구현 완료. #305 acceptance 4개 전부 충족.

---

## 다음

L1·L2 판정 완료 → 확정분(§1~3 저위험 확정 + L1·L2)을 `claude-kit-boundary.md` §2(5-레이어 모델)에
승격했다 — 이 draft는 **retired**, SSOT는 `claude-kit-boundary.md`. staleness 3겹 방어는 별도 설계
트랙(#215 하위)으로 분리 권장.
