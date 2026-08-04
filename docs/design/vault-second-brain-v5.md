# Vault Second Brain 설계안 v5 — LLM-compiled wiki (A 主) + 참고자료 창고 (B, 승격 게이트 폐기)

> 작성일: 2026-06-23 · 최종 개정: 2026-08-04(#477) · 상태: **구현됨** — A(wiki)·B(참고자료 창고) 모두 코드에 반영, §15 전 항목 완료
> 대체 대상: `vault-second-brain-v4.md` (인간 저작 second-brain 모델)
> 방향 출처 — **정전(SSOT) = GitHub #215**(④ 재설계). 근거 트레일: 토론 문서 `docs/discussions/20260612_vault-llm-wiki-redesign/`
> (SUMMARY+UNRESOLVED+RESOLUTIONS-draft) · `docs/discussions/20260623_vault-debloat-reckoning/DECISION.md`(5레이어) ·
> 메모리 `project_vault_usage_reality`. **이 토론 문서·메모리는 repo 비커밋 로컬 작업물**(`.gitignore`의 `docs/discussions/`,
> 트레일 정책 #204/#215) — repo 클론으로는 안 보이므로, 본문의 그 경로·라인 인용은 *로컬 근거 포인터*이고 검증 가능한 정전은 #215다.
> 상속: v4의 type opt-in(§2.2)·recall 중심(§2.3)·git 통합·거부목록(§9)은 **계승**. v4 status machine(§3.3)은
> **2026-08-02 #480으로 폐기**(§5) — 초판의 "계승" 서술은 그 시점까지만 유효했다.
> 이 문서는 *바뀌는 것*만 명세하고, 안 바뀌는 기계는 v4를 참조한다.

---

## 0. 한 줄

vault의 무게중심을 **인간 저작(v4)에서 LLM 컴파일(v5)로** 옮긴다. **A(wiki) = LLM이 자율 컴파일하는
도메인 지식, AI recall이 主.** **B = 나중에 꺼내 쓰려고 넣어두는 참고자료 창고**(2026-08-02 #480 —
선별은 입구가 아니라 인출에서 일어난다, §5).
second-brain은 "인간이 나중에 읽는다"에서 "AI가 인간 대신 읽고 recall한다"로 재정의된다.

> **2026-07-09/10 정정**: 이전 초안의 "B 인간-읽기는 default OFF, 한 달 재판으로 존재를 증명해야 한다(L1)"
> 프레이밍은 owner가 측정-게이트 패러다임 자체를 폐기하면서 무효화됐다(#267 마지막 코멘트, §13 참조) — B는
> 재판 통과 여부와 무관하게 지금 그대로 쓰고, 판단이 필요해지면 그때 git log/transcript 같은 기존 기록을
> 사후에 뒤져 확인한다. A와 B는 애초에 **목적이 다른 별개 공간**(§3 레이어 표)이라 이 정정이 A쪽 설계엔
> 영향이 없다 — B의 존폐가 A를 게이팅한 적이 없다(#354, discovery report 발견 3 교정).

---

## 1. 진단 — 왜 v4→v5 (증거 기반)

v4는 "인간이 채우는 second-brain"을 전제했으나, 측정·증언·디스크가 그 전제를 부정했다:

1. **telemetry 실측**(#215, 05-15~06-11): vault delivery(save-plan-doc·save-session·vault-searcher) 사망,
   `goal` 활발. delivery 사망 시점 = goal-doc 워크플로우 성숙 시점.
2. **owner memory**(`project_vault_usage_reality:21`, 06-12): "second-brain-proper가 가치를 **한 번도**
   증명한 적 없음 — vault는 늘 second-brain을 가장한 work-dump." → **인간-읽기 수요는 한 번도 관찰된 적 없다.**
3. **근본 원인 2층**: (a) AI 생산량 > 인간 검토 대역폭 → "나중에 읽는다"가 영원히 안 옴 → 매립장화.
   (b) 출처 뒤섞임(스크랩·개인·LLM) → 신호가 소음에 묻힘.
4. **B 미사용의 진짜 원인**(adversarial 검증, RESOLUTIONS §U1): "뒤섞임"보다 **구조적 중복**이 더 그럴듯.
   5레이어 분리 후 B 후보 content가 거의 다 다른 집(이슈/memory/rules/AGENTS.md/wiki A)이 있다. 게다가
   B *읽기* 경로("Obsidian 열기")는 *쓰기*를 죽인 그 터미널 context-switch 마찰과 동일하다.

→ **결론**: A(LLM이 컴파일하는 도메인 지식 recall)는 실가치가 있고 vault를 정당화한다. B의 인간-읽기 목적은
미검증이었다. 그래서 원래는 **A를 主로 풀로 짓고, B는 "증명해야 사는" probation 타겟**으로 두기로 했었다
(L1 owner 합의) — 단 이 probation 프레이밍 자체는 §0/§13에 기록된 2026-07-09/10 owner 결정으로 이후
폐기됐다. B가 미검증이라는 진단은 여전히 유효하지만, 그 해법이 "재판 통과해야 산다"는 아니게 됐다.

---

## 2. 채택 모델 — Karpathy LLM Wiki

(gist 2026-04-03.) "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."

- 노트는 *인간이 읽으라고*가 아니라 *모델이 인간 대신 읽으라고* 최적화된 plain markdown KB.
- LLM이 자율적으로 쓰고·링크·분류·일관성 체크. **생산량>검토대역폭 병목을 구조적으로 우회**(A의 핵심 이점).
- loop = LLM이 "뭐가 빠졌나" self-ask(query responder 아닌 knowledge compiler) + `--save`로 합성 지식 적재 = compounding.

> "codebase"는 비유 — 지식이 코드처럼 구조화·재사용된다는 뜻. 코드는 repo가 정본(SSOT). wiki엔 코드에서
> *추출된 지식*만(§9 repo↔vault 경계). v4 §10(외부 검증 요약) 교훈 정합: "capture 자동화만으론 brain 불가, **recall이 핵심**."

---

## 3. 5레이어 분리 (출처가 안 섞이는 게 1차 원칙)

매립의 근본이 "출처 뒤섞임"이므로 레이어 분리가 1차 축. (DECISION.md §2.2 표.)

| 레이어 | 내용 | 소비자 | 저작 | 위치 |
|---|---|---|---|---|
| **repo** | 코드 + 코드구조맵(AGENTS.md) | AI+인간 | — | git repo |
| **vault wiki A** | 도메인 지식(작업하다 알게 된 것) | **AI recall** + 인간 | AI 자율 compounding | `vault/wiki/` |
| **vault notes B** | 참고자료(클리핑·논문·분석·브레인스토밍·초기 기획·공부 노트) | 인간(기획할 때 인출, §5) | 인간 저작 + 외부 원문 보관, 선별 없음(§5) | `vault/sources/`, `vault/notes/` |
| **rules** | work-policy("어떻게 일하나") | AI+인간 | 인간, 안정 | `~/.claude/rules`, `rules/RULES.md` |
| **memory** | 프로젝트 사실 | AI | auto | `~/.claude/projects/.../memory` |

- **policy/memory ≠ wiki**: wiki는 휘발·축적·AI 저작, policy는 안정·권위·인간 저작 — 성격 반대.
  policy를 wiki에 넣으면 U3(오염 복리)로 규칙 변질 + 출처 분리 위반.
- **decision은 GitHub 이슈가 정전**(trail 정책): 레포 바운드 decision은 이슈로 간다. B로 안 간다.
- **A의 인간 부차 소비 경로**: OVM `/base`(§9). 빌트인 `recent` 템플릿은 폴더 필터가 없어 `wiki/` 페이지도
  이미 섞여 나온다 — wiki만 따로 보려면 커스텀 `.base` 파일(`file.inFolder("wiki")`)을 직접 작성해야 한다,
  이 스킬이 자동 생성하는 건 3개 빌트인(`sources`/`notes`/`recent`)뿐이라서다. 브라우징이 설계 밖이라서가
  아니라 A의 主 소비자가 AI recall이라 전용 빌트인을 아직 안 만들었을 뿐이다(#530).

---

## 4. A (wiki) 설계 — 主 레이어

### 4.1 Frontmatter — `type: wiki` + provenance, status machine 밖

```yaml
type: wiki                 # v4 §2.2 opt-in — 관리·recall 가시성 위해 부여
created: YYYY-MM-DD
tags: [{domain}]
anchor: {local path/URL}   # optional — 체크 가능한 소스 있을 때만(#305 cache/store 분류축). 없으면 source-free
verified: YYYY-MM-DD       # 모든 write(신규·update)마다 자동 스탬프 — 능동 "검증"이 아니라 last-touched 신호
provenance: {session/query}  # U3 추적용 必 — 어느 탐구가 이 페이지를 낳았나
```

- **status machine 밖**: A엔 **status-machine 검토**(raw→draft→evergreen 같은 판단형 승인)가 없다(AI 저작).
  `wiki` skill PLAN 단계가 쓰기 전 보여주는 확인("one human glance", `obsidian-vault-manager/skills/wiki/SKILL.md`
  Phase 4)은 이 검토와 다르다 — 승인/반려
  판단이 아니라 저장 전 오탈자·오분류를 잡는 저비용 눈길이라, A가 판단형 검토 없이 자율 컴파일한다는 §2의
  성격을 바꾸지 않는다(§U6 정정, 2026-07-11, #215). A는 provenance 추적 AI 페이지지 검토-status 페이지가
  아니다. (raw→draft→evergreen은 원래 B의 일이었으나 그 machine 자체가 폐기됐다 — §5, #480. A쪽 서술엔
  영향 없다.)
- **staleness 3겹 방어 (#305)**: 분류 단위는 페이지+dominant-type(경계 mixed는 claim 승격으로 defer). `anchor:`
  유무가 cache(소스-앵커드)/store(소스-프리) 축. cache 페이지는 wiki 스킬 compile 시점에 `anchor` 파일의
  mtime을 `verified:`와 비교하는 lazy check(변했을 때만 재컴파일 — ferry 부활 아님, §3 pull-mostly 정합).
  store 페이지는 검증 불가를 인정하고 `verified:` 나이를 recall 경로(vault-searcher)에서 노출해 LLM 헤지를
  유도. `verified:`는 인간도 AI도 능동 갱신하지 않는다 — compile/update 시 자동 스탬프라 B 대역폭 재발도
  U3 자기검증 순환도 없다.
- **왜 파일시스템 mtime이 아니라 프론트매터 필드인가**: vault는 `/vault-commit`으로 git에 커밋되는 저장소라
  clone/checkout/restore가 파일 mtime을 체크아웃 시점으로 재설정해버린다 — fs mtime은 vault 이관 시 날아가는
  신호. `verified:`를 커밋되는 콘텐츠(프론트매터)에 두면 그 이관을 버틴다. vault-searcher가 이미 노출하는
  "modification date"(fs mtime)와는 별개 신호 — 겹치는 게 아니라 mtime이 못 버티는 자리를 메운다.

### 4.2 먹이 = query-driven compounding (게이트된 명시 `--save`)

- 미리 정한 소스 폴더가 아니라 **사용자의 탐구 흐름 그 자체**가 먹이. 조사·결정 중 LLM이 합성한 답을 wiki 페이지로 `--save`.
- **`--save`는 자동이 아니라 게이트된 컴파일 액션**(skill 호출, 사용자/AI 명시 발동). v4 §9.1 "항상-on push 없음"
  보존 — brain화는 명시 시점에. 코드를 긁어 넣는 게 아니라 작업하다 *알게 된 것*이 마찰 0으로 wiki가 된다.
- 진입점은 OVM skill(§7). hook 아님.

### 4.3 recall = AI가 인간 대신 읽음

- vault-searcher(haiku) + manifest access-ranking 인덱스로 wiki 페이지 recall. **#211 작업2(access-ranking)
  CLOSED**로 랭킹 시그널(`recent_commits`/`references_in`/`type` 가중치)은 갖췄지만, 그 인덱스를 읽는
  경로 자체가 결함이었다 — vault-searcher.md가 manifest 전체를 `Read`했는데, 실제 vault 규모(180개
  엔트리 / 3,338줄)에서 Read 도구 2,000줄 상한에 걸려 뒤가 잘렸고, `generate-manifest.py`가 `rel_path`
  사전순 정렬이라 `wiki/`가 항상 그 잘린 쪽에 몰려 **wiki 39개 전량이 조용히 후보 집합에서 사라졌다**
  (#523, "인프라 完" 선언과 정반대로 A 레이어만 골라 떨어뜨림). #523에서 manifest를 Python 스크립트
  (`manifest-domain-candidates.py`/`manifest-keyword-candidates.py`)로 먼저 필터링해 후보만 좁혀
  넘기는 방식으로 정정했다 — Read 도구 경유를 우회해 원본 파일 크기가 상한에 안 걸리게 하고,
  `candidate_count`를 배열보다 먼저 직렬화해 다시 잘리더라도 불일치로 드러나게 한다(#468의 OVM
  manifest-wiki-match.py와 같은 패턴). manifest는 ③ delivery staleness 추적에서 **④ wiki recall
  인덱스로 재용도**(§10 보류분).

---

## 5. B 설계 — 참고자료 창고 (status machine·승격 게이트 폐기, 2026-08-02 #477/#480)

B는 **선별에서 살아남은 것**이 아니라 **나중에 꺼내 쓰려고 넣어둔 참고자료**다. 클리핑·논문·분석·
브레인스토밍·초기 기획·공부 노트가 들어가고, 기획할 때 인출하는 게 용도다.

> **핵심 논거 — 범주 오류(#477)**: 승격 게이트는 들어온 다음 올려주는 장치지 **들어오는 걸 막는 장치가
> 아니다.** 매립장 방어를 승격 게이트에 기대는 배치 자체가 틀렸다.

실측(텔레메트리 491세션 + vault 134파일, 2026-08-02)이 그 배치가 한 번도 작동하지 않았음을 보여준다 —
규격 밖인 `plan` 57개(B 전체의 55%)가 조용히 통과했고(`type`이 애초에 E8 대상이 아니라 게이트가 관여한
적이 없다), evergreen은 1개, `/capture`·`/note` 호출은 0회(같은 기간 `/wiki`는 22회), retro 42회 실행에
승격 0건, archived 94개 중 90개가 커밋 하나(`1be026b`)의 일괄 처리였다.

- **대체 방어선은 저장 쪽이 아니라 인출 쪽이다.** 이 층의 성공 지표는 "선별 정확도"가 아니라 **인출이
  실제로 일어나는가**로 바뀐다(§13의 판단-기반 원칙 그대로 — 재판도 측정 게이트도 부활하지 않는다).
- **폐기**: status machine(`raw→draft→evergreen→archived`)과 B 내부 승격 게이트(§6). 어느 파일도
  `status:`를 새로 쓰지 않고, 어떤 스킬도 승격을 제안하지 않는다.
- **유지**: `provenance:` **필수**. 입구에 게이트가 없어졌으니 "이게 어디서 왔나"를 되짚을 수 있는 것이
  인출 시점의 유일한 신뢰 장치다 — A(§4.1)가 U3 오염 복리를 provenance로 막는 것과 같은 이유다.

```yaml
created: YYYY-MM-DD
type: capture | note | decision   # 폴더 마커 (sources/ = capture, notes/ = note·decision)
tags: [{type}, {keyword}]
provenance: "{출처 — URL·세션 주제·대화·책·회의}"   # 必
# status: 없음 (폐기)
```

- **입구 = `/vault-save`(vault-bridge 신설), `/capture`·`/note`는 폐지.** 하나의 입구가 저작 주체로만
  기계적으로 갈린다: 원문 그대로 가져온 것(URL·붙여넣은 원문·세션 덤프) → `sources/`, 내가 쓴 서술 →
  `notes/`. 정제도로 나누지 않으므로 "capture와 note 중 뭘 쓰지"라는 판단이 입구에서 사라진다.
- **입구가 vault-bridge인 이유**: B는 프로젝트에서 일하다 자료를 넣는 층이라 ③ delivery I/O 기판에 붙는
  게 맞다. OVM은 **사서**로 남는다 — 컴파일(`/wiki`)·감사(`/audit`)·뷰(`/base`), 즉 들어온 다음의 일.
  신설이라 #102 ADR 폐기가 아니고(입구 스킬이 새로 생긴 것), OVM 정체성도 안 바뀌며, 프로젝트 어디서든
  호출 가능해진다 — 셋이 동시에 성립한다.
- **`--type decision`은 KEEP으로 확정 (#477 미결 2, 2026-08-04 판정)**: 볼트 재고를 실측한 결과
  `type: decision` 실물은 `.legacy/20_Projects/claude-kit/decision-2026-06-03-workflow-harness-architecture.md`
  단 1개뿐이었고, 이미 v4 마이그레이션 시점에 라이브 구조(`sources/`·`notes/`) 밖 `.legacy/`로 archive돼
  있었다. 그 내용(harness/leaf 단방향, goal-doc, retro E8 승격, 3-tier 규칙)은 문서 자체의 "Issue 매핑"
  절이 "기존 보강 후보"로 #99·#100·#108·#115·#119를 스스로 지목했고, "신규 후보"로 든 workflow-harness는
  같은 날 등록된 #122(신규 플러그인)와 주제가 일치한다(문서가 #122를 번호로 인용하진 않는다 — 정정,
  fresh-context 리뷰). 그 아키텍처(⑤ 자체 하네스·retro E8 승격)는
  이후 #282(2026-06-28, native `/goal`로 retire)·#480(E8 승격 기계 제거)로 더 나아가 폐기까지 됐다 —
  **이슈 흡수로 이미 종결**, 마이그레이션 불필요. 라이브 B층엔 `type: decision` 실물이 0개라 `--type decision`
  능력 자체의 존폐만 남는데, 레포 바운드 결정은 §10 라우팅으로 계속 이슈로 가고 이 플래그는 레포 비바운드
  범용 결정(예: 개인 도구 선택)에만 쓰이므로 **KEEP** — 삭제하면 그 쓰임이 갈 곳이 없어진다.

### 5.1 두-볼트(A/B) 목적 분리 (discovery 교정, #354)

A(wiki)와 B는 **연동은 가능하되 목적이 다른 별개 공간**이다 — 이 둘을 하나의 승급 파이프라인처럼 읽으면
안 된다(승급 파이프라인 자체가 §5에서 폐기됐다).

- **A**: LLM이 자율 컴파일하는 도메인 지식, AI recall이 소비자, 항상 살아있음(§4). B의 존폐와 무관하다.
- **B**: 인간이 나중에 꺼내 쓰려고 넣어둔 참고자료. A의 위생(§7 self-audit)과는 애초에 무관하다 — B의
  용도가 죽어도(§13) A 위생은 B를 경유한 적이 없으므로 영향받지 않는다.
- 두 공간을 섞어 쓰지 않는다 — A에 인간 전용 서사를 넣거나 B에 AI self-compounding을 넣지 않는다. 연동은
  다음 절의 링크only 원칙으로만 이뤄진다.

---

## 6. 승격 게이트 — 폐기 (2026-08-02 #477/#480). 남은 코드도 같은 날 정리 완료

§5의 결정 1로 **B 내부 promotion 게이트(raw/draft → evergreen)는 폐기됐다.** 이 절이 규정하던 것 —
audit E8 후보 제시 + retro의 인간 yes/no 확정 + frontmatter status 전이 — 은 전부 무효다. A(wiki)→B
자동 distillation은 애초에 만들어진 적이 없고(§U2 정정, 2026-07-11, #215), 이제 새로 지을 이유도 없다.

- **이번 변경에서 같이 뺀 것**: E2 필수 필드에서 `status`(v4 §3.3 status machine에 딸려 있던 요구). 새
  파일이 `status:`를 안 쓰는데 audit이 그걸 Critical로 잡으면 문서와 코드가 첫날부터 어긋난다.
- **후속에서 마저 뺀 것 (2026-08-02, #480 완료)**: audit **E7**(`stale_draft`)·**E8**(`promotion_candidate`),
  `generate-manifest.py`의 `_compute_promotion_candidate`(+ 관련 env 임계값), retro Phase 2 PROMOTE,
  `e8-candidates.py`, `vault-commit-message.py`의 promote 메시지 분기 — 딸린 테스트·픽스처·DoD 기대값·
  `docs/VALIDATION.md`·`reference/vault-audit-rules.md`까지 한 덩어리로 정리됐다. `generate-manifest.py`가
  건네주는 매니페스트를 읽는 코드를 고치는 김에, 4일째 무음 정지 중이던 SessionStart 훅의 macOS
  `timeout` 부재 버그(#484)도 선행 조건으로 같이 고쳤다. E7은 새 파일에 `status: draft`가 없어 발화한
  적이 없었고, E8은 status를 안 보고 `type`+refs/access로만 계산해 **폐기된 게이트의 후보를 계속
  띄우고** 있었다(#435) — 대상 자체가 사라졌으므로 #435는 종결 대상.
- **inbox stale(E6)은 아직 남아 있다**: B가 참고자료 창고면 `inbox/`는 임시 대기열이 아니라 영구
  보관처인데 E6은 나이로 stale을 잡는다. 이건 폴더 3분할(`inbox`→`sources`, #477 하위 B)과 한 덩어리라
  거기서 같이 처리한다.

---

## 7. U3 오염 복리 방어 — audit wiki self-audit + provenance

compounding은 노이즈에게도 복리. "검토를 AI에 위임"한 그 위임을 신뢰할 장치가 설계의 핵심:

- **provenance 추적**: 모든 `--save` 페이지가 `provenance:`(생성 query/session) 보유 → 나쁜 합성을 출처로 역추적.
- **wiki self-audit**: OVM audit를 `wiki/`로 확장 — 페이지 간 **모순 검출** + stale/orphan + provenance 결손 플래그.
  audit가 이미 E1~E11 검출 엔진이라 wiki 검사 E-rule 추가가 자연스럽다.
- **주기**: audit 호출 시점(v4 §9.1 brain화 의식)에 일괄. 항상-on 아님.

---

## 8. U4 recall/재사용 지표 — 측정 게이트 폐기, 1회 build-verify로 대체 (2026-07-10, #267)

- **지표 정의(유효)**: 페이지 수(성장) ❌ → **wiki 페이지 recall/재사용 이벤트**(vault-searcher가 wiki 페이지를
  실제 hit한 횟수) ✅. "양이 아니라 가치"라는 프레이밍 자체는 살아 있다 — 폐기된 건 이걸 재려던 절차다.
- **폐기(#267 "방향 전환" 코멘트, 2026-07-10)**: 코멘트가 이름 붙여 폐기한 건 네 항목이다 — 재측정 2주
  타임박스·recall 인용 카운트·살림/retire 이원 갈래·"owner 자기관찰로 인용 ≥1 확정" 완료조건. 본 섹션이
  전제해온 "telemetry **Option B**(cross-project 가시성)를 먼저 짓고 그 위에서 정식 계측" 틀은 이 네 항목에
  명시적으로 들어 있진 않다 — 이건 이 문서의 추론이되, 같은 스레드의 별도 "대체 = build(measure 아님)"
  코멘트(Option B로 게이트되던 계측을 1회 build-verify로 갈음)가 뒷받침한다. owner: "개발 마일스톤을 다
  측정기반으로 바꾸는 것"은 원하는 방향이 아니다.
- **대체 = 1회 build-verify(완료)**: Option B 없이, vault-searcher recall-first 트리거를 land하고(PR #337)
  평범한 도메인 질문 1회로 실제 발화하는지 end-to-end 확인 — 독립 서브에이전트가 트리거 조건 충족 +
  답변이 실제 wiki/notes 파일과 일치(환각 아님) 둘 다 PASS 판정. 조직적 사용량 집계가 아니라 "작동하는지"만
  보는 build-verify다.
- **결론**: recall/재사용이라는 *지표 정의*는 이 문서에 여전히 유효하지만, 그걸 상시 계측하는 인프라
  (telemetry Option B)는 더 이상 U4의 전제도 목표도 아니다. 필요해지면 그때 git log/session transcript
  같은 기존 기록을 사후에 뒤진다(§13과 동일 원칙). #202(retro 큐레이션)는 자기 몫의 Option B 의존을 별도
  트랙으로 그대로 유지한다.

---

## 9. 구현 위치 (U5) — 신규 플러그인 0, OVM 확장 + vault-bridge I/O 재사용

레이어 모델(claude-kit-boundary.md): ③딜리버리=vault-bridge, ④지식베이스=OVM. wiki(A)는 본질이 ④ 지식
상주·컴파일·감사라 **OVM의 일**이다.

| 관심사 | 귀속 |
|---|---|
| wiki(A) 컴파일·링크·일관성·self-audit | **OVM 확장**(audit가 E1~E11 보유) |
| ~~B 내부 promotion 게이트~~ | **폐기**(§6, #480) — 귀속처 자체가 없어졌다 |
| B 입구(참고자료 저장) | **vault-bridge `/vault-save`**(§5, #480) — 프로젝트에서 호출 |
| B 사서 일(감사·뷰) | **OVM** `/audit`·`/base` — 들어온 다음의 일. `/base recent`는 폴더 무관이라 A도 섞여 나옴(§3) |
| wiki read(AI recall) 인덱스 | **vault-bridge manifest 재용도** |
| wiki read 위임 | **vault-bridge vault-searcher**(haiku, recall 정렬 完) |
| A `--save` 진입점(`/wiki`) | **OVM skill**(호출형), hook 아님 |

- **신규 플러그인 기각**: vault 도메인 3분할은 MECE 흐림 + CON-5 단방향 위험. A는 OVM 내부 capability로 추가
  (leaf 내부 확장 = 경계 무손상).
- **CON-5 무손상**: harness(⑤)는 여전히 leaf OUTPUT만 읽는다. wiki는 leaf 내부 기능.

---

## 10. repo↔vault 경계 (U7) — 2단계 결정트리 (decision-check 선행 + 기존 이분법)

**정정(2026-07-11, #215)**: 이전 단일 테스트("다른 레포에서도 참인가")는 §3이 이미 선언한 3번째 목적지
(decision류 → GitHub 이슈, B로도 AGENTS.md로도 안 감)를 반영하지 못했다. `--save` 시점 라우팅은 **먼저
decision 여부를 걸러낸 뒤** 남은 것에만 기존 이분법을 적용하는 2단계 트리다.

**1단계 — 레포 바운드 decision인가?**
"이게 *이 레포의* 설계/아키텍처 결정(GitHub 이슈 trail이 필요한 것)인가?" — 예 → **GitHub 이슈**로 간다,
wiki에는 쓰지 않는다. 이 레포에 안 묶인 판단(범용 방법론 선택 등)은 이 갈래가 아니다 — 그런 건 2단계로
내려간다.

**2단계 — (decision이 아닐 때만) 다른 레포에서도 참인가?**
- **vault wiki A** = 레포 초월 *도메인 지식*(다른 레포에서도 유효/참). 예: "Defuddle CLI는 H1을 title로 추출".
- **repo AGENTS.md** = *이* 레포 구조 맵(어디에 뭐가 있나). 레포 밖에선 무의미.
- 예→wiki A, 아니오(이 레포 구조)→AGENTS.md/deepinit.

**목적지 3개 요약**: decision(레포 바운드) → GitHub 이슈 · 도메인 지식(레포 초월) → wiki A · 구조 지식(이
레포 한정) → AGENTS.md. §3의 레이어 표와 정합.

**조각별 라우팅**: 코드 조사 중 세 종류가 섞여 나오면 **조각별로** 라우팅한다(한 `--save`/`/wiki` 호출에
한 종류) — 각 fragment에 위 2단계 트리를 독립 적용해 목적지를 나누고, decision으로 판정된 fragment는 wiki에
쓰지 않고 GitHub 이슈로 안내한다(emission-only, `wiki` skill Phase 2 참조).

---

## 11. v4 자산 정합 (U6)

| v4 자산 | A(wiki) | B(notes) |
|---|---|---|
| `type:` opt-in (§2.2) | `type: wiki` 부여 | `capture`/`note`/`decision` = 폴더 마커 |
| status machine (§3.3) | **밖**(인간 검토 액션 없음) | **폐기**(§5, #480) |
| provenance | `provenance:` 必(U3) | **必**(§5, #480 — 인출 쪽 방어선) |
| 항상-on push 없음 (§9.1) | **보존** — `--save`=게이트된 명시 액션 | 보존 |
| recall 중심 (§2.3) | A의 존재 이유 그 자체 | — |
| git 통합 (§4) | 계승 | 계승 |
| 거부 목록 (§9.2 embedding/RAG 등) | **계승** — plain-md 유지, no embedding/`.db`(헌법) | 계승 |

> **정정(§U6, 2026-07-11, #215)**: "항상-on push 없음"과 §2의 "AI 자율 compounding"이 충돌하는 것처럼
> 보였던 건 구분축을 잘못 잡아서다 — 진짜 구분은 **트리거 주체**(사용자 vs AI)가 아니라 **이산성**(discrete
> gated action vs 상시-on 백그라운드 push)이다. `--save`/`/wiki`는 사용자든 AI든 명시적으로 호출하는 하나의
> 스킬 실행이라 항상 이산적 이벤트고, v4 §9.1이 막으려던 건 "아무 호출 없이 매 turn 자동으로 쓰는" 훅형
> push였다. AI가 스스로 "이거 wiki에 저장해야겠다" 판단해서 `/wiki`를 호출해도, 그 호출 자체가 이산 게이트라
> §9.1과 충돌하지 않는다. `wiki` skill PLAN 단계의 쓰기-전 확인(§4.1 정정 참조)은 이 이산 게이트 위에 얹힌
> 추가 안전장치이지, 원칙 충돌의 해소책이 아니다.

---

## 12. 보류분 결정 (DECISION.md "보류" 2건 통합)

- **save-session → inbox/ writer 유지, 단 재정정(2026-07-08 D1, 커밋 `f59f580`; 이후 #331로 커맨드 자체 retire).** record/quick
  모드와 `type: session` 산출은 폐기됐고, `/save-session`은 이제 `type: capture`를 inbox/에 씀(raw, 당시 `/capture`와
  동일 산출물). B(인간 검증 durable)가 아닌 건 그대로 — B 직행하면 "덤프 파이프"가 B로 부활 → **inbox/ 운반
  유지**(③ delivery CON-1 어댑터) 원칙은 안 바뀌었고, 내용은 당시 Model X(access_count 기준) promotion 후보로
  채굴 가능했으나(그 경로는 #480에서 폐기, §6) 직접 B-surface는 아니었다. #215 "축소" 결정과 정합(전면 kill 아님).
- **manifest → KEEP + 재용도.** ③ delivery staleness 추적 → **④ wiki recall 인덱스**로 재정의. #211 작업2
  (access-ranking) CLOSED — importance-ordered recall 지원. vault-searcher가 읽음.

---

## 13. 검증 계획 — 측정 게이트 폐기 (2026-07-09/10, #267)

원래 초안은 B 인간-읽기 목적을 1개월 관찰 클럭(retrieval-into-work ≥3 + 결정 변경 ≥1 통과 바, 미달 시
archive/A-only 확정)으로 재판할 계획이었다. **owner가 이 클럭을 공식 게이트로 돌리는 것 자체를 거부**했다
(#267 마지막 코멘트, 2026-07-09): "계측하는 건 큰 의미가 없고 시도하면서 나중에 로그를 뒤져보는 게 낫지,
이런 식으로 결정을 미루는 방향은 원하는 게 아니다." 같은 날 A recall 측정 게이트(§8 U4) 폐기 결정과 동일
원칙이 B에도 확장 적용됐다.

- **대체**: B는 필요하면 그냥 열어서 쓴다. 판단이 필요해지면(예: A-only로 완전히 좁힐지 재고) 그때
  git log/session transcript 같은 **기존 기록을 사후에** 뒤져 확인한다 — 별도 seed/측정 인프라를 먼저
  안 짓는다.
- **폐기된 것**: 1개월 관찰 클럭, pass/fail 임계값(retrieval-into-work ≥3, 결정 변경 ≥1), seed/cold-archive
  준비 절차. 이 문서의 이전 버전에 있던 해당 문구는 전부 무효.
- **fallback은 유지**: B 인간-읽기가 (측정이 아니라 판단으로) 죽는다고 판정되는 날이 와도 A는 영향받지
  않는다 — A의 위생은 §7 self-audit이 전담하며 애초에 B를 경유한 적이 없다(§5.1, §U2 정정). A는 B 판정과
  무관하게 항상 정당(§5.1).

---

## 14. 제약 / 헌법 정합

- **plain markdown 유지, no embedding/`.db`** — #211 reject 조항 + claude-kit-boundary.md file-over-app. Karpathy plain-md 정합.
- **CON-5 단방향**: harness→leaf만. wiki는 leaf(OVM/vault-bridge) 내부. 역방향 금지.
- **CON — A↔B = 링크only** (#354, discovery 발견 5 확정): A(wiki)와 B(notes)는 연동 시 **참조(wikilink)만,
  복사·동기화 없음.** repo→vault ferry를 죽인 원래 결론(§2 pull-mostly)을 볼트 *레이어 간*에도 그대로
  적용한 것. B 내부 promotion은 §6에서 폐기돼 이 CON이 다룰 전이 자체가 없어졌고, A→B distillation이
  언젠가 실제로 지어진다면(§15, 미구현) 그 설계도 이 링크only 원칙을 지켜야 한다는 뜻으로 유지한다.
  역방향(B→A로 인간 노트를 그대로 흡수)도
  금지 — A는 AI가 탐구 과정에서 합성한 지식만 먹는다(§4.2).
- **MECE**: wiki는 OVM(④) capability. vault-bridge(③)는 I/O 기판. 경계 무손상.
- **비가역 회피**: 기존 더미는 hard delete 아닌 cold archive. 삭제는 trash 경유(`rm` 금지).

---

## 15. 미결 / 별 트랙 (구현 아님 — 본 문서는 설계)

- ~~**구현은 별 세션**(goal G22 제약)~~ — 초판 제약. A는 #215~#344로, B는 #480으로 구현됐고, 이 문서는 그 구현의 명세다.
- ~~**#480 잔여 — 승격 기계 제거**(§6): audit E7/E8, `_compute_promotion_candidate`, retro PROMOTE,
  `e8-candidates.py`, `vault-commit-message.py` promote 분기.~~ — **완료 (2026-08-02).** 딸린
  테스트·픽스처·DoD 기대값·`docs/VALIDATION.md`·`reference/vault-audit-rules.md`까지 정합됐고,
  선행 조건이던 SessionStart 훅의 `timeout` 부재 버그(#484)도 같이 고쳤다. #435는 대상 소멸로 종결.
- ~~**#480 잔여 (후속 세션)**: 볼트 `type: decision` 처분 판정(#477 미결 2), `/wiki` 배치 정렬
  (#477 미결 3), 재고 `provenance:` 백필과 E2 확장.~~ — **완료 (2026-08-04, #477 정리 세션)**.
  미결 1(입구 frontmatter 규격)은 `/vault-save` 코드(`created`/`type`/`tags`/`provenance`, `status:` 없음)가
  이미 본 문서 §5와 정확히 일치해 재확인만으로 종결. 미결 2(decision 처분)는 §5의 KEEP 판정 참조. 미결 3
  (`/wiki` 배치)는 §9 표(`/wiki`=OVM skill, `/vault-save`=vault-bridge)가 이미 그 정렬 상태라 재확인만으로
  종결. `provenance:` 백필은 sources/notes/wiki 135개 파일을 git add-commit 이력(날짜+커밋 메시지)에서
  역산해 채웠고, 그 위에서 E2를 `provenance`까지 확장했다(`ovm-primitives.sh`·`audit-validate.py`·
  `reference/vault-audit-rules.md`, DoD 재검증 통과). 폴더 3분할(`inbox`→`sources`)은 #477 하위 B로 이미 완료.
- ~~**U4 측정(recall hit)**~~ — **완료.** 측정 게이트 폐기, 1회 build-verify로 대체(§8, PR #337, #267).
  상시 계측(telemetry Option B)은 여전히 미착수지만 더 이상 U4의 전제가 아니다.
- ~~**#94**(commands→skills): 살아남는 커맨드 셋 확정 후(#215 mooted 해소).~~ — **완료.**
  살아남는 셋(3개: `vault-link`/`vault-manifest-refresh`/`vault-commit`) 확정 조건이 이미 충족돼
  있었고(2026-07-09 코멘트), PR #364로 `commands/*.md` → `skills/` 마이그레이션 완료.
- ~~**wiki self-audit E-rule 구체**(U3)~~ — **완료.** E12a(결정론 staleness, `verified:` 나이 >
  `STALE_WIKI_DAYS`)는 #330/PR #334, E12b(cross-page 의미 모순, `--deep` opt-in)는 #336/PR #344로 각각
  landed·merged.
- ~~**`--save` skill 인터페이스**(U5): OVM skill 진입점의 정확한 시그니처·게이트 UX.~~ — **완료.**
  `obsidian-vault-manager/skills/wiki/SKILL.md`가 SYNTHESIZE → U7 ROUTE → DEDUP → PLAN → WRITE 5단계
  파이프라인으로 이미 구현·landed — PLAN 단계가 쓰기 전 인간 확인("one human glance")을 게이트로 둔다.
- ~~**U2 promotion 재작성 주체**~~ — **정정 완료(2026-07-11, #215).** "AI가 A-source에서 B초안을 뽑는다"는
  경로는 실제로 만들어진 적이 없었다(`generate-manifest.py`가 `type: wiki`를 promotion 후보에서 구조적으로
  제외) — §3/§5/§5.1/§6/§9/§14를 코드에 맞게 정정. B는 (그 시점 기준) 인간 직접 저작 + 자기 status 전이(E8)로만 정의됐고 — 이 정의는 이후 #480에서 참고자료 창고로 다시 바뀐다,
  A→B 자동 distillation은 미구현·미계획으로 남는다(원하면 별 세션에서 새로 설계).
- ~~**U6 항상-on 원칙 vs AI 자동 --save**~~ — **정정 완료(2026-07-11, #215).** 구분축을 트리거 주체에서
  이산성(discrete gated action vs 상시-on push)으로 교정(§11), `wiki` PLAN 단계의 쓰기-전 확인을 "판단형
  검토"가 아닌 "저비용 눈길"로 좁혀 §4.1과 정합(코드는 그대로, 문서 표현만 정정).
- ~~**U7 repo↔vault 경계 라우팅**~~ — **정정 완료(2026-07-11, #215).** §10을 2단계 결정트리(decision→GitHub
  이슈 선행 체크 + 기존 이분법)로 확장해 §3의 3-way 구조와 정합. `wiki/SKILL.md` Phase 2(U7 ROUTE)도 동일
  트리로 구현 갱신.

---

## 16. `/vault-link` 처리 방향 — KEEP, B 전용으로 스코프 확정 (#354)

discovery 발견 4가 제기한 의문("A-only에선 전역 wiki라 프로젝트 바인딩 자체가 불필요해질 수 있다")을
검토한 결론: **`/vault-link`는 유지한다.**

- **실제 코드 역할 재확인**: `/vault-link`가 만드는 `.vault-link`는 "어느 볼트를 쓸지" 고르는 볼트-선택
  라우팅이 **아니다** — 볼트 루트는 항상 하나(`VAULT_BRIDGE_VAULT_ROOT` > `VAULT_BRIDGE_VAULT_PATH` >
  `~/vault` 3단 우선순위, 단일 해석). `.vault-link`의 `vault_path`가 실제로 하는 일은 **`notes/{project}/`
  서브폴더로 검색 범위를 좁히는 것**뿐인데, `vault-searcher.md`(Mode 2)가 이 값을 읽어 `search_root`를
  스코프한다 — 이미 살아서 쓰이는 메커니즘이지 죽은 코드가 아니다.
- **A(wiki)는 원래부터 무관**: wiki는 §4처럼 항상 전역(레포 초월 도메인 지식)이라 애초에 프로젝트
  바인딩 대상이 아니었다. `/vault-link`의 스코프는 처음부터 **B(notes/) 서브폴더 배치·검색 좁히기뿐**이고,
  이 결정은 그 사실을 명문화하는 것이지 새로 좁히는 게 아니다.
- **세션-레벨 볼트 셀렉터**(발견 4가 언급한 "진짜 남은 니즈")는 실사용 증거가 없어 YAGNI로 defer한다 —
  필요해지면 그때 짓는다.
