---
goal_id: G15
title: ⑤ self-hosting — handoff 실질화 (이슈 청킹·에픽 제안 → goal-doc 슬라이스 바인딩)
issues: [171]
epic: 172
wave: 5
depends_on: [G14]
recommended_model: opus
status: ready
created: 2026-06-08
---

# G15 — handoff 실질화 (#171)

> G14 슬라이스 3(여력 시 항목)을 분리한 자기완결 실행 단위예요. G14에서 ⑤ thin 진입의
> 코어(workflow-harness scaffold + retro)가 닫혔고, 이 goal은 ⑤ self-hosting의 두 번째
> 조각 — "쌓인 이슈를 손으로 청킹/에픽 묶기"라는 가장 비싼 수작업을 자동화해요.

## 배경 / 분리 사유

#171은 레퍼런스 워크플로우 step 2(handoff: 열린 이슈 검토 → 해결에 유리한 단위로 청킹/에픽
제시)의 실질화예요. G14에서 "여력 시" 항목이었으나, 두 선행 제약 때문에 별도 슬라이스로
분리했어요:

1. **#140 물리위치 게이트 미해결**: "이슈 읽기→청킹"=②인접 vs "슬라이스 루프 진입"=⑤. 급조 시
   잘못된 위치 배치 → CON-5 경계 훼손 리스크.
2. **#104(vault-bridge slim) 정합**: #172 권장순서가 #171 앞에 #104를 두고, #171 노트도
   "#104 slim 정합 위치 제약 준수"를 명시.

현재 `vault-bridge/commands/handoff.md`는 continuation-prompt 생성기(③ delivery)일 뿐, 청킹/
에픽 로직이 없어요(사실상 껍데기).

## 물리위치 권고 (#140 게이트 — 빌드 착수 시 확정)

**권고: ⑤ workflow-harness 신규 스킬** (예: `handoff-plan`). 근거:

- #171의 핵심 산출물은 **goal-doc 슬라이스 바인딩 출력**(다음 세션 `/goal` 진입) = ⑤ 슬라이스
  루프 진입. 이게 deliverable의 무게중심이라 ⑤가 자연스러운 home.
- CON-5 정합: ⑤ 스킬이 `gh` 이슈(외부 데이터)를 읽고 goal-doc(⑤ 아티팩트)을 생성 → 어떤 leaf도
  이 스킬에 역의존하지 않음. (반대로 ②에 두면 ⑤ 슬라이스 루프가 ② 스킬에 의존 — harness→leaf라
  허용되긴 하나, 산출물 무게중심이 ⑤이므로 ⑤ 배치가 더 단순.)
- 기존 vault-bridge `/handoff`(continuation prompt, ③)는 그대로 유지 — 역할이 다름(세션 인수인계
  vs 백로그 청킹). 중복 정의 금지.

**확정 절차**: 빌드 착수 시 이 권고를 #140 패턴으로 1줄 기록(기존 ② 도메인 플러그인이 아니라 ⑤
신규 스킬인 이유 = 산출물이 슬라이스 루프 진입). C-2(thin 신규 플러그인 금지)는 해당 없음 —
workflow-harness는 G14에서 이미 신설된 ⑤ home이라 거기 입주.

## 완료 조건 (Definition of Done)

- [ ] `workflow-harness/skills/handoff-plan/SKILL.md` (또는 합의된 위치) — 열린 이슈 수집
      (`gh issue list`) → 의존성·도메인 기준 청킹 → "한 세션 병렬 처리 가능 단위" 제안.
- [ ] 에픽 후보 식별 + 링크 제안 — **user-confirmed 게이트**(silent 등록 금지, #125 안전판 일관).
- [ ] 청킹 결과 → **goal-doc(#100) 슬라이스 바인딩 형식** 출력(다음 세션 `/goal`로 바로 연결).
      goal-doc 스키마는 `docs/design/goal-doc-spec.md` 준수.
- [ ] vault 쓰기 없음 또는 user-initiated slash만 (CON-1). 에픽/이슈 변경은 `gh` + user-confirmed.
- [ ] 단방향 의존(CON-5): ⑤ → leaf만. 역방향 금지. plugin.json version-sync + ci-coverage green.
- [ ] 격리 code-reviewer/verifier 패스(자기승인 금지, CON-3).

## 제약 / 안전판 (재정의 금지 — 참조만)

- 헌법/정책 단일출처: `docs/design/claude-kit-boundary.md` §5 (CON-1 vault write·CON-3 self-approval·CON-5 단방향).
- 확인 게이트(#125 rule-tiers §2): 에픽 등록·이슈 변경은 자동 후보까지, 확정은 사용자. silent 금지.
- 물리위치: #140 게이트(위 권고 — 빌드 착수 시 1줄 확정).

## 참조

- Epic: #172(self-hosting sub-epic, 권장순서 #123→#171→#134), #108(layer redesign)
- 선행: G14(`G14-self-hosting-bootstrap.md` — workflow-harness + retro 입주 완료)
- 정합 권장: #104(vault-bridge slim) — #171 전 권장(#172). 착수 시 #104 상태 확인.
- 후속: #134 게이트체인(handoff·retro·CI 게이트 오케스트레이션)

## 권장 진행

1. #104 상태 확인 → 정합 위치 제약 반영.
2. #140 위치 1줄 확정(⑤ workflow-harness 권고) → 빌드.
3. 청킹·에픽·goal-doc 슬라이스 바인딩 직렬 구현 → 격리 리뷰(자기승인 금지) → version-sync·ci-coverage green.
