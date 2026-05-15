# telemetry — claude-kit Phase 1 local dogfooding

This directory holds the local-only event logger and analysis scripts used
to dogfood the three claude-kit plugins (thinking-tools,
obsidian-vault-manager, vault-bridge). It is **not** part of any plugin's
runtime surface — hooks are registered in your personal
`.claude/settings.local.json` (gitignored), so other users see nothing.

Phase 1 boundary: no remote transmission, no exposure to other users, no
plugin manifest modification. Phase 2/3 evolution lives in
`docs/discussions/20260512_telemetry-instrumentation/plan.md` §10.

## Measurement scope — Option A (project-local)

Hooks are registered in `.claude/settings.local.json`, which means the
logger only fires when Claude Code is started inside the claude-kit
repo (cwd-based). Sessions in other repos are **not** measured.

The discussion §2.1 originally floated "capture external plugins too as
a comparison cohort" — that maps to Option B (registering hooks in the
global `~/.claude/settings.json`). We chose A because:

- the plan §6.2 specifies project-local explicitly,
- it keeps the dogfooding window clearly scoped to claude-kit work,
- Phase 2's opt-in UX work stays cleanly separable from Phase 1 N=1.

Migrating to B later is a one-minute copy of the `hooks` block into
`~/.claude/settings.json`. If during W2-W4 the cross-context data turns
out to be load-bearing, do that.

## Quick start

```bash
# 1. Enable logging in your shell profile (~/.zshrc or equivalent)
export CLAUDE_KIT_TELEMETRY=1

# 2. Hooks are already registered in .claude/settings.local.json after
#    running the W1 D1-D2 MVP install. Restart Claude Code if it was open.

# 3. Do normal work. Events accumulate in telemetry/events/events-YYYY-MM-DD.jsonl

# 4. Inspect
python3 telemetry/scripts/validate-schema.py --since=7d
python3 telemetry/scripts/report.py --top=10
python3 telemetry/scripts/sequence.py --n=2 --top=20
```

## Files

| Path | Tracked | Purpose |
|------|---------|---------|
| `event-logger.sh` | yes | Single dispatch handler. Reads hook stdin, appends jsonl. |
| `plugin-map.json` | yes | Bare skill/agent name → plugin lookup. |
| `scripts/validate-schema.py` | yes | Required-field check + PIPE_BUF size guard. |
| `scripts/report.py` | yes | Top events, outcome distribution. |
| `scripts/sequence.py` | yes | Session-scoped n-gram extraction. |
| `events/events-*.jsonl` | **no** | Your local event log (gitignored). |

## Event schema (v1)

```json
{
  "ts": "2026-05-15T08:11:01Z",
  "session_id": "abc123",
  "cwd": "/path/to/repo",
  "plugin": "vault-bridge",
  "event": "skill_invoke",
  "name": "save-session",
  "qualified_name": "vault-bridge:save-session",
  "trigger": "explicit",
  "outcome": "started",
  "tool_use_id": "toolu_01ABC",
  "meta": {}
}
```

| event | hook | source |
|-------|------|--------|
| `skill_invoke` (started/success/error/blocked) | PreToolUse(Skill) / PostToolUse(Skill) | `tool_input.skill` |
| `agent_spawn` (started/success/error) | PreToolUse(Agent) / PostToolUse(Agent) | `tool_input.subagent_type` |
| `command_run` | UserPromptSubmit | first slash-token of prompt |
| `session_start` / `session_end` | SessionStart / SessionEnd | session_id only |
| `stop` | Stop | response-boundary counter |

`outcome` values: `started` (PreToolUse), `success` / `error` / `blocked` (PostToolUse).

## Lock strategy: lockless POSIX O_APPEND

`event-logger.sh` uses a single `printf '%s\n' >> file` per event. POSIX
guarantees atomic offset+write for `O_APPEND` writes ≤ `PIPE_BUF` (4096B
on macOS and Linux). Our schema produces ~400-600B per line — comfortably
inside the atomicity window.

`validate-schema.py` warns at 3500B per line. If that warning ever fires
(e.g. W2 adds a fat `meta`), revisit and add a real lock (`mkdir`-based
atomic, or `flock` if a shared dep becomes acceptable). Until then,
adding locking is over-engineering for this N=1 use case.

