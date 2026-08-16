#!/usr/bin/env bash
# run-audit-dod.sh — single-command wrapper for the audit DoD measurement (#660)
#
# WHY THIS EXISTS: docs/VALIDATION.md and .github/workflows/validate.yml used to run
# this as multiple separate registered commands sharing a hardcoded fixture path
# (/tmp/ovm-fixture-audit-recheck, /tmp/dod.json). check-test-exitcode.py extracts
# each command from a fenced block and runs it in its OWN `bash -c` — shell state
# does NOT survive between commands, so a per-run `D=$(mktemp -d)` on one line is
# invisible on the next. That forced a FIXED shared path, and two worktrees running
# the DoD gate concurrently would create/delete each other's fixture mid-run. The
# failure then surfaced as "seeded_detected drift: E10 E11 E12 E1 E2 E3 E5 E6 E9 all
# 0" — which reads to a human as "my change broke all 10 detectors" when the real
# cause is a torn-down fixture, not a code regression.
#
# FIX: fold the whole sequence into ONE registered command (this script) that owns
# a private, self-created temp dir (mktemp -d, trap-cleaned on exit — mirrors the
# precedent in test-infer-tags-batch.sh). No fixed /tmp path anywhere.
#
# FAILURE-MESSAGE SPLIT (#660): a broken fixture build (gen-fixture.sh failing, the
# audit-validate.py --dod run failing, or an empty/partial dod.json) is reported as
# "FIXTURE ERROR: ..." with exit 2 — visibly distinct from a real DoD invariant
# failure, which is whatever assert-dod.py itself prints, propagated with its own
# exit code. Only assert-dod.py's verdict may be read as "the DoD gate failed."
#
# The marker is printed AFTER the build log, not before it: check-test-exitcode.py keeps
# only the last 500 chars of stderr, and gen-fixture.sh emits 1,815 bytes on a SUCCESSFUL
# run — so a marker printed first is truncated away by a late failure, which is exactly
# the concurrent-teardown case, and the reader is left with generic build noise again.
# The log is tailed for the same reason: the distinguishing line has to survive the cut.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

D="$(mktemp -d)"
trap 'rm -rf "$D"' EXIT

FIXTURE_DIR="$D/fixture"
DOD_JSON="$D/dod.json"

if ! OVM_FIXTURE_DIR="$FIXTURE_DIR" bash "$SCRIPT_DIR/gen-fixture.sh" --with-audit-errors >"$D/gen-fixture.log" 2>&1; then
  tail -n 20 "$D/gen-fixture.log" >&2
  echo "FIXTURE ERROR: could not build the audit fixture (gen-fixture.sh failed) — this is NOT a DoD verdict" >&2
  exit 2
fi

if ! python3 "$SCRIPT_DIR/audit-validate.py" "$FIXTURE_DIR" --dod > "$DOD_JSON" 2>"$D/audit-validate.log"; then
  tail -n 20 "$D/audit-validate.log" >&2
  echo "FIXTURE ERROR: audit-validate.py --dod run failed — this is NOT a DoD verdict" >&2
  exit 2
fi

if [ ! -s "$DOD_JSON" ]; then
  echo "FIXTURE ERROR: dod.json is empty/missing after the --dod run — this is NOT a DoD verdict" >&2
  exit 2
fi

# From here on, any failure is a real DoD invariant failure — let assert-dod.py's
# own stdout/exit code propagate as-is (its final stdout line is the documented
# success text check-test-exitcode.py tail-matches against). NOT `exec` — that
# replaces this shell and the EXIT trap never fires, leaking a 528-file fixture dir
# per run.
python3 "$SCRIPT_DIR/assert-dod.py" "$DOD_JSON"
exit $?
