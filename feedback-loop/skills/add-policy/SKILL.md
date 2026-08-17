---
name: add-policy
description: "The landfill engine of the ⑤ self-improvement loop: take ONE work-policy / convention / rule — stated by the user in natural language, or handed off as a distill proposal — infer its classification, and place it in one of three native landfill sites (an always-read reminder, a deterministic hook — blocking or recovery, or an invocable skill) behind a single 1-click confirmation. Leaves every change in the working tree; never commits. Trigger: 이 규칙 추가, 이거 어디다 정리, 정책 분류, 규칙 매립, add policy, add-policy, classify this rule, where does this rule go, land this rule, /add-policy. Routing: distill (sibling) DISCOVERS what is worth keeping and emits the proposal; add-policy LANDS it — distill never fills the placement, add-policy never re-judges the rule's reuse value (it does judge whether the artifact is needed — the §6 gate). Declarative knowledge (facts/decisions) = vault /vault-save, not a policy. Example: '/add-policy' or '이 규칙 어디다 넣을지 분류해줘'."
model: inherit
allowed-tools: Read Edit Write Bash Grep AskUserQuestion
effort: medium
---

**User language: Korean for dialogue.** What the engine WRITES is English — the
`~/.claude/rules` catalogue, a hook script, a skill body. **`~/.claude/CLAUDE.md` is the
exception**: the user's own stance/voice document, so read it first and write in its language.
([reference.md](reference.md) §0)

# add-policy — the landfill engine (layer ⑤)

`add-policy` is the **landfill half** of the recursive-improvement loop: it answers **"where
does this rule go, and in what form?"** and writes it there on a single confirmation. Its
sibling `distill` is the **discovery half**; the boundary between them is §6's necessity gate.

## 1. Input contract — what the engine accepts

The engine takes a rule in **natural language**: a **user one-liner**, or a **distill proposal
object** carrying *what*, *why*, *session provenance*, and an *inviolability judgment*. It
**re-runs the classification itself** on either — a proposal never arrives with the placement
pre-filled, so tier is inferred and **the inviolability judgment is enforced (§5), not
re-made**. ([reference.md](reference.md) §1)

**Source gate — the third input, and the one that must not land unjudged.** A candidate also
arrives **inferred by the agent**, which the two accepted kinds' free pass does not cover. Route
by **provenance**: a **distill proposal proceeds** — distill already judged it, and a proposal is
never bounced back to the skill that sent it. **Everything else, including anything that reads
like a user one-liner**, asks one question: **can you point at the user's own utterance stating
this rule in the transcript?** Yes → proceed. No → it is agent-inferred: **hand it to
`/distill`** — bouncing is not re-judging, it sends the candidate to the judge. Run it **before**
classification and the §6 conflict check, so a bounce wastes neither.
([reference.md](reference.md) §1-source)

## 2. Classification grid (default taxonomy — editable, replaceable)

