#!/usr/bin/env bash
# Regression test for scripts/worktree-isolation-guard.sh (#594).
#
# Every guard in this repo carries a regression test (subagent-git-guard.sh →
# test-subagent-git-guard.py, no-pyyaml-guard.sh → test-no-pyyaml-guard.sh); this is
# the worktree-isolation guard's. It builds REAL git repos and a REAL linked worktree in
# a temp dir — the whole detection rests on git-dir vs git-common-dir and on default-branch
# resolution, neither of which a hand-written fixture would exercise honestly.
#
# It locks: the fire condition (main checkout + default branch), the three silent cases the
# guard must never flag (linked worktree, feature branch, git-ignored path), default-branch
# resolution (origin/HEAD wins over the main/master fallback), the mode matrix, and the
# once-per-(session, repo) dedup.
#
# Run: bash scripts/test/test-worktree-isolation-guard.sh   (exit 0 pass, 1 fail)

set -uo pipefail

GUARD="$(cd "$(dirname "$0")/.." && pwd)/worktree-isolation-guard.sh"
PASS=0
FAIL=0

ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# Keep dedup markers inside the sandbox so a rerun never inherits a previous run's state.
export TMPDIR="$WORK/tmp"
mkdir -p "$TMPDIR"

# run <payload> [env assignments...] — feed a payload, capture stdout, set $out/$rc.
run() { rc=0; out="$(printf '%s' "$1" | "${@:2}" bash "$GUARD" 2>/dev/null)" || rc=$?; }

payload() {  # payload <file_path> [session_id]
  jq -nc --arg p "$1" --arg s "${2:-}" \
    '{tool_name:"Write", tool_input:{file_path:$p}} + (if $s == "" then {} else {session_id:$s} end)'
}

warned() { printf '%s' "$1" | grep -q 'worktree-isolation-guard'; }

# --- fixtures ---------------------------------------------------------------
# MAIN: main checkout on `main`, one commit, a .gitignore, plus a linked worktree.
MAIN="$WORK/main-repo"
git init -q -b main "$MAIN"
git -C "$MAIN" config user.email t@t.t
git -C "$MAIN" config user.name t
printf 'ignored/\n' >"$MAIN/.gitignore"
git -C "$MAIN" add -A
git -C "$MAIN" commit -qm init
mkdir -p "$MAIN/ignored"
WT="$WORK/wt"
git -C "$MAIN" worktree add -q -b feat/x "$WT"

# TRUNK: no `main` branch at all; origin/HEAD points at origin/trunk. Also carries a local
# `main` branch so the fallback would pick the WRONG answer if origin/HEAD were ignored.
TRUNK="$WORK/trunk-repo"
git init -q -b trunk "$TRUNK"
git -C "$TRUNK" config user.email t@t.t
git -C "$TRUNK" config user.name t
git -C "$TRUNK" commit -q --allow-empty -m init
git -C "$TRUNK" branch main
git -C "$TRUNK" update-ref refs/remotes/origin/trunk "$(git -C "$TRUNK" rev-parse HEAD)"
git -C "$TRUNK" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk

# MASTER: no origin, default branch is `master` (fallback's second name).
MASTER="$WORK/master-repo"
git init -q -b master "$MASTER"
git -C "$MASTER" config user.email t@t.t
git -C "$MASTER" config user.name t
git -C "$MASTER" commit -q --allow-empty -m init

# --- fire path --------------------------------------------------------------
run "$(payload "$MAIN/a.md" s1)"
{ warned "$out" && [ "$rc" -eq 0 ]; } && ok "main checkout + default branch → warn" \
  || bad "main checkout + default branch → warn (out=$out rc=$rc)"

# A not-yet-existing nested parent must still resolve to the repo.
run "$(payload "$MAIN/new/deep/b.md" s2)"
warned "$out" && ok "nonexistent nested parent → warn" || bad "nested parent (out=$out)"

