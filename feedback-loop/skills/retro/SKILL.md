---
name: retro
description: "Session retro for the ⑤ execution loop: turn telemetry waste patterns and this session's own observed waste into confirmed git issues, deduped against existing open issues. Trigger: 회고, 회고해줘, 세션 회고, 낭비 탐색, retro, session retrospective, waste sweep. Routing: vault structural defects only = obsidian-vault-manager /audit; this skill is the ⑤ post-loop consumer that ACTS on telemetry output. Example: '/retro' or '회고해줘'."
model: inherit
allowed-tools: Bash AskUserQuestion
effort: medium
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion prompts, confirmation messages, reports) MUST be in Korean. Instructions below are English for LLM parsing.

# retro — measure → improve loop closure (layer ⑤)

`retro` reads what the leaf layers already produced (the project-local
`telemetry/` dogfooding output, plus this session's own observed waste) and
turns it into *confirmed* git issues. It does NOT detect vault defects itself
(that is `/audit`, layer ④) and performs no vault writes or rule-file edits
(#639 — the memory/rule branches that used to surface `/vault-save`/`/wiki`/
`/distill` were removed as pass-throughs: memory re-suggested the wrap-chain
step just run, and rule handed off to `/distill`, which is directly invocable
and does its own worth-keeping judgment).

## Boundary & safety (constitutional — do not relax)

Single source of truth: [`docs/design/claude-kit-boundary.md`](../../../docs/design/claude-kit-boundary.md) §5.

- **CON-5 one-way dependency**: `retro` only *reads* leaf artifacts (telemetry
  output) and *invokes* leaf capabilities via `gh`. It NEVER modifies
  leaf-plugin code and nothing in a leaf depends back on `retro`.
- **User-confirmed gate (silent forbidden)**: issue filing is proposed as a
  candidate and applied ONLY on explicit user confirmation.

## Phase 1 — COLLECT (gather + dedup)

1. **Collect telemetry in one Bash call** (no dependency between them, #528):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" stamp
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" 2>/dev/null        # outcome/error mix, latency
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sequence.py" --n=2 --top=20 2>/dev/null # A->B repeats
   ```
   - `stamp` prints the Phase-1 start time (epoch ms); **read it and carry it
     forward as `START_MS`** for Phase 2's `emit` — Phase 1/2 are separate
     Bash-tool calls (fresh shell each), so nothing on disk can key the two
     together (#580).
   - `report.py`/`sequence.py` need `.claude-kit/telemetry/events/` +
     `CLAUDE_KIT_TELEMETRY=1`; otherwise fall back to session-observed waste
     only. `sequence.py`'s self-transition "runs" are a length, not a count —
     a short run (2) is review-round churn worth an item; a long run can be a
     skill dispatching isolated subagents by design and not waste (#598).

2. **Waste signals**: from the collected output above plus this session's
   observable waste (repeated failed tool calls, review rounds, same-error
   retries). Each: `{pattern, count, scope}` — `scope` = `harness` (→ harness
   issue) or `local` (→ this-repo issue).

3. **Dedup** (count → `items_deduped`):
   - *Within session*: collapse duplicate `(path, error_type)` pairs.
   - *Cross-run*: before proposing an issue, check existing open issues so a
     repeat isn't filed twice — a comparison-set read, so use the shared cache
     instead of a fresh `gh` call:
     ```bash
     bash "${CLAUDE_PLUGIN_ROOT}/scripts/gh-issues-cache.sh" get
     ```
     Cached ≤5 min old, else fetched live and refreshed. Match candidates
     against the returned titles locally (case-insensitive substring). **Never
     reuse this cache for a live-status render** (a specific PR/issue shown to
     the user) — a cached one already misjudged a merged PR as open
     (2026-07-30). A failed fetch prints `[gh-issues-cache FAILED] ...` and
     exits nonzero (#618) — treat dedup as unknown, not clean: ask the user
     before filing, or skip and note the check couldn't run.

**Output**: `{waste[], items_deduped}`.

---

## Phase 2 — ACT (file + report + telemetry)

1. **File**: for each deduped waste pattern, draft `{title, body}` (evidence:
   counts, event types, scope). Confirm with the user, then `gh issue create`
   — split by scope, harness vs. local trackers never conflated (#134). After
   the last create, invalidate the comparison-set cache so the next dedup
   doesn't compare against a stale backlog (#638):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/gh-issues-cache.sh" invalidate
   ```
2. **Report** (Korean): processed / deduped counts.
3. **Emit telemetry** (best-effort, opt-in), passing `START_MS` from Phase 1
   plus the two counters — the helper owns the opt-in gate, events-dir rule,
   `duration_ms` (now − `START_MS`, `null` if missing), and the 3500B PIPE_BUF
   guard:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" emit "$START_MS" "$PROCESSED" "$DEDUPED"
   ```

---

## Configuration

| Env var | Default | Effect |
|---------|---------|--------|
| `CLAUDE_KIT_TELEMETRY` | unset | `1` enables the Phase-2 telemetry append |

## Rules

- Silent issue filing is FORBIDDEN — user-confirmed.
- `retro` performs zero vault writes and zero rule-file edits — a git issue is
  its only output. Session insights and rule candidates route through
  `/vault-save`/`/wiki` and `/distill` directly, not via `retro`.
- Dedup before filing.
- CON-5: read leaf artifacts only; never modify leaf-plugin code; no reverse dependency.
