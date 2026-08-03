#!/usr/bin/env bash
# feedback-loop/scripts/gh-issues-cache.sh — shared open-issue backlog cache for
# comparison-set lookups (#528). retro's dedup step (skills/retro/SKILL.md) is the
# caller here; thinking-tools/scripts/next-candidate.py independently implements the
# same cache-path/TTL convention in Python rather than calling this script — CON-5
# forbids a leaf script from depending on a harness one, so the two stay separate
# code that happen to agree on where the cache lives.
#
# NEVER point a live-status render (a specific PR/issue's current state shown to the
# user) at this cache — only "does something like this already exist" comparison-set
# checks, where a few minutes of staleness is harmless. session-close's pre-render
# lookups must stay live: a cached one already misjudged a PR merged 9 hours earlier
# as still open (2026-07-30).
#
# Usage: gh-issues-cache.sh get   # prints the open-issue JSON array (cache or live fetch)

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
    # Only a successful fetch is cache-worthy — a failure must never be written down
    # and later read back as "genuinely zero open issues" (matches next-candidate.py's
    # fail-open/fail-empty distinction).
    [ -n "$OUT" ] && printf '%s' "$OUT" > "$CACHE" 2>/dev/null
    printf '%s' "${OUT:-[]}"
    ;;
  *)
    exit 0
    ;;
esac
