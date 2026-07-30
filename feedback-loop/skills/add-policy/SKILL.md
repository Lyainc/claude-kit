---
name: add-policy
description: "The landfill engine of the ⑤ self-improvement loop: take ONE work-policy / convention / rule — stated by the user in natural language, or handed off as a distill proposal — infer its classification, and place it in one of three native landfill sites (an always-read reminder — CLAUDE.md for stance/voice or the ~/.claude/rules work-rule catalogue — a deterministic hook guard, or an invocable skill) behind a single 1-click confirmation. Leaves every change in the working tree; never commits. Trigger: 이 규칙 추가, 이거 어디다 정리, 정책 분류, 규칙 매립, add policy, add-policy, classify this rule, where does this rule go, land this rule, /add-policy. Routing: distill (sibling) DISCOVERS what is worth keeping and emits the proposal; add-policy LANDS it — distill never fills the placement, add-policy never re-judges what to keep. Declarative knowledge (facts/decisions) = vault /capture·/note, not a policy. Example: '/add-policy' or '이 규칙 어디다 넣을지 분류해줘'."
model: inherit
allowed-tools: Read Edit Write Bash Glob Grep AskUserQuestion
---

**User language: Korean for dialogue.** All user-facing DIALOGUE MUST be Korean. What the
engine WRITES is English for the `~/.claude/rules` catalogue, a hook script, and a skill body.
**`~/.claude/CLAUDE.md` is the exception** — the user's own stance/voice document: read it
first and write in the language it is already in. ([reference.md](reference.md) §0)

# add-policy — the landfill engine (layer ⑤)

`add-policy` is the **landfill half** of the recursive-improvement loop: it takes one
work-policy/rule, answers **"where does this go, and in what form?"**, and writes it there on a
single confirmation. Classification is a judgment and is user-confirmed; placement, once
classified, is deterministic. Its sibling `distill` is the **discovery half** — what is worth
keeping. The two never overlap.

## 1. Input contract — what the engine accepts

The engine takes a rule in **natural language**: a **user one-liner**, or a **distill proposal
object** carrying *what*, *why*, *session provenance*, and an *inviolability judgment*. It
**re-runs the classification itself** on either — a proposal never arrives with the placement
pre-filled, so **tier is inferred from what/why, never supplied**, and **the inviolability
judgment is enforced (§5), not re-made**. Why both follow: [reference.md](reference.md) §1.

## 2. Classification grid (default taxonomy — editable, replaceable)

**Layer** — internal reasoning, never an axis the user fills in, and an editable default rather
than a hardcoded ontology: **judgment** = what you *decide/assess* (→ the reminder site's
persona block); **expression** = how you *say/phrase* things (→ its voice block); **work-rule**
= how you *do the work*. Why this partition is reusable: [reference.md](reference.md) §2.

## 3. The three landfill sites (+ tier absorbed, 1-click UX)

There are exactly **three** native places a rule actually lands. Keeping the count small
is what makes classification reliable and keeps the engine portable.

| Site | What it is | Tier absorbed | Form | Conflict-check target |
|------|-----------|---------------|------|----------------------|
| **reminder**<br>(CLAUDE.md or `~/.claude/rules`) | an always-read rule; channel is **layer-determined** (below) | **SOFT** | one prose line appended to the layer's channel | that channel's current rules |
| **hook** | deterministic auto-enforcement | **HARD** (a guard blocks) | a guard script + a `hooks` registration entry, emitted to the working tree only, never self-activated | existing hook matchers/scripts |
| **skill** | an invocable procedure | (n/a) | `~/.claude/skills/<name>/SKILL.md` | existing skills (patch > extend > new) |

**Tier folds into the site, so the user never picks an axis**: *layer* is internal reasoning,
*tier* answers "auto-enforced or just reminded" (**HARD ⇒ hook, SOFT ⇒ reminder**), and the
scope/channel question is the site choice itself.

**Layer → tier default (engine inference):** *judgment* and *expression* are **always SOFT** —
not deterministically guardable. A *work-rule* is **HARD (→ hook) iff its violation is
deterministically detectable**, else SOFT (→ reminder). Examples: [reference.md](reference.md) §3-tier.

