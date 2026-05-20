# Spec First — Interview State Template

## Usage

Save trigger is **user-initiated only**. Write this file when the user explicitly
asks to pause and resume later (Korean: "저장해줘", "나중에 이어하자", "여기까지 저장";
English: "save state", "pause and resume later").

The Phase 1 loop does NOT proactively persist state — the in-memory STATE block
(emitted after every round) is the canonical run-time checkpoint. File persistence
exists for cross-session continuity only.

Restore by reading this file at the start of a new session.

## STATE Block Format

```
<!-- STATE:CHECKPOINT -->
skill: spec-first
phase: {0|1|2|3|4}
target: {name} | domain: {tech|biz|creative} | brownfield: {true|false}
round: {N} | refine_generation: {0|N}
clarity: [goal:{score:.2f}] [constraint:{score:.2f}] [success:{score:.2f}] [context:{score:.2f or N/A}]
ambiguity: {value:.2f} | gate: {open|closed} | consecutive_gate: {0|1|2+}
scoring_rationale:
  goal: "{last rationale}"
  constraint: "{last rationale}"
  success: "{last rationale}"
  context: "{last rationale or N/A}"
<!-- /STATE -->
```

## File Persistence Format

When saving to file (`docs/specs/{target}/state.md`):

```markdown
---
skill: spec-first
target: {name}
domain: {tech|biz|creative}
saved_at: {ISO-datetime}
---

<!-- STATE:CHECKPOINT -->
...full STATE block content...
<!-- /STATE -->

## Discoveries so far

### Goal
{accumulated goal clarity notes}

### Constraints identified
{list of constraints found so far}

### Success criteria identified
{list of success criteria found so far}

### Context (brownfield)
{integration points and existing stack notes}
```

## Restoration Instructions

On new session start:
1. Read this file
2. Restore STATE block values
3. Display to user: "이전 인터뷰를 이어서 시작합니다. Round {N}부터 재개해요."
4. Resume from the dimension with lowest clarity score (not from Round 1)
