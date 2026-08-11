#!/usr/bin/env bash
# Regression test for scripts/no-pyyaml-guard.sh (PR #259 review P1).
#
# Every guard in this repo carries a regression test (subagent-git-guard.sh →
# test-subagent-git-guard.py, event-logger.sh → test-event-logger.sh); this is
# no-pyyaml-guard.sh's. It locks the detection regex boundary (the FP-sensitive
# part) + the mode matrix (enforce/warn/off) + the deny envelope + the emit path.
#
# Run: bash scripts/test/test-no-pyyaml-guard.sh   (exit 0 pass, 1 fail)

set -uo pipefail

GUARD="$(cd "$(dirname "$0")/.." && pwd)/no-pyyaml-guard.sh"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

# run <payload> <env...> — feed a payload, capture stdout, return exit code via $rc.
run() { rc=0; out="$(printf '%s' "$1" | "${@:2}" bash "$GUARD" 2>/dev/null)" || rc=$?; }

# denied <json> — true only if permissionDecision:deny is nested under hookSpecificOutput
# (documented PreToolUse schema). A top-level permissionDecision is silently ignored by
# Claude Code, so this must NOT match on substring alone.
denied() { printf '%s' "$1" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; }

# --- deny path: a PyYAML import in a .py write is blocked ---
run '{"tool_input":{"file_path":"/x/foo.py","content":"import yaml\nx=yaml.load(s)"}}'
denied "$out" && ok "import yaml in .py → deny" || bad "import yaml in .py → deny (got: $out)"

run '{"tool_input":{"file_path":"/x/foo.py","content":"from yaml import safe_load"}}'
denied "$out" && ok "from yaml import → deny" || bad "from yaml import → deny (got: $out)"

run '{"tool_input":{"file_path":"/x/foo.py","content":"import yaml.cyaml"}}'
denied "$out" && ok "import yaml.cyaml (dotted) → deny" || bad "import yaml.cyaml → deny (got: $out)"

# Edit payload (new_string) is also inspected.
run '{"tool_input":{"file_path":"/x/foo.py","new_string":"import yaml"}}'
denied "$out" && ok "Edit new_string import yaml → deny" || bad "Edit new_string → deny (got: $out)"

# --- allow path: no output, exit 0 ---
run '{"tool_input":{"file_path":"/x/foo.py","content":"import json\nd=json.load(f)"}}'
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "stdlib-only .py → allow" || bad "stdlib-only → allow (out=$out rc=$rc)"

run '{"tool_input":{"file_path":"/x/README.md","content":"do not import yaml here"}}'
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "non-.py mention → allow" || bad "non-.py → allow (out=$out rc=$rc)"

run '{"tool_input":{"file_path":"/x/foo.py","content":"# we deliberately do not import yaml\nimport json"}}'
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "comment mention (not line-start) → allow" || bad "comment mention → allow (out=$out rc=$rc)"

# FP boundary: a module that merely STARTS with yaml must not match.
run '{"tool_input":{"file_path":"/x/foo.py","content":"import yamllint"}}'
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "import yamllint (prefix) → allow (FP guard)" || bad "yamllint → allow (out=$out rc=$rc)"

# --- mode matrix ---
run '{"tool_input":{"file_path":"/x/foo.py","content":"import yaml"}}' env CLAUDE_KIT_NO_PYYAML_CONTRACT=warn
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "warn mode → no deny on stdout (allow)" || bad "warn mode (out=$out rc=$rc)"

run '{"tool_input":{"file_path":"/x/foo.py","content":"import yaml"}}' env CLAUDE_KIT_NO_PYYAML_CONTRACT=off
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "off mode → no-op (allow)" || bad "off mode (out=$out rc=$rc)"

# --- emit path: deny ALSO emits a rule_fire event when telemetry is opted in ---
TMPD="$(mktemp -d)"
printf '%s' '{"tool_input":{"file_path":"/x/foo.py","content":"import yaml"}}' \
  | env CLAUDE_KIT_TELEMETRY=1 CLAUDE_KIT_TELEMETRY_DIR="$TMPD" CLAUDE_PROJECT_DIR="$REPO_ROOT" \
    bash "$GUARD" >/dev/null 2>&1 || true
if grep -q '"event":"rule_fire"' "$TMPD"/events-*.jsonl 2>/dev/null \
   && grep -q '"rule_id":"no-pyyaml"' "$TMPD"/events-*.jsonl 2>/dev/null; then
  ok "telemetry ON → guard emits rule_fire (no-pyyaml)"
else
  bad "telemetry ON → rule_fire emitted ($(cat "$TMPD"/events-*.jsonl 2>/dev/null))"
fi
trash-put "$TMPD" 2>/dev/null || true   # P4: trash, never rm -rf (CI: ephemeral runner cleans up)

# telemetry OFF → guard still denies but emits nothing.
TMPD2="$(mktemp -d)"
printf '%s' '{"tool_input":{"file_path":"/x/foo.py","content":"import yaml"}}' \
  | env CLAUDE_KIT_TELEMETRY= CLAUDE_KIT_TELEMETRY_DIR="$TMPD2" CLAUDE_PROJECT_DIR="$REPO_ROOT" \
    bash "$GUARD" >/dev/null 2>&1 || true
if ls "$TMPD2"/events-*.jsonl >/dev/null 2>&1; then
  bad "telemetry OFF → leaked an event (CON-2 violation)"
else
  ok "telemetry OFF → guard denies but emits 0 (CON-2)"
fi
trash-put "$TMPD2" 2>/dev/null || true   # P4: trash, never rm -rf

echo
if [ "$FAIL" -eq 0 ]; then
  echo "OK: all no-pyyaml-guard cases passed ($PASS)"
  exit 0
fi
echo "FAILED: $FAIL case(s) failed, $PASS passed" >&2
exit 1
