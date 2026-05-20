# Spec First — Examples

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
- G1: 단일 문장 표현 가능 → Y
- G2: 측정 가능/관찰 가능 → N (무엇이 "가벼운가" 불명확)
- G3: 주요 수혜자 → Y (개발자/터미널 사용자)
- G4: 동기 이해 가능 → Y (기존 앱 무거움)
- Goal clarity: 3/4 = 0.75 ✓

**Phase 1 Round 2** [Success, Q: "어떤 상태가 되면 완성됐다고 할 수 있나요?"]:

> "task add '할 일', task list, task done 1 이 세 가지 커맨드가 동작하면 돼요."

**Scoring**:
- S1: verifiable AC → Y
- S2: 범위 명확 → Y (세 커맨드로 한정)
- S3: 목표와 연결 → Y
- S4: 측정 방법 → Y (커맨드 실행 테스트)
- Success clarity: 4/4 = 1.0 → capped at 0.90

**Phase 1 Round 3** [Constraint, Q: "기술 스택이나 환경 제약이 있나요?"]:

> "Python이면 좋겠어요. pip install로 배포하고 싶어서요."

**Scoring**:
- C1: hard constraint → Y (Python)
- C2: hard/soft 구분 → Y (pip = hard, 다른 배포 방식 = soft)
- C3: 근거 → Y (pip 배포)
- Constraint clarity: 3/3 = 1.0 → capped at 0.90

**Gate Check** (Round 3):
```
[Gate Check] Ambiguity: 0.16 (target ≤ 0.20) ✓
  Goal: 75% ✓ | Constraint: 90% ✓ | Success: 90% ✓
  consecutive_gate: 1
```
(1 − (0.75×0.40 + 0.90×0.30 + 0.90×0.30) = 0.16)

**Phase 1 Round 4** [Follow-up Goal, Q: "로컬 파일에 저장하면 될까요?"]:

> "네, ~/.tasks.json 같은 파일이면 충분해요."

Goal clarity: 0.90 (G2 Y로 전환 → 4/4 = 1.0 → cap 0.90)

**Gate Check** (Round 4):
```
[Gate Check] Ambiguity: 0.10 (target ≤ 0.20) ✓
  Goal: 90% ✓ | Constraint: 90% ✓ | Success: 90% ✓
  consecutive_gate: 2 → Gate OPEN
```
(1 − (0.90×0.40 + 0.90×0.30 + 0.90×0.30) = 0.10)

**Phase 3 — Seed 생성** (`docs/specs/task-cli-tool.yaml`):

```yaml
<!-- Output conforms to thinking-tools/reference/common-schema.md -->
---
skill: spec-first
version: 0.1.0
generated: 2026-05-19
input:
  target: task-cli-tool
  options: []
output:
  type: spec
  structure: templates/SEED_SPEC.yaml

# spec-first extensions
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
  - id: c1
    type: technical
    description: Python으로 구현
    hard: true
    rationale: pip install로 배포 목적
  - id: c2
    type: technical
    description: 데이터 저장소는 ~/.tasks.json
    hard: true
    rationale: 단순성, 외부 DB 없음

success_criteria:
  - id: ac1
    description: "`task add '할 일'` 명령으로 항목 추가"
    verifiable: true
    measurable_via: 커맨드 실행 후 파일 확인
  - id: ac2
    description: "`task list`로 전체 목록 출력"
    verifiable: true
    measurable_via: stdout 확인
  - id: ac3
    description: "`task done 1`로 항목 완료 처리"
    verifiable: true
    measurable_via: 상태 변경 확인

context:
  existing_stack: []
  dependencies: []

ambiguity:
  overall: 0.10
  gate_passed: true
  breakdown:
    goal: 0.90
    constraint: 0.90
    success: 0.90
    context: null

metadata:
  interview_rounds: 4
  questions_asked: 5
  generated_by: thinking-tools/spec-first
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

Context clarity: 0.60 ✓ (integration point 파악)

*... 이후 라운드에서 이메일 vs 인앱 알림 채널 결정, 성공 기준 수립 ...*

**Ambiguity 0.65 → 0.17** · Round 7 · Gate 통과

**Seed**: `docs/specs/user-notification-system.yaml`

알림 시스템 도입 전 `/unknown-discovery`로 Seed 구멍 점검 추천:
```
→ unknown-discovery: 알림 전달 실패 처리, 알림 과부하 방지(rate limiting) 누락 발견
```
