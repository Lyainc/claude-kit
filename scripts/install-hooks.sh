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

awk '/^#   /{sub(/^#   /, ""); print}' scripts/hooks/pre-commit > "$target"
chmod +x "$target"

echo "Installed pre-commit shim -> $target"
