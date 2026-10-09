# Build Spec — Examples

아래 점수·계산은 채점 설명이에요. 실제 사용자 대면 Gate Check는 숫자 없이 ✓/✗를
표시하고, 점수와 consecutive_gate는 STATE에만 기록해요. 질문 제출이나 무응답은 답변이
아니므로 각 예시의 인용된 사용자 답변을 실제로 받은 뒤에만 다음 단계로 넘어가요.

## Example 1: Greenfield Tech — Task CLI Tool

**입력**: "task CLI를 만들고 싶어. 뭐가 필요한지 모르겠어."

---

**Phase 0**:
- Domain: Tech (CLI 언급)
- Brownfield detection: 파일 없음 → greenfield
- Weights: Goal 0.40, Constraint 0.30, Success 0.30

**Phase 1 Round 1** [Goal, Q: "어떤 문제를 해결하려고 하나요?"]:

> "터미널에서 todo를 관리하고 싶어요. 기존 앱들이 너무 무거워서."

**Scoring**:
- goal-check-1: 단일 문장 표현 가능 → Y
- goal-check-2: 측정 가능/관찰 가능 → N (무엇이 "가벼운가" 불명확)
- goal-check-3: 주요 수혜자 → Y (개발자/터미널 사용자)
- goal-check-4: 동기 이해 가능 → Y (기존 앱 무거움)
- Goal clarity: 3/4 = 0.75 ✓

**Phase 1 Round 2** [Success, Q: "어떤 상태가 되면 완성됐다고 할 수 있나요?"]:

> "task add '할 일', task list, task done 1 이 세 가지 커맨드가 동작하면 돼요."

**Scoring**:
- success-check-1: verifiable AC → Y
- success-check-2: 범위 명확 → Y (세 커맨드로 한정)
- success-check-3: 목표와 연결 → Y
- success-check-4: 측정 방법 → Y (커맨드 실행 테스트)
- Success clarity: 4/4 = 1.0 → capped at 0.90

**Phase 1 Round 3** [Constraint, Q: "기술 스택이나 환경 제약이 있나요?"]:

> "Python과 pip install 배포는 꼭 지켜 주세요. 다른 스택이나 배포 방식은 제외할게요."

**Scoring**:
- constraint-check-1: hard constraint → Y (Python)
- constraint-check-2: hard/soft 구분 → Y (사용자가 Python·pip를 모두 hard로 확정)
- constraint-check-3: 근거 → Y (pip 배포)
- Constraint clarity: 3/3 = 1.0 → capped at 0.90

**Gate Check** (Round 3):
```
[Gate Check] 게이트: 통과 임박
  Goal: ✓ | Constraint: ✓ | Success: ✓
```
(1 − (0.75×0.40 + 0.90×0.30 + 0.90×0.30) = 0.16)
격리 판정이 같은 체크리스트 결과를 반환한 경우 STATE의 consecutive_gate는 1이에요.

**Phase 1 Round 4** [Follow-up Goal, Q: "로컬 파일에 저장하면 될까요?"]:

> "네, ~/.tasks.json 같은 파일이면 충분해요."

Goal clarity: 0.90 (goal-check-2 Y로 전환 → 4/4 = 1.0 → cap 0.90)

**Gate Check** (Round 4):
```
[Gate Check] 게이트: 통과 임박
  Goal: ✓ | Constraint: ✓ | Success: ✓
```
(1 − (0.90×0.40 + 0.90×0.30 + 0.90×0.30) = 0.10)
격리 판정이 같은 결과를 반환해 두 번째 연속 통과하면 Gate가 열려요. 격리 호출을 받을 수
없을 때는 경고와 scoring_isolated: false를 표시해요. Phase 2.5는 1회 실행하고 실제
채택·기각 답변을 기다려요. 아래 YAML은 작성 당시 형식의 역사적 예시이며, 신규 Seed는
현재 SEED_SPEC.yaml의 lifecycle·relations.version: 2·amendment header를 모두 사용해요.
사용자 활성화 승인 없는 조기 출력은 paused로 남겨요.

**Phase 3 — Seed 생성** (`docs/specs/task-cli-tool.yaml`):

