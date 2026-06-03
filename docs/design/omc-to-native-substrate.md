# OMC → native substrate 매핑 + strangler 점진 대체 경로

**Issue**: #132 · **Epic**: #108 (⑤ 실행 트랙) · **선행**: #99(경계 A), adversarial-review
**확정**: #122 thin 레이어 범위 (이 문서가 그 게이트)
**Status**: design · **Created**: 2026-06-03

---

## 0. 방향 (adversarial 통과 형태)

`docs/adversarial-review/2026-06-03-harness-ownership.md`에서 strong-form(전면 OMC 자체 대체 = 옵션 B)이 기각됐어요. 채택된 narrow-form은 이거예요:

> **Claude Code 네이티브(dynamic Workflow, /goal, agents, hooks)를 substrate로 한 경량 하네스로, OMC를 strangler 점진 대체한다.**

이 문서의 역할은 **무엇을 native가 대체/위임하고, 무엇이 gap으로 남는지** 확정하는 거예요. 그래야 #122 thin 레이어가 native가 이미 주는 걸 다시 짓지 않거든요(adversarial native-supersession 방어 = 이 매핑이 게이트).

핵심 결론 한 줄: **OMC ⑤ capability 8종 중 6종은 native가 흡수(full/partial), gap은 정확히 2종 — 슬라이스→스킬 바인딩 라우팅 + D5 헌법 invariant enforcement.** 이 2종이 #122 thin 레이어 2-구성과 1:1.

---

## 1. OMC ⑤ Capability 인벤토리

현재 OMC가 ⑤(실행/doing/오케스트레이션) 레이어에서 제공하는 기능을 8개 capability로 묶었어요. (출처: `omc-reference` 스킬 — Agent Catalog · Skills Registry · Tools Reference · Team Pipeline.)

| ID | Capability | OMC 구현체 | 설명 |
|----|-----------|-----------|------|
| **C1** | 자율 goal 루프 | `ultragoal` (+ Claude `/goal` 핸드오프) | 완료조건까지 세션 자율 진행. ultragoal은 plan/ledger를 `.omc/ultragoal`에 영속 → durable multi-goal |
| **C2** | 지속 반복 루프 | `ralph` · `ultrawork` · `ultraqa` · `autopilot` · `autoresearch` · `self-improve` | "완료까지 멈추지 않음" + 검증 reviewer 루프. ralph=until-done+verify, ultrawork=고throughput 병렬, ultraqa=test-fix 사이클 |
| **C3** | 에이전트 오케스트레이션 + 모델 라우팅 | 19종 named agent (`executor`·`verifier`·`code-reviewer`·`planner`·`architect`·`debugger`…) + haiku/sonnet/opus 라우팅 | 역할별 서브에이전트 위임 + 모델 티어 선택 |
| **C4** | 병렬 fan-out / 파이프라인 | `ultrawork` 병렬 레인 · `/team N:executor` | 독립 작업 동시 실행, 결과 수집 |
| **C5** | 팀 오케스트레이션 | team pipeline (`team-plan → team-prd → team-exec → team-verify → team-fix`) · CLI teams (codex/gemini) | 공유 task list 위 N 에이전트 협업 |
| **C6** | 상태 관리 / 메모리 | `state_*` · `notepad_*` · `project_memory_*` · `shared_memory_*` · `wiki_*` · `.omc/state/` | 세션 간/내 구조화 상태·노트·KV·위키 영속 |
| **C7** | 훅 트리거 | `[MAGIC KEYWORD]` 주입 · `boulder` 마커 · `<remember>` 영속 · kill switch(`DISABLE_OMC`) | 턴 경계에서 systemMessage·additionalContext 주입으로 행동 유도 |
| **C8** | 검증 게이트 | `verifier` · `code-reviewer` 에이전트 + "authoring≠review / self-approval 금지" 정책 | 저작과 리뷰를 별도 패스로 분리, 완료 전 evidence 수집 |

> **인벤토리 경계 주의**: "슬라이스→스킬 바인딩 라우팅"은 OMC가 *선언적으로 제공하지 않는* 기능이라 위 인벤토리에 없어요. 그건 재설계가 새로 도입하는 ⑤ 표면이고, §4 gap으로 분류돼요(OMC capability 대체가 아니라 net-new gap).

---

