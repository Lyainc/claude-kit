#!/usr/bin/env bash
# test-infer-tags-batch.sh — regression for ovm-primitives.sh `infer-tags` batch mode (#152)
#
# Locks the SHELL-level batch surface that audit-validate.py --infer-self-test does
# NOT cover (that test exercises the Python reference impl, not ovm-primitives.sh):
#   - multiple-path args -> one JSON array, one element per path
#   - stdin mode ('-')   -> same array contract
#   - single path        -> a one-element array (not a bare object)
#   - uniform schema      -> error elements carry `type: null` like success elements
#   - partial-failure exit-code policy: a mix of ok+failed exits 0; all-failed exits 1
#   - SECURITY hard-fail: traversal / out-of-vault / empty input must `die` (exit 1,
#     no JSON on stdout) and NEVER degrade into a graceful error element.
#
# The security cases pin the behavior verified during PR #157 review: a reviewer
# flagged `abs_files+=("$(validate_vault_path ...)")` as silently swallowing the
# `die` (claiming arr+=() always exits 0), which would convert a security hard-fail
# into graceful degradation. That was a false positive — command-substitution exit
# status propagates through the append under `set -e` — and these tests guard the
# real, intended behavior so a future refactor can't regress it unnoticed.
#
# Standalone-runnable; exits non-zero on any assertion failure.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIM="${SCRIPT_DIR}/../ovm-primitives.sh"

command -v jq >/dev/null 2>&1 || { echo "FAIL: jq required on PATH" >&2; exit 1; }
[ -f "$PRIM" ] || { echo "FAIL: ovm-primitives.sh not found at $PRIM" >&2; exit 1; }

VAULT="$(mktemp -d)"
trap 'rm -rf "$VAULT"' EXIT
mkdir -p "$VAULT/notes/devops"
cat > "$VAULT/notes/devops/decision-2026-01-02-ci-cache.md" <<'MD'
---
type: decision
created: 2026-01-02
---
body
MD
cat > "$VAULT/notes/note-foo-bar.md" <<'MD'
---
type: note
---
body
MD

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf 'ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf 'FAIL %s\n     %s\n' "$1" "$2" >&2; }

F1="notes/devops/decision-2026-01-02-ci-cache.md"
F2="notes/note-foo-bar.md"

# 1. two-file happy path -> JSON array of length 2, exit 0
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags "$F1" "$F2")"; rc=$?
if [ $rc -eq 0 ] && [ "$(printf '%s' "$out" | jq 'length')" = 2 ]; then
  ok "happy 2-file: array len 2, exit 0"
else bad "happy 2-file" "rc=$rc out=$out"; fi

# success element carries a non-null `type`
if [ "$(printf '%s' "$out" | jq -r '.[0].type')" = "decision" ]; then
  ok "success element carries type"
else bad "success type" "$out"; fi

# 2. single path -> a one-element array (not a bare object)
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags "$F2")"; rc=$?
if [ $rc -eq 0 ] && [ "$(printf '%s' "$out" | jq 'if type=="array" then length else -1 end')" = 1 ]; then
  ok "single path: one-element array, exit 0"
else bad "single path" "rc=$rc out=$out"; fi

# 3. stdin mode -> same array contract, exit 0
out="$(printf '%s\n%s\n' "$F1" "$F2" | VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags -)"; rc=$?
if [ $rc -eq 0 ] && [ "$(printf '%s' "$out" | jq 'length')" = 2 ]; then
  ok "stdin 2-file: array len 2, exit 0"
else bad "stdin happy" "rc=$rc out=$out"; fi

# 4. partial fail (1 ok + 1 unreadable) -> exit 0; error element has type:null + error;
#    the ok element survives intact.
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags "$F2" "notes/does-not-exist.md")"; rc=$?
nerr="$(printf '%s' "$out" | jq '[.[]|select(has("error"))]|length')"
ntypenull="$(printf '%s' "$out" | jq '[.[]|select(has("error"))|select(.type==null)]|length')"
nok="$(printf '%s' "$out" | jq '[.[]|select(has("error")|not)]|length')"
if [ $rc -eq 0 ] && [ "$nerr" = 1 ] && [ "$ntypenull" = 1 ] && [ "$nok" = 1 ]; then
  ok "partial fail: exit 0, error element type:null, ok element intact"
else bad "partial fail" "rc=$rc nerr=$nerr ntypenull=$ntypenull nok=$nok out=$out"; fi

# 5. all-fail (every path unreadable) -> exit 1, but still emits the array
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags "notes/nope1.md" "notes/nope2.md")"; rc=$?
if [ $rc -eq 1 ] && [ "$(printf '%s' "$out" | jq 'length')" = 2 ]; then
  ok "all-fail: exit 1 (array still emitted)"
else bad "all-fail" "rc=$rc out=$out"; fi

# 6. empty input (no paths) -> die, exit 1, no JSON
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags 2>/dev/null)"; rc=$?
if [ $rc -eq 1 ] && [ -z "$out" ]; then
  ok "no args: die exit 1, no stdout"
else bad "no args" "rc=$rc out=$out"; fi

# 7. SECURITY: traversal path -> hard die before Python, exit 1, NO JSON on stdout
#    (a graceful-degradation regression would print a JSON array here instead).
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags '../../../etc/passwd' 2>/dev/null)"; rc=$?
if [ $rc -eq 1 ] && [ -z "$out" ]; then
  ok "traversal: hard die exit 1, no JSON (not graceful-degraded)"
else bad "traversal hard-fail" "rc=$rc out=$out"; fi

# 8. SECURITY: out-of-vault absolute path -> hard die, exit 1, NO JSON on stdout
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags '/etc/hosts' 2>/dev/null)"; rc=$?
if [ $rc -eq 1 ] && [ -z "$out" ]; then
  ok "out-of-vault: hard die exit 1, no JSON"
else bad "out-of-vault hard-fail" "rc=$rc out=$out"; fi

# 9. SECURITY: a traversal path mixed AMONG valid paths still hard-dies the whole
#    batch (the guard runs up front, before any Python read).
out="$(VAULT_ROOT="$VAULT" bash "$PRIM" infer-tags "$F1" '../escape.md' 2>/dev/null)"; rc=$?
if [ $rc -eq 1 ] && [ -z "$out" ]; then
  ok "traversal among valid paths: whole batch hard-dies"
else bad "mixed traversal hard-fail" "rc=$rc out=$out"; fi

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
echo "OK: all infer-tags batch cases passed"
