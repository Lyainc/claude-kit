#!/usr/bin/env bash
# Regression test for scripts/worktree-isolation-guard.sh (#594).
#
# Every guard in this repo carries a regression test (subagent-git-guard.sh →
# test-subagent-git-guard.py, no-pyyaml-guard.sh → test-no-pyyaml-guard.sh); this is
# the worktree-isolation guard's. It builds REAL git repos and a REAL linked worktree in
# a temp dir — the whole detection rests on git-dir vs git-common-dir and on default-branch
# resolution, neither of which a hand-written fixture would exercise honestly.
#
# It locks: the fire condition (main checkout + default branch), every silent case the guard
# must never flag (linked worktree, feature branch, git-ignored path, another repository,
# inside .git/, a bare repo), default-branch resolution (origin/HEAD wins over the
# main/master fallback), the mode matrix, warn-mode dedup, and that enforce never dedups.
#
# The linked-worktree case deliberately puts the DEFAULT branch in the worktree and a feature
# branch in the main checkout: with the two on the same branch, the branch check alone would
# silence the case and the git-dir vs git-common-dir comparison — the mechanism this whole
# guard rests on — could be deleted with the suite still green.
#
# Every silent assertion checks rc too: a PreToolUse hook exiting 2 blocks the user's tool
# call, and "no output" alone cannot tell that apart from a clean pass.
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

newrepo() {  # newrepo <path> <initial-branch>
  git init -q -b "$2" "$1"
  git -C "$1" config user.email t@t.t
  git -C "$1" config user.name t
  git -C "$1" commit -q --allow-empty -m init
}

# Absolute, so the fail-open case can strip PATH without losing the interpreter itself.
BASHBIN="$(command -v bash)"

# run <payload> <project_dir> [env assignments...] — feed a payload, set $out/$rc.
run() { rc=0; out="$(printf '%s' "$1" | env CLAUDE_PROJECT_DIR="$2" "${@:3}" "$BASHBIN" "$GUARD" 2>/dev/null)" || rc=$?; }

payload() {  # payload <file_path> [session_id]
  jq -nc --arg p "$1" --arg s "${2:-}" \
    '{tool_name:"Write", tool_input:{file_path:$p}} + (if $s == "" then {} else {session_id:$s} end)'
}

warned() { printf '%s' "$1" | grep -q 'worktree-isolation-guard'; }
# denied <json> — true only if permissionDecision:deny is nested under hookSpecificOutput
# (documented PreToolUse schema). A top-level permissionDecision is silently ignored by
# Claude Code, so this must NOT match on substring alone.
denied() { printf '%s' "$1" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; }
silent() { [ -z "$out" ] && [ "$rc" -eq 0 ]; }

# --- fixtures ---------------------------------------------------------------
# MAIN: main checkout on `main`, a .gitignore, plus a linked worktree on a feature branch.
MAIN="$WORK/main-repo"
newrepo "$MAIN" main
printf 'ignored/\n' >"$MAIN/.gitignore"
git -C "$MAIN" add -A
git -C "$MAIN" commit -qm ignore
mkdir -p "$MAIN/ignored"
WT="$WORK/wt"
git -C "$MAIN" worktree add -q -b feat/x "$WT"

# FLIP: the branches swapped — main checkout on a FEATURE branch, linked worktree holding the
# DEFAULT branch. Only the git-dir vs git-common-dir comparison can keep the worktree silent
# here, so this is the case that fails if that comparison is ever removed.
FLIP="$WORK/flip-repo"
newrepo "$FLIP" main
FLIPWT="$WORK/flip-wt"
# Move the main checkout off `main` FIRST — git refuses to check a branch out twice, and a
# failed `worktree add` would leave the case passing on a missing directory instead.
git -C "$FLIP" checkout -q -b feat/z
git -C "$FLIP" worktree add -q "$FLIPWT" main
[ -d "$FLIPWT" ] || { printf 'fixture FLIPWT missing\n' >&2; exit 1; }

