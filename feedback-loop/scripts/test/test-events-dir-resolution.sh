#!/usr/bin/env bash
# feedback-loop/scripts/test/test-events-dir-resolution.sh
#
# Regression gate for the shared events-dir rule:
#
#     ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_DIR:-<git toplevel>}/.claude-kit/telemetry/events}
#
# The bug this pins: the fallback used to be plain `$PWD`. A hook fires with
# whatever CWD it happens to have, so any hook invoked from a subdirectory built
# its own `.claude-kit/telemetry/` there. Five stray copies had accumulated in
# this repo before the fix — one of them under `.github/ISSUE_TEMPLATE/`.
#
# The rule is duplicated across four scripts by the leaf-standalone convention
# (no shared import), so a partial revert would silently split writers from
# readers. All four are asserted here:
#   write side — event-logger.sh, retro-telemetry.sh
#   read side  — report.py, validate-schema.py
#
# Cases:
#   1. event-logger.sh run from a subdirectory, CLAUDE_PROJECT_DIR unset
#      -> event lands at git toplevel, and NO .claude-kit/ appears in the subdir
#   2. CLAUDE_KIT_TELEMETRY_DIR set -> still wins over everything (highest priority)
#   3. CLAUDE_PROJECT_DIR set -> still wins over the git toplevel
#   4. report.py / validate-schema.py resolve the same dir from a subdirectory
#   5. retro-telemetry.sh reads the toplevel events dir from a subdirectory
#   6. CLAUDE_PROJECT_DIR set to repo A while CWD has `cd`-drifted into an
#      unrelated repo B -> events land under A, never under B's toplevel (#533 —
#      a prior revision spelled the var CLAUDE_PROJECT_ROOT, which the harness
#      never sets, so this branch silently never fired and every hook fell to
#      git-toplevel-of-CWD; a session that `cd`s into e.g. an Obsidian vault
#      mid-session then wrote telemetry into that unrelated repo)
#
# Standalone-runnable. Exits non-zero on any assertion failure.
#
# Note on `env`: every `-u` must precede the first NAME=VALUE. env treats the
# first argument containing `=` as the start of the assignment list, so a `-u`
# placed after one is parsed as the command name and the unset silently no-ops.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${SCRIPT_DIR}/.."

FAILED=0
_assert() {
  # _assert <description> <expected> <actual>
  if [ "$2" = "$3" ]; then
    return 0
  fi
  printf 'FAIL: %s\n  expected: %s\n  actual:   %s\n' "$1" "$2" "$3" >&2
  FAILED=1
}

if ! command -v jq >/dev/null 2>&1; then
  printf 'FAIL: jq not found on PATH (required by event-logger.sh)\n' >&2
  exit 1
fi

# --- fixture: a throwaway git repo with a nested subdirectory ---------------
FIXTURE="$(mktemp -d)"
# macOS mktemp hands back /var/..., a symlink to /private/var. `git rev-parse
# --show-toplevel` resolves symlinks, so compare against the resolved form or
# every assertion fails on a path that is actually correct.
FIXTURE="$(cd "$FIXTURE" && pwd -P)"
trap 'trash-put "$FIXTURE" 2>/dev/null || true' EXIT

git -C "$FIXTURE" init -q 2>/dev/null || { printf 'FAIL: git init failed\n' >&2; exit 1; }
SUBDIR="${FIXTURE}/nested/deeper"
mkdir -p "$SUBDIR"

TOPLEVEL_EVENTS="${FIXTURE}/.claude-kit/telemetry/events"
TODAY="$(date -u +%Y-%m-%d)"

# --- case 1: subdirectory CWD, no env override -> git toplevel --------------
(
  cd "$SUBDIR" || exit 1
  printf '{}' | env -u CLAUDE_PROJECT_DIR -u CLAUDE_KIT_TELEMETRY_DIR \
    CLAUDE_KIT_TELEMETRY=1 \
    bash "${SCRIPTS_DIR}/event-logger.sh" session_start >/dev/null 2>&1
)

if [ -f "${TOPLEVEL_EVENTS}/events-${TODAY}.jsonl" ]; then
  _assert "case 1: event lands at git toplevel" "yes" "yes"
else
  _assert "case 1: event lands at git toplevel" "yes" "no (missing ${TOPLEVEL_EVENTS}/events-${TODAY}.jsonl)"
fi

# The regression itself: nothing may be created under the subdirectory.
STRAY="$(find "${FIXTURE}/nested" -type d -name '.claude-kit' 2>/dev/null | head -1)"
_assert "case 1: no stray .claude-kit under the subdirectory" "" "$STRAY"

# --- case 2: CLAUDE_KIT_TELEMETRY_DIR wins over everything ------------------
EXPLICIT="${FIXTURE}/explicit-events"
(
  cd "$SUBDIR" || exit 1
  printf '{}' | env CLAUDE_KIT_TELEMETRY=1 CLAUDE_KIT_TELEMETRY_DIR="$EXPLICIT" \
    bash "${SCRIPTS_DIR}/event-logger.sh" session_start >/dev/null 2>&1
)
if [ -f "${EXPLICIT}/events-${TODAY}.jsonl" ]; then
  _assert "case 2: CLAUDE_KIT_TELEMETRY_DIR honored" "yes" "yes"
