---
name: retro
description: "Session retro for the ⑤ execution loop: route findings (telemetry waste patterns, session insights, validated rule patterns) to 3 opt-in outputs (action→git issue / memory→vault-save suggestion / rule→distill handoff), dedup repeats, and cap work with a retro budget. Trigger: 회고, 회고해줘, 세션 회고, 낭비 탐색, retro, session retrospective, waste sweep. Routing: vault structural defects only = obsidian-vault-manager /audit; this skill is the ⑤ post-loop consumer that ACTS on telemetry output. Example: '/retro' or '회고해줘'."
model: inherit
allowed-tools: Read Edit Bash Grep Glob AskUserQuestion
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion prompts, confirmation messages, reports) MUST be in Korean. Instructions below are English for LLM parsing.

# retro — measure → improve loop closure (layer ⑤)

`retro` is the first consumer that closes claude-kit's measure→improve loop: it
reads what the leaf layers already produced (the project-local `telemetry/`
dogfooding output, plus this session's own observed waste) and turns it into
*confirmed* actions. It does NOT detect vault defects itself (that is `/audit`,
layer ④) and it performs no vault writes of its own — the memory branch only
surfaces a `/vault-save`/`/wiki` command for the user to run.

## Boundary & safety (constitutional — do not relax)

Single source of truth: [`docs/design/claude-kit-boundary.md`](../../../docs/design/claude-kit-boundary.md) §5.

- **CON-5 one-way dependency**: `retro` (harness, ⑤) only *reads* leaf artifacts
  (telemetry output) and *invokes* leaf capabilities. It NEVER modifies
  leaf-plugin code and nothing in a leaf depends back on `retro`.
- **CON-1 / Write Role Contract**: `retro` performs **zero vault writes**. The
  B-layer promotion gate (raw/draft → evergreen `status:` transition) that
  `retro`'s PROMOTE phase used to re-confirm was abolished (v5 §5/§6, #480) —
  `/vault-save` writes no `status:` field at all, so there is nothing left to
  promote. Every vault write is surfaced as a `/vault-save` slash command (raw
  session ore → `sources/`) or `/wiki` (compiled domain knowledge → `wiki/`) for
  the USER to run — `retro` does not write it. (Session knowledge is
  wiki-first: local context is native memory, active recall is `/wiki`; the old
  `/save-session` command was retired #331.)
- **User-confirmed gate (silent forbidden)**: issue filing and rule additions
  are proposed as candidates and applied ONLY on explicit user confirmation.
  Silent auto-file / auto-add is forbidden.

## Pipeline: COLLECT → OUTPUT → BUDGET

The budget (`RETRO_BUDGET`, default 10) caps the total items *processed* in
OUTPUT. Items are processed in priority order (P0 → P1 → P2); when the
budget is exhausted, processing STOPS and the remainder is reported (never
silently dropped). BUDGET is the final accounting + telemetry phase.

**Budget unit (precise):** an item consumes budget only when it is *acted on* —
an issue filed, or a memory/rule action surfaced. Items deduped in COLLECT do
NOT consume budget and are NOT part of the unprocessed remainder count (they
are counted under `items_deduped`, not "미처리").

---

## Phase 1 — COLLECT (gather + dedup + prioritize)

Zero mutation. Produce a deduped, priority-sorted item list.

1. **Read config**: `RETRO_BUDGET` (default 10).

2. **Collect telemetry + prior-retro signals in one Bash call.** These four
   commands share no dependency on one another's output, so run them together
   in a single Bash invocation instead of four separate calls (#528 — cuts 3
   turns off the wrap chain):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" stamp
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" 2>/dev/null        # outcome/error mix, latency (default 7d window)
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sequence.py" --n=2 --top=20 2>/dev/null # A->B repeats; same-label runs listed separately by length
   EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}/.claude-kit/telemetry/events}"
   [ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] && [ -d "$EVENTS_DIR" ] && \
     grep -h '"name":"retro"' "$EVENTS_DIR"/events-*.jsonl 2>/dev/null | tail -n 20
   ```
   - `retro-telemetry.sh stamp` — prints the Phase-1 start time (epoch ms) to
     stdout; **read that value and carry it forward as `START_MS`.** No file
     is written: Phase 1 and Phase 3 are separate Bash-tool calls (fresh
     shell each time), so there is no process/session id stable enough to
     key a shared `/tmp` file on — `$PPID` and `$CLAUDE_SESSION_ID` both
     drift between the two calls in practice, which used to corrupt
     `duration_ms` to `null` and orphan stamp files in `/tmp` (#580). This
     skill is what connects the two calls instead: inline `START_MS` as the
     first argument to the Phase-3 `emit` call below. The helper owns the
     events-dir rule + opt-in gate (shared with
     `feedback-loop/scripts/event-logger.sh`): it prints nothing UNLESS
     telemetry is opted in AND the events dir is resolvable — off either
     gate, `START_MS` is empty and Phase 3's `emit` falls back to
     `duration_ms: null`.
   - `report.py` / `sequence.py` — waste signals (action-branch source). Both
     self-resolve the events dir via the same shared rule and are safe to run
     unconditionally (`2>/dev/null` no-ops on absent/empty telemetry). Use
     their output only when the project-local telemetry dogfooding output
     exists (the events dir — `.claude-kit/telemetry/events/` by default, see
     `feedback-loop/README.md`) and `CLAUDE_KIT_TELEMETRY=1`; otherwise fall
     back to session-observed waste only. `sequence.py`'s "self-transition
     runs" section is a length, not a count — a short run (length 2) is the
     review-round-churn candidate worth an item; a long run is a skill
     dispatching several isolated subagents by design (e.g. expert-panel's
     per-persona rounds) and is not waste on its own (#598).
   - `EVENTS_DIR`/`grep` — prior-retro read (dedup source, only when
     `CLAUDE_KIT_TELEMETRY=1` AND the events dir exists — the same opt-in gate
     as Phase 3): reports cumulative processing (best-effort).

3. **Waste signals**: from the collected output above, plus this session's
   observable waste (repeated failed tool calls, repeated review rounds,
   repeated same-error retries). Each signal: `{pattern, count, scope}` where
   `scope` = `harness` (workflow/tooling waste → harness issue) or `local`
   (this-repo waste → local issue).

4. **Session insights** (memory-branch source): notable decisions/learnings worth
   keeping. **Validated patterns** (rule-branch source): repeated user corrections
   that could become a project rule.

5. **Dedup** (count → `items_deduped`):
   - *Within session*: collapse duplicate `(path, error_type)` pairs to one.
   - *Action cross-run*: before proposing an issue, check existing open issues so
     a repeat pattern is not filed twice. This is a **comparison-set** read (does
     something like this already exist), not a live-status render — so it goes
     through the shared open-issue cache instead of its own `gh` call:
     ```bash
     bash "${CLAUDE_PLUGIN_ROOT}/scripts/gh-issues-cache.sh" get
     ```
     `gh-issues-cache.sh` returns the cached open-issue JSON (`number,title,body,labels,updatedAt`)
     when a fetch from this session is still fresh (≤5 min), else fetches live
     (`--limit 300`, ponytail: widen if a repo actually exceeds this) and refreshes the
     cache — cutting the redundant `gh` call when `thinking-tools/scripts/next-candidate.py`
     already populated it (or vice versa) earlier in the same `/wrap` run. Match each
     candidate pattern against the returned titles locally (case-insensitive substring is
     enough — this is dedup, not the report). **Never reuse this cache for a live-status
     render** (a specific PR/issue's current state shown to the user) — session-close's
     pre-render lookups must stay live; a cached one already misjudged a PR merged 9 hours
     earlier as still open (2026-07-30).
   - *Prior retro*: use the `grep` output already collected in step 2 above —
     do not re-invoke it here.

6. **Prioritize**: tag each item P0/P1/P2. Waste signals: harness-level
   repeated waste = P1, local nit = P2, integrity-breaking repeat = P0. Sort
   P0 → P1 → P2.

**Output**: `{waste[], insights[], rule_candidates[], budget, items_deduped}`.

---

## Phase 2 — OUTPUT (3 branches, each opt-in)

Default: **action branch active**; memory + rule branches OFF unless the user
opts in (offer them, do not run silently).

| Branch | Source | Mechanism | Default |
|--------|--------|-----------|---------|
| **액션 (action)** | repeat/waste patterns | git issue via `gh` — `scope: harness` → harness-level issue, `scope: local` → this-repo issue | **ON** (confirm before filing) |
| **기억 (memory)** | session insights | surface the exact `/vault-save …` (raw ore → `sources/`) or `/wiki` (compiled knowledge → `wiki/`) command for the USER to run — user-initiated slash; `retro` does NOT write vault | off (offer) |
| **규칙 (rule)** | validated patterns | surface a ready-to-run `/distill` invocation (propose-only handoff — `distill` judges worth-keeping, then hands it to `add-policy`; `retro` does NOT `Edit`) | off (offer) |

- **Action**: for each deduped waste pattern, draft `{title, body}` (body cites
  the evidence: counts, event types, scope). Confirm with the user (filing a
  GitHub issue is outward-facing), then `gh issue create`. Split by scope:
  harness-level waste vs. local-repo waste go to the matching tracker — never
  conflate them (mirrors #134's 2-branch waste split).
- **Memory**: never write the vault from `retro`. Output the ready-to-run slash
  command so the user keeps the Write Role Contract.
- **Rule**: surface a ready-to-run `/distill` invocation — never `Edit` a rule file directly.
  A pattern `retro` noticed was judged rule-worthy by **nobody**: `retro` observed it, and the
  user has not stated it. `distill` is the skill that makes that judgment (its anti-capture
  filter, including the recurrence floor), and `add-policy` deliberately does not — it lands
  what is already judged. Handing `retro`'s observation straight to `add-policy` therefore
  lands an unjudged rule, which is exactly the bypass `add-policy`'s §1 source gate bounces
  back here (#459). The chain is **retro → distill → add-policy**: `distill` judges, then
  `add-policy` classifies and places (which site, what form). Pass the pattern as
  natural-language prose; do NOT pre-fill the placement — that is the engine's, not
  `retro`'s. (The user may of course invoke `/add-policy` directly; a rule *they* state is
  already judged and takes the explicit path.)

---

## Phase 3 — BUDGET (accounting + telemetry)

1. **Enforce the cap**: total processed (issues filed + memory/rule actions)
   ≤ `RETRO_BUDGET`. If COLLECT produced more, the lowest-priority tail
   was not processed — report it explicitly:
   ```
   회고 예산 {budget} 도달 — 미처리 {N}건 (P0 {a} · P1 {b} · P2 {c}). 다음 회고에서 이어집니다.
   ```
   No silent drop.
2. **Report** (Korean): processed / deduped / budget_used + the remainder
   breakdown above.
3. **Emit telemetry** (best-effort, opt-in). Pass `START_MS` (captured from Phase 1's
   `stamp` output) plus the three retro counters to the helper; it owns the shared
   opt-in gate + events-dir rule (so the emit only fires when `CLAUDE_KIT_TELEMETRY=1`
   AND the events dir is resolvable), appends ONE schema-valid `skill_invoke` line
   whose `meta` carries those counters **plus `duration_ms`** (now − `START_MS`;
   `null` when `START_MS` is empty/non-numeric, which is schema-valid — the latency
   collector treats null as "no datum"), and enforces the 3500B PIPE_BUF guard:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" emit "$START_MS" "$PROCESSED" "$DEDUPED" "$BUDGET_USED"
   ```
   `report.py` latency reads `duration_ms`, so emitting it surfaces retro's own
   execution cost in the latency table; the other meta keys never pollute it.
   `budget_used` = items processed (≤ `RETRO_BUDGET`).

---

## Configuration

| Env var | Default | Effect |
|---------|---------|--------|
| `RETRO_BUDGET` | `10` | max items processed per retro (P0→P1→P2 truncation on overflow) |
| `CLAUDE_KIT_TELEMETRY` | unset | `1` enables the Phase-3 telemetry append |

## Rules

- Silent issue filing / rule handoff is FORBIDDEN — both are user-confirmed.
- `retro` performs zero vault writes.
- Memory output is a `/vault-save` suggestion — never a direct vault write.
- Rule output is a `/distill` suggestion — never a rule-file `Edit`. A pattern only `retro` noticed is
  unjudged, and `add-policy` never judges worth-keeping: the chain is retro → distill → add-policy (#459).
- Dedup before processing; enforce the budget; report the remainder (no silent drop).
- CON-5: read leaf artifacts only; never modify leaf-plugin code; no reverse dependency.
