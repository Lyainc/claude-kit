#!/usr/bin/env bash
# claude-kit work-rules — no-PyYAML guard (PreToolUse Write|Edit hook).
#
# ⚠️ DOGFOOD ARTIFACT (G20 #258, 2026-06-23): emitted by the `add-policy` landfill
# engine as its FIRST real dogfood. Uncommitted, NOT self-registered — a reviewable
# specimen the main context keeps or discards. It is also the concrete hook-site
# example G20 attaches a `rule_fire` telemetry emission to (see the goal-doc).
#
# Rule landed: "claude-kit Python scripts must NOT import PyYAML — parse frontmatter
# with stdlib only." This is a REAL, stated-in-comments-but-unenforced convention
# (several scripts declare "stdlib only, no PyYAML" in comments — e.g. generate-manifest.py —
# and all repo .py files comply, but no guard enforced it). Classification (add-policy engine):
#   layer = work-rule (how the work is done) ·
#   tier  = HARD (the violation `import yaml` is deterministically grep-detectable) ·
#   site  = hook (PreToolUse Write|Edit) — HARD ⇒ hook, per the engine's tier→site map.
#
# Fires on every PreToolUse Write|Edit. It acts ONLY when the target is a *.py file
# whose written content introduces a PyYAML import; every other write is allowed.
# Deterministic shell — zero per-turn LLM cost (CON-2). Fails OPEN when jq is absent
# (a missing tool must never block a legitimate write) and nudges to install it.
#
# Mode (env): CLAUDE_KIT_NO_PYYAML_CONTRACT = enforce (default) | warn | off.
#   enforce — deny the write (permissionDecision:deny) + systemMessage.
#   warn    — allow but emit a stderr CONTRACT WARNING.
#   off     — no-op.
#
# Detection scope (honest): it matches an `import yaml` / `from yaml ...` line in
# command/import position at the start of a logical line (optional indentation),
# NOT inside a string/comment that merely mentions "import yaml". Like its sibling
# guards it targets an honest authoring slip, not a deliberate adversary; `importlib`
# dynamic loads and aliased re-exports are out of scope (KNOWN gaps, same family as
# subagent-git-guard.sh's KNOWN_EVASIONS).
#
# Wiring (per-developer; .claude/ is gitignored — NOT auto-registered):
#   { "hooks": { "PreToolUse": [ { "matcher": "Write|Edit", "hooks": [ { "type": "command",
#       "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/no-pyyaml-guard.sh\"" } ] } ] } }

set -uo pipefail

MODE="${CLAUDE_KIT_NO_PYYAML_CONTRACT:-enforce}"
[ "$MODE" = "off" ] && exit 0

# jq absent → fail open (never block a write because a tool is missing).
if ! command -v jq >/dev/null 2>&1; then
  printf '[no-pyyaml-guard] jq not found — guard inert; install jq to enable.\n' >&2
  exit 0
fi

PAYLOAD="$(cat 2>/dev/null || printf '{}')"
[ -n "$PAYLOAD" ] || PAYLOAD='{}'

FILE_PATH="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
[ -n "$FILE_PATH" ] || exit 0

# Only guard Python files.
case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

# Write carries .content; Edit carries .new_string. Concatenate whatever is present.
CONTENT="$(printf '%s' "$PAYLOAD" | jq -r '[.tool_input.content, .tool_input.new_string] | map(select(. != null)) | join("\n")' 2>/dev/null || true)"
[ -n "$CONTENT" ] || exit 0

# Match a PyYAML import at logical-line start (optional indentation), not in prose.
if ! printf '%s' "$CONTENT" | grep -Eq '^[[:space:]]*(import[[:space:]]+yaml([[:space:]]|$|\.)|from[[:space:]]+yaml[[:space:]]+import)'; then
  exit 0
fi

reason="$(basename "$FILE_PATH") introduces a PyYAML import — claude-kit Python is stdlib-only (no PyYAML). Parse frontmatter with the stdlib pattern (see generate-manifest.py). This keeps scripts dependency-free and runnable on a vanilla Python."

# Telemetry (G20 #258, best-effort): the rule fired — emit a rule_fire liveness event so
# report.py can count how often this guard catches a violation. EMIT-ONLY (CON-5): a
# PROCESS call to feedback-loop's logger, never a code import — feedback-loop pulls in no
# guard code. The logger self-gates on CLAUDE_KIT_TELEMETRY=1 (silent + no LLM otherwise),
# so this is a no-op unless telemetry is opted in. Wrapped to NEVER break the guard.
# (Fires in both warn and enforce: the rule was violated either way.)
_LOGGER="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || printf '.')}/feedback-loop/scripts/event-logger.sh"
if [ -f "$_LOGGER" ]; then
  _rf="$(jq -nc --arg f "$(basename "$FILE_PATH")" --arg cwd "$PWD" \
    '{session_id:"", cwd:$cwd, meta:{rule_id:"no-pyyaml", severity:"hard", file:$f}}' 2>/dev/null || true)"
  [ -n "$_rf" ] && printf '%s' "$_rf" | bash "$_LOGGER" rule_fire >/dev/null 2>&1 || true
fi

if [ "$MODE" = "warn" ]; then
  printf '[no-pyyaml-guard] CONTRACT WARNING: %s\n' "$reason" >&2
  exit 0
fi

# enforce (default): deny the write. permissionDecisionReason drives the deny dialog;
# systemMessage surfaces the override knob. (Native form matches subagent-git-guard.sh.)
jq -nc --arg reason "$reason" \
  '{permissionDecision:"deny", permissionDecisionReason:$reason, systemMessage:("no-pyyaml-guard: " + $reason + " Set CLAUDE_KIT_NO_PYYAML_CONTRACT=warn to allow, =off to disable.")}'
exit 0
