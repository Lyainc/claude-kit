# RCA Checklist (rules/rca-checklist.md)

A thin **reference** for root-cause analysis in claude-kit. This is a doc, not a skill and
not a workflow. Nothing executes it; the `retro` skill (feedback-loop) stays a *thin
consumer* — when retro routes a finding to the `rule` output, it may link here, but it does
not embed this procedure (spec `claude-kit-work-rules.yaml` constraint **c7**). Read this
when a defect or rule-violation is a **repeat**, decide the fix, and stop.

Scope: claude-kit work itself (plugins, scripts, hooks, docs, CI). Style and expression
hygiene are out of scope — those are delegated to external linters/formatters
(`.prettierrc`, `ruff.toml`, etc.) per **c4**. RCA here targets claude-kit-specific policy
where a violation causes *objective damage*, never taste (**c6**).

---

## When to enter RCA — the RECURRENCE GATE

Do **not** run this 4-step procedure for every mistake. Over-applying it overfits the
codebase to one-time accidents and bloats the guard surface.

- **First occurrence of a defect class → direct fix.** Fix the symptom, move on. No RCA,
  no new permanent guard. One-offs happen; a one-off does not justify a forever rule.
- **Second occurrence of the *same class* → enter RCA.** Repetition is the signal that the
  cause is systemic, not incidental. The second time a class of violation appears, run the
  4 steps below and add a *permanent* deterministic guard so there is no third time.

"Same class" means the same root mechanism, not the same surface text. Two different files
drifting between `plugin.json` and `marketplace.json` are the *same class* (version-sync
drift); a typo in one file and a logic bug in another are *different classes*.

If you are unsure whether something is a repeat, treat it as a first occurrence (direct fix)
— the gate is biased toward *less* guard-building, because a guard that never fires is dead
weight that telemetry will later flag (spec **c8**).

---

## The 4-step RCA: What → Why → How → Revise

Run these in order. Each step has a concrete exit condition.

### 1. What — name the observed violation/defect

State the *observable* fact, not a guess: what broke, where, and how it was noticed (a
failed check, a CI red, a review comment, a wrong output). Pin it to a concrete artifact —
a file path, a check name, a commit. If you cannot point at something observable, you do not
yet have a "What"; you have a hunch. Stop and gather evidence first.

Exit when: the defect is reproducible or at least pinned to a specific artifact and trigger.

### 2. Why — trace upstream to the origin (with STOP-AT-DETERMINISM)

Ask why the defect was *possible*, then ask why *that* was possible, walking upstream toward
the origin — the earliest point where a different decision would have prevented the whole
chain. The point of tracing past the immediate symptom is to fix the cause once instead of
patching every downstream copy.

**STOP-AT-DETERMINISM (c7).** Stop tracing the moment the cause is expressible as a
*deterministic code or config change*: a new or tightened `scripts/check-*.py` rule, a CI
step in `validate.yml`, or an entry in an external linter config. That expressible point
*is* the root cause for our purposes. Do **not** keep tracing into unfalsifiable territory
("we weren't careful enough", "the team should think harder", "the process is immature") —
those are not roots you can encode, so they cannot close the loop and they invite endless
regress.

Concretely, you have reached a valid stopping point if the answer to "what one mechanical
change makes this impossible to reintroduce silently?" is itself mechanical:

- a check script that exits non-zero on the bad state (block) or warns (soft);
- a config entry handed to an external linter (style/expression — delegated, not
  reimplemented per **c4**);
- a CI wiring change that makes an existing check actually run.

If the only honest answer is "a human should remember to…", you have **over-traced** — back
up to the last deterministic checkpoint, or conclude this class genuinely belongs to the
*soft* layer (a work-end reminder, not a hard guard) and record that decision rather than
inventing an unenforceable rule.

Exit when: the cause is stated as a specific deterministic change, OR you have explicitly
classified it as soft (judgment-type, reminder-only).

