#!/usr/bin/env bash
# completion-condition candidate-pool hook + next-candidate.py regression (#517).
#
# Two failure shapes this pins, both of which are silent in production:
#
# 1. **The matcher stops matching.** Plugin skills arrive as `plugin:skill`, machine skills
#    bare. The hook was ported from a machine-level one keyed on the bare name, and #406
#    recorded that carrying that key over unchanged makes the hook NEVER fire — a hook that
#    never fires looks exactly like a hook with nothing to say.
#
# 2. **A failed backlog lookup reads as an empty backlog.** "no open issues" and "could not
#    look" lead to opposite decisions, so collapsing them into one blank section is how a
#    missing `gh` gets read as a groomed backlog. Same class as #443/#447.
#
# Deterministic: `gh` is stubbed on PATH, so no network and no real backlog is consulted.

set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # thinking-tools/
hook="${root}/hooks/completion-condition-context.sh"
script="${root}/scripts/next-candidate.py"

pass=0
fail=0
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

ok()   { pass=$((pass + 1)); }
bad()  { fail=$((fail + 1)); printf 'FAIL: %s\n' "$1" >&2; }
check(){ if [ "$2" = "$3" ]; then ok; else bad "$1 — expected [$3], got [$2]"; fi; }

command -v jq >/dev/null 2>&1 || { echo "SKIP: jq not installed" >&2; exit 0; }
command -v python3 >/dev/null 2>&1 || { echo "SKIP: python3 not installed" >&2; exit 0; }

# --- fixture repos -----------------------------------------------------------------
mk_repo() {  # $1 = dir, $2 = remote url (empty for none)
  mkdir -p "$1" && git -C "$1" init -q 2>/dev/null
  git -C "$1" config user.email t@t && git -C "$1" config user.name t
  echo x > "$1/f.txt" && git -C "$1" add -A && git -C "$1" commit -qm "init"
  [ -n "$2" ] && git -C "$1" remote add origin "$2"
  return 0
}
mk_repo "$tmp/plain" ""
mk_repo "$tmp/gh" "https://github.com/example/example.git"

# --- hermetic "gh absent" PATH ------------------------------------------------------
# Never assume gh is missing from /usr/bin or /bin — GitHub Actions ubuntu runners ship
# gh preinstalled there, which is exactly what made "gh missing -> 조회 못 함" fail
# deterministically in CI while always passing on a local macOS/Homebrew PATH (#535).
# Build a PATH containing only symlinks to what this one invocation actually needs
# (python3 to run the script, git for its `git remote -v` check), with no gh in it.
no_gh_dir="$tmp/bin-no-gh"
mkdir -p "$no_gh_dir"
ln -s "$(command -v python3)" "$no_gh_dir/python3"
ln -s "$(command -v git)" "$no_gh_dir/git"

# --- gh stubs ----------------------------------------------------------------------
stub_dir="$tmp/bin"
mkdir -p "$stub_dir"
make_stub() {  # $1 = body
  printf '#!/usr/bin/env bash\n%s\n' "$1" > "$stub_dir/gh"
  chmod +x "$stub_dir/gh"
}

fire() {  # $1 = skill name, $2 = cwd; echoes hook stdout
  printf '{"tool_name":"Skill","tool_input":{"skill":"%s"},"cwd":"%s"}' "$1" "$2" \
    | CLAUDE_PLUGIN_ROOT="$root" bash "$hook" 2>/dev/null
}

# === 1. matcher ====================================================================
out="$(fire "thinking-tools:completion-condition" "$tmp/gh")"
check "qualified skill name fires" "$([ -n "$out" ] && echo yes || echo no)" "yes"

out="$(fire "completion-condition" "$tmp/gh")"
check "bare skill name fires" "$([ -n "$out" ] && echo yes || echo no)" "yes"

out="$(fire "thinking-tools:expert-panel" "$tmp/gh")"
check "other skill stays silent" "$([ -n "$out" ] && echo yes || echo no)" "no"

out="$(printf '{"tool_name":"Bash","tool_input":{"command":"ls"},"cwd":"%s"}' "$tmp/gh" \
  | CLAUDE_PLUGIN_ROOT="$root" bash "$hook" 2>/dev/null)"
check "non-Skill tool stays silent" "$([ -n "$out" ] && echo yes || echo no)" "no"

# === 2. kill switch ================================================================
out="$(printf '{"tool_name":"Skill","tool_input":{"skill":"completion-condition"},"cwd":"%s"}' "$tmp/gh" \
  | CLAUDE_KIT_NEXT_CANDIDATE_DISABLE=1 CLAUDE_PLUGIN_ROOT="$root" bash "$hook" 2>/dev/null)"
