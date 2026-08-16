# Adversarial Review — Design Rationale

**Canonical text.** These paragraphs used to sit in `SKILL.md`; they moved here under #663 so the
skill body keeps headroom against the #447 token budget. Nothing was trimmed — the rules themselves
stay in the body, only their *why* lives here. This file is background reading for a human editor,
not an instruction the skill applies mid-run.

**Every `##` section below is a pinned contract, not background.** Each one is compared WHOLE and
verbatim (whitespace-normalised) against a constant in `_RATIONALE_SECTIONS`, in
`thinking-tools/scripts/test/test-judge-rubric-anchors.py`. The slice runs from the heading to the
NEXT heading, and a partial edit at either end — head sentence, tail sentence, or a rewritten
number — reds. The heading set is pinned too, at every depth, so a new section reds until someone
pins it. Editing any of this text is therefore a deliberate contract change, and the matching
constant is updated in the same commit. Sentence-level pins were tried first and did not converge:
each round closed one edge and exposed the next. What this still does NOT catch is contradicting
prose parked in an unpinned region next to a pinned one; only whole-file equality would, and that
was rejected as costing more than the residual risk.

## Attacker angle input (#423)

The Steelman is model-authored, so selecting from it would make the angle vary run-to-run on one
claim (measured 2026-07-22, #423) and break the shared-input guarantee with `expert-panel`. The
domain does not change between a claim and its steelmanned form; only the framing does, and framing
is what shifted the selection.

## Shared-pool contact point

Both skills run the rule on that same original text and every cut starts at rank 1, so the two
point at the same pool entry for a given claim. (The rule itself — the fixed role labels are never
selected from the pool and never change per topic — stays in the loaded body, where the skill can
act on it.)

## Angle recovery after compaction

The Selection Rule's input is the submitted claim rather than the Steelman partly for this reason:
a compacted session may no longer hold the Steelman verbatim, while the original topic text is
recoverable.

## Single-claim cache sizing

The Phase 0.5 one-shot call is sized for the typical **single-claim** session. Reusing the first
claim's cache across later claims preserves the token budget at the cost of not surfacing
claim-specific decisions for subsequent claims.

## Backlog prefilter cost

The Phase 0 scan is one deterministic shell scan of the open+closed issue corpus (same script
`build-spec` Phase 0 uses, #489), separate from Phase 0.5's vault-searcher token budget.

A surfaced conflict is never a forced verdict, because the claim can still survive a known
conflict — it just cannot survive one the Attacker never saw.

## Standard-mode visibility is best-effort

Outside isolated execution mode the Role Visibility Contract is a prompt contract only: the LLM
shares full conversation history across personas. Isolated execution mode provides mechanical
isolation via subagent context boundaries.

## Backlog scan carry-over is not optional

Stating the Phase 0 result distinguishes "scanned, no conflict" from "never scanned", which mirrors
`build-spec`'s `context.backlog_scan` contract (#489).

## Why vault access is vault-searcher's alone

Searching is vault-searcher's job (MECE boundary); critiquing is this skill's job.

## Why the auto-defender needs a quality floor

The floor keeps Survival Score reflecting the claim's actual strength rather than an
under-motivated auto-defender's laziness.

## Why the export schema block is mandatory

The block lets a downstream skill read the verdict counts without parsing the prose body, so an
exported report without it is not machine-readable.

## Isolated-Judge fallback rendering (#433)

The one-line `[격리 판정 실패 — 자체 판정, 신뢰도 낮음]` note mirrors the isolated-fallback pattern
`build-spec`/`unknown-discovery` already use for their own gate-imminent scoring (#433): a
self-judged round and an isolated one differ in confidence and must not render identically.

## Automated Defense subagent isolation

An inline auto-defender shares context with the Attacker turn that just produced the attack, which
biases it toward a generic, half-hearted rebuttal; a dedicated subagent call removes that bias the
same way isolated Judge removes evaluation bias.

## Automated Defense cost

Unlike Phase 0.5's one-shot vault-searcher call, which carries an explicit token ceiling in the
body, 자동 방어 spawns a fresh Defender subagent every attack round — up to 5 rounds × N claims per session. No explicit
token ceiling is enforced here; the isolation guarantee is worth the added subagent calls since
자동 방어 is opt-in.