else
  _assert "case 2: CLAUDE_KIT_TELEMETRY_DIR honored" "yes" "no"
fi

# --- case 3: CLAUDE_PROJECT_DIR wins over the git toplevel -----------------
PROJ="${FIXTURE}/as-project-root"
mkdir -p "$PROJ"
(
  cd "$SUBDIR" || exit 1
  printf '{}' | env -u CLAUDE_KIT_TELEMETRY_DIR \
    CLAUDE_KIT_TELEMETRY=1 CLAUDE_PROJECT_DIR="$PROJ" \
    bash "${SCRIPTS_DIR}/event-logger.sh" session_start >/dev/null 2>&1
)
if [ -f "${PROJ}/.claude-kit/telemetry/events/events-${TODAY}.jsonl" ]; then
  _assert "case 3: CLAUDE_PROJECT_DIR honored over git toplevel" "yes" "yes"
else
  _assert "case 3: CLAUDE_PROJECT_DIR honored over git toplevel" "yes" "no"
fi

# --- case 4: the Python read side resolves the same dir from a subdirectory --
for PY in report.py validate-schema.py; do
  RESOLVED="$(
    cd "$SUBDIR" || exit 1
    env -u CLAUDE_PROJECT_DIR -u CLAUDE_KIT_TELEMETRY_DIR python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('m', '${SCRIPTS_DIR}/${PY}')
m = importlib.util.module_from_spec(spec)
sys.argv = ['${PY}']
spec.loader.exec_module(m)
print(m.resolve_events_dir())
" 2>/dev/null
  )"
  _assert "case 4 (${PY}): resolves to the git toplevel events dir" \
    "$TOPLEVEL_EVENTS" "$RESOLVED"
done

# --- case 5: retro-telemetry.sh finds the toplevel events dir from a subdir --
# `stamp` prints the epoch-ms start time to stdout ONLY when both gates hold
# (opt-in AND `[ -d "$EVENTS_DIR" ]`) — no file is written at all (#580). So
# non-empty stdout is the proof that resolution found the toplevel dir case 1
# created: under a $PWD-only fallback the subdirectory has no events dir, the
# gate short-circuits, and stamp prints nothing.
STAMP_OUT="$(
  cd "$SUBDIR" || exit 1
  env -u CLAUDE_PROJECT_DIR -u CLAUDE_KIT_TELEMETRY_DIR \
    CLAUDE_KIT_TELEMETRY=1 CLAUDE_SESSION_ID=test-events-dir \
    bash "${SCRIPTS_DIR}/retro-telemetry.sh" stamp 2>/dev/null
)"
if [ -n "$STAMP_OUT" ]; then
  _assert "case 5: retro-telemetry.sh resolves the toplevel events dir" "yes" "yes"
else
  _assert "case 5: retro-telemetry.sh resolves the toplevel events dir" "yes" "no"
fi

# --- case 6 (#533): CLAUDE_PROJECT_DIR set to repo A, CWD drifted into an
# unrelated repo B -> events land under A, nothing appears under B. This is
# the exact shape of the bug: a session working in claude-kit `cd`s into
# ~/vault mid-session (e.g. for /vault-commit), and a hook fires while CWD is
# still B. Wrong var name -> CLAUDE_PROJECT_DIR ignored -> falls to
# git-toplevel-of-CWD -> events land inside the vault repo.
REPO_A="${FIXTURE}/repo-a"
mkdir -p "$REPO_A"
REPO_B="${FIXTURE}/repo-b"
git -C "$FIXTURE" init -q "$REPO_B" 2>/dev/null || { printf 'FAIL: git init repo-b failed\n' >&2; exit 1; }
(
  cd "$REPO_B" || exit 1
  printf '{}' | env -u CLAUDE_KIT_TELEMETRY_DIR \
    CLAUDE_KIT_TELEMETRY=1 CLAUDE_PROJECT_DIR="$REPO_A" \
    bash "${SCRIPTS_DIR}/event-logger.sh" session_start >/dev/null 2>&1
)
if [ -f "${REPO_A}/.claude-kit/telemetry/events/events-${TODAY}.jsonl" ]; then
  _assert "case 6: event lands under CLAUDE_PROJECT_DIR (repo A), not CWD" "yes" "yes"
else
  _assert "case 6: event lands under CLAUDE_PROJECT_DIR (repo A), not CWD" "yes" "no"
fi
_assert "case 6: no .claude-kit/ leaked into the CWD repo (B)" "" \
  "$(find "${REPO_B}" -type d -name '.claude-kit' 2>/dev/null | head -1)"

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
printf 'OK: all events-dir resolution cases passed\n'
