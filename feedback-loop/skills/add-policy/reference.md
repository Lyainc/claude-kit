# add-policy — reference

Rationale, worked examples, and measured background for `SKILL.md`. Split out (#447) so the skill
body fits inside the 5,000-token window auto-compaction re-attaches. Everything here is *why* a
rule reads the way it does — never a rule the engine must not miss. Read a section when the
SKILL.md line pointing at it is the one you are acting on.


## §0 — written-artifact language, per site

The SKILL.md preamble states the rule; this is the full reasoning for the CLAUDE.md exception.

**User language: Korean for dialogue; written-artifact language depends on the site.** All
user-facing DIALOGUE (the classification readout, AskUserQuestion prompts, confirmation
messages, command suggestions) MUST be in Korean. For the prose the engine actually WRITES:

- **`~/.claude/rules` catalogue, a hook script + its comments, a skill's SKILL.md body**:
  English. These are pure procedural/LLM-executed artifacts with no reader-language identity
  of their own — they follow claude-kit's own Language Policy for skill/rule content, not the
  user-facing-output rule.
- **`~/.claude/CLAUDE.md`**: match that file's **own existing language**, don't force English.
  Unlike the sites above, this file is the user's actual stance/voice persona document — for a
  Korean-voice user it is written in Korean prose (including judgment/expression rules about
  *how to speak*), so an English insertion breaks the file's own convention and can be
  self-contradictory (an English line dictating Korean tone). Read the target file first and
  write the new line in the language it is already in.


## §1 — why a distill proposal arrives with the placement unfilled

SKILL.md §1 states both consequences in one sentence each.

The engine receives **both as natural language and re-runs the classification itself**.
A distill proposal NEVER carries the placement slots (the classification grid) pre-filled
— filling them would usurp landfill responsibility. Two consequences:

- **Tier is inferred by the engine from what/why, never supplied.** The proposal does not
  carry an enforceability/tier hint. Whether a rule is *deterministically guardable* (→ a
  hook) or *something a human must be reminded of* (→ reminder) is judged by the engine
  from the rule's **content**. This is not a missing input — it is the engine's designed
  responsibility: the user is not asked to name an axis; the tool infers it.
- **The inviolability judgment is respected, not re-made.** The judgment "is X
  inviolable?" belongs to discovery and rides in the proposal. The engine does not
  re-judge it — it *enforces* it (§5).


## §2 — why the default taxonomy is reusable, not personal

SKILL.md §2 ships the partition; this is the argument for shipping one at all.

> **Why this default is reusable, not personal**: the three layers partition
> behaviour-rule space by a property of the *rule*, not of any individual — "is it about
> what you judge, how you express, or how you work?" Every rule lands in one. Personal
> *instances* of these layers (specific address forms, a specific critic stance, a
> private rules catalogue) are NOT shipped here — only the empty partition is.


## §3 — the loaded-directory leak, as measured

SKILL.md §3 states the rule (`never add a second .md inside ~/.claude/rules/`); this is what happened when it was broken.

- **Everything under `~/.claude/rules/` is loaded, not just its index.** Claude Code reads
  *every* `.md` in that directory into every session, so a catalogue that splits a thin index
  from per-entry detail files only saves context if the **detail files live outside the loaded
  directory**. Follow the index's own links to find where they actually are, and write a new
  one beside them. Never add a second `.md` inside `~/.claude/rules/` on the assumption that
  "it's only the detail, it won't be read" — observed in practice, 12 detail files placed in
  `rules/policies/` rode in every session (~41 KB) while the index claimed the split had
  thinned the surface.


## §3-sites — the conflict-check target per site, and why the fallback is non-negotiable

SKILL.md §3 ships the site table without a per-site conflict-target column; §6 states the rule
generically ("read the current contents of the chosen site"). What that resolves to:

| Site | What §6 reads before writing |
|------|------------------------------|
| **reminder** | that channel's current rules — CLAUDE.md's persona block, or the catalogue index *plus* the detail files its links resolve to |
| **hook** | the existing hook matchers and guard scripts, so a second guard doesn't fire on the same event |
| **skill** | existing skills, in the order patch > extend > new |

And the fallback: **a confident write into a non-existent catalogue is the breakage the
`[ -d "$HOME/.claude/rules" ]` detection guards against.** The engine cannot assume the machine
it is running on has the same private structure as the one it was written on.


## §3-tier — worked examples of the layer → tier inference

SKILL.md §3 states the rule; these are the cases it was derived from.

**Layer → tier default (engine inference, reduces variance):** *judgment* and *expression*
are **always SOFT** (a reminder — they are not deterministically guardable). A *work-rule*
is **HARD (→ hook) iff its violation is deterministically detectable**, else SOFT (→
reminder): "leave deletes recoverable / never `rm`" is detectable → hook; "run Python
through the project runner" stated as a habit is a reminder. This is the engine's tier
inference from what/why, never a user-supplied axis.


## §4 — user-shell receiver, in full

SKILL.md §4 keeps the rule; this is the original section with its receiver/audience reasoning.

### 4. User-shell receiver — the destination outside the three sites

The three sites are all **inside the Claude Code substrate** (CLAUDE.md / hook / skill).
A rule whose **receiver is the user's own shell** — a command alias, an environment
setting — has no home among them. This is NOT a fourth landfill site (there are exactly
three, per §3); it is an out-of-band destination handled by emission only:

- The engine judges such a rule **outside the three sites** and **emits a command only**:
  "this is a shell-level setting — add this line to your shell config yourself." The
  engine does **not** write the user's shell files directly (outside the repo, higher
  risk).
