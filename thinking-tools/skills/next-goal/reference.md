# Next Goal Detailed Rules

Read this after `SKILL.md` and before Phase 1. It is the canonical ranking and condition-writing
procedure; `SKILL.md` retains the input and output contracts.

## Phase 1 — Pick (internal ranking, only the outcome is rendered)

### Step 0 — Group before you narrow

Cluster the follow-ups that share a file, module, theme, or epic. **Take the highest-ROI
*group*, not the highest-ROI single item.** A candidate may bundle several related follow-ups
into one wider unit; it is not mechanically the narrowest extractable piece.

Decomposing too fine is the default failure mode, not too coarse. This step is where that
gets prevented — the check at the end of Phase 2 is only a backstop for what slips through.

### Step 1 — Floor test

Ask it in the negative: **"if this were never done, what would actually be worse?"**

Asked positively ("is this high-ROI?") the question is self-satisfying and always answers yes.
"Nothing, it would just be tidier" is below the floor. Cleanup, wording, formatting, typos, and
nits from review comments on this session's own PR are almost always below it.

### Step 2 — Size test

**Does this fill a session?** Impact and size are separate axes and a candidate must clear both
— a ten-minute verification can be genuinely high-impact and still make a wasted session.

**Size it against a fanned-out session, not a lone context.** A session runs parallel subagents
on independent pieces and can hand a self-contained thread to another session entirely, so its
capacity is several times what one linear context types. The unit that fits is an epic, a
module's whole migration, a subsystem's related work — **worth several PRs is normal, not a
warning sign.** If one context would finish the candidate in a straight line without delegating
anything, it is below this bar: bundle, or go to step 3.

A candidate that passes the floor but not the size test is **not dropped and not taken alone**:
bundle it with the next-best items so the session lands one real dent instead of one errand.

**Bundle only what shares the candidate's file, module, theme, or epic.** An unrelated pairing
buys size at the cost of cohesion and then fails the scope check at the end of Phase 2. When
nothing related is in this session's pool, go to step 3 and bundle from the backlog — do not
widen it into an incoherent pair.

**Judgment-shaped candidates get narrowed here, not in Phase 2.** "Design X", "decide Y",
"investigate Z" clear both bars but have no observable end-state, so the condition cannot be
falsified in one tool call and Phase 2 would have to send them back. Narrow to the artifact the
judgment produces — a drafted file, a registered issue, a landed guard — or take the work that
consumes the design instead.

### Step 3 — Widen to the backlog

Fires when the candidate fails either bar, **or** when chain depth ≥ 3. Grouping alone cannot
save a pool that holds only nits: a session that just polished one module leaves that module's
nits behind, so ranking them by ROI still returns a nit, and the chain decays the longer it runs.

Rank the backlog by:
1. Issues that combine with what just shipped — context is hot, so doing it now is cheapest
2. Label and staleness priority

Take the wider unit. **Several backlog issues sharing one theme are one unit here** — a group of
four related issues is a better pick than the single highest-ranked one, and closing them
together is what the fanned-out capacity in step 2 is for.

### What Phase 1 renders

Three fields, nothing more. The ranking that produced them is never narrated.

```
NEXT      — the pick, in one line
POOL      — where it came from; on a switch, why the thread's own pool failed the floor
RUNNERS   — what lost, in one line
```

Emit all three on every run, not only on a switch. Direction stays the user's, and they cannot
overrule a choice they cannot see.

Follow-ups outside the chosen group are dropped here. This skill keeps no holding area for
in-flight decisions — anything that must survive becomes a clause inside Phase 2's sentence.

---

## Phase 2 — Condition (the paragraph)

Fold Phase 1's candidate into one natural-language paragraph that a goal evaluator can judge.

### What the evaluator can and cannot see

A `/goal` evaluator judges completion **from evidence surfaced in the conversation**. It does
not run commands or read files on its own. Every claim the condition rests on must therefore be
something a session would visibly produce.

### Shape it against four levers (internal only — never rendered as labels)

- **L1 — falsifiable in one tool call.** Fold verification into a single wrapper or a single
  exit code. If proving completion takes six commands, the loop slows and failure modes multiply.