**Layer** — internal reasoning, never a user-filled axis, an editable default not a hardcoded
ontology: **judgment** = what you *decide/assess* (→ the reminder site's persona block);
**expression** = how you *say/phrase* (→ its voice block); **work-rule** = how you *do the
work*. Why this partition is reusable: [reference.md](reference.md) §2.

## 3. The three landfill sites (+ tier absorbed, 1-click UX)

There are exactly **three** native places a rule lands (the small count keeps classification
reliable and the engine portable):

- **reminder** (CLAUDE.md or `~/.claude/rules`) — an always-read rule, **SOFT**: one prose line
  appended to the layer's channel, **layer-determined** (below).
- **hook** — deterministic auto-enforcement, **HARD**: a guard script + a `hooks` registration
  entry, working tree only, never self-activated. **Two forms** (#609), by *when* the violation
  becomes visible: **blocking** = PreToolUse + `hookSpecificOutput.permissionDecision: "deny"`;
  **recovery** = PostToolUse + `exit 2`, stderr back to Claude — reports only
  (PostToolUse carries neither `permissionDecision` nor `updatedInput`).
- **skill** — an invocable procedure: `~/.claude/skills/<name>/SKILL.md` (patch > extend > new).

**Tier folds into the site, so the user never picks an axis** (**HARD ⇒ hook, SOFT ⇒
reminder**); the hook's *form* folds the same way, never a second axis — **HARD means
"deterministically enforced", not "a guard blocks"** (#609), since recovery auto-fires like
blocking but cannot undo. The scope/channel question is the site choice itself.

**Layer → tier default (engine inference):** *judgment* and *expression* are **always SOFT**
(not deterministically guardable); a *work-rule* is **HARD (→ hook) iff its violation is
deterministically detectable**, else SOFT — detectable **before** the act → blocking, only
**after** (from what the act leaves behind) → recovery. Examples: [reference.md](reference.md)
§3-tier.

**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):** *judgment /
expression* (stance·voice) → the top-level **`~/.claude/CLAUDE.md`** persona block; *work-rule*
→ the machine **work-rule catalogue `~/.claude/rules`** *if it exists*, **otherwise fall back to
`~/.claude/CLAUDE.md`**. It routes by the layer §2 already computed — no new site, no new axis.
The fallback is **non-negotiable: never hardcode the machine's `rules/` structure**: detect it
(`[ -d "$HOME/.claude/rules" ]`) and degrade to CLAUDE.md where it is absent. Per-site
conflict target, and why the fallback is non-negotiable: [reference.md](reference.md) §3-sites.

**Thin pointer + backing detail (catalogue channel):** machine-level reminders ride in *every*
session, so the catalogue holds the detail and `~/.claude/CLAUDE.md` gets at most a one-line
pointer — none if it already points at the catalogue, never full rule prose. And **everything
under `~/.claude/rules/` is loaded, not just its index**, so write the new detail file where the
index's own links point, outside that directory; never add a second `.md` there. (Measured leak:
[reference.md](reference.md) §3)

**1-click confirmation**: present the *decision*, not the grid — where it lands, the exact
text/diff, one line of why-here — then one confirmation:

```
## 분류 결과
- 규칙: <one-line summary>
- 들어갈 곳: <CLAUDE.md | hook | skill> — <HARD라 자동강제 / SOFT라 리마인드 / 절차라 호출형>
- 추가/변경될 내용: <exact prose/guard/skill stub, or the entry's before → after on an Edit>
- 충돌: <none | sibling | edits an existing entry (before→after) | contradicts an existing rule (explain)>
- 필요성: <통과 | 기존 항목으로 충분 | 안 넣는 게 나음 — <이유 한 줄>>
- 은퇴: <none | Pn 흡수 — 같은 쓰기에서 은퇴 | Pn 미발동 — 삭제 / 조건 좁히기?>
- memory 중복: <none | memory에도 있어요: <path...> — 매립 후 그 항목은 지울게요 (§6)>
```

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" — with two exceptions. 필요성 not
통과, and then the gate's recommendation is the first option and the question carries **that**
recommendation, never a generic refusal: 기존 항목으로 충분 asks about folding it into that
entry, 안 넣는 게 나음 asks whether to land it at all. And 은퇴 = 미발동, a three-way pick rather
than a yes/no (#609). Wordings: [reference.md](reference.md) §3-gate-question. **Never write without confirmation.** If any axis
cannot be settled, hold the classification and report what is ambiguous instead of placing it
arbitrarily ("don't know" beats a confident-wrong placement).

## 4. User-shell receiver — the destination outside the three sites

A rule whose **receiver is the user's own shell** (an alias, an env setting) has no home among
the three sites. Not a fourth site: **emit the command only**, never write the user's shell
files. **Receiver/audience match is a rule**: place a rule where its audience reads it, and say
so in the placement reasoning. ([reference.md](reference.md) §4)

## 5. Inviolability safety mechanism (the engine enforces it)

The *judgment* "skill X is user-authored" rides in the distill proposal; the **mechanism**
preventing an overwrite is the engine's and is non-negotiable (losing it overwrites
user-authored content irreversibly). When the engine writes to the **skill** site:

- If the target's frontmatter carries **`provenance: user-authored`** — or any marker the
  engine/distill did not write, or none at all on a pre-existing user skill — **NEVER overwrite
  its body**: propose a **sibling** skill or a **reference** append. **User-authored skills are
  inviolable.**
- Only **`provenance: distilled`** skills may be revised; a newly created skill carries a
  top-level **`provenance: distilled`** — machine-authored, revisable later.

Verify before writing: read the target's frontmatter and confirm provenance, and **check
`[ -d "$HOME/.claude/skills" ]` first** — a glob against that missing directory errors instead
of matching nothing. Missing = "no existing skills", not a failure. (An old nested
`metadata.provenance: distilled` reads as an unknown marker, so it stays inviolable — the
intended fail-safe: [reference.md](reference.md) §5.)

## 6. Conflict check (target = the landfill site's current rules + native auto-memory)

**New site**: check the target **exists** first (`[ -f "$TARGET" ]`, as §5 does for the skill
site). Never infer "missing" from a read *error* — that **overwrites existing content**. Absent
→ **`Write`**, not append; exists but unreadable → stop and report.
([reference.md](reference.md) §6-new-site)

Otherwise read the **current contents of the chosen site** first (read-only `Bash`/`Grep`):
that channel's own rules, or the existing hook matchers and guard scripts (so a new guard
doesn't fire on an event one already covers), or existing skills.
**If the site is an index+detail split, follow the index's links and read the detail files
too** — they may sit outside the indexed directory (§3), and scanning that directory alone
downgrades the check to a title comparison:

- **Duplicate**: if the site already states the same rule, strengthen that entry rather than
  adding a second (DRY).
- **Edit (explicit modification of an existing entry)**: if the request clearly targets one
  existing entry and asks to change it ("update rule X to say Y"), treat it as an in-place edit,
  not a new append: show that entry's **before → after** in the §3 confirmation instead of new
  prose, so the user approves the exact rewrite. Its own outcome, not a variant of Duplicate.
- **Supersede (the catalogue's exit path)**: a rule that makes an existing entry redundant
  absorbs it and retires it in the **same write**, on the same confirmation — never a separate
  prompt. **Its canonical, binding text is [reference.md](reference.md) §6-supersede-contract —
  read that section and apply it as written; this bullet is a locator, not the contract.**
  Rationale: [reference.md](reference.md) §6-supersede.
- **Unused retirement (the other exit, #609)**: absorption above is otherwise the only way an
  entry ever leaves. Positive evidence only — the **user says outright the entry never came
  up**, never silence. **Reminder-site entries only, never a user-authored skill** (§5).
  Surfaces in the §3 은퇴 field with **two choices — delete it, or
  narrow its firing condition to what it was written for**: **recommends only**,
  no second prompt (§3 carries the pick), no answer means keep, `trash-put` never `rm`.
  ([reference.md](reference.md) §6-unused)
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target that
  rule as an explicit edit, do NOT write — report the contradiction and stop.
- **Sibling**: if it is one half of an existing rule's pair, link them with a one-line
  "sibling to <that rule>", not duplicated context.

**The Duplicate scan also covers native auto-memory** (`~/.claude/projects/<proj>/memory/*.md`
`feedback` entries), in two steps whose conflation is a data-loss bug. **Its canonical, binding
text is [reference.md](reference.md) §6-memory-contract: Read that section and apply it as
written, then read §6-snippet and run the command it ships — this paragraph is a locator, not
the contract.** Memory is an input queue that empties into a §3 site — **never a fourth site**,
never a write destination. Why two steps: [reference.md](reference.md) §6-memory.

**Necessity gate — runs here, after the conflict check and before the §3 confirmation.** Four
questions, three outcomes; it **recommends only** and weighs the artifact's cost, never the
rule's **reuse value** (distill's). **Its canonical, binding text is
[reference.md](reference.md) §6-gate-contract — read that section and apply it as written; this
line is a locator, not the contract.** Why it exists: [reference.md](reference.md) §6-gate.

For a new rule the engine appends in each site's **native form** (CLAUDE.md prose / a hook
script / a skill SKILL.md); an **Edit** rewrites the targeted entry in place. If the site's
content is already an index+detail split (one-line index rows linking to per-entry files, e.g.
`README.md` → `../policies/Pn.md`), match that shape — one terse index row plus its linked
detail file, not a new inline block — and **put the detail file where the existing ones live,
resolving the index's own link to find out**. Never invent this split on a site that doesn't
already use it. An **Edit** there rewrites **both** the index row and its detail file whenever
the change touches what the index claims.

## 7. Output contract

Every change is left **in the working tree** — no commit/push/PR; a guard script's `chmod +x`,
activation and live test are the main context's job. **Zero own harness hooks (CON-2)**: a hook
written into the *user's* config is a landfill output, not a harness hook. Close in Korean:
"메인 컨텍스트가 검토 후 커밋하세요." Written-content language and the hook registration
fragment: [reference.md](reference.md) §7.

## 8. Post-write self-check (artifact verification)

After writing, verify the artifact deterministically; a malformed write is **reported in Korean
and fixed**, never left in place, and you **never claim a write or a removal that didn't happen**.
*What* gets checked depends on the site, so **read [reference.md](reference.md) §8 and run its
checklist** for the site just written (skill / hook / reminder, plus the Edit, retirement and
memory-duplicate-removal cases). Reporting "done" without running it is the failure this step
exists to prevent. An in-skill self-check, never a registered harness hook (CON-2).

## Rules

- Classify, then place: classification is user-confirmed (one 1-click step), placement
  deterministic once classified.
- Source gate first (§1): a candidate the AGENT inferred — no user utterance to point at in
  the transcript — is bounced to `/distill` before classification, never landed. The engine
  still never re-judges what to keep; it routes the unjudged to the judge.
- Three sites only: reminder (SOFT) / hook (HARD — blocking or recovery, #609) / skill
  (procedure). The reminder *channel* is layer-routed — stance/voice → `~/.claude/CLAUDE.md`,
  work-rule → `~/.claude/rules` if present else CLAUDE.md fallback (never hardcode the machine's
  `rules/` structure). A user-shell receiver is command emission only, not a fourth site.
- Tier (HARD/SOFT) is inferred from the rule's what/why, never asked of the user; so is the
  hook's form (blocking vs recovery).
- The **necessity gate** (four questions, three outcomes, and one occurrence → narrow the
  condition, no counter) and both **retirements** (§6 Supersede / never-fired) ride the one
  confirmation — no second prompt. The gate **recommends only** and never blocks a landing;
  it judges the artifact's cost, never reuse value. A retired number is never reused.
- Native auto-memory is a **duplicate-scan target and a promotion queue, not a fourth site**:
  scan its `feedback` entries, land the rule in a §3 site, then delete the memory duplicate;
  skip the scan silently when that directory doesn't exist (§6).
- User-authored skills are **inviolable**: never overwrite a `provenance: user-authored` body;
  propose a sibling/reference instead.
- The default taxonomy is editable, not a hardcoded ontology; personal instances are zero.
- Never commit/push; leave changes in the working tree. Zero own harness hooks (CON-2).
