# 열린 이슈의 제품 개발 단위와 잔여 Seed 계획

2026-10-11 사용자 확정 계획. 기준 소스는 main `cd571879d75df2209f7b0cf27c958ba53b89efdd`(v6.0.2)다. 열린 이슈 23개와 현재 열린 PR 6개를 확인했다. 이슈 본문은 최초 intake 이후 변하지 않았고, 새 draft PR #847은 이번 재계획에 반영했다. 이 문서는 개발 계획이며 Seed나 완료 근거를 대신하지 않는다.

> 2026-10-12 상태 정정: 이슈 작업 #834·#815·#793은 각각 PR #853·#852·#851로 완료되어 닫혔다. 아래 서술은 확정 당시 계획이며, 이 세 작업을 미해결로 읽지 않는다.

**제품 작업 묶음 6개 안에서 새 Seed 8개와 명확한 이슈 작업 3개를 관리한다.** 사용자가 “수정한 계획대로 8개 Seed와 3개 이슈 작업으로 확정 (추천)”을 선택했다. 이슈마다 Seed를 하나씩 만드는 11개 생성안은 폐기한다. 공동 목표·승인·완료 판정이 같은 요구만 한 Seed로 통합한다. 같은 파일을 만지거나 같은 릴리스에 들어간다는 사실만으로 요구를 합치지 않는다.

## 확정된 사용자 결정과 미확정 범위

- 대상은 열린 이슈 전체의 유효한 잔여 요구다. 이미 충족한 요구와 진행 PR 범위를 다시 구현하지 않는다.
- #835 사용자 응답은 한국어 기본이며 영어로 요청하면 영어로 응답한다. 기여 지침의 스킬 본문 언어·안전 규칙·사용자 지정 산출물 언어는 유지한다.
- #741·#824·#812·#769·#708·#770은 **결정 전까지 paused로 생성**한다. 조사·측정 자체도 일괄 active 승인으로 해석하지 않는다. 재개에는 해당 범위의 실제 사용자 결정이 필요하다.
- 새 8개는 기존 Seed의 자식으로 연결하지 않는 독립 Seed이며 #835·#814 active, 나머지 6개 paused 생성이 확정됐다. 부분 선행 조건은 제약·완료조건에 기록하고 전체 Seed `depends_on`은 두지 않는다.
- 이 계획의 실행은 Seed 저작·검증과 기존 이슈의 경로 연결이다. 실제 기능 구현·실측·설치 갱신·PR 병합은 이 계획 문서 작성의 부수 효과가 아니다.

## 제품 작업 묶음과 실행 단위

작업 묶음은 계획·검토를 위한 분류다. 새로운 상위 Seed를 만들어 같은 요구나 별도 진척 상태를 중복 저장하지 않는다.

| 제품 작업 묶음 | 이슈와 산출물 | 완료·출시 단위 |
|---|---|---|
| 지침의 명료성과 언어 계약 | #835: 계약·의미 보존을 다루는 새 active Seed. #834: manifest 경로 한 문단을 고치는 이슈 작업 | 같은 정비 작업 묶음으로 계획하되 #834는 독립 원자 커밋. 네 플러그인 본문·안전/형식·관련 검사와 실제 manifest 경로를 검증 |
| 안전하고 검증되는 Seed 개발 흐름 | #814: 출처 보존 전이와 필요한 실제 소비 검증의 새 active Seed. #815: CI 편입 이슈 작업. #812: paused 성능 평가 Seed | 생애주기 보장과 CI는 독립 완료 가능. 성능 기준선·동등성 결정 전에는 최적화를 확정하지 않고, 채택 변경의 완료에는 board 회귀 CI 통과 요구 |
| 사고 스킬의 역할·실행 계약 | #793: 최신 역할 완료조건 1–5 감사 작업. #769: paused native substrate 경계 Seed. #770: paused 세 스킬 effort 평가 Seed | 역할 감사, Workflow 허용 결정, effort 유지/변경은 별도 완료 판정. 현재 Agent 실행을 Workflow 결정 대기로 막지 않음 |
| 지식 검색의 모델 적합성 | #708: paused vault-searcher 모델 평가 Seed | 세 검색 모드·후보 필터 후 실제 입력·규모 증가·품질로 pin 유지/변경/보류를 판정. 다른 사고 스킬 평가와 독립 |
| 회고 후보 안내 | #741: paused 넛지 Seed | 신호·임계값·세션 범위·opt-in/부재/오류 결정 후에만 해당 구현. 외부 session-close self-check는 별도 소유 범위 |
| 원문 기반 문서 편집 | #824: paused 편집 효용 Seed. 진행 draft PR #847을 선행 자료로 재사용 | 초기 자료를 다시 만들지 않고 미검증 효용·중요 재수정·반복·클린본·선택 복원과 최소 채택 범위를 판정 |

