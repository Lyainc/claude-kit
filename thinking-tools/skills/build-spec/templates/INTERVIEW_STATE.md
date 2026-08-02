# Build Spec — Interview State Template

STATE 블록의 정확한 필드는 [SKILL.md](../SKILL.md)의 STATE Block Contract 섹션이 유일 소스다 —
필드가 바뀔 때마다 이 파일까지 고칠 필요가 없도록, 여기서는 필드를 다시 나열하지 않는다.

저장 트리거·복원 절차 등 `unknown-discovery`와 공유하는 계약은
[../../../reference/interview-state.md](../../../reference/interview-state.md) 참고.

## File Persistence Format

저장 경로: `docs/specs/{target}/state.md`

```markdown
---
skill: build-spec
target: {name}
domain: {tech|biz|creative}
saved_at: {ISO-datetime}
---

<!-- STATE:CHECKPOINT -->
...세션의 현재 STATE 블록을 SKILL.md 형식 그대로 붙여넣는다 (필드를 여기서 다시 정의하지 않음)...
<!-- /STATE -->

## Discoveries so far

### Goal
{accumulated goal clarity notes}

### Constraints identified
{list of constraints found so far}

### Success criteria identified
{list of success criteria found so far}

### Context (brownfield)
{integration points and existing stack notes}
```

## Restoration

저장 트리거·일반 복원 단계는 [../../../reference/interview-state.md](../../../reference/interview-state.md) 참고.
build-spec 고유: 복원 시 "이전 인터뷰를 이어서 시작합니다. Round {N}부터 재개해요."를 먼저 표시한다.
