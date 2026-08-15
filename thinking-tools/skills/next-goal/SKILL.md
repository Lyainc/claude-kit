---
name: next-goal

description: |
  Author the next session's completion condition — pick one session-sized unit of follow-up work
  (an epic-sized theme sized for a fanned-out session, not the smallest extractable fragment),
  then render it as a single `/goal`-evaluable paragraph. Two stages in one skill: an internal
  ROI ranking whose only visible output is the pick plus its runners-up, and the condition
  paragraph itself, shaped against the surfaced-evidence levers a goal evaluator can actually
  check.

  Trigger when user mentions: 완료조건, 다음 세션 목표, START-PROMPT, goal 조건 작성,
  다음 작업 정해줘, completion condition, next goal, what should I do next session.
  Routing: 세션 종료 루틴 전체(PR 정리·이슈 점검 포함)는 그 루틴을 쓰고, 이 스킬은 그중
  "무엇을 다음에 할지 + 어떤 조건으로 닫을지"만 담당한다. 아이디어를 명세로 굳히는 건
  build-spec, 문서 저작은 doc-concretize.
allowed-tools: Read Bash
effort: medium
---

# Next Goal

## Language Behavior

- **Instructions**: English (this file)
- **Output**: Korean. The rendered paragraph follows the user's working language.

## What this produces

Two things, in this order:

1. **The pick** — three short fields naming what to do next, where the candidate came from, and what lost.
2. **The condition** — one fenced `/goal ` paragraph, ready to paste.

Nothing else. No status recap, no file writes, no issue writes. This skill creates nothing,
edits nothing, and closes nothing — a caller that also manages PRs or issues does that in its
own steps, before invoking this one.

## Input contract

The caller supplies, or this skill collects:

| Input | Required | How to get it if absent |
|-------|----------|-------------------------|
| This session's follow-up candidates | yes | Read back from the conversation |
| Open backlog | only when Phase 1 step 3 fires | Bash: `gh issue list --state open --limit 60` |
| Chain depth (how many sessions this thread has run) | no | Assume 1 when unknown |

If the repo has no GitHub remote, the backlog widening step is unavailable — say so in one
clause and rank the session's own pool alone.

**A hook may have already delivered the last two.** When thinking-tools is installed as a
plugin, invoking this skill fires `hooks/next-goal-context.sh`, which runs
`scripts/next-candidate.py` and injects the chain depth plus the open backlog as unrequested
context. Read what arrived rather than fetching it a second time.

**Never assume it arrived.** The hook goes silent whenever it cannot produce something — kill
switch set, no `jq`, no `python3`, no GitHub remote, `gh` missing or unauthenticated — and it
never announces the skip. Stating the data is present would assert something false in exactly
the runs where the comparison set matters most. So: injected block in context → use it; absent
→ fall back to the table above. The report labels its own gaps (`조회 못 함` / `조회 실패`
against `0개`), so a failed lookup is never readable as an empty backlog.

The injected payload carries **data only**. Every judgment — the impact floor, when to
re-pick, disclosing which pool the candidate came from — lives in this file and nowhere else.

---

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
  into the condition itself, scoped to correctness and requirement gaps only — say "ignore style"
  explicitly, or the reviewer invents gaps and drives over-engineering.
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

### Stop at "commits pushed" — check before emitting

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

**Read the emitted sentence back for merge vocabulary before showing it.** Stating this boundary
in prose alone has been observed to fail — the check has to be an actual pass over the output.

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

## Output format

**Called from a routine that owns its own report shape** — a session-close pass, a wrap-up
sequence — return the three values and the paragraph, and let the caller place them. Do not
render the layout below on top of the caller's; that would print the pick twice in two shapes.
The three values are what the caller needs, in this order: the pick, the pool it came from, the
runners-up.

**Called directly**, render them:

```
NEXT     · {한 줄}
POOL     · {출처; 전환 시 왜 자체 풀이 바닥을 못 넘었는지}
RUNNERS  · {탈락 후보 한 줄}
```

Then a **plain 3-backtick fence whose first characters are the literal `/goal `**, the whole
paragraph on one line inside it, so the next session is a single paste.

**Never nest fences** — an inner fence inside an outer one renders as literal backticks, not a
code block. No tables and no box-drawing frames either; terminal width varies and both wrap into
garbage.

**Nothing follows the fence.**

---

## Example

```
NEXT     · vault 폴더 재편 에픽 통째 — inbox→sources 개명(#B) + audit E4/E10 규칙 정합(#C) + manifest 스키마 갱신(#D)
POOL     · 이번 스레드 #B + 백로그에서 같은 테마 #C·#D 합류
RUNNERS  · telemetry 리포트 서식 정리 (테마가 달라 이 에픽과 안 묶임)
```

```
/goal vault 폴더 재편 에픽(#B·#C·#D)을 한 번에 닫는다: inbox/ 를 sources/ 로 개명하고 그 경로를 참조하는 여섯 지점(capture 기본 경로, pre-write-guard 경로 검증, audit E10 배치 규칙, generate-manifest.py, v4 §3.1 문서, CLAUDE.md 규약표)을 갱신하고, audit E4 규칙을 새 배치에 맞게 다시 쓰고, manifest 스키마에 sources/notes 구분 필드를 추가한다. 세 갈래는 파일이 안 겹치므로 병렬로 돌리되 한 갈래 안의 경로 수정 여섯 지점은 순차로 처리하고, 기계적인 경로 치환과 manifest 필드 추가는 Workflow agent() 에 effort low 로 넘기고 판정이 걸린 audit E4 규칙 재작성은 메인에서 직접 본다 — 실물을 보고 난이도가 다르면 이 배정은 바꿔도 된다. 완료 상태는 scripts/check-test-exitcode.py 가 exit 0 을 내고 마크다운 링크 26개 중 이동 영향권에 든 것이 전부 갱신되고 audit 이 E4·E10 오탐 0 으로 도는 것이다. 최종 diff에 fresh-context 리뷰를 돌려 correctness·요구사항 갭 0을 확인하되 스타일 지적은 무시하고, 커밋은 논리 단위로 쪼개 푸시까지만 한다 — 세 갈래가 각각 PR감이지만 PR은 다음 세션이 판단하므로 이번엔 열지 않는다. 또는 80턴 후 정지.
```

---

## References

- `/goal` completion conditions: https://code.claude.com/docs/en/goal — conditions are capped at
  4,000 characters and the feature requires Claude Code v2.1.139+; on an older CLI a Skip renders
  cleanly instead of a broken paste.
- Loop design and falsifiability: https://code.claude.com/docs/en/best-practices
