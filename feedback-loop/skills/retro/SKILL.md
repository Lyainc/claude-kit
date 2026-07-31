---
name: retro
description: "Session retro for the ⑤ execution loop: re-confirm vault promotion candidates (audit E8) behind a user-confirmed gate, route findings to 3 opt-in outputs (action→git issue / memory→vault capture / rule→distill handoff), dedup repeats, and cap work with a retro budget. Trigger: 회고, 회고해줘, 세션 회고, 낭비 탐색, 승격 후보 검토, retro, session retrospective, waste sweep, promote candidates. Routing: vault structural defects only = obsidian-vault-manager /audit; this skill is the ⑤ post-loop consumer that ACTS on audit/telemetry output. Example: '/retro' or '회고해줘'."
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
  *other* vault write (the memory branch) is surfaced as a `/capture` slash
  command (raw session ore → `inbox/`) or `/wiki` (compiled domain knowledge →
  `wiki/`) for the USER to run — `retro` does not write it. (Session knowledge
  is wiki-first: local context is native memory, active recall is `/wiki`; the
  old `/save-session` command was retired #331.)
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
   Then **stamp the pipeline start** for the Phase-4 `duration_ms` datum (each Bash
   call is a fresh shell, so the start time must live on disk, not in a variable):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" stamp
   ```
   The helper owns the events-dir rule + opt-in gate (shared with
   `feedback-loop/scripts/event-logger.sh`): it no-ops unless telemetry is opted in
   AND the events dir is resolvable — the SAME branch the Phase-4 emit + stamp cleanup
   run inside, so no stamp is orphaned in `/tmp` when telemetry output is unreachable.

2. **E8 promotion candidates** (PROMOTE source). Read the vault-bridge manifest
   (the same source `/audit` uses — never re-scan the vault yourself) through the
   filter script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/e8-candidates.py"
   ```
   It prints `{"e8_candidates": [{path, references_in, access_count, status, type}, ...],
   "scanned": N}`. **Never `cat` the manifest**: it is ~120 KB / 168 files on a real
   vault, and the harness hands the model only a **2 KB preview** of a large Bash
   result — three entries, the third cut mid-string. A `cat` therefore reports "no
   candidates" after seeing 1.8% of the vault, in a form indistinguishable from a
   full scan (#460). The script filters server-side so the whole result arrives.
   **Exit 3 = manifest absent/unparseable**: emit a Korean note suggesting
   `/vault-manifest-refresh` then `/audit`, and skip the PROMOTE phase — never
   collapse that branch into "후보 0건". An empty list on exit 0 IS "0 candidates",
   and `scanned` is what makes the coverage claim in the report honest. The script
   applies the E8 *threshold* itself rather than trusting the manifest's
   `promotion_candidate` flag (that flag ignores `status`, #435) — that is reading
   the leaf's data, not re-implementing its scan.

3. **Waste signals** (action-branch source). If the project-local telemetry
   dogfooding output exists (the events dir — `.claude-kit/telemetry/events/`
   by default, see `feedback-loop/README.md`) and `CLAUDE_KIT_TELEMETRY=1`,
   surface repeat-waste patterns (the report/sequence scripts self-resolve the
   events dir via the same shared rule):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" 2>/dev/null        # outcome/error mix, latency (default 7d window)
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sequence.py" --n=2 --top=20 2>/dev/null # repeated n-grams (review-round churn)
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
     EVENTS_DIR="${CLAUDE_KIT_TELEMETRY_DIR:-${CLAUDE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}/.claude-kit/telemetry/events}"
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
| **기억 (memory)** | session insights | surface the exact `/capture …` (raw ore → `inbox/`) or `/wiki` (compiled knowledge → `wiki/`) command for the USER to run — user-initiated slash; `retro` does NOT write vault | off (offer) |
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
3. **Emit telemetry** (best-effort, opt-in). Pass the four retro counters to the
   helper; it owns the shared opt-in gate + events-dir rule (so the emit only fires
   when `CLAUDE_KIT_TELEMETRY=1` AND the events dir is resolvable), appends ONE
   schema-valid `skill_invoke` line whose `meta` carries those counters **plus
   `duration_ms`** (now − the Phase-1 start stamp; `null` when the stamp is
   missing/corrupt, which is schema-valid — the latency collector treats null as "no
   datum"), enforces the 3500B PIPE_BUF guard, and removes the start stamp:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/retro-telemetry.sh" emit "$PROCESSED" "$PROMOTED" "$DEDUPED" "$BUDGET_USED"
   ```
   `report.py` latency reads `duration_ms`, so emitting it surfaces retro's own
   execution cost in the latency table; the other meta keys never pollute it.
   `budget_used` = items processed (≤ `RETRO_BUDGET`).

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
- The only vault write is the frontmatter-only `status:` patch (PROMOTE), main context, user-confirmed.
- Memory output is a `/capture` suggestion — never a direct vault write.
- Rule output is a `/distill` suggestion — never a rule-file `Edit`. A pattern only `retro` noticed is
  unjudged, and `add-policy` never judges worth-keeping: the chain is retro → distill → add-policy (#459).
- Never re-scan the vault or re-implement audit's detection — read the leaf's manifest, apply the E8
  threshold to it, re-confirm against the note itself, act.
- Dedup before processing; enforce the budget; report the remainder (no silent drop).
- CON-5: read leaf artifacts only; never modify leaf-plugin code; no reverse dependency.