- **L2 — an independent review gate inside the condition.** `evaluator_passed ≠ complete`. A
  model is the worst judge of its own output, so put a fresh-context review of the final diff
  into the condition itself — split by scope, not one call for both. Correctness, and
  CLAUDE.md/guard-script rule compliance, route to `/code-review high` (it already carries
  finder → per-finding verifier, and grades repo rules by running the guards itself, #728);
  requirement gaps route to a fresh-context subagent (native review does not know this session's
  Seed or requirements).
  Name that subagent's type: `subagent_type: "thinking-tools:requirement-gap-reviewer"`. The
  methodology lives in that agent's body — requirement sourcing, three-state verdicts
  (충족 / 미충족 / 산출물로 판단 불가), blocking/should-fix/nit severity, pre-existing defects held
  separate — so it arrives with the type, Seed or no Seed. Omit the type and the call falls
  through to `general-purpose`, which carries none of it and fails silently: a vanilla reviewer
  reports "no findings" too. Say "ignore style" for both calls, or the reviewer invents gaps and
  drives over-engineering. The agent is read-only by its own contract — no edits, no `git` state
  changes — and it does not pick its own scope either, so the condition must say that the
  delegation hands it the base ref or diff range (P3: the parent provides scope; a reviewer that
  resolves its own base grades something different on every run). Told no range, it stops.
  A `subagent_type` the harness does not know is refused outright — it never falls through to an
  untyped spawn — so on a machine whose installed thinking-tools predates the agent, update the
  plugin rather than dropping the type back out of the condition. Additionally attach `${CLAUDE_PLUGIN_ROOT}/reference/seed-diff-grading.md` when the unit
  traces back to a build-spec Seed: that document specializes the same three states onto the
  Seed's `constraints[]` and `success_criteria[]`. Bound its rounds separately from L3's
  session-wide turn cap: only unresolved blocking/should-fix findings buy another round, nits
  get collected without spending one.
- **L3 — a turn cap.** End with `or stop after N turns` so an unattended run cannot spin. Size N
  for the whole unit, not for one slice of it — a multi-PR unit that fans out needs room to
  finish, and a cap tuned to a single linear slice silently shrinks the work back down.
- **L4 — say the work fans out, and by which path.** When pieces are independent, the condition
  names that they run as parallel subagents (or hand off to another session), so the next session
  does not serialize by default. Independence is the test — anything sharing a file stays
  sequential. Name the path too, not just the fan-out: the main session's effort is one
  session-wide dial, so the delegation unit is the only place it can be set per branch. The
  `Agent` tool takes no effort parameter, which makes "이 갈래는 effort low로 서브에이전트에"
  unexecutable; what does execute is a Workflow `agent()` call (`opts.effort`), a named agent
  (its definition's `effort:` follows), a named skill (its `effort:` applies), or an
  argument-form command like `/code-review high`. Write the assignment as a default the next
  session may override — candidates are picked without opening the files, so a per-branch
  difficulty call is one session ahead of the evidence.

And the four elements: a single measurable end-state · the proof method · the invariant
constraints · the turn or time cap.

These inform what goes *into* the sentence. They never appear as labels, headers, or a
checklist in the output.

### Format mandate

Inside the fence: **`/goal ` plus one paragraph, nothing else.** No bold labels, no separate
fields, no `현재상태` / `참조` blocks. Plain prose, with the relevant issue, PR, and file
numbers woven in inline so the next session can follow those numbers to whatever background it
needs — self-contained from the paragraph alone. Convert relative dates to absolute where a
date matters.

**The line budget is one paragraph and it is spent.** Anything else worth carrying forward — a
constraint to respect, a pointer to a separate pass — goes *inside* the sentence as a clause,
never as an appended line. Appending a cold status block below the paragraph is the exact
failure of the handoff format this replaced.

### Read the emitted sentence back — check before emitting

The condition must **not** end at merged, "머지한다", or "머지하는 것으로 닫는다". Merge is an
irreversible step decided against information this paragraph does not have.

Do not write "PR을 연다" into it either — opening a PR is a judgment on what has accumulated by
then, and mandating it forces a half-unit PR.

If the goal is expected to close the unit, the most it may say is that the accumulated commits
are then ready to go up as one or more PRs (a unit this size usually splits into several) —
**and it must say the negative out loud in the same clause**
(`PR은 다음 세션이 판단하므로 이번엔 열지 않는다`). "Ready to go up as a PR" is not a
self-evident stop state: an evaluator reading it infers the PR is the deliverable and returns
not-complete on a run that did exactly what was asked. Naming the non-action makes the end state
falsifiable instead of inferable.

**Also check depth, not just breadth.** Re-read the condition's completion state: if it stays
satisfied (a) when every verdict comes back negative, or (b) when every branch ends shallow,
add one clause naming the depth every branch must clear regardless of outcome. A conditional
deliverable like "채택된 항목 수만큼 이슈" demands nothing by itself — six REJECTs and zero
issues still satisfies it.

**Read the emitted sentence back for merge vocabulary and depth before showing it.** Stating
these boundaries in prose alone has been observed to fail — the check has to be an actual pass
over the output.

### Scope check — mandatory, before emitting

Verify the condition is **one cohesive unit of related work, not the smallest fragment
mechanically extractable**. Cohesion is about theme, not size: several PRs under one epic pass,
while two unrelated errands bundled for bulk fail. Widen until the condition is one coherent
theme — do not merely note the risk, actually widen it.

Then check the floor from the other side: **could one context finish this in a straight line?**
If yes, it is too small — go back and add the related work you left out.

This sits upstream of commit atomicity and review-sized diffs, which still apply downstream
unchanged. It is the same policy as Phase 1 step 0; that is where the widening should already
have happened, and this is the backstop.

---
