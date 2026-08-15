#!/usr/bin/env bash
# install-hooks.sh — install the tracked pre-commit shim into .git/hooks/pre-commit (#651).
#
# .git/hooks is untracked and shared by every linked worktree, so the shim that execs
# scripts/hooks/pre-commit (#637) has no install path today: a fresh clone, CI, or another
# contributor's machine never gets it. This is the one documented install step
# (CONTRIBUTING.md Prerequisites runs it) — extracts the shim text VERBATIM from
# scripts/hooks/pre-commit's own header comment (the "Install it verbatim:" block), so
# there is exactly one place that shim is authored. Edit it there, not here.
#
# Verification: scripts/check-hooks-installed.py confirms the installed copy still
# matches this source (P12 — existence is not enough).
set -eu

root=$(git rev-parse --show-toplevel)
cd "$root"

hooks_dir=$(git rev-parse --git-common-dir)/hooks
mkdir -p "$hooks_dir"
target="$hooks_dir/pre-commit"

# Extract to a temp file and move it into place only on success. Redirecting straight into
# $target truncates it BEFORE awk runs, and .git/hooks is shared by every linked worktree —
# so running this from a worktree whose branch lacks scripts/hooks/pre-commit would leave a
# 0-byte executable hook behind for the whole repo, which git runs and which exits 0: the
# #637 guard silently off everywhere. Same reason for the non-empty check: a reformatted
# header block would otherwise install an empty hook and report success.
tmp="${target}.tmp.$$"
trap 'rm -f "$tmp"' EXIT
awk '/^#   /{sub(/^#   /, ""); print}' scripts/hooks/pre-commit > "$tmp"
if [ ! -s "$tmp" ]; then
  echo "ERROR: no shim found in scripts/hooks/pre-commit — expected the '#   '-indented" >&2
  echo "       block under 'Install it verbatim:'. Nothing was installed." >&2
  exit 1
fi

# Never destroy a hook this repo did not write: back up anything already there that is not
# the shim we are about to install (a contributor's own pre-commit), since .git/hooks is
# untracked and the loss would be unrecoverable.
if [ -e "$target" ] && ! cmp -s "$tmp" "$target"; then
  mv -f "$target" "$target.bak"
  echo "Existing pre-commit hook backed up -> $target.bak"
fi

mv -f "$tmp" "$target"
chmod +x "$target"

echo "Installed pre-commit shim -> $target"
