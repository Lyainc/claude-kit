# RULES.md — claude-kit work rules

This is the repository's **work-rules** reference: the conventions, the enforcement
model, and the task-end checklist for doing work *on* claude-kit. It is an
LLM-optimized reference doc (English body), with a short Korean note where it
addresses a human reader directly.

> 한국어 메모 (사람 독자용): 이 문서는 claude-kit **작업 규칙**(work-rule)이에요.
> 페르소나 — 말투(voice)와 관점·판단(stance) — 는 개인 `~/.claude/CLAUDE.md`에
> 있고, 여기엔 안 섞여요. 규칙은 두 종류로 갈려요 — 위반이 객관적 손상을 내면
> **정책(policy)** 이라 결정론 스크립트로 막고, 취향·회색지대면 **선호(preference)**
> 라 외부 린터 설정에 위임해요. 하드코딩으로 자기 스타일을 강요하지 않아요.

## 0. Why this file exists — stance / voice / work-rule (c1)

claude-kit's main-agent **persona** lives in the developer's *personal*
`~/.claude/CLAUDE.md`, and it is itself two independent layers: **voice**
(어조 — tone: warmth, honorifics, liveliness) and **stance** (관점 — the judgment
posture: critic, honesty, calibration). Both are deliberately **not** in this repo.
The third layer — **work-rule** (작업 규율 — how code/docs in this repo are written,
traced, and enforced) — lives **here in `rules/`**, physically separate from the
persona.

That is the c1 trichotomy: **stance · voice · work-rule** are three independent
layers. A lively *voice* must never soften a *stance* judgment, and neither may bend a
*work-rule*; and a work rule must never depend on who is at the keyboard or on their
tone or judgment style. Anyone (or any agent) working on claude-kit follows `rules/`;
nobody is required to adopt anyone else's persona.

