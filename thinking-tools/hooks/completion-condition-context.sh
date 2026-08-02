#!/usr/bin/env bash
# thinking-tools PreToolUse(Skill) hook — completion-condition candidate-pool injection (#517).
#
# Fires only when the `completion-condition` skill is invoked, and pushes next-candidate.py's
# output into the model's context as additionalContext — unrequested.
#
# Why injection rather than an instruction to go look. Phase 1 ranks "this session's high-ROI
# follow-ups", a pool that contains only what this session produced. A session that just
# finished polishing one module leaves that module's nits behind, so the chain decays the
# further it runs: ranking nits by ROI still returns a nit. That is not a judgment failure and
# no better sentence fixes it — the comparison set is empty by construction. An instruction
# ("also check the backlog") is one more thing that has to be remembered at the moment it is
# least likely to be; arriving data has to be read.
#
# Data only — the payload carries what the skill cannot compute (chain depth, the backlog) and
# nothing about what to do with it. The impact floor, the re-pick rule, and the
# disclose-your-pool rule live in SKILL.md and only there; shipping them here too would be
# duplication across the boundary, not inheritance.
#
# Never blocks and never grants permission: additionalContext only, no permissionDecision —
# returning "allow" here would silently skip whatever permission handling the Skill call would
# otherwise get, which this hook has no business deciding.
#
# Fails open in every direction: opt-out set, no jq, wrong skill, no python3, empty report → exit 0 silent.
#
# Kill switch: CLAUDE_KIT_NEXT_CANDIDATE_DISABLE=1 skips entirely.

set -uo pipefail

[ "${CLAUDE_KIT_NEXT_CANDIDATE_DISABLE:-}" = "1" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0

payload=$(cat 2>/dev/null || true)
[ -z "$payload" ] && exit 0

tool=$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null || true)
[ "$tool" = "Skill" ] || exit 0

# Plugin skills arrive qualified (`thinking-tools:completion-condition`); the bare form is
# accepted too so a direct invocation or a future re-host does not silently stop firing.
skill=$(printf '%s' "$payload" | jq -r '.tool_input.skill_name // .tool_input.skill // empty' 2>/dev/null || true)
case "$skill" in
  thinking-tools:completion-condition|completion-condition) ;;
  *) exit 0 ;;
esac

cwd=$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null || true)
[ -z "$cwd" ] && cwd=$(pwd)

command -v python3 >/dev/null 2>&1 || exit 0
report=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/next-candidate.py" --cwd "$cwd" 2>/dev/null || true)
[ -z "$report" ] && exit 0

ctx="[completion-condition 후보 풀 — 훅이 자동 주입, 요청해서 받은 게 아니에요]

${report}

Phase 1은 '이번 세션의 후속'만 보고 후보를 고르는데, 그 풀에는 이번 세션이 만든 것만 들어 있어요.
위는 그 바깥의 비교집합이라 Phase 1이 스스로 계산할 수 없는 데이터예요 — 판정 기준은 SKILL.md에 있어요."

jq -nc --arg c "$ctx" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$c}}'

exit 0
