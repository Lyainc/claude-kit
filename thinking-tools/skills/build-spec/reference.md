# Build Spec — Reference

## 1. Ambiguity Scoring Rubric (A1 — Y/N Checklist)

For each dimension, evaluate after receiving the user's answer. Mark Y/N and write a one-line rationale for each item. clarity = Y_count / total_questions.

### Goal Clarity (4 questions)

| # | Question | Y if... |
|---|----------|---------|
| G1 | 단일 문장으로 목표를 표현할 수 있나? | Goal can be stated in one sentence without "and/or" ambiguity |
| G2 | 목표가 측정 가능하거나 관찰 가능한가? | User described a state that can be verified as achieved |
| G3 | 목표의 주요 수혜자(사용자/시스템)가 명확한가? | At least one clear beneficiary identified |
| G4 | "왜"를 설명할 수 있나 (동기 이해 가능)? | Underlying motivation stated or inferable |

### Constraint Clarity (3 questions)

| # | Question | Y if... |
|---|----------|---------|
| C1 | 최소 1개의 hard constraint가 명시됐나? | At least one non-negotiable limit stated (tech stack, deadline, budget, legal) |
| C2 | hard / soft constraint 구분이 가능한가? | User decided hard vs soft for each major constraint — "all hard" counts when the user made that call. N only when hard/soft was never raised or the answers do not show it |
| C3 | 제약의 근거를 이해할 수 있나? | Reason for each major constraint is stated or inferable |

### Success Criteria (4 questions)

| # | Question | Y if... |
|---|----------|---------|
| S1 | 최소 1개의 verifiable acceptance criterion이 있나? | At least one criterion with observable outcome |
| S2 | "성공"의 범위가 명확한가 (what is in/out)? | Clear boundary between success and partial success |
| S3 | 성공 기준이 목표와 직접 연결되나? | Criteria would actually validate the goal |
| S4 | 측정 방법 또는 관찰 방법이 제시됐나? | How to check if criterion is met is inferable |

### Context Clarity (3 questions, brownfield only)

| # | Question | Y if... |
|---|----------|---------|
| X1 | 기존 스택/시스템과의 통합 포인트가 파악됐나? | Integration surface described (API, database, module) |
| X2 | 기존 코드의 어느 부분에 영향을 주는지 알 수 있나? | Affected components or files identified |
| X3 | 기존 의존성·제약과 새 기능의 충돌 가능성 검토됐나? | Potential conflicts acknowledged or ruled out **against both the code and the open-issue backlog** (SKILL.md Phase 0 backlog scan). Backlog unavailable → code alone is enough for Y |

---

## 2. Scoring Calibration Notes