check "kill switch silences" "$([ -n "$out" ] && echo yes || echo no)" "no"

# === 3. output shape ===============================================================
out="$(fire "completion-condition" "$tmp/gh")"
event="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.hookEventName' 2>/dev/null)"
check "emits PreToolUse envelope" "$event" "PreToolUse"
has_decision="$(printf '%s' "$out" | jq -r 'has("permissionDecision") or (.hookSpecificOutput|has("permissionDecision"))' 2>/dev/null)"
check "never grants permission" "$has_decision" "false"

# === 4. backlog failure is never an empty backlog ==================================
# A repo with no GitHub remote: reported as not-consulted, not as zero issues.
got="$(python3 "$script" --cwd "$tmp/plain" 2>/dev/null | grep -c '조회 안 함')"
check "no remote -> '조회 안 함'" "$got" "1"

# gh absent, GitHub remote present: reported as could-not-look.
got="$(env PATH="$no_gh_dir" python3 "$script" --cwd "$tmp/gh" 2>/dev/null | grep -c '조회 못 함')"
check "gh missing -> '조회 못 함'" "$got" "1"

# gh present but failing (auth expired / no access): reported as failed, not empty.
make_stub 'exit 1'
got="$(env PATH="$stub_dir:$PATH" python3 "$script" --cwd "$tmp/gh" 2>/dev/null | grep -c '조회 실패')"
check "gh failing -> '조회 실패'" "$got" "1"

# gh present and succeeding with zero issues: the ONLY case allowed to read as empty.
make_stub 'echo "[]"'
out="$(env PATH="$stub_dir:$PATH" python3 "$script" --cwd "$tmp/gh" 2>/dev/null)"
check "genuinely empty -> '실제로 비어'" "$(printf '%s' "$out" | grep -c '실제로 비어')" "1"
check "genuinely empty is not a failure line" "$(printf '%s' "$out" | grep -c '조회')" "0"

# === 5. payload carries data, not verdicts =========================================
# The impact floor / re-pick / disclose-your-pool rules belong to SKILL.md alone; shipping
# them in the payload too is duplication across the boundary (claude-kit-boundary altitude).
make_stub 'echo "[]"'
ctx="$(printf '{"tool_name":"Skill","tool_input":{"skill":"completion-condition"},"cwd":"%s"}' "$tmp/gh" \
  | env PATH="$stub_dir:$PATH" CLAUDE_PLUGIN_ROOT="$root" bash "$hook" 2>/dev/null \
  | jq -r '.hookSpecificOutput.additionalContext' 2>/dev/null)"
for verdict in '임팩트 바닥' '다시 고르세요' '밝히세요' '반드시 비교'; do
  check "payload omits verdict [$verdict]" "$(printf '%s' "$ctx" | grep -c "$verdict")" "0"
done

# === 6. gh-open-issues cache reuse (#528) ==========================================
# Test 4's "genuinely empty" call above already populated $tmp/gh's shared cache
# (.claude-kit/cache/gh-open-issues.json) with a successful empty-backlog fetch.
# With `gh` now entirely unavailable, a cache-hit must still read as "genuinely
# empty" — not fall through to "조회 못 함" — proving the fresh cache is served
# without shelling out again. retro's dedup step (feedback-loop/skills/retro/SKILL.md)
# reads the same cache via feedback-loop/scripts/gh-issues-cache.sh.
got="$(env PATH=/usr/bin:/bin python3 "$script" --cwd "$tmp/gh" 2>/dev/null | grep -c '실제로 비어')"
check "fresh cache served without gh on PATH" "$got" "1"

# An expired cache must NOT be served — it falls back to a live fetch (or, with no
# `gh` on PATH here, the same "조회 못 함" as an uncached miss). GH_CACHE_TTL_OVERRIDE=-1
# forces immediate expiry deterministically — OS mtime writes vs. reads across two
# separate process invocations are not guaranteed to order/resolve identically across
# platforms/filesystems, which is what made this flake on Linux CI while passing locally.
got="$(env PATH=/usr/bin:/bin GH_CACHE_TTL_OVERRIDE=-1 python3 "$script" --cwd "$tmp/gh" 2>/dev/null | grep -c '조회 못 함')"
check "expired cache falls back to a live lookup" "$got" "1"

# === report ========================================================================
if [ "$fail" -eq 0 ]; then
  echo "OK: all ${pass} completion-condition-hook cases passed"
  exit 0
fi
echo "FAILED: ${fail} of $((pass + fail)) cases" >&2
exit 1
