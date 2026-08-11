#!/usr/bin/env bash
# claude-kit work-rules — worktree isolation guard (PreToolUse Write|Edit hook, #594).
#
# Enforces rules/RULES.md §1 "Concurrent work goes in an isolated git worktree (#234)"
# — the claude-kit-concrete form of machine work-rule P1. Until #594 that rule had NO
# deterministic guard at all: enforcement was the prose rule plus the §4 self-check.
#
# WHAT IT CATCHES (and what it does not). #594's 8th recorded near-miss was a NEW shape:
# not two sessions colliding, but ONE session that never isolated itself — it edited the
# shared MAIN CHECKOUT on the DEFAULT BRANCH for several commits, and was found only by a
# stray `git status --short`. No hook, no warning, nothing. That shape IS deterministically
# detectable, which is why it gets a guard while P1's general question stays SOFT:
#   "is another session working this repo right now?"  → judgment, NOT detectable (SOFT).
#   "am I writing the main checkout on its default branch?" → two git commands, no judgment.
# So this guard answers only the second question. It is the self-isolation half of P1;
# the sibling-occupancy half is #594's claim-file proposal and is deliberately NOT here.
#
# KNOWN GAP (deliberate, same honest-slip threat model as the sibling guards): a write to
# the main checkout while it sits on a FEATURE branch is not flagged. That is #594's
# original incident shape, but it is also ordinary solo work in the main checkout, so
# flagging it would fire on the legitimate case with no way to tell them apart. Closing it
# needs the claim file (who else is live right now), not a branch comparison.
#
# Fires on every PreToolUse Write|Edit. It acts ONLY when the target file resolves inside a
# MAIN checkout (git-dir == git-common-dir; a linked worktree's differ) that is currently on
# its DEFAULT branch (origin/HEAD, else main, else master), and only for a path git does not
# ignore. Deterministic shell — zero per-turn LLM cost (CON-2). Fails OPEN when jq or git is
# absent (a missing tool must never block a legitimate write).
#
# Mode (env): CLAUDE_KIT_WORKTREE_GUARD = warn (default) | enforce | off.
#   warn    — allow, emit a systemMessage + stderr warning. DEFAULT, because P1 is SOFT:
#             a false block costs a real session (same reasoning as worktree-collision-warn).
#   enforce — deny the write (permissionDecision:deny) + systemMessage.
#   off     — no-op.
#
# The warning fires ONCE per (session, repo): the isolation decision is made once, and a
# per-write repeat trains the reader to ignore exactly the line that matters. A payload
# without `.session_id` gets no dedup (warn every time) rather than a silent guard.
#
# Wiring (per-developer; .claude/ is gitignored — NOT auto-registered):
#   { "hooks": { "PreToolUse": [ { "matcher": "Write|Edit", "hooks": [ { "type": "command",
#       "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/worktree-isolation-guard.sh\"" } ] } ] } }
# Wire it in the MAIN checkout's .claude/settings.json — that is the checkout it protects.

set -uo pipefail

MODE="${CLAUDE_KIT_WORKTREE_GUARD:-warn}"
[ "$MODE" = "off" ] && exit 0

# jq / git absent → fail open (never block a write because a tool is missing).
command -v jq >/dev/null 2>&1 || exit 0
command -v git >/dev/null 2>&1 || exit 0

PAYLOAD="$(cat 2>/dev/null || printf '{}')"
[ -n "$PAYLOAD" ] || PAYLOAD='{}'

RAW_PATH="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
[ -n "$RAW_PATH" ] || exit 0

CWD="$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null || true)"
[ -n "$CWD" ] || CWD="$PWD"

# Expand ~, then resolve a relative path against the session cwd.
ABS="${RAW_PATH/#\~/$HOME}"
case "$ABS" in /*) ;; *) ABS="$CWD/$ABS" ;; esac

# The file may not exist yet (Write creates it), and neither may its parent chain — walk up
# to the nearest existing directory, which is what git must be asked about.
DIR="$(dirname "$ABS")"
while [ ! -d "$DIR" ] && [ "$DIR" != "/" ]; do DIR="$(dirname "$DIR")"; done
[ -d "$DIR" ] || exit 0

# Normalize both git dirs the same way (cd + pwd -P) so a symlinked TMPDIR or repo path
# cannot make an identical pair compare unequal.
GITDIR="$(cd "$DIR" 2>/dev/null && cd "$(git rev-parse --git-dir 2>/dev/null)" 2>/dev/null && pwd -P)" || exit 0
[ -n "$GITDIR" ] || exit 0
COMMONDIR="$(cd "$DIR" 2>/dev/null && cd "$(git rev-parse --git-common-dir 2>/dev/null)" 2>/dev/null && pwd -P)" || exit 0
[ -n "$COMMONDIR" ] || exit 0

# Linked worktree → already isolated, which is the whole point of the rule. Nothing to say.
[ "$GITDIR" = "$COMMONDIR" ] || exit 0

# Detached HEAD → symbolic-ref fails → not on a branch, so not on the default branch.
BRANCH="$(git -C "$DIR" symbolic-ref --short -q HEAD 2>/dev/null || true)"
[ -n "$BRANCH" ] || exit 0

# Default branch: origin/HEAD is authoritative when present; else the conventional names.
DEFAULT="$(git -C "$DIR" symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null || true)"
DEFAULT="${DEFAULT#origin/}"
if [ -z "$DEFAULT" ]; then
  for c in main master; do
    if git -C "$DIR" show-ref --verify -q "refs/heads/$c"; then DEFAULT="$c"; break; fi
  done
fi
[ -n "$DEFAULT" ] || exit 0
[ "$BRANCH" = "$DEFAULT" ] || exit 0

# A git-ignored path is local state (.claude/settings.json, scratch output), not repo work.
git -C "$DIR" check-ignore -q "$ABS" 2>/dev/null && exit 0

TOPLEVEL="$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$DIR")"

# Once per (session, repo). No session_id → no dedup, rather than a permanently silent guard.
SID="$(printf '%s' "$PAYLOAD" | jq -r '.session_id // empty' 2>/dev/null || true)"
if [ -n "$SID" ]; then
  KEY="$(printf '%s|%s' "$SID" "$COMMONDIR" | shasum 2>/dev/null | cut -c1-16)"
  if [ -n "$KEY" ]; then
    MARKER="${TMPDIR:-/tmp}/claude-kit-worktree-guard.$KEY"
    [ -e "$MARKER" ] && exit 0
    : >"$MARKER" 2>/dev/null || true
  fi
fi

MSG="P1 워크트리 격리 위반 가능성: 메인 체크아웃($TOPLEVEL)의 기본 브랜치($DEFAULT)에 직접 쓰고 있어요. 동시 작업 중이라면 다른 세션과 서로를 덮어씁니다 — 전용 워크트리에서 작업하세요 (git worktree add). 세션·저장소당 한 번만 알립니다. CLAUDE_KIT_WORKTREE_GUARD=enforce로 차단, =off로 끄기."

printf '[worktree-isolation-guard] %s\n' "$MSG" >&2

if [ "$MODE" = "enforce" ]; then
  jq -nc --arg m "$MSG" \
    '{permissionDecision:"deny", permissionDecisionReason:$m, systemMessage:("worktree-isolation-guard: " + $m)}'
  exit 0
fi

jq -nc --arg m "$MSG" '{systemMessage: ("worktree-isolation-guard: " + $m)}'
exit 0
