#!/usr/bin/env bash
# thinking-tools PostToolUse(Bash) hook — build-spec Seed metadata-first guard, output side.
# Claude registers it in .claude-plugin/plugin.json; Codex in hooks/codex-hooks.json, where it
# runs only once the user trusts the hook.
#
# seed-read-guard.sh judges the command text before it runs, so a read built by command
# substitution (`for f in $(git ls-files docs); do cat "$f"; done`) names no Seed and passes. This
# hook inspects the tool OUTPUT instead: when it carries a Seed body and the transcript shows no
# `seed-relations.py metadata` for that Seed (or the Seed cannot be identified), it returns block
# feedback telling the model not to apply the body (reference/seed-lifecycle.md §발견과 소비).
# The command has already run, so this cannot stop the read, only the application. Signature
# matching and Seed identification are heuristics and never claim complete coverage.
#
# Output contract (same shape on both runtimes): stdout JSON {"decision":"block","reason":...}.
# Fails open in every direction: opt-out set, no jq, no python3, empty/unparseable payload,
# unreadable transcript → exit 0 silent. Decision logic + self-test: scripts/seed-read-check.py --post.
#
# Kill switch: CLAUDE_KIT_SEED_READ_GUARD=off disables it entirely.

set -uo pipefail

[ "${CLAUDE_KIT_SEED_READ_GUARD:-}" = "off" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

payload=$(cat 2>/dev/null || true)
[ -z "$payload" ] && exit 0

# Fast exit: a Seed body always carries both top-level keys (or the amendment-contract header).
case "$payload" in
  *lifecycle:*success_criteria:*|*success_criteria:*lifecycle:*|*"AMENDMENT CONTRACT"*) ;;
  *) exit 0 ;;
esac

reason=$(printf '%s' "$payload" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seed-read-check.py" --post 2>/dev/null || true)
[ -z "$reason" ] && exit 0

jq -nc --arg reason "$reason" '{decision:"block", reason:$reason}'

exit 0
