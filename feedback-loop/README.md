# feedback-loop

claude-kit's **self-improvement loop** (layer ⑤). It closes the
**measure → review → keep** cycle — it is **NOT** an execution or iteration
engine (it does not run your tasks, drive a loop, or replace OMC `/loop` / ralph).
It *measures* what claude-kit did, helps you *review* it, and turns the signal
into *kept* improvements.

Two pieces ship together:

- **`retro` skill** — a session retrospective. Re-confirms vault promotion
  candidates (obsidian-vault-manager `audit` E8) behind a **user-confirmed** gate,
  then routes findings to three opt-in outputs: **action** (a git issue),
  **memory** (a ready-to-run `/vault-save` slash command), **rule** (a ready-to-run
  `/distill` slash command — a pattern only `retro` observed has been judged
  worth keeping by nobody yet, so it goes to the judge before the landfill
  engine, #459). Dedups repeats and caps work with a retro budget.
- **telemetry** — an opt-in local event logger (`scripts/event-logger.sh`) plus
  analysis scripts (`report.py`, `sequence.py`, `validate-schema.py`). It records
  which skills/agents/commands ran so `retro` (and you) can spot waste and dead
  surfaces.

## Definition — project-unit, nudge-only, zero local dependency (#229)

feedback-loop is scoped **per project**, not per machine. Telemetry events are
written under the project's own tree (`${CLAUDE_PROJECT_DIR}/.claude-kit/...`, see
*Events directory*) and `retro` reviews that project's signal. There is no
machine-global state and no shared store across projects.

The only coupling the design **permits** to the developer's **machine-level policy
base** (the *local-harness* MVP at `~/.claude/rules/`) is a **user-confirmed nudge** —
never an import, fetch, or shared store. What ships today is the project-scoped half:
`retro` surfaces a rule candidate behind a user-confirmed gate and hands it to
`distill` → `add-policy`, which owns where it lands. The further step — *promoting* a recurring project rule up to the
machine-level base — is the **deferred (YAGNI)** form of that same bridge (it lands
only once there are 2+ projects and a real drift event). Either way it is a
**suggestion you confirm** (carried by the `rule_fire` data contract), never a runtime
or build dependency.

**Zero local dependency = portability.** Because the bridge is nudge-only,
feedback-loop runs **identically on a machine that has no local-harness at all** —
nothing imports it, nothing fetches it, nothing breaks when it is absent. This is the
externally-distributable half of layer ⑤: a public install must work for users who
have never heard of local-harness. (Strong coupling to the machine base is therefore
forbidden — it would break that portability.) Canonical statement of this boundary:
[`docs/design/claude-kit-boundary.md`](../docs/design/claude-kit-boundary.md) §0.

## Privacy & cost — read this

The telemetry hooks are registered in this plugin's manifest, so **the hook is
invoked every session once the plugin is installed**. But it does **nothing**
unless you opt in:

- **`CLAUDE_KIT_TELEMETRY` is unset → silent exit.** The handler writes nothing,
  transmits nothing. No file is created, no event is logged.
- **`CLAUDE_KIT_TELEMETRY=1` → local append only.** Events append to a
  **user-writable local directory** on your machine. Nothing is ever transmitted
  off-machine.
- **Zero per-turn LLM cost (CON-2).** The hooks are deterministic shell — no model
  call, ever. They cannot loop or add token cost.

To enable:

```bash
export CLAUDE_KIT_TELEMETRY=1   # in your shell profile (~/.zshrc, etc.)
```

## Events directory

Events go to a **user-writable** path (never the plugin install cache). The single
resolution rule is shared by the logger, `retro`, and the analysis scripts:

```
${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_DIR}/.claude-kit/telemetry/events}
```

- `CLAUDE_KIT_TELEMETRY_DIR` — explicit override (highest priority).
- otherwise `${CLAUDE_PROJECT_DIR}/.claude-kit/telemetry/events` (falls back to the
  git toplevel, then the CWD, when `CLAUDE_PROJECT_DIR` is unset — plain CWD would
  scatter event dirs across subdirectories when a hook fires from one).

`.claude-kit/` is gitignored, so events are never committed.

## Inspect

```bash
python3 feedback-loop/scripts/validate-schema.py --since=7d   # schema health
python3 feedback-loop/scripts/report.py --top=10              # top events, outcomes, latency, skill lifecycle
                                                                #   (liveness events like rule_fire excluded from
                                                                #   outcomes/Top N by default; --top-include-liveness to include)
python3 feedback-loop/scripts/sequence.py --n=2 --top=20      # repeated n-gram patterns (review-round churn)
```

## Files

| Path | Tracked | Purpose |
|------|---------|---------|
| `.claude-plugin/plugin.json` | yes | Manifest. Registers the 8 telemetry hooks (Skill/Agent Pre+Post, UserPromptSubmit, Stop, SessionStart, SessionEnd). |
| `skills/retro/SKILL.md` | yes | The retro skill (measure→review→keep loop closure). |
| `scripts/event-logger.sh` | yes | Single dispatch handler. Reads hook stdin, appends jsonl. Opt-in, silent, lockless. |
| `scripts/plugin-map.json` | yes | Bare skill/agent name → plugin lookup. |
| `scripts/report.py` | yes | Top events, outcome distribution, per-event latency, skill-lifecycle view. |
| `scripts/sequence.py` | yes | Session-scoped n-gram extraction (untested-by-design; best-effort). |
| `scripts/validate-schema.py` | yes | Required-field check + PIPE_BUF size guard. |
| `${events dir}/events-*.jsonl` | no | Your local event log (user-writable, gitignored). |

