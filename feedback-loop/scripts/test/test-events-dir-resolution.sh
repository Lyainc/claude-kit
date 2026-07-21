#!/usr/bin/env bash
# feedback-loop/scripts/test/test-events-dir-resolution.sh
#
# Regression gate for the shared events-dir rule:
#
#     ${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_ROOT:-<git toplevel>}/.claude-kit/telemetry/events}
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
#   1. event-logger.sh run from a subdirectory, CLAUDE_PROJECT_ROOT unset
#      -> event lands at git toplevel, and NO .claude-kit/ appears in the subdir
#   2. CLAUDE_KIT_TELEMETRY_DIR set -> still wins over everything (highest priority)
#   3. CLAUDE_PROJECT_ROOT set -> still wins over the git toplevel
#   4. report.py / validate-schema.py resolve the same dir from a subdirectory
#   5. retro-telemetry.sh reads the toplevel events dir from a subdirectory
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
  printf '{}' | env -u CLAUDE_PROJECT_ROOT -u CLAUDE_KIT_TELEMETRY_DIR \
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

# --- case 3: CLAUDE_PROJECT_ROOT wins over the git toplevel -----------------
PROJ="${FIXTURE}/as-project-root"
mkdir -p "$PROJ"
(
  cd "$SUBDIR" || exit 1
  printf '{}' | env -u CLAUDE_KIT_TELEMETRY_DIR \
    CLAUDE_KIT_TELEMETRY=1 CLAUDE_PROJECT_ROOT="$PROJ" \
    bash "${SCRIPTS_DIR}/event-logger.sh" session_start >/dev/null 2>&1
)
if [ -f "${PROJ}/.claude-kit/telemetry/events/events-${TODAY}.jsonl" ]; then
  _assert "case 3: CLAUDE_PROJECT_ROOT honored over git toplevel" "yes" "yes"
else
  _assert "case 3: CLAUDE_PROJECT_ROOT honored over git toplevel" "yes" "no"
fi

# --- case 4: the Python read side resolves the same dir from a subdirectory --
for PY in report.py validate-schema.py; do
  RESOLVED="$(
    cd "$SUBDIR" || exit 1
    env -u CLAUDE_PROJECT_ROOT -u CLAUDE_KIT_TELEMETRY_DIR python3 -c "
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
# The stamp itself lands in /tmp, not the events dir — but the script exits 0
# early unless `[ -d "$EVENTS_DIR" ]` holds. So the stamp EXISTING is the proof
# that resolution found the toplevel dir case 1 created: under a $PWD-only
# fallback the subdirectory has no events dir, the gate short-circuits, and no
# stamp is ever written.
STAMP_FILE="/tmp/retro-start-test-events-dir.ms"
trash-put "$STAMP_FILE" 2>/dev/null || true
(
  cd "$SUBDIR" || exit 1
  env -u CLAUDE_PROJECT_ROOT -u CLAUDE_KIT_TELEMETRY_DIR \
    CLAUDE_KIT_TELEMETRY=1 CLAUDE_SESSION_ID=test-events-dir \
    bash "${SCRIPTS_DIR}/retro-telemetry.sh" stamp >/dev/null 2>&1
)
if [ -s "$STAMP_FILE" ]; then
  _assert "case 5: retro-telemetry.sh resolves the toplevel events dir" "yes" "yes"
else
  _assert "case 5: retro-telemetry.sh resolves the toplevel events dir" "yes" "no"
fi
trash-put "$STAMP_FILE" 2>/dev/null || true

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
printf 'OK: all events-dir resolution cases passed\n'
