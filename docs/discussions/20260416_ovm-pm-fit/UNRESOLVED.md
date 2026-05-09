# Unresolved — OVM PM Fit 패널

**Date**: 2026-04-16

모든 주요 토픽 합의. 다음은 구현 착수 전 결정 필요:

## U1. Vault Preamble 템플릿 구성

OMC planner/executor가 vault 컨벤션을 준수하도록 주입할 preamble 최소 요소:

- [ ] 파일명 컨벤션 (`{type}-YYYY-MM-DD[-{topic}][-vN].md`)
- [ ] Frontmatter 표준 (`created`, `tags`, `type`, `status`, `workstream`, `role`, `parent`)
- [ ] 디렉토리 배치 규칙 (`00_Inbox/`, `20_Projects/`, `30_Notes/`, `10_MOC/`)
- [ ] wiki-link 규약
- [ ] 쓰기 금지 영역 (W1 이후: 기존 `30_Notes/*` 본문)
- [ ] OVM의 "vault-내부 한정" 경계

**미결정**: 길이 상한 (token 소모 방지), 예제 포함 여부

## U2. `/plan-audit`와 `/plan-consolidate` 분리의 실효성

- 한 스킬(`/plan-manage`)로 통합 vs 두 스킬 분리
- 분리 이점: "감사만" 실행 가능 (dry-run 유사)
- 통합 이점: 워크플로 마찰 감소
- **권고**: 분리 유지 (감사 결과 확인 후 통합 결정 승인 게이트)

## U3. OMC planner 호출 실패 시 폴백

- OMC 미설치 환경에서 OVM PM 스킬이 어떻게 동작?
- 옵션 A: OMC 강제 의존, 미설치 시 에러
- 옵션 B: 폴백 수동 가이드 출력
- 옵션 C: 기본 Claude 에이전트로 fallback
- **권고**: 옵션 A (OMC 생태계 기본 전제). 단 marketplace.json에 의존 명시

## U4. Preamble 위치

- Option 1: SKILL.md 본문 상단에 인라인
- Option 2: `obsidian-vault-manager/reference/vault-conventions-preamble.md`로 분리, SKILL에서 로드
- **권고**: Option 2 (재사용·업데이트 용이)

## U5. 이전 W7(binding) / W8(autosync) 조정 범위

이 패널 결정이 W7/W8에 미치는 영향:
- W7 (Note↔Project Binding): 영향 없음. 지식 레이어 규약은 PM 레이어와 독립.
- W8 (plan-doc-autosync): 영향 있음. "세션 계획 문서 자동 vault 저장"의 쓰기 주체가 `/plan-consolidate`와 겹칠 수 있음. **W8이 OVM의 일부로 재위치될 가능성** 검토 필요.

**미결정**: W8을 vault-bridge에 두는 현재 설계 유지 vs OVM으로 이동

## U6. 기존 프로젝트 참고

- OMC 생태계의 `/plan`, `/ralplan` 등 기존 스킬 중 재활용 가능한 것이 있나?
- `/plan-audit`·`/plan-consolidate`이 기존 스킬의 얕은 래퍼라면 신규 스킬 자체가 불필요할 수도
- **결정 필요**: OMC 기존 스킬 조사 후 중복 여부 최종 확정