# TRUNK: no `main` checked out; origin/HEAD points at origin/trunk. It also carries a local
# `main` branch, so the fallback would pick the WRONG answer if origin/HEAD were ignored.
TRUNK="$WORK/trunk-repo"
newrepo "$TRUNK" trunk
git -C "$TRUNK" branch main
git -C "$TRUNK" update-ref refs/remotes/origin/trunk "$(git -C "$TRUNK" rev-parse HEAD)"
git -C "$TRUNK" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk

# MASTER: no origin, default branch is `master` (the fallback's second name).
MASTER="$WORK/master-repo"
newrepo "$MASTER" master

# OTHER: a second repo on its default branch, standing in for ~/vault — a repo the session
# writes to routinely but is not working, where `git worktree add` is no remedy.
OTHER="$WORK/other-repo"
newrepo "$OTHER" main

BARE="$WORK/bare.git"
git init -q --bare -b main "$BARE"

# --- fire path --------------------------------------------------------------
run "$(payload "$MAIN/a.md" s1)" "$MAIN"
{ warned "$out" && [ "$rc" -eq 0 ]; } && ok "main checkout + default branch → warn" \
  || bad "main checkout + default branch → warn (out=$out rc=$rc)"

# A not-yet-existing nested parent must still resolve to the repo.
run "$(payload "$MAIN/new/deep/b.md" s2)" "$MAIN"
warned "$out" && ok "nonexistent nested parent → warn" || bad "nested parent (out=$out)"

# A session running INSIDE a worktree still owns the main checkout it must not write.
run "$(payload "$MAIN/a.md" s3)" "$WT"
warned "$out" && ok "session in worktree writing the main checkout → warn" || bad "worktree→main (out=$out)"

# origin/HEAD wins over the main/master fallback.
run "$(payload "$TRUNK/a.md" s4)" "$TRUNK"
warned "$out" && ok "origin/HEAD default (trunk) → warn" || bad "origin/HEAD default (out=$out)"

run "$(payload "$MASTER/a.md" s5)" "$MASTER"
warned "$out" && ok "master fallback default → warn" || bad "master fallback (out=$out)"

# --- silent paths -----------------------------------------------------------
run "$(payload "$FLIPWT/a.md" s6)" "$FLIPWT"
silent && ok "linked worktree ON the default branch → silent (main-checkout test alive)" \
  || bad "linked worktree on default branch (out=$out rc=$rc)"

run "$(payload "$WT/a.md" s7)" "$WT"
silent && ok "linked worktree on a feature branch → silent" || bad "linked worktree (out=$out rc=$rc)"

run "$(payload "$FLIP/a.md" s8)" "$FLIP"
silent && ok "main checkout on feature branch → silent (documented gap)" || bad "feature branch (out=$out rc=$rc)"

run "$(payload "$MAIN/ignored/x.md" s9)" "$MAIN"
silent && ok "git-ignored path → silent" || bad "ignored path (out=$out rc=$rc)"

run "$(payload "$OTHER/a.md" s10)" "$MAIN"
silent && ok "another repo on its default branch (vault case) → silent" || bad "other repo (out=$out rc=$rc)"

run "$(payload "$MAIN/.git/hooks/pre-commit" s11)" "$MAIN"
silent && ok "write inside .git/ → silent" || bad ".git write (out=$out rc=$rc)"

run "$(payload "$BARE/x" s12)" "$BARE"
silent && ok "bare repo → silent (no working tree to isolate)" || bad "bare repo (out=$out rc=$rc)"

run "$(payload "$WORK/not-a-repo/x.md" s13)" "$MAIN"
silent && ok "outside any repo → silent" || bad "non-repo (out=$out rc=$rc)"

run '{"tool_name":"Write","tool_input":{}}' "$MAIN"
silent && ok "no file_path → silent" || bad "no file_path (out=$out rc=$rc)"

git -C "$MAIN" checkout -q --detach
run "$(payload "$MAIN/a.md" s14)" "$MAIN"
silent && ok "detached HEAD → silent" || bad "detached HEAD (out=$out rc=$rc)"
git -C "$MAIN" checkout -q main

