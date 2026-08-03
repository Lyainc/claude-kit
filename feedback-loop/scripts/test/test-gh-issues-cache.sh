#!/usr/bin/env bash
# Regression for feedback-loop/scripts/gh-issues-cache.sh — the shared open-issue
# backlog cache retro's dedup step reads (#528). Pins: a fresh cache is served
# without touching `gh`, a failed fetch is never cached (so a later retry can
# still succeed), and an expired cache falls back to a live fetch.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${SCRIPT_DIR}/../gh-issues-cache.sh"
fail() { echo "FAIL: $1"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PROJECT_DIR="$TMP"
CACHE="$TMP/.claude-kit/cache/gh-open-issues.json"

STUB_DIR="$TMP/bin"
mkdir -p "$STUB_DIR"
stub() { printf '#!/usr/bin/env bash\n%s\n' "$1" > "$STUB_DIR/gh"; chmod +x "$STUB_DIR/gh"; }

# 1. live fetch on a cold cache, and the result gets cached
stub 'echo "[{\"number\":1,\"title\":\"first\"}]"'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
echo "$OUT" | jq -e '.[0].number==1' >/dev/null || fail "cold fetch did not return live data"
[ -f "$CACHE" ] || fail "successful fetch was not cached"

# 2. fresh cache is served without calling gh again
stub 'exit 1'  # if the script still shells out, this breaks the assertion below
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
echo "$OUT" | jq -e '.[0].number==1' >/dev/null || fail "fresh cache was not reused"

# 3. a failed fetch is never cached (so a later retry can still succeed)
rm -f "$CACHE"
stub 'exit 1'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
[ "$OUT" = "[]" ] || fail "failed fetch did not fail open to []"
[ -f "$CACHE" ] && fail "failed fetch was cached"

# 4. expired cache falls back to a live fetch
stub 'echo "[{\"number\":2,\"title\":\"second\"}]"'
PATH="$STUB_DIR:$PATH" "$SCRIPT" get >/dev/null
[ -f "$CACHE" ] || fail "setup fetch for expiry case was not cached"
python3 -c "import os,sys; os.utime(sys.argv[1], (0, 0))" "$CACHE"  # far in the past
stub 'echo "[{\"number\":3,\"title\":\"third\"}]"'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
echo "$OUT" | jq -e '.[0].number==3' >/dev/null || fail "expired cache was served instead of a live refetch"

echo "OK: all gh-issues-cache cases passed"
