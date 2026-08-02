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
| C2 | hard / soft constraint 구분이 가능한가? | User differentiated "must have" vs "nice to have" |
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
- **Why the verdict is isolated at all** (#433): the interviewer asking, scoring, and then declaring its own gate open is a 1-in-3-roles loop — the same self-verification bias `adversarial-review` removes by spawning its Judge as a separate `Agent` subagent, and `unknown-discovery` removes for Depth scoring. So the verdict that actually opens the gate comes from a subagent, not from this context. When that subagent call fails, SKILL.md Phase 2 announces the fallback instead of absorbing it silently: a self-scored gate and an isolated one carry different confidence, and rendering them identically would hide exactly that difference from the user.
- **A policy-blocked `Agent` call is the same condition, not a separate one** (#433 remaining scope): a session-level policy that denies `Agent` calls (e.g. "no subagent spawns unless requested") stops the isolated call exactly like a timeout or an unavailable subagent does, so it takes the same fallback — inline score, one-line announce, `scoring_isolated: false`. It does **not** additionally trigger an `AskUserQuestion` approval prompt. Reasons: (1) a policy denial has already routed through the harness's own permission gate (or a hard deny rule) before the call fails — asking the user again re-confirms a decision that gate already recorded; (2) under unattended execution the question would get no answer and default to the lower-risk branch anyway (`P6`), which is exactly "continue inline, announce" — so the prompt changes nothing except adding friction; (3) `#430` already caps interview length, and a meta-question is still an extra round the user has to clear.
- **`scoring_isolated` is not folded into the Gate Check ✓/✗ line**: the fallback announce line already prints immediately before that block whenever `scoring_isolated: false`, so the confidence drop is already visible at the exact moment it matters. The ✓/✗ row is scoped to "which dimension is short of its floor" (line above, "shows *which* dimensions still fall short"); mixing a confidence flag into it would answer two different questions in one line and make both harder to read.
- For "빠르게" (quick) mode: evaluate G1-G4 only; gate = Goal ≥ 0.75 (skip other dimensions).
- If user provides a very detailed answer covering multiple dimensions at once: score all relevant dimensions simultaneously.

---

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

**Phase 4 title convention.** Phase 4 used to pass the spec slug straight through
(`gh issue create --title "{target}"`). Many repos — claude-kit among them — carry type and scope in
the title (`fix(vault-bridge): 매니페스트가 archived 노트를 올린다`) instead of in labels, and some
enforce it with a `gh issue create` guard hook, so a bare slug is rejected outright. Phase 4 now reads
the repo's own recent titles and follows their shape rather than assuming one.

**Known ceiling.** Term overlap is not meaning: a conflicting issue sharing no vocabulary with the
target scores 0 and never surfaces. Closed candidates are ranked on titles only. Both are recorded in
SKILL.md Known Limitations — the scan narrows the search, it does not close it.

---

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