- **Receiver/audience match is a rule, not a nicety**: a rule's receiver and the site's
  reader must match. A task-end reminder, for instance, is read by the main context only
  — putting a subagent-directed rule there is a receiver mismatch (the next session never
  reads it). State this in the placement reasoning: place a rule where its intended
  audience actually reads.


## §5 — provenance inspection and the old `metadata.provenance` fail-safe

SKILL.md §5 keeps the three provenance gates and the existence check.

The engine respects the discovery judgment; it does not re-run it, but it *does* execute
the block. Verify before writing: read the target's frontmatter and confirm provenance.
Read-only `Bash`/`Grep` is the natural way to inspect provenance across candidate skills
(e.g. grep the frontmatter of `~/.claude/skills/*/SKILL.md`) — the same read-only use
`distill` retains for its discovery checks. **Check `[ -d "$HOME/.claude/skills" ]` first**:
on a vanilla machine with no prior distilled/personal skills, that directory doesn't exist
yet, and a glob against a missing directory errors instead of matching nothing — treat a
missing directory the same as "no existing skills found" (nothing to conflict with,
`mkdir -p` it and create the new skill), not as a scan failure.

> **Migration note (old `metadata.provenance`)**: skills written by the *previous* distill
> carried a nested `metadata.provenance: distilled`, not a top-level key. The engine reads
> the top-level `provenance:` only, so such a skill falls into the "unknown marker →
> inviolable" branch — protected, but not engine-revisable. This is the **intended
> fail-safe** (safe > overwrite). To let the engine revise an old distilled skill, add a
> top-level `provenance: distilled` line to its frontmatter.


## §6-new-site — why a read error is not a missing file

SKILL.md §6 keeps the rule and the `[ -f ]` check.

**New site (no prior conflict possible)**: check whether the target file **exists** first —
`[ -f "$TARGET" ]`, the same existence-check principle §5 uses for the skill site (there it's
a directory check, `[ -d "$HOME/.claude/skills" ]`) — never infer
"missing" from a read *error*, since a read can fail for reasons other than absence
(permissions, a transient tool error), and misdiagnosing one of those as "missing" would skip
the conflict check and **overwrite existing content** instead of appending to it. If the
existence check confirms the file genuinely isn't there yet (a brand-new machine, e.g. no
`~/.claude/CLAUDE.md` at all), there is nothing to conflict with: skip straight to writing,
and **create the file (`Write`)** with the new rule instead of appending (`Edit`). If the
file exists but reading it still fails for some other reason, stop and report the failure —
do not guess.


## §6-memory — why the memory scan is two steps

SKILL.md §6 keeps both steps and the content-match rule.

**The Duplicate scan also covers native auto-memory** — Claude Code's auto-memory
(`~/.claude/projects/<proj>/memory/*.md`) stores `feedback`-type entries, which are *the same
kind of thing this engine lands*: user guidance on how to work. Auto-memory writes are never
checked against the reminder sites, so a rule already landed in CLAUDE.md / `~/.claude/rules`
can sit duplicated in memory and neither side catches it — the landfill write is the one moment
that can. So scan **both** the chosen site's current content **and** those `feedback` memories.

This is **two steps, and conflating them is a data-loss bug**: the command below only **lists
candidate files** (every `feedback` memory in scope — on a real machine that is routinely a dozen
unrelated ones). A *Duplicate* is decided in step 2, by **reading each candidate and comparing
its content to the rule being landed**. Only a content match is a hit. A file that merely has
`type: feedback` is not a duplicate and is never touched.