```yaml
---
# Output conforms to thinking-tools/reference/common-schema.md
skill: build-spec
schema_version: 1
version: 0.1.0
generated: 2026-05-19
input:
  target: task-cli-tool
  options: []
output:
  type: spec
  structure: templates/SEED_SPEC.yaml

# build-spec extensions
spec_version: 1
created: 2026-05-19
target: task-cli-tool
domain: tech
brownfield: false
refine_generation: 0

goal:
  statement: "터미널에서 todo를 가볍게 관리할 수 있는 Python CLI 도구"
  clarity_score: 0.90

constraints:
  - id: constraint-1
    type: technical
    description: Python으로 구현
    hard: true
    rationale: pip install로 배포 목적
  - id: constraint-2
    type: technical
    description: 데이터 저장소는 ~/.tasks.json
    hard: true
    rationale: 단순성, 외부 DB 없음

success_criteria:
  - id: acceptance-1
    description: "`task add '할 일'` 명령으로 항목 추가"
    verifiable: true
    measurable_via: 커맨드 실행 후 파일 확인
  - id: acceptance-2
    description: "`task list`로 전체 목록 출력"
    verifiable: true
    measurable_via: stdout 확인
  - id: acceptance-3
    description: "`task done 1`로 항목 완료 처리"
    verifiable: true
    measurable_via: 상태 변경 확인

context:
  existing_stack: []
  dependencies: []

issues:
  source: null        # session did not start from a GitHub issue
  tracking: []

relations:
  parent: null
  refines: []
  link_reason: null   # no parent, nothing to explain
  depends_on: []
  children: []

ambiguity:
  overall: 0.10
  gate_passed: true

clarity_breakdown:    # per-dimension CLARITY score
  goal: 0.90
  constraint: 0.90
  success: 0.90
  context: null

metadata:
  interview_rounds: 4
  questions_asked: 5
  generated_by: thinking-tools/build-spec
---
```

---

## Example 2: Brownfield Tech — 알림 기능 추가

**입력**: "이 repo에 사용자 알림 기능 추가하고 싶어"

---

**Phase 0**:
- Domain: Tech
- Brownfield detection: `package.json` 발견 → AskUserQuestion: "기존 프로젝트에 추가인가요?"
  - 답: "네" → brownfield 확정, Context Clarity 활성화
- `package.json` 읽기: `{"name": "user-dashboard", "dependencies": {"express": "^4.18"}}`
- 컨텍스트 주입: "현재 프로젝트: user-dashboard (Express 기반 대시보드). 의존성: express."
- Weights: Goal 0.34, Constraint 0.26, Success 0.25, Context 0.15

**Phase 1 Round 1** [Goal]:
> "로그인 알림과 새 메시지 알림 두 가지가 필요해요."

Goal clarity: 0.50 (아직 "누가 받나", "어떤 채널로"가 불명확)

**Phase 1 Round 2** [Context]:
> "기존 User 모델에 notification_settings 필드를 추가하면 될 것 같아요."

Context clarity: 1/3 (integration point만 확인; 영향 컴포넌트·충돌은 추가 확인 필요)

*... 이후 라운드에서 이메일 vs 인앱 알림 채널 결정, 성공 기준 수립 ...*

코드와 열린·닫힌 백로그를 확인하고 모든 활성 차원의 floor 및 두 라운드 연속 통과를
충족한 뒤 격리 Gate 판정을 받아요. 숫자 요약만으로 Gate를 열지 않아요.

**Seed**: `docs/specs/user-notification-system.yaml`

게이트 뒤 Phase 2.5에서 전달 실패 처리나 알림 과부하 같은 미질문 항목을 한 번 점검해요.
선행 unknown-discovery 리포트를 feedback으로 받은 경우에는 중복 패스를 건너뛰어요.


## Quick Start (moved from SKILL.md)

```
User: "task CLI를 만들고 싶어. 뭐가 필요한지 모르겠어."

→ Phase 0: domain=Tech, greenfield 확인, 열린·닫힌 백로그 조회
→ Phase 1: Goal부터 질문, 실제 답변을 받은 뒤 체크리스트 채점
→ Phase 1: 최저 clarity 차원의 제약·성공 조건과 미해결 답변 확인
→ Phase 2: 모든 활성 floor와 2회 연속 Gate 통과, 격리 실패 시 명시적 fallback
→ Phase 2.5: 맹점 패스 1회, 채택·기각 답변 대기
→ Phase 3: 현재 템플릿으로 Seed 생성, 승인 근거와 lifecycle 기록·검증
→ 이슈 저작 요청이 있으면 issue-raise에 인계; 생성 승인은 별도 대기
```

## Korean I/O Directive (moved from SKILL.md)

모든 사용자 대면 출력(질문, Gate Check 표시, Seed 요약)은 **한국어**로 작성합니다.
STATE 블록 키와 YAML 필드명은 영어를 유지합니다.
사용자가 영어로 작성한 경우 영어로 응답합니다.
