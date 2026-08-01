# 출력 어댑터 계약 — 균일 호출 인터페이스 + 포맷×동작 매핑 + net-new gap

**Status**: design · **Created**: 2026-06-04 · **Issue**: #101 · **Epic**: #108
**선행**: #99(경계 A — `docs/design/claude-kit-boundary.md`)
**하류 소비처**: #102(출력 레이어 물리 구조 — 이 *논리* 계약을 입력) · #103/#104(② 출력 레이어 조립) · #122 Gap-ROUTE(라우터가 이 어댑터로 슬라이스를 위임) · #133(issue-authoring 경계)
**Source**: #108 레이어 재설계 논의 C-5(신설 최소화 만장일치) · G2 어댑터 슬라이스 · goal-doc-spec §3.5

> **위치(논리 계약, 물리 구조 아님)**: 이 문서는 슬라이스가 출력 스킬을 *어떻게 균일하게 호출하는지*의 **논리적 계약**만 정의해요. ②를 단일 플러그인으로 묶을지 분산할지의 **물리 구조 확정은 #102(G3 wave)** 게이트라 여기서 안 다뤄요(계약은 구조 독립적 — #101 Acceptance는 #102 결정 없이 충족). 헌법(CON-*)/정책(POL-*) 규칙은 `docs/design/claude-kit-boundary.md`가 단일 출처고, 이 문서는 그걸 **참조만** 하고 재정의하지 않아요.

