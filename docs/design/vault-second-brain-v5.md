# Vault Second Brain 설계안 v5 — LLM-compiled wiki (A 主) + earned-promotion notes (B probation)

> 작성일: 2026-06-23 · 상태: **초안 (linchpin L1·L2 owner 합의 완료, 구현은 별 세션)** · 커밋은 owner 확인 후
> 대체 대상: `vault-second-brain-v4.md` (인간 저작 second-brain 모델)
> 방향 출처: #215(④ 재설계, 정전) · `docs/discussions/20260612_vault-llm-wiki-redesign/`(SUMMARY+UNRESOLVED+RESOLUTIONS-draft)
> · `docs/discussions/20260623_vault-debloat-reckoning/DECISION.md`(5레이어) · 메모리 `project_vault_usage_reality`
> 상속: v4의 type opt-in(§2.2)·status machine(§3.3)·recall 중심(§2.3)·git 통합·거부목록(§9)은 **계승**.
> 이 문서는 *바뀌는 것*만 명세하고, 안 바뀌는 기계는 v4를 참조한다.

---

## 0. 한 줄

vault의 무게중심을 **인간 저작(v4)에서 LLM 컴파일(v5)로** 옮긴다. **A(wiki) = LLM이 자율 컴파일하는
도메인 지식, AI recall이 主.** **B(notes) = promotion에서 살아남은 잔여물**이지 미리 짓는 레이어가 아니다 —
인간-읽기 목적은 **default OFF, 한 달 재판**으로 존재를 증명해야 한다(L1). second-brain은 "인간이 나중에
읽는다"에서 "AI가 인간 대신 읽고 recall한다"로 재정의된다.

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
미검증이다. 그러므로 **A를 主로 풀로 짓고, B는 "증명해야 사는" probation 타겟**으로 둔다. (L1 owner 합의.)

---

## 2. 채택 모델 — Karpathy LLM Wiki

(gist 2026-04-03.) "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."

- 노트는 *인간이 읽으라고*가 아니라 *모델이 인간 대신 읽으라고* 최적화된 plain markdown KB.
- LLM이 자율적으로 쓰고·링크·분류·일관성 체크. **생산량>검토대역폭 병목을 구조적으로 우회**(A의 핵심 이점).
- loop = LLM이 "뭐가 빠졌나" self-ask(query responder 아닌 knowledge compiler) + `--save`로 합성 지식 적재 = compounding.

> "codebase"는 비유 — 지식이 코드처럼 구조화·재사용된다는 뜻. 코드는 repo가 정본(SSOT). wiki엔 코드에서
> *추출된 지식*만(§9 repo↔vault 경계). v4 §385 교훈 정합: "capture 자동화만으론 brain 불가, **recall이 핵심**."

---

## 3. 5레이어 분리 (출처가 안 섞이는 게 1차 원칙)

매립의 근본이 "출처 뒤섞임"이므로 레이어 분리가 1차 축. (DECISION.md §2.2 표.)

| 레이어 | 내용 | 소비자 | 저작 | 위치 |
|---|---|---|---|---|
| **repo** | 코드 + 코드구조맵(AGENTS.md) | AI+인간 | — | git repo |
| **vault wiki A** | 도메인 지식(작업하다 알게 된 것) | **AI recall** + 인간 | AI 자율 compounding | `vault/wiki/` |
| **vault notes B** | promotion 잔여물(고신호 큐레이션) | A 위생(必) + 인간(probation) | AI 초안+인간 확정 | `vault/notes/` |
| **rules** | work-policy("어떻게 일하나") | AI+인간 | 인간, 안정 | `~/.claude/rules`, `rules/RULES.md` |
| **memory** | 프로젝트 사실 | AI | auto | `~/.claude/projects/.../memory` |

- **policy/memory ≠ wiki**: wiki는 휘발·축적·AI 저작, policy는 안정·권위·인간 저작 — 성격 반대.
  policy를 wiki에 넣으면 U3(오염 복리)로 규칙 변질 + 출처 분리 위반.
- **decision은 GitHub 이슈가 정전**(trail 정책): 레포 바운드 decision은 이슈로 간다. B로 안 간다.

---

## 4. A (wiki) 설계 — 主 레이어

### 4.1 Frontmatter — `type: wiki` + provenance, status machine 밖

```yaml
type: wiki                 # v4 §2.2 opt-in — 관리·recall 가시성 위해 부여
created: YYYY-MM-DD
tags: [{domain}]
provenance: {session/query}  # U3 추적용 必 — 어느 탐구가 이 페이지를 낳았나
```

- **status machine 밖**: A엔 인간 검토 액션이 없다(AI 저작). raw→draft→evergreen은 B의 일(인간 검토 선언).
  A는 provenance 추적 AI 페이지지 검토-status 페이지가 아니다.

### 4.2 먹이 = query-driven compounding (게이트된 명시 `--save`)