**SOFT reminder channel — routed by layer (one mapping, NOT a fourth site):** a SOFT rule
is a reminder, but *which* always-read file it lands in depends on its layer:

- **judgment / expression** (stance·voice — what you decide, how you phrase) → the
  top-level **`~/.claude/CLAUDE.md`** persona block.
- **work-rule** (how you do the work) → the machine **work-rule catalogue
  `~/.claude/rules`** *if it exists*; **otherwise fall back to `~/.claude/CLAUDE.md`**.

This routes the SOFT channel by the layer §2 already computed — no new site, no new axis. The
fallback is **non-negotiable: never hardcode the machine's `rules/` structure**. Detect it
(`[ -d "$HOME/.claude/rules" ]`) and degrade to CLAUDE.md where `~/.claude/rules` is absent —
a confident write into a non-existent catalogue is the breakage this guards against.

**Thin pointer + backing detail (catalogue channel):** machine-level reminders ride in *every*
session's context, so the always-on surface must stay thin. Two consequences:

- When a work-rule lands in `~/.claude/rules`, the catalogue holds the detail and
  `~/.claude/CLAUDE.md` gets at most a one-line pointer — none if the catalogue is already
  pointed at. Never paste full rule prose into the always-read CLAUDE.md.
- **Everything under `~/.claude/rules/` is loaded, not just its index.** An index+detail split
  only saves context if the **detail files live outside the loaded directory**. Follow the
  index's own links to find where they are and write the new one beside them; never add a
  second `.md` inside `~/.claude/rules/`. ([reference.md](reference.md) §3)

**1-click confirmation**: present the *decision*, not the grid — where it lands, the exact
text/diff to be added, one short line of why-here — then ask a single confirmation:

```
## 분류 결과
- 규칙: <one-line summary>
- 들어갈 곳: <CLAUDE.md | hook | skill> — <HARD라 자동강제 / SOFT라 리마인드 / 절차라 호출형>
- 추가/변경될 내용: <the exact prose/guard/skill stub, OR the entry's before → after if this is an edit>
- 충돌: <none | sibling of an existing rule | edits an existing entry (before→after) | contradicts an existing rule (explain)>
- memory 중복: <none | 이 규칙이 memory에도 있어요: <path...> — 매립 후 그 항목은 지울게요 (§6)>
```

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" **Never write without
confirmation.** If any axis cannot be settled, do NOT place it arbitrarily — hold the
classification and report what is ambiguous ("don't know" beats a confident-wrong placement).

## 4. User-shell receiver — the destination outside the three sites

A rule whose **receiver is the user's own shell** (an alias, an environment setting) has no
home among the three sites. Not a fourth site: **emit the command only** and never write the
user's shell files. **Receiver/audience match is a rule**: place a rule where its intended
audience actually reads it, and say so in the placement reasoning. ([reference.md](reference.md) §4)

## 5. Inviolability safety mechanism (the engine enforces it)

The *judgment* "skill X is user-authored" rides in the distill proposal; the **mechanism** that
prevents an overwrite is the engine's, and it is non-negotiable — losing it silently overwrites
user-authored content irreversibly. When the engine writes to the **skill** site:

- If the target skill's frontmatter carries **`provenance: user-authored`** (or any
  provenance marker the engine/distill did not write, or no marker on a pre-existing user
  skill), **NEVER overwrite its body** — propose a **sibling** skill or a **reference**
  append instead. **User-authored skills are inviolable.**
- Only **`provenance: distilled`** skills (machine-distilled) may be revised by the
  engine.
- A newly created skill carries a top-level **`provenance: distilled`** — machine-authored,
  engine-revisable later.

Verify before writing: read the target's frontmatter and confirm provenance, and **check
`[ -d "$HOME/.claude/skills" ]` first** — on a vanilla machine a glob against that missing
directory errors instead of matching nothing. Missing = "no existing skills", not a failure.

> **Migration note**: a skill carrying only the old nested `metadata.provenance: distilled`
> reads as an unknown marker and is therefore treated as **inviolable** — the intended
> fail-safe. Details: [reference.md](reference.md) §5.

## 6. Conflict check (target = the landfill site's current rules + native auto-memory)