## 2. Native substrate 프리미티브 + 실측 한계

#132 Acceptance "각 native 기능의 실측 한계 기록"에 대응해요. 한계마다 근거 티어를 명시했어요 — 추측으로 메우지 않으려고요.

**근거 티어**: `[SPEC]` = 메인 세션의 Claude Code 도구 정의(Workflow/Agent/ScheduleWakeup 등)에 명시된 값 — authoritative하나 서브에이전트·레포 grep으로는 안 보여서 출처를 행마다 병기 · `[WORKAROUND]` = OMC가 그 한계 우회용 기능을 만든 정황증거 · `[CONFIRMED]` = 세션/사용자·파일 실측 확인(날짜) · `[DOGFOOD]` = 미검증, 실착수 시 실측 필요.

| ID | Native 프리미티브 | 제공 | 실측 한계 | 근거 |
|----|------------------|------|----------|------|
| **N1** | dynamic Workflow | `agent()`/`parallel()`/`pipeline()`/`phase()`/`log()`, schema 구조화 출력, worktree 격리, budget, resume, nested workflow | 동시 에이전트 cap = `min(16, cores−2)`; 총 1000 에이전트; **중첩 1단계**(workflow 안 workflow 1회); `Date.now`/`Math.random`/argless `new Date()` 사용 불가; **resume 동일 세션 한정** | `[SPEC]` (Workflow 도구 정의 — 메인 세션 도구 명세 기재값) |
| **N2** | `/goal` | 세션 자율 진행 + 완료조건 Stop 훅 평가, 충족 시 auto-clear | **세션 싱글톤 — 1 세션 1 활성 goal, 동시 다중 goal 불가**; 완료조건이 **freeform 텍스트** — 구조화 goal-doc을 슬라이스별 스킬에 바인딩하는 파싱은 native가 안 함 | `[CONFIRMED 2026-06-03]` + `[WORKAROUND]` (OMC `ultragoal`이 durable multi-goal/ledger 영속용으로 존재 = native가 multi-goal·영속을 안 줌의 방증) |
| **N3** | Agent / Task 도구 | 서브에이전트 spawn, `run_in_background`, `SendMessage`로 컨텍스트 이어 재호출, `agentType`(커스텀 에이전트 레지스트리), worktree 격리 | 서브에이전트 **최종 메시지는 호출자에게만** 반환(사용자 비노출) → **중간 critique 과정 관찰 불가**(INV-2 enforce 설계 제약, §4.2 참조); 새 Agent 호출은 fresh context(SendMessage만 컨텍스트 유지) | `[SPEC]` (Agent 도구 정의) |
| **N4** | hooks | 이벤트 12종↑: PreToolUse·PermissionRequest·PostToolUse·PostToolUseFailure·Stop·SubagentStart·SubagentStop·SessionStart·SessionEnd·UserPromptSubmit·PreCompact·Notification. `systemMessage`/`additionalContext` emit, PreToolUse·PermissionRequest는 차단 가능 | 이벤트 셋은 native가 정의(플러그인이 임의 이벤트 추가 불가); PreToolUse/PermissionRequest가 **차단**은 하지만 "self-approval인지/격리됐는지" 같은 **의미 판정은 native가 안 함 — 핸들러 로직이 소유**; soft warning은 비차단 | `[CONFIRMED 2026-06-03]` (OMC `hooks.json` 11종 실측 + Notification 도구 명세; 본 세션 SubagentStart 훅 수신 확인) |
| **N5** | Skill | 자동 검색(description 기반), `context: fork`(별도 에이전트 실행), `agent:`, `model:` 지정 | 트리거는 description 매칭 — 결정적 라우팅 아님(LLM 판단); fork 시 메인 컨텍스트 비공유 | `[SPEC]` |
| **N6** | CronCreate / ScheduleWakeup | 스케줄·재개·self-paced 루프 | `delaySeconds` clamp `[60, 3600]`; 프롬프트 캐시 TTL 5분(300s 넘기면 캐시 미스) | `[SPEC]` (ScheduleWakeup 도구 정의) |
| **N7** | Team 도구 | `TeamCreate`/`TeamDelete`/`SendMessage`/`Task*` — **이게 OMC team pipeline의 substrate** | 조정 오버헤드 — 독립 병렬 레인이 정당화될 때만 | `[SPEC]` |
| **N8** | model 파라미터 / `/fast` | agent()/Task `model` 오버라이드, /fast(Opus 고속), effort 티어 | — | `[SPEC]` |

