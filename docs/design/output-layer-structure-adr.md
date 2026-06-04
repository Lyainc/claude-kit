# 출력 레이어 물리 구조 ADR — 단일 플러그인 vs 분산(논리 계약)

**Status**: design (decision · accepted) · **Created**: 2026-06-04 · **Issue**: #102 · **Epic**: #108
**선행**: #99(`docs/design/claude-kit-boundary.md` — 경계 A·CON-5·leaf vendor-neutral) · #100(`docs/design/goal-doc-spec.md` — work_type) · #101(`docs/design/output-adapter-contract.md` — 직계 입력, §5.1 #102 경계)
**하류 소비처**: #103(doc-concretize/doc-polish 행선지 U-1) · #124(diverse-sampling Mode B 호출 경로, #103 경유 2차) · #111-4(spec-first 물리 분리) · #138(mirror drift 가드 위치) · issue-authoring 빌드 위치
**Source**: `docs/discussions/20260602_claude-kit-layer-redesign/UNRESOLVED.md` U-2/U-1 · `SUMMARY.md` C-2/C-5 · `docs/plans/goal-docs/G2-goal-doc-output-contract.md` 쟁점 표

> **위치(물리 구조만)**: 이 ADR은 ②(결정화·출력) 레이어의 **물리 구조만** 결정해요. 출력 자산을 *어떻게 균일하게 호출하는지*의 **논리 계약**은 #101이 이미 닫았고(`output-adapter-contract.md` §5.1 — 어댑터 계약은 구조 독립적, #102 어느 결과에도 불변), 이 ADR은 그걸 입력으로 받아 *물리 귀속*만 확정해요. 헌법(CON-*)/정책(POL-*) 규칙은 `claude-kit-boundary.md`가 단일 출처고, 이 문서는 **참조만** 하고 재정의하지 않아요.

---

## 0. 결정 대상 — 무엇이 미결인가

#101이 논리 어댑터 계약(균일 호출 4-튜플 입력 / 2-튜플 출력 규약·포맷×동작 8매핑·산출 체이닝)을 닫았어요. 남은 미결 = ②를 **물리적으로 단일 플러그인으로 묶을지 vs 분산 유지할지**예요(UNRESOLVED.md U-2). #101이 "어떻게 호출하나"를 닫았으니, 이 ADR이 푸는 건 "어디에 물리적으로 사나" 단 하나예요.

핵심 관찰: 기존 ② 출력 자산은 *이미* 서로 다른 곳에 도메인별로 흩어져 있어요. 단 "5개가 5곳에 분산"이라는 단순 서사는 부정확해요 — 단일 통합의 실 비용을 정직하게 보려면 *무엇이 실제로 이동 대상인지*를 구분해야 하거든요.

