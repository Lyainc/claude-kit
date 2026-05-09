# Expert Panel SUMMARY — PM Agent Design (C/D/E 심층 비교)

> **STATUS: SUPERSEDED BY `docs/discussions/20260416_ovm-pm-fit/SUMMARY.md`**
>
> 본 패널은 "OVM 정체성 = 개별 artifact CRUD" 전제 하에 옵션 C(신규 플러그인) 선택. 후속 패널(`20260416_ovm-pm-fit`)이 OVM 기존 스킬 중 3개(inbox-review, context, archive)가 이미 멀티파일 메타 작업임을 발견, OVM 정체성을 "vault 라이프사이클 관리 (portfolio 포함)"로 재정의함. 전제 변경으로 결론이 "OVM 편입 + 스킬 2개"로 역전됨. 본 SUMMARY의 Action Items는 **더 이상 유효하지 않음**.

**Date**: 2026-04-16
**Objective**: 기획 에이전트와 실행 에이전트 MECE 분리 통한 성능 고도화. 옵션 C(별도 플러그인) / D(OVM 흡수) / E(thinking-tools 흡수) 비교.
**Panel**: Moderator, Optimistic Practitioner, Critical Practitioner, Project Manager (필수), Knowledge Management Expert (필수), Plugin Architecture Expert, LLM Orchestration Expert

## Topics & Outcome

| # | Topic | Outcome |
|---|-------|---------|
| 1 | C/D/E 정체성·SoC·runtime 적합도 | E 탈락, C vs D 속행 |
| 2 | Planner/Executor 분리 효과와 함정 | 합의: 3층 구조(Plan → Execute → Verify) 채택 |
| 3 | runtime 라우팅 성능 | C 우세 (키워드 경쟁 최소, 네임스페이스 독립) |
| 4 | 유지보수·1년 전망 | C + MVP 범위(planner만 신규, executor/verifier 재사용) |

합의 실패 0건.

## Final Recommendation

| 항목 | 결정 |
|------|------|
| 채택 옵션 | **C — 신규 플러그인 `plan-orchestrator`** |
| MVP 구성 | Planner 에이전트(opus, 신규) + `/plan-audit` + `/plan-consolidate` 스킬 2개 |
| Executor | OMC executor 재사용 + skill 레벨 vault adapter prompt preamble |
| Verifier | OMC verifier 재사용 |
| 핸드오프 artifact | 구조화 Markdown(frontmatter + changes codeblock) |
| 파이프라인 | Plan → User Approval → Execute → Verify (별 세션) |
| Marketplace | OVM·vault-bridge와 peer-dependency, 세트 설치 권장 |

## Plugin Runtime Rules (CLAUDE.md scope 정정 반영)

사용자 scope 지정에 따라, claude-kit **세 플러그인의 runtime 지침**만 개선 (루트 개발용 CLAUDE.md 아님):

### OVM (`obsidian-vault-manager/CLAUDE.md` + agent/skill descriptions)
- `vault-knowledge-manager` description에 "멀티 plan 감사·통합은 scope 아님 → plan-orchestrator 위임" 명시
- 소환 배제 키워드 추가: "마스터 플랜", "워크스트림", "plan consolidate"

### vault-bridge (description + hooks scope)
- vault-searcher는 현 상태 유지 (읽기 소스로 plan-orchestrator planner가 호출)
- W1 구현 시 "메타 계획 문서 쓰기 허용 scope"는 plan-orchestrator 호출 context에서만 활성화

### plan-orchestrator (신규, `plan-orchestrator/CLAUDE.md` + descriptions)
- **planner 에이전트**: "PROACTIVELY when 사용자가 멀티 plan 감사, 마스터 플랜 통합, 워크스트림 분해, team dispatch 최적화 요청 시"
- **`/plan-audit`**: "다중 plan/session 문서 감사 → 중복·의존성·충돌 리포트 생성"
- **`/plan-consolidate`**: "감사 리포트 기반으로 Master Plan + sub-plan frontmatter 정규화 artifact 생성"
- **Planner 금지**: 직접 파일 쓰기 금지 (artifact만 생성). 실제 적용은 executor 호출.

## Action Items

### P0
1. Master Plan에 **W9 — plan-orchestrator 플러그인** 신설 (workstream block 추가)
2. `plan-orchestrator/.claude-plugin/plugin.json` 스캐폴드 (peer-dependency 표기 포함)
3. planner 에이전트 description 초안 (PROACTIVELY 트리거, 소환 신뢰도 8/10 목표)
4. 핸드오프 artifact 스키마 v1 확정 (JSON Schema 또는 구조화 MD)

### P1
5. `/plan-audit` + `/plan-consolidate` SKILL.md 작성
6. vault adapter preamble 템플릿 (frontmatter·wiki-link·type-first 파일명 컨벤션 주입)
7. OVM vault-knowledge-manager description에 배제 키워드 반영
8. marketplace.json에 plan-orchestrator 항목 추가 + 세트 설치 권장 문구
9. claude-kit 루트 README에 4번째 플러그인 소개

### P2
10. 필요 시 V2에서 전용 executor/verifier 분화 검토

## Risks

- **플러그인 4개 체제의 사용자 인지 부담** — marketplace 번들 + README 명확화로 완화
- **Planner artifact 포맷 변경 시 executor 호환성** — JSON Schema 버저닝으로 완화
- **OMC executor의 vault 컨벤션 준수 신뢰도** — vault adapter preamble 품질이 결정 변수. 초기 테스트로 검증 필요
- **runtime 소환 키워드 경쟁** (vault-knowledge-manager ↔ planner) — OVM description 개정이 필수 선행

## Related Documents

- Master Plan: `~/vault/20_Projects/claude-kit/project-2026-04-16-master-plan.md` (W9 추가 대상)
- Previous panel: `docs/discussions/20260416_master-plan-validation/SUMMARY.md`