> **N2 싱글톤의 함의**: native `/goal`이 세션 싱글톤이라는 건 thin 하네스가 **한 번에 goal-doc 1개**를 다룬다는 설계로 흡수돼요(§4에서 non-gap 처리). 슬라이스 fan-out은 N1 Workflow가 한 goal 안에서 처리하니까 multi-goal durability(C1의 ultragoal 부분)는 ⑤ thin 범위 밖이에요.

---

## 3. Capability → Native 매핑 매트릭스

각 OMC ⑤ capability를 native가 얼마나 대체하는지 판정해요.
**판정**: ✅ Full(native가 완전 대체) · ◐ Partial(native가 대부분, 잔여 일부) · ✗ Gap(native 못 채움 → 하네스 소유).

| OMC capability | 1차 native | 판정 | 근거 / 잔여 gap |
|----------------|-----------|------|----------------|
| **C1** 자율 goal 루프 | N2 `/goal` | ◐ Partial | 단일-goal 세션 자율 진행은 N2가 대체. **잔여①**: 구조화 goal-doc→슬라이스 바인딩 파싱 = native freeform 완료조건으로 안 됨 → **Gap-ROUTE**. **잔여②**: durable multi-goal/ledger(ultragoal) = §2 N2 싱글톤 한계, 단 ⑤ thin 범위 밖(non-gap, §4.3) |
| **C2** 지속 반복 루프 | N1 Workflow 루프 + N2 `/goal` | ✅ Full | `while(budget.remaining())` / loop-until-dry / loop-until-count 패턴이 ralph·ultrawork·ultraqa의 반복+검증 루프를 직접 표현. "멈추지 않음"은 /goal Stop 훅이 대체 |
| **C3** 에이전트 + 모델 라우팅 | N3 Agent/`agentType` + N8 model | ✅ Full | `agentType`이 OMC와 동일 레지스트리에서 해석 → `executor`·`code-reviewer` 등 named agent 직접 호출 가능. 모델 티어는 N8 param |
| **C4** 병렬 fan-out / 파이프라인 | N1 `parallel()`/`pipeline()` | ✅ Full | 오히려 native가 상위 — 구조적 동시성 + schema 검증 출력 + pipeline 배리어 제어. cap `min(16, cores−2)`는 §2 한계 |
| **C5** 팀 오케스트레이션 | N7 Team 도구 | ✅ Full | OMC team pipeline의 substrate가 **곧 native Team 도구** — OMC는 그 위 스테이지 네이밍(plan→prd→exec→verify→fix)만 얹음. 스테이지는 N1 pipeline으로 재현 |
| **C6** 상태 관리 / 메모리 | N4 훅-기록 파일 + 파일 메모리 디렉토리 + N1 반환값 | ◐ Partial | 세션 상태·파일 메모리는 native 커버. **잔여**: `notepad`/`wiki`/`shared_memory` 같은 구조화 KV에 1:1 native 도구는 없음 — 단 plain 파일 I/O로 대체 가능 → **non-gap**(§4.3) |
| **C7** 훅 트리거 | N4 hooks | ✅ Full | 이벤트·주입 **메커니즘 자체가 native**(MAGIC KEYWORD·boulder·remember는 native 훅에 얹은 authored handler). 주입 *내용*의 정교함은 OMC 핸들러 로직이지만 ⑤ 대체 관점에선 메커니즘이 native라 ✅ |
| **C8** 검증 게이트 | N1 verify 스테이지 + N3 reviewer 에이전트 | ◐ Partial (orchestration만) | reviewer **소환**은 native가 함(pipeline verify 스테이지). **잔여**: "self-approval 금지 / authoring≠review / 격리됐는지"의 **강제(enforcement)**는 native가 판정 안 함 → **Gap-INV** |

**매트릭스 요약**: ✅ Full ×5 (C2·C3·C4·C5·C7), ◐ Partial ×3 (C1·C6·C8). Partial의 잔여 중 native 못 채우는 건 **Gap-ROUTE(C1)**와 **Gap-INV(C8)** 둘뿐. C1·C6의 나머지 잔여는 §4.3에서 non-gap으로 정리.

---