## Seed를 만들 범위와 만들지 않을 범위

| 이슈 | Seed 경로 또는 실행 방식 | 확정 상태 |
|---|---|---|
| #835 | `docs/specs/plugin-language-instructions.yaml` | 새 active. description 제외·네 플러그인 본문 전수·의미 보존 |
| #814 | `docs/specs/seed-lifecycle-residual-validation.yaml` | 새 active. 이전 정확 부모 파일·전체 commit·선택 항목의 출처 보존 강제와 실제 승인/소비의 잔여 보장 |
| #741 | `docs/specs/retro-nudge-design-validation.yaml` | 사용자 결정: paused |
| #824 | `docs/specs/document-editing-preflight.yaml` | 사용자 결정: paused. #847의 이미 수행한 초기 비교 제외 |
| #812 | `docs/specs/seed-board-performance-evaluation.yaml` | 사용자 결정: paused |
| #769 | `docs/specs/native-substrate-boundary-decision.yaml` | 사용자 결정: paused |
| #708 | `docs/specs/vault-searcher-model-evaluation.yaml` | 사용자 결정: paused |
| #770 | `docs/specs/skill-effort-evaluation.yaml` | 사용자 결정: paused |
| #834 | 이슈의 명확한 재현·한 문단 수정·경로 대조 | 새 Seed 없음 |
| #815 | 고정 CLI의 validate/test·양성/실패 주입·workflow/문서 정합 | 새 Seed 없음. 이미 확정된 CI 작업 |
| #793 | 최신 역할 계약 완료조건 1–5의 감사·입증된 갭만 수정 | 새 Seed 없음. 기존 Seed의 부분 검증 근거를 재사용 |

Seed 없는 명확한 작업도 next-goal의 이슈 후보로 처리할 수 있다. 현재 `thinking-tools/skills/next-goal/SKILL.md`는 이슈 묶음 선택과 Seed 없는 직접 출력을 허용한다. 모든 이슈에 active Seed가 있어야 다음 작업이 생긴다는 전제는 맞지 않는다. 복잡한 잔여 요구에 Seed가 있을 때 그 경로를 명시하면 요구·상태·관계가 함께 전달되는 것이다.

## 의존성: 전체 작업을 막는 엣지와 단계별 게이트를 구별

| 관계 | 실제 선행 조건 | 막지 않는 작업 | 기록 방식 제안 |
|---|---|---|---|
| #815 CI → #812 채택 변경 | 성능 변경을 완료 처리할 때 실제 board 회귀 CI가 통과해야 함 | #812의 재개 승인 후 기준선 측정·후보 검토는 CI 설치 완료를 기다릴 필요 없음 | #812 수용조건의 완료 게이트. 전체 Seed `depends_on`으로 묶지 않음 |
| #793 역할 감사 → #770의 expert-panel 최종 판단 | 평가 표본의 역할·입력·출력이 비교 가능한 계약을 준수해야 함 | 다른 두 스킬의 관측과 판정, 이미 준수 여부가 확인된 표본 | 평가 전제와 해당 표본의 기준. 세 스킬 전체를 차단하는 엣지 없음 |
| #769 경계 결정 → 미래 Workflow fan-out | 허용/금지 정책을 결정한 뒤에만 해당 후속 착수 | 현재 native Agent·worker·hook 계약 유지/검증, #793 역할 감사 | 미래 후속의 명시 착수 조건. 현재 8개 Seed 전체에 공통 선행 엣지 없음 |
| #771 전문가 resume | 이슈가 요구한 격리 실사용과 자기 이전 입장 재주입 비중·전체 비용 근거 | #793 감사·#770 일반 설정 평가 | 기존 조건부 백로그 유지. 이슈 종료·PR 병합 자체로 조건 충족 처리하지 않음 |
| #814 내부 구현 단계 | 현재 전이 재현 → 정확 출처 정책 확정 → 검증기 회귀 → 실제 승인·소비 검증 | #815 CI, #835 지침 정리 | 한 Seed 내부의 단계. 외부 local-harness/설치 검증은 해당 소유 범위와 권한을 따름 |

