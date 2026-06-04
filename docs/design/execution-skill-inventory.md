# ⑤ 실행 스킬 인벤토리 — spec/impl/critique 분리 + debug/quality/issue (native 위임 우선)

**Status**: design · **Created**: 2026-06-04 · **Issue**: #133 · **Epic**: #108(⑤ 실행 트랙)
**선행**: #100(`docs/design/goal-doc-spec.md` §3.6 슬라이스 바인딩) · #132(`docs/design/omc-to-native-substrate.md` §3 C3·§4.1 native 우선 판정의 입력) · #99(`docs/design/claude-kit-boundary.md` 단방향·레이어 귀속)
**하류 소비처**: #122 Gap-ROUTE(impl/critique/debug 바인딩 결정) · #134(게이트 체인 — critique 격리) · #101(`docs/design/output-adapter-contract.md` — issue-authoring 경계)
**Source**: #133 이슈 + 2026-06-03 결정(spec/impl/critique 각각 별도 스킬) + `docs/adversarial-review/2026-06-03-harness-ownership.md`(strong-form 기각·native 위임 우선)

> **위치(native 위임 우선 판정)**: 이 문서는 ⑤ 실행 슬라이스가 호출할 스킬 각각이 **(a) 기존 leaf 재사용 / (b) native agent 위임 / (c) 신설** 중 무엇인지 *판정*해요. 판정 기준은 `omc-to-native-substrate.md` §6.2 게이트 — **native가 이미 주는 capability는 자체 빌드 금지**, 신설은 native·기존이 못 채우는 부분에 한정(C-5 만장일치 "신설 최소화"). 헌법/단방향 규칙은 `claude-kit-boundary.md` 단일 출처 **참조만**.

---

## 0. 범위와 판정 기준

### 0.1 범위 — ⑤ 실행 슬라이스 스킬

`omc-to-native-substrate.md` §4.1 4종 라우터 중 **기능개발 full**(spec→impl→critique, 각 별도 스킬 — 2026-06-03 결정)과 **버그수정 경량**(debug 직행), 그리고 **품질·이슈** 슬라이스가 호출하는 스킬을 인벤토리해요.

| 단계/용도 | 후보 스킬 | #133 이슈 분류 |
|-----------|----------|---------------|
| spec(명세화) | spec-first | ② 기존 재사용 |
| impl(구현) | (신설 후보) 또는 native agents | native 우선 판정 |
| critique(비평) | adversarial-review | ① 기존 재사용 |
| 디버깅 | debug(5 Whys RCA + 유사 패턴 스캔 + 구조 개선) | 신설 후보 |
| 품질 | quality(린터보다 큰 단위) | 신설 후보(게이트 체인 공유) |
| 이슈 닫기/생성 | issue | #101 issue-authoring과 조율 |
| 회고 | retro | **#123 소관 — 본 인벤토리 범위 외** |

### 0.2 판정 enum — 3종

| 판정 | 의미 | 신설 여부 |
|------|------|----------|
| **REUSE** | 기존 claude-kit leaf 스킬(①/②)로 충분 | 신설 0 |
| **NATIVE** | Claude Code 네이티브 agent/Workflow 위임으로 충분(`substrate` §3 C3 ✅ Full = `agentType` 동일 레지스트리) | 신설 0 |
| **NEW** | native·기존이 못 채우는 gap 입증 시에만 신설. ①/② leaf로 귀속(vendor-neutral), 하네스(⑤)가 단방향 호출 | 신설 — gap 입증 게이트 |

> **native 우선 순서**: 각 단계는 **REUSE → NATIVE → NEW** 순으로 판정해요 — 기존 leaf가 있으면 REUSE, 없으면 native agent로 되는지(NATIVE), 그것도 안 되는 gap만 NEW. NEW는 "후보"로 두고 gap 입증(telemetry/dogfood) 전까지 기본값은 NATIVE/REUSE예요.