## 4. Thin gap 목록 (native가 못 채우는 부분)

native가 흡수 못 해 **경량 하네스가 thin하게 소유**해야 하는 부분이에요. 정확히 2종.

### 4.1 Gap-ROUTE — 슬라이스→스킬 바인딩 라우팅

native `/goal`은 freeform 완료조건만 평가하고(§2 N2), 구조화 goal-doc을 **"이 워크타입은 이 슬라이스 시퀀스, 각 슬라이스는 이 스킬"** 로 바인딩하는 선언적 라우팅이 없어요. 이 라우팅 + goal-doc 파싱이 하네스 몫이에요.

4종 워크타입 라우터 (#122 D11):

| 워크타입 | 슬라이스 시퀀스 | 바인딩(예시) |
|----------|----------------|-------------|
| 기능개발 full | spec → impl → critique (각 별도 스킬) | spec=spec-first, impl=executor/native agents 위임(#133 판정), critique=code-reviewer/verifier |
| 버그수정 경량 | goal-doc 생략, debug 직행 | debug 스킬(#133) |
| 의사결정 | 실행 없음 | expert-panel / adversarial-review 산출만 |
| 문서작성 | 출력 전용 | doc-concretize / doc-polish / spec-first |

> native 위임 우선: impl 등은 #133 스킬 인벤토리가 "native agents·기존 leaf로 충분한지" 먼저 판정 → 충분하면 신설 안 함. 하네스는 *바인딩 결정 로직*만 소유(`test-slice-router.py`로 hermetic 검증).

### 4.2 Gap-INV — D5 헌법 invariant enforcement

native hooks로 핸들러를 *작성*할 순 있어도(N4), native가 다음 의미 불변을 *내장 강제*하지 않아요(§2 N4 한계). 하네스가 핸들러를 소유해 enforce해요. 이게 adversarial에서 살아남은 narrow strength(="엔진"이 아니라 "섀시/헌법").

| # | Invariant | native가 못 하는 이유 | 하네스 enforce 수단 |
|---|-----------|---------------------|--------------------|
| INV-1 | **new-file-only** (critique/저작 산출은 새 파일, 덮어쓰기 금지) | PreToolUse는 Write 차단은 하나 "이게 critique 산출인지" 의미 판정 안 함 | PreToolUse Write 가드(vault-bridge pre-write-guard 패턴 재사용) |
| INV-2 | **격리 critique** (authoring 컨텍스트 ≠ review 컨텍스트) | native는 별도 에이전트 소환은 하나 "같은 컨텍스트가 자기 검토 중"인지 판정 안 함 | 슬라이스 게이트가 critique를 별도 서브에이전트(N3)로 강제 분리 |
| INV-3 | **self-approval 금지** | PermissionRequest 훅이 승인을 가로챌 순 있으나 "누가 author인지"의 의미 판정은 안 함 | reviewer ≠ author 검증 로직(하네스 소유) |
| INV-4 | **goal-doc 스키마 검증** | native /goal은 freeform — 스키마 없음 | goal-doc 파서가 #100 스키마로 검증 후 라우팅 |
| INV-5 | **단방향 의존** (harness→leaf, leaf→harness 금지) | native에 의존 방향 개념 없음 | leaf 디렉토리 git diff 0줄 가드 + trigger-regression 제거 0건 검증 |

> **enforce 설계 제약**: INV-2/INV-3을 별도 서브에이전트로 강제 분리하면, 그 서브에이전트의 *중간* critique 과정은 하네스가 관찰 못 해요(§2 N3 — 최종 메시지만 호출자 반환). 따라서 격리 critique enforce는 schema 구조화 출력(N1)으로 *결과*만 검증하는 형태가 돼요 — 과정 감시가 아니라 산출 계약. PermissionRequest 훅(N4)이 self-approval 차단의 native 후보지만, "현재 author가 누구인지"의 의미 판정은 여전히 핸들러 몫이라 INV-3은 gap으로 남아요.

> **D2 격리와 INV-5의 관계**: #122는 D2(harness=CC전용 / leaf=vendor-neutral / 단방향)를 별도 불릿으로 명시해요. 그중 **단방향 enforce 측면은 INV-5가 흡수**하고, **vendor-neutrality 계약 측면(leaf가 특정 벤더에 묶이지 않음)은 #99 경계 A로 단일화**돼 이 문서 범위 밖이에요(§4.4 정합표 참조).

### 4.3 Non-gap (native 한계지만 thin 레이어가 안 채움)

1:1 정합을 흐리지 않으려고 명시 배제해요 — 이건 native 한계지만 하네스가 채울 gap이 *아니에요*.

- **durable multi-goal / ledger** (C1의 ultragoal 부분): N2 싱글톤 한계지만, 하네스는 **goal-doc 1개/세션** 설계라 불필요. 슬라이스 fan-out은 N1 Workflow가 한 goal 안에서 처리. → 범위 밖.
- **구조화 KV (notepad/wiki/shared_memory)** (C6): plain 파일 I/O + goal-doc 자체 + N1 반환값으로 대체 가능. 자체 KV 엔진 빌드는 native-supersession 매몰비용 리스크 → 안 지음.

### 4.4 #122 thin 레이어와 1:1 정합 검증

#132 Acceptance "gap 목록이 #122 하네스 스코프와 1:1 정합". #122 스코프는 thin 추가 레이어를 **세 불릿**으로 명시해요 — (a) 슬라이스→스킬 바인딩 라우팅, (b) 헌법 invariant enforcement(D5), (c) D2 격리(harness=CC전용 / leaf=vendor-neutral / 단방향). 이 셋이 이 문서 gap 2종에 다음처럼 정확히 매핑돼요(잉여·누락 없음).

| #122 thin 레이어 구성 | 이 문서 gap | 정합 |
|---------------------|------------|------|
| (a) "4종 슬라이스 라우터" + "native(/goal·Workflow) 위임 경계 명시" | **Gap-ROUTE** (§4.1) | ✅ 1:1 |
| (b) "D5 헌법 invariant enforcement (native가 못 채우는 gap)" | **Gap-INV** (§4.2, INV-1~5) | ✅ 1:1 |
| (c) "D2 격리 — 단방향 enforce" | **Gap-INV / INV-5**가 흡수 (§4.2 주석) | ✅ INV-5에 포함 |
| (c) "D2 격리 — vendor-neutrality 계약" | #99 경계 A로 단일화 → 이 문서 범위 밖 | ✅ 위임(non-gap) |
| (해당 없음) Non-gap §4.3 (durable multi-goal, 구조화 KV) | #122 scope에 없음 → 배제로 정합 보존 | ✅ |

**결론**: #122 thin 3-불릿 → gap 2종(ROUTE + INV)으로 정확히 환원돼요. D2의 단방향은 INV-5에, vendor-neutrality는 #99에 귀속되니 **초과 gap 없음, 누락 gap 없음**. #122는 이 2종만 구현하고 나머지(C2·C3·C4·C5·C7 + C1/C6/C8의 native 커버분)는 native에 위임하면 돼요.

---

## 5. Strangler 점진 대체 경로

OMC는 지금 ⑤를 담당하며 정상 동작 → 전면 교체 아닌 **route-by-route 점진 흡수**. 각 단계는 독립 검증 + 롤백 가능, 미이관 경로는 OMC가 계속 담당(= strangler).

| Phase | 내용 | 이슈 | 검증 | 롤백 |
|-------|------|------|------|------|
| **P0** | Baseline — OMC가 ⑤ 전담 (현재) | — | 현행 동작 | (N/A) |
| **P1** | substrate 매핑 + native 한계 실측 (이 문서) | #132 | 본 문서 Acceptance | 문서만 — 코드 영향 0 |
| **P2** | thin 하네스 골격 — plugin 스캐폴드 + native substrate 위 `/goal` 엔진 + 4종 라우터(**Gap-ROUTE**) | #122 S1–S2 | `test-slice-router.py` 4종 케이스 | 플러그인 미설치 시 OMC 무영향 (opt-in) |
| **P3** | invariant + 규칙 — D5 enforcement(**Gap-INV** INV-1~5) + 3-tier 병합 | #122 S4–S5, #125 | 헌법 disable 차단 테스트 + 병합 우선순위 테스트 | 훅 모드 플래그로 비활성(`WRITE_CONTRACT` 패턴) |
| **P4** | 스킬 바인딩 + 게이트 체인 — spec/impl/critique/debug/quality 바인딩, 4지점 게이트 | #133, #134 | feature-dev goal-doc 1개 e2e dogfood | 라우트를 OMC autopilot/ralph로 재지정 |
| **P5** | retro + telemetry — 루프 닫기, 이관 parity 측정 | #123, D8 | telemetry `meta` 필드 | 스킬 제거 |
| **P6** | OMC 표면 축소 (**조건부·가역**) — telemetry가 native+하네스 parity 입증 **AND** native invariant 지원 성숙 시에만, ⑤ 의존을 route별 감축 | (후속) | route별 parity 게이트 | route별 OMC 재지정(완전 가역) |

**strangler 불변식**:
- 매 phase에서 **미이관 ⑤ 경로는 OMC가 계속 담당** — 큰 빅뱅 컷오버 없음.
- P2~P5는 **opt-in 추가** — 설치/활성 전엔 OMC 동작 그대로.
- P6만 OMC 표면을 줄이며, **route별로 가역**(parity 미달 시 OMC로 되돌림).
- native가 강해질수록(supersession) P2~P3의 native 위임분이 *수혜* — 자체 빌드분(Gap-ROUTE/INV)은 native가 그 invariant를 충분히 강제하게 되면 *축소 가능*(#122 비고). 매몰비용 아님.

**hard 의존 게이트 (#100 LINCHPIN)**: P2(Gap-ROUTE의 goal-doc 파싱)와 P3(INV-4 goal-doc 스키마 검증)는 둘 다 **#100(G2, 현재 gated)의 goal-doc 스키마 확정이 hard 전제**예요. 스키마 없이는 파싱·검증 구현 불가 → #100 머지 전 P2/P3 착수 불가(G6 슬라이스 순서의 "S3 = G2 hard 전제"와 동일 게이트). P1(이 문서)·#132는 #100과 독립이라 선행 완료 가능.

---

## 6. Acceptance 추적 + 게이트 역할

### 6.1 #132 Acceptance 충족

| #132 Acceptance | 충족 위치 |
|-----------------|----------|
| `docs/design/omc-to-native-substrate.md`: capability 인벤토리 × native 매핑 매트릭스 + gap 목록 + strangler 단계 | §1(인벤토리) × §3(매트릭스) + §4(gap) + §5(strangler) |
| 각 native 기능의 실측 한계 기록(예: `/goal` 세션 싱글톤) | §2 (근거 티어 명시, /goal 싱글톤 = `[CONFIRMED 2026-06-03]`) |
| gap 목록이 #122 하네스 스코프와 1:1 정합 | §4.4 (Gap-ROUTE ↔ 4종 라우터, Gap-INV ↔ D5 enforcement) |

### 6.2 게이트 역할 (native-supersession 방어)

이 매핑이 #122 착수 전 게이트예요: **native가 이미 주는 capability(C2·C3·C4·C5·C7)는 자체 빌드 금지**, thin 레이어는 Gap-ROUTE·Gap-INV 2종만 구현. native가 `/goal`·Workflow를 강화할수록 위임분은 수혜고, 자체 enforcement는 native invariant 지원이 성숙하면 축소 가능(P6). adversarial이 기각한 "from-scratch 자체 엔진"으로의 회귀를 이 문서가 구조적으로 차단해요.

### 6.3 하위 이슈 연계

- **#122**(thin 하네스): 이 문서가 thin 범위(Gap-ROUTE/INV) 확정 → P2~P3.
- **#133**(스킬 인벤토리): §4.1 바인딩의 impl/debug/quality "native 우선 판정"의 입력.
- **#134**(게이트 체인): §4.2 INV-2/INV-3(격리 critique·self-approval)가 슬라이스 게이트로 쓰임.
- **#125**(3-tier 규칙): 병합 지점 = goal-doc 파싱(§4.1 ROUTE) 단계.
- **#100**(goal-doc spec, LINCHPIN): §4.2 INV-4 스키마 검증의 스키마 출처. 이 문서는 스키마를 정의하지 않고 *검증 지점*만 명시.

---

**참조**: `docs/adversarial-review/2026-06-03-harness-ownership.md`(방향), #99(경계 A), #122(thin 하네스), #100(goal-doc), `docs/discussions/20260602_claude-kit-layer-redesign/`(레이어 모델 C-1), `docs/plans/goal-docs/G6-workflow-harness-rules.md`(슬라이스 순서).
