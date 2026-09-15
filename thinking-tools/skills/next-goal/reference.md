# next-goal — rationale and runtime limits

Read only when a judgment needs explanation. The binding selection and completion rules live
in `SKILL.md`; this file does not supply a second ranking algorithm.

## Cohesion and value

Mechanically selecting the smallest fragment loses necessary related work. The opposite error
is enlarging a valid small task solely because one context could finish it. Group by the real
problem and its dependencies, then stop when the unit has practical value and a provable end
state. A nits-only pool may remain empty after one backlog comparison. Unknown backlog is not
empty backlog, and neither requires a fabricated next goal.

## Evidence and bounded review

A repository check cannot prove the installed copy or a fresh runtime invocation. A runtime
migration's completion condition must expose each relevant layer. Reviewer scope comes from the
caller so separate passes grade the same diff. Review round limits count attempts across calling
methods; an infrastructure failure is not a reason to try a new agent until something agrees.
Use existing machine rules P9/P18 when installed; do not copy their catalogue into the goal.

## Runtime limits

- Claude `/goal`: 4,000 characters, requires Claude Code v2.1.139+. Confirm current support with
  the installed CLI and [official goal documentation](https://code.claude.com/docs/en/goal).
- Claude skill listing and invoked body are different budgets. The installed v2.1.267 code uses
  a default 1,536-character per-description listing cap, 1% listing budget, a 5,000-token
  per-skill compaction reattachment cap, and 25,000 tokens across reattached skills. These are
  version-specific observations, not an initial invocation body cap of 3,000 tokens.
- Codex starts with name/description/path, reserving at most 2% of known context or 8,000
  characters when unknown. Selection reads the full SKILL.md. See [official skills docs](https://learn.chatgpt.com/docs/build-skills).
- A tool's output preview may truncate a read independently. Check its truncation marker and
  retrieve missing ranges; a clean listing-budget check cannot prove full invocation content.
