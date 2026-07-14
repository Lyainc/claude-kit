---
name: add-policy
description: "The landfill engine of the ⑤ self-improvement loop: take ONE work-policy / convention / rule — stated by the user in natural language, or handed off as a distill proposal — infer its classification, and place it in one of three native landfill sites (an always-read reminder — CLAUDE.md for stance/voice or the ~/.claude/rules work-rule catalogue — a deterministic hook guard, or an invocable skill) behind a single 1-click confirmation. Leaves every change in the working tree; never commits. Trigger: 이 규칙 추가, 이거 어디다 정리, 정책 분류, 규칙 매립, add policy, add-policy, classify this rule, where does this rule go, land this rule, /add-policy. Routing: distill (sibling) DISCOVERS what is worth keeping and emits the proposal; add-policy LANDS it — distill never fills the placement, add-policy never re-judges what to keep. Declarative knowledge (facts/decisions) = vault /capture·/note, not a policy. Example: '/add-policy' or '이 규칙 어디다 넣을지 분류해줘'."
model: inherit
allowed-tools: Read Edit Write Bash Glob Grep AskUserQuestion
---

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

Instructions below are English for LLM parsing.

# add-policy — the landfill engine (layer ⑤)

`add-policy` is the **landfill half** of the recursive-improvement loop: it takes one
work-policy/convention/rule and answers **"where does this go, and in what form?"**,
then writes it there on a single confirmation. It is not a magic generator — it makes
classification *consistent* and placement *standardized*. Classification is a judgment,
so it goes through one human confirmation; placement, once the classification is fixed,
is deterministic.

Its sibling `distill` is the **discovery half**: distill judges *what* is worth keeping
and emits a natural-language proposal; `add-policy` decides *where and how* to embed it.
The two never overlap — distill does not fill the placement, and `add-policy` does not
re-judge whether the rule is worth keeping.

## 1. Input contract — what the engine accepts

The engine takes a rule stated in **natural language**, from either source:

- **User natural-language rule** (direct invocation): a one-liner like "from now on,
  always do X" / "never do Y".
- **distill proposal object** (the discovery → landfill handoff) carrying:
  - **what**: the technique/rule content in one line;
  - **why**: what is lost if it is not captured (the reuse value);
  - **session provenance**: the session pattern it was observed in;
  - **inviolability judgment**: if the proposal patches an existing skill X, is X
    user-authored (inviolable)? — see §5.

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

## 2. Classification grid (default taxonomy — editable, replaceable)

Seat the rule on the grid below. This grid ships as a **default starting taxonomy, not a
hardcoded ontology**: a user who disagrees edits the labels or empties them. It is a
validated default so the engine is not an empty shell, but it is meant to be adapted.

**Layer — what kind of rule is this?** (a general MECE of behaviour-rule space — any
user's rule falls into exactly one, independent of who fills it in):

- **judgment** — what you *decide/assess* (e.g. "don't agree without evidence"). Pure
  judgment/honesty rules usually live in the reminder site's persona block, not a guard.
- **expression** — how you *say/phrase* things (tone, address, wording). Lives in the
  reminder site's voice block.
- **work-rule** — how you *do the work* (e.g. "run Python through the project's runner",
  "leave deletes recoverable"). The most landfill-shaped layer.

The layer is reasoning the engine does internally to pick a site — it is **not exposed to
the user as an axis to fill in** (see §3, 1-click). The default labels (judgment /
expression / work-rule) are editable; swap or drop them for a different vocabulary.

> **Why this default is reusable, not personal**: the three layers partition
> behaviour-rule space by a property of the *rule*, not of any individual — "is it about
> what you judge, how you express, or how you work?" Every rule lands in one. Personal
> *instances* of these layers (specific address forms, a specific critic stance, a
> private rules catalogue) are NOT shipped here — only the empty partition is.

## 3. The three landfill sites (+ tier absorbed, 1-click UX)

There are exactly **three** native places a rule actually lands. Keeping the count small
is what makes classification reliable and keeps the engine portable.

| Site | What it is | Tier absorbed | Form | Conflict-check target |
|------|-----------|---------------|------|----------------------|
| **reminder**<br>(CLAUDE.md or `~/.claude/rules`) | an always-read reminder rule; the channel is **layer-determined** (see below) | **SOFT** (the model reads it and follows) | one prose line/paragraph appended to the layer's channel | the chosen channel's current rules |
| **hook** | deterministic auto-enforcement | **HARD** (a PreToolUse-style guard blocks) | a working guard script + a registration entry in the project/user `hooks` configuration Claude Code loads — emitted to the working tree only, never self-activated | existing hook matchers/scripts |
| **skill** | an invocable procedure | (n/a — a procedure, not a tier) | `~/.claude/skills/<name>/SKILL.md` | existing skills (patch > extend > new) |

**Tier folds into the site, so the user never picks an axis:**

- *layer* answers "what kind of rule" (internal reasoning),
- *tier* answers "auto-enforced or just reminded" → **HARD ⇒ hook, SOFT ⇒ reminder** (the
  reminder *channel* is then routed by layer — below),
- the scope/channel question ("which CLAUDE.md? which config?") is the site choice itself.

**Layer → tier default (engine inference, reduces variance):** *judgment* and *expression*
are **always SOFT** (a reminder — they are not deterministically guardable). A *work-rule*
is **HARD (→ hook) iff its violation is deterministically detectable**, else SOFT (→
reminder): "leave deletes recoverable / never `rm`" is detectable → hook; "run Python
through the project runner" stated as a habit is a reminder. This is the engine's tier
inference from what/why, never a user-supplied axis.

**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):** a SOFT rule
is a reminder, but *which* always-read file it lands in depends on its layer:

