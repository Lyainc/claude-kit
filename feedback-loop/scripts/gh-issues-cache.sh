#!/usr/bin/env bash
# feedback-loop/scripts/gh-issues-cache.sh — shared open-issue backlog cache for
# comparison-set lookups (#528). retro's dedup step (skills/retro/SKILL.md) is the
# caller here; thinking-tools/scripts/next-candidate.py independently implements the
# same cache-path convention in Python rather than calling this script — CON-5
# forbids a leaf script from depending on a harness one, so the two stay separate
# code that happen to agree on where the cache lives. That script WRITES this cache
# but no longer reads it (#638): it runs after the issue-creating steps of the same
# chain, so any TTL long enough to be a cache is longer than the gap it would have to
# span. This script's own `get` still caches — its caller (retro dedup) runs BEFORE
# those creations, so it is on the right side of them.
#
# NEVER point a live-status render (a specific PR/issue's current state shown to the
# user) at this cache — only "does something like this already exist" comparison-set
# checks, where a few minutes of staleness is harmless. session-close's pre-render
# lookups must stay live: a cached one already misjudged a PR merged 9 hours earlier
# as still open (2026-07-30).
#
# Usage: gh-issues-cache.sh get   # prints the open-issue JSON array (cache or live fetch)
#   On a fetch failure, prints "[gh-issues-cache FAILED] ..." (NOT "[]") and exits 1 —
#   callers must branch on this before reading the output as an issue list (#618).

set -uo pipefail

TTL=300   # ponytail: flat 300s ceiling, long enough to span one /wrap run; widen if not.
LIMIT=300 # ponytail: open-issue cap, matches next-candidate.py; widen both together if a repo exceeds this.

PROJ_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$PWD")}"
CACHE="${PROJ_ROOT}/.claude-kit/cache/gh-open-issues.json"

case "${1:-}" in
  get)
    # One python3 call does the freshness check AND the read, so "python3 itself is
    # missing" fails the `if` (command not found, nonzero exit) instead of two
    # separate now()/mtime() shellouts each falling back to 0 — which would have
    # made an unreadable clock look identically fresh forever, the exact kind of
    # unverifiable-state-read-as-valid this file's own dedup guarantee exists to avoid.
    if FRESH="$(python3 -c "
import sys, os, time
p, ttl = sys.argv[1], int(sys.argv[2])
if time.time() - os.path.getmtime(p) < ttl:
    sys.stdout.write(open(p).read())
else:
    sys.exit(1)
" "$CACHE" "$TTL" 2>/dev/null)"; then
      printf '%s' "$FRESH"
      exit 0
    fi
    mkdir -p "$(dirname "$CACHE")" 2>/dev/null
    OUT="$(gh issue list --state open --limit "$LIMIT" \
      --json number,title,body,labels,updatedAt 2>/dev/null)"
    GH_RC=$?
    # #618: `gh` failing (nonzero exit) must never be read back as "genuinely zero
    # open issues" — the two used to collapse to the same "[]" stdout, so retro's
    # dedup step read a fetch failure as "no duplicates" and re-filed an issue that
    # already existed. Only a successful fetch (GH_RC=0) is cache-worthy or prints
    # as a bare JSON array; a failure prints a distinguishable marker on stdout and
    # exits nonzero instead (matches next-candidate.py's fail-open/fail-empty
    # distinction — see BACKLOG_UNAVAILABLE there).
    if [ "$GH_RC" -ne 0 ]; then
      printf '[gh-issues-cache FAILED] gh issue list 실패(exit %s) — 열린 이슈를 못 받았어요, 진짜 0건인지는 알 수 없어요.' "$GH_RC"
      exit 1
    fi
    # Write to a temp file then rename (atomic on the same filesystem) so a concurrent
    # reader (next-candidate.py writes the same path independently, #542) never sees a
    # partially-written file. Only a non-empty OUT is cache-worthy (#628) — a successful
    # call (GH_RC=0) with empty stdout would otherwise cache empty content, and a later
    # read within the TTL returns that raw empty string with no `${:-[]}` fallback.
    if [ -n "$OUT" ]; then
      TMP="${CACHE}.tmp.$$"
      { printf '%s' "$OUT" > "$TMP" && mv -f "$TMP" "$CACHE"; } 2>/dev/null
    fi
    printf '%s' "${OUT:-[]}"
    ;;
  *)
    exit 0
    ;;
esac