- 미리 정한 소스 폴더가 아니라 **사용자의 탐구 흐름 그 자체**가 먹이. 조사·결정 중 LLM이 합성한 답을 wiki 페이지로 `--save`.
- **`--save`는 자동이 아니라 게이트된 컴파일 액션**(skill 호출, 사용자/AI 명시 발동). v4 §9.1 "항상-on push 없음"
  보존 — brain화는 명시 시점에. 코드를 긁어 넣는 게 아니라 작업하다 *알게 된 것*이 마찰 0으로 wiki가 된다.
- 진입점은 OVM skill(§7). hook 아님.

### 4.3 recall = AI가 인간 대신 읽음

- vault-searcher(haiku) + manifest access-ranking 인덱스로 wiki 페이지 recall. **#211 작업2(access-ranking)
  CLOSED라 인프라 完.** manifest는 ③ delivery staleness 추적에서 **④ wiki recall 인덱스로 재용도**(§10 보류분).

---

## 5. B (notes) 설계 — earned promotion-residue, probation (L1)

B는 **미리 짓는 레이어가 아니라 promotion에서 살아남은 것**으로 정의된다. 두 목적을 분리한다:

- **B-as-promotion-residue (A 위생용)**: A의 노이즈를 낮추는 고신호 큐레이션 잔여물. **인간이 안 읽어도
  A 위생(U3)으로 독립 정당.** → A→B promotion *메커니즘*은 KEEP.
- **B-as-human-read-layer (인간 읽기)**: **재판 대상, default OFF.** §13 retrieval-into-work 테스트 통과해야 삶.

```yaml
type: note | decision      # v4 §3.3 — note/decision만 evergreen 자격
status: raw|draft|evergreen|archived   # v4 status machine 그대로 (전이 주체=인간)
```

- B는 v4 status machine을 **그대로** 쓴다. status 변경 액션 = "내가 검토했다"(v4 §2.4) = promotion 게이트 의미.

---

## 6. A→B promotion 게이트 — audit E8 + AI 초안+인간 확정 (L2)

- **후보 제시**: AI(OVM audit E8 재배치 — raw→evergreen 후보). **승인**: 인간 yes/no.
- **빈도**: 매 세션 금지(검토 대역폭 병목 = B 죽인 원인 재발). **retro의 budget-capped, user-confirmed 흐름에
  올라탐**(`RETRO_BUDGET=10` 상한 존재). 새 always-on 트리거 0.
- **재작성 주체 (L2 owner 합의)**: **AI 초안 + 인간 확정/손질.** AI가 A-source에서 B노트 초안을 뽑고, 인간은
  게이트에서 확정/손질만. "검증=확정 액션"이라 v4 §2.4와 동형이고, 검토 대역폭이 현실적(B를 죽인 대역폭 병목을
  안 되살림). **복사 아닌 distillation** — 단방향, 동기화 금지(dual-source 부활 방지).

---

## 7. U3 오염 복리 방어 — audit wiki self-audit + provenance

compounding은 노이즈에게도 복리. "검토를 AI에 위임"한 그 위임을 신뢰할 장치가 설계의 핵심:

- **provenance 추적**: 모든 `--save` 페이지가 `provenance:`(생성 query/session) 보유 → 나쁜 합성을 출처로 역추적.
- **wiki self-audit**: OVM audit를 `wiki/`로 확장 — 페이지 간 **모순 검출** + stale/orphan + provenance 결손 플래그.
  audit가 이미 E1~E11 검출 엔진이라 wiki 검사 E-rule 추가가 자연스럽다.
- **주기**: audit 호출 시점(v4 §9.1 brain화 의식)에 일괄. 항상-on 아님.

---

## 8. U4 양≠가치 측정 — recall hit/재사용 (telemetry Option B 게이트)

- 측정 대상: 페이지 수(성장) ❌ → **wiki 페이지 recall/재사용 이벤트**(vault-searcher가 wiki 페이지를 실제 hit한 횟수) ✅.
- **의존**: cross-project 가시성 = telemetry **Option B**. Option A(in-repo)는 레포 밖 세션 못 봄 → wiki recall 측정 불가.
  #202(retro 큐레이션)·#215 "양≠가치"가 같은 Option B 의존 공유.
