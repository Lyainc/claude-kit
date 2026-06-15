---
goal_id: G16
title: ⑤ 하네스 본체 — 4종 슬라이스 라우터 + D5 헌법 invariant enforcement (#122 잔여)
issues: [183]
wave: 5
depends_on: [G14]
recommended_model: opus
status: ready
work_type: feature-full
created: 2026-06-08
---

# G16 — ⑤ 하네스 본체 (4종 슬라이스 라우터 + D5 invariant, #183)

> **✅ 완료 (#183 CLOSED · #217 정합).** 4종 슬라이스 라우터 + D5 헌법 invariant enforcement는 배포됐어요 —
> 산출물은 `dev-harness/scripts/slice_router.py`·`invariant_guard.py` + 테스트 `dev-harness/scripts/test/test-router.py`·`test-invariant.py`.
> #217이 ⑤ 하네스를 dev-harness(개발 거버넌스)/feedback-loop(자기개선)로 분리하면서, 이 문서가 "workflow-harness"로
> 부르던 플러그인은 라우터·invariant가 거버넌스 산출물이라 **dev-harness**가 됐고, 본문 경로를 현재값으로 갱신했어요.
> frontmatter `status: ready`는 goal-doc-spec §1.1 enum(gated/ready 2종)에 완료 표기 수단이 없어 유지하되,
> 완료 상태의 단일 출처는 이 배너예요(CON-4 enum 진화는 schema_version 경유 — 미적용).

> **handoff-plan(#171) dogfooding 산출.** G15에서 `dev-harness/skills/handoff-plan`이
> 열린 backlog 18건을 의존·도메인으로 청킹한 결과, #183(=#122 잔여)이 "한 세션에 다 하면
> 비싼 ⑤ 하네스 본체"로 식별됐고, 그걸 **비용 커서로 4슬라이스 분할**한 goal-doc이에요.
> `epic:` frontmatter는 goal-doc-spec 미정의라 omit(spec-faithful) — #172 self-hosting 정합은
> gh advisory 링크로 처리했어요(handoff-plan EPIC phase 설계와 일관).

## 배경 / 목적

PR #181이 #122를 **v0.1.0 thin scaffold**(plugin.json + README + retro 1개)로 닫으면서
(`Closes #122`), 원래 acceptance 6항목 중 **핵심 3종 + 통합테스트가 미구현으로 남았어요**.
#183이 이걸 silent scope drop 방지 원칙(#178/#180/#182 일관)대로 분리 트래킹해요.

이 잔여는 #108 strangler 단계의 **P2(하네스 골격 #122 S1–S2, 4종 라우터) + P3(invariant+규칙
#122 S4–S5)** 에 해당해요. PR #181이 P5(retro)를 먼저 닫은 셈이라 P2–P3가 역순으로 남았고,
이 goal이 그걸 닫아요. **OMC가 현재 ⑤를 정상 담당 중**이라 strangler 점진 흡수고, native가
invariant를 충분히 강제하면 자체 enforcement는 축소 가능(P6 가역 종착점) — 그래서 자체 빌드는
**native가 강제 못 하는 gap에만** 한정해요.

## 완료 조건 (Definition of Done)

#183 acceptance와 1:1 (각 슬라이스가 한 항목):

- [ ] **4종 슬라이스 라우터** — `work_type` 1차 키로 슬라이스 시퀀스 결정 + 각 슬라이스를
      바인딩된 스킬에 위임. 기능개발full(spec→impl→critique) / 버그수정경량(goal-doc 부재→debug
      직행) / 의사결정(실행없음) / 문서작성(출력전용). (goal-doc-spec §3.6 + §4.4)
- [ ] **D5 헌법 invariant enforcement** — native(`/goal`·Workflow)가 강제 못 하는 invariant만
      thin enforce: new-file-only vault write · 격리 critique(self-approval 금지) · goal-doc
      스키마(INV-4) · 단방향 의존(CON-5). (boundary §5 CON-1/CON-3/CON-4/CON-5)
- [ ] **native 위임 경계 구현** — goal-doc parse/exec·슬라이스 루프는 가능한 한 native에 위임,
      자체 빌드는 native 미제공분에 한정. 경계를 README에 1줄 명문화.
- [ ] **통합 테스트** — 4종 라우팅 + native 위임 fallback. CLAUDE.md Validation 등록 + CI(`validate.yml`) wired (ci-coverage --strict green).

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| 자체 enforce 범위 | 전부 자체 / native 미강제 gap만 | **gap만 thin** | OMC 정상 담당 중, native supersession 시 매몰비용. 자체 소유 = adversarial surviving strength(invariant enforcement)에 한정 |
| 슬라이스 분할 커서 | 라우터+invariant 합침 / 4개로 쪼갬 | **4개 분리** | 라우터+invariant를 한 세션에 합치면 비용 초과 위험. 비용 커서 = 한 세션 처리 가능 단위 |
| #134 게이트 체인 정합 | 선행 / 병렬 / 후행 | **부분 병렬** | invariant enforcement(S2) ↔ #134 4지점 게이트가 정합. #134는 design doc이라 S2 구현 전 설계 착수 가능 |
| `executor|native` 귀속 | 지금 확정 / #133 위임 | **#133 정합** | 슬라이스 스킬 귀속은 #133(CLOSED) 인벤토리 — native 위임 우선 판정. 표기는 `candidate-or`(goal-doc-spec §3.2) |

## 슬라이스 순서

1. **4종 슬라이스 라우터** → 바인딩: spec-first → executor|native(#133) → adversarial-review|code-reviewer(#133) | 대상 파일: `dev-harness/` (라우터 로직 + 진입점) | 산출: `work_type`→슬라이스 시퀀스 결정·위임(§3.6 기본 바인딩 + §4.4 bug-light 부재 라우팅) | 검증: 4종(feature-full/decision-only/doc-only/bug-light) 라우팅 단위테스트
2. **D5 헌법 invariant enforcement** → 바인딩: spec-first → executor|native(#133) → adversarial-review|code-reviewer(#133) | 대상 파일: `dev-harness/` (enforce 레이어) | 산출: native 미강제 invariant(new-file-only·격리critique·INV-4·CON-5) thin enforce | 검증: invariant 위반 케이스 차단 테스트(각 CON별 negative case)
3. **native 위임 경계 구현** → 바인딩: 직접(메인 컨텍스트, 설계 결정) → executor|native(#133) | 대상 파일: `dev-harness/` + `README.md` | 산출: goal-doc parse/exec·슬라이스 루프 native 위임 경계 + 자체 빌드 한정 범위 명문화 | 검증: native fallback 동작(native 가능분은 위임, 미제공분만 자체)
4. **통합 테스트** → 바인딩: executor|native(#133) → verifier | 대상 파일: `dev-harness/scripts/test/` | 산출: 4종 라우팅 + native fallback 통합테스트 + CLAUDE.md Validation·`validate.yml` 등록 | 검증: ci-coverage --strict green(신규 테스트 wired) + 통합테스트 통과

> **슬라이스 의존**: S1 → S2(라우터 위에 invariant enforce가 올라감). S3는 S1과 병렬 가능
> (위임 경계는 라우터 설계와 동시 진행). S4는 S1–S3 후(통합). `→`는 산출→입력 체이닝(§3.5).

## 제약 / 안전판 (재정의 금지 — 참조만)

- 헌법/정책 단일출처: `docs/design/claude-kit-boundary.md` §5 (CON-1·CON-3·CON-4·CON-5). 이 goal의 S2가 enforce하는 대상이 정확히 이 헌법 목록이에요(재정의 아님, enforce).
- goal-doc 스키마(INV-4): `docs/design/goal-doc-spec.md` §4.3 — S1 라우터가 이 스키마로 파싱·라우팅.
- native 위임 우선: `docs/design/omc-to-native-substrate.md` §4.1(Gap-ROUTE)·§4.2(INV-4)·§5(strangler).
- 격리 critique(CON-3): S1/S2 구현 후 자기승인 금지 — 별도 컨텍스트 reviewer/verifier.

## E2E 자가검증

```bash
# 1) 라우터: work_type별 슬라이스 시퀀스 결정 (4종)
#    - feature-full → spec→impl→critique (각 별도 스킬)
#    - decision-only → 실행 없음
#    - doc-only → 출력 전용
#    - (bug-light) → goal-doc 부재 시 debug 직행
python3 dev-harness/scripts/test/test-router.py   # 신설 예정 (S4)

# 2) invariant enforce: 위반 케이스 차단
python3 dev-harness/scripts/test/test-invariant.py # 신설 예정 (S4)

# 3) ci-coverage: 신규 테스트가 CI에 wired (silent local-only 금지)
python3 scripts/check-ci-coverage.py --strict
# Expected: OK: every registered test is wired into CI.

# 4) version-sync: 매니페스트 정합 (스킬/버전 추가 시)
python3 scripts/check-version-sync.py
# Expected: OK: version-sync clean
```

> 통과 기준은 DoD 4항목과 1:1 — 라우터 4종(1)·invariant 차단(2)·native 경계 명문화(3)·통합테스트
> CI 등록(4). S4에서 위 `test-router.py`/`test-invariant.py`를 실제 신설하고 Validation에 등록해요.

## 참조

- 이슈: #183(#122 잔여), #122(thin scaffold, CLOSED via PR #181), #108(layer redesign), #134(게이트 체인 — S2 invariant와 정합), #105(thought-chain dissolve — 라우터가 실행)
- 선행: G14(`G14-self-hosting-bootstrap.md` — scaffold + retro), #100(goal-doc-spec, CLOSED), #133(⑤ 스킬 인벤토리, CLOSED)
- 정합: #172(⑤ self-hosting sub-epic — 이 goal이 #134와 함께 완료조건의 마지막 미완분을 닫음)
- 산출 경위: G15 handoff-plan(#171) dogfooding — `docs/plans/goal-docs/G15-handoff-realization.md`
