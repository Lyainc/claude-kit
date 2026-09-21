#!/usr/bin/env bash
# thinking-tools PreToolUse(Write|Edit) hook — build-spec Seed append guard.
#
# Denies the one edit shape that turns a Seed into a changelog: the old text survives whole
# inside the new text (nothing replaced, only added) AND the added part reads like a work log
# (a date, past-tense reporting, review provenance). Replacing a field's value — the amendment
# the Seed template's header actually sanctions — never matches, so correcting the spec stays
# frictionless while journaling in it stops.
#
# Why a hook and not another sentence in a SKILL.md: the session doing the appending is a
# `/goal` loop in someone else's repo, and the only surfaces it reads are the Seed file and its
# own completion condition. build-spec's SKILL.md is invisible to it. The same repo already
# shows what doc-only rules achieve here — Phase 3's "if file exists append -v2" produced zero
# -v2 files across 18 commits to one Seed.
#
# Fails open in every direction: opt-out set, no jq, no python3, unparseable payload,
# unreadable target → exit 0 silent. Decision logic + self-test: scripts/seed-append-check.py.
#
# Kill switch: CLAUDE_KIT_SEED_GUARD=off disables it entirely.

set -uo pipefail

[ "${CLAUDE_KIT_SEED_GUARD:-}" = "off" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

payload=$(cat 2>/dev/null || true)
[ -z "$payload" ] && exit 0

reason=$(printf '%s' "$payload" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/seed-append-check.py" 2>/dev/null || true)
[ -z "$reason" ] && exit 0

# permissionDecision must nest under hookSpecificOutput (documented PreToolUse schema) —
# a top-level one is silently ignored.
jq -nc --arg reason "$reason" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse", permissionDecision:"deny", permissionDecisionReason:$reason}, systemMessage:($reason + " (CLAUDE_KIT_SEED_GUARD=off 로 끌 수 있어요.)")}'

exit 0
