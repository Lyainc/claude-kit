---
goal_id: G18
title: 발견 갈래 — distill 역할 분리 (판단/제안 ↔ 매립 저작 분리, #251 선행 1순위)
issues: [252]
wave: 1
depends_on: []
recommended_model: opus
status: ready
work_type: feature-full
created: 2026-06-16
---

# G18 — distill 역할 분리 (발견/제안 ↔ 매립 저작)

> **⚠️ 부분 충족 goal — 에픽 #251의 "발견" 갈래만 닫아요.** #251(재귀개선 루프 정밀화)은
> 발견(distill 분리)→매립(add-policy 범용 엔진)→측정(telemetry 폐루프) 세 갈래로, 이 goal-doc은
> 그중 **선행 1순위인 발견 갈래**만 다뤄요. 이 goal이 닫는 작업 이슈는 발견 갈래 전용 **#252**이고,
> 에픽 #251은 매립(G19 예정)·측정(G20 예정)이 다 끝나야 close돼요 — G18 완료 ≠ #251 close
> (#251은 본문 "## 참조"의 advisory 링크로 관리, goal-doc-spec §1.3 epic-neutral 정합).

> **선행 계약이라 `gated`로 시작 → consensus 게이트 통과로 `status: ready` 전환됨(2026-06-16).**
> S1(발견↔매립 인터페이스 계약)이 매립 갈래(G19)의 입력 인터페이스를 확정하는 linchpin이라,
> goal-doc-spec §1.1("linchpin/고위험은 gated 시작")대로 consensus 게이트(architect+critic)를 먼저
> 걸었어요. 게이트는 **방향 합의 + 보강 7건(C1~C7) 반영**으로 통과했고(verdict는 "쟁점과
> 트레이드오프 > consensus 게이트 verdict" 섹션), 그 보강이 본 goal-doc에 반영된 상태예요. distill
> SKILL.md 리팩터 자체(S2)는 저위험이지만, 경계 명세(S1)가 후속 갈래를 묶는 계약이라 게이트를 걸었어요.

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
distill은 **발견/제안(자연어)만** 남기고, 매립 책임(Phase 2의 "어디에" 판단 + Phase 4 저작 +
Phase 5의 *산물* 검증)을 분리해요. 단 통째 분리가 아니라 **Phase별 면(面) 분할**이에요(consensus
게이트 C3·C4): Phase 5의 *자리* 검증("읽히는 자리 맞나" — SUMMARY §5(c) 매립후검증 씨앗)과
provenance/inviolability *판단*("이 스킬 건드려도 되나")은 **발견 측에 잔류**하고, 제안 객체가 그
판단을 운반해요. 이 분리의 산출 = **distill 출력 = 매립 엔진이 소비할 자연어 제안 객체**(shape
category + 필수정보 산문; 직렬 format은 소비자 G19로 이연 — C2)이고, 이게 #251이 말한 "매립 엔진
입력 인터페이스 확정 → 코어 모양이 잡힘"의 선행 조건이에요.

**왜 지금 이것부터인가** (세 근거):
- **블로커** — 발견 갈래는 매립(G19)·측정(G20)의 선행. distill 출력 계약이 잡혀야 매립 엔진 입력
  인터페이스가 확정돼요(#251 "선행 = distill 역할 분리").
- **수요 무관 가치** — #251이 명시: "수요와 무관하게 지금도 깨끗해지는 리팩터". 매립 엔진을 짓든
  안 짓든, 발견/매립 책임 경계를 명시하는 것만으로 distill SKILL.md가 깨끗해져요.
- **dogfooding** — work_type=feature-full이라 slice-router가 feature-full로 라우팅 →
  feature-full.js(#201) impl/critique 분리 스테이지로 실행되며 dev-harness 워크플로를 self-test해요.

## 완료 조건 (Definition of Done)

#251 발견 갈래 task와 1:1 (각 슬라이스가 한 항목):

- [x] **발견↔매립 책임 경계 명세** — distill의 출력 계약을 "자연어 제안 객체"로 정의하되 **shape
      category + 필수정보(무엇을 / 왜 안 지키면 깨지나 / 어느 세션 패턴에서 나왔나)의 산문 명세**까지
      (직렬 스키마·필드 format은 소비자 G19로 이연 — C2). Phase 2의 "어디에 박을지" 판단 + Phase 4
      저작 + Phase 5 *산물* 검증이 **매립 책임**임을 명시. 단 Phase 5 *자리* 검증 +
      provenance/inviolability *판단*은 **발견 잔류**(C3·C4). distill에 남는 것 = SCAN(발견) +
      제안(+inviolability 판단) + GATE(제안 넘길지 확인)임을 경계로 고정.
- [x] **distill SKILL.md 재구조화** — 발견/제안 레이어로 재저작. 매립 책임은 분리 마킹 + transition
      전략(T1: WRITE 잠정 유지 + **봉인/deferral 표식**으로 G19 명시 제거 대상화 — C6). provenance
      마커의 기계적 write는 매립이되, **inviolability 판단·안전 불변식("user-authored 스킬은 덮어쓰지
      않음")은 재저작 중 비손실**(C4). distill 기능이 제안 단계까지 비퇴행으로 동작.
- [x] **격리 critique 통과** — 경계 정합(발견/매립이 깨끗이 갈렸나) + CON-3 self-approval 금지
      (별도 컨텍스트 reviewer) + distill 기능 비퇴행 + 안전 불변식 보존 확인. VERDICT: APPROVE.

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| **T1 — 매립 엔진 부재 동안 transition** | (a) distill이 제안만 출력 + WRITE 잠정 유지(점진) / (b) WRITE 즉시 제거 + 매립은 G19 대기(강결합) | **(a) 점진** | 매립 엔진(G19)이 아직 claude-kit에 없음. WRITE 즉시 제거하면 매립 엔진 나오기 전까지 distill 기능 공백. 발견/매립 경계는 *명세*로 먼저 긋고, 저작은 G19가 흡수할 때 distill에서 제거. distill 비퇴행 우선 |
| **T2 — Phase 2 PRIORITIZE 귀속** | distill 잔류(스킬 증류 전용 로직) / 매립 엔진 이관(범용 "어디에") | **매립 이관(명세상)** | patch>extend>reference>new는 "어디에 박을지" = 매립 판단. add-policy 칼2(CLAUDE.md/hook/skill 매립지)와 동일 도메인. 단 T1(a)대로 코드 이관은 G19에서, G18은 *경계 마킹*까지 |
| **T3 — issue 바인딩** | #251 직접(부분충족) / 발견 갈래 전용 이슈 신설 | **이슈 신설 (#252) — 확정** | #251은 에픽이라 이 goal이 닫지 않음. 추적 정합상 발견 갈래 전용 이슈(#252) 신설로 확정(2026-06-16, repo owner). `issues: [252]` + #251 advisory(G16 선례와 일관) |
| **T4 — work_type 적합성** | feature-full / doc-only | **feature-full** | SKILL.md 재저작이 문서처럼 보이나 스킬 *동작*을 바꾸는 기능 변경 + 경계 설계라 spec→impl→critique 3단계가 유효. 격리 critique가 경계 정합 검증에 실하중 |

### consensus 게이트 verdict (architect + critic 격리 검토, 2026-06-16)

S1 착수 전 게이트(goal-doc-spec §1.1 — linchpin·gated 시작). architect·critic 두 관점을 별도
컨텍스트에서 독립 검토(CON-3: reviewer≠author). **방향 합의**: 발견/매립 분리 + T1 점진 + T2 명세상
이관은 양쪽 모두 **AGREE-WITH-CONDITION** — 상류 SUMMARY §2.3(R3 역할 분리)·add-policy §3 배치
규칙(patch>extend>reference>new = "어디에 박을지" 매립 판단)·§5 엔트리 템플릿(What/Why)과 정합.
단 `ready` 전환 조건으로 두 관점이 수렴한 보강 7건을 반영해요. **공통 근본**: distill의 5 Phase를
*통째로* 발견/매립 한쪽에 배정한 게 틀렸어요 — GATE·SELF-CHECK·WRITE는 발견 면과 매립 면을 동시에
가져서 각각 면(面) 분할 대상이에요.

| # | 보강 | 출처 | 반영 |
|---|------|------|------|
| C1 | **비퇴행 게이트 교체** — 기존 grep `discover\|발견\|propose\|제안`은 리팩터 *전* 파일에서도 통과(무력·자기충족). 재구조화로만 생기는 sentinel anchor + 매립 책임 마킹 존재로 교체해 "리팩터됨 vs 무변화"를 실제 구분 | architect 권고4 + critic BLOCKER-1 | §E2E (2) |
| C2 | **자연어 제안 = shape category + 필수정보 산문, format은 G19 이연** — what/why/세션 근거는 *지금* 산문 명세(발견 측 출력 품질 요건), 직렬 스키마·필드 format은 소비자(G19) 생길 때. add-policy §2/§5 입력 기대 역산이되 claude-kit 자기완결(경로 의존 X, lineage만 — CON-5) | architect 권고2 + critic BLOCKER-3 | DoD·S1 |
| C3 | **Phase 5 SELF-CHECK 면 분할** — "산물 검증(frontmatter 파싱 등 → 매립)" vs "자리 검증(읽히는 자리 맞나 → SUMMARY §5(c) 매립후검증 씨앗, 발견 잔류)". 통째 매립 금지 | architect 권고1 | 배경·DoD·S1 |
| C4 | **provenance/inviolability 발견-측 귀속(안전 불변식)** — "이 기법이 기존 스킬 X를 patch하나, X가 inviolable한가"의 *판단*은 발견(distill 잔류) + 제안 객체가 운반, 마커의 기계적 *write*만 매립. S2 재저작이 "user-authored 스킬은 덮어쓰지 않음" 규칙을 떨구지 않게 | critic BLOCKER-4 | 배경·DoD·S2·§E2E (2c) |
| C5 | **GATE 매립-확인 분리** — GATE의 "patch/extend/new + target 확인"은 매립 결정의 확인 → 매립 엔진(G19) 1클릭 게이트로 표시. distill GATE는 "이 제안 넘길까"까지(단 transition 동안 잠정 유지 가능 — C6 정합) | architect 권고3 | S1·S2 |
| C6 | **transition WRITE 봉인/deferral 마커** — WRITE에 "잠정·G19 흡수 시 제거" 표식 + deferral 마커로 하이브리드 영구화 방지·G19 명시 제거 대상화 | architect 권고4 + critic BLOCKER-2 | 제약·DoD·S2 |
| C7 | **(minor) E2E #1 PyYAML 의존 제거** → stdlib 파싱(invariant_guard._parse_frontmatter 동형, repo 컨벤션) + **trigger 보존 자동 가드**(`grep -q 증류 && grep -q distill`) | critic minor | §E2E (1)(2b) |

> **C2의 architect↔critic 텐션 해소**: architect "빈 라벨 방지 위해 필수정보 명세" ↔ critic "소비자
> 없는 format 프리징 = YAGNI"는 충돌이 아니라 층위 차이라 양립해요 — *자연어가 담아야 할 내용*
> (what/why/근거)은 지금 명세하고, *그 내용의 직렬화된 필드 구조*는 G19로 이연. 둘 다 "새 추상 레이어
> 금지(#251)"를 공유해요.

> S3 격리 critique(별도 컨텍스트, VERDICT: APPROVE 필요)는 이 게이트와 별개예요 — S2 재구조화 *산출*의
> 비퇴행·경계 정합·안전 불변식 보존을 사후 검증해요. S3 verdict(PASS/REJECT)도 이 섹션에 추가 기록.

### S3 격리 critique verdict (code-reviewer, 별도 컨텍스트, 2026-06-16)

feature-full.js(#201) 워크플로로 S2 impl(executor) → S3 critique(code-reviewer)를 분리 agent()
스테이지로 실행(CON-3 구조적 강제 — reviewer≠author, 별도 컨텍스트). **VERDICT: APPROVE** — 3 DoD
전부 충족, §E2E 8개 가드 통과(frontmatter·sentinel·trigger·inviolability·language·type·version·banned).
S2 diff는 **strictly additive(69 insertions, 0 deletions)**라 원래 Phase 1~5 로직 무손상 = 비퇴행
구조적 보장.

findings(전부 non-blocking, verdict 게이트 안 함):
- **F1 (MEDIUM)** — boundary 섹션 "never fills the classification grid"가 절대적으로 읽히는데
  transition 동안 Phase 2/3가 placement-action을 함(텐션). → **반영 완료**: target-state 한정 +
  placement-action(잠정 유지)과 add-policy 격자(절대 안 채움) 구분 + transition 마커가 placement+WRITE
  둘 다 덮게 수정.
- **F2 (LOW)** — layer/scope/tier/channel을 정의 없이 사용. → **반영 완료**: "the embedding engine's
  placement schema" gloss 추가(self-contained, CON-5 lineage-only).
- **F3 (LOW)** — goal-doc status flip이 S2 files_changed 밖. → **no-action**(정확: goal-doc 편집은
  S1/게이트 산출이지 S2 executor 작업 아님 — critic도 동의).

F1/F2 반영분은 critic이 명시한 수정안 그대로라 critic-directed fix(self-approval 아님). 반영 후 §E2E
8개 재통과 확인. **G18 DoD 3항목 전부 충족, S3 APPROVE로 격리 critique 통과(2026-06-16).**

## 슬라이스 순서

1. **발견↔매립 경계 명세** → 바인딩: spec-first | 대상 파일: `feedback-loop/skills/distill/` (경계 명세 — SKILL.md 내 섹션 또는 인접 reference) | 산출: distill 출력 계약 = **shape category + 필수정보(무엇을 / 왜 / 세션 근거) 산문 명세**(직렬 format은 G19 이연 — C2) + Phase 2/4 매립 + Phase 5 *면 분할*(산물=매립 / 자리=발견) + provenance·inviolability *판단*의 발견 귀속 식별(C3·C4) + GATE 매립-확인 분리(C5) | 검증: 필수정보 산문이 G19 매립 엔진(add-policy lineage, 런타임 의존 X)의 분류 입력으로 충분한 자기완결 계약인지 명세 정합(consensus verdict 섹션 + S3 기록)
2. **distill SKILL.md 재구조화** → 바인딩: executor|native(#133) | 대상 파일: `feedback-loop/skills/distill/SKILL.md` | 산출: 발견/제안 레이어로 재저작 + 매립 책임 분리 마킹(**sentinel anchor** `DISCOVER-LANDFILL-BOUNDARY` + `landfill responsibility` — C1) + transition WRITE 봉인/deferral 표식(C6) + 안전 불변식 비손실(C4) + trigger 문구 보존(C7) | 검증: frontmatter 파싱(stdlib) + 경계 섹션 sentinel 존재 + trigger·inviolability 보존 + distill 기능 제안 단계까지 비퇴행
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
- **transition deferral (C6)**: T1(a) 점진은 distill을 "제안 명세 + Phase 4 WRITE 잠정 유지"
  하이브리드로 남겨요. WRITE 블록에 "잠정·G19 흡수 시 제거" 봉인 표식을 달고, 그 표식이 G19(매립
  엔진)의 명시적 제거 대상이 되게 해요. 표식 없이 두면 "잠정"이 영구화되거든요 — 하이브리드는
  *관리되는* transition이지 종착이 아니에요(critic BLOCKER-2: 트립와이어 없으면 영구화).

## E2E 자가검증

```bash
# 1) distill SKILL.md frontmatter 파싱 + 필수 키 (재구조화 후 비손상)
#    repo 컨벤션대로 stdlib만 사용 — PyYAML 의존 회피(invariant_guard._parse_frontmatter 동형, C7).
python3 -c "
d = open('feedback-loop/skills/distill/SKILL.md').read()
assert d.startswith('---'), 'no frontmatter'
fm = d.split('---', 2)[1]
keys = [ln.split(':', 1)[0].strip() for ln in fm.splitlines() if ':' in ln and not ln.startswith((' ', '\t'))]
missing = [k for k in ['name', 'description', 'model', 'allowed-tools'] if k not in keys]
assert not missing, 'frontmatter missing key: %s' % missing
print('distill frontmatter OK')"

# 2) 발견/매립 경계 섹션 존재 — sentinel anchor로 검증 (C1).
#    기존 grep 'discover|발견|propose|제안'은 리팩터 *전* 파일에서도 통과(무력·자기충족)했음.
#    재구조화로만 생기는 고정 앵커 2개를 요구해 '리팩터됨 vs 무변화'를 실제로 구분.
grep -q 'DISCOVER-LANDFILL-BOUNDARY' feedback-loop/skills/distill/SKILL.md \
  && grep -q 'landfill responsibility' feedback-loop/skills/distill/SKILL.md \
  && echo "boundary section present (sentinel OK)" || echo "MISSING boundary section/sentinel"

# 2b) trigger 문구 보존 가드 (C7) — #251 발견 시작점이라 회귀 금지.
#     thinking-tools trigger-regression은 feedback-loop 비대상이라 여기서 결정적으로 확인.
grep -q '증류' feedback-loop/skills/distill/SKILL.md \
  && grep -q 'distill' feedback-loop/skills/distill/SKILL.md \
  && echo "trigger phrases preserved" || echo "MISSING trigger phrase (REGRESSION)"

# 2c) 안전 불변식 보존 가드 (C4) — user-authored 스킬 inviolability가 재저작에서 떨어졌는지.
grep -qi 'inviolable\|user-authored' feedback-loop/skills/distill/SKILL.md \
  && echo "inviolability invariant present" || echo "MISSING inviolability invariant (SAFETY REGRESSION)"

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

> 통과 기준은 DoD 3항목과 1:1 — 경계 명세 sentinel(2)·trigger 보존(2b)·안전 불변식(2c)·재구조화
> 비손상(1)·정책 가드(3-5). (2)(2b)(2c)는 consensus 게이트 C1/C7/C4가 무력 grep을 결정적 가드로
> 교체한 결과예요 — 기존 grep은 리팩터 전 파일에서도 통과해 "비퇴행"을 증명 못 했어요.
> S3 격리 critique VERDICT는 자가검증 자동화 대상이 아니라 별도 컨텍스트 reviewer 산출(CON-3).

## 참조

- 이슈: #252(이 goal이 닫는 발견 갈래 작업 이슈), #202(distill 배포, CLOSED — 역할분리 상류), #210(telemetry 측정 갈래 cross-ref)
- Epic: #251 (재귀개선 루프 정밀화 — 발견 갈래; advisory 링크, frontmatter epic-neutral)
- 선행: #100(goal-doc-spec, CLOSED), #133(⑤ 스킬 인벤토리, CLOSED — `executor|native` 귀속)
- 후속: G19(매립 — add-policy 범용 엔진, 이 goal의 출력 계약을 입력으로), G20(측정 — telemetry 폐루프)
- 산출 경위: #251 task list "발견 — distill 역할 분리 (선행 1순위)" 슬라이스화
- 정합: local-harness add-policy + `docs/decisions/2026-06-14-dev-harness-slim-and-p3.md`(행선지 ADR — 매립 행선지가 "local 잔류"에서 "claude-kit 입주"로 뒤집힌 결정, G19 상류)
