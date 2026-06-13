#!/usr/bin/env bash
# claude-kit work-rules — deterministic task-end checklist reminder (Stop hook).
#
# #216 c5 tier-2 (SOFT): at task end, remind the main agent to run the rules/ checklist
# before finishing, so the self-check can't be silently skipped. This is the honest soft
# form of "skip 차단": a reminder that ALWAYS fires when rule-governed work is pending —
# not a hard block (hard enforcement is the CI tier: scripts/check-*.py + external linters).
#
# Why deterministic shell (not a prompt hook): a prompt-based Stop hook loops, because every
# LLM turn re-fires Stop (the vault-bridge lesson). This script emits a non-blocking
# systemMessage ONLY when governed files are dirty — no LLM call, no decision:block, no loop.
#
# Wiring (per-developer, by design): .claude/ is gitignored in this repo, so this handler is
# committed under scripts/ (shared, no external-orchestrator dependency — c3) but activated locally by adding to your own
# .claude/settings.json (see rules/RULES.md §4 "How the reminder hook is wired"):
#   { "hooks": { "Stop": [ { "hooks": [ { "type": "command",
#       "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/rules-checklist-hook.sh\"" } ] } ] } }

set -euo pipefail

# Tolerate a missing jq: emit nothing rather than erroring on every Stop under `set -e`.
command -v jq >/dev/null 2>&1 || exit 0

# Kill switch.
[ "${CLAUDE_KIT_RULES_HOOK_DISABLE:-0}" = "1" ] && exit 0

payload=$(cat 2>/dev/null || true)

# Resolve repo root: $CLAUDE_PROJECT_DIR (set for project hooks) > payload .cwd > git from PWD.
root="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$root" ]; then
  root=$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null || true)
fi
if [ -z "$root" ] || [ ! -d "$root" ]; then
  root=$(git rev-parse --show-toplevel 2>/dev/null || true)
fi
[ -z "$root" ] && exit 0

# Is there uncommitted work in rule-GOVERNED paths? (deterministic; no work -> no reminder).
# Governed: scripts/, rules/, CI workflows, plugin manifests, and skill/agent markdown bodies.
dirty=$(git -C "$root" status --porcelain 2>/dev/null \
  | grep -aE '(^| )(scripts/|rules/|feedback-loop/|dev-harness/|\.github/workflows/|.*/skills/.*\.md|.*/agents/.*\.md|.*plugin\.json|\.claude-plugin/marketplace\.json)' \
  | head -1 || true)

[ -z "$dirty" ] && exit 0

msg="작업 끝 — rules/RULES.md 작업끝 체크리스트 확인했나요? 하드 게이트(커밋 전): python3 scripts/check-*.py --self-test 및 실모드, 외부 린터(scripts/run-linters.py). skip하지 마세요 — 통과 못 하면 CI에서 차단돼요."
jq -nc --arg m "$msg" '{systemMessage: $m}'

exit 0
