---
name: retro
description: "Session retro for the ⑤ execution loop: re-confirm vault promotion candidates (audit E8) behind a user-confirmed gate, route findings to 3 opt-in outputs (action→git issue / memory→vault capture / rule→add-policy handoff), dedup repeats, and cap work with a retro budget. Trigger: 회고, 회고해줘, 세션 회고, 낭비 탐색, 승격 후보 검토, retro, session retrospective, waste sweep, promote candidates. Routing: vault structural defects only = obsidian-vault-manager /audit; this skill is the ⑤ post-loop consumer that ACTS on audit/telemetry output. Example: '/retro' or '회고해줘'."
model: inherit
allowed-tools: Read Edit Bash Grep Glob AskUserQuestion
---

**User language: Korean.** All user-facing output (status lines, AskUserQuestion prompts, confirmation messages, reports) MUST be in Korean. Instructions below are English for LLM parsing.

# retro — measure → improve loop closure (layer ⑤)

`retro` is the first consumer that closes claude-kit's measure→improve loop: it
reads what the leaf layers already produced (obsidian-vault-manager audit E8
findings, the project-local `telemetry/` dogfooding output) and turns it into
*confirmed* actions. It does NOT detect vault defects itself (that is `/audit`,
layer ④) and it does NOT re-implement promotion classification — it re-confirms
and acts.

## Boundary & safety (constitutional — do not relax)

Single source of truth: [`docs/design/claude-kit-boundary.md`](../../../docs/design/claude-kit-boundary.md) §5.

- **CON-5 one-way dependency**: `retro` (harness, ⑤) only *reads* leaf artifacts
  (audit findings / vault-bridge manifest / telemetry output) and *invokes* leaf
  capabilities. It NEVER modifies leaf-plugin code and nothing in a leaf depends
  back on `retro`.
- **CON-1 / Write Role Contract**: the ONLY vault write `retro` performs is the
  frontmatter-only `status:` patch in PROMOTE — a **v4 status-machine transition**
  (`raw`/`draft` → `evergreen`). CON-1's "new-file-only / 덮어쓰기 금지" rule targets
  *content / whole-file* clobbering; the v4 status machine by design mutates the
  `status:` field in place (raw→draft→evergreen→archived), so a frontmatter-only,
  user-confirmed status transition is *within* CON-1's intent, not against it.
  (This carve-out is ratified in boundary.md §5 — the "CON-1 status-machine note":
  OVM `audit` E2 OPTIONAL-FIX exercises it as a leaf write, and `retro` is the
  **first harness-layer** use; both are bounded to frontmatter-only + user-confirmed
  + non-subagent.) The patch is applied in **main
  context** — a user-initiated `/retro` slash command, never a subagent, so
  vault-bridge `pre-write-guard`'s Write Role Contract passes — and **only after
  the user confirms**. **CON-5 is unaffected**: a vault note is user *data*, not a
  leaf plugin, so editing it introduces no reverse harness→leaf dependency. Every
  *other* vault write (the memory branch) is surfaced as a `/capture` or
  `/save-session` slash command for the USER to run — `retro` does not write it.
- **User-confirmed gate (silent forbidden)**: promotion, issue filing, and rule
  additions are all proposed as candidates and applied ONLY on explicit user
  confirmation. Silent auto-fix / auto-file / auto-promote is forbidden.
- **No body edits**: PROMOTE touches only the `status:` line of frontmatter.

## Pipeline: COLLECT → PROMOTE → OUTPUT → BUDGET

The budget (`RETRO_BUDGET`, default 10) caps the total items *processed* across
PROMOTE + OUTPUT. Items are processed in priority order (P0 → P1 → P2); when the
budget is exhausted, processing STOPS and the remainder is reported (never
silently dropped). BUDGET is the final accounting + telemetry phase.

**Budget unit (precise):** an item consumes budget only when it is *acted on* —
promoted, an issue filed, or a memory/rule action surfaced. Items deduped in
COLLECT, or dropped by the PROMOTE threshold/type re-check, do NOT consume budget
and are NOT part of the unprocessed remainder count (they are counted under
`items_deduped` / silently-ineligible, not "미처리").

---

## Phase 1 — COLLECT (gather + dedup + prioritize)

Zero mutation. Produce a deduped, priority-sorted item list.