## §6-snippet — why the scan command is written the way it is

SKILL.md §6 ships the runnable snippet with one-line comments; this is the full reasoning behind each choice, including the `n starts at 9` guard, zsh NOMATCH, and why `2>/dev/null` is banned.

```bash
# Machine-global site -> all projects. Project-scoped CLAUDE.md -> that project's dir only:
#   SCAN_ROOT="$HOME/.claude/projects/<current-project-dir>"
SCAN_ROOT="$HOME/.claude/projects"
# `find`, not a glob: `~/.claude/projects` exists on any machine that ever ran Claude Code, but
# `memory/` only appears once auto-memory has written something — an unmatched `*/memory/*.md`
# glob aborts the command (zsh NOMATCH) instead of scanning nothing.
# `awk`, not `grep`: the type must be read from the FRONTMATTER (n==1 = between the `---`
# fences), or `type: feedback` quoted in a note's body matches. Line 1 must BE the opening
# `---`, else n starts at 9 and never reaches 1 — otherwise a file with no frontmatter at all
# would let its first body `---` (a horizontal rule) open a fake frontmatter. Trailing `$` on
# the value, or `type: feedback-loop` matches. `|| true`: a missing SCAN_ROOT is not a failure.
# NO `2>/dev/null`: a dead awk or an unreadable file must be VISIBLE. The pipe already fixes
# the exit code at `sort`'s, so stderr is the only channel left that can say "this scan is
# incomplete" — and a duplicate check that fails silently reports "no duplicates", which is
# the wrong direction to fail. If anything lands on stderr, treat the scan as INCONCLUSIVE and
# say so; do not report "memory 중복: none".
[ -d "$SCAN_ROOT" ] && find "$SCAN_ROOT" -path '*/memory/*.md' -not -name 'MEMORY.md' -exec awk '
  FNR==1 { n = ($0 ~ /^---[[:space:]]*$/) ? 0 : 9 }
  /^---[[:space:]]*$/ { n++ }
  n==1 && /^[[:space:]]*type:[[:space:]]*feedback[[:space:]]*$/ { print FILENAME }
' {} + | sort -u || true
```


## §6-gate — why the necessity gate exists, and why it only recommends (#450)

SKILL.md §6 ships the four questions and the three outcomes. This is what they were derived from.

**The engine had an entry path and no "don't land this" verdict.** Of §6's verdicts only
Contradiction stops a write, and it stops it for *disagreeing with an existing rule* — a rule
that contradicts nothing and is simply unnecessary passed straight through.

**Measured failure — P14.** `local-harness` P14 landed on 2026-07-24 with two guards and was
retired the next day (`local-harness/docs/decisions/2026-07-25-p14-hook-retirement.md`). Two of
the retirement's three findings were knowable at landing time:

- *The gate was doubled.* `session-close` ① already asked the same question with the owner's
  confirmation in hand; the new guard re-asked it from a position with less information. P14's
  own design document had named ① as the place that judgment belonged — question 3 is that
  finding turned into a question.
- *The predicate measured a different quantity.* The evidence was commit counts; the
  implementation read PR *age*.

Retirement cost five hand-assembled steps (trash the guard, unwire `settings.json`, delete the
row, fix every inbound citation, write the decision record), with nothing checking coherence.
`Supersede` does not catch this case: P14 was not displaced by a later rule, it should never
have entered. Its firing record was one guard twice (both overridden, then merged) and the
other zero times.

**The standing cost is measured, not speculative.** `local-harness/rules/README.md` rides in
every session in full: on 2026-07-23, framing 6,571 B against 3,704 B of actual policy — 64% of
the per-session catalogue cost was not policy. The 2026-07-10 index+detail split put 12 detail
files in `rules/policies/`, where the recursive loader picked all of them up (~41 KB per
session) while the README claimed the split had thinned the surface. Accumulation runs ~1 policy
per 3.3 days against 1 removal in 39 days.

**Why recommendation-only.** A gate that can refuse turns 1 click into 2 and puts the tool in
the position of vetting work the user explicitly asked for. Rejected alternatives: an isolated
subagent verdict per landing (too heavy — revisit if the gate is observed rubber-stamping
itself); a post-hoc audit skill or usage-based cleanup (no firing telemetry, and "decide after N
weeks of observation" is a pattern this repo rejects — and post-hoc cleanup does not address the
entry path at all); putting the gate in `distill` (the `/add-policy` direct-invocation path
never passes through distill, and distill does not know the site's cost).

**Why this is not distill's question.** `distill` asks what a rule is *worth* — is it reusable
at class level. The gate asks what the *artifact* costs — must this be a **new** entry, is it
worth an always-loaded line. Only the side that knows the site (catalogue size, hook surface,
neighbouring entries) can answer the second. It is a placement judgment, not a value judgment,
which is the same line #429 draws — hence the precision in SKILL.md's intro and in the
`description`: add-policy never re-judges *reuse value*, but it does judge *artifact necessity*.


## §6-supersede — why the exit path is a §6 verdict (#429)

SKILL.md §6 ships the verdict. The measurement behind it:

- 2026-06-14 → 2026-07-23: 12 policies in 39 days (~1 per 3.3 days) in `local-harness`.
- Policies removed in that window: **1** (P7 absorbed into P9), and that was a by-product of a
  manual audit, not of any rule.
- At that rate the catalogue reaches 30 entries by late September. Since `~/.claude/rules` is
  loaded whole into every session, entry count is standing token cost — and matching degrades
  faster than cost grows: against a flat 30 rows the model compares its moment to 30 candidates,
  and every row that doesn't fire lowers the credibility of the rows that do.

**Why a fifth verdict rather than a new mechanism.** The engine already reads the target site's
full current content on every run (§6). Hanging the exit path on the entry path costs one more
verdict and no new surface.

Rejected: usage-based retirement ("drop a policy that hasn't fired in N months") — there is no
firing telemetry to measure, and "observe for N weeks, then decide" is rejected here as a
pattern; a periodic audit skill — a new surface that only runs when a human runs it (in
practice, twice, both manual).

**Why the engine may own it.** `add-policy` does not re-judge what is worth keeping — that is
distill's. Supersede asks "does this new rule make that entry redundant", a *placement*
judgment about the artifact, so it belongs to the landfill side. Same boundary as §6-gate.

**Out of scope, with a trigger**: grouping the catalogue table by *when a rule is needed*
instead of by number ("30 rows to match" becomes "pick a group, match 4"). Start when the table
passes **20 rows**; below that a flat scan is cheaper than the structure. That is catalogue-side
work (local-harness), not `add-policy`.


## §7 — output contract, in full

SKILL.md §7 keeps the working-tree rule and the closing line; this holds the written-content language rule and the hook registration fragment.

### 7. Output contract

- **Language of the written content itself**: English for the rules catalogue, a hook
  script, or a skill body; for `~/.claude/CLAUDE.md` match that file's own existing
  language instead — see the language directive above. The confirmation dialogue around
  the write is always Korean regardless of site.
- Every change is left **in the working tree**. **No commit / push / PR** — the main
  context owns git.
- For the **hook** site, the engine emits the guard script *and* the registration diff to
  the working tree only; it **never self-registers or activates** a hook before the user
  approves (the guard appears as a reviewable diff first). The registration entry follows
  the Claude Code `hooks` shape — `{event-type} → matcher → command array` — e.g.:
  ```json
  { "matcher": "Bash", "hooks": [{ "type": "command", "command": "bash <guard-script-path>" }] }
  ```
  The user wires this into the `hooks` block of their Claude Code configuration; the engine
  emits the fragment but does not name or assume a specific config filename.
- **Zero own harness hooks (CON-2)**: the engine adds no hooks to claude-kit's own harness
  surface. Writing a hook into the *user's* configuration is a landfill *output* — user
  machine state — not a claude-kit harness hook. The distinction matters: the engine's own
  validation is in-skill, never a registered harness hook.
- If a guard script was added, leave `chmod +x` / activation / a live test to the main
  context (this skill emits text into the working tree; the main context runs, verifies,
  and commits).
- Close with one Korean line: "메인 컨텍스트가 검토 후 커밋하세요."


## §8 — worked self-check example for the skill site

SKILL.md §8 keeps the per-site checks themselves. They are the **landfill-side artifact
verification** that moved here from distill's old Phase 5 — distill kept only the
discovery-side placement-fit judgment.

Example for a freshly written skill (best-effort, Korean report on failure):

```bash
SKILL_PATH="$HOME/.claude/skills/<name>/SKILL.md"
[ -s "$SKILL_PATH" ] && grep -q '^name:' "$SKILL_PATH" && grep -q '^description:' "$SKILL_PATH" \
  && grep -q '^allowed-tools:' "$SKILL_PATH" && grep -q '^provenance:' "$SKILL_PATH" \
  && echo "self-check OK" || echo "self-check FAILED — report to user in Korean"
```