**New site (no prior conflict possible)**: check whether the target file **exists** first —
`[ -f "$TARGET" ]`, the same existence-check principle §5 uses for the skill site. Never infer
"missing" from a read *error*: a read can fail for permissions or a transient tool fault, and
misdiagnosing that as "missing" skips the conflict check and **overwrites existing content**.
If the file genuinely isn't there yet, skip to writing and **create it (`Write`)** rather than
appending (`Edit`). If it exists but the read fails for another reason, stop and report —
do not guess. ([reference.md](reference.md) §6-new-site)

Otherwise, before adding, read the **current contents of the chosen site** (not any private
catalogue — read-only `Bash`/`Grep` to scan the site's existing rules/skills) and check.
**If the site is an index+detail split, follow the index's links and read the detail files
too** — they may sit outside the indexed directory (see §3), so scanning that directory alone
returns one-line summaries and silently downgrades the check to a title comparison:

- **Duplicate**: if the site already states the same rule, strengthen that entry instead
  of adding a second (DRY).
- **Edit (explicit modification of an existing entry)**: if the request clearly targets one
  existing entry and asks to change it — "이 규칙 Pn을 이렇게 바꿔줘" / "update rule X to say Y" —
  treat it as an in-place edit of that entry, not a new append. Show the entry's
  **before → after** text in the §3 confirmation instead of new prose to add, so the user
  approves the exact rewrite. It is its own outcome, not a variant of Duplicate.
- **Contradiction**: if it conflicts with an existing rule and the request does NOT target that
  rule as an explicit edit (it disagrees, it doesn't ask to change the entry), do NOT write —
  report the contradiction and stop.
- **Sibling**: if it is one half of an existing rule's pair, link them with a one-line
  "sibling to <that rule>" instead of duplicating context.

**The Duplicate scan also covers native auto-memory** — Claude Code's auto-memory
(`~/.claude/projects/<proj>/memory/*.md`) stores `feedback`-type entries, the same kind of
thing this engine lands, and nothing else ever cross-checks them against the reminder sites.
So scan **both** the chosen site's content **and** those `feedback` memories.

This is **two steps, and conflating them is a data-loss bug**: Step 1 only **lists candidate
files**; a *Duplicate* is decided in Step 2 by **reading each candidate and comparing its
content to the rule being landed**. Only a content match is a hit. A file that merely has
`type: feedback` is not a duplicate and is never touched. ([reference.md](reference.md) §6-memory)

**Step 1 — list candidates** (read-only). Scope follows the chosen landfill site: a
machine-global site (`~/.claude/CLAUDE.md`, `~/.claude/rules`) is duplicated by a memory in
**any** project, so scan all of them; a **project-scoped** `CLAUDE.md` is only duplicated by
**that project's own** memory — another project's memory is neither a duplicate nor yours to
delete. Set `SCAN_ROOT` accordingly:

```bash
# Machine-global site -> all projects. Project-scoped CLAUDE.md -> that project's dir only:
#   SCAN_ROOT="$HOME/.claude/projects/<current-project-dir>"
SCAN_ROOT="$HOME/.claude/projects"
# `find` not a glob (an unmatched `*/memory/*.md` aborts under zsh NOMATCH); `awk` not `grep`
# (the type must come from the FRONTMATTER, n==1, or a body mention matches, and line 1 must BE
# the opening `---`); trailing `$` or `type: feedback-loop` matches; `|| true` because a missing
# SCAN_ROOT is not a failure. NO `2>/dev/null` — stderr is the only channel left that can say
# the scan is incomplete. Details: [reference.md](reference.md) §6-snippet.
[ -d "$SCAN_ROOT" ] && find "$SCAN_ROOT" -path '*/memory/*.md' -not -name 'MEMORY.md' -exec awk '
  FNR==1 { n = ($0 ~ /^---[[:space:]]*$/) ? 0 : 9 }
  /^---[[:space:]]*$/ { n++ }
  n==1 && /^[[:space:]]*type:[[:space:]]*feedback[[:space:]]*$/ { print FILENAME }
' {} + | sort -u || true
```

**Memory is an input, never a destination.** A `feedback` memory is a promotion queue that
empties into one of the three sites of §3 — a scan-scope extension, **not a fourth site**.
A rule is never *written* to memory.

**Step 2 — read each candidate and judge.** Same Duplicate/Sibling/Contradiction/Edit call as
above, against the rule being landed. Most candidates will be unrelated; say so and move on.

- **Vanilla machine → silently skip.** No `~/.claude/projects` (or no `memory/` inside it) means
  the user has no auto-memory: skip the memory scan and proceed, exactly as §5 treats a missing
  `~/.claude/skills`. A missing directory is "nothing to conflict with", never a scan failure,
  and never a reason to stop the landfill write. Zero candidates is the same: not a failure.
- **But a scan that ERRORED is not a scan that found nothing.** A dead `awk` or an unreadable
  memory file shows up only on **stderr**. If anything is on stderr the memory scan is
  **inconclusive** — say so in the §3 confirmation ("memory 스캔 실패 — 중복 여부 확인 못 했어요")
  instead of reporting `none`. It must never fail in the direction of "no duplicates".
- **On a content-match hit → surface it in the §3 1-click confirmation** ("이 규칙이 memory에도
  있어요 — 매립 후 memory 항목은 지울게요"), and after the write succeeds remove that memory file
  **and its `MEMORY.md` index line — the line whose markdown link target is that
  file's basename** (never match on the title or the description text; those repeat), so the rule
  ends up in exactly one place. The removal rides on the same single confirmation — no second
  prompt. Use a recoverable delete (`trash-put` when available); if none is available, leave the
  file and report it for the user to remove — **never force-delete, never `rm`**.
For a new rule the engine appends in each site's **native form** (CLAUDE.md prose / a hook
script / a skill SKILL.md); for an **Edit**-classified rule it rewrites the targeted entry in
place instead — always conflict-checked against that site's present content. If the chosen
site's current content is already an index+detail split (a thin summary table/list of
one-liners each linking to a per-entry file, e.g. a catalogue `README.md` → `../policies/Pn.md`),
match that shape — add one terse index row plus its linked detail file, not a new inline block —
so the always-loaded index doesn't grow unbounded. **Put the new detail file wherever the
existing ones live, resolving the index's own link to find out**; dropping it inside the loaded
directory re-opens the leak the split exists to close. Never invent this split on a site that
doesn't already use it. When an **Edit** targets an entry in such a split, rewrite **both** the
index row's one-liner and its linked detail file whenever the change touches anything the index
summary claims, so the two don't drift apart.

## 7. Output contract

Every change is left **in the working tree** — no commit/push/PR, and a guard script's
`chmod +x` / activation / live test are the main context's job. **Zero own harness hooks
(CON-2)**: a hook written into the *user's* configuration is a landfill output, not a
harness hook. Close with one Korean line: "메인 컨텍스트가 검토 후 커밋하세요."
Written-content language and the hook registration fragment: [reference.md](reference.md) §7.

## 8. Post-write self-check (artifact verification)

After writing, verify the artifact deterministically and report any failure to the user
in Korean — never leave a malformed result behind. This is the **landfill-side artifact
verification** that moved here from distill's old Phase 5 (distill keeps only the
discovery-side placement-fit judgment). The check depends on the site:

- **skill site**: frontmatter parses and carries `name` / `description` / `allowed-tools`;
  `name` is kebab-case and matches the directory name; the body is non-empty (more than
  the frontmatter); a newly created skill carries a top-level `provenance: distilled`
  (new skills only — an Edit of a pre-existing skill already has provenance set).
- **hook site**: the guard script passes `bash -n` and the registration entry is well-formed
  JSON (a matcher plus a command array).
- **reminder site**: for a new rule, a non-empty addition landed in the **routed channel** —
  CLAUDE.md for stance/voice, `~/.claude/rules` for a work-rule (CLAUDE.md fallback when the
  catalogue is absent). For an **Edit**-classified rule, verify the rewrite instead: the old entry text is gone and
  the approved new text is present — an edit need not grow the file. On an index+detail split, also verify the **link
  resolves** (`[ -f ]` on the path the new index row points at) and that the loaded directory
  gained no new `.md` — a broken link or a leaked detail file are the two ways this split
  fails silently.
- **memory duplicate removal** (only when §6 found one): the duplicate memory file is gone and
  its `MEMORY.md` index line with it. If the delete could not run, say so in Korean — never
  claim a removal that didn't happen.

A worked `bash` example of the skill-site check is in [reference.md](reference.md) §8.

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