> **범위 외 항목**: `retro`(#123 소관)는 이 인벤토리의 *판정 대상이 아니에요* — REUSE/NATIVE/NEW enum은 in-scope 6항목(spec/impl/critique/debug/quality/issue)에만 적용하고, §0.1 표의 `retro` 행은 "범위 외" 마커일 뿐 판정값이 아니에요.

---

## 1. 인벤토리 표 (핵심 판정)

| 단계 | 타겟 | 판정 | native 우선 근거 | 레이어 귀속(NEW 시) |
|------|------|------|-----------------|---------------------|
| **spec** | spec-first | **REUSE** | ② 기존 출력 leaf. Socratic 게이트(Ambiguity ≤ 0.2)는 native에 등가 없음 → 재사용이 정답, native 위임 부적합 | (기존 ②) |
| **impl** | native `executor` agent | **NATIVE** | `substrate` §3 **C3 = ✅ Full**: `agentType`이 OMC와 동일 레지스트리에서 해석 → `executor` 직접 호출 + 모델 티어 N8 + worktree 격리 N1/N3. claude-kit 신설 0 | — (native, leaf 아님) |
| **critique** | adversarial-review(claim/설계) + native `code-reviewer`/`verifier`(code diff) | **REUSE(①) + NATIVE** | adversarial-review = ① 기존 leaf(주장 공격·survival verdict). code diff 비평은 native code-reviewer/verifier(C3 ✅). 격리(INV-2/INV-3)는 Gap-INV(#122/#134) 강제 | (기존 ①) |
| **debug** | native `debugger` agent (1차) / 신설 debug-method(보류) | **NATIVE(1차) + NEW(보류·gap 미입증)** | `debugger`는 `substrate` §1 **C3**(19종 named agent 중 `debugger` 명시)·§2 **N3**(agentType 레지스트리)에 실재 — 추측 아님. stack-trace/RCA 오케스트레이션 커버. "5 Whys RCA 구조화"가 native 대비 gap인지 *미입증* → 기본 NATIVE, NEW는 보류 | ①(인지 — 추론 구조화) |
| **quality** | native `code-reviewer`/`verifier` + doc-polish(md) + adversarial-review/expert-panel(claim) | **REUSE + NATIVE (NEW 미정당)** | 코드=code-reviewer(native), md=doc-polish(②), 평가=adversarial-review/expert-panel(①)이 공간을 덮음. 전용 quality 신설은 3자 중복 리스크 → **현재 미정당** | (만약 신설 시 ① — 단 중복 리스크 플래그) |
| **issue** | gh CLI(기계적) + issue-authoring(본문 저작) | **REUSE(외부) + NEW(②)** | gh = 외부 전송 도구 재사용. 본문 저작(템플릿·라벨·중복 검출)은 gap → NEW. #101 §4.1이 선언한 net-new와 동일 항목 | **②**(출력 leaf — `boundary` line 25/38) |
| *(retro)* | — | **범위 외(#123)** | 본 인벤토리는 spec/impl/critique/debug/quality/issue만 | — |

---

## 2. `goal-doc-spec` §3.6 `candidate-or` 바인딩 해소

`goal-doc-spec` §3.6은 impl/critique 바인딩을 §3.2 `candidate-or` 문법(`skill-id("|"skill-id)+"(#"issue-no")"`)으로 두고 **#133에 위임**했어요:

> (§3.6 인용, 정정 후) impl/critique의 구체 귀속(재사용/native위임/신설)은 **#133 인벤토리**가 확정해요. 표기는 `candidate-or` 형태(`executor|native(#133)`, §3.2 문법 — 완전-TBD `placeholder` `<#133>`와 구분)로 두고 #133과 정합. **native 위임 우선**.

> **용어 주의 (§3.2 정합)**: `executor|native(#133)`은 §3.2 grammar상 **`candidate-or`**(후보 정해짐·확정만 #133 대기)지 **`placeholder`**(`<#133>` — 후보조차 미정)가 아니에요. 이 절은 §3.2 정의를 따라 `candidate-or`로 통일해요. (§3.6/§5 본문이 이 표기를 한때 "placeholder"로 부른 건 §3.2 grammar 대비 부정확 — 이번 #101/#133 작업에서 `goal-doc-spec.md` §3.6:164·§5:213 산문을 `candidate-or`로 정정했어요. 토큰 자체는 불변이라 CON-4 stable contract·INV-4 비검증에 영향 0.)

이 인벤토리가 그 `candidate-or`의 referent를 **확정(해소)**해요. §3.2 문법은 그대로 유효(`candidate-or`/`placeholder` 둘 다 INV-4 비검증 대상이라 §3.6 *토큰* 표기는 불변 — referent 공급으로 해소):

| `goal-doc-spec` §3.6 `candidate-or` | 해소된 바인딩 | §3 표기 정합 |
|----------------------------------|--------------|-------------|
| spec = `spec-first` | spec-first (REUSE, ② 기존) — 변동 없음 | §3.3 단일 형태 ✅ |
| impl = `executor\|native(#133)` | **native `executor` agent** (NATIVE 위임, claude-kit 신설 0). `candidate-or`의 `native` 가지 채택 | §3.2 `candidate-or` → resolution ✅ |
| critique = `adversarial-review\|code-reviewer(#133)` | **payload 타입별 분기**: claim/설계 → adversarial-review(① REUSE); code diff → native `code-reviewer`/`verifier`(NATIVE) | §3.2 `candidate-or` → resolution ✅ |

> **§3 표기 정합 확인**: 해소 결과는 §3.2 토큰 문법을 위반하지 않아요 — `candidate-or`의 후보 중 하나(또는 payload 분기)를 *선택*한 거고, INV-4는 "바인딩 식 존재"만 검증하지 타겟 resolution을 검증 안 해요(`goal-doc-spec` §4.3 5번). 즉 §3.6 토큰 표기(`executor|native(#133)`)는 그대로 남고, 이 표가 라우터(#122)가 런타임에 쓸 **resolution 사전**이에요.

> **`goal-doc-spec.md` 편집 범위(정직성)**: 이번 작업에서 `goal-doc-spec.md`에 가한 건 §3.6:164·§5:213의 **산문 용어 정정**(`placeholder` → `candidate-or`, §3.2 grammar 정렬)뿐이고, 스키마 필드·바인딩 *토큰*·섹션 구조는 일절 안 건드렸어요(CON-4 stable contract 보존 — 정정은 §3.2가 이미 정의한 용어로의 정렬이지 의미 변경 아님). #133 귀속 자체는 이 §2 표가 단일 출처로 공급하고, §3.6은 그 referent를 forward-ref해요("State each rule once").

---

## 3. 신설(NEW) 항목 레이어 귀속

`claude-kit-boundary.md` §3 "규율 범위": 단방향 규칙은 harness↔leaf 경계에만 적용, leaf 내부 cognitive 레이어 간 호출(①→②)은 허용. 신설 스킬은 ①/② leaf로 귀속되고 하네스(⑤)가 단방향 호출해요.

| NEW 후보 | 레이어 | 귀속 근거 | 상태 |
|----------|--------|----------|------|
| **issue-authoring** | **② 출력 leaf** | `boundary` 레이어 표(line 25)가 `issue`를 ②로, line 38이 "issue-skill의 ②출력 leaf 귀속 + diverse-sampling Mode B 합성"을 단일 출처로 확정 | **firm** — #101 §4.1 net-new와 동일 항목(§4 경계) |
| **debug-method** (5 Whys RCA 구조화) | ① 인지 leaf | 5 Whys·유사 패턴 스캔은 *추론 구조화*(adversarial-review와 동류 ① 동작)지 오케스트레이션이 아님 | **보류** — native `debugger` 대비 gap 미입증. 기본값 NATIVE |
| **quality** (큰 단위 품질) | ①(평가) — *만약* | 큰 단위 평가는 ① 평가 동작이나 adversarial-review/expert-panel(①)·code-reviewer(native)·doc-polish(②)와 중복 | **미정당** — 중복 리스크. #134 게이트 체인이 별개 필요 입증 시에만 재검토 |

> **신설 최소화 결과**: firm 신설 = **issue-authoring 1건**(② leaf). debug-method·quality는 보류/미정당이라 현재 신설 0 — `substrate` §6.2 게이트("native가 주는 건 자체 빌드 금지") + C-5 만장일치 정합. native가 강해질수록(supersession) debug/quality의 native 커버분이 수혜, 자체 빌드 부담은 축소(`substrate` §5 P6).

---

## 4. issue 스킬 ↔ #101 issue-authoring 경계 (중복 0)

issue는 **#101(출력-포맷 축)과 #133(실행-스킬 축)이 만나는 유일 교차점**이에요. `output-adapter-contract.md` §5.2와 **동일한 소유권 분할**을 여기서 거울처럼 기록해요(양쪽이 같은 분할을 참조 → 중복 0). **정규 출처는 #101 §5.2**, 아래 표는 #133 독립 가독성을 위한 *의도적 거울*이에요(스펙 변경 시 양쪽 수동 동기화 — `output-adapter-contract.md` §5.2 의사결정 기록 참조):

| 책임 | 소유 doc | 내용 |
|------|---------|------|
| gap *선언* + 어댑터 *매핑* (`issue=gh CLI` + 본문 저작 빈틈) | **#101** (`output-adapter-contract.md` §2 #8 + §4.1) | "issue-authoring이 net-new gap" + 균일 호출 규약 |
| 실행스킬 *판정* + *레이어 귀속* (gh=외부 REUSE, issue-authoring=NEW ②) | **#133** (이 문서 §1·§3) | "gh CLI=외부 재사용, issue-authoring=신설 ② leaf" |

- #101은 issue-authoring을 **출력-포맷 축의 net-new gap**으로 *선언*해요(≤2 중 1건).
- #133은 issue-authoring을 **② 출력 leaf로 *귀속 판정*** + gh CLI를 외부 도구 REUSE로 분류해요.
- 두 doc은 서로 **참조만**, 상대 영역 재정의 안 함. gap은 #101이 한 번 선언, 레이어는 #133이 한 번 판정(`boundary` line 25/38 단일 출처). → **중복 0**.

> **debug/quality는 교차점 아님**: 이 둘은 ⑤ 실행-스킬 축 전용(출력 포맷 아님)이라 #101 net-new에 안 셈. issue만 두 축이 만나요(이슈 본문 = ② 출력물이면서 동시에 "이슈 닫기/생성" ⑤ 실행 용도).

---

## 5. #133 Acceptance 추적

| #133 Acceptance | 충족 위치 |
|-----------------|----------|
| `execution-skill-inventory.md`: 표 확정 + 각 항목 재사용/native위임/신설 판정 + 신설 항목 레이어 귀속 | §1(인벤토리 표 + REUSE/NATIVE/NEW 판정) + §3(NEW 레이어 귀속) |
| spec/impl/critique 별도 스킬 바인딩이 #100 goal-doc 슬라이스 표기와 정합 | §2(§3.6 `candidate-or` 바인딩 해소표 + §3.2 정합) |
| issue 스킬 ↔ #101 issue-authoring 경계 명시(중복 회피) | §4(소유권 분할표 — #101 §5.2와 거울 정합) |

---

**참조**: `docs/design/goal-doc-spec.md`(§3.2 candidate-or 문법·§3.6 work_type 기본 바인딩·§4.3 INV-4) · `docs/design/omc-to-native-substrate.md`(§2 N3 agentType 레지스트리·§3 C3 native 매핑·§4.1 4종 라우터·§4.4 bug-light·§6.2 게이트·§5 P6) · `docs/design/claude-kit-boundary.md`(§3 규율 범위·레이어 표 line 25/38 issue ② 귀속·CON-5 단방향) · `docs/design/output-adapter-contract.md`(#101 issue-authoring 선언·§5.2 경계) · `docs/adversarial-review/2026-06-03-harness-ownership.md`(strong-form 기각) · #100/#101/#122/#123/#132/#134.