- **결론**: U4 측정은 Option B 선행 게이트 — **지금 못 지음.** 본 문서는 "지표 = recall hit/재사용, Option B 의존"
  명세만 남기고 구현은 별 트랙(#202 공동).

---

## 9. 구현 위치 (U5) — 신규 플러그인 0, OVM 확장 + vault-bridge I/O 재사용

레이어 모델(claude-kit-boundary.md): ③딜리버리=vault-bridge, ④지식베이스=OVM. wiki(A)는 본질이 ④ 지식
상주·컴파일·감사라 **OVM의 일**이다.

| 관심사 | 귀속 |
|---|---|
| wiki(A) 컴파일·링크·일관성·self-audit | **OVM 확장**(audit가 E1~E11 보유) |
| A→B promotion 게이트 | **OVM audit E8 재배치**(v4 status machine 재사용) |
| wiki read(AI recall) 인덱스 | **vault-bridge manifest 재용도** |
| wiki read 위임 | **vault-bridge vault-searcher**(haiku, recall 정렬 完) |
| `--save` 진입점 | **OVM skill**(호출형), hook 아님 |

- **신규 플러그인 기각**: vault 도메인 3분할은 MECE 흐림 + CON-5 단방향 위험. A는 OVM 내부 capability로 추가
  (leaf 내부 확장 = 경계 무손상).
- **CON-5 무손상**: harness(⑤)는 여전히 leaf OUTPUT만 읽는다. wiki는 leaf 내부 기능.

---

## 10. repo↔vault 경계 (U7) — "다른 레포에서도 참인가" 단일 테스트

- **vault wiki A** = 레포 초월 *도메인 지식*(다른 레포에서도 유효/참). 예: "Defuddle CLI는 H1을 title로 추출".
- **repo AGENTS.md** = *이* 레포 구조 맵(어디에 뭐가 있나). 레포 밖에선 무의미.
- **라우팅 게이트(`--save` 시점 1줄)**: "이게 다른 레포에서도 참/유용한가?" 예→wiki A, 아니오(이 레포 구조)→AGENTS.md/deepinit.
- 누수 방어: 코드 조사 중 두 종류가 섞여 나오면 **조각별로** 라우팅(한 `--save`에 한 종류).

---

## 11. v4 자산 정합 (U6)

| v4 자산 | A(wiki) | B(notes) |
|---|---|---|
| `type:` opt-in (§2.2) | `type: wiki` 부여 | `type: note`/`decision` 그대로 |
| status machine (§3.3) | **밖**(인간 검토 액션 없음) | **그대로** |
| provenance | `provenance:` 必(U3) | 불요(인간 확정) |
| 항상-on push 없음 (§9.1) | **보존** — `--save`=게이트된 명시 액션 | 보존 |
| recall 중심 (§2.3) | A의 존재 이유 그 자체 | — |
| git 통합 (§4) | 계승 | 계승 |
| 거부 목록 (§9.2 embedding/RAG 등) | **계승** — plain-md 유지, no embedding/`.db`(헌법) | 계승 |

---

## 12. 보류분 결정 (DECISION.md "보류" 2건 통합)

- **save-session record/quick → inbox/ writer 유지.** `type: session`을 inbox/에 씀(raw). B(인간 검증 durable)가
  아님. B 직행하면 "덤프 파이프"가 B로 부활 → **inbox/ 운반 유지**(③ delivery CON-1 어댑터), 내용은 promotion으로
  나중 *채굴* 가능하나 직접 B-surface 아님. #215 "축소" 결정과 정합(전면 kill 아님).
- **manifest → KEEP + 재용도.** ③ delivery staleness 추적 → **④ wiki recall 인덱스**로 재정의. #211 작업2
  (access-ranking) CLOSED — importance-ordered recall 지원. vault-searcher가 읽음.

---

## 13. 검증 계획 (1개월) + fallback

B 인간-읽기 목적의 재판. "열었나"(novelty/Hawthorne confound) 폐기, **retrieval-into-work**로 측정:

- **seed**: 기존 더미 1회 채굴분(decision만, AI 후보 + 인간 yes/no) + cold archive(hard delete 아님). 같은
  큐레이션 content가 두 경로로 닿게: **ask-Claude(A recall) vs open-Obsidian(B browse).**
- **측정**: organic retrieval = B/A 항목이 *실제* 작업 질문에 끌려 들어오고 세션 결과가 인용/변경. novelty browse 폐기.
- **판별자**: 과거 결정 필요 시 owner가 어느 경로? 늘 A·B 안 브라우즈 → "mixing 원인" 반증, 수요=A. 깨끗한 B를
  진짜 브라우즈하고 작업 바뀜 → "mixing→clean→read" 확증.
- **통과 바**: browse 경로 retrieval-into-work ≥3 + 결정 변경 ≥1. 미만이면 B 인간-읽기 사망 → archive, **A-only 확정.**
- **fallback**: B 인간-읽기 폐기해도 A→B promotion-residue 메커니즘(A 위생)은 유지. A는 독립적으로 정당.

---

## 14. 제약 / 헌법 정합

- **plain markdown 유지, no embedding/`.db`** — #211 reject 조항 + claude-kit-boundary.md file-over-app. Karpathy plain-md 정합.
- **CON-5 단방향**: harness→leaf만. wiki는 leaf(OVM/vault-bridge) 내부. 역방향 금지.
- **MECE**: wiki는 OVM(④) capability. vault-bridge(③)는 I/O 기판. 경계 무손상.
- **비가역 회피**: 기존 더미는 hard delete 아닌 cold archive. 삭제는 trash 경유(P4).

---

## 15. 미결 / 별 트랙 (구현 아님 — 본 문서는 설계)

- **구현은 별 세션** (goal G22 제약). 본 문서는 합의된 설계지 코드 변경 아님.
- **U4 측정(recall hit)**: telemetry Option B 선행 게이트 — 지금 불가, #202 공동.
- **#94**(commands→skills): 살아남는 커맨드 셋 확정 후(#215 mooted 해소).
- **wiki self-audit E-rule 구체**(U3): audit 확장 구현 시 E-rule 번호·검출 로직 명세.
- **`--save` skill 인터페이스**(U5): OVM skill 진입점의 정확한 시그니처·게이트 UX.
