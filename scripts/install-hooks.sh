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
#
# Extraction is anchored to the "Install it verbatim:" marker and stops at the first line that
# is not '#   '-indented. An unanchored "every indented line in the file" rule silently welds
# any OTHER indented comment into the hook — and this header is the one place the shim is
# meant to be edited, so that is an ordinary edit, not an exotic one. Measured: one indented
# example line added above the block displaced the shebang off line 1, and the hook then ran
# under the default shell printing an error on every commit.
tmp="${target}.tmp.$$"
trap 'rm -f "$tmp"' EXIT
awk '
  /Install it verbatim:/ { inblock = 1; next }
  inblock && /^#   / { sub(/^#   /, ""); print; next }
  inblock && /^#[ \t]*$/ { next }
  inblock { exit }
' scripts/hooks/pre-commit > "$tmp"
if [ ! -s "$tmp" ] || [ "$(head -n 1 "$tmp")" != "#!/bin/sh" ]; then
  echo "ERROR: no usable shim in scripts/hooks/pre-commit — expected the '#   '-indented" >&2
  echo "       block under 'Install it verbatim:' to start with '#!/bin/sh'. Nothing was" >&2
  echo "       installed." >&2
  exit 1
fi

# Never destroy a hook this repo did not write: back up anything already there that is not
# the shim we are about to install (a contributor's own pre-commit), since .git/hooks is
# untracked and the loss would be unrecoverable.
# A second run must not clobber the first run's backup: that is the run where the original is
# already only in .bak, so overwriting it is the very loss this block prevents.
if [ -e "$target" ] && ! cmp -s "$tmp" "$target"; then
  if [ -e "$target.bak" ]; then
    echo "ERROR: $target holds a hook that is not this shim, and $target.bak already exists." >&2
    echo "       Refusing to overwrite an existing backup — move or delete it, then re-run." >&2
    exit 1
  fi
  mv "$target" "$target.bak"
  echo "Existing pre-commit hook backed up -> $target.bak"
fi

mv -f "$tmp" "$target"
chmod +x "$target"

echo "Installed pre-commit shim -> $target"
