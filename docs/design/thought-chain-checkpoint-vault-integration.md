# thought-chain Checkpoint & Vault Integration

> **⚠️ SUPERSEDED (G21 cut).** The `/save-plan-doc` + `plan-doc-syncer` "③ delivery" intake
> and the `snapshot_export` / `snapshot_import` opt-in gates that this design is built on were
> removed (dual-source antipattern, telemetry 3-week zero, issue #215). The vault-save path
> described here is dead: thought-chain now routes its single vault destination to
> `vault-bridge:save-session` (with a `plan` arg for plan docs), with visibility gated only on
> `.vault-link` presence. Kept for historical context; do not implement from this doc.

> Status: ~~Design — ready for implementation~~ SUPERSEDED
> Owner: thinking-tools plugin
> Created: 2026-05-12
> Related: `thinking-tools/skills/thought-chain/SKILL.md`, `docs/thought-chain-rationale.md` (both since removed — thought-chain itself was fully dissolved, #105, and its rationale doc with it)

## 1. Background

`thought-chain` orchestrates four thinking-tools skills (`unknown-discovery` → `expert-panel` → `doc-concretize` → `doc-polish`) with checkpoints between stages. The current design has three pain points surfaced during real usage:

1. **Dead exits**: when the user stops mid-pipeline, the partial result is discarded. The skill has no path to persist that result.
2. **Coarse "stop here" semantic**: the only mid-pipeline outputs are "continue / stop / re-run", and "re-run" rarely matches the real user need (the more common need is *deepen* the current output, not restart).
3. **No vault wiring**: the final polished document is printed to terminal and lost when the session ends. `vault-bridge` has all the primitives (`/save-plan-doc`, `/save-session`) but `thought-chain` doesn't call them.

This design adds (a) a `deepen` checkpoint option, (b) a vault-aware stop/finish flow, (c) an `--autopilot` flag for power users, and (d) saved-document metadata that records pipeline depth.

## 2. Goals & Non-Goals

### Goals

- G1. Replace the dead "stop here" exit with a vault-save path on both mid-pipeline stops and end-of-pipeline completion.
- G2. Add `deepen` as a first-class checkpoint option semantically distinct from `re-run`.
- G3. Provide `--autopilot` for users who want a no-checkpoint run; pre-declare vault destination via `--auto-vault`.
- G4. Guarantee that anything written to vault has been through `doc-polish` (no raw mid-stage artifacts in vault).
- G5. Detect `.vault-link` / opt-in gate state at pipeline start so the end-state question never offers an option the user cannot actually take.

### Non-Goals

- NG1. Adding a new "dev plan" output type. (Plan-doc save already covers this; "convert to dev plan" from the original draft is folded into the plan-doc destination.)
- NG2. New modes inside the downstream skills (`unknown-discovery`, `expert-panel`, etc.). Deepen is implemented entirely in the orchestrator by re-invoking the same skill with the prior output as input plus a "refine deeper" instruction.
- NG3. Replacing the `thinking-facilitator` routing path. `thought-chain` remains the explicit-pipeline entry; facilitator remains the single-skill router.
- NG4. Persisting pipeline state across sessions. If the user exits, work is lost unless they chose vault save. (Cross-session resume is a separate, larger design.)

## 3. UX Changes

### 3.1 Checkpoint options (between stages)

Replace the current 3-option checkpoint with the following 5-option set:

```
───
✓ Stage 1: Discovery 완료 — Critical 2건, Important 3건 발견
→ 다음으로 어떻게 진행할까요?

1. 다음 단계로 (Stage 2: Expert Panel)
2. 더 묻기 — 이 단계에 머무르며 결과 심화
3. 재실행 — 이 단계를 처음부터 다시
4. 멈추고 vault 저장
5. 그냥 멈춤
```

**Semantics:**

| Option | Behavior |
|--------|----------|
| 다음 단계로 | Hand current output to next stage. Unchanged from today. |
| 더 묻기 | Re-invoke the current stage's skill with its prior output as context + "go deeper / refine further" instruction. Counts toward `deepen_cap` (see §3.2). |
| 재실행 | Discard current stage output. Re-run the stage from a clean state with original input. Use case: stage went in wrong direction entirely. |
| 멈추고 vault 저장 | Stop pipeline. If stopping before Stage 4, automatically run a mini polish pass on current artifact. Then trigger the vault destination question (§3.4). |
| 그냥 멈춤 | Stop pipeline. Print whatever exists to terminal. No vault write. |

### 3.2 `deepen` mechanics

When the user picks "더 묻기":

1. The orchestrator re-invokes the current stage's skill, passing the prior output plus a "deepen" instruction:
   - `unknown-discovery`: additional interview rounds on existing findings; raises depth metric.
   - `expert-panel`: additional debate rounds; attack unresolved dissent; re-synthesize.
   - `doc-concretize`: expand sections, add recursive depth one level deeper.
   - `doc-polish`: stricter Layer 2/3 quality pass.
2. After the deepened pass completes, the same checkpoint surfaces again. The user can deepen again, continue, etc.

**Deepen cap**: hard limit of **3 deepen rounds per stage**. After the 3rd, the next checkpoint replaces "더 묻기" with a friction prompt:

```
이 단계에서 이미 3번 심화했어요. 결과가 충분하지 않다면 재실행이 나을 수도 있어요.

1. 그래도 한 번 더 (강제 deepen, cap 해제)
2. 다음 단계로
3. 재실행
4. 멈추고 vault 저장
5. 그냥 멈춤
```

Forcing past the cap is allowed but requires explicit selection — this prevents accidental infinite loops while preserving user agency.

**Stage labels**: the "더 묻기" label is **stage-specific** for clarity:

| Stage | Label |
|-------|-------|
| unknown-discovery | 더 인터뷰 |
| expert-panel | 더 토론 |
| doc-concretize | 더 구체화 |
| doc-polish | 더 다듬기 |

Trade-off: stage-specific labels add minor learning cost but make the action's effect obvious. Worth the cost.

### 3.3 Pre-pipeline gate check

At pipeline start, before Stage 1 runs, the orchestrator detects vault state once:

```bash
[ -f "$PWD/.vault-link" ] && cat "$PWD/.vault-link" || echo "NOT_FOUND"
```

State derived:
- `vault_linked ∈ {yes, no}`
- `snapshot_export ∈ {true, false}`
- `import_allowed` from vault `_index.md` (best-effort read)

The state is held in the pipeline session memory and reused at every vault prompt. This avoids late-stage "actually, this option isn't available" surprises.

**No upfront question**. The gate check is silent; results only surface when a vault destination is offered (mid-pipeline stop or end-of-pipeline).

### 3.4 Vault destination question (single-select)

Surfaced when the user picks "멈추고 vault 저장" OR at end-of-pipeline:

```
분석 결과를 어떻게 저장할까요?

1. 터미널만 — 출력만, vault에 남기지 않음 (기본)
2. Plan doc로 vault에 저장
3. Session note로 vault에 저장
4. 종료 — 출력 없이 끝
```

**Conditional option display:**

| Gate state | Plan doc | Session note |
|------------|----------|--------------|
| `.vault-link` absent | Hidden + hint message | Hidden + hint message |
| `snapshot_export: false` | Hidden + hint | Visible |
| `snapshot_export: true`, `import_allowed: false` | Visible but warning shown | Visible |
| Both gates open | Visible (recommended) | Visible |

**Hint message** when options hidden:
```
vault 저장을 원하시면 먼저 `/vault-link`로 프로젝트를 바인딩하세요.
Plan doc 저장에는 추가로 `.vault-link`의 `snapshot_export: true` 및
vault `_index.md`의 `snapshot_import: true`가 필요해요.
```

**Routing:**
- "Plan doc로 vault에 저장" → invoke `/vault-bridge:save-plan-doc` with the polished document as the target.
- "Session note로 vault에 저장" → invoke `/vault-bridge:save-session` with the polished document embedded in record-mode body.
- "터미널만" → current behavior, print full polished document to terminal.
- "종료" → no output, exit cleanly.

### 3.5 Mid-stop polish guarantee

If the user picks "멈추고 vault 저장" at a checkpoint **before** Stage 4 (polish), the orchestrator runs a minimal polish pass on the current artifact before saving:

- After Stage 1 stop: package findings as a markdown document → polish → save.
- After Stage 2 stop: package consensus + dissents as a markdown document → polish → save.
- After Stage 3 stop: run doc-polish on the concretized document → save.
- After Stage 4 (normal completion): save directly.

**Invariant**: vault never receives a non-polished artifact. This keeps vault signal-to-noise high.

### 3.6 `--autopilot` flag

CLI flag, opt-in only, not asked at start:

```
/thought-chain --autopilot
/thought-chain --autopilot --auto-vault plan
/thought-chain --autopilot --auto-vault session
```

Behavior:
- `--autopilot`: every checkpoint auto-selects "다음 단계로". No deepen, no re-run. After Stage 4, end-state question is auto-answered to "터미널만" unless `--auto-vault` is provided.
- `--auto-vault plan`: end-state auto-answers to "Plan doc로 vault에 저장". If gate is closed at end, falls back to terminal output with a single-line warning.
- `--auto-vault session`: end-state auto-answers to "Session note로 vault에 저장". If `.vault-link` is missing, falls back to terminal with warning.
- `--auto-vault` without `--autopilot` is an error: checkpoint stops are still interactive, so destination can be picked then.

**Escape hatch**: thought-chain runs in main context; the user can interrupt at any time. After interrupt, the next checkpoint surfaces. Document this in README — no special implementation needed.

**README caveat** (per `docs/thought-chain-rationale.md:38-40`): autopilot mode reduces thought-chain to a 4-skill macro. The checkpoint UX is one of three justifications for thought-chain's existence; disabling it is a deliberate power-user choice.

### 3.7 Saved-document metadata

When thought-chain saves to vault (plan or session), the YAML frontmatter includes pipeline metadata:

```yaml
created: 2026-05-12
type: plan                      # or "session"
status: active
tags: [thought-chain, security, performance]   # auto-extracted from discovery/panel domains
thought_chain:
  stages_run: [discovery, panel, concretize, polish]
  deepen_counts:
    discovery: 2
    panel: 1
    concretize: 0
    polish: 0
  stopped_at: polish             # or "panel" if mid-stop occurred
  quality_score: 92              # from doc-polish final report
  duration_seconds: 1820         # wall-clock
```

This lets later vault queries distinguish a lightly-run analysis from a deeply-iterated one — useful for trust calibration when reusing the document.

`tags` auto-extraction:
- From `unknown-discovery`: finding domains (`security`, `performance`, etc.)
- From `expert-panel`: expert specializations (deduplicated against discovery domains)
- Always prepended with `thought-chain`

## 4. Implementation Outline

### 4.1 File changes

| File | Change |
|------|--------|
| `thinking-tools/skills/thought-chain/SKILL.md` | Replace §"Checkpoint System" with 5-option spec. Add §"Deepen Mechanics", §"Vault Destination", §"Autopilot Flag", §"Pre-Pipeline Gate Check". Update Pipeline Stages diagram footer. Update Final Output sample to include frontmatter when vault destination chosen. |
| `thinking-tools/skills/thought-chain/reference.md` | Add deepen prompts (per-stage), vault destination routing examples, autopilot flag examples. |
| `thinking-tools/docs/thought-chain-rationale.md` | Add note: "Checkpoint UX is opt-out via `--autopilot`; rationale for keeping thought-chain separate from facilitator still holds for the default (no-autopilot) path." |
| `thinking-tools/.claude-plugin/plugin.json` | Version bump (minor). Update description if needed. |
| `.claude-plugin/marketplace.json` | Mirror version bump + description on thinking-tools entry. |

### 4.2 Orchestration logic blocks (added to SKILL.md instructions)

1. **Pre-pipeline gate snapshot** — runs once before Stage 1; stores `{vault_linked, snapshot_export, import_allowed}` in session memory.
2. **Checkpoint dispatcher** — at each stage boundary, render the 5-option AskUserQuestion (or skip if `--autopilot`). Route per selection.
3. **Deepen invocation** — when "더 묻기" picked: increment `deepen_counts[stage]`. If count <= 3, re-call current skill with `{prior_output, mode: "deepen"}`. If count > 3, show friction prompt.
4. **Stop-and-save handler** — runs mini-polish if stopping before Stage 4. Then triggers vault destination question (or `--auto-vault` value if set).
5. **End-state question** — runs after Stage 4 (or after stop-and-save mini-polish). Conditional options per gate state.
6. **Vault save dispatch** — invokes `/vault-bridge:save-plan-doc` or `/vault-bridge:save-session` via the Skill tool. Bundles frontmatter metadata.
7. **Metadata aggregator** — collects `stages_run`, `deepen_counts`, `stopped_at`, `quality_score`, `duration_seconds`, `tags` throughout the pipeline.

### 4.3 `allowed-tools` update

Current: `Skill Read Write AskUserQuestion`
Required: same set is sufficient (Skill covers `vault-bridge:save-plan-doc` and `vault-bridge:save-session` invocations; Bash is **not** added because gate state can be derived from `Read` on `.vault-link`).

### 4.4 Backward compatibility

- Existing `--quick`, `--skip`, `--start` flags unchanged.
- Default checkpoint behavior (no `--autopilot`) preserves the user-confirmation invariant — new options expand the menu but don't change defaults.
- Documents saved before this change have no `thought_chain:` frontmatter block; vault queries should treat absence as "no metadata", not as an error.

## 5. Testing & Acceptance

### 5.1 Manual test scenarios

1. **Full pipeline, no vault** — run end-to-end, pick "터미널만" at end. Result matches current behavior.
2. **Mid-stop with vault save** — stop after Stage 2, pick "Plan doc로 vault에 저장". Verify: mini-polish ran, file saved to `~/vault/20_Projects/{name}/plan-YYYY-MM-DD-{topic}.md`, frontmatter contains `stopped_at: panel`.
3. **Deepen + cap** — pick "더 인터뷰" 3 times in Stage 1. Verify: 4th checkpoint shows friction prompt; force-deepen works.
4. **Autopilot + auto-vault** — `--autopilot --auto-vault plan`. Verify: no checkpoints surface; end produces a plan-doc save.
5. **Gate closed** — run with `.vault-link` absent. Verify: end-state question hides plan/session options, shows hint.
6. **Autopilot fallback** — `--autopilot --auto-vault plan` with `snapshot_export: false`. Verify: terminal output + warning line.

### 5.2 Acceptance criteria

- [ ] All 6 manual scenarios pass.
- [ ] `SKILL.md` JSON validation passes (no broken frontmatter).
- [ ] No regression in single-stage invocation of any downstream skill (unknown-discovery, expert-panel, doc-concretize, doc-polish unchanged).
- [ ] Saved vault documents have valid frontmatter per `vault-bridge` naming + format conventions.
- [ ] `marketplace.json` version aligned with `thinking-tools/plugin.json`.

## 6. Open Questions

- Q1. Should the deepen cap (currently 3) be configurable via env var? Decision: defer. Hard-code 3, observe usage, raise later if friction emerges.
- Q2. Should `--auto-vault plan` retry with `session` fallback if plan gate is closed, instead of falling back to terminal? Decision: no. Terminal fallback is loud and predictable; silent destination change would surprise users.
- Q3. Where does the topic name for `plan-YYYY-MM-DD-{topic}.md` come from when saving? Decision: derived from `unknown-discovery`'s original analysis target (the user's initial prompt). Slugged + lowercased. User can override via AskUserQuestion sub-prompt during save.

## 7. Priority & Sequencing

Per the previous critique, implement in this order:

| Phase | Scope | Notes |
|-------|-------|-------|
| P0 | §3.3 (gate check) + §3.4 (vault destination) + §3.5 (mid-stop polish) + §3.7 (metadata) | Largest user value; resurrects the dead exit. |
| P0 | §3.1 (5-option checkpoint) + §3.2 (deepen + cap) | New deepen semantic; clear separation from re-run. |
| P1 | §3.6 (`--autopilot` + `--auto-vault`) | Convenience, requires gate-fallback handling. |
| P2 | README + rationale doc updates | Documentation, after implementation stable. |

P0 items together produce a meaningful release. P1 can ship in the same PR if implementation cost is low; otherwise split.

## 8. See Also

- `thinking-tools/skills/thought-chain/SKILL.md` — current pipeline spec
- `vault-bridge/commands/save-plan-doc.md` — plan-doc save command + 2-layer gate
- `vault-bridge/commands/save-session.md` — session-note save command
- `docs/thought-chain-rationale.md` — why thought-chain exists separately from facilitator
- `CLAUDE.md` §"Vault File Conventions" — frontmatter standard
