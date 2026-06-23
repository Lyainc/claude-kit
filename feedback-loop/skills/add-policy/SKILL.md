---
name: add-policy
description: "The landfill engine of the ⑤ self-improvement loop: take ONE work-policy / convention / rule — stated by the user in natural language, or handed off as a distill proposal — infer its classification, and place it in one of three native landfill sites (a CLAUDE.md reminder, a deterministic hook guard, or an invocable skill) behind a single 1-click confirmation. Leaves every change in the working tree; never commits. Trigger: 이 규칙 추가, 이거 어디다 정리, 정책 분류, 규칙 매립, add policy, add-policy, classify this rule, where does this rule go, land this rule, /add-policy. Routing: distill (sibling) DISCOVERS what is worth keeping and emits the proposal; add-policy LANDS it — distill never fills the placement, add-policy never re-judges what to keep. Declarative knowledge (facts/decisions) = vault /capture·/note, not a policy. Example: '/add-policy' or '이 규칙 어디다 넣을지 분류해줘'."
model: inherit
allowed-tools: Read Edit Write Bash Glob Grep AskUserQuestion
---

**User language: Korean.** All user-facing output (the classification readout, AskUserQuestion prompts, confirmation messages, command suggestions) MUST be in Korean. Instructions below are English for LLM parsing.

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
  hook) or *something a human must be reminded of* (→ CLAUDE.md) is judged by the engine
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
  judgment/honesty rules usually live in a CLAUDE.md persona block, not a guard.
- **expression** — how you *say/phrase* things (tone, address, wording). Lives in a
  CLAUDE.md voice block.
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
| **CLAUDE.md** | an always-read reminder rule | **SOFT** (the model reads it and follows) | one prose line/paragraph appended | that CLAUDE.md's current rules |
| **hook** | deterministic auto-enforcement | **HARD** (a PreToolUse-style guard blocks) | a working guard script + a registration entry in the project/user `hooks` configuration Claude Code loads — emitted to the working tree only, never self-activated | existing hook matchers/scripts |
| **skill** | an invocable procedure | (n/a — a procedure, not a tier) | `~/.claude/skills/<name>/SKILL.md` | existing skills (patch > extend > new) |

**Tier folds into the site, so the user never picks an axis:**

- *layer* answers "what kind of rule" (internal reasoning),
- *tier* answers "auto-enforced or just reminded" → **HARD ⇒ hook, SOFT ⇒ CLAUDE.md**,
- the scope/channel question ("which CLAUDE.md? which config?") is the site choice itself.

**Layer → tier default (engine inference, reduces variance):** *judgment* and *expression*
are **always SOFT** (a CLAUDE.md reminder — they are not deterministically guardable). A
*work-rule* is **HARD (→ hook) iff its violation is deterministically detectable**, else
SOFT (→ CLAUDE.md): "leave deletes recoverable / never `rm`" is detectable → hook; "run
Python through the project runner" stated as a habit is a reminder → CLAUDE.md. This is the
engine's tier inference from what/why, never a user-supplied axis.

**1-click confirmation**: present the *decision*, not the grid. Show the user where it
will land, the exact text/diff that will be added, and one short line of why-here — then
ask a single confirmation:

```
## 분류 결과
- 규칙: <one-line summary>
- 들어갈 곳: <CLAUDE.md | hook | skill> — <one-line reason: HARD라 자동강제 / SOFT라 리마인드 / 절차라 호출형>
- 추가될 내용: <the exact prose / guard / skill stub>
- 충돌: <none | sibling of an existing rule | contradicts an existing rule (explain)>
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
`distill` retains for its discovery checks.

> **Migration note (old `metadata.provenance`)**: skills written by the *previous* distill
> carried a nested `metadata.provenance: distilled`, not a top-level key. The engine reads
> the top-level `provenance:` only, so such a skill falls into the "unknown marker →
> inviolable" branch — protected, but not engine-revisable. This is the **intended
> fail-safe** (safe > overwrite). To let the engine revise an old distilled skill, add a
> top-level `provenance: distilled` line to its frontmatter.

## 6. Conflict check (target = the landfill site's current rules)

Before adding, read the **current contents of the chosen site** (not any private
catalogue — read-only `Bash`/`Grep` to scan the site's existing rules/skills) and check:

- **Duplicate**: if the site already states the same rule, strengthen that entry instead
  of adding a second (DRY).
- **Contradiction**: if it conflicts with an existing rule, do NOT write — report the
  contradiction to the user and stop.
- **Sibling**: if it is one half of an existing rule's pair, link them with a one-line
  "sibling to <that rule>" rather than duplicating context.

The engine does not maintain a numbered catalogue; it appends in each site's **native
form** (CLAUDE.md prose / a hook script / a skill SKILL.md) and conflict-checks against
that site's present content.

## 7. Output contract

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
  the frontmatter); a newly created skill carries a top-level `provenance: distilled`.
- **hook site**: the guard script is syntactically valid (`bash -n`) and the registration
  entry is well-formed JSON (a matcher plus a command array).
- **CLAUDE.md site**: the rule was actually appended (a non-empty addition to the file).

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
- Three sites only: CLAUDE.md (SOFT reminder) / hook (HARD guard) / skill (procedure). A
  user-shell receiver is out-of-band (not a fourth site) = command emission only.
- Tier (HARD/SOFT) is inferred by the engine from the rule's what/why, never asked of the
  user (the classification axes are never exposed as a form to fill).
- User-authored skills are **inviolable**: never overwrite a `provenance: user-authored`
  body; propose a sibling/reference instead.
- The default taxonomy is an editable starting point, not a hardcoded ontology; personal
  instances (address forms, a specific persona, a private catalogue) are zero.
- Never commit/push; leave changes in the working tree for the main context. Zero own
  harness hooks (CON-2).