## Event schema (v1)

```json
{
  "ts": "2026-05-15T08:11:01Z",
  "session_id": "abc123",
  "cwd": "/path/to/repo",
  "plugin": "vault-bridge",
  "event": "skill_invoke",
  "name": "vault-commit",
  "qualified_name": "vault-bridge:vault-commit",
  "trigger": "explicit",
  "outcome": "success",
  "tool_use_id": "toolu_01ABC",
  "meta": { "duration_ms": 1234, "input_tokens": 500, "output_tokens": 120, "cache_read_tokens": 42, "cache_creation_tokens": 17, "model": "claude-sonnet-5" }
}
```

`meta.model` (#511): PostToolUse payloads carry no model field at all — only `session_start`
does. `event-logger.sh` caches it there (session-scoped, keyed by `session_id`, under
`${events dir}/.session-model/`) and `extract_end_meta` relays it into `skill_invoke_end` /
`agent_spawn_end` events. Omitted when the session never fired `session_start` with telemetry
on, or when the payload didn't carry a model. Cache files older than 2 days are swept on the
next `session_start` (#514), so `.session-model/` stays bounded to recent sessions.

| event | hook | source |
|-------|------|--------|
| `skill_invoke` (started/success/error/blocked) | PreToolUse(Skill) / PostToolUse(Skill) | `tool_input.skill` |
| `agent_spawn` (started/success/error) | PreToolUse(Task\|Agent) / PostToolUse(Task\|Agent) | `tool_input.subagent_type` |
| `command_run` | UserPromptSubmit | first slash-token of prompt |
| `session_start` / `session_end` | SessionStart / SessionEnd | session_id only |
| `stop` | Stop | response-boundary counter |
| `rule_fire` | `event-logger.sh rule_fire` (emitted by any work-rule guard) | rule_id / severity / file (all optional) |

`outcome` values: `started` (PreToolUse), `success` / `error` / `blocked`
(PostToolUse), `fired` (rule_fire). All inner `meta` keys are optional — only the
`meta: {}` envelope is required. `rule_fire` (#216 c8) is owned here as a schema
(data contract); emitters only *emit* to it — they never import feedback-loop code,
so CON-5 (one-way dependency) is preserved.

**rule_fire emit convention (G20, enforcement-liveness measurement)**: any work-rule
guard — a `check-*.py` violation, a task-end reminder, or a **landed add-policy hook
guard** — records that it *fired* by shelling out to the logger:

```bash
printf '%s' '{"meta":{"rule_id":"<id>","severity":"hard","file":"<f>"}}' \
  | bash "$CLAUDE_PROJECT_DIR/feedback-loop/scripts/event-logger.sh" rule_fire
```

This is a **process call, not a code import** (CON-5 emit-only). The logger lifts
`meta.rule_id` into `name`/`qualified_name`, so `report.py` counts fires per rule
(`report.py --format=json` → `rule_fire: {<id>: <count>}`). **Honesty bound (G20
consensus gate)**: a fire = a violation was *caught*, NOT that the rule was *followed*
— a perfectly-obeyed rule fires zero times, and a 0-fire rule is invisible here (no
landed-rule registry to diff against). `report.py` ships this caveat inline; the
rule_fire view is an enforcement-**liveness** tally, never a compliance measure.
`scripts/no-pyyaml-guard.sh` is the reference emitter.

**Aggregation treatment of liveness events (#491)**: `report.py` never mixes a
liveness-type event (today, `rule_fire` is the only one — see `LIVENESS_EVENTS` in
`report.py`) into the outcome mix or the Top N ranking by default. A real 7d
measurement window showed `rule_fire` alone at 52% of all events, which would drown
out real skill/agent/command usage signal in both views. Instead:

- the outcome mix (`Outcomes: {...}` / json `outcomes`) always excludes liveness
  events — they render on their own `Liveness (...)` line (table) / `liveness` key
  (json) instead, so a fire count is never misread as a normal outcome share;
- Top N excludes liveness events by default; pass `--top-include-liveness` to fold
  them back in when you deliberately want the undifferentiated view.

Any future event added to `LIVENESS_EVENTS` gets the same treatment automatically.

## Lock strategy: lockless POSIX O_APPEND

`event-logger.sh` uses a single `printf '%s\n' >> file` per event. POSIX
guarantees atomic offset+write for `O_APPEND` writes ≤ `PIPE_BUF` (4096B on macOS
and Linux). Our schema produces ~400-600B per line — comfortably inside the
atomicity window. `validate-schema.py` warns at 3500B per line; if that ever
fires, revisit and add a real lock. `flock` (util-linux) is **not** present on
macOS by default — don't introduce it without re-checking the size guard.

## Boundary (CON-5)

`feedback-loop` is a layer-⑤ harness-class plugin even though it is externally
distributed (deployment unit ≠ layer). It only **reads leaf OUTPUT** — audit E8
findings, the vault-bridge manifest, telemetry events — and **invokes** leaf
capabilities via user-initiated slash commands. It never modifies leaf-plugin
code, and no leaf depends back on it. The single source of truth for the boundary
is [`docs/design/claude-kit-boundary.md`](../docs/design/claude-kit-boundary.md)
§3 / §5.