> **삭제된 문서 인용 주의**: 본문이 인용하는 `goal-doc-spec.md`(#282/#283 하네스 철회로 2026-06-29 삭제) · `execution-skill-inventory.md` · `omc-to-native-substrate.md` · G2 goal-doc · 레이어 재설계 토론 문서는 **더 이상 열리는 파일이 없어요**(2026-07-21 정리). 이 문서 자체(어댑터 계약)는 지금도 유효하고 CLAUDE.md가 참조하는 현행 문서예요 — 위 인용들은 논증의 출처 표시로만 읽고, 근거가 필요하면 함께 적힌 이슈 번호로 찾으세요.

---

## 0. 이 계약이 푸는 문제 — 왜 어댑터인가

claude-kit ②(결정화·출력) 레이어의 출력 자산은 **이질적**이에요. graphify는 다단계 파이프라인 커맨드, `note`/`capture`는 user-initiated 슬래시 커맨드, doc-concretize/doc-polish/build-spec는 모델 호출 스킬, gh는 셸 CLI예요. 입력도 제각각(폴더 경로 / 토픽 문자열 / 직전 산출물 / 구조화 Seed)이고 출력 목적지도 제각각(repo-local / vault / GitHub / stdout)이에요.

goal-doc 슬라이스(`docs/design/goal-doc-spec.md` §3)는 이걸 `바인딩: <skill>` 한 줄로 가리키는데, **그 바인딩이 가리키는 호출 계약이 없으면 표기법이 공허**해요(G2 배경 §). 그래서 가치는 **신규 스킬이 아니라 "어떤 출력이든 균일하게 호출하는 어댑터 계약"**이에요 — SUMMARY.md **C-5 만장일치**:

> ②는 대부분 기존 *조립*. net-new ≤1-2(issue 통합 정도). 가치는 신규 스킬이 아니라 /goal 슬라이스-바인딩이 균일 호출하는 **출력 어댑터 계약** + intent/포맷 라우팅.

이 문서는 그 어댑터 계약을 (1) 균일 호출 인터페이스(§1), (2) 포맷×동작 8매핑(§2), (3) 산출 체이닝 계약(§3), (4) net-new gap(§4)으로 확정해요.

---

## 1. 균일 호출 인터페이스

어댑터는 이질적 출력 자산을 **물리적으로 통합하지 않아요**(그건 #102). 대신 **호출 규약(calling convention)**을 통일해요 — 라우터(Gap-ROUTE)가 바인딩된 스킬이 무엇이든 동일한 4-튜플을 넣고 동일한 2-튜플을 받아요.

### 1.1 입력 계약 — 4-튜플 `(intent, format, payload, destination)`

| 필드 | 타입 | enum/형식 | 의미 | 라우팅 역할 |
|------|------|----------|------|------------|
| `intent` | enum | `visualize` \| `capture` \| `crystallize` \| `author` \| `edit` \| `handoff` \| `record` \| `file-issue` | 슬라이스의 *동작*(왜·무엇을 하려는가) | `format`과 함께 어댑터 타겟 결정(§2). 한 `format` 안에서 타겟이 갈릴 때 디스앰비규에이터(예: `format=md` × `author`→doc-concretize / `edit`→doc-polish) |
| `format` | enum | `html` \| `note` \| `goal-doc` \| `handoff` \| `session` \| `md` \| `issue` | 산출물의 *형식* | §2 매핑표의 1차 키(8행) |
| `payload` | union | `source_path` \| `topic_string` \| `prior_artifact_ref` \| `structured_seed` | 입력 내용. 체이닝 시 직전 슬라이스의 `artifact_path`(§3) | 어댑터에 전달되는 본문 |
| `destination` | enum | `repo_path` \| `vault`(게이트) \| `github` \| `stdout` \| `local_ephemeral` | 산출물이 안착할 위치 | `vault`는 CON-1 게이트(§1.3) |

> **`intent`×`format`이 "동작×포맷"**: §2 매핑표가 정확히 이 곱집합의 의미 있는 셀만 채워요. `format`이 1차 키, `intent`가 한 포맷 내 분기(md·issue에서만 실분기 발생)예요.

> **`format=goal-doc`의 실제 산출물 주의**: 이 enum 값의 매핑 타겟 build-spec의 실제 산출물은 YAML Seed(`docs/specs/{slug}.yaml`)이지 `goal-doc-spec` 8필드 문서가 아니에요 — *intent 수준* 정합이고, Seed→goal-doc 재프레임은 **#111 소관**이에요(§2 #3 주의 참조). 라우터(#122)는 enum만 보지 말고 §2 #3 주의를 함께 읽어야 해요.

> **`intent=file-issue` 명명 의도**: 다른 intent 값은 단일 동사형(`visualize`·`capture`·`author`)인데 `file-issue`만 동사+목적어형이에요 — `format=issue`와의 충돌을 피하면서 *기계적 파일링*(gh 생성/종료, §2 #8)을 본문 *저작*(issue-authoring, §4.1)과 구분하려는 의도적 명명이에요.

### 1.2 출력 계약 — 2-튜플 `(artifact_path, status)`

| 필드 | 타입 | enum/형식 | 의미 |
|------|------|----------|------|
| `artifact_path` | typed-ref | `file` \| `vault-ref` \| `github-url` \| `stdout-text` | 산출물의 해소 가능한 참조. **타입 태그를 동반**(체이닝 호환성 판정용 §3.2) |
| `status` | enum | `success` \| `gated` \| `partial` \| `failed` | 실행 결과. `gated`=산출 준비됐으나 user-initiated 확정 대기(CON-1 vault write) 또는 분기 게이트 verdict 대기(`goal-doc-spec` §3.4) |

- `artifact_path`는 **단일 책임**: "다음 슬라이스가 `payload`로 집어넣을 수 있는 참조"를 반환해요. 이게 산출 체이닝(§3)의 핸드오프 토큰이에요.
- `status: gated`는 실패가 아니에요 — "어댑터는 제 몫을 다했고, 비가역/소유권 게이트(vault write, 분기 verdict) 때문에 다음 행동이 user/라우터로 넘어감"의 신호예요.

### 1.3 gating 차원 — CON-1/CON-3 참조 (재정의 아님)

`destination = vault`인 어댑터(note·session)는 **항상 `status: gated`로 시작**해요. 근거는 `claude-kit-boundary.md`의 헌법 규칙이고 여기서 재정의하지 않아요:

- **CON-1**(vault writes: new-file-only, user-initiated slash command only) → vault 목적지 어댑터는 서브에이전트가 자동 호출 불가. 라우터는 어댑터를 *준비*시키되 쓰기는 메인 컨텍스트 슬래시 커맨드(`/vault-save`·`/wiki`)로만 개시. 어댑터 반환 `status: gated`가 이 경계의 런타임 표식.
- **CON-3**(self-approval 금지) → 출력이 *critique/검증* 산출일 때 저작≠리뷰 분리. 단 이건 ⑤ 실행/게이트 영역(#132 Gap-INV)이지 출력 어댑터 영역이 아니에요 — 이 문서는 *출력*만 다루고 critique 격리는 #122/#134로 위임.

> vault가 아닌 목적지(`repo_path`·`stdout`·`local_ephemeral`·`github`)는 CON-1 게이트 대상이 아니에요. 특히 `/handoff`는 vault를 **안 건드리고** 로컬 gitignored `resume.md` 또는 stdout만 산출하므로 `gated`가 아니라 `success`예요(§2 #4 주의). (`/handoff`는 G26에서 retire — 인수인계 기능은 머신 레벨 `session-close` 스킬로 이관, 이 레포 외부.)

> **START-PROMPT는 native `/goal` 평가자 입력 (#285)**: retired `/handoff`(row #4)·`/save-session`(row #5)이 산출하던 다음-세션 인계 산출물 = START-PROMPT는 이제 session-close ④(이 레포 외부)가 저작하고, native `/goal` 평가자가 소비해요. 표준 정본·경계 anchor는 #285 + `claude-kit-boundary.md` §2.5. 무인 실행 중 비가역 액션의 on-the-loop 게이트는 #309 P3 + `claude-kit-boundary.md` §2.5-1.

---

## 2. 포맷×동작 매핑표 (8매핑)

각 행 = 한 `(format, 대표 intent)` → 한 어댑터 타겟. **8개 전부 기존 자산을 가리켜요**(net-new는 §4 issue-authoring 1건뿐). 타겟 열의 "구현체"는 호출 메커니즘이 이질적임을 드러내요 — 어댑터가 통일하는 건 *호출 규약*이지 구현이 아니거든요.

| # | `format` | `intent` | 어댑터 타겟 (구현체) | 레이어 | 호출 메커니즘 | 기본 `destination` | `status` 특이 |
|---|----------|----------|---------------------|--------|--------------|-------------------|--------------|
| 1 | `html` | `visualize` | **graphify** (`/graphify` 스킬 → AST+의미추출 파이프라인) | ②(graphify html 산출 · ① 인접 §2 주의) | 슬래시 커맨드 + 서브에이전트 fan-out | `repo_path` (`graphify-out/graph.html`+`graph.json`+`GRAPH_REPORT.md`) | `success` |
| 2 | `note` | `capture` | **vault-bridge `/vault-save`** (#480 — OVM `/note` 대체) | ③ delivery leaf (vault-bridge) | user-initiated 슬래시 커맨드 | `vault` (`notes/{slug}.md` 또는 `notes/decision-YYYY-MM-DD-{slug}.md`) | **`gated`** (CON-1) |
| 3 | `goal-doc` | `crystallize` | **build-spec** (요구사항 결정화) | ② 출력 leaf | 모델 호출 스킬 (Socratic 게이트) | `repo_path` (`docs/specs/{slug}.yaml` Seed) | `success` · **Seed↔goal-doc 재프레임=#111** (§2 주의) |
| 4 | `handoff` | `handoff` | **`/handoff`** (vault-bridge 커맨드 — G26에서 retire, 머신 레벨 `session-close` 스킬로 이관·이 레포 외부) | vault-bridge 커맨드 (로컬 핸드오프 · **vault 비경유** → ③ "vault 운반"에 미해당) | user-initiated 슬래시 커맨드 (`disable-model-invocation`) | `local_ephemeral` (`.claude-kit/vault-bridge/resume.md`, gitignored) 또는 `stdout` | `success` (**vault 미사용 → CON-1 비대상**) |
| 5 | ~~`session`~~ | ~~`record`~~ | ~~**`/save-session`**~~ — **RETIRED (#331, 2026-07-10)**: 세션지식 경로가 wiki-first로 재정의돼 OVM `/wiki` + native memory로 이관. 원석 캡처는 OVM `/capture`가 담당 | — | — | — | — |
| 6 | `md` | `author` | **doc-concretize** (신규 MD 구조화 저작) | ② 출력 leaf | 모델 호출 스킬 | `repo_path` (임의 `.md`) | `success` |
| 7 | `md` | `edit` | **doc-polish** (기존 MD 린트·개선, Editor-not-Writer) | ② 출력 leaf | 모델 호출 스킬 | `repo_path` (기존 `.md` in-place Edit) | `success` |
| 8 | `issue` | `file-issue` | **gh CLI** (기계적 생성/종료/라벨/코멘트) | 외부 도구 (③ GitHub 딜리버리) | 셸 Bash | `github` (이슈 URL) | `success` · **본문 *저작*은 gap → §4 issue-authoring** |

> **매핑 정직성 주의 (#3 goal-doc=build-spec)**: build-spec의 *실제 산출물*은 요구사항 3요소(`goal`/`constraints`/`success_criteria`)를 담은 **YAML Seed**(`docs/specs/{slug}.yaml`)지, `goal-doc-spec` §1~§2의 frontmatter 8필드+본문 5섹션 **goal-doc이 아니에요**. 매핑 `goal-doc=build-spec`는 *"명세 결정화 출력"이라는 intent 수준* 정합이고, Seed→goal-doc 산출물 재프레임(build-spec를 ② goal-doc 출력 스킬로 포지셔닝/개명할지)은 **#111(build-spec reconcile)의 소관**이에요 — 이 문서는 그걸 **재정의하지 않고 위임만** 해요. 따라서 goal-doc 저작은 §4 net-new gap이 *아니에요*(기존 #111 트랙이 소유).

> **매핑 정직성 주의 (#1 graphify)**: graphify는 코퍼스→지식그래프 산출이라 ①(인지: 연결 발견)과 ②(출력: html/json) 경계에 걸쳐요. 출력 어댑터 관점에선 `html` 포맷 산출 타겟이고, 산출물(`graph.html`)이 §3 체이닝의 `file` 참조로 흘러요.

> **행 #5 폐기 경위 (2026-07-08 D1 → 2026-07-10 #331)**: 먼저 D1이 `/save-session`을 session-note 저작에서 `type:capture` 원석 캡처로 재목적화했고(`claude-kit-boundary.md` §2 D1, 커밋 `f59f580`), 이틀 뒤 #331이 커맨드 자체를 retire했어요 — 원석 캡처는 이미 OVM `/capture`가 하고 있어 중복이었거든요. 세션 지식은 이제 OVM `/wiki`(컴파일) + native memory로 갑니다. 즉 `session`은 더 이상 유효한 format enum 값이 아니에요.

---

## 3. 산출 체이닝 계약 (`goal-doc-spec` §3.5 정합)

`goal-doc-spec` §3.5는 시퀀스 표기 `→`가 단순 순서가 아니라 **산출→입력 체이닝**임을 정의하고, 그 런타임 계약을 명시적으로 이 문서에 위임해요:

> (§3.5 인용) 각 `→`는 **앞 슬라이스의 artifact path가 뒤 슬라이스의 payload로 들어감**을 뜻해요. 이 데이터 패싱의 런타임 계약(intent/format/payload/destination → artifact path)은 **#101 출력 어댑터 계약**이 담당해요.

### 3.1 체이닝 = `artifact_path(N) → payload(N+1)`

§1의 입출력 계약이 §3.5 위임을 **1:1로 실현**해요:

```
slice N    : adapter(intent_N, format_N, payload_N, dest_N) → (artifact_path_N, status_N)
slice N+1  : payload_{N+1} := artifact_path_N            # ← "→"의 런타임 의미
             adapter(intent_{N+1}, format_{N+1}, payload_{N+1}, dest_{N+1}) → ...
```

즉 `goal-doc-spec` §3.5의 예시 `unknown-discovery → expert-panel → doc-concretize → doc-polish`는, 각 `→`에서 앞 어댑터의 `artifact_path`(타입 태그 동반)가 뒤 어댑터의 `payload`로 바인딩되는 것으로 실행돼요. §1.2가 `artifact_path`를 "다음 슬라이스가 payload로 집어넣을 참조"로 단일 정의한 게 이걸 위한 거예요.

### 3.2 체이닝 타입 호환성 — 라우터 런타임 책임

`artifact_path`는 타입 태그(`file`/`vault-ref`/`github-url`/`stdout-text`)를 동반해요. `→`는 **`artifact_path` 타입(N)이 어댑터(N+1)의 허용 `payload` 타입일 때만 유효**해요:

- 호환 예: doc-concretize(`file:.md`) `→` doc-polish(`payload=source_path` 수용) ✅
- 비호환 예: gh(`github-url`) `→` doc-polish(`.md` 파일 기대) ✗ — 변환 슬라이스 필요

`goal-doc-spec` §3.2가 *바인딩 타겟 resolution*을 INV-4 비검증·라우터 런타임 책임(#122)으로 둔 것과 동형으로, **체이닝 타입 호환성도 INV-4 스키마 검증 대상이 아니라 라우터 런타임 책임**이에요. 어댑터는 `artifact_path` 타입을 *선언*만 하고, 호환성 *판정/거부*는 Gap-ROUTE 라우터(#122 S2 `test-slice-router.py` 예정)가 해요. 이 분리가 "표기/계약 = 설계 수준, resolution/호환 = 런타임 수준"이라는 linchpin 경계와 정합해요(`goal-doc-spec` §5 주석).

### 3.3 조건분기 verdict와 `status` (§3.4 인접)

`goal-doc-spec` §3.4 조건분기(`S1.verdict == PASS ? ... : ...`)의 verdict는 ①인지 스킬(adversarial-review survival 등)이 산출하고 쟁점/트레이드오프 섹션에 기록돼요. 출력 어댑터 관점에선 `status: gated`가 "분기 게이트 입력 대기"를 표현할 수 있으나, **verdict의 *생성*은 출력 어댑터가 아니라 ①인지/⑤게이트 영역**이에요. 이 문서는 `status` enum에 `gated`를 둬 분기/CON-1 게이트를 *표현*만 하고, verdict 생성·분기 선택 로직은 #122/#134로 위임해요(범위 분리).

---

## 4. net-new gap 목록 (≤2)

C-5 만장일치 "신설 최소화" 준수 — **gap이 입증될 때만 신설**, 무근거 신설 금지. §2의 8매핑이 전부 기존 자산이므로 net-new는 다음 **1건**이에요(상한 2 이내).

### 4.1 issue-authoring (net-new #1, 유일 firm)

| 항목 | 내용 |
|------|------|
| **gap** | `format=issue`의 §2 #8 매핑은 gh CLI로 *기계적* 생성/종료/라벨만 커버해요. issue **본문 저작**(템플릿 선택·라벨 추론·**기존 이슈 대비 중복 검출**·Acceptance 구조화)은 gh CLI에 빈틈이에요. |
| **왜 native·기존으로 안 되나** | gh는 전송 도구지 저작기가 아니에요. doc-concretize(②)는 임의 MD 저작이라 이슈 *스키마*(라벨 체계·중복 검출)를 모르고, OVM note(②)는 vault 전용이에요. |
| **레이어 귀속** | **② 출력 leaf**. 근거: `claude-kit-boundary.md` 레이어 표(line 25)가 `issue`를 이미 ②로, line 38이 "issue-skill의 ②출력 leaf 귀속"을 단일 출처로 확정. intra-leaf 합성(diverse-sampling Mode B → issue 본문 후보 생성)은 boundary §3 "규율 범위"로 허용. |
| **#133 경계** | 이 gap의 *선언*은 #101(이 문서), *실행스킬 인벤토리 귀속 판정*은 #133. 중복 0 — §5.2 참조. |

### 4.2 net-new이 *아닌* 것 (정직성 — 명시 배제)

1:1 정합을 흐리지 않으려고, gap처럼 보이나 net-new가 아닌 항목을 명시 배제해요:

- **goal-doc 저작 (build-spec Seed↔goal-doc)**: §2 #3 주의대로 Seed→goal-doc 재프레임은 **#111의 기존 트랙**이지 #101 신설 gap이 아니에요. build-spec는 이미 존재하는 ② 자산이고, 포지셔닝/개명은 #111이 소유.
- **debug · quality**(⑤ 실행 스킬 신설 후보): 이건 *출력 포맷* gap이 아니라 **⑤ 실행 스킬** 축이라 #133 소관이에요. 출력 어댑터(이 문서)의 net-new에 안 셈 — 축이 다름(§5.2).

> **결론**: #101 출력-포맷 축의 net-new = **issue-authoring 1건**(≤2 충족, C-5 "≤1-2" 준수). debug/quality는 #133 실행-스킬 축의 별도 후보이고, 두 축이 만나는 유일 지점이 issue(=②, §5.2)예요.

---

## 5. 경계 정합

### 5.1 #102(물리 구조)와의 경계

이 문서 = **논리 계약**(어댑터 호출 규약·매핑·체이닝). ②를 단일 플러그인으로 묶을지(기존 출력 자산이 이미 도메인별 분산 — 물리 위치는 `output-layer-structure-adr.md` §0) 분산 유지할지의 **물리 구조는 #102(G3 wave)** 결정이에요. 어댑터 계약은 구조 독립적이라 #102 어느 결과에도 불변 — #101 Acceptance는 #102 없이 충족(G2 쟁점 표 "출력 레이어 물리 구조" 행 정합).

> **#102 RESOLVED (2026-06-04, PR #139)**: **분산(논리 계약)** 채택 — `output-layer-structure-adr.md`. (정정: graphify는 claude-kit 마켓플레이스 플러그인이 아니라 user-level 스킬이에요 — 초기 §5.1 표현을 ADR §0에서 정정.)

### 5.2 #133(실행 스킬 인벤토리)와의 issue-authoring 경계 — 중복 0

issue-authoring은 #101(출력-포맷 축)과 #133(실행-스킬 축)이 만나는 **유일 교차점**이에요. 중복 0을 위해 소유권을 분할해요:

| 책임 | 소유 doc | 내용 |
|------|---------|------|
| gap *선언* + 어댑터 *매핑* (`issue=gh CLI` + 본문 저작 빈틈) | **#101** (이 문서 §2 #8 + §4.1) | "issue-authoring이 net-new gap이다" + 호출 규약 |
| 실행스킬 *판정* + *레이어 귀속* (재사용/native/신설, ②) | **#133** | "gh CLI=외부 재사용, issue-authoring=신설 ② leaf" |

두 doc은 서로 **참조만** 하고 상대 영역을 재정의하지 않아요. net-new gap은 #101이 *한 번* 선언하고, 레이어 귀속은 #133이 *한 번* 판정해요(`boundary` line 25/38 단일 출처 인용). → 중복 0.

> **의사결정 기록(거울 표 해소)**: 이 분할표는 한때 #133 문서 §4에 거울로도 존재했고 수동 동기화 대상이었어요. 그 문서가 goal-doc 하네스 철회(#282/#283)로 삭제되면서 **이 §5.2가 유일한 출처**가 됐어요 — 동기화 부담도 drift 리스크도 함께 사라졌어요.

### 5.3 #122 Gap-ROUTE와의 경계

라우터(#132 Gap-ROUTE)는 `work_type`→슬라이스 시퀀스를 결정한 뒤, 각 슬라이스 바인딩을 **이 어댑터 계약으로 호출**해요. 즉 어댑터 = 라우터가 이질적 출력 자산을 균일 호출하는 인터페이스 layer. resolution(타겟 실재)·체이닝 타입 호환은 §3.2대로 라우터 런타임 책임.

---

## 6. #101 Acceptance 추적

| #101 Acceptance | 충족 위치 |
|-----------------|----------|
| **계약 doc** (슬라이스가 출력 스킬을 호출하는 균일 인터페이스: 입력 intent/format/payload/destination, 출력 artifact path + 상태) | §1(4-튜플 입력 + 2-튜플 출력) |
| **포맷×동작 매트릭스** (html=graphify, note=OVM note, goal-doc=build-spec, handoff=/handoff [G26 retire → 머신 레벨 `session-close`], session=/save-session [#331 retire → OVM `/wiki`+memory], md저작=doc-concretize, md편집=doc-polish, issue=gh CLI) | §2(8매핑 표) |
| **net-new gap 목록**(≤2, 유력 issue-authoring) | §4(issue-authoring 1건 + 명시 배제) |
| (정합) `goal-doc-spec` §3.5 산출 체이닝 런타임 계약 | §3(`artifact_path(N)→payload(N+1)` + 타입 호환) |
| (정합) #133 issue-authoring 경계 중복 0 | §5.2(소유권 분할표) |

> 위 표의 처음 3행은 **#101 이슈 Acceptance 기준**(계약 doc·매트릭스·gap 목록)이고, `(정합)` 표시 2행은 하류 스펙(§3.5·#133)과의 **추가 정합 확인** 항목이에요 — 이슈 Acceptance가 아니라 본 PR이 추가로 닫은 경계 정합이에요.

---

**참조**: `docs/design/claude-kit-boundary.md`(경계 A·CON-1/CON-3·② 레이어 표·issue ② 귀속 line 25/38) · #99/#100/#102/#111/#122/#132/#133. (goal-doc-spec·omc-to-native-substrate·execution-skill-inventory·G2 goal-doc·레이어 재설계 토론 문서는 goal-doc 하네스 철회(#282/#283)와 함께 삭제됐어요 — 근거는 각 이슈 번호로 찾으세요.)