**Broad machine rules vs this repo's concrete rules.** Some work-rules are *광의(broad)*
— they hold on the developer's machine across every project (e.g. "isolate concurrent
agents in separate git worktrees", "Python goes through uv"). Those live, stated
abstractly, in the developer's *personal* `~/.claude/rules/` (a separate machine-level
base). claude-kit holds only the **concrete** form of any rule it actually needs, and
holds it **self-contained**: this repo has **zero runtime/build dependency** on that
personal layer, so a public clone works on any machine. The relationship is
intellectual lineage (the same idea expressed at two abstraction levels), not a dependency —
§0's "depend" means runtime/build, never lineage. The subagent git side-effect
contract (§1, #209) is the worked example: claude-kit holds it concretely here, while its
broad/abstract *what + why* lives as a machine-level work-rule — the same idea at two
altitudes, linked by lineage, not by any runtime reference. Do **not** add a `~/.claude/...`
reference that a clone would need to resolve.

## 1. Domain conventions & traceability

These are the conventions specific to working on claude-kit. The canonical *runtime*
guidance lives in `CLAUDE.md`; this section captures the **work/traceability** rules.

- **Issue = canonical source of truth.** Every non-trivial change traces to a GitHub
  issue. The issue holds the *why* (the decision, the spec, the trade-off). Commits
  and PRs are the *how*; they point back to the issue, never the reverse. When the
  issue and a PR description disagree, the issue wins — reconcile by updating one of
  them, do not let the trail fork.
- **PR descriptions in Korean, referencing the issue.** PR bodies are written in
  Korean and reference the master plan / vault spec / issue number so the decision
  trail stays searchable. (Per `feedback_trace_to_root`: on a tangled inconsistency,
  trace upstream to the origin before acting, then fix all related artifacts.)
- **Conventional Commits, English.** `feat:`, `fix:`, `docs:`, `refactor:`,
  `chore:`. Branch prefixes: `feat/`, `fix/`, `docs/`, `refactor/`. (Commit subject
  language and branch prefixes are claude-kit policy, enforced by review/convention,
  not by this file's scripts.)
- **Version lockstep.** All plugins share one version and ship together under a
  single tag `vX.Y.Z`. Do **not** bump a version in a feature branch — the release
  workflow bumps every manifest at once. `plugin.json` is the source of truth;
  `marketplace.json` is derived. See `RELEASING.md` and the Version Sync Rule in
  `CLAUDE.md`.
- **Vault file conventions — by reference, not redefined.** Files written to the
  vault follow the unified convention already specified in `CLAUDE.md` ("Vault File
  Conventions" — folder layout, filename pattern, frontmatter standard, `type:`
  opt-in). This file does **not** restate them; treat `CLAUDE.md` as canonical and
  keep them in one place.
- **Subagents do not cause git side effects (#209).** A subagent (Workflow `agent()`,
  Agent/Task) leaves all changes in the working tree — it does **not** `commit`,
  `push`, or create PRs. The **main context owns git**. This keeps isolated-critique
  premises intact (the review target is an uncommitted diff) and prevents
  unapproved outward-facing actions (a push or PR is an external, often irreversible
  publish). Two layers enforce it: (1) Workflow scripts that delegate implementation
  MUST state this contract in the subagent prompt; (2) a
  deterministic PreToolUse Bash guard, `scripts/subagent-git-guard.sh`, blocks subagent
  `git commit` / `git push` / `gh pr create` / `gh pr merge` at runtime (main-context
  git is untouched — the guard acts only when the call carries a subagent identifier).
  The guard earned its HARD promotion (§2 POLICY) when the pattern recurred *despite*
  the prompt-level contract: an `executor` subagent committed + pushed + opened PR #205
  against an explicit "Do NOT commit" prompt. It is wired per-developer in
  `.claude/settings.json` (like the §4 reminder hook), and its regression test
  (`scripts/test/test-subagent-git-guard.py`) blocks in CI so the guard logic cannot
  silently regress.
- **A subagent's deliverable rides its final message — pin it (#211).** "Only the last
  assistant message returns to the caller" is a property of *every* subagent — native
  `Agent`/`Task` and schema-less Workflow `agent()` alike. A subagent can do correct work
  across many turns and then end with a content-free sign-off (`"done"`, `"완료"`); that
  sign-off — not the work — becomes the return value, and the real output is stranded in
  the transcript (confirmed: an omp-analysis workflow stranded 351k tokens of analysis
  behind `"Complete."`). Every spawn point MUST defend, strongest first: (1) **prefer a
  `schema`** — the subagent is *forced* to call `StructuredOutput`, so the validated object
  returns, never a stray sign-off; (2) when a schema is too rigid (free-form reports),
  **pin a final-message contract** in the prompt or agent definition — "your LAST assistant
  message IS the deliverable; never end on a content-free sign-off." This is a **repo-wide**
  rule, not substrate-local: the native-agent application is
  each agent's own "Final Response Contract" section (`thinking-facilitator`,
  `vault-searcher`, `vault-knowledge-manager`, `vault-file-organizer`). Sibling to the #209
  git contract above — #209 governs a subagent's *git side effects*, this governs its
  *returned output* (the two axes of the same "subagent contract" theme). Enforcement is
  convention + the §4 self-check, not a deterministic guard: "did the final message carry
  the deliverable?" is a judgment call (the §3 SOFT tier), so it is not made HARD. The
  general-candidate status of this contract (an abstract lift toward the machine level, the
  way #209 earned its promotion) is tracked in `docs/design/claude-kit-boundary.md` §0.
- **Concurrent work goes in an isolated git worktree (#234).** When another agent or
  tool is working this repo at the same time (e.g. a second CLI agent running its own
  slices in parallel), do your work in a **dedicated `git worktree`** — never the shared
  main checkout. Concurrent writers on one checkout race each other: index corruption,
  half-applied edits, branch confusion, and trampling a collaborator's in-flight work.
  This is the claude-kit-**concrete** form (the *how*) of a broad machine-level
  work-rule whose abstract *what + why* lives one altitude up (machine work-rule P1,
  lineage source `discovery-2026-06-14.md f15`); per §0 claude-kit holds only the
  concrete form, self-contained, with **no** runtime reference to that layer. Sibling to
  the #209 git contract above — both govern how a delegated/concurrent agent touches the
  repo. The rule stays SOFT overall, because "is someone else working this repo right now?"
  is a judgment call (the §3 SOFT tier), not deterministically detectable in general.
  **One slice of it is detectable, and since #594 it is guarded**: the 8th recorded
  near-miss was a session that never isolated *itself* — it edited the shared main checkout
  on the default branch for several commits, found only by a stray `git status --short`.
  "Am I writing the main checkout on its default branch?" is two git commands with no
  judgment in it, so `scripts/worktree-isolation-guard.sh` (PreToolUse Write|Edit, wired
  per-developer like the §4 reminder hook) warns on exactly that, once per session and repo.
  It **warns**, it does not block (`CLAUDE_KIT_WORKTREE_GUARD=enforce` opts into blocking):
  a false block costs a real session, which is why the rule keeps its SOFT tier and the §4
  self-check remains the enforcement for everything the guard cannot see. What it cannot
  see, deliberately: a write to the main checkout on a *feature* branch — #594's original
  incident shape, but also ordinary solo work, and nothing distinguishes the two without a
  record of who else is live (#594's claim-file proposal). Its regression test
  (`scripts/test/test-worktree-isolation-guard.sh`) blocks in CI so the detection cannot
  silently rot.
- **Identifiers ride the global ID; local tracking IDs stay local (#214).** The
  single authority for identifier prefixes is `docs/design/glossary.md`. Anything
  worth tracking globally becomes a GitHub issue (`#N`) — do **not** invent a
  parallel global tracking scheme (`U/P/W/D/C`). A document's running number is local:
  valid only inside that document; when cross-referencing, carry the source
  (`<file> §U1`) or promote it to an issue. Do not reuse a letter across meanings, and
  write local IDs letter+digit with no hyphen (`C2`, not `C-2`). Before introducing a
  new global prefix, register it in the glossary first.

## 2. POLICY vs PREFERENCE (c6)

This is the classifier that keeps the repo from hardcoding one person's taste onto
everyone who works in it.

> **The test: "Does a violation cause OBJECTIVE DAMAGE?"**

- **Yes → it MAY be promoted to POLICY.** A policy is a claude-kit-specific rule
  whose violation breaks something real and measurable. Policy is enforced by a
  deterministic check (a `scripts/check-*.py` or an external linter we *require to
  pass*), and it blocks in CI.
- **No → it stays PREFERENCE.** Taste, formatting, gray-zone style: the violation is
  cosmetic or arguable, with no objective damage. Preference is **never hardcoded**
  here. It is delegated to **external linter/formatter config** (`.prettierrc`,
  `ruff.toml`, etc.) so each repo/setup configures its own taste, and claude-kit
  only requires *that the configured linter passes* — it does not reimplement the
  linter or bake in style constants.

The promotion gate is one-directional: a rule must *earn* its way into POLICY by
demonstrating objective damage. When unsure, it stays PREFERENCE.

**POLICY — worked examples (objective damage):**

1. **`marketplace.json` ↔ `plugin.json` version/description/keywords drift.** If
   these diverge, a release ships divergent manifests and the marketplace serves
   wrong metadata. Objective damage → `check-version-sync` (block).
2. **A note written to the vault without a `type:` field.** Without `type:`, the file
   is invisible to claude-kit's management (v4 §2.2 opt-in) — capture/audit/search
   silently skip it, so the user's note is functionally lost to the tooling.
   Objective damage → `check-type-optin` (block).
3. **A registered regression test that exits non-zero (or is not wired into CI).** A
   green-looking suite that doesn't actually run, or a test that fails and is ignored,
   means a guard is silently off. Objective damage → `check-test-exitcode` /
   `check-ci-coverage` (block).
4. **A subagent that commits, pushes, or opens/merges a PR (#209).** A subagent
   publishing on its own breaks the isolated-critique premise (the review target is no
   longer an uncommitted diff) *and* performs an unapproved outward-facing, often
   irreversible action (a push / PR). This recurred despite the prompt-level contract
   (PR #205), which is what earned the promotion. Objective damage → runtime venue is
   the deterministic PreToolUse deny hook `scripts/subagent-git-guard.sh`; the
   CI-blocking part is its regression test (`scripts/test/test-subagent-git-guard.py`).

**PREFERENCE — worked examples (taste / gray-zone):**

1. **Line length, quote style, indent width, trailing commas.** Whether a line wraps
   at 88 or 100, single vs double quotes — no objective damage. Delegate to
   `ruff.toml` / `.prettierrc`; claude-kit requires the linter to pass, never
   hardcodes the constant.
2. **Import ordering / blank-line grouping.** Stylistic; a misordered import does not
   break behavior. Delegate to the external formatter's config.
3. **Markdown wrap width / list-marker style (`-` vs `*`).** Cosmetic prose
   formatting. Delegate to a markdown linter config if desired; not a claude-kit
   policy.

## 3. The 3-tier enforcement model (c5)

Enforcement has exactly three tiers. Heavier tiers cost more and are reserved for
where they are actually warranted.

- **HARD — deterministic, blocks in CI.** External linters/formatters (required to
  *pass*) plus `scripts/check-*.py` guards. These run in CI and a violation blocks
  the merge. No judgment, no LLM, no per-turn cost. The HARD checks, by name:
  - `check-version-sync` — marketplace ↔ plugin.json drift (existing).
  - `check-ci-coverage` — every registered test is wired into CI (existing).
  - `check-type-optin` — vault notes carry the `type:` opt-in marker.
  - `check-language-policy` — language policy (doc body language placement) holds.
  - `check-banned-words` — claude-kit-specific banned terms are absent.
  - `check-test-exitcode` — registered regression tests actually exit 0.
  - `subagent-git-guard` (#209) — a deterministic **PreToolUse Bash deny hook**
    (`scripts/subagent-git-guard.sh`) that blocks subagent `git commit` / `git push` /
    `gh pr create` / `gh pr merge`. Its enforcement *venue* differs from the checks
    above: it blocks in the **live session** (a Claude Code hook, wired per-developer
    like the §4 reminder hook), not at merge time. What blocks in CI is its regression
    test (`scripts/test/test-subagent-git-guard.py`), which keeps the guard logic from
    silently regressing. It is HARD because the violation is objective damage (§2 #4).
  - (Each non-existing check is described here at the **policy level**; its exact
    behavior is defined by its own slice/script, not invented here.)
- **SOFT — task-end self-check via the rules reminder hook.** Judgment-type rules
  that cannot be made deterministic are checked by the **main agent at task end**
  against the checklist in §4. A Claude Code hook fires the reminder so the check is
  not silently skipped; the main agent self-verifies. This is a reminder, not a
  blocker — it carries no per-turn LLM cost beyond the task-end trigger.
- **HUMAN — irreversible / release gates only.** A human gate is reserved for
  irreversible or release-time decisions (publishing a tag, anything not safely
  revertible). Everything safely automatable lives in HARD or SOFT; the HUMAN tier
  stays small on purpose.

**Deferred (YAGNI, c5): the haiku verifier.** A native haiku sub-agent verifier (to
guard against self-approval, following the `vault-searcher` haiku pattern) is **not**
built in v1. Self-approval in a single context is a *potential* problem, not a
demonstrated one. The verifier is added only **if self-approval proves to be a real
problem** — earning its way in exactly like a PREFERENCE→POLICY promotion.

## 4. The SOFT task-end checklist

At task end, the main agent self-checks the following (this is the SOFT tier in §3).
None of these block automatically — they are the judgment-type rules that a
deterministic script cannot fairly decide:

- [ ] **Traceability**: the change references its issue; the PR description (Korean)
      points back to the issue / spec / master plan. No forked decision trail.
- [ ] **Identifiers (#214)**: no new parallel global tracking scheme was invented;
      local tracking IDs (`U/P/W/D/C`) stayed local or carried their source on
      cross-reference; any new global prefix was registered in `docs/design/glossary.md`.
- [ ] **Stance/voice/work-rule separation (c1)**: no persona content (voice *or* stance)
      leaked into repo files; work rules stayed in `rules/`, tone and judgment-posture
      stayed in personal config.
- [ ] **POLICY vs PREFERENCE (c6)**: no subjective style constant was hardcoded; any
      style concern was delegated to external linter config, not baked in.
- [ ] **MECE / no reimplementation**: no external-linter behavior was reimplemented;
      claude-kit only delegates to and requires linters, it does not rebuild them.
- [ ] **Conventions**: conventional-commit subjects, branch prefix, version lockstep
      respected (no manual version bump in a feature branch).
- [ ] **Subagent git side effects (#209)**: no subagent committed, pushed, or opened a
      PR; changes were left in the working tree for the main context to own; any
      impl-delegating workflow prompt states the no-git-side-effects contract; if you
      ran agents on this repo, the runtime guard (`scripts/subagent-git-guard.sh`) was
      wired in your `.claude/settings.json`.
- [ ] **Subagent output contract (#211)**: every subagent spawn point either passes a
      `schema` or pins a final-message contract, so the deliverable rides the final message
      and is not stranded behind a content-free sign-off (`"done"` / `"완료"`).
- [ ] **Concurrent worktree isolation (#234)**: if another agent or tool was working
      this repo concurrently, your changes were made in a dedicated `git worktree`, not
      the shared main checkout — so concurrent writers did not race or trample each
      other's in-flight work. The detectable slice (writing the main checkout on its
      default branch) is warned by `scripts/worktree-isolation-guard.sh` when it is wired
      in your `.claude/settings.json`; the rest — a feature-branch write to the main
      checkout while a sibling session is live — is still only this self-check (#594).
- [ ] **HARD checks green**: the relevant `scripts/check-*.py` and external linters
      were run and pass (or are wired so CI will run them).
- [ ] **Recurrence (c7)**: if this violation looks like a *repeat pattern*, enter the
      RCA flow (§5) before closing out.

**How the reminder hook is wired.** The task-end reminder is a deterministic Claude
Code hook: `scripts/rules-checklist-hook.sh`, registered via the developer's local
`.claude/settings.json`. Note that `.claude/` is **gitignored**, so the wiring is
**per-developer by design** — each developer opts the hook into their own session;
the script is shared in-repo, the activation is local. The hook surfaces this
checklist at task end so the SOFT tier is not silently skipped.

## 5. Recurrence-driven RCA

When a violation is a **recurring pattern** (not a one-off), run the root-cause
analysis flow rather than just patching the symptom. The RCA checklist lives at
**`rules/rca-checklist.md`** — it is the entry point for the What → Why → How →
Revise flow, gated on recurrence and stopping at the level expressible as a
deterministic code change (so RCA does not regress into endless re-analysis). A
one-off slip does **not** trigger RCA; only a repeat pattern does.

## 6. Coverage of the 11 initial expectations (ac1)

The work-rules effort started from 11 expected items. Each is covered by a mechanism
in this minimal core. SOFT and DEFERRED rows mark **intended limits**, not gaps.

| # | Expected item | Mechanism | Tier |
|---|---------------|-----------|------|
| 1 | Style hygiene | `ruff.toml` / `.prettierrc` injected, run via `scripts/run-linters.py` (delegation, never hardcoded) | HARD-when-present / else exit 2 (#456) |
| 2 | Domain conventions | §1 + `check-type-optin` (vault `type:`) + `check-banned-words` | HARD + SOFT |
| 3 | No new plugin/skill | c2: zero new `plugin.json`/`SKILL.md`; rules live in `scripts/` + `rules/` + `.claude/` only | by-design (ac5 grep) |
| 4 | Persona separation | §0 — persona (voice + stance) in personal `~/.claude/CLAUDE.md`, work rules in `rules/` | SOFT (c1) |
| 5 | Enforcement | §3 three-tier model (HARD scripts + linters / SOFT hook / HUMAN gate) | structural |
| 6 | Procedure omission | §4 task-end checklist + `scripts/rules-checklist-hook.sh` reminder; `check-test-exitcode` | SOFT + HARD |
| 7 | Verification evidence | Deterministic scripts emit real exit-code evidence; `check-test-exitcode` runs registered tests; CI. No external-orchestrator dependency (c3) | HARD |
| 8 | Expression hygiene | claude-kit-specific banned terms → `check-banned-words` (HARD); general prose hygiene → external linters (delegation, c4) | HARD + delegated |
| 9 | Consistency / traceability | §1 (issue = canonical, trace-to-root) + `check-version-sync` + `check-ci-coverage` | HARD + SOFT |
| 10 | Telemetry | Reuse existing `telemetry/` (event-logger, `report.py` lifecycle). Rule-fire event schema **DEFERRED to #217** (telemetry external-distribution owner) — c8 | DEFERRED (soft) |
| 11 | Violation correction | §5 + `rules/rca-checklist.md` (4-step RCA, stop-at-determinism, recurrence gate) | reference (c7) |

**Intended limits.** Rows 4, 6 (checklist part) and 9 (traceability part) are SOFT by
design — judgment-type rules a deterministic script cannot fairly decide (c5). Row 10
(telemetry rule-fire) is DEFERRED: #217 owns telemetry external distribution, so the
rule-fire event schema is added there to avoid a split owner (c8 is the only non-hard
constraint). Row 1 is latent on a repo with no linter installed — the delegation
mechanism is committed and activates the moment a linter is present (c4). Latent is not
silent: since #456 a run where every linter skipped exits 2 and reports no verdict, so
"nothing was inspected" can no longer be read as "the tree is clean".
