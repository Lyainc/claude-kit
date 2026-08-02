# Interview State — Shared Persistence Contract

Applies to every skill that runs a Phase 1 interview loop with optional cross-session STATE
file persistence (`unknown-discovery`, `build-spec`). STATE block **fields** differ per skill
(each skill's own SKILL.md is the single source of truth for its current fields — this file
does not repeat them, so a field rename never needs a second edit here). What both skills
share is *when* to save and *how* to restore.

## Save Trigger — User-Initiated Only

The Phase 1 loop does **not** proactively persist state. The in-memory STATE block emitted at
every checkpoint/round is the canonical run-time checkpoint; file persistence exists for
cross-session continuity only, and only fires on an explicit user request:

- Korean: "저장해줘", "나중에 이어하자", "여기까지 저장"
- English: "save state", "pause and resume later"

## Restoration Procedure

1. Read the saved state file at the start of the new session.
2. Restore all STATE block fields (scores, round/checkpoint counters, per-area/dimension status).
3. Resume from the lowest-scoring area/dimension — never restart at round/question 1.
4. Tell the user what was restored before asking the next question.

## Compaction Recovery

Same rule as [state-contract.md](state-contract.md): on context compaction, restore from the
most recently emitted in-session STATE block — every field in it, not a subset.

## Skill-Specific Detail

Save path, STATE field schema, and save-file frontmatter stay skill-specific:

- unknown-discovery: [`../skills/unknown-discovery/templates/INTERVIEW_STATE.md`](../skills/unknown-discovery/templates/INTERVIEW_STATE.md)
- build-spec: [`../skills/build-spec/templates/INTERVIEW_STATE.md`](../skills/build-spec/templates/INTERVIEW_STATE.md)

**재드리프트 방지**: 이 문서가 유일한 저장/복원 규칙 소스다. 두 스킬의 템플릿 파일이 이 규칙을
다시 산문으로 베껴 쓰면 그 사본이 여기와 따로 낡아가는 게 애초의 드리프트였다 — 그래서
템플릿 파일들은 이 섹션들을 인용만 하고 재서술하지 않는다. 이 관례를 지키는 자동 검증은 없다.
