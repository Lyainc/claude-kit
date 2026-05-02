# Expert Panel SUMMARY — PM 기능 OVM 적합성 재검토

**Date**: 2026-04-16
**Supersedes**: `docs/discussions/20260416_pm-agent-design/SUMMARY.md`
**Override Reason**: 이전 패널은 "OVM 정체성 = 개별 artifact CRUD" 전제로 C(신규 플러그인) 선택. 본 패널에서 OVM 기존 스킬 6개 중 3개(inbox-review, context, archive)가 이미 메타·배치 작업임을 발견, 정체성 전제 자체를 "vault 라이프사이클 관리 (portfolio 포함)"로 재정의. 전제 변경으로 결론 역전.

**Objective**: PM 기능을 OVM에 두는 것이 OVM 궁극 목적과 부합하는가, 아니면 scope creep인가.
**Panel**: Moderator, Optimistic Practitioner, Critical Practitioner, Project Manager (필수), Knowledge Management Expert (필수), Plugin Architecture Expert, Product Strategy Expert

## Topics & Outcome

| # | Topic | Outcome |
|---|-------|---------|
| 1 | OVM 궁극 목적 정직한 정의 | 합의: "vault 라이프사이클 관리 across artifact → project → portfolio, vault-내부 한정" |
| 2 | PM 1-4가 OVM에 정말 부합하는가 | 합의: PARA 지원 완성 위한 핵심 기능. scope creep 아님 |
| 3 | OVM 외 대안 재심 | 합의: vault-bridge(티어 불일치), thinking-tools(쓰기 부재), 신규 플러그인(부합도 열위) 모두 탈락 |
| 4 | 이전 패널 override 절차 | 합의: 크로스 레퍼런스 박기, 전제 변경 명시 |

합의 실패 0건.

## Final Decision

| 항목 | 결정 |
|------|------|
| PM 홈 | **OVM** |
| OVM 정체성 재정의 | "Obsidian vault 라이프사이클 관리 (artifact → project → portfolio granularity), vault-내부 범위 한정" |
| 신규 플러그인 | **불필요**. 이전 패널 옵션 C 철회 |
| 신규 에이전트 | **불필요**. OMC planner/executor/verifier 재사용 |
| 구현 | OVM 스킬 2개 추가: `/plan-audit`, `/plan-consolidate` |
| Runtime 엔진 | OMC planner/executor/verifier 호출 + vault preamble 주입 |

## 경계 규약 (scope 오염 방지)

1. **쓰기 경계**: vault 파일시스템(`~/vault/`) 내부만. 코드 리포·외부 파일 쓰기 금지
2. **분석 위임**: 멀티 plan 감사·의존성 분석은 OMC planner 호출 (vault preamble 주입)
3. **Orchestration 제외**: Team dispatch·에이전트 오케스트레이션은 OMC `/team`·`/autopilot` 영역. OVM 범위 아님

## PM 기능 6개 매핑

| # | 기능 | 위치 |
|---|------|------|
| 1 | 다중 plan 감사 | OVM `/plan-audit` (OMC planner 위임) |
| 2 | 의존성 분석 | OVM `/plan-audit` |
| 3 | 통합 Master Plan 작성 | OVM `/plan-consolidate` (OMC executor 위임) |
| 4 | 아카이브 결정 | OVM `/plan-consolidate` |
| 5 | 워크스트림 분해 + DoD | OMC planner 직접 호출 (OVM 스킬 내부) |
| 6 | Team dispatch | **OMC `/team` 영역, OVM 범위 밖** |

## Action Items

### P0
1. OVM `/plan-audit` SKILL.md 작성 (OMC planner 위임 + vault preamble 주입)
2. OVM `/plan-consolidate` SKILL.md 작성 (OMC executor 위임 + 동일 preamble)
3. vault preamble 템플릿: `obsidian-vault-manager/reference/vault-conventions-preamble.md`
4. `vault-knowledge-manager` agent description 개정 — "포트폴리오 레벨 감사·통합은 `/plan-audit`·`/plan-consolidate` 분리" 명시
5. 이전 패널 SUMMARY에 "SUPERSEDED BY" 헤더 추가
6. Master Plan W9 철회 (신규 플러그인 제안 무효). 대신 OVM 새 스킬 2개로 축소

### P1
7. OVM `plugin.json` keywords에 `plan-audit`, `plan-consolidate` 추가
8. OVM README 업데이트 — 확장된 정체성("vault 라이프사이클 관리") 반영
9. `CLAUDE.md` (OVM runtime 지침, 즉 agent/skill description 레벨)에 경계 규약 3종 반영
10. 이전 W7/W8 spec 축소 적용 (직전 비판적 재검토 권고)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| OVM description 키워드가 PM 스킬과 vault-knowledge-manager agent 사이 경쟁 | description 개정으로 명시적 경계 (스킬은 "포트폴리오 레벨", 에이전트는 "개별 note·project" 명시) |
| 사용자가 `/plan-audit` 결과를 OVM이 vault 밖까지 조작한다고 오해 | 스킬 description에 "vault-내부 범위 한정" 명시 |
| OMC planner 호출 시 vault 컨벤션 미준수 | preamble 템플릿 품질에 의존. 초기 몇 케이스 수동 검증 후 safe 단계로 전환 |
| 이전 패널 결정과 상충 기록 혼란 | SUPERSEDES/SUPERSEDED BY 헤더로 명시적 연결 |

## Related Documents

- **Superseded panel**: `docs/discussions/20260416_pm-agent-design/SUMMARY.md`
- **Master Plan**: `~/vault/20_Projects/claude-kit/project-2026-04-16-master-plan.md` (W9 철회 + W7/W8 축소 필요)
- **Previous panel (master plan validation)**: `docs/discussions/20260416_master-plan-validation/SUMMARY.md` (영향 없음, 여전히 유효)
