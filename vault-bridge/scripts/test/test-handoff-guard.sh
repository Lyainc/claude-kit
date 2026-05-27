#!/usr/bin/env bash
# test-handoff-guard.sh — Unit tests for resolve-resume-path.sh
#
# resolve-resume-path.sh always writes to $PROJECT_ROOT/.claude-kit/vault-bridge/resume.md.
# The */.claude-kit/* whitelist fires first, so .claude-kit/ paths inside vault body trees
# (inbox/, notes/, assets/) are ALLOWED — this is intentional (pre-mortem scenario 1).
# The vault body guard exists as defense-in-depth for future edge cases where TARGET
# is not a .claude-kit/ path.
#
# Usage: bash vault-bridge/scripts/test/test-handoff-guard.sh
# Expected exit code: 0 (all cases pass)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD="${SCRIPT_DIR}/../resolve-resume-path.sh"

PASS=0
FAIL=0

pass() { echo "  PASS: $1"; ((PASS++)); }
fail() { echo "  FAIL: $1"; ((FAIL++)); }

echo "=== test-handoff-guard.sh ==="

# ── Case 1: Normal project outside vault root ──────────────────────────────
echo ""
echo "Case 1: Normal project outside vault root → allowed, echoes .claude-kit path"

_VAULT="/tmp/test-vault-c1-$$"
_PROJ="/tmp/test-proj-c1-$$"
mkdir -p "$_PROJ"
_out=$(CLAUDE_PROJECT_ROOT="$_PROJ" VAULT_BRIDGE_VAULT_ROOT="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0, echoes .claude-kit path (got: $_out)"
else
  fail "expected 0 + .claude-kit path, got rc=$_rc out='$_out'"
fi
rm -rf "$_PROJ"

# ── Case 2: PROJECT_ROOT inside vault inbox/ — .claude-kit/ is still allowed ─
echo ""
echo "Case 2: PROJECT_ROOT inside vault inbox/ → .claude-kit/ whitelist applies (allowed)"

_VAULT="/tmp/test-vault-c2-$$"
_PROJ="$_VAULT/inbox/myproject"
mkdir -p "$_PROJ"
_out=$(CLAUDE_PROJECT_ROOT="$_PROJ" VAULT_BRIDGE_VAULT_ROOT="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
# .claude-kit/ whitelist fires before vault body check — always allowed
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0 — .claude-kit/ whitelist allows even inside vault inbox/"
else
  fail "expected 0 (whitelist), got rc=$_rc out='$_out'"
fi
rm -rf "$_VAULT"

# ── Case 3: PROJECT_ROOT inside vault notes/ — .claude-kit/ is still allowed ─
echo ""
echo "Case 3: PROJECT_ROOT inside vault notes/ → .claude-kit/ whitelist applies (allowed)"

_VAULT="/tmp/test-vault-c3-$$"
_PROJ="$_VAULT/notes/somefolder/myproject"
mkdir -p "$_PROJ"
_out=$(CLAUDE_PROJECT_ROOT="$_PROJ" VAULT_BRIDGE_VAULT_ROOT="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0 — .claude-kit/ whitelist allows even inside vault notes/"
else
  fail "expected 0 (whitelist), got rc=$_rc out='$_out'"
fi
rm -rf "$_VAULT"

# ── Case 4: PROJECT_ROOT = vault root itself — .claude-kit/ allowed ────────
echo ""
echo "Case 4: PROJECT_ROOT is vault root (cloned vault as project) → .claude-kit/ allowed"

_VAULT="/tmp/test-vault-c4-$$"
mkdir -p "$_VAULT"
_out=$(CLAUDE_PROJECT_ROOT="$_VAULT" VAULT_BRIDGE_VAULT_ROOT="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0 — .claude-kit/ whitelist applies even when PROJECT_ROOT = vault root"
else
  fail "expected 0 (whitelist), got rc=$_rc out='$_out'"
fi
rm -rf "$_VAULT"

# ── Case 5: VAULT_BRIDGE_VAULT_ROOT override — custom vault root respected ─
echo ""
echo "Case 5: VAULT_BRIDGE_VAULT_ROOT override → custom vault root used for body-tree check"

_VAULT="/tmp/custom-vault-c5-$$"
_PROJ="/tmp/test-proj-c5-$$"
mkdir -p "$_PROJ"
_out=$(CLAUDE_PROJECT_ROOT="$_PROJ" VAULT_BRIDGE_VAULT_ROOT="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0 — VAULT_BRIDGE_VAULT_ROOT override respected, normal project allowed"
else
  fail "expected 0 with override, got rc=$_rc out='$_out'"
fi
rm -rf "$_PROJ"

# ── Case 6: PROJECT_ROOT inside vault assets/ — .claude-kit/ still allowed ─
echo ""
echo "Case 6: PROJECT_ROOT inside vault assets/ → .claude-kit/ whitelist applies (allowed)"

_VAULT="/tmp/test-vault-c6-$$"
_PROJ="$_VAULT/assets/attachments/myproject"
mkdir -p "$_PROJ"
_out=$(CLAUDE_PROJECT_ROOT="$_PROJ" VAULT_BRIDGE_VAULT_ROOT="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0 — .claude-kit/ whitelist allows even inside vault assets/"
else
  fail "expected 0 (whitelist), got rc=$_rc out='$_out'"
fi
rm -rf "$_VAULT"

# ── Case 7: VAULT_BRIDGE_VAULT_PATH fallback (no VAULT_ROOT set) ──────────
echo ""
echo "Case 7: VAULT_BRIDGE_VAULT_PATH fallback when VAULT_BRIDGE_VAULT_ROOT unset"

_VAULT="/tmp/test-vault-c7-$$"
_PROJ="/tmp/test-proj-c7-$$"
mkdir -p "$_PROJ"
_out=$(CLAUDE_PROJECT_ROOT="$_PROJ" VAULT_BRIDGE_VAULT_PATH="$_VAULT" bash "$GUARD" 2>/dev/null)
_rc=$?
if [ $_rc -eq 0 ] && echo "$_out" | grep -q ".claude-kit/vault-bridge/resume.md"; then
  pass "exits 0 — VAULT_BRIDGE_VAULT_PATH fallback accepted"
else
  fail "expected 0, got rc=$_rc out='$_out'"
fi
rm -rf "$_PROJ"

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ $FAIL -eq 0 ]; then
  echo "OK: all cases passed"
  exit 0
else
  echo "FAIL: $FAIL case(s) failed"
  exit 1
fi
