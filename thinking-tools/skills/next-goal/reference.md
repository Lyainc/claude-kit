# next-goal — detailed judgment rules

Split out of `SKILL.md` (#750) to keep the always-loaded body under the runtime prompt budget.
`SKILL.md` carries the imperative core and a compressed version of every rule below; read this
file when a judgment call needs the full rationale, not on every invocation.

## §1 — Step 0: why grouping happens before narrowing

A candidate may bundle several related follow-ups into one wider unit; it is not mechanically
the narrowest extractable piece. Decomposing too fine is the default failure mode, not too
coarse. This step is where that gets prevented — the scope check at the end of Phase 2 is only
a backstop for what slips through.

## §2 — Step 2: size test detail

Impact and size are separate axes and a candidate must clear both — a ten-minute verification
can be genuinely high-impact and still make a wasted session.

A session runs parallel subagents on independent pieces and can hand a self-contained thread to
another session entirely, so its capacity is several times what one linear context types.
**Worth several PRs is normal, not a warning sign.**

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

## §3 — Step 3: why grouping alone can't save a nits-only pool

Grouping alone cannot save a pool that holds only nits: a session that just polished one module
leaves that module's nits behind, so ranking them by ROI still returns a nit, and the chain
decays the longer it runs.

## §4 — Phase 2 four levers, full detail

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
  plugin rather than dropping the type back out of the condition. Additionally attach
  `${CLAUDE_PLUGIN_ROOT}/reference/seed-diff-grading.md` when the unit traces back to a
  build-spec Seed: that document specializes the same three states onto the Seed's
  `constraints[]` and `success_criteria[]`. Bound its rounds separately from L3's session-wide
  turn cap: only unresolved blocking/should-fix findings buy another round, nits get collected
  without spending one.
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

## §5 — Read the emitted sentence back, full rationale

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