# origin/HEAD wins over the main/master fallback.
run "$(payload "$TRUNK/a.md" s3)"
warned "$out" && ok "origin/HEAD default (trunk) → warn" || bad "origin/HEAD default (out=$out)"

run "$(payload "$MASTER/a.md" s4)"
warned "$out" && ok "master fallback default → warn" || bad "master fallback (out=$out)"

# --- silent paths -----------------------------------------------------------
run "$(payload "$WT/a.md" s5)"
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "linked worktree → silent" || bad "linked worktree (out=$out rc=$rc)"

git -C "$MAIN" checkout -q -b feat/y
run "$(payload "$MAIN/a.md" s6)"
[ -z "$out" ] && ok "main checkout on feature branch → silent (documented gap)" \
  || bad "feature branch (out=$out)"
git -C "$MAIN" checkout -q main

run "$(payload "$MAIN/ignored/x.md" s7)"
[ -z "$out" ] && ok "git-ignored path → silent" || bad "ignored path (out=$out)"

run "$(payload "$WORK/not-a-repo/x.md" s8)"
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "outside any repo → silent" || bad "non-repo (out=$out rc=$rc)"

run '{"tool_name":"Write","tool_input":{}}'
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "no file_path → silent" || bad "no file_path (out=$out rc=$rc)"

git -C "$MAIN" checkout -q --detach
run "$(payload "$MAIN/a.md" s9)"
[ -z "$out" ] && ok "detached HEAD → silent" || bad "detached HEAD (out=$out)"
git -C "$MAIN" checkout -q main

# --- relative path resolves against the payload cwd -------------------------
run "$(jq -nc --arg c "$MAIN" '{tool_name:"Write",tool_input:{file_path:"a.md"},cwd:$c,session_id:"s10"}')"
warned "$out" && ok "relative path + cwd → warn" || bad "relative path (out=$out)"

# --- mode matrix ------------------------------------------------------------
run "$(payload "$MAIN/a.md" s11)" env CLAUDE_KIT_WORKTREE_GUARD=off
[ -z "$out" ] && [ "$rc" -eq 0 ] && ok "off mode → no-op" || bad "off mode (out=$out rc=$rc)"

run "$(payload "$MAIN/a.md" s12)" env CLAUDE_KIT_WORKTREE_GUARD=enforce
{ printf '%s' "$out" | grep -q '"permissionDecision":"deny"'; } && ok "enforce mode → deny" \
  || bad "enforce mode → deny (out=$out)"

run "$(payload "$MAIN/a.md" s13)"
{ warned "$out" && ! printf '%s' "$out" | grep -q 'permissionDecision'; } \
  && ok "warn mode (default) → systemMessage only, never deny" || bad "warn mode (out=$out)"

# --- dedup ------------------------------------------------------------------
run "$(payload "$MAIN/a.md" dup)"
warned "$out" || bad "dedup: first call should warn (out=$out)"
run "$(payload "$MAIN/b.md" dup)"
[ -z "$out" ] && ok "dedup: same session + repo → silent on second write" || bad "dedup second (out=$out)"
run "$(payload "$TRUNK/a.md" dup)"
warned "$out" && ok "dedup is per-repo: same session, other repo → warns" || bad "dedup per-repo (out=$out)"
run "$(payload "$MAIN/a.md" other-session)"
warned "$out" && ok "dedup is per-session: new session → warns again" || bad "dedup per-session (out=$out)"

# A payload with no session_id must never dedup itself into permanent silence.
run "$(payload "$MAIN/a.md")"
warned "$out" || bad "no session_id: first call should warn (out=$out)"
run "$(payload "$MAIN/a.md")"
warned "$out" && ok "no session_id → no dedup (warns every time)" || bad "no session_id repeat (out=$out)"

# ---------------------------------------------------------------------------
printf '\n'
if [ "$FAIL" -gt 0 ]; then
  printf 'FAILED: %d passed, %d failed\n' "$PASS" "$FAIL" >&2
  exit 1
fi
printf 'OK: all worktree-isolation-guard cases passed (%d)\n' "$PASS"
exit 0
