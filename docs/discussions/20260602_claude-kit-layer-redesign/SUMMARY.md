# claude-kit 레이어 재설계 — 전문가 패널 SUMMARY (2026-06-02)

## 배경

사용자의 2026-06 개발 워크플로우 비전(에이전틱 루프)에 맞춰 claude-kit을 5개 레이어로 재구성하는 안을 검토. 패널: Plugin Architecture(PA) · Agentic Workflow(AW) · Cognitive-Tools/DX(CT) · Maintainability/Complexity-Budget(MB) + Moderator. 모드: brief(transcript 생략).

### 레이어 모델

| 레이어 | 동작 | 현재 매핑 |
|---|---|---|
| ① 인지 | reasoning 조작 | diverse-sampling · unknown-discovery · expert-panel(=ideation) · adversarial-review(=critique) |
| ② 결정화·출력 | 포맷·목적별 산출물 | spec-first(goal-doc) · doc-concretize · doc-polish · graphify(html) · note · issue |
| ③ 딜리버리 | vault 운반 | vault-bridge |
| ④ 지식베이스 | vault 상주 관리 | obsidian-vault-manager |
| ⑤ 실행(doing) | debug · quality · retro · issue 클로징 | **대부분 OMC 영역** |

## 합의 사항 (Consensus)

### C-1. claude-kit vs OMC 경계 = **옵션 A** (만장일치)
claude-kit은 ①②③④만 소유하고 ⑤(doing/오케스트레이션)는 OMC가 담당. 의존 방향은 "claude-kit 스킬 = OMC가 호출하는 leaf capability". (B)(루프 전체 흡수)는 OMC 중복 + 버전 동기화·유지보수 표면 폭발로 기각.
- **액션**: claude-kit↔OMC 통합 계약 명세. goal-doc이 둘을 잇는 glue.

### C-2. doc-concretize/doc-polish = **②로 분리 합의, 행선지 보류**
②(의도적 출력 레이어)가 생기므로 둘은 thinking-tools에서 분리. (지난 critic 입장 "thinking-tools에 두고 리프레이밍"을 뒤집은 근거 = 출력 레이어의 존재.) 단 **비대칭 확정**: doc-concretize = 구조화 저작(인지 코어 보존 필요), doc-polish = 순수 마크다운 린트(Track A 이후). 같은 칸 아님.
- **제약**: thin 2-스킬 "doc-tools" 플러그인 신설 금지(약한 응집). 분산 또는 fold 선호.
- 행선지는 UNRESOLVED.

### C-3. thought-chain = **dissolve → goal-doc 레시피** (CT 1인 조건부 동의)
고정 4단계 thought-chain은 비전의 `/goal 자율진행`(슬라이스별 스킬 바인딩)의 경직된 부분집합. goal-doc이 supersede. CT는 "풀 분석 한 방" 편의 손실을 우려하나 goal-doc 레시피가 동등 편의 입증 시 동의.
- **시퀀싱**: ② 출력 레이어 + goal 플로우 존재 후로 연기.
- **제약**: breaking change → 마이그레이션 노트 + major 범프.

### C-4. vault-bridge = **haiku READ + gated WRITE primitive + hooks** (만장일치)
"haiku 순수 딜리버리" 초기 의도는 **READ에만 성립**. 핵심 발견: vault-bridge 자기 pre-write-guard(Write Role Contract)가 서브에이전트 vault write를 차단 → write는 구조적으로 메인컨텍스트 전용(user-initiated). 따라서 write는 haiku 위임 불가. 재설계 = 이 비대칭을 명시 수용하고 저작 책임을 ②로 evict.
- **UX 제약**: /save-session·/handoff 등 슬래시 명령 *이름* 보존(compose-via-② → deliver).
- **시퀀싱**: ②가 저작 흡수 후에야 ③ 슬림 가능 (②먼저 → ③슬림).

### C-5. 출력 포맷 세분화 = **신설 최소화 + 균일 어댑터** (만장일치)
기존 매핑: html=graphify, note=OVM note, goal-doc=spec-first, handoff=/handoff, issue=gh CLI. ②는 대부분 기존 *조립*. net-new ≤1-2(issue 통합 정도). 가치는 신규 스킬이 아니라 /goal 슬라이스-바인딩이 균일 호출하는 **출력 어댑터 계약** + intent/포맷 라우팅(선택 과부하 방지).

## 권고 실행 순서 (의존성 반영)

1. **경계 A 선언** [결정, 코드 없음] — 모든 후속의 전제.
2. **goal-doc 포맷 + 슬라이스-스킬 바인딩 스펙 설계** — glue이자 thought-chain 후계자. (별도 설계 필요)
3. **출력 어댑터 계약 + 기존 출력 스킬 매핑표** — net-new gap(≤2) 식별.
4. **② 출력 레이어 조립** — vault-bridge에서 evict될 저작 책임 흡수 포함.
5. **doc-concretize/doc-polish를 ②로 이동** (행선지 결정 후).
6. **vault-bridge 슬림** (haiku read + gated write + hooks). 4 의존.
7. **thought-chain dissolve** (goal-doc 레시피로). 2+4 의존. 마이그레이션 노트 + major 범프.

## 핵심 액션 아이템

| ID | 액션 | 의존 | 비고 |
|---|---|---|---|
| A1 | claude-kit↔OMC 통합 계약 명세 | — | 경계 A 구체화 |
| A2 | goal-doc 포맷·슬라이스 바인딩 스펙 | A1 | thought-chain 후계 |
| A3 | 출력 어댑터 계약 + 매핑표 | A1 | net-new gap 식별 |
| A4 | ② 출력 레이어 조립 (+저작 흡수) | A3 | thin 플러그인 금지 |
| A5 | doc-concretize/doc-polish 이동 | A4 + 행선지 결정 | 비대칭 보존 |
| A6 | vault-bridge 슬림 | A4 | write=메인 전용 명시 |
| A7 | thought-chain dissolve | A2,A4 | major 범프 |

## 즉시 적용 가능 (no-regret)

- 이번 세션 C1(expert-panel STATE 블록, 커밋 `79781d1`)은 ① 인지 코어라 모든 시나리오에서 생존 — 재설계와 독립.
- spec-first 분리(진행 중)는 C-2/②와 정합 — goal-doc 출력 스킬로 ②에 안착.