여기에는 새 Seed 전체의 착수를 반드시 막아야 한다고 입증된 Seed 간 의존성이 없다. 사용자가 새 8개를 독립 Seed로 두고 실제 단계 게이트를 각 제약·완료조건에 표현하는 구조를 확정했다. 이후 `depends_on`이 필요하다면 실제로 먼저 완료해야 하는 Seed인지 확인하고 해당 관계의 승인을 받는다.

## 통합과 재사용의 경계

- **#835/#834:** 지침 정비 계획은 함께 관리한다. #834는 재현·수정이 이미 분명한 문서 작업이라 별도 Seed의 저작·상태 관리 비용을 추가하지 않는다. 기존 언어 계약 Seed에 무관한 수용조건을 얹어야만 함께 출시할 수 있는 것은 아니다.
- **#815/#812:** board 품질이라는 공동 작업 묶음이다. CI는 런타임 변경을 제외하고 #812는 미측정이며 paused이므로 한 Seed로 합치면 승인과 완료 시점이 충돌한다.
- **#708/#770:** runtime/provider·선언/적용값·품질·전체 비용의 관측 양식은 공유한다. 검색 품질과 pin 판단, 사고 스킬 effort 판단은 서로 다른 목표·자료·승인 단위이므로 같은 Seed로 합치지 않는다. vault 자료가 없다는 이유로 다른 평가까지 막지 않는다.
- **#814/기존 graph Seed:** `docs/specs/seed-relations-graph.yaml`의 관련 metadata·Refine·관계 검증 증거를 재사용한다. 최신 세대 해석 등 과거 요구와 출처 보존 전이 정책을 한꺼번에 바꾸거나 기존 ID/승인/완료 근거를 새 요구에 복사하지 않는다. 구체적인 소비 시나리오의 중복은 저작 시 대조해 기존 항목과 새 항목의 소유권을 하나로 둔다.
- **#793/기존 delegated Seed:** `docs/specs/expert-panel-delegated-mode.yaml`의 `constraint-10`과 `acceptance-2`는 worker 역할·반환의 검증에 재사용한다. 기존 goal은 단일 worker 위임이고 `constraint-4`는 역할 pin을 이 Seed 때문에 바꾸지 않도록 제한한다. inline·격리·worker 전체의 감사 소유권을 자동으로 옮기거나 기존 goal을 확장하지 않는다.
- **복수 이슈가 실제로 하나의 요구를 구현할 경우:** 한 Seed의 각 수용조건과 구현 이슈를 대응시킬 수 있다. 현재 `issues.source` 한 개와 `issues.tracking` 목록으로 표현할 수 있어 새 issue 배열이나 호환 스키마를 추가할 필요는 없다. 이번 후보에는 승인·완료 판정을 같이 해야 할 만큼 같은 목표인 두 이슈가 확인되지 않았다.

## 진행 중인 PR과 조건부 백로그

