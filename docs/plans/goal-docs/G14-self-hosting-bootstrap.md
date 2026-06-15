---
goal_id: G14
title: ⑤ self-hosting 부트스트랩 — ⑤ 하네스 scaffold + retro 첫 입주
issues: [122, 123, 171]
wave: 5
depends_on: [G1, G2, G6]
recommended_model: opus
status: ready
work_type: feature-full
created: 2026-06-08
---

# G14 — ⑤ self-hosting 부트스트랩 (⑤ 하네스 scaffold + retro 첫 입주)

> **✅ 완료 (#122·#123 CLOSED · #217 정합).** ⑤ thin 진입(하네스 scaffold + retro 첫 입주)은 배포됐어요.
> #217이 ⑤ 하네스를 **dev-harness**(개발 거버넌스)와 **feedback-loop**(자기개선)로 분리하면서, 이 문서가
> 단일 "workflow-harness"로 부르던 플러그인은 그 둘이 됐어요 — 실제 산출물: retro → `feedback-loop/skills/retro/`,
> telemetry → `feedback-loop/scripts/`, 거버넌스 scaffold → `dev-harness/`. 본문 경로는 산출물이 실제 안착한
> 플러그인으로 갱신했고(scaffold-레벨 참조는 "⑤ 하네스"로 둠), frontmatter `status: ready`는 goal-doc-spec §1.1
> enum(gated/ready 2종)에 완료 표기 수단이 없어 유지하되 완료 상태의 단일 출처는 이 배너예요.

> 이 문서는 다음 세션에서 Claude Code `/goal`에 그대로 넣을 수 있는 자기완결 실행 계획이에요.
> 기존 G6(#122/#125)·G7(#123/#121)을 **2026-06-08 현재값으로 갱신·통합**한 실행 단위예요 —
> 그 사이 #125·#121이 닫혔고, #172(self-hosting sub-epic)가 "#122 전체보다 thin 진입"으로 방향을 재정의했어요.
> `epic:` frontmatter는 goal-doc-spec 미정의라 omit(spec-faithful, §1.3) — #172 self-hosting 소속은
> 아래 "## 참조"의 advisory 링크로 관리해요(G16·handoff-plan EPIC phase 설계와 일관, #186).

## 배경 / 목적

Epic #108 layer redesign의 **설계·계약 스파인이 전부 닫혔어요** — #100(goal-doc LINCHPIN)·#101(출력 어댑터 계약)·#102(분산)·#103(doc 이동)·#169(CI 종료조건) 모두 CLOSED. 즉 남은 건 ⑤ 실행 트랙의 *구현*뿐이에요.

그런데 #172가 짚은 **우선순위 역전**이 정확히 지금 상태예요: LINCHPIN이 닫힌 뒤에도 ⑤ 트랙은 미착수고 leaf 폴리싱(thinking-tools·OVM audit)만 활발했어요. 게다가 self-hosting gap — "OMC를 대체할 ⑤ 경량 하네스를, 그 하네스가 자동화할 워크플로우를 손으로 돌리며 만드는 중" — 이 가장 비싼 수작업 지점에 그대로 남아 있어요.

이 goal은 그 역전을 해소하는 **⑤ thin 진입**이에요. #122 전체(OMC strangler 점진 대체)를 다 짓지 않고, **최소 플러그인 셸 + retro 첫 입주 스킬**만 올려서 측정→개선 루프를 닫아요. telemetry에 이미 5개 PR을 투자해뒀는데 소비처가 없어서 루프가 안 닫혀 있거든요(retro가 그 첫 소비처).

## 포함 이슈 (현재값)

- **#122** (⑤ 하네스 플러그인) — **thin scaffold만**. 전체 strangler 엔진 아님. #125(3-tier 규칙)는 이미 닫혀(`rule-tiers.md`) 이 goal에서 빠짐.
- **#123** (retro thin) — telemetry 첫 소비처. **이 goal의 메인**. #121(telemetry meta)도 닫혀 retro의 meta 연동만 남음.
- **#171** (handoff 실질화) — 다음 슬라이스. 여력 있으면 착수, 아니면 G15로 분리.

## 완료 조건 (Definition of Done)

### 슬라이스 1 — ⑤ 하네스 thin scaffold (#122)
- [ ] `dev-harness/`·`feedback-loop/` 각 `.claude-plugin/plugin.json` (name, version, keywords) — #217로 2개 플러그인 분리
- [ ] `dev-harness/`·`feedback-loop/` skills 디렉토리 + 각 `README.md`
- [ ] `.claude-plugin/marketplace.json`에 항목 추가 (source 경로) — version-sync 규칙 준수
- [ ] 단방향 의존 명시(README): **dev-harness·feedback-loop(harness) → leaf(vault-bridge·obsidian-vault-manager)** (CON-5, harness→leaf). 역방향 금지.
- [ ] `scripts/check-version-sync.py` + `check-ci-coverage.py --strict` green

### 슬라이스 2 — retro 스킬 (#123, 메인)
- [ ] `feedback-loop/skills/retro/SKILL.md` — 4단계 파이프라인 **COLLECT → PROMOTE → OUTPUT → BUDGET**
- [ ] **E8 임계승격**: audit E8 `promotion_candidate` findings 입력 → refs_in·access_count 임계 재확인 → **user-confirmed 게이트** → `status: evergreen` 패치(Edit, frontmatter-only). silent auto-fix 금지.
- [ ] **3갈래 출력** (각 opt-in, 기본 액션만 활성): 액션→git issue / 기억→vault capture(user-initiated slash) / 규칙→`.claude/*.local.md`
- [ ] **dedup**: 동일 세션 (파일·error_type) 쌍 중복 제거 + 이전 retro 처리분 telemetry 확인 후 스킵
- [ ] **회고예산**: 세션당 처리 상한(configurable), 초과 시 P0→P1→P2 절사 + 잔여 보고
- [ ] telemetry `meta: {}`에 `{retro_items_processed, items_promoted, items_deduped, budget_used}` 추가
- [ ] vault 쓰기는 user-initiated slash 경유 (vault-bridge Write Role Contract 준수)

### 슬라이스 3 — handoff 실질화 (#171, 여력 시)

> **2026-06-08 분리됨 → [`G15-handoff-realization.md`](G15-handoff-realization.md).** 슬라이스 1·2(scaffold + retro)로 ⑤ thin 진입 코어가 닫혔고, #171은 #140 물리위치 게이트(⑤ harness 권고) + #104 정합이 선행돼야 해서 급조 시 CON-5 리스크가 커요. goal-doc이 허용한 G15 분리로 처리했어요(아래 항목은 G15 DoD로 이관).

- [ ] handoff가 열린 이슈를 청킹/에픽 후보로 제안 (continuation prompt 외 신규 로직)
- [ ] 청킹 결과 → goal-doc(#100) 슬라이스 바인딩 형식 출력 (다음 세션 `/goal` 연결)
- [ ] 에픽 링크 user-confirmed, vault 쓰기 없음 또는 user-initiated만 (CON-1)

---

## 쟁점과 트레이드오프

| 쟁점 | 옵션 | 결정 | 근거 |
|------|------|------|------|
| #122 범위 | OMC 전체 strangler vs thin scaffold | **thin scaffold만** | telemetry 루프 닫는 최소 진입; #172가 "전체보다 thin 진입"으로 방향 재정의 |
| #123 위치 | ⑤ 하네스 신규 스킬 vs ② leaf 이식 | **⑤ feedback-loop 신규** | CON-5: retro가 telemetry(당시 ④ leaf, #217로 feedback-loop 흡수)를 소비하니 ⑤가 자연스러운 home |
| #171 처리 | G14 슬라이스 3 포함 vs G15 분리 | **G15 분리** | #140 물리위치 게이트 미해결 + #104 정합 선행 필요 → 급조 시 CON-5 경계 훼손 |

---

## 슬라이스 순서

1. **S1: ⑤ 하네스 thin scaffold** → 바인딩: executor|native(#133) | 대상 파일: dev-harness/·feedback-loop/ (.claude-plugin/plugin.json, skills/, README.md) | 산출: 플러그인 셸 + 단방향 의존 명시 README | 검증: check-version-sync.py + check-ci-coverage.py --strict green
2. **S2: retro 스킬 구현** → 바인딩: spec-first → executor|native(#133) | 대상 파일: feedback-loop/skills/retro/SKILL.md | 산출: COLLECT→PROMOTE→OUTPUT→BUDGET 4단계 파이프라인 + telemetry 메타 | 검증: user-confirmed 게이트 + vault Write Role Contract 준수 확인
3. **critique** → 바인딩: adversarial-review|code-reviewer(#133) | 대상 파일: feedback-loop/ | 산출: 비판적 검토 결과 | 검증: PASS (자기승인 금지 CON-3)

---

## E2E 자가검증

```bash
# 1. 플러그인 셸 존재 확인
ls dev-harness/.claude-plugin/plugin.json feedback-loop/.claude-plugin/plugin.json && echo "ok plugin.json (dev-harness·feedback-loop)"
ls -d dev-harness/skills/ feedback-loop/skills/ && echo "ok skills 디렉토리"
ls dev-harness/README.md feedback-loop/README.md && echo "ok README.md"

# 2. retro 스킬 존재 확인
ls feedback-loop/skills/retro/SKILL.md && echo "ok retro SKILL.md"

# 3. 버전 동기화 + CI 커버리지 확인
python3 scripts/check-version-sync.py && echo "ok version-sync clean"
python3 scripts/check-ci-coverage.py --strict && echo "ok ci-coverage clean"

# 4. 단방향 의존(CON-5) 확인 — leaf가 harness(dev-harness·feedback-loop)를 역방향으로 import하지 않는지
grep -rl "dev[._-]harness\|feedback[._-]loop" thinking-tools/ obsidian-vault-manager/ vault-bridge/ 2>/dev/null \
  && echo "FAIL: 역방향 의존 발견" || echo "ok CON-5 단방향 clean"
```

**통과 기준**: 모든 확인 통과 + version-sync + ci-coverage green + CON-5 역방향 의존 없음

---

## 제약 / 안전판 (재정의 금지 — 참조만)
- **CON-5 단방향 의존**: dev-harness·feedback-loop(harness) → leaf(②③④). 역방향·순환 금지. 물리 위치는 #140 게이트("이슈 읽기→청킹"=②인접 / "슬라이스 루프"=⑤)로 결정.
- **Write Role Contract**: vault 쓰기는 메인컨텍스트 user-initiated slash만. 서브에이전트 vault write 금지.
- **확인 게이트**(#125 rule-tiers §2): 승격·에픽 등록·규칙 추가는 자동 후보까지, 확정은 사용자. silent 금지.
- 헌법/정책 목록 단일출처: `docs/design/claude-kit-boundary.md` §Design Principles 참조.

## 참조
- Epic: #172(self-hosting sub-epic, 권장순서 #123→#171→#134), #108(layer redesign)
- 기존 goal-doc: `G6-workflow-harness-rules.md`, `G7-retro-telemetry.md` (이 G14가 현재값으로 대체)
- 결정 맥락: `docs/discussions/20260602_claude-kit-layer-redesign/`, `docs/adversarial-review/2026-06-03-harness-ownership.md`
- 후속(이 goal 후): #134 게이트체인(오케스트레이션), #104 vault-bridge slim(#171 정합 위치 — #171 전 권장)

## 권장 진행
1. **워밍업(저비용)**: C2 quick-win — #180 잔여 doc/CI nit(**N2** exit 순서 1→2→3·**N3** rule-tiers tier 번호 주석+헌법 끄기불가·**N4** graphify 표기·**N5** adversarial STATE 한 줄) + #177 정리(N3~N6 코드 클린업). 컨텍스트 적재 겸.
   > *Reconcile note (2026-06-08): 이 초안의 이전 표기 "#180(N4/N6/N8 … CONTRIBUTING 정정)"은 #180 실제 nit 번호(N1~N5)와 어긋난 mis-reference였어요. graphify=N4만 정확했고, "헌법 끄기불가"는 N3(rule-tiers) 자리의 실질 개선, "CONTRIBUTING 정정"은 대응 nit이 없는 confabulation(파일명·이슈번호 참조는 모두 정확)이라 실제값으로 정정했어요.*
2. 슬라이스 1(scaffold) → 슬라이스 2(retro, 메인) 직렬. 슬라이스 3(handoff)는 여력 시.
3. 각 슬라이스 후 verifier/critic 패스 (자기승인 금지).
