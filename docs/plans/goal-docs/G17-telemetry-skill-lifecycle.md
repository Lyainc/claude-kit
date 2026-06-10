---
goal_id: G17
title: telemetry per-skill lifecycle 파생 뷰 — never-fired/last-used 식별 (report.py)
issues: [203]
wave: 독립
depends_on: []
recommended_model: sonnet
status: ready
work_type: feature-full
created: 2026-06-10
---

# G17 — telemetry per-skill lifecycle 파생 뷰

## 배경 / 목적

`report.py`는 top-N 집계만 산출해서 **count 0인 스킬은 Counter에 키 자체가 없어**
`--top`을 키워도 영구 비가시예요. "안 쓰이는 스킬"(트리거 안 되는 description, 죽은
표면)을 리포트가 못 보여주는 건 telemetry README Phase 2 진입 조건("actionable
insights ≥3" + "data-gap 식별")의 명시적 격차예요(#203).

착안은 SIS(claude-self-improving-skills)의 per-skill lifecycle 집계 — 단 **관점만
차용**, 메커니즘은 우리식 파생 뷰. flock 사이드카는 도입하지 않아요(lockless
O_APPEND 철학 유지). 소비처: retro COLLECT phase가 이 뷰를 waste 신호로 읽어요.

## 완료 조건 (Definition of Done)

- [ ] `report.py`에 lifecycle 파생 뷰 추가: 카탈로그(`*/skills/*/SKILL.md` 스캔)
      대비 `never-fired` / `last-used > Nd` / `bottom-N` 섹션 출력
- [ ] 카탈로그 source of truth = `*/skills/*/SKILL.md` 스캔 (plugin-map.json은
      bare-name lookup 보조일 뿐 카탈로그 아님)
- [ ] 기존 events jsonl **읽기 전용** — 쓰기 경로 변경 0, 새 파일 0
- [ ] **측정범위 캐비앗 하드코딩**: 뷰 출력에 "claude-kit 레포 내 세션 기준
      (telemetry Option A)" 명시
- [ ] **해석 가이드 동봉**: in-repo 사용이 본질인 스킬(thinking-tools류) 우선 해석,
      vault-bridge/OVM류 never-fired는 측정범위 밖 사용 가능성 먼저 의심하라는 출력
- [ ] distilled-skill 뷰(~/.claude/skills 스캔)는 **제외** (UNRESOLVED U4, P3 재상정)
- [ ] `test-report.py` 케이스 확장: zero-count 스킬 가시화 + 캐비앗 문자열 출력 검증

## 쟁점과 트레이드오프

| 쟁점 | 선택 | 비용 |
|------|------|------|
| 카탈로그 출처 | SKILL.md 스캔 (레포가 진실) | plugin-map.json과 이원화 아님 — map은 lookup 보조 |
| zero-count 가시화 방식 | 파생 뷰 (이벤트 스키마 불변) | SIS식 사이드카 카운터 기각 — O_APPEND 철학 유지 |
| 측정범위 왜곡 | 캐비앗 하드코딩 + 해석 가이드 | never-fired ≠ 무가치 (타 프로젝트 사용 비가시) |

## 슬라이스 순서

1. **spec** → 바인딩: spec-first | 대상 파일: docs/plans/spec-203-skill-lifecycle-view.md | 산출: 구현 스펙 (메인 컨텍스트 작성 완료) | 검증: 사용자 확인
2. **impl** → 바인딩: executor|native(#133) | 대상 파일: telemetry/scripts/report.py, telemetry/scripts/test/test-report.py | 산출: lifecycle 파생 뷰 + 테스트 확장 | 검증: python3 telemetry/scripts/test/test-report.py
3. **critique** → 바인딩: adversarial-review|code-reviewer(#133) | 대상 파일: impl diff | 산출: VERDICT (APPROVE/REJECT + findings) | 검증: APPROVE 도달

## E2E 자가검증

```bash
python3 telemetry/scripts/test/test-report.py
# Expected: OK (기존 + 신규 lifecycle 케이스 전부)
python3 telemetry/scripts/report.py --since=all >/dev/null && echo "report OK"
python3 telemetry/scripts/validate-schema.py --self-test
# Expected: 기존 green 유지 (이벤트 쓰기 경로 불변)
```