1. **Read config**: `RETRO_BUDGET` (default 10), `VAULT_AUDIT_PROMOTION_REFS`
   (default 3), `VAULT_AUDIT_PROMOTION_ACCESS` (default 5). Resolve vault root:
   `VAULT_BRIDGE_VAULT_ROOT` → `VAULT_BRIDGE_VAULT_PATH` → `~/vault` (expand `~`).
   Then **stamp the pipeline start** for the Phase-4 `duration_ms` datum. Each
   Bash call is a fresh shell (env vars do not persist between calls), so the
   start time must live on disk, not in a variable. Gate it on the SAME condition
   as the Phase-4 emit — telemetry opt-in AND a resolvable events dir — so no stamp
   is orphaned in `/tmp` when telemetry output is unreachable (the Phase-4 `rm -f`
   only runs inside that same branch). The events dir follows the single shared rule
   (same as `feedback-loop/scripts/event-logger.sh`): env override, else the
   user-writable `.claude-kit/telemetry/events` under the project root — never the
   plugin install cache:
   ```bash
   PROJ_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
   EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${PROJ_ROOT}/.claude-kit/telemetry/events}"
   # `:-unknown` fallback is benign: retro runs single-session per sid, and this stamp is
   # written here but read back in the separate Phase-4 shell — a `$$`-suffix can't survive
   # across invocations, so sid-less concurrent retros only theoretically share the path.
   [ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] && [ -d "$EVENTS_DIR" ] && \
     python3 -c 'import time;print(int(time.time()*1000))' \
       > "/tmp/retro-start-${CLAUDE_SESSION_ID:-unknown}.ms" 2>/dev/null || true
   ```

2. **E8 promotion candidates** (PROMOTE source). Read the vault-bridge manifest
   (the same source `/audit` uses — do NOT re-derive):
   ```bash
   cat "$VAULT_ROOT/.vault-bridge/manifest.json" 2>/dev/null
   ```
   Take `files[]` entries with `promotion_candidate: true`; keep
   `{path, references_in, access_count, status, type}`. If the manifest is
   absent/unparseable, emit a Korean note suggesting `/vault-manifest-refresh`
   then `/audit`, and skip the PROMOTE phase (do not guess candidates).

3. **Waste signals** (action-branch source). If the project-local telemetry
   dogfooding output exists (the events dir — `.claude-kit/telemetry/events/`
   by default, see `feedback-loop/README.md`) and `CLAUDE_KIT_TELEMETRY=1`,
   surface repeat-waste patterns (the report/sequence scripts self-resolve the
   events dir via the same shared rule):
   ```bash
   python3 feedback-loop/scripts/report.py 2>/dev/null        # outcome/error mix, latency (default 7d window)
   python3 feedback-loop/scripts/sequence.py --n=2 --top=20 2>/dev/null # repeated n-grams (review-round churn)
   ```
   Plus this session's observable waste (repeated failed tool calls, repeated
   review rounds, repeated same-error retries). Each signal:
   `{pattern, count, scope}` where `scope` = `harness` (workflow/tooling waste →
   harness issue) or `local` (this-repo waste → local issue). If telemetry is
   absent, fall back to session-observed waste only.

4. **Session insights** (memory-branch source): notable decisions/learnings worth
   keeping. **Validated patterns** (rule-branch source): repeated user corrections
   that could become a project rule.

5. **Dedup** (count → `items_deduped`):
   - *Within session*: collapse duplicate `(path, error_type)` pairs to one.
   - *E8 cross-run*: idempotent by the status machine — a note already
     `status: evergreen`/`archived` is not a promotion candidate, so a re-run
     never re-promotes it.
   - *Action cross-run*: before proposing an issue, check existing open issues so
     a repeat pattern is not filed twice. Use a **title search** so the match is
     targeted (not capped at the first 100 issues):
     ```bash
     gh issue list --state open --search "in:title <pattern keywords>" --json number,title 2>/dev/null
     ```
   - *Prior retro* (only when `CLAUDE_KIT_TELEMETRY=1` AND the events dir exists —
     the same opt-in gate as Phase 4): read prior `retro` events to report
     cumulative processing (best-effort):
     ```bash
     EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_ROOT:-$PWD}/.claude-kit/telemetry/events}"
     [ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] && [ -d "$EVENTS_DIR" ] && \
       grep -h '"name":"retro"' "$EVENTS_DIR"/events-*.jsonl 2>/dev/null | tail -n 20
     ```

6. **Prioritize**: tag each item P0/P1/P2. Reuse audit's mapping for vault items
   (E8 = P2). Waste signals: harness-level repeated waste = P1, local nit = P2,
   integrity-breaking repeat = P0. Sort P0 → P1 → P2.

**Output**: `{candidates_e8[], waste[], insights[], rule_candidates[], budget, items_deduped}`.

---

## Phase 2 — PROMOTE (E8, user-confirmed)

For E8 candidates, in priority order, until the budget is reached:

1. **Re-confirm threshold**: keep only candidates with
   `references_in >= REFS` **OR** `access_count >= ACCESS` (the env thresholds
   from COLLECT — mirrors `generate-manifest.py`). Drop any that no longer meet it
   (manifest may be stale).
2. **Status + type guard**: read the note's current `status:` AND `type:`. Promote
   ONLY when `status` is `raw`/`draft` **and** `type` is `note` or `decision`
   (v4 §3.3 — `session`/`capture`/`plan` can never become evergreen). Skip
   `evergreen`/`archived` (dedup idempotence) or any non-promotable type. This
   re-confirms `type` the same way step 1 re-confirms refs/access, closing the
   stale-manifest window (a note retyped after the last manifest refresh).
3. **User-confirmed gate** (AskUserQuestion, Korean): list the surviving
   candidates with `refs_in` / `access` / current status; let the user pick which
   to promote (multi-select) or skip all. **Never promote without this.**
4. **Apply** (confirmed only): `Edit` the note's frontmatter `status:` value to
   `evergreen`. Frontmatter-only — never touch the body, name, or path. Main
   context only.
5. Count promoted → `items_promoted`.

---

## Phase 3 — OUTPUT (3 branches, each opt-in)

Default: **action branch active**; memory + rule branches OFF unless the user
opts in (offer them, do not run silently).

| Branch | Source | Mechanism | Default |
|--------|--------|-----------|---------|
| **액션 (action)** | repeat/waste patterns | git issue via `gh` — `scope: harness` → harness-level issue, `scope: local` → this-repo issue | **ON** (confirm before filing) |
| **기억 (memory)** | session insights | surface the exact `/capture …` or `/save-session` command for the USER to run (user-initiated slash; `retro` does NOT write vault) | off (offer) |
| **규칙 (rule)** | validated patterns | surface a ready-to-run `/add-policy` invocation (propose-only handoff — `add-policy` classifies + places; `retro` does NOT `Edit`) | off (offer) |