# An inherited GIT_DIR must not redirect the lookups at another repository.
run "$(payload "$WT/a.md" s15)" "$WT" env GIT_DIR="$MAIN/.git"
silent && ok "inherited GIT_DIR ignored → worktree still silent" || bad "GIT_DIR (out=$out rc=$rc)"

# Fail open: no jq, no git, no unbound-variable crash — never block on a missing tool.
run "$(payload "$MAIN/a.md" s16)" "$MAIN" env PATH=/nonexistent
silent && ok "jq/git absent → fail open, silent" || bad "fail open (out=$out rc=$rc)"

run "$(payload "$MAIN/a.md" s17)" "$MAIN" env -u HOME
[ "$rc" -eq 0 ] && ok "unset HOME → no crash (rc=0)" || bad "unset HOME (out=$out rc=$rc)"

# --- path resolution --------------------------------------------------------
run "$(jq -nc --arg c "$MAIN" '{tool_name:"Write",tool_input:{file_path:"a.md"},cwd:$c,session_id:"s18"}')" "$MAIN"
warned "$out" && ok "relative path + cwd → warn" || bad "relative path (out=$out)"

run "$(payload '~/a.md' s19)" "$MAIN" env HOME="$MAIN"
warned "$out" && ok "~ expansion → warn" || bad "~ expansion (out=$out)"

# --- mode matrix ------------------------------------------------------------
run "$(payload "$MAIN/a.md" s20)" "$MAIN" env CLAUDE_KIT_WORKTREE_GUARD=off
silent && ok "off mode → no-op" || bad "off mode (out=$out rc=$rc)"

run "$(payload "$MAIN/a.md" s21)" "$MAIN" env CLAUDE_KIT_WORKTREE_GUARD=enforce
denied "$out" && ok "enforce mode → deny" || bad "enforce mode → deny (out=$out)"

run "$(payload "$MAIN/a.md" s22)" "$MAIN"
{ warned "$out" && ! denied "$out"; } && ok "warn mode (default) → systemMessage only, never deny" \
  || bad "warn mode (out=$out)"

# --- dedup ------------------------------------------------------------------
run "$(payload "$MAIN/a.md" dup)" "$MAIN"
warned "$out" || bad "dedup: first call should warn (out=$out)"
run "$(payload "$MAIN/b.md" dup)" "$MAIN"
silent && ok "dedup: same session + repo → silent on second write" || bad "dedup second (out=$out rc=$rc)"
run "$(payload "$TRUNK/a.md" dup)" "$TRUNK"
warned "$out" && ok "dedup is per-repo: same session, other repo → warns" || bad "dedup per-repo (out=$out)"
run "$(payload "$MAIN/a.md" other-session)" "$MAIN"
warned "$out" && ok "dedup is per-session: new session → warns again" || bad "dedup per-session (out=$out)"

# A payload with no session_id must never dedup itself into permanent silence.
run "$(payload "$MAIN/a.md")" "$MAIN"
warned "$out" || bad "no session_id: first call should warn (out=$out)"
run "$(payload "$MAIN/a.md")" "$MAIN"
warned "$out" && ok "no session_id → no dedup (warns every time)" || bad "no session_id repeat (out=$out)"

# enforce must deny EVERY offending write — a deny that fires once and goes quiet is worse
# than no guard, because the agent just re-issues the same Write.
run "$(payload "$MAIN/a.md" enf)" "$MAIN" env CLAUDE_KIT_WORKTREE_GUARD=enforce
denied "$out" || bad "enforce dedup: first call should deny (out=$out)"
run "$(payload "$MAIN/a.md" enf)" "$MAIN" env CLAUDE_KIT_WORKTREE_GUARD=enforce
denied "$out" && ok "enforce never dedups: same session + same file → denies again" \
  || bad "enforce dedup second (out=$out)"

# ---------------------------------------------------------------------------
printf '\n'
if [ "$FAIL" -gt 0 ]; then
  printf 'FAILED: %d passed, %d failed\n' "$PASS" "$FAIL" >&2
  exit 1
fi
printf 'OK: all worktree-isolation-guard cases passed (%d)\n' "$PASS"
exit 0
