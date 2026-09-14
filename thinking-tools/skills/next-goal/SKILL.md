---
name: next-goal

description: |
  Choose an epic-sized next-session unit by ROI and render an evidence-backed completion
  condition. For an end-to-end session-close routine, use that routine; use build-spec for
  specs and doc-concretize for documents.

  Trigger when user mentions: 완료조건, 다음 세션 목표, START-PROMPT, goal 조건 작성,
  다음 작업 정해줘, completion condition, next goal, what should I do next session.
allowed-tools: Read Bash
effort: medium
---

# Next Goal

## Codex Portability

When Codex invokes this skill, read [the portability contract](../../reference/codex-portability.md)
first, then read [the detailed rules](reference.md). Apply this section and the vendor-neutral
rules there, but do not execute any later
hook, Workflow, Agent/Skill, model-routing, or Claude `/goal` output instruction; Claude Code
ignores this section.
For Phase 2, name only direct checks available in the current runtime. Request an independent
Codex subagent review only when that facility is available, otherwise perform a separate direct
final check; never name a Claude agent type, model route, Workflow, or slash review command.
Describe parallel work only when the current Codex runtime can delegate it, otherwise keep the
work sequential.
For a direct call, render `NEXT`, `POOL`, `RUNNERS`, then one plain `GOAL` paragraph — never a
`/goal` fence. A caller cannot invoke this skill as a nested tool; it reuses those four values
inline instead.

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
re-pick, disclosing which pool the candidate came from — lives in these skill instructions, not
the payload.

---

## Detailed Rules

Before Phase 1, read [the detailed rules](reference.md). They are canonical for the ROI ranking,
condition criteria, and pre-emission checks; keep the input and output contracts in this file.

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
/goal vault 폴더 재편 에픽(#B·#C·#D)을 한 번에 닫는다: inbox/ 를 sources/ 로 개명하고 그 경로를 참조하는 여섯 지점(capture 기본 경로, pre-write-guard 경로 검증, audit E10 배치 규칙, generate-manifest.py, v4 §3.1 문서, CLAUDE.md 규약표)을 갱신하고, audit E4 규칙을 새 배치에 맞게 다시 쓰고, manifest 스키마에 sources/notes 구분 필드를 추가한다. 세 갈래는 파일이 안 겹치므로 병렬로 돌리되 한 갈래 안의 경로 수정 여섯 지점은 순차로 처리하고, 기계적인 경로 치환과 manifest 필드 추가는 Workflow agent() 에 effort low 로 넘기고 판정이 걸린 audit E4 규칙 재작성은 메인에서 직접 본다 — 실물을 보고 난이도가 다르면 이 배정은 바꿔도 된다. 완료 상태는 scripts/check-test-exitcode.py 가 exit 0 을 내고 마크다운 링크 26개 중 이동 영향권에 든 것이 전부 갱신되고 audit 이 E4·E10 오탐 0 으로 도는 것이다. 최종 diff에 correctness는 /code-review high 로, 요구사항 갭은 읽기 전용 fresh-context 서브에이전트로 나눠 돌려 각각 0을 확인하되 스타일 지적은 무시하고, 커밋은 논리 단위로 쪼개 푸시까지만 한다 — 세 갈래가 각각 PR감이지만 PR은 다음 세션이 판단하므로 이번엔 열지 않는다. 또는 80턴 후 정지.
```

---

## References

- `/goal` completion conditions: https://code.claude.com/docs/en/goal — conditions are capped at
  4,000 characters and the feature requires Claude Code v2.1.139+; on an older CLI a Skip renders
  cleanly instead of a broken paste.
- Loop design and falsifiability: https://code.claude.com/docs/en/best-practices
