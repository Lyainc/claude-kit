# claude-kit 레이어 재설계 — UNRESOLVED (2026-06-02)

합의에 도달하지 못했거나, 후속 설계가 필요해 보류된 항목.

> **이슈 매핑 (2026-06-03)**: 전 항목이 Epic **#108** 산하 이슈로 트래킹됨.
> U-1 → #102→#103 · U-2 → **#102** · U-3 → **#100**(LINCHPIN) · U-4 → #105(CT 조건) · U-5 → #99(경계 선언)+#100(parse/exec 인터페이스).
> spec-first 미해결은 **#111**. 독립 항목: #106(expert-panel D4a)·#107(C2 saturation). backlog: #113·#114·#115.

## U-1. doc-concretize/doc-polish 행선지 (TOPIC 2 보류)

분리는 합의됐으나 *어디로* 갈지 미결.

| 후보 | 장점 | 단점 |
|---|---|---|
| 신규 "doc-tools" 플러그인 | 출력 저작 응집 | 2-스킬 thin 플러그인, 마켓 엔트리 증가(MB 반대) |
| 분산 (concretize→출력 저작, polish→quality/lint 표면) | 레이어 정합 | 두 스킬이 갈라져 페어링 깨짐 |
| OVM에 fold | 기존 플러그인 재사용 | OVM은 vault 상주 도메인 — md 일반 저작과 도메인 불일치 가능 |

- **비대칭 재확인**: concretize=구조화 저작(인지 코어), polish=린트. 한 칸에 묶을 근거 약함.
- **판단 보류 사유**: ② 출력 레이어가 "단일 플러그인 vs 분산"으로 먼저 결정돼야 행선지가 따라옴 (U-2 의존).

> **RESOLVED via #102 (2026-06-04)**: (U-2 분산 결정의 하류 — 아래 **U-2 RESOLVED** 먼저 참조) 행선지 = **in-place reframe**(doc-concretize/doc-polish는 thinking-tools 잔류, 역할만 재정의). 분산=논리 계약이라 물리 이동 불필요 — `docs/design/output-layer-structure-adr.md` §2.5. 방향은 #102가 지정, 물리 실행은 #103.

## U-2. ② 출력 레이어 = 단일 플러그인 vs 분산 (TOPIC 2·5 파생)

html/md/issue/note/goal-doc은 이질적이라 응집도가 의문(PA). graphify(html)·OVM(note)·spec-first(goal-doc)는 *이미 각자 플러그인/스킬*. ②를 새 단일 플러그인으로 묶으면 기존과 중복·이동 비용. 분산 유지하면 "출력 레이어"는 물리적 플러그인이 아니라 *논리적 계약*(출력 어댑터 인터페이스)일 뿐.
- **잠정 우세**: 논리적 계약(분산) — 기존 자산 재배치 최소화. 단 미확정.

> **RESOLVED (2026-06-04, #102)**: **분산(논리 계약)** 채택 확정 — `docs/design/output-layer-structure-adr.md`. 단일·전체/부분 OVM-fold 기각, load-bearing 근거 = C-2(thin 약한 응집 금지). "출력 레이어"의 실체 = 물리 플러그인이 아니라 #101 논리 어댑터 계약.

## U-3. goal-doc 포맷 및 슬라이스-스킬 바인딩 스펙 (TOPIC 3 핵심 glue)

thought-chain dissolve의 전제이자 OMC↔claude-kit glue. 미설계 영역:
- goal-doc 스키마(완료 조건·쟁점/트레이드오프·슬라이스 순서·E2E 자가검증법 — 이미지 step 3·4 기준).
- 슬라이스별 스킬 바인딩 표기법(기본 spec-impl-critique, 디버깅 debug 등).
- OMC `/goal` 자율진행과의 인터페이스(누가 goal-doc을 파싱·실행하나 — OMC인가 claude-kit인가).
- **이게 별도 설계 트랙으로 분리돼야 함** (재설계의 가장 큰 미지수).

## U-4. thought-chain 편의 손실 보전 (TOPIC 3, CT dissent)

CT 1인 조건부 동의의 미해결 조건: goal-doc 레시피가 "풀 분석 한 방"(discover→debate→concretize→polish) 편의를 *동등하게* 제공함을 입증해야 dissolve 확정. 미입증 시 thought-chain을 얇은 goal-doc 템플릿 별칭으로 잔존시키는 절충 가능성.

## U-5. OMC↔claude-kit 통합 계약 구체 (TOPIC 1, A1 파생)

경계 A는 합의됐으나 계약의 *형태* 미정:
- claude-kit 스킬을 OMC가 호출하는 메커니즘(슬래시 invoke / agent 위임 / skill 트리거).
- 버전·인터페이스 안정성 계약(OMC 업데이트가 claude-kit 스킬 호출 규약을 깨지 않도록).
- ⑤ 실행 스킬(debug·quality·retro)이 OMC에 *이미* 있는지 vs 신설 필요한지 인벤토리.

## 미해결 우선순위

1. **U-3 (goal-doc 스펙)** — 최우선. thought-chain·② 레이어·OMC glue 전부 여기 의존.
2. **U-2 (② 단일 vs 분산)** — U-1 행선지의 전제.
3. **U-5 (통합 계약)** — 경계 A 실효화.
4. U-1, U-4 — 위 결정 후 자동 수렴 가능.
