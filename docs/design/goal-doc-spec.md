# goal-doc 스펙 — 스키마 + 슬라이스→스킬 바인딩 표기법 + parse/exec 인터페이스

**Status**: design (LINCHPIN) · **Created**: 2026-06-04 · **Issue**: #100 · **Epic**: #108
**선행**: #99(경계 A — `docs/design/claude-kit-boundary.md`), `docs/design/omc-to-native-substrate.md` §4.1/§4.2
**하류 소비처**: #122(INV-4 스키마 검증 + Gap-ROUTE 라우터) · #105(thought-chain dissolve 바인딩) · #125(tier 선언 필드) · #133(슬라이스 스킬 귀속) · #101(출력 어댑터 계약)
**Source**: `docs/discussions/20260602_claude-kit-layer-redesign/UNRESOLVED.md` U-3 · `docs/plans/goal-docs/G2-goal-doc-output-contract.md`(dogfooding 레퍼런스) · consensus 게이트(architect+critic, 2026-06-04)

> **위치(헌법 제약 하의 스펙)**: 이 문서는 `docs/design/claude-kit-boundary.md` **CON-4**("goal-doc = stable harness-neutral contract")의 제약 *안에서* goal-doc 스키마 *세부*를 정의해요. 헌법/정책 규칙 목록·경계는 #99가 단일 출처고, 이 문서는 그걸 재정의하지 않아요(참조만). goal-doc은 harness(현재 OMC / 목표 native 기반 경량 하네스)가 바뀌어도 안정적인 중립 계약이에요.

---

## 0. goal-doc이란 — 역할과 런타임 목적

goal-doc은 **하나의 목표를 "어떤 워크타입인지 + 어떤 슬라이스 시퀀스로 + 각 슬라이스를 어떤 스킬이 실행하는지"로 선언하는 구조화 문서**예요. 두 가지 런타임 목적을 가져요:

