#!/usr/bin/env bash
# thinking-tools SessionStart hook — first-run onboarding hint (#117).
#
# Surfaces a one-time, deterministic onboarding hint so a new user discovers what
# claude-kit can do without reading the README first. Hosted in thinking-tools
# (not vault-bridge) because it's the most-likely first install for the target
# audience and has no vault dependency to early-exit on. Marketplace repos can't
# register hooks, and C-2 forbids a thin 4th "welcome" plugin (output-layer ADR),
# so the hint rides the entry plugin's own SessionStart. Zero per-turn LLM cost.
#
# Grace: shown on the first 3 sessions, then silent — the env kill switch is the
# explicit opt-out. State is a single integer in one file.
# ponytail: single counter file, no JSON schema, no dismiss-state — kill switch covers opt-out.
#
# Kill switch: CLAUDE_KIT_WELCOME_DISABLE=1 skips entirely.

set -uo pipefail

[ "${CLAUDE_KIT_WELCOME_DISABLE:-}" = "1" ] && exit 0

state_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.claude-kit"
counter_file="${state_dir}/welcome-count"

count=0
if [ -f "$counter_file" ]; then
  count=$(cat "$counter_file" 2>/dev/null || echo 0)
  case "$count" in ''|*[!0-9]*) count=0 ;; esac
fi

# Already shown enough times — stay silent.
[ "$count" -ge 3 ] && exit 0

mkdir -p "$state_dir" 2>/dev/null || true
printf '%d' "$((count + 1))" > "$counter_file" 2>/dev/null || true

# SessionStart has NO user-visible message channel — top-level `systemMessage` is
# ignored here (verified against code.claude.com/docs/hooks; it only surfaces for
# PreToolUse/PostToolUse). The supported channel is `additionalContext`, which
# injects into Claude's context; Claude then surfaces the hint to the user only
# when it fits (fresh session / "뭐 할 수 있어?"), which also honors the design's
# "no forced action" principle. Static text, no double-quotes → hand-written JSON,
# no jq dependency.
msg='{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[claude-kit onboarding hint] claude-kit plugins are installed. If this session is starting fresh without a specific task, or the user asks what they can do, briefly surface these work-flow entry points to the user in Korean (do NOT force it if they already have a task in hand): 사고·기획 → build-spec, diverse-sampling, unknown-discovery; 검토·반증 → expert-panel, adversarial-review, doc-polish; 기록·지식관리 → vault-save, wiki. Full table: README 무엇부터 써볼까 섹션. The user can silence this with CLAUDE_KIT_WELCOME_DISABLE=1."}}'
printf '%s\n' "$msg"

exit 0