### 3. How — fix across ALL affected artifacts, consistently

Apply the fix everywhere the cause manifests, in one consistent pass — not just at the spot
where it was first noticed. A root cause usually has several downstream expressions; fixing
one and leaving siblings inconsistent is how the *next* repeat is born.

- Enumerate every artifact touched by this cause (all plugins, both `plugin.json` and
  `marketplace.json`, every doc/mirror pair such as CLAUDE.md ↔ AGENTS.md, every fixture).
- Fix them to a single consistent state.
- Prefer reusing an existing mechanism over inventing one. If a `scripts/check-*.py` already
  owns this domain, *tighten* it rather than adding a parallel checker.

Exit when: no affected artifact is left in the broken state and the immediate defect no
longer reproduces.

### 4. Revise — encode the fix so it cannot recur

Make the deterministic change identified in step 2 real and *wired in*, so the same class is
caught automatically next time. This is what separates RCA from a normal fix: the symptom is
gone *and* the door is closed.

- Add or tighten the `scripts/check-*.py` rule (or external linter config entry).
- Give the check a `--self-test` so the rule itself is regression-tested (every check in this
  repo follows that convention — see `scripts/check-version-sync.py`,
  `scripts/check-ci-coverage.py`).
- Add a failing-then-passing fixture/case proving the new guard catches the original defect.
- Make it actually run: register the check in `docs/VALIDATION.md`'s `## Validation` list
  **and** in `.github/workflows/validate.yml`. (`check-ci-coverage.py` exists precisely to
  catch a check that is registered but never wired into CI — a guard you forget to run is
  no guard.)

Exit when: the new/tightened guard fails on the original bad state and passes on the fixed
state, has a `--self-test`, and is wired into CI.

If step 2 concluded the class is *soft* (judgment-type), "Revise" instead means: record it
in the soft work-end checklist surface so the work-end trigger reminds about it — not a hard
block. Do not fabricate a deterministic check for something that is genuinely judgment.

---

## Worked example: version-sync drift

A small end-to-end pass, showing How → Revise landing on a deterministic check.

- **Recurrence gate.** A plugin's `version` in `marketplace.json` once lagged its
  `plugin.json` — fixed by hand (first occurrence, direct fix, no RCA). Later, a *second*
  plugin shipped with a `description` mismatch between the same two files. Same class
  (manifest fields drifting out of sync). The gate now opens: enter RCA.

- **What.** A release shipped a `marketplace.json` entry whose `description`/`version`
  disagreed with the plugin's own `.claude-plugin/plugin.json`. Observable: divergent
  manifests in the merged commit; users saw a stale description.

- **Why (trace upstream, stop at determinism).** Immediate cause: the two files were edited
  independently and nothing compared them. Upstream: `plugin.json` is the source of truth and
  `marketplace.json` is derived, but the derivation was manual, so any manual edit could
  diverge. The honest "one mechanical change that makes this impossible to ship silently" is:
  *a check that compares the synced fields and exits non-zero on any drift.* That is
  deterministic and falsifiable — **stop here.** (Tracing further into "be more careful when
  editing manifests" is unfalsifiable; do not go there.)

- **How (all artifacts, consistent).** Reconcile every drifting field across *all* plugin
  entries to a single consistent state, with `plugin.json` winning (it is the source of
  truth). Not just the one description that was noticed — sweep every entry so no sibling is
  left inconsistent.

- **Revise (encode so it cannot recur).** `scripts/check-version-sync.py` enforces
  `name`/`version`/`description`/`keywords` parity as a **block** guard (drift → exit 1),
  ships a `--self-test` covering each drift type, offers `--fix` to reconcile from
  `plugin.json`, and is wired into `## Validation` + `validate.yml`. The same defect can no
  longer reach `main` silently. The loop is closed.

This is the shape every RCA should reach: the "Revise" step is a concrete, self-tested,
CI-wired deterministic guard — or an explicit, recorded decision that the class is soft.
