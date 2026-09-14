#!/usr/bin/env bash
# One exit status for this paired-repo Codex close-loop slice. It touches only temporary HOME
# fixtures in local-harness; fresh runtime execution remains the separately authorized smoke.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARNESS_DIR="${LOCAL_HARNESS_DIR:-$REPO_DIR/../local-harness}"

[ -x "$HARNESS_DIR/rules/run-tests.sh" ] || {
  echo "FAIL: local-harness rules/run-tests.sh is required: $HARNESS_DIR" >&2
  exit 2
}

(
  cd "$REPO_DIR"
  python3 scripts/check-codex-portability.py
  uv run --with tiktoken python3 scripts/check-skill-token-budget.py --self-test
  uv run --with tiktoken python3 scripts/check-skill-token-budget.py
  python3 feedback-loop/scripts/test/test-codex-portability.py
  bash feedback-loop/scripts/test/test-retro-telemetry.sh
  python3 feedback-loop/scripts/test/test-distill-gate-routing.py
  python3 feedback-loop/scripts/test/test-add-policy-routing.py
  python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py
  python3 feedback-loop/scripts/test/test-add-policy-necessity-gate.py
)

(
  cd "$HARNESS_DIR"
  LOCAL_HARNESS_CHECK_CODEX_SESSION=1 bash rules/run-tests.sh
)

echo "PASS: Codex close-loop source, install, and discovery checks"
