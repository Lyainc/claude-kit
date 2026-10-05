---
name: add-policy
description: "Classify and land one user-confirmed reusable work policy as an always-read reminder, deterministic hook, or invocable skill; leaves changes uncommitted. Trigger: 이 규칙 추가, 이거 어디다 정리, 정책 분류, 규칙 매립, add policy, add-policy, classify this rule, where does this rule go, land this rule, /add-policy. Routing: use distill to discover a proposal; add-policy does not re-judge reuse value; use vault-save for declarative facts."
model: inherit
allowed-tools: Read Edit Write Bash Grep AskUserQuestion
---

**User language: Korean for dialogue.** Artifact language: reference.md §0 (binding).

## Codex Portability

On Codex, read [the portability contract](../../reference/codex-portability.md)
first. Set `CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"`; never read or write `~/.claude`. Inspect each
target and its parent first; create a missing one only after the existing one-click confirmation,
and stop unmodified if unreadable or conflicting.

- SOFT reminder: inspect `$CODEX_ROOT/AGENTS.md` and its declared source/catalogue. A work-rule
  updates the existing shared catalogue entry when available (global file stays a thin pointer, no
  duplicate rule prose); other reminders edit the declared managed source plus its installed copy
  in the same exact-diff approval. Preserve symlinks; unclear ownership or sync: stop; edit an
  unmanaged file only with no catalogue.
- Procedure: only `$HOME/.agents/skills/<name>/SKILL.md` (§5).
- Hook: a script plus a merged `$CODEX_ROOT/hooks.json` definition, never replacing existing hooks
  (read `codex.md`, this site only). Hook trust is separate; never silently grant trust.

Codex memory is not writable: skip §6's memory promotion/deletion. Claude Code ignores this
section.

# add-policy

## 1. Input contract

A user one-liner or a distill proposal object (what, why, provenance, inviolability
judgment): re-classify it; enforce (§5), do not re-make, the judgment.

**Source gate — the third input.** A candidate may be
inferred by the agent. Route by provenance: a distill proposal proceeds (never bounced back to the
skill that sent it). Everything else, including anything that reads like a user one-liner, asks:
can you point at the user's own utterance stating this rule in the transcript? Yes: proceed. No:
hand it to `/distill` (bouncing is not re-judging: it routes to the judge), before
classification and the §6 conflict check.

## 2. Classification grid

Internal layer: judgment (decide), expression (say), work-rule (do).

## 3. The three landfill sites

- **reminder** (CLAUDE.md or `~/.claude/rules`): always-read, SOFT, one prose line.
- **hook**: deterministic, HARD; guard script + `hooks` entry, working tree only, never
  self-activated. Blocking = PreToolUse + `permissionDecision: "deny"`; recovery = PostToolUse +
  `exit 2`, reports only.
- **skill**: `~/.claude/skills/<name>/SKILL.md`.

Tier folds into the site (HARD ⇒ hook, SOFT ⇒ reminder), inferred per reference §3-tier, never
asked; HARD means "deterministically enforced", not "a guard blocks".

SOFT channel by layer (not a fourth site): judgment/expression → `~/.claude/CLAUDE.md`; work-rule →
`~/.claude/rules` if it exists, else fall back to CLAUDE.md. Never hardcode the machine's `rules/`
structure: detect it (`[ -d "$HOME/.claude/rules" ]`). Catalogue: a thin pointer in CLAUDE.md at
most (none if it already points there), never full rule prose; `~/.claude/rules/` is loaded whole,
so never add a second `.md` there.

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

Then AskUserQuestion (Korean): "여기에 이렇게 넣을게요 — 맞아요?" If 필요성 is 기존 항목으로 충분 /
안 넣는 게 나음 or 은퇴 is 미발동, first read reference §3-gate-question (binding): the
recommendation is the first option, never a generic refusal; 미발동 is a three-way pick, not
yes/no. Never write without confirmation; hold an unsettled axis.

## 4. User-shell receiver

A rule for the user's own shell (alias, env) is not a fourth site: emit the command only, never
write the user's shell files; place a rule where its audience reads it (reference §4).

## 5. Inviolability safety mechanism

On the skill site, a target with `provenance: user-authored` (or a marker the engine did not write,
or none on a pre-existing user skill) is NEVER overwritten: propose a sibling skill or a reference
append. Only `provenance: distilled` skills may be revised; a new skill carries it. Provenance
inspection: reference §5 (binding).

## 6. Conflict check

New site: check the target exists first (`[ -f "$TARGET" ]`); a read *error* is not "missing" (it
overwrites existing content): absent → `Write`, unreadable → stop and report.
Otherwise read the site's current rules, hook matchers and guard scripts, or skills (read-only
`Bash`/`Grep`), following an index+detail split's links to its detail files (§3):

- **Duplicate**: the site already states the rule → strengthen that entry, no second one.
- **Edit (explicit modification of an existing entry)**: edit in place, showing before → after in
  the §3 confirmation.
- **Supersede (the catalogue's exit path)**: a rule that makes an existing entry redundant absorbs
  it and retires it in the same write, on the same confirmation, never a separate prompt. Read
  reference §6-supersede-contract and apply it as written; this bullet is a locator, not the
  contract.
- **Unused retirement (#609)**: only when the user says outright the entry never came up (never
  silence); recommends only, never `rm`. Read reference §6-unused-contract and apply it as written.
- **Contradiction**: conflicts with an existing rule and the request does NOT target it as an
  explicit edit → do NOT write; report and stop.
- **Sibling**: pair of an existing rule → link "sibling to <rule>".

**The Duplicate scan also covers native auto-memory**: read reference §6-memory-contract and apply it as written, then read
§6-snippet and run the command it ships.

**Necessity gate — runs here, after the conflict check and before the §3 confirmation.**
Recommends only and weighs the artifact's cost, never the rule's reuse value (distill's). Read
reference §6-gate-contract and apply it as written.

On an index+detail split, match that shape: one index row plus its linked detail file, not a
new inline block; never invent this split on a site that doesn't already use it. An Edit rewrites
both row and detail file. Read reference §6-shape-contract and apply it as written.

## 7. Output contract

Leave every change in the working tree (no commit/push/PR; a guard's `chmod +x`, activation and
live test are the main context's). Zero own harness hooks (CON-2). Details: reference §7. Close
in Korean: "메인 컨텍스트가 검토 후 커밋하세요."

## 8. Post-write self-check

After writing, read reference §8 and run its checklist for the site written; report a malformed
write in Korean and fix it; never claim a write or removal that didn't happen.

## Rules

- Classify, then place: user-confirmed classification, deterministic placement.
- Source gate first (§1): an agent-inferred candidate is bounced to `/distill`, never landed.
- The default taxonomy is editable, not a hardcoded ontology; personal instances are zero.