| ② 출력 자산 | 현재 물리 위치 | 도메인 | 단일 통합 시 성격 |
|------------|---------------|--------|------------------|
| graphify(html) | **user-level 스킬** (`~/.claude/skills/graphify/`, claude-kit 마켓플레이스 **미등록**) | 시각화 | *이동 아님* — 신규 채택 여부라는 별개 결정 |
| OVM note | obsidian-vault-manager (vault 도메인 플러그인) | vault 지식 | 도메인 분리 이동 (note↔vault 응집 파괴) |
| spec-first / doc-concretize / doc-polish | thinking-tools (인지 플러그인) | 인지·저작 | thinking-tools에서 추출 (이미 한 곳) |
| handoff / save-session | vault-bridge 커맨드 | 세션·딜리버리 (#101 §2: ③ 딜리버리·vault 운반) | *② 아님* — ③ 결합이라 ② 통합 부적합 |
| gh(issue) | 외부 CLI | GitHub (전송=gh 외부 / 본문 *저작*=issue-authoring ② leaf, #133) | *이동 아님* — 외부 전송 도구 |

> **이동 대상의 실제 범위 (정직성)**: claude-kit 마켓플레이스 플러그인은 **3개**(thinking-tools · obsidian-vault-manager · vault-bridge)뿐이에요. graphify는 user-level 스킬이라 단일 통합 시 "이동"이 아니라 "신규 채택"이고, gh는 외부 도구, handoff/save-session은 #101 §2가 vault-bridge 커맨드/③ 딜리버리로 귀속해요. 즉 단일화의 *실질 이동 대상*은 thinking-tools의 doc-concretize/doc-polish/spec-first(± OVM note) 정도로 좁아요. 이 좁은 집합이 §2.2 단일 반증의 정직한 입력이에요 — 비용은 "5곳 통합"보다 작지만, *바로 그 좁음*이 C-2 위반으로 이어진다는 게 §2.2의 핵심이에요.

work_type = decision-only예요 → 산출 = **결정 + 근거 ADR, 코드 없음**(#102 Acceptance: "결정 + 근거 ADR"). 이 ADR이 실행(파일 이동·스캐폴딩)을 하는 게 아니라 *어느 물리 구조를 채택할지*만 못박아요.

---

## 1. 선택지 비교 (최소 3안)

| 선택지 | 정의 | 장점 | 단점 |
|--------|------|------|------|
| **1. 단일 플러그인** | ② 출력 자산을 신규 단일 "output" 플러그인으로 물리 통합 | A) 런타임 호출 균일성 — 단 #101 §5.1이 이미 구조 독립으로 충족(§2.2). B) **소스 co-location/유지보수 응집**(한 디렉토리 발견·편집, 매니페스트·버전·trigger 한 곳 관리) — 단일이 실제로 주는 별개 이점(§2.2 인정 후 기각) | 실질 이동 대상(thinking-tools의 doc-*/spec-first ± OVM note) 추출 + 도메인 응집 파괴(note↔vault, doc-*↔인지 코어) + 새 마켓 엔트리. **결정타**: 비용 줄이려 좁게 추출할수록(doc-*/spec-first만) 정확히 **C-2가 금지한 thin doc-tools 플러그인**(약한 응집)이 됨 — 비용 최소화 ≡ C-2 위반(§2.2) |
| **2. 분산 (논리 계약)** | 기존 자산을 각자 도메인 플러그인에 유지. "출력 레이어"의 실체 = 물리 플러그인이 아니라 #101 논리적 어댑터 계약(균일 호출 인터페이스) | 재배치 비용 0 · **C-2(thin 금지) 정합** · C-5 정합 · 도메인 응집 보존 | "출력 레이어"가 물리적으로 안 보여 발견성/응집이 약함(완화: #101 어댑터 계약 doc이 논리적 단일 진입점, /goal 슬라이스 바인딩이 스킬을 *이름*으로 호출하므로 물리 위치는 발견성과 무관) |
| **3. OVM-fold (전체)** | ② 출력 자산을 obsidian-vault-manager에 **전체 흡수**(whole-layer fold) | 기존 플러그인 재사용(신설 0) | html(graphify)·YAML Seed(spec-first)를 vault 도메인에 넣으면 경계 붕괴 — #102가 닫는 건 이 *전체* fold뿐. ※ doc-* **부분** md-fold는 option 3이 아니라 분산의 sub-variant(§2.3)이고 #103이 자산 도메인 적합성으로 정함 — 여기서 선결정 안 함 |

---

## 2. Verdict — **분산 (논리 계약)** 채택

**채택: 선택지 2 — 분산 (논리 계약). Confidence: Strong** — 단일·OVM-fold를 반증했고 분산이 어드버서리얼 압력 하에서 생존했어요.

### 2.1 근거 인용 (Source 정합)

- **U-2 잠정 우세 = 분산** — UNRESOLVED.md U-2: "잠정 우세: 논리적 계약(분산) — 기존 자산 재배치 최소화."
- **C-2 = thin 2-스킬 doc-tools 플러그인 신설 금지** — SUMMARY.md C-2 제약: "thin 2-스킬 doc-tools 플러그인 신설 금지(약한 응집). 분산 또는 fold 선호."
- **C-5 = 신설 최소화 만장일치** — SUMMARY.md C-5("신설 최소화 + 균일 어댑터", 만장일치).

> **C-5 reframe 차단**: 단일 측은 "C-5는 *신규 스킬* proliferation 제약이고, 기존 스킬 *재배치*는 net-new 0이라 신설이 아니라 통합"으로 reframe할 수 있어요(C-5 원문 "가치는 신규 스킬이 아니라 어댑터 계약"은 *스킬* net-new를 말함). 이 reframe는 C-5 *문면*은 피해가요. 그래서 단일 패배의 load-bearing 근거는 C-5가 아니라 **C-2**예요(§2.2) — 새 마켓 엔트리 자체가 C-5 *정신*에 반하지만, 더 직접적으로 C-2(약한 응집 thin 플러그인 금지)가 막거든요.

### 2.2 단일 반증 — 두 축 분리 + C-2가 결정타

단일의 이점을 정직하게 두 축으로 나눠요:

- **축 A — 런타임 호출 균일성**: #101 §5.1이 "어댑터 계약은 구조 독립적"으로 못박아 *논리 계약으로 이미 충족*돼요. 물리 통합 없이도 라우터(#122)는 균일 호출이 가능해요(4-튜플 입력·2-튜플 출력은 스킬이 어느 플러그인에 살든 불변). 발견성도 무관해요 — /goal 바인딩이 스킬을 *이름*으로 가리키거든요. **이 축에선 단일이 줄 게 없어요.**
- **축 B — 소스 co-location/유지보수 응집**: 기여자가 ② 자산을 한 디렉토리에서 발견·편집하고 매니페스트·버전·trigger 회귀를 한 곳에서 관리하는 이점. **이건 #101이 충족 못 하는 별개 축이고, 단일이 실제로 줘요.** ADR이 이걸 "이동 비용"으로만 계상하고 "도착 후 이점"으로 인정 안 하면 over-claim이에요 — 그래서 여기서 인정해요.

그런데도 단일이 지는 이유는 **축 B의 이득이 C-2에 걸려 실현 불가**하기 때문이에요. §0에서 봤듯 실 이동 대상은 thinking-tools의 doc-*/spec-first(± note)로 좁아요(graphify=user-level 스킬·gh=외부·handoff/save-session=③). 그런데 이동 비용을 줄이려고 단일을 *좁게* 뽑을수록(doc-*/spec-first만) 그게 정확히 **C-2가 만장일치로 금지한 "thin 2-스킬 doc-tools 플러그인(약한 응집)"**이 돼요 — 즉 **비용 최소화 ≡ C-2 위반**이 같은 방향이에요. 게다가 축 B로 얻는 응집은 *약한 응집*(html·yaml·md·note가 한 칸에 어색하게 모인)이고, 잃는 응집은 *강한 응집*(note↔vault 도메인, doc-*↔① 인지 코어)이라 순손실이에요. → **단일 패배 — load-bearing 근거는 C-2(약한 응집), C-5는 보조**.

### 2.3 OVM-fold 반증 — 전체 fold vs 부분 fold 분리

OVM-fold는 두 형태로 갈라야 정직해요 — 전체 fold와 doc-* 부분 fold. **둘 다 doc-* 행선지 결정의 일부라 #102가 판정해요**(G3 line 33 DoD가 "#102 ADR이 #103 행선지를 명시 지정"을 요구).

**먼저 사실 인정**: OVM은 *이미* ② 출력 leaf를 호스트해요 — note는 `boundary` line 25·#101 §2 #2에서 ②출력 leaf로 확정돼 있는데 OVM에 살거든요. 그러니 "OVM=vault 도메인 only, ②는 못 들어옴"이라는 범주 벽은 프로젝트 자체 설계로 이미 뚫려 있어요. md-authoring에 한정하면 `boundary` §4 file-over-app("지식은 plain Markdown에 상주")과 OVM note의 구조화 md 저작 core는 doc-concretize와 *겹치기*까지 해요. 그래서 "도메인 불일치"를 *전면* 단정하는 건 부정확해요(U-1 원문도 "불일치 *가능*"이지 확정이 아님).

- **(3a) 전체 fold** — graphify(html)·spec-first(YAML Seed)까지 vault 도메인에 흡수. 이건 명백히 도메인 경계 붕괴라 **#102가 기각**해요. 누구도 html/yaml을 vault에 넣자고 하지 않으니 이게 option 3의 실 패배 지점이에요.
- **(3b) 부분 md-fold** — doc-concretize/doc-polish만 OVM으로. 이건 option 3(전체 fold)이 *아니라* 분산의 sub-variant(자산이 신규 monolith가 아니라 기존 도메인 플러그인에 사는 건 동일)지만, doc-*에 대해선 **기각**해요. 비대칭이 fold가 아니라 잔류를 가리키거든요: note는 destination=vault(CON-1 gated)라 진짜 vault-resident지만, doc-*는 destination=repo_path(#101 §2 #6/#7, non-gated)라 OVM이 호스트하는 *vault-destined ②*에 안 맞아요. 게다가 doc-concretize는 ① 인지 코어 결합(C-2 "구조화 저작")이라 ④/vault로 빼면 코어가 단절돼요. → doc-* 행선지는 §2.5에서 **in-place reframe**으로 지정.

> **CON-1 논거 정정**: "repo-local 출력은 vault write가 아니라 CON-1 정신 불일치"는 약한 근거예요 — OVM은 *이미* vault write(note, CON-1 gated)와 non-vault 동작(audit)을 한 플러그인에서 운영하고, #101 §1.3이 "vault 아닌 목적지는 CON-1 비대상"을 정상 처리하거든요. 정확한 반박은 "destination 비대칭(vault/repo)이 한 플러그인에 공존하면 fold의 유일 장점인 *응집*이 실현 안 됨"이에요.

→ **OVM-fold 패배 — 전체 fold는 도메인 붕괴로, 부분 md-fold는 비대칭으로 기각. doc-* 행선지 = in-place reframe(§2.5)**.

### 2.4 결론

U-2 잠정 우세(분산)가 어드버서리얼 압력 하에서도 유지돼요. **Confidence: Strong** — #102가 결정하는 것은 두 층위예요: (1) **물리 구조** = 신규 monolith 아님 + 전체/부분 OVM-fold 아님 + thin doc-tools 아님(C-2) → 자산은 도메인 홈에 두고 "출력 레이어"는 #101 논리 계약, (2) **doc-concretize/doc-polish 행선지** = in-place reframe(thinking-tools 잔류, §2.5 — G3 DoD line 33 충족). 물리 실행(SKILL.md reframe·thought-chain 링크·매니페스트 동기화)만 #103/S2가 맡아요. 분산 = harness-neutral · 도메인 응집 · 신설 0 · 재배치 0이에요.

### 2.5 #103 concretize/polish 행선지 지정 (G3 DoD line 33)

G3 goal-doc(`docs/plans/goal-docs/G3-output-layer-structure.md` line 33)은 "#102 ADR이 #103의 concretize/polish 행선지를 **명시적으로 지정**(어느 플러그인/디렉토리에 안착)해야 #103 게이트가 풀림"을 #102 완료 조건으로 못박아요. 분산 결정의 직접 귀결로 행선지를 지정해요:

- **지정: in-place reframe** — doc-concretize·doc-polish는 **`thinking-tools/skills/`에 잔류**, 역할만 재정의해요(concretize = 구조화 저작/① 인지 코어 보존, doc-polish = md 린트/quality·lint 표면). 물리 이동·신규 플러그인·OVM-fold 전부 안 함.
- **근거** (G3 쟁점표 line 58 (a) 권고와 정합): 분산 = "논리적 계약"이라 물리 이동이 *불필요*해요 — #101 출력 어댑터 계약만 만족하면 위치는 thinking-tools여도 무방하거든요. 반대로 이동/fold는 thought-chain 링크·매니페스트·README 표면을 전부 건드려 회귀 위험↑·가치↓예요. §2.3 비대칭(note=vault-destined / doc-*=repo_path·non-gated, concretize=① 인지 코어 결합)도 잔류를 가리켜요.
- **스코프 경계**: #102는 *방향*(in-place 잔류)을 지정하고, 물리 실행(SKILL.md description reframe·thought-chain 링크 검증·매니페스트 동기화)은 **#103/S2**가 수행해요. #102가 #103의 기계적 작업을 대신하진 않되, G3 DoD가 요구한 *행선지 1곳 확정*은 충족해요.

---

## 3. #101 §5.1과의 정합 (불변성 명시)

#101 `output-adapter-contract.md` §5.1의 핵심을 인용해요(괄호 부연 및 §5.1 말미의 #102 결정 결과 문장은 자기참조라 생략):

> 이 문서 = **논리 계약**(어댑터 호출 규약·매핑·체이닝). ②를 단일 플러그인으로 묶을지 분산 유지할지의 **물리 구조는 #102(G3 wave)** 결정이에요. 어댑터 계약은 구조 독립적이라 #102 어느 결과에도 불변 — #101 Acceptance는 #102 없이 충족.

따라서 **분산 채택은 #101 Acceptance/계약에 영향 0**이에요. 균일 호출 규약(4-튜플 입력·2-튜플 출력·포맷×동작 8매핑·산출 체이닝)은 단일이든 분산이든 **불변**이에요. "출력 레이어"의 실체 = 물리 플러그인이 아니라 이 논리 계약이라는 게 #101과 #102가 공유하는 전제고, 이 ADR은 그 전제를 *물리 결정*으로 닫는 거예요.

---

## 4. 하류 게이트 표 (이 결정이 무엇을 해제/대기시키나)

| 하류 | 의존 | #102=분산 결정의 효과 | 상태 |
|------|------|----------------------|------|
| **#103 (doc-concretize/doc-polish 행선지, U-1)** | U-1 ← U-2 | 분산 확정 → 행선지 **지정: in-place reframe(thinking-tools 잔류, 역할 재정의)**(§2.5; G3 line 58 (a) 권고 정합). 신규 doc-tools 플러그인(C-2 thin 금지)·OVM-fold·물리 이동 모두 기각(회귀 위험↑·가치↓). 비대칭: concretize=구조화 저작(① 인지 코어 결합) · polish=md 린트라 같은 칸 금지. #103은 SKILL.md description reframe + thought-chain 링크/매니페스트 검증만 실행 | **unblocked — 행선지 1곳 확정(G3 DoD line 33 충족)** |
| **#124 (diverse-sampling Mode B → doc-concretize 하위호출 경로)** | #102 → #103 (2차 의존) | 분산 + #103 in-place reframe → diverse-sampling→doc-concretize가 **intra-plugin Skill 호출**(둘 다 thinking-tools)이라 #124 크로스플러그인 의존 우려 *소멸*(G3 쟁점표 line 60). 단 호출 경로 라인은 #103 행선지 확정값에 종속(머지 후 박제)이라 **#102 직접 게이트 아님 — #103 경유 2차 의존** | **대기 — #103 머지 후 경로 확정(placeholder 미잔존 검증)** |
| **#111-4 (spec-first 물리 분리)** | #102 | 분산/흡수 결정 → standalone 플러그인 신설 = 껍데기 → **폐기**(G2 쟁점 표 #111-4: "분산/흡수면 폐기"; (b)보류 → 폐기 확정). spec-first는 현 위치(`thinking-tools/skills/spec-first`) 유지, plugin.json/marketplace.json 등록·디렉토리 레이아웃·버전 동기화 불필요 | **폐기 확정 — 게이트 해소** |
| **#138 (mirror drift 가드 위치)** | #102(논리적 영향) · 형식 Refs #101/#133/#134 | 분산 → issue-authoring 소유권 분할 거울 표가 `output-adapter-contract.md` §5.2 · `execution-skill-inventory.md` §4 두 doc에 물리 분산 유지 → grep 기반 drift 가드가 적합(CLAUDE.md Validation 또는 #134 게이트 체인 흡수). 단일 통합이었다면 한 doc에 합쳐 가드가 불필요했을 수 — 분산이 가드 필요를 *확정* | **unblocked — 가드 = 분산 doc 간 grep** |
| **issue-authoring 빌드 위치** | #102 + #133(② 귀속 firm) | 분산 → ② 출력 leaf 귀속은 #133 firm이나 *물리적으로 어느 플러그인에 빌드*할지는 thin 신규 금지(C-2) 하에 기존 ② 도메인 플러그인 후보로 별도 후속 결정. #133=귀속 판정만, 빌드 위치=미정 | **대기 — 빌드 시 위치 후속(C-2 적용)** |

---

## 5. 헌법/정책 정합 (#99 단일 출처 참조만, 재정의 금지)

- CON-5(harness → leaf only, no reverse) · leaf vendor-neutral · harness-neutral by construction은 `claude-kit-boundary.md` §3/§5가 단일 출처예요. 이 ADR은 **참조만** 해요.
- 핵심: **분산이든 단일이든 leaf는 harness-neutral by construction을 유지**해요(leaf 레벨 vendor-neutrality는 커밋 `7a94a34`에서 이미 달성). 물리 구조 결정은 단방향 규칙·vendor-neutrality에 영향이 없어요 — 둘 다 boundary 단일 출처가 규정하고 #102는 그 규칙을 *소비만* 하거든요.
- 명시: 이 ADR은 **어떤 CON-*/POL-* 규칙도 재정의/추가하지 않아요**.

---

## 6. 코드 영향 — doc-only 명시

- 이 ADR은 **doc-only**예요. 분산 = 현상 유지(기존 자산 재배치 최소화)라 plugin.json/marketplace.json 변경 0, 스캐폴딩 실행 없음이에요.
- **대조 기록**: *만약* 단일 결정이었다면 스캐폴딩(신규 플러그인 plugin.json·marketplace.json 등록·디렉토리·자산 이동·버전 동기화)이 필요했을 거고, 그 실행은 **별도 후속으로 게이트**됐을 거예요(이 goal은 결정+ADR까지, #111-4 패턴과 동형). 분산이라 그 후속은 애초에 불필요해요.
- #102 Acceptance("결정 + 근거 ADR")는 doc-only로 충족돼요.

---

## 7. #102 Acceptance 추적

| #102 Acceptance | 충족 위치 |
|-----------------|----------|
| 결정(단일 vs 분산) | §2 verdict = 분산 |
| 근거 ADR | §1 비교표 + §2 근거 인용(U-2/C-2/C-5) + §3 #101 정합 |
| (G3 DoD line 33) #103 concretize/polish 행선지 명시 지정 | §2.5(in-place reframe) + §4 #103 행 |
| (하류) #103/#124/#111-4/#138/issue-authoring 게이트 | §4 게이트 표 |

---

**참조**: `docs/design/output-adapter-contract.md`(§5.1 #102 경계 · §5.2 거울 표) · `docs/design/claude-kit-boundary.md`(§3 CON-5 단방향 · §5 헌법/정책 · leaf vendor-neutral) · `docs/design/execution-skill-inventory.md`(§4 issue-authoring ② 귀속) · `docs/discussions/20260602_claude-kit-layer-redesign/UNRESOLVED.md`(U-1/U-2) · `SUMMARY.md`(C-2/C-5) · `docs/plans/goal-docs/G2-goal-doc-output-contract.md`(쟁점 표) · `docs/plans/goal-docs/G3-output-layer-structure.md`(line 33 #103 행선지 DoD · line 58 in-place 권고 · line 60 #124) · #99/#100/#101/#103/#111/#124/#133/#138.