- **judgment / expression** (stance·voice — what you decide, how you phrase) → the
  top-level **`~/.claude/CLAUDE.md`** persona block.
- **work-rule** (how you do the work) → the machine **work-rule catalogue
  `~/.claude/rules`** *if it exists*; **otherwise fall back to `~/.claude/CLAUDE.md`**.

The engine already computes the layer (§2); it only routes the SOFT channel by it — no new
site, no new axis. The fallback is **non-negotiable: never hardcode the machine's `rules/`
structure**. Detect it (`[ -d "$HOME/.claude/rules" ]`) and degrade to CLAUDE.md on a
vanilla machine where `~/.claude/rules` is absent — a confident write into a non-existent
catalogue is the exact breakage this guards against. (Receiver/audience match, §4: a
work-rule's reader is the work-rule catalogue, a persona rule's reader is CLAUDE.md.)

**Thin pointer + backing detail (when the catalogue channel is used):** machine-level
reminders ride in *every* session's context, so the always-on surface must stay thin. When
a work-rule lands in `~/.claude/rules`, put the detail in the catalogue (its native form)
and keep `~/.claude/CLAUDE.md` to at most a one-line pointer — add no pointer if the
catalogue is already pointed at. This mirrors the catalogue's own thin-list-routes-to-detail
shape (a thin CLAUDE.md on top, the backing detail below). Never paste the full rule prose
into the always-read CLAUDE.md.

**1-click confirmation**: present the *decision*, not the grid. Show the user where it
will land, the exact text/diff that will be added, and one short line of why-here — then
ask a single confirmation:

```
## 분류 결과
- 규칙: <one-line summary>
- 들어갈 곳: <CLAUDE.md | hook | skill> — <one-line reason: HARD라 자동강제 / SOFT라 리마인드 / 절차라 호출형>
- 추가/변경될 내용: <the exact prose / guard / skill stub to add, OR the existing entry's before → after if this is an edit>
- 충돌: <none | sibling of an existing rule | edits an existing entry (show before→after) | contradicts an existing rule (explain)>
- memory 중복: <none | 이 규칙이 memory에도 있어요: <path...> — 매립 후 그 항목은 지울게요 (§6)>
  (내용이 실제로 겹치는 것만. `type: feedback`이라고 다 중복인 건 아니에요 — §6 step 2)
```

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" The user confirms or
redirects. **Never write without confirmation.** If any axis cannot be settled (e.g. a
high-risk target where a confident-wrong placement would be damaging), do NOT place it
arbitrarily — hold the classification and report what is ambiguous ("don't know" beats a
confident-wrong placement).

## 4. User-shell receiver — the destination outside the three sites

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

## 5. Inviolability safety mechanism (the engine enforces it)