- Never assign 0.0 (no answer means unknown, not impossible) or 1.0 (always some residual ambiguity).
- Floor values are hard gates — even if overall Ambiguity ≤ 0.20, a dimension below its floor blocks the gate.
- The isolated gate judge (SKILL.md Phase 2) therefore returns **per-dimension clarity**, never one Ambiguity number. Collapsing the verdict to a single weighted sum deletes the floors without anyone noticing: brownfield Goal 0.9 / Constraint 0.9 / Success 0.9 / Context 0.5 gives Ambiguity 0.16 — under the 0.20 threshold — while Context sits below its 0.60 floor. The floors exist precisely because the sum can be bought with the dimensions that were easy to answer.
- **Why the verdict is isolated at all** (#433): the interviewer asking, scoring, and then declaring its own gate open is a 1-in-3-roles loop — the same self-verification bias `adversarial-review` removes by spawning its Judge as a separate `Agent` subagent, and `unknown-discovery` removes for Depth scoring. So the verdict that actually opens the gate comes from a subagent, not from this context. When the isolated verdict does not arrive — the subagent call fails, is blocked, or stays alive without ever returning one — SKILL.md Phase 2 announces the fallback instead of absorbing it silently: a self-scored gate and an isolated one carry different confidence, and rendering them identically would hide exactly that difference from the user. The announce line and `scoring_isolated: false` cover every one of those routes, because what they report is "this verdict was not isolated", not why.
- **A policy-blocked `Agent` call is the same condition, not a separate one** (#433 remaining scope): a session-level policy that denies `Agent` calls (e.g. "no subagent spawns unless requested") stops the isolated call exactly like a timeout or an unavailable subagent does, so it takes the same fallback — inline score, one-line announce, `scoring_isolated: false`. It does **not** additionally trigger an `AskUserQuestion` approval prompt. Reasons: (1) a policy denial has already routed through the harness's own permission gate (or a hard deny rule) before the call fails — asking the user again re-confirms a decision that gate already recorded; (2) under unattended execution the question would get no answer and default to the lower-risk branch anyway (`P6`), which is exactly "continue inline, announce" — so the prompt changes nothing except adding friction; (3) `#430` already caps interview length, and a meta-question is still an extra round the user has to clear.
- **A live-but-silent subagent is the same condition too** (#647): a spawned subagent that stays alive and emits only idle notifications, returning no final text, never errors and never times out — so it matches neither "call fails" nor "policy blocks it", and the gate would simply wait. Measured once (2026-08-15: three subagents, no report, `SendMessage` re-requests also unanswered, ~7 minutes lost before a human noticed). The rule is therefore stated, not detected: a subagent that returns only idle notifications and no final text after one re-request counts as unavailable and takes this same fallback — inline score, one-line announce, `scoring_isolated: false`. One re-request, not a polling loop: a single observation does not justify a detection mechanism, and the re-request is what distinguishes "silent" from "still working".
- **`scoring_isolated` is not folded into the Gate Check ✓/✗ line**: the fallback announce line already prints immediately before that block whenever `scoring_isolated: false`, so the confidence drop is already visible at the exact moment it matters. The ✓/✗ row is scoped to "which dimension is short of its floor" (line above, "shows *which* dimensions still fall short"); mixing a confidence flag into it would answer two different questions in one line and make both harder to read.
- For "빠르게" (quick) mode: evaluate G1-G4 only; gate = Goal ≥ 0.75 (skip other dimensions).
- If user provides a very detailed answer covering multiple dimensions at once: score all relevant dimensions simultaneously.

---

**Why only the gate-opening round is isolated, and why the judge sees no scores.** Every other round
stays inline: cheap by default, the expensive call only where it changes an outcome. The judge gets
the transcript and checklist alone, because a judge shown the score it is meant to check is not
isolated.

**Why the Gate Check shows ✓/✗, not numbers.** The per-dimension mark is the user-facing progress
signal: it shows which dimensions still fall short without exposing the underlying numeric scores.

## 3. Brownfield Repo Files Detection List

In order of precedence for context injection:

1. `README.md` — project overview, purpose
2. `CLAUDE.md` or `AGENTS.md` — AI operating context (high signal)
3. `plugin.json` or `package.json` — name, version, description, keywords
4. `pyproject.toml` — Python project metadata
5. `requirements.txt` — dependency signal
6. `Cargo.toml` — Rust project
7. `go.mod` — Go project

Extract: project name, description, key dependencies, notable constraints.
Inject as Phase 1 context prefix: "현재 프로젝트: {name} — {description}. 주요 의존성: {deps}."

---

## 4. Dimension Weight Table

| Dimension | Greenfield | Brownfield | Floor |
|-----------|-----------|-----------|-------|
| Goal | 0.40 | 0.34 | 0.75 |
| Constraint | 0.30 | 0.26 | 0.65 |
| Success | 0.30 | 0.25 | 0.70 |
| Context | — | 0.15 | 0.60 |

Brownfield weights sum to 1.00: 0.34 + 0.26 + 0.25 + 0.15 = 1.00.

---

## 5. Backlog Scan — why closed issues, and why the skip must be loud (#489)

**Closed issues are the higher-risk half.** X3 (conflicts) asks whether the spec collides with a
decision already made. A decision that has been *made* is normally a **closed** issue — closed as
COMPLETED means "this is settled, do not go the other way". The open backlog holds what is still
undecided, which is the weaker signal of the two. So a scan restricted to `--state open` misses
precisely the class it exists to catch.

This is not hypothetical. Until #489 the scan ran `gh issue list --state open --limit 100`, and with
that filter **build-spec's own scan could not find #407 and #140** — the two closed decisions that
govern build-spec itself (#407: add the issue adapter to build-spec, no new skill; #140: ② leaf,
no thin plugin). On 2026-08-02 three days of design were built on the assumption that gap was still
open, because the closed record was unreachable from every tool that looked.

**Why a script instead of a wider `gh` call.** `--state all` on this repo returns 200+ closed issues;
their bodies would swallow the interview's context budget. `scripts/backlog-prefilter.py` reads the
whole corpus **in the shell**, scores by term overlap, and prints only a budgeted digest — open
candidates with trimmed bodies, closed candidates as titles. Same shape as
obsidian-vault-manager audit Phase 1: deterministic narrowing at zero LLM cost. The `--limit 100`
ceiling goes away with it (open 500 / closed 1000).

**Why the skip line is loud.** The old text said `gh` failure → *skip silently*. A silent skip makes
"scanned, no conflicts" and "never scanned" produce identical output, so the safety check can be off
without anyone noticing — the #443·#447 failure class. The script therefore always prints: either a
digest or a `[backlog-scan SKIPPED]` line, and that line is copied verbatim into
`context.backlog_scan`.

**Known ceiling.** Term overlap is not meaning: a conflicting issue sharing no vocabulary with the
target scores 0 and never surfaces. Closed candidates are ranked on titles only. Both are recorded in
SKILL.md Known Limitations — the scan narrows the search, it does not close it.

---

**Why the backlog scan exists, and why it stays in the shell.** Code and manifests carry only what
already shipped; a repo's decided-but-unbuilt constraints live in the backlog, so X3 has no source
without it. `backlog-prefilter.py` reads the whole open+closed corpus in the shell and emits only a
budgeted digest, so the corpus never enters context. A `[backlog-scan PARTIAL]` line is copied whole
because that side's "0 hits" is unconfirmed, not clean — a paraphrase would erase the difference.

## 6. UD Handoff — Phase 2.5 Skip Condition (#430)

**Why detect the feedback source at all.** `<feedback>` may arrive as a file path — a Refine-mode
session's `<feedback>` can be an `unknown-discovery` Discovery Report handed off asynchronously via
a Seed file (`../../reference/ud-bs-boundary.md`'s "UD → BS" path). Phase 1's A3 has to `Read` that
path before injecting it, or Phase 2.5's skip condition below has nothing to check — a condition
that can never observe its own trigger is not a condition, it is dead text.

**Why skip Phase 2.5 when it fires.** Phase 2.5 exists to catch dimensions the interview never
asked about. `unknown-discovery`'s interview already ran a deeper version of exactly that sweep
against this same spec — more rounds, isolated Depth scoring, four dedicated areas — so re-running
the one-`Agent`-call version on top of it is redundant, not additive, and would just spend a call
re-deriving findings the UD report already states with more rigor.

**Detection.** The report's frontmatter carries `skill: unknown-discovery` (common-schema.md);
absent that (a bare prose feedback string), the user naming it explicitly is enough.


---

## 7. Amendment Contract — why it travels in the file

**Why a header comment and not only this skill.** The session that edits a Seed after emit is
usually a `/goal` loop that never loads build-spec. Its only readable surfaces are the Seed file
and its own completion condition, so a rule stated here reaches nobody. The template's header
comment is the one place the offender is guaranteed to read, and `next-goal` carries the same
sentence into the condition paragraph.

**What the rot looks like.** Measured on a real Seed (999 lines, 18 commits, near-monotonic
growth): constraint rationales had become commit messages — `(2026-09-17 requirement-gap-reviewer
발견·수정) 첫 구현은 ... 빠뜨렸었다 ... 바로잡았고 ... 단위 테스트 4케이스로 확인` — and the file
had grown a CHANGELOG header. None of it is a requirement; all of it is already in git and the
issue timeline.

**In-place edit vs `-v2`.** They answer different questions. A full build-spec re-run produces a
new generation and still writes `-v2`/`-v3` (Phase 3 step 2). An in-place edit is for a fact the
spec states wrongly — the value gets replaced, the file does not grow a journal entry. Ids survive
both: a `-vN` regeneration keeps the prior `c*`/`ac*` ids so children's `refines` still resolve.

**Enforcement.** `hooks/seed-append-guard.sh` denies three shapes. First, an edit that introduces a
key `templates/SEED_SPEC.yaml` does not define at that position — a top-level `status:` and one
indented inside a constraint item alike (#767); keys the Seed already carried are left alone, so a
field a Seed needs belongs in the template first. Second, the journaling shape: the old text
surviving whole inside the new text while the added part carries work-log vocabulary. An addition
that starts a new key or list item is structural growth and exempt from that second check only — a
new constraint legitimately carries a provenance date, so signal alone would fire on exactly the
edit Refine mode has to make. Third, an edit after which a `c*`/`ac*` id the Seed held before has
disappeared (#780 c3) — other Seeds' `refines` point at those ids.

**On Codex this document contract is the only enforcement.** The guard is a Claude Code PreToolUse
hook; a Codex run edits the Seed with no hook in the way, so the header comment and this section are
all that stand between a Seed and a `status:` field there.

## 8. Seed Relations — Phase 0 question and Phase 3 parent write (#780)

SKILL.md keeps the steps as short imperatives; this section holds the reasons and the detail.

**Why the sub-feature list is human-picked.** next-goal never scans `docs/specs/` to guess a parent,
because a directory scan would decide for the user which Seed a new one belongs to, and a wrong guess
writes a wrong edge into two files. build-spec only *offers* candidates from `Glob(pattern="docs/specs/*.yaml")`
and the user chooses. No `docs/specs/` or no match means there is nothing to offer, so the question is
skipped entirely.

**Option count.** `AskUserQuestion` allows 4 options. Show at most 3 same-repo Seeds, each labelled by its
`target:` and ordered most recently modified first (a slug appears once, as its latest `-vN`: when `foo.yaml`
and `foo-v2.yaml` both match, only `foo-v2.yaml` is offered, because the older file is a superseded
generation), plus "아니요, 독립 Seed". Any other same-repo path, or an
other-repo coordinate `owner/repo:docs/specs/x.yaml`, comes in through Other. "아니요, 독립 Seed" means no
parent and `relations` stays at the template defaults.

**What gets recorded.** While interviewing, note which of the parent's `c*`/`ac*` ids this Seed spells
out (`relations.refines`, may be empty) and any sibling Seed it must wait on (`relations.depends_on`).
`depends_on` is written only when the user says so, never inferred, because a guessed dependency blocks
work that was never blocked.

**Link reason.** Also record `relations.link_reason`: one sentence on what the refined parent items leave
open that this Seed settles; with `refines` empty, why no parent item maps. If the interview did not make
it evident, ask; if the user gives none, leave `null` (shown as 미확인). A fabricated reason reads as a
fact in every later `tree` output, so a blank is better than a guess.

**Issue references.** `issues.source` is the issue the session started from, recorded only when the
conversation or input names it (`#N` same repo, `owner/repo#N` otherwise); otherwise `null`.
`issues.tracking` stays `[]` at creation and gets the number of the issue implementing the Seed once
step 7's issue-raise creates one (an `Edit` on the just-emitted Seed). Source and tracking are distinct: a
Seed created from #N whose implementation is tracked in the same #N lists it in both. These are
references, never a status.

**Why Refine carries relations and ids.** A refined Seed is written to a new `-vN` file. If `relations`
is not restored verbatim, the edges vanish in that file. The prior `c*`/`ac*` ids stay as they are
because children's `refines` point at those ids. The parent edge already sits in the restored
`relations`, so the sub-feature question is skipped in Refine mode.

**Phase 3 parent write.** With a parent chosen, fill the template's `relations` block: `relations.parent`
(same repo: repo-root relative path; other repo: `owner/repo:docs/specs/x.yaml`), `relations.refines`,
`relations.depends_on`.
- Same-repo parent: resolve the chosen parent to its latest `-vN` first (highest N of the same slug; the
  unsuffixed file counts as v1), then `Edit` only that file's `relations.children`, adding the new Seed's
  path, and set `relations.parent` to that resolved path. Editing the older generation would leave the
  edge on a superseded file, and the child's parent edge would point at a file whose `children` the
  reader never consults. If the parent predates `relations`, add the template's `relations` block
  first, then edit only that field.
- Other-repo parent: never written. Each repo writes only itself, so a session here editing another
  repo's file would bypass that repo's own review and guards. Print one line telling the user to add
  the new Seed to that parent's `children` from a session in that repo.

**What `seed-relations.py check` reports.** It reads the new Seed's edges and verifies them against the
files they name, printing `MISMATCH` lines where an edge is not mirrored on the other side (for example
the parent's `children` lacks the new Seed) and `FAILED` where a referenced Seed cannot be read. Show
those lines to the user; do not fix them silently. `check` also prints `UNRECORDED` lines (not errors) for
a missing `link_reason` or `issues.source`; show those as 미확인 items. To see the parent-to-child item
mapping from either side, run `seed-relations.py tree <seed>`.

**Linking an existing Seed that has no relations.** Write an edge only when the user names it or the
files verify it (for example an issue body that cites the parent's path). Proposing a candidate link is
separate from writing it: a proposal waits for the user's yes. Never write `relations` or `depends_on`
on a guess, and never write into another repo's Seed.

## 9. Requirement-gap review of a Seed-traced diff (note for later reviewers)

build-spec does not run this review itself. When a completion condition's requirement-gap review
(next-goal's L2, not the correctness + CLAUDE.md/guard-script `/code-review` call) traces its diff back
to a Seed, it runs as `subagent_type: "thinking-tools:requirement-gap-reviewer"`. That agent carries the
grading methodology in its own body, Seed or no Seed, but not its own scope, so hand it the base ref or
diff range as well, and additionally attach `${CLAUDE_PLUGIN_ROOT}/reference/seed-diff-grading.md`'s
instruction to its prompt for the Seed-aware specialization.

## 10. Known Limitations and Phase 2.5 rationale

**Why Phase 2.5 runs once, after the gate.** Put earlier, every finding becomes new interview rounds, which doubles the interview and gets the skill abandoned in real use. After the gate it reads an already-sharp spec, so its questions are sharper too. The clarity gate only scores dimensions that were *asked*: a dimension nobody raised is not scored low, it is not scored at all, so all four dimensions can sit at 0.9 while the spec still collides with a decision made elsewhere. This pass looks at the unasked.

### Known Limitations

- **Isolated verdict is gate-only**: per-round scoring stays inline; only the round that would open the
  gate is re-judged in a subagent (Phase 2). A mid-interview score can still drift — it just cannot open
  the gate on its own. Users can override scores by providing explicit corrections during the interview.
- **Blind-spot pass is one shot**: three findings, one call, no follow-up round (constraint: the
  interview length must not grow). It is a last sweep, not a second interview — a spec needing real
  blind-spot work should go through `unknown-discovery` directly.
- **Backlog scan reads titles and bodies, not comments**: an issue whose current state lives in its
  comment timeline can still read as unconflicting. Closed candidates are ranked by **title only**
  (bodies are not fetched for the closed half — that is what keeps the corpus out of context), so a
  closed decision whose conflict is stated only in its body is reachable but not pre-surfaced.
- **A silent subagent is indistinguishable from a slow one** (#647): a spawned subagent can stay alive,
  emit only idle notifications, and never return a final report — no error, no timeout, so nothing in
  Phase 2 / Phase 2.5 fires on its own. The documented rule (one re-request, then treat as unavailable)
  is what converts it into the inline fallback, and applying that rule is a judgment call, not a check.
- **The prefilter is the recall ceiling**: candidates are scored by term overlap, so a conflicting
  issue that shares no vocabulary with the target scores 0 and never appears. Term overlap is not
  meaning.