> **`/distill` suggestion (propose-only, #202):** when the session surfaced a
> *reusable procedural technique* (not declarative knowledge — that is the memory
> branch's `/capture`), `retro` MAY surface a ready-to-run `/distill` command the
> SAME way the memory branch surfaces `/capture` — a suggestion for the USER to run,
> never inline. `distill` is a sibling skill, NOT a fourth always-on output branch;
> `retro` does not run it and does not embed its procedure.

- **Action**: for each deduped waste pattern, draft `{title, body}` (body cites
  the evidence: counts, event types, scope). Confirm with the user (filing a
  GitHub issue is outward-facing), then `gh issue create`. Split by scope:
  harness-level waste vs. local-repo waste go to the matching tracker — never
  conflate them (mirrors #134's 2-branch waste split).
- **Memory**: never write the vault from `retro`. Output the ready-to-run slash
  command so the user keeps the Write Role Contract.
- **Rule**: surface a ready-to-run `/add-policy` invocation — never `Edit` a rule file
  directly. `retro` discovers *that* a validated pattern is rule-worthy; **`add-policy`
  (the landfill engine) owns classification + placement** (which site, what form), exactly
  as the memory branch hands off to `/capture`. This is the same discover→land split as
  distill→add-policy (#251): a project-local SOFT rule lands in `add-policy`'s **CLAUDE.md
  site at project-local scope** (a project-local `.claude/CLAUDE.md` is a CLAUDE.md-family
  landfill, not a fourth site — "which CLAUDE.md?" is the engine's scope choice), a
  deterministically-guardable rule becomes a **hook**, a procedure becomes a **skill** —
  `add-policy` decides, not `retro`. Pass the validated pattern as the natural-language
  rule the engine re-classifies; do NOT pre-fill the placement.

---

## Phase 4 — BUDGET (accounting + telemetry)

1. **Enforce the cap**: total processed (promoted + issues filed + memory/rule
   actions) ≤ `RETRO_BUDGET`. If COLLECT produced more, the lowest-priority tail
   was not processed — report it explicitly:
   ```
   회고 예산 {budget} 도달 — 미처리 {N}건 (P0 {a} · P1 {b} · P2 {c}). 다음 회고에서 이어집니다.
   ```
   No silent drop.
2. **Report** (Korean): processed / promoted / deduped / budget_used + the
   remainder breakdown above.
3. **Emit telemetry** (best-effort, opt-in). Only when `CLAUDE_KIT_TELEMETRY=1`
   AND the events dir is resolvable. The dir follows the single shared rule
   (`${CLAUDE_KIT_TELEMETRY_DIR:-${PROJ_ROOT}/.claude-kit/telemetry/events}`); `PROJ_ROOT`
   is anchored to `${CLAUDE_PROJECT_ROOT:-$PWD}` (NOT bare `$PWD`) so an in-session
   `cd` cannot silently misdirect the append — this mirrors the vault-bridge hook
   convention (every hook resolves `PROJ_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"`). Append ONE
   schema-valid line whose `meta` carries the four retro fields **plus
   `duration_ms`** (the envelope `meta` is the only schema-required part;
   `report.py` latency reads `duration_ms`, so emitting it surfaces retro's own
   execution cost in the latency table — the other keys never pollute it).
   `duration_ms` = pipeline wall-clock from the Phase-1 start stamp; when the
   stamp is missing it falls back to `null`, which is schema-valid (the latency
   collector treats null as "no datum"). Silent on any failure; skip if the line
   ≥ 3500B:
   ```bash
   PROJ_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
   EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${PROJ_ROOT}/.claude-kit/telemetry/events}"
   if [ "${CLAUDE_KIT_TELEMETRY:-}" = "1" ] && [ -d "$EVENTS_DIR" ]; then
     # duration_ms = now − Phase-1 start stamp; null when the stamp is unavailable.
     START_MS=$(cat "/tmp/retro-start-${CLAUDE_SESSION_ID:-unknown}.ms" 2>/dev/null || true)
     END_MS=$(python3 -c 'import time;print(int(time.time()*1000))' 2>/dev/null || true)
     # Require both to be all-digits before arithmetic — a corrupt/non-numeric
     # stamp must fall back to null, not resolve to 0 and emit a bogus duration.
     if [[ "$START_MS" =~ ^[0-9]+$ ]] && [[ "$END_MS" =~ ^[0-9]+$ ]]; then DURATION_MS=$((END_MS - START_MS)); else DURATION_MS=null; fi
     LINE=$(jq -nc \
       --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       --arg sid "${CLAUDE_SESSION_ID:-unknown}" --arg cwd "$PROJ_ROOT" \
       --argjson processed "$PROCESSED" --argjson promoted "$PROMOTED" \
       --argjson deduped "$DEDUPED" --argjson budget "$BUDGET_USED" \
       --argjson duration "$DURATION_MS" \
       '{ts:$ts, session_id:$sid, cwd:$cwd, plugin:"feedback-loop",
         event:"skill_invoke", name:"retro", qualified_name:"feedback-loop:retro",
         trigger:"explicit", outcome:"success", tool_use_id:"",
         meta:{retro_items_processed:$processed, items_promoted:$promoted,
               items_deduped:$deduped, budget_used:$budget, duration_ms:$duration}}' 2>/dev/null)
     [ -n "$LINE" ] && [ "${#LINE}" -lt 3500 ] && \
       printf '%s\n' "$LINE" >> "${EVENTS_DIR}/events-$(date -u +%Y-%m-%d).jsonl" 2>/dev/null
     rm -f "/tmp/retro-start-${CLAUDE_SESSION_ID:-unknown}.ms" 2>/dev/null || true
   fi
   ```
   `budget_used` = items processed (≤ `RETRO_BUDGET`); `duration_ms` is the retro
   pipeline wall-clock (null if the start stamp was unavailable).

---

## Configuration

| Env var | Default | Effect |
|---------|---------|--------|
| `RETRO_BUDGET` | `10` | max items processed per retro (P0→P1→P2 truncation on overflow) |
| `VAULT_AUDIT_PROMOTION_REFS` | `3` | inbound-link threshold re-confirmed in PROMOTE |
| `VAULT_AUDIT_PROMOTION_ACCESS` | `5` | 7-day access threshold re-confirmed in PROMOTE |
| `CLAUDE_KIT_TELEMETRY` | unset | `1` enables the Phase-4 telemetry append |
| `VAULT_BRIDGE_VAULT_ROOT` / `VAULT_BRIDGE_VAULT_PATH` | `~/vault` | vault root resolution |

## Rules

- Silent promotion / issue filing / rule handoff is FORBIDDEN — all are user-confirmed.
- The only vault write is the frontmatter-only `status:` patch (PROMOTE), main context, user-confirmed. Memory output is a `/capture` suggestion and rule output is an `/add-policy` suggestion — never a direct vault write or rule-file `Edit`.
- `add-policy` owns rule classification + placement (the discover→land split).
- Never re-implement audit/promotion classification — read leaf output, re-confirm thresholds, act.
- Dedup before processing; enforce the budget; report the remainder (no silent drop).
- CON-5: read leaf artifacts only; never modify leaf-plugin code; no reverse dependency.
