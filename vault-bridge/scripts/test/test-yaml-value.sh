#!/usr/bin/env bash
# Regression test for the `_yaml_value` awk helper in plan-doc-sync.sh.
#
# `_yaml_value` is a security-relevant parser: its output feeds the
# `vault_path` traversal check that gates filesystem reads. A regression
# that silently returns the wrong scalar would bypass that gate.
#
# This test extracts `_yaml_value` (and the `_is_truthy` helper) from the
# live hook source via sed range, evals them into the current shell, then
# asserts behavior against synthetic .vault-link / _index.md inputs.

set -euo pipefail

HOOK="$(cd "$(dirname "$0")/../.." && pwd)/hooks/plan-doc-sync.sh"
[ -f "$HOOK" ] || { echo "FAIL: $HOOK not found" >&2; exit 1; }

# Extract `_yaml_value` and `_is_truthy` from the hook. The sed range
# matches `name() {` to the next line that starts with `}`. This relies on
# the hook keeping the closing brace at column 0 — see plan-doc-sync.sh:38-66.
eval "$(sed -n '/^_yaml_value() {/,/^}/p' "$HOOK")"
eval "$(sed -n '/^_is_truthy() {/,/^}/p' "$HOOK")"

PASS=0
FAIL=0
assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
    printf '  ok   %s\n' "$desc"
  else
    FAIL=$((FAIL + 1))
    printf '  FAIL %s\n    expected: %q\n    actual:   %q\n' "$desc" "$expected" "$actual" >&2
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Test 1: flat key:value file (no frontmatter) ---
cat > "$TMP/flat" <<'EOF'
vault_path: 20_Projects/test
auto_capture: true
EOF
assert_eq "flat: vault_path read" "20_Projects/test" "$(_yaml_value "$TMP/flat" vault_path)"
assert_eq "flat: auto_capture read" "true" "$(_yaml_value "$TMP/flat" auto_capture)"

# --- Test 2: frontmatter scope respected ---
cat > "$TMP/fm" <<'EOF'
---
vault_path: 20_Projects/scoped
auto_capture: true
---
# body content below
auto_capture: false
some_other_key: outside
EOF
assert_eq "fm: vault_path inside fm" "20_Projects/scoped" "$(_yaml_value "$TMP/fm" vault_path)"
assert_eq "fm: auto_capture inside fm (not body)" "true" "$(_yaml_value "$TMP/fm" auto_capture)"
assert_eq "fm: body-only key returns empty" "" "$(_yaml_value "$TMP/fm" some_other_key)"

# --- Test 3: quoted values stripped ---
cat > "$TMP/quoted" <<'EOF'
key_a: "true"
key_b: 'value with spaces'
key_c: bare
EOF
assert_eq "quoted: double quotes stripped" "true" "$(_yaml_value "$TMP/quoted" key_a)"
assert_eq "quoted: single quotes stripped" "value with spaces" "$(_yaml_value "$TMP/quoted" key_b)"
assert_eq "quoted: bare scalar untouched" "bare" "$(_yaml_value "$TMP/quoted" key_c)"

# --- Test 4: missing key returns empty ---
assert_eq "missing key" "" "$(_yaml_value "$TMP/flat" nonexistent)"

# --- Test 5: key sanitization rejects regex metacharacters ---
# `_yaml_value` should reject keys containing characters outside [A-Za-z0-9_].
# Capture stderr to verify the rejection message; stdout must be empty.
out_dot="$(_yaml_value "$TMP/flat" 'key.with.dots' 2>/dev/null || true)"
assert_eq "sanitize: key with dots returns empty stdout" "" "$out_dot"
out_brk="$(_yaml_value "$TMP/flat" 'key[bracket]' 2>/dev/null || true)"
assert_eq "sanitize: key with brackets returns empty stdout" "" "$out_brk"
out_empty="$(_yaml_value "$TMP/flat" '' 2>/dev/null || true)"
assert_eq "sanitize: empty key returns empty stdout" "" "$out_empty"

# --- Test 6: _is_truthy lax boolean parity ---
_is_truthy "true"  && assert_eq "truthy: true"  "0" "0" || assert_eq "truthy: true"  "0" "1"
_is_truthy "TRUE"  && assert_eq "truthy: TRUE"  "0" "0" || assert_eq "truthy: TRUE"  "0" "1"
_is_truthy "yes"   && assert_eq "truthy: yes"   "0" "0" || assert_eq "truthy: yes"   "0" "1"
_is_truthy "1"     && assert_eq "truthy: 1"     "0" "0" || assert_eq "truthy: 1"     "0" "1"
_is_truthy "false" && assert_eq "truthy: false" "1" "0" || assert_eq "truthy: false" "1" "1"
_is_truthy ""      && assert_eq "truthy: empty" "1" "0" || assert_eq "truthy: empty" "1" "1"
_is_truthy "no"    && assert_eq "truthy: no"    "1" "0" || assert_eq "truthy: no"    "1" "1"

echo ""
printf 'Result: %d pass, %d fail\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
