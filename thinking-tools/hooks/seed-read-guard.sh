#!/usr/bin/env bash
# thinking-tools PreToolUse(Read|Bash) hook — build-spec Seed metadata-first read guard.
# Claude registers it in .claude-plugin/plugin.json; Codex (Bash only) in hooks/codex-hooks.json,
# where it runs only once the user trusts the hook.
#
# Denies a Read/cat of a build-spec Seed body until `seed-relations.py metadata` ran for that
# Seed in the same transcript (reference/seed-lifecycle.md §발견과 소비). A direct read bypasses
# that contract, and the Seed's own header cannot enforce it because the header is only visible
# after the body is read. At most one deny per Seed per transcript, zero when metadata already ran.
# Bash detection is heuristic (reader commands, cd tracking, glob expansion) and never claims to
# block every read (seed-residual constraint-3).
#
# Fails open in every direction: opt-out set, no jq, no python3, empty/unparseable payload,
# unreadable transcript → exit 0 silent. Decision logic + self-test: scripts/seed-read-check.py.
#
# Kill switch: CLAUDE_KIT_SEED_READ_GUARD=off disables it entirely.

set -uo pipefail

[ "${CLAUDE_KIT_SEED_READ_GUARD:-}" = "off" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

payload=$(cat 2>/dev/null || true)
[ -z "$payload" ] && exit 0

# Fast exit: no yaml/yml mention anywhere in the payload means no Seed can be read.
case "$payload" in
  *.yaml*|*.yml*) ;;
  *) exit 0 ;;
esac

reason=$(printf '%s' "$payload" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seed-read-check.py" 2>/dev/null || true)
[ -z "$reason" ] && exit 0

jq -nc --arg reason "$reason" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason:$reason}}'

exit 0
