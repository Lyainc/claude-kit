#!/usr/bin/env bash
# Regression for feedback-loop/scripts/gh-issues-cache.sh — the shared open-issue
# backlog cache retro's dedup step reads (#528). Pins: a fresh cache is served
# without touching `gh`, a failed fetch is never cached (so a later retry can
# still succeed), a failed fetch is distinguishable from a genuine zero-open-issue
# backlog (#618 — both used to print bare "[]"), and an expired cache falls back
# to a live fetch.
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

# 3. a failed fetch is never cached (so a later retry can still succeed), exits
#    nonzero, and is NOT the bare "[]" a genuine zero-open-issue backlog prints (#618) —
#    a caller must be able to tell "gh failed" apart from "genuinely zero issues".
rm -f "$CACHE"
stub 'exit 1'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
RC=$?
[ "$RC" -ne 0 ] || fail "failed fetch exited 0"
[ "$OUT" != "[]" ] || fail "failed fetch printed the same [] a genuine zero-issue backlog would"
case "$OUT" in
  "[gh-issues-cache FAILED]"*) : ;;
  *) fail "failed fetch did not print the FAILED marker (got: $OUT)" ;;
esac
[ -f "$CACHE" ] && fail "failed fetch was cached"

# 3b. a genuine zero-open-issue backlog (gh succeeds, returns "[]") is NOT confused
#     with a failure — exits 0, prints bare "[]", and gets cached like any other result.
rm -f "$CACHE"
stub 'echo "[]"'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
RC=$?
[ "$RC" -eq 0 ] || fail "genuine zero-issue fetch did not exit 0"
[ "$OUT" = "[]" ] || fail "genuine zero-issue fetch did not print []"
[ -f "$CACHE" ] || fail "genuine zero-issue fetch was not cached"

# 4. expired cache falls back to a live fetch
stub 'echo "[{\"number\":2,\"title\":\"second\"}]"'
PATH="$STUB_DIR:$PATH" "$SCRIPT" get >/dev/null
[ -f "$CACHE" ] || fail "setup fetch for expiry case was not cached"
python3 -c "import os,sys; os.utime(sys.argv[1], (0, 0))" "$CACHE"  # far in the past
stub 'echo "[{\"number\":3,\"title\":\"third\"}]"'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get)"
echo "$OUT" | jq -e '.[0].number==3' >/dev/null || fail "expired cache was served instead of a live refetch"

# 5. stderr leak (#629, same class as #617): a write-unable cache dir must not
# leak the shell's own redirection-open diagnostic. `printf ... > "$TMP" 2>/dev/null`
# alone doesn't guarantee this — the `>` open failure prints before `2>/dev/null`
# takes effect (fixed by wrapping in `{ ...; } 2>/dev/null`, gh-issues-cache.sh:54).
rm -f "$CACHE"
mkdir -p "$(dirname "$CACHE")"
chmod 500 "$(dirname "$CACHE")"
STDERR_629="$(mktemp)"
stub 'echo "[{\"number\":4,\"title\":\"fourth\"}]"'
OUT="$(PATH="$STUB_DIR:$PATH" "$SCRIPT" get 2>"$STDERR_629")"
RC=$?
chmod 700 "$(dirname "$CACHE")"
[ "$RC" -eq 0 ] || fail "write-unable cache dir caused a non-zero exit"
[ ! -s "$STDERR_629" ] || fail "write-unable cache dir leaked to stderr: $(cat "$STDERR_629")"
echo "$OUT" | jq -e '.[0].number==4' >/dev/null || fail "write-unable cache dir still lost the live fetch result"
rm -f "$STDERR_629"

echo "OK: all gh-issues-cache cases passed"
