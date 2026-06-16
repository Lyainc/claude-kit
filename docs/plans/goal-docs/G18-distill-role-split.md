---
goal_id: G18
title: 발견 갈래 — distill 역할 분리 (판단/제안 ↔ 매립 저작 분리, #251 선행 1순위)
issues: [252]
wave: 1
depends_on: []
recommended_model: opus
status: gated
work_type: feature-full
created: 2026-06-16
---

# G18 — distill 역할 분리 (발견/제안 ↔ 매립 저작)

> **⚠️ 부분 충족 goal — 에픽 #251의 "발견" 갈래만 닫아요.** #251(재귀개선 루프 정밀화)은
> 발견(distill 분리)→매립(add-policy 범용 엔진)→측정(telemetry 폐루프) 세 갈래로, 이 goal-doc은
> 그중 **선행 1순위인 발견 갈래**만 다뤄요. 이 goal이 닫는 작업 이슈는 발견 갈래 전용 **#252**이고,
> 에픽 #251은 매립(G19 예정)·측정(G20 예정)이 다 끝나야 close돼요 — G18 완료 ≠ #251 close
> (#251은 본문 "## 참조"의 advisory 링크로 관리, goal-doc-spec §1.3 epic-neutral 정합).

> **선행 계약이라 `status: gated`.** S1(발견↔매립 인터페이스 계약)이 매립 갈래(G19)의 입력
> 인터페이스를 확정하는 linchpin이라, goal-doc-spec §1.1("linchpin/고위험은 gated 시작")대로
> consensus 게이트(architect+critic) 통과 후 `ready` 전환을 권장해요. distill SKILL.md 리팩터
> 자체(S2)는 저위험이지만, 경계 명세(S1)가 후속 갈래를 묶는 계약이라 게이트를 권장해요.

## 배경 / 목적

#202로 distill이 배포된 직후, distill ↔ add-policy(local-harness) ↔ feedback-loop 관계를
재검토하면서 **distill이 판단과 저작을 둘 다 한다**는 중복이 드러났어요. 현재 distill 파이프라인
(`feedback-loop/skills/distill/SKILL.md`)은 5단계예요:

- **Phase 1 SCAN** — 재사용 기법 후보 식별 + anti-capture 필터 → **발견(무엇을)**
- **Phase 2 PRIORITIZE** — patch>extend>reference>new 액션 선택 → **매립 판단(어디에)**
- **Phase 3 GATE** — AskUserQuestion 확인 → 발견/제안의 유저 게이트
- **Phase 4 WRITE** — 실제 Edit/Write로 스킬 저작 → **매립(어떻게)**
- **Phase 5 SELF-CHECK** — 작성 검증 → 매립 부속

#251의 한 줄 결론대로 "어디에 어떻게 박는가"는 add-policy 범용 매립 엔진의 일이에요. 그래서
distill은 **발견/제안(자연어)만** 남기고, 매립 책임(Phase 2의 "어디에" 판단 + Phase 4/5 저작)을
분리해요. 이 분리의 산출 = **distill 출력 = 매립 엔진이 소비할 자연어 제안 객체**이고, 이게
#251이 말한 "매립 엔진 입력 인터페이스 확정 → 코어 모양이 잡힘"의 선행 조건이에요.

**왜 지금 이것부터인가** (세 근거):
- **블로커** — 발견 갈래는 매립(G19)·측정(G20)의 선행. distill 출력 계약이 잡혀야 매립 엔진 입력
  인터페이스가 확정돼요(#251 "선행 = distill 역할 분리").
- **수요 무관 가치** — #251이 명시: "수요와 무관하게 지금도 깨끗해지는 리팩터". 매립 엔진을 짓든
  안 짓든, 발견/매립 책임 경계를 명시하는 것만으로 distill SKILL.md가 깨끗해져요.
- **dogfooding** — work_type=feature-full이라 slice-router가 feature-full로 라우팅 →
  feature-full.js(#201) impl/critique 분리 스테이지로 실행되며 dev-harness 워크플로를 self-test해요.

## 완료 조건 (Definition of Done)

#251 발견 갈래 task와 1:1 (각 슬라이스가 한 항목):

- [ ] **발견↔매립 책임 경계 명세** — distill의 출력 계약을 "자연어 제안 객체"로 정의(매립 엔진
      입력 인터페이스). Phase 2의 "어디에 박을지" 판단과 Phase 4/5 저작이 **매립 책임**임을 명시·
      문서화. distill에 남는 것 = SCAN(발견) + 제안 + GATE(유저 확인)임을 경계로 고정.
- [ ] **distill SKILL.md 재구조화** — 발견/제안 레이어로 재저작. 매립 책임은 분리 마킹 + 매립 엔진
      부재 동안의 transition 전략(쟁점 T1) 명시. distill 기능이 제안 단계까지는 비퇴행으로 동작.
- [ ] **격리 critique 통과** — 경계 정합(발견/매립이 깨끗이 갈렸나) + CON-3 self-approval 금지
      (별도 컨텍스트 reviewer) + distill 기능 비퇴행 확인. VERDICT: APPROVE.

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| **T1 — 매립 엔진 부재 동안 transition** | (a) distill이 제안만 출력 + WRITE 잠정 유지(점진) / (b) WRITE 즉시 제거 + 매립은 G19 대기(강결합) | **(a) 점진** | 매립 엔진(G19)이 아직 claude-kit에 없음. WRITE 즉시 제거하면 매립 엔진 나오기 전까지 distill 기능 공백. 발견/매립 경계는 *명세*로 먼저 긋고, 저작은 G19가 흡수할 때 distill에서 제거. distill 비퇴행 우선 |
| **T2 — Phase 2 PRIORITIZE 귀속** | distill 잔류(스킬 증류 전용 로직) / 매립 엔진 이관(범용 "어디에") | **매립 이관(명세상)** | patch>extend>reference>new는 "어디에 박을지" = 매립 판단. add-policy 칼2(CLAUDE.md/hook/skill 매립지)와 동일 도메인. 단 T1(a)대로 코드 이관은 G19에서, G18은 *경계 마킹*까지 |
| **T3 — issue 바인딩** | #251 직접(부분충족) / 발견 갈래 전용 이슈 신설 | **이슈 신설 (#252) — 확정** | #251은 에픽이라 이 goal이 닫지 않음. 추적 정합상 발견 갈래 전용 이슈(#252) 신설로 확정(2026-06-16, repo owner). `issues: [252]` + #251 advisory(G16 선례와 일관) |
| **T4 — work_type 적합성** | feature-full / doc-only | **feature-full** | SKILL.md 재저작이 문서처럼 보이나 스킬 *동작*을 바꾸는 기능 변경 + 경계 설계라 spec→impl→critique 3단계가 유효. 격리 critique가 경계 정합 검증에 실하중 |

## 슬라이스 순서

1. **발견↔매립 경계 명세** → 바인딩: spec-first | 대상 파일: `feedback-loop/skills/distill/` (경계 명세 — SKILL.md 내 섹션 또는 인접 reference) | 산출: distill 출력 계약(자연어 제안 객체 형식) = 매립 엔진(G19) 입력 인터페이스 + Phase 2/4/5의 매립 책임 식별 | 검증: 제안 객체 형식이 G19 매립 엔진의 입력으로 소비 가능한 계약인지 명세 수준 정합(쟁점 T1/T2 verdict 기록)
2. **distill SKILL.md 재구조화** → 바인딩: executor|native(#133) | 대상 파일: `feedback-loop/skills/distill/SKILL.md` | 산출: 발견/제안 레이어로 재저작 + 매립 책임 분리 마킹 + transition 전략(T1 verdict) 반영 | 검증: frontmatter 파싱 + 발견/매립 경계 섹션 존재 + distill 기능 제안 단계까지 비퇴행
3. **격리 critique** → 바인딩: adversarial-review|code-reviewer(#133) | 대상 파일: (분석만) | 산출: 경계 정합 + 비퇴행 + CON-3 self-approval 금지 검증 verdict | 검증: 별도 컨텍스트 reviewer가 VERDICT: APPROVE (REJECT 시 S2 재작업)

> **슬라이스 의존**: S1 → S2 → S3 순차. S1 경계 명세가 S2 재구조화의 입력, S2 산출을 S3가 격리
> 검토. `→`는 산출→입력 체이닝(goal-doc-spec §3.5). S3 verdict(PASS/REJECT)는 이 쟁점 섹션에 기록.

## 제약 / 안전판 (재정의 금지 — 참조만)

- 헌법/정책 단일출처: `docs/design/claude-kit-boundary.md` §5. 특히 **CON-3 격리 critique**(S3가
  self-approval 금지 enforce) · **CON-5 단방향 의존**(feedback-loop는 leaf OUTPUT만 읽고 leaf code
  import 0 — distill 재구조화가 이 경계를 흐리지 않게).
- distill MECE 경계: `feedback-loop/skills/distill/SKILL.md` Boundary ①(절차 기법만, 선언지식은
  vault)/②(vs skill-creator). 이 분리는 발견/매립 분리와 직교 — 둘 다 유지.
- 경량화 원칙(#251): "도구를 위한 도구 금지". 경계 명세는 distill을 *얇게* 만드는 방향이지,
  새 추상 레이어를 추가하는 게 아니에요.
- 매립 엔진 본체(add-policy 범용화)는 **G19 범위** — 이 goal은 distill 측 출력 계약까지만.

## E2E 자가검증

```bash
# 1) distill SKILL.md frontmatter 파싱 + 필수 키 (재구조화 후 비손상)
python3 -c "import yaml,sys; d=open('feedback-loop/skills/distill/SKILL.md').read(); \
  fm=d.split('---')[1]; m=yaml.safe_load(fm); \
  assert all(k in m for k in ['name','description','model','allowed-tools']), 'frontmatter missing key'; \
  print('distill frontmatter OK')"

# 2) 발견/매립 경계 섹션 존재 (S1 명세가 SKILL.md에 반영됐는지)
grep -qi 'discover\|발견\|propose\|제안' feedback-loop/skills/distill/SKILL.md \
  && echo "boundary section present" || echo "MISSING boundary section"

# 3) 언어 정책 가드 (metadata 한글 누수 0)
python3 scripts/check-language-policy.py
# Expected: OK: language-policy clean

# 4) type opt-in 가드 (마크다운 type 필드)
python3 scripts/check-type-optin.py
# Expected: OK: check-type-optin clean

# 5) version-sync (distill description 변경 시 marketplace 동기화)
python3 scripts/check-version-sync.py
# Expected: OK: version-sync clean (drift 시 --fix)
```

> 통과 기준은 DoD 3항목과 1:1 — 경계 명세 SKILL.md 반영(2)·재구조화 비손상(1)·정책 가드(3-5).
> S3 격리 critique VERDICT는 자가검증 자동화 대상이 아니라 별도 컨텍스트 reviewer 산출(CON-3).
> distill description을 바꾸면 trigger 문구 회귀를 수동 확인(thinking-tools trigger-regression은
> feedback-loop 비대상 — distill trigger는 #251 발견 시작점이라 보존 필수).

## 참조

- 이슈: #252(이 goal이 닫는 발견 갈래 작업 이슈), #202(distill 배포, CLOSED — 역할분리 상류), #210(telemetry 측정 갈래 cross-ref)
- Epic: #251 (재귀개선 루프 정밀화 — 발견 갈래; advisory 링크, frontmatter epic-neutral)
- 선행: #100(goal-doc-spec, CLOSED), #133(⑤ 스킬 인벤토리, CLOSED — `executor|native` 귀속)
- 후속: G19(매립 — add-policy 범용 엔진, 이 goal의 출력 계약을 입력으로), G20(측정 — telemetry 폐루프)
- 산출 경위: #251 task list "발견 — distill 역할 분리 (선행 1순위)" 슬라이스화
- 정합: local-harness add-policy + `docs/decisions/2026-06-14-dev-harness-slim-and-p3.md`(행선지 ADR — 매립 행선지가 "local 잔류"에서 "claude-kit 입주"로 뒤집힌 결정, G19 상류)