`flock` (util-linux) is **not present on macOS by default**. Don't
introduce it as a dependency without re-checking the size guard.

## Phase 2 portability (rev3 Principle #6)

`event-logger.sh` resolves its own directory via `${BASH_SOURCE[0]}`,
not absolute paths. Phase 2 migrates this whole directory under a
plugin's `${CLAUDE_PLUGIN_ROOT}/scripts/`. The 1-line migration map:

```
$CLAUDE_PROJECT_ROOT/telemetry/   →   ${CLAUDE_PLUGIN_ROOT}/scripts/
```

The `.claude/settings.local.json` hook commands DO use absolute paths,
because that file is per-user-machine local. Phase 2 moves hook
registration into a plugin manifest, where `${CLAUDE_PLUGIN_ROOT}` is
substituted by Claude Code at install time.

## Rotation policy

`report.py` triggers rotation on every invocation:

- Files older than 30 days → gzip in place (`events-YYYY-MM-DD.jsonl.gz`).
- Files older than 90 days → delete.

(rotation impl is W1 W2 scope; the skeleton currently no-ops.)

## R7 — recover after repo re-clone

`.claude/settings.local.json` is gitignored — if you re-clone or move to a
new machine, hook registration is lost. To restore:

1. Set `CLAUDE_KIT_TELEMETRY=1` in your shell profile.
2. Copy the 8 hook entries from this README's "Hook registration" section
   below into `.claude/settings.local.json` under a `hooks` key.
3. Re-open Claude Code. Verify by triggering any slash command and
   checking that `telemetry/events/events-$(date -u +%F).jsonl` grew.

## Hook registration (paste into `.claude/settings.local.json`)

Replace `/ABS/PATH/TO/claude-kit` with your actual checkout path.

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Skill", "hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh skill_invoke_start"}]},
      {"matcher": "Agent", "hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh agent_spawn_start"}]}
    ],
    "PostToolUse": [
      {"matcher": "Skill", "hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh skill_invoke_end"}]},
      {"matcher": "Agent", "hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh agent_spawn_end"}]}
    ],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh command_run"}]}],
    "Stop":            [{"hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh stop"}]}],
    "SessionStart":    [{"hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh session_start"}]}],
    "SessionEnd":      [{"hooks": [{"type": "command", "command": "/ABS/PATH/TO/claude-kit/telemetry/event-logger.sh session_end"}]}]
  }
}
```

If `settings.local.json` already has `hooks`, merge by event type.

## Debugging

`event-logger.sh` is intentionally silent — failures don't break a turn.
To diagnose, run it manually with a synthetic payload:

```bash
echo '{"session_id":"x","cwd":"/y","tool_input":{"skill":"vault-bridge:save-session"}}' \
  | CLAUDE_KIT_TELEMETRY=1 bash telemetry/event-logger.sh skill_invoke_start
cat telemetry/events/events-$(date -u +%F).jsonl | jq -c .
```

## History — VAULT_BRIDGE_DUMP_PAYLOAD (removed)

The `VAULT_BRIDGE_DUMP_PAYLOAD=1` env-var gate in `vault-bridge/hooks/pre-write-guard.sh` was a single-purpose instrument used during W1 D5 to verify that main-context `Write` payloads carry no agent identifier before flipping `VAULT_BRIDGE_WRITE_CONTRACT` default `warn→enforce`. The flip shipped in vault-bridge v1.10.0 (2026-05-15); the gate was removed in the follow-up cleanup. Trail: `docs/discussions/20260512_telemetry-instrumentation/plan.md` + `docs/plans/unified-dev-plan-2026-05-13.md` §rev3.

## Phase Gate (W4 D28)

Run weekly:

```bash
python3 telemetry/scripts/validate-schema.py --since=7d --strict   # schema stability
python3 telemetry/scripts/report.py --top=10                       # actionable insights
python3 telemetry/scripts/sequence.py --n=2 --top=20               # workflow patterns
```

Phase 2 entry criteria (from plan §10):

- `validate-schema --since=7d` shows zero schema changes in the last week
- `report --top=10` yields ≥3 actionable insights
- ≥1 data-gap area identified for Phase 2 backlog