The *judgment* "skill X is user-authored / inviolable" is discovery's (it rides in the
distill proposal). The **mechanism** that prevents an overwrite is the engine's — and it
is non-negotiable, because losing it silently overwrites user-authored content
irreversibly. When the engine writes to the **skill** site:

- If the target skill's frontmatter carries **`provenance: user-authored`** (or any
  provenance marker the engine/distill did not write, or no marker on a pre-existing user
  skill), **NEVER overwrite its body** — propose a **sibling** skill or a **reference**
  append instead. **User-authored skills are inviolable.**
- Only **`provenance: distilled`** skills (machine-distilled) may be revised by the
  engine.
- A newly created skill carries **`provenance: distilled`** (a top-level frontmatter
  key, matching the gate above) — the marker that it was machine-authored and may later
  be revised.

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

## 6. Conflict check (target = the landfill site's current rules + native auto-memory)

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

Otherwise, before adding, read the **current contents of the chosen site** (not any private
catalogue — read-only `Bash`/`Grep` to scan the site's existing rules/skills) and check:

- **Duplicate**: if the site already states the same rule, strengthen that entry instead
  of adding a second (DRY).
- **Edit (explicit modification of an existing entry)**: if the request clearly targets one
  existing entry and asks to change it — "이 규칙 Pn을 이렇게 바꿔줘" / "update rule X to say
  Y" — treat it as an in-place edit of that entry, not a new append. Show the entry's
  **before → after** text in the §3 confirmation instead of new prose to add, so the user
  approves the exact rewrite. This is the first-class path for what used to only surface as
  a side effect of Duplicate (strengthen) or, worse, get misread as Contradiction and
  refused outright.
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target
  that rule as an explicit edit (it just disagrees, it doesn't ask to change the entry), do
  NOT write — report the contradiction to the user and stop.
- **Sibling**: if it is one half of an existing rule's pair, link them with a one-line
  "sibling to <that rule>" rather than duplicating context.

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

**Step 1 — list candidates** (read-only). Scope follows the chosen landfill site: a
machine-global site (`~/.claude/CLAUDE.md`, `~/.claude/rules`) is duplicated by a memory in
**any** project, so scan all of them; a **project-scoped** `CLAUDE.md` is only duplicated by
**that project's own** memory — another project's memory is neither a duplicate nor yours to
delete. Set `SCAN_ROOT` accordingly:

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

**Step 2 — read each candidate and judge.** Same Duplicate/Sibling/Contradiction/Edit call as
above, against the rule being landed. Most candidates will be unrelated; say so and move on.

- **Vanilla machine → silently skip.** No `~/.claude/projects` (or no `memory/` inside it) means
  the user has no auto-memory: skip the memory scan and proceed, exactly as §5 treats a missing
  `~/.claude/skills`. A missing directory is "nothing to conflict with", never a scan failure,
  and never a reason to stop the landfill write. Zero candidates is the same: not a failure.
- **But a scan that ERRORED is not a scan that found nothing.** The pipe fixes the exit code at
  `sort`'s, so a dead `awk` or an unreadable memory file shows up only on **stderr**. If
  anything is on stderr, the memory scan is **inconclusive** — say so in the §3 confirmation
  ("memory 스캔 실패 — 중복 여부 확인 못 했어요") instead of reporting `none`. A duplicate check
  must never fail in the direction of "no duplicates".
- **On a content-match hit → surface it in the §3 1-click confirmation** ("이 규칙이 memory에도
  있어요 — 매립 후 memory 항목은 지울게요"), and after the landfill write succeeds, remove that
  memory file **and its `MEMORY.md` index line — the line whose markdown link target is that
  file's basename** (never match on the title or the description text; those repeat), so the rule
  ends up in exactly one place. The removal rides on the same single confirmation — no second
  prompt. Use a recoverable delete (`trash-put` when available); if none is available, leave the
  file and report it for the user to remove — **never force-delete, never `rm`**.
- **Memory is an input, never a destination.** The landfill sites stay the **three** of §3 — a
  rule is never *written* to memory. A `feedback` memory is a promotion queue that empties into
  one of the three sites; this is a scan-scope extension, **not a fourth site**.

The engine does not maintain a numbered catalogue **of its own** (this claim is about the
engine's internal bookkeeping, not the target site's structure — the site it writes into may
itself use a numbered catalogue, e.g. the `policies/Pn.md` shape below); for a new rule it
appends in each site's **native form** (CLAUDE.md prose / a hook script / a skill SKILL.md),
and for an **Edit**-classified rule it rewrites the targeted entry in place instead — always
conflict-checked against that site's present content. If the chosen site's current content
is already an index+detail split (a thin summary table/list of one-liners each linking to a
per-entry file, e.g. a catalogue `README.md` → `policies/Pn.md`), match that shape — add one
terse index row plus its linked detail file, not a new inline block — so the always-loaded
index doesn't grow unbounded as entries accumulate. Never invent this split on a site that
doesn't already use it. When an **Edit** targets an entry that already lives in such a split,
rewrite **both** the index row's one-liner and its linked detail file whenever the change
touches anything the index summary claims, so the two don't drift apart.

## 7. Output contract

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

## 8. Post-write self-check (artifact verification)

After writing, verify the artifact deterministically and report any failure to the user
in Korean — never leave a malformed result behind. This is the **landfill-side artifact
verification** that moved here from distill's old Phase 5 (distill keeps only the
discovery-side placement-fit judgment). The check depends on the site:

- **skill site**: frontmatter parses and carries `name` / `description` / `allowed-tools`;
  `name` is kebab-case and matches the directory name; the body is non-empty (more than
  the frontmatter); a newly created skill carries a top-level `provenance: distilled` (this
  sub-clause is for a newly created skill only — when the write is an Edit of a pre-existing
  skill, provenance is already set, not newly stamped, so it doesn't apply there).
- **hook site**: the guard script is syntactically valid (`bash -n`) and the registration
  entry is well-formed JSON (a matcher plus a command array).
- **reminder site**: for a new rule, it was actually appended to the **routed channel** —
  CLAUDE.md for stance/voice, `~/.claude/rules` for a work-rule (or the CLAUDE.md fallback
  when the catalogue is absent) — a non-empty addition to that file. For an
  **Edit**-classified rule, verify the rewrite instead: the old entry text is gone and the
  approved new text is present — an edit isn't guaranteed to grow the file, so "non-empty
  addition" is not the right check here.
- **memory duplicate removal** (only when §6 found one): the duplicate memory file is gone and
  its `MEMORY.md` index line with it. If the delete could not run, report that in Korean — never
  claim a removal that didn't happen.

Example for a freshly written skill (best-effort, Korean report on failure):

```bash
SKILL_PATH="$HOME/.claude/skills/<name>/SKILL.md"
[ -s "$SKILL_PATH" ] && grep -q '^name:' "$SKILL_PATH" && grep -q '^description:' "$SKILL_PATH" \
  && grep -q '^allowed-tools:' "$SKILL_PATH" && grep -q '^provenance:' "$SKILL_PATH" \
  && echo "self-check OK" || echo "self-check FAILED — report to user in Korean"
```

A malformed write is reported and fixed, never left in place. This verification is an
in-skill self-check, never a registered harness hook (CON-2).

## Rules

- Classify, then place. Classification is user-confirmed (one 1-click step); placement is
  deterministic once classified.
- Three sites only: reminder (SOFT) / hook (HARD guard) / skill (procedure). The reminder
  *channel* is layer-routed — stance/voice → `~/.claude/CLAUDE.md`, work-rule →
  `~/.claude/rules` if present else CLAUDE.md fallback (never hardcode the machine's `rules/`
  structure). A user-shell receiver is out-of-band (not a fourth site) = command emission only.
- Tier (HARD/SOFT) is inferred by the engine from the rule's what/why, never asked of the
  user (the classification axes are never exposed as a form to fill).
- Native auto-memory is a **duplicate-scan target and a promotion queue, not a fourth site**:
  scan its `feedback` entries, land the rule in one of the three sites, then delete the memory
  duplicate — and skip the scan silently when the memory directory doesn't exist (§6).
- User-authored skills are **inviolable**: never overwrite a `provenance: user-authored`
  body; propose a sibling/reference instead.
- The default taxonomy is an editable starting point, not a hardcoded ontology; personal
  instances (address forms, a specific persona, a private catalogue) are zero.
- Never commit/push; leave changes in the working tree for the main context. Zero own
  harness hooks (CON-2).