- #844는 PR #845가 JSON/mtime 경합을, #846이 생성 도중 수정의 신선도를 처리한다. #826은 PR #841, #817은 PR #843, #762는 PR #842 범위를 중복 명세화하지 않는다. #762의 기존 Seed는 closed/completed이며 이슈/PR OPEN으로 재활성화하지 않는다.
- #824의 draft PR #847(`a46b7ddac917db65d0799c74e7dfc56cad2be9d6`)은 `docs/design/document-editing-minimal-proposal.md` 한 파일을 추가한다. 초기 HTML 6개와 의미 체크 89 충족/1 부분은 PR이 기록한 관측이며 이번 계획에서 독립 재실증한 결과는 아니다. 사용자 중요 재수정 감소·반복 안정성·클린본·실질적 제외 후 선택 복원은 미검증이다. 문서 제출/병합을 개발 승인이나 효용 확정으로 쓰지 않는다.
- #750·#822·#827 핵심 수정·#832 소스 수정은 새 구현에서 제외한다. #832 실제 리뷰 실행과 #827 도구 부재 fallback의 미확인 한계는 지원 완료로 확대하지 않는다. 상태 정리는 완료 근거를 보존하는 별도 업무다.
- #771, #756의 실제 마일스톤 관리 의사, #732의 남은 fence 엣지/성능 근거, #689의 오검출 누적 3건은 기존 착수 조건을 유지한다. 과거 수치·최근 댓글 부재·이슈 상태로 조건 충족을 추정하지 않는다.
- 기존 paused doctor·build-spec 통합·discussion Seed는 이번 OPEN 이슈 범위 밖이다. 재개나 과거 `/wrap` 복원을 승인한 것으로 해석하지 않는다.

## 저작·연결·검증 순서

1. 사용자가 확정한 단위와 관계를 사용한다. #835/#814 active와 paused 6개를 구별한다.
2. 승인된 8개 Seed에 실제 사용자 답변·출처·제약·항목별 관측 완료조건을 기록한다. 기존 Seed와 겹치는 요구는 복사하지 않고 해당 검증을 재사용한다. 인터뷰/게이트/검토 결과를 만들지 않는다.
3. 생애주기·관계·템플릿 검증을 실행하고, active 후보의 eligibility 및 paused 제외가 의도대로인지 확인한다. 기존 Seed의 ID·내용·역사적 근거를 보존한다.
4. 각 이슈에 실제 Seed 경로와 상태를 연결한다. Seed 없는 #834/#815/#793은 이슈 작업이라는 실행 경로를 명확히 하며 존재하지 않는 Seed를 링크하지 않는다. 이슈 본문을 수정할 때는 직전에 재조회해 기존 내용과 동시 변경을 보존한다.
5. 공유할 Seed·계획 변경을 원자 커밋으로 검토할 수 있게 묶는다. 공개 링크가 아직 브랜치/PR 기준이라면 main에서 사용 가능한 상태와 구분한다. 병합·설치 적용을 자동으로 수행하지 않는다.

## 검토 근거와 한계

원 이슈·현재 소스·기존 Seed metadata 및 관련 본문을 대조했고, 별도 읽기 전용 에이전트가 통합 범위와 차단 조건을 검토했다. 이 검토는 기능 구현·CI 실행·모델 비용/품질 실측을 수행한 결과가 아니다.

- [#834](https://github.com/Lyainc/claude-kit/issues/834), [#815](https://github.com/Lyainc/claude-kit/issues/815), [#812](https://github.com/Lyainc/claude-kit/issues/812): 명확한 문서/CI 작업과 미결정 성능 평가의 구분.
- [#814](https://github.com/Lyainc/claude-kit/issues/814), `thinking-tools/scripts/seed-lifecycle.py`의 부모 변경 승인 검사, 기존 graph Seed: 출처 보존의 신규 보장과 기존 검증 구분.
- [#793](https://github.com/Lyainc/claude-kit/issues/793), 기존 delegated Seed `constraint-4`/`constraint-10`/`acceptance-2`: 전체 역할 감사와 worker 요구의 부분 겹침.
- [#708](https://github.com/Lyainc/claude-kit/issues/708), [#770](https://github.com/Lyainc/claude-kit/issues/770): 공통 관측 양식과 별도 설정 판단.
- [PR #847](https://github.com/Lyainc/claude-kit/pull/847), 해당 commit의 편집 제안 문서: 새 진행 작업 반영.
- `thinking-tools/skills/build-spec/reference.md` §8 및 `thinking-tools/reference/seed-lifecycle.md`: 관계 선택·승인·생애주기 경계의 정본.