1. **파싱·검증(INV-4, #122)**: 하네스의 goal-doc 파서가 이 스펙의 스키마로 goal-doc을 검증한 뒤,
2. **라우팅(Gap-ROUTE, §4.1)**: `work_type`을 1차 키로 슬라이스 시퀀스를 결정하고 각 슬라이스를 바인딩된 스킬에 위임해요.

claude-kit은 goal-doc을 **생성**만 하는 ②출력 leaf(spec-first 산출)이고, **실행**은 harness(`/goal` in-session 액티브 에이전트 + Workflow)가 담당해요(경계 A, §4).

> **스키마 진화 주의**: goal-doc은 CON-4의 "stable contract"라 필드 추가/의미 변경은 `schema_version`(§1.3)으로 관리해요. 이 문서는 `schema_version: 1`을 정의해요.

---

## 1. Frontmatter 스키마

### 1.1 Core 필드 (dogfood 베이스라인 — 8종, 전부 required)

G2~G12 goal-doc이 실사용한 8필드예요. 전부 required.

| 필드 | 타입 | enum/형식 | 의미 | 작성 규칙 |
|------|------|----------|------|----------|
| `goal_id` | string | `G\d+` 패턴 | goal 식별자(예: `G2`). `depends_on`이 참조하는 네임스페이스 | epic 내 유일 |
| `title` | string | 자유 | 한 줄 제목 | 워크타입+산출이 드러나게 |
| `issues` | list\<int\> | **GitHub 이슈 번호** | 이 goal이 닫는 이슈 묶음(예: `[100, 101, 111]`) | §1.4 네임스페이스 주의 |
| `wave` | int \| string | **사람용 스케줄 라벨**(파서 미검증 — §1.5) | 실행 wave(정수) 또는 스케줄 태그(`독립`/`게이트`) | 라우팅 키 아님 |
| `depends_on` | list\<goal_id\> | **goal_id 네임스페이스**(이슈 번호 아님) | 선행 goal(예: `[G1]`) | §1.4 네임스페이스 주의 |
| `recommended_model` | enum | `haiku` \| `sonnet` \| `opus` | 권장 실행 모델 | 복잡도 기반 |
| `status` | enum | `gated` \| `ready` | `gated`=consensus 게이트 대기, `ready`=착수 가능 | linchpin/고위험은 `gated` 시작 |
| `created` | date | `YYYY-MM-DD` | 작성일 | — |

### 1.2 `work_type` — 라우팅 키 (required, consensus 게이트 추가)

> **추가 근거(dogfooding 발견)**: 베이스라인 8필드엔 워크타입 선언이 없어요. 그런데 Gap-ROUTE(`omc-to-native-substrate.md` §4.1)는 **워크타입을 1차 라우팅 키**로 써요("이 워크타입은 이 슬라이스 시퀀스"). 8필드만으로는 파서가 goal-doc의 워크타입을 결정적으로 판별 못 해요(예: G2의 `issues`/`wave`로는 feature-full/decision/doc 구분 불가). #100 이슈가 이미 요구한 "슬라이스 바인딩 4종 분류 명시"의 올바른 귀착점이 이 frontmatter 필드예요 — 바인딩 표기 수준이 아니라 파서가 읽는 required 키 수준. consensus 게이트(critic CRITICAL)에서 확정.

| 필드 | 타입 | enum | 의미 |
|------|------|------|------|
| `work_type` | enum | `feature-full` \| `decision-only` \| `doc-only` | 라우팅 1차 키. §3.6 기본 바인딩이 이 값으로 결정됨 |

- **3종인 이유 (bug-light 부재)**: substrate §4.1의 4종 라우터 중 **버그수정 경량(bug-light)은 "goal-doc 생략, debug 직행"**이에요(§4.4). goal-doc이 *존재하는* 한 워크타입은 절대 bug-light가 아니므로, `work_type` enum은 3종이고 bug-light는 **goal-doc 부재**로 라우터가 판별해요(§4.4).

### 1.3 확장 필드 (optional)

| 필드 | 타입 | 형식 | 미선언 시 | 소비처 |
|------|------|------|----------|--------|
| `applies_tiers` | list\<enum\> | **cumulative**: `[default]` \| `[default, user]` \| `[default, user, project]` | `[default]` | #125 3-tier 병합(병합 지점=goal-doc 파싱 단계) |
| `schema_version` | int | 현재 `1` | `1` | CON-4 진화 호환(vault v4 `schema_version` gate 선례 — `docs/design/vault-second-brain-v4.md`) |

> **`applies_tiers` 형식(consensus MAJOR 반영)**: "optional"만으로는 부족해요 — #125 병합(project > user-global > default)이 입력 형식을 알아야 하거든요. **cumulative list**로 고정: 상위 tier 선언은 하위를 포함해요(`[default, user]` = default+user 적용, project 미적용). 미선언 = `[default]`(보수적 안전 기본값 — 헌법 항목은 어느 tier도 override 불가이므로 default-only가 안전). 이건 #125 "tier 선언 필드 연결 지점"의 실현이고, override 가능 범위는 #99 **정책(policy)** 항목에 한해요(헌법 항목 override 불가).

### 1.4 ID 네임스페이스 주의 (consensus MAJOR 반영)

`issues:`와 `depends_on:`은 **서로 다른 네임스페이스**예요 — 한 frontmatter에 공존하니 파서가 혼동하면 안 돼요:

- `issues: [100, 101]` → **GitHub 이슈 번호** 공간.
- `depends_on: [G1]` → **`goal_id`** 공간(이슈 #1이 아님).

파서는 `depends_on` 항목을 `goal_id`(`G\d+`)로 해소하고, `issues`를 GitHub 번호로 해소해요. (Gap-ROUTE 파서가 `[G1]`을 이슈 #1로 오인하면 의존 순서가 깨져요.)

### 1.5 `wave` 타입 정직성 (consensus 반영)

`wave`는 **사람용 wave-planning 메타데이터**지 파서 라우팅 입력이 아니에요. 코퍼스에 정수(`1`~`5`)와 범주 라벨(`독립`, `게이트`, `독립·게이트`)이 혼재해요(G8~G12 다수 — 예: G9 `독립·게이트`, G10/G8/G11 `독립`, G12 `게이트`). 라우터는 `wave`가 아니라 `work_type` + `depends_on` + 슬라이스 바인딩을 읽으니, **`wave`를 enum으로 검증하지 않아요**(INV-4 값 검증 대상에서 제외). 정수=실행 순서 ordinal, 라벨=스케줄 범주(독립/게이트)로 자유 기술해요. 기계 의존 순서는 `depends_on`이 담당해요.

> INV-4가 enum으로 검증하는 필드는 `recommended_model`, `status`, `work_type`, `applies_tiers`예요. `wave`는 **존재는 required**(§1.1 core 8필드)지만 **값 공간은 비검증**이에요.

---

## 2. 본문 5섹션 스키마

순서 고정. 전부 required. (G2/G5 dogfooding에서 5섹션 전부 실하중 확인.)

| # | 섹션 | required | 의미 | 작성 규칙 |
|---|------|----------|------|----------|
| 1 | **배경 / 목적** | ✓ | 왜 이 goal인지, 가치·응집 근거 | 묶음 goal이면 이슈 응집 근거 |
| 2 | **완료 조건 (Definition of Done)** | ✓ | 이슈별 Acceptance를 체크박스로 1:1 | 측정 가능하게. INV-4가 "DoD 섹션 존재"를 검증 |
| 3 | **쟁점과 트레이드오프** | ✓ | 선택지·권장·근거 표. **조건분기 슬라이스의 verdict가 기록되는 곳**(§3.4) | backlog/게이트 처리 패턴 포함 |
| 4 | **슬라이스 순서** | ✓ | 각 슬라이스: 번호 + 바인딩 + 대상 파일 + 산출 + 검증. §3 표기법 따름 | 라우터가 시퀀스를 읽는 본문 핵심 |
| 5 | **E2E 자가검증** | ✓ | 실행 가능한 bash 블록 + 통과 기준 | DoD와 1:1 대조 가능하게 |

- **의존성/순서 주의** 섹션은 권장(선행 goal·크로스청크 게이트가 있으면). required 아님.
- §3 슬라이스의 verdict(조건분기 판정)는 **쟁점/트레이드오프 섹션**에 기록해요(G5 dogfood 패턴). 파서는 그 섹션에서 분기 게이트를 읽어요.
- **섹션 식별 규칙**: 파서는 본문 섹션을 *순서 + 키워드*(예: 완료조건/DoD, 슬라이스, 자가검증)로 식별해요 — **제목 정확 문자열 매칭이 아니에요**. (G2 "완료 조건 (Definition of Done)"처럼 표기가 goal-doc마다 달라도 흡수.)

---

## 3. 슬라이스 → 스킬 바인딩 표기법

### 3.1 슬라이스 라인 형식

각 슬라이스는 본문 "슬라이스 순서" 섹션에서 다음 형식이에요:

```
N. **<슬라이스명>** → 바인딩: <binding-expr> | 대상 파일: <path|("분석만")> | 산출: <...> | 검증: <...>
```

`<binding-expr>`가 이 표기법의 핵심이고, 아래 4형태 중 하나예요.

### 3.2 토큰 문법 (consensus 반영 — 산문이 아니라 grammar)

바인딩 타겟은 **파싱 가능한 토큰**이에요:

```
binding-target := skill-id [ "(" qualifier ")" ]
skill-id       := <kebab-case 스킬/에이전트 식별자>   # 예: doc-concretize, executor, adversarial-review
qualifier      := <자유 텍스트 설명>                   # 예: (구조화 저작), (메인 컨텍스트)
placeholder    := "<#" issue-no ">"                       # 미확정 타겟(#133 대기) — 예: <#133>
candidate-or   := skill-id ("|" skill-id)+ "(#" issue-no ")" # 후보 OR + 확정 이슈 — 예: executor|native(#133)
```

> `placeholder`(`<#133>`)는 **후보 스킬조차 미정**(완전 TBD)일 때, `candidate-or`(`executor|native(#133)`)는 **후보는 정해졌고 확정만 #133 대기**일 때 써요. 둘 다 **INV-4 비검증 대상**이에요(타겟 resolution은 #133/라우터 런타임 책임) — 파서는 슬라이스에 바인딩 *식이 존재*하는지만 봐요.

- placeholder는 **#133 인벤토리가 확정할 귀속**을 표기해요. INV-4는 구조(바인딩 존재)만 검증하고 타겟 스킬의 실재(resolution)는 검증 안 해요 — resolution 실패는 라우터 런타임 책임(#122)이지 스키마 검증 책임이 아니에요. (consensus: placeholder ↔ INV-4 충돌 없음 = survived.)

### 3.3 4형태

| 형태 | 표기 | 예 | 의미 |
|------|------|-----|------|
| **단일** | `<target>` | `doc-concretize (구조화 저작)` | 한 슬라이스 = 한 스킬 |
| **시퀀스** | `<t1> → <t2> → <t3>` | `spec-first → executor\|native(#133) → adversarial-review` | 순차 단계 — `→`는 **항상 산출→입력 체이닝**을 함의(§3.5), 단순 순서 아님 |
| **위임(직접)** | `직접(<context>)` | `직접(메인 컨텍스트, 설계 결정)` | in-session 액티브 에이전트가 직접 수행(서브에이전트 미spawn). native 위임 우선의 표기 |
| **조건분기** | `<선행슬라이스 verdict> ? <t-pass> : <t-fail>` | `S1.verdict == PASS ? (제거) : doc-polish(alias)` | 선행 슬라이스 판정으로 택1. verdict는 쟁점/트레이드오프 섹션에 기록(§2) |

### 3.4 조건분기 — #105 CT-게이트 표현 (consensus CRITICAL 반영)

G5(thought-chain dissolve)의 S3은 `S3-PASS 또는 S3-ALIAS (S1 결과에 따라 택1)`예요. 이건 **선행 슬라이스의 verdict가 후행 슬라이스를 고르는** 메커니즘이고, 단일/시퀀스/위임 3형태로는 표현 못 해요. **조건분기(4번째 형태)**가 이걸 표현해요:

```
S3. **dissolve 실행** → 바인딩: S1.verdict == "동등 입증" ? executor(thought-chain 제거 + CHANGELOG) : executor(thin alias 잔존)
```

분기 게이트(`S1.verdict`)는 **쟁점/트레이드오프 섹션**에 기록돼요(파서가 거기서 읽음). 이게 #105의 "CT 조건 미충족 시 thin alias 잔존"을 goal-doc 레시피로 표현하는 표기적 근거예요 — 스키마 부적합이 아니라 *CT 판정 결과*로 alias 여부가 갈리게 돼요.

### 3.5 산출 체이닝 — #105 thought-chain 동등성 (consensus MAJOR 반영)

thought-chain의 핵심 가치는 단계 간 **자동 출력 전달**(passing outputs between stages automatically)이에요. 시퀀스 표기(`→`)는 순서뿐 아니라 **산출→입력 체이닝**을 의미해요:

```
S2. **풀 분석** → 바인딩: unknown-discovery → expert-panel → doc-concretize → doc-polish
```

각 `→`는 **앞 슬라이스의 artifact path가 뒤 슬라이스의 payload로 들어감**을 뜻해요. 이 데이터 패싱의 런타임 계약(intent/format/payload/destination → artifact path)은 **#101 출력 어댑터 계약**이 담당해요(이 스펙 범위 밖, 본 goal은 #100 코어 집중). 표기 수준에서 thought-chain 4단계가 표현 가능함이 입증되므로 #105 "동등 편의"는 표기 부적합이 아닌 #101/#105 런타임에서 닫혀요.

> **linchpin 책임 한정**: 이 스펙은 thought-chain 동등성을 *표기로 표현 가능함*까지 보장해요. 실제 산출 패싱 *동작* 입증은 #105(depends_on=[G2,G3])의 e2e dogfood가 담당하고, 데이터 패싱 *계약*은 #101이 정의해요. 표기력은 여기서 닫혔어요(조건분기 + 시퀀스 체이닝).

### 3.6 work_type별 기본 바인딩 (Gap-ROUTE §4.1 정합)

| `work_type` | 기본 슬라이스 시퀀스 | 기본 바인딩 |
|-------------|---------------------|------------|
| `feature-full` | spec → impl → critique (**각각 별도 스킬** — 2026-06-03 결정, 단일 "spec-impl-critique" 아님) | spec=spec-first, impl=executor\|native(#133), critique=adversarial-review\|code-reviewer(#133) |
| `decision-only` | 실행 없음, 산출만 | expert-panel \| adversarial-review |
| `doc-only` | 출력 전용 | doc-concretize \| doc-polish \| spec-first |
| *(bug-light)* | *goal-doc 생략* | debug 직행(#133) — goal-doc 부재로 라우팅(§4.4) |

> impl/critique의 구체 귀속(재사용/native위임/신설)은 **#133 인벤토리**가 확정해요. 표기는 `candidate-or` 형태(`executor|native(#133)`, §3.2 문법 — 완전-TBD `placeholder` `<#133>`와 구분)로 두고 #133과 정합. **native 위임 우선** — #133이 "native agents/기존 leaf로 충분한지" 먼저 판정, 충분하면 신설 안 함.

---

## 4. parse/exec 인터페이스

### 4.1 실행 주체 — native 위임 우선 (경계 A 정합)

- **단기**: Claude Code 네이티브 `/goal` + Workflow + 기존 OMC **공존**. 자체 from-scratch 실행 엔진 빌드 안 함.
- **장기**: native substrate(`/goal`·Workflow·agents·hooks) 위 **경량 하네스가 strangler 점진(route-by-route) 흡수**. 자체 빌드는 native가 강제 못 하는 invariant enforcement(§4.3)에 한정.
- 근거: `claude-kit-boundary.md` §1(경계 A) + `omc-to-native-substrate.md`(strong-form 기각, narrow path 채택).

### 4.2 누가 파싱·실행하나

- **생성**: claude-kit이 goal-doc을 *생성*만 하는 ②출력 leaf예요(spec-first가 산출 어댑터). leaf는 harness를 import·assume 안 함(CON-5 단방향).
- **실행**: `/goal`은 **session-scoped Stop hook**이라 셸에서 mutate 불가 → 실행 주체는 **in-session 액티브 에이전트**예요. 액티브 에이전트가 goal-doc을 읽고 슬라이스를 §3 바인딩대로 위임(서브에이전트 spawn / 직접 수행)해요.
- 즉 **claude-kit = goal-doc 생성 leaf**, **harness/native = goal-doc 실행**. 이 분리가 경계 A의 ②(출력) vs ⑤(실행)에 정확히 대응해요.

### 4.3 INV-4 — 파서가 검증하는 것 (#122 §4.2)

goal-doc 파서는 이 스키마로 다음을 **결정적 검증**해요:

1. **required frontmatter 존재**: §1.1 core 8 + §1.2 `work_type`.
2. **enum 값 적법성**: `recommended_model` ∈ {haiku,sonnet,opus}, `status` ∈ {gated,ready}, `work_type` ∈ {feature-full,decision-only,doc-only}, `applies_tiers` ⊆ cumulative 형식. (`wave`는 §1.5대로 미검증.)
3. **본문 5섹션 존재**: §2 순서·존재.
4. **네임스페이스 해소**: `depends_on`=goal_id, `issues`=GitHub번호(§1.4).
5. **바인딩 구조 존재**: 슬라이스 라인이 §3 형식. (타겟 resolution은 라우터 런타임 책임 — INV-4 비대상.)

검증 통과 후 라우터가 `work_type`으로 §3.6 시퀀스를 결정·위임해요.

### 4.4 bug-light = goal-doc 부재 라우팅

버그수정 경량은 goal-doc을 **생략**해요(substrate §4.1 + G6). 따라서:

- goal-doc이 *존재*하면 `work_type` ∈ {feature-full, decision-only, doc-only} 중 하나(절대 bug-light 아님).
- bug-light는 인라인 트리거 → 라우터가 **goal-doc 없이 debug 직행**. (`work_type` 필드로 표현되는 게 아니라 goal-doc 부재 자체가 신호.)

이게 §1.2 work_type enum이 4종이 아니라 3종인 이유예요.

---

## 5. 하류 소비처 정합표

| 소비처 | 이 스펙이 제공하는 것 | 정합 |
|--------|---------------------|------|
| **#122 INV-4** (스키마 검증) | §4.3 결정적 검증 항목 + §1 enum 명시 + `work_type` 라우팅 키 | ✅ 파서가 검증·라우팅 가능 |
| **#122 Gap-ROUTE** (4종 라우터) | §1.2 `work_type` 1차 키 + §3.6 work_type별 기본 바인딩 + §4.4 bug-light 부재 처리 | ✅ 4종 전부 라우팅 |
| **#105** (thought-chain dissolve) | §3.4 조건분기(CT-게이트) + §3.5 산출 체이닝(4단계 시퀀스) | ✅ 표기력 닫힘(동작 입증=#105 e2e, 계약=#101) |
| **#125** (tier 선언) | §1.3 `applies_tiers` cumulative enum + 미선언 시맨틱(`[default]`) | ✅ 병합 지점=파싱 단계 입력 형식 확정 |
| **#133** (슬라이스 스킬 귀속) | §3.2 `candidate-or`/`placeholder` 문법 + §3.6 native 위임 우선 표기 | ✅ 미확정 귀속을 `candidate-or`(`executor\|native(#133)`)로, #133이 확정 |
| **#101** (출력 어댑터 계약) | §3.5 산출 체이닝의 런타임 계약을 #101에 위임 명시 | ✅ 경계 명확(이 스펙=표기, #101=데이터 패싱) |

> 표의 **✅ = *설계 표기 수준* 정합**이에요 — 하류 *구현* 검증(파서·라우터)은 #122 P2~P3에서 이뤄져요(`omc-to-native-substrate.md` §5). 이 스펙은 그 구현이 의존할 계약을 표기 수준에서 닫아요.

---

## 6. dogfooding 레퍼런스 + 발견

### 6.1 G2 자기 참조

이 스펙의 첫 레퍼런스 구현은 `docs/plans/goal-docs/G2-goal-doc-output-contract.md`예요. G2는 8 core 필드 + 본문 5섹션을 실사용했고, 그게 §1.1/§2의 베이스라인이에요.

### 6.2 dogfooding이 발견한 것 (스펙 권고 반영)

| 발견 | 출처 | 스펙 반영 |
|------|------|----------|
| `status: gated` 게이트 표기가 유용 | G2 frontmatter | §1.1 `status` enum에 `gated` 포함 |
| 쟁점 표의 backlog/게이트 처리 패턴 | G2 §쟁점 | §2 섹션3에 verdict 기록 위치로 활용(§3.4) |
| **워크타입 선언 필드 부재가 라우팅 불가를 야기** | consensus 게이트(G2를 파서에 넣는 반례) | §1.2 `work_type` required 추가 ← 가장 큰 발견 |
| 조건분기 슬라이스 필요 | G5 S3-PASS/ALIAS | §3.4 4번째 바인딩 형태 추가 |
| `wave` 타입 불일치(정수 vs 라벨) | G9/G10/G12 코퍼스 | §1.5 wave를 사람용 라벨로 정직하게 선언 |

### 6.3 dogfooding 표본 범위 한정 (정직성 — consensus 반영)

> **false confidence 차단**: G2를 (work_type을 사후 분류하면) doc-only에 해당하는 표본이에요(doc-concretize 바인딩). 단 G2 *작성 시점*엔 `work_type` 필드 자체가 없었어요 — consensus 게이트 이전 코퍼스 G1~G12 초안 전부 미보유였고(이 필드는 게이트가 신설), 그 **부재**가 §1.2 결함을 dogfooding만으로 못 잡은 직접 증거예요. 스펙 확정 후 레퍼런스 G2엔 `work_type: doc-only`를 부여했고, **나머지 G1·G3~G12의 work_type 부여(마이그레이션)는 INV-4 파서 도입(#122 P2~P3)의 선행 요건**이에요. 따라서 G2 dogfooding이 *직접* 검증하는 건 **doc-only류 워크타입의 스키마 적합성**까지고, 가장 복잡한 **feature-full**(spec→impl→critique 3단계 + 산출 패싱) 워크타입의 e2e 검증은 **#122 P4의 "feature-dev goal-doc 1개 e2e dogfood"**(`omc-to-native-substrate.md` §5 P4)로 명시 이관해요. G1/G6 등이 executor 바인딩으로 부분 표본을 주지만 그건 별도 청크 작성이지 G2 dogfooding이 아니에요. §1.2 work_type 결함이 doc-only류 표본 자가검증만으로는 안 잡히고 consensus 게이트에서 잡힌 게 이 한정의 증거예요.

---

## 7. #100 Acceptance 추적

| #100 Acceptance | 충족 위치 |
|-----------------|----------|
| goal-doc **스키마** spec doc (frontmatter + 본문 5섹션 의미·필수성·작성 규칙) | §1(frontmatter) + §2(본문 5섹션) |
| **슬라이스→스킬 바인딩 표기법** (각 슬라이스 `바인딩: <skill/agent>` + 기본 바인딩, spec→impl→critique 각각 별도 스킬, 귀속은 #133 정합) | §3(전체) + §3.6(work_type별 기본 바인딩) |
| **parse/exec 인터페이스** (native 위임 우선, `/goal`=Stop hook이라 실행=in-session 액티브 에이전트, claude-kit=생성 leaf) | §4(전체) |
| G2 dogfooding 레퍼런스 인용 + 발견 필드/패턴 반영 | §6 |
| 하류 소비처 정합(#122 INV-4·#105·#125·#133·#101) | §5 |

---

**참조**: `docs/design/claude-kit-boundary.md`(경계 A·CON-4), `docs/design/omc-to-native-substrate.md`(§4.1 Gap-ROUTE·§4.2 INV-4·§5 strangler), `docs/plans/goal-docs/G2-goal-doc-output-contract.md`(dogfood), `docs/plans/goal-docs/G5-thought-chain-dissolve.md`(조건분기 dogfood), #100/#122/#105/#125/#133/#101.
