# Thought Chain — Hook & Integration Reference

## Recommended Hooks for Skill Synergy

Hooks can automate transitions between thinking-tools skills without manual orchestration.

### 1. Post-Discovery → Expert Panel Auto-Suggest

**Type**: PostToolUse (after unknown-discovery Phase 3 completion)
**Purpose**: When discovery finds Critical items, auto-suggest expert-panel review

```
Hook trigger: unknown-discovery output contains "Critical" findings
Action: Suggest "/expert-panel" with discovered topics pre-loaded
Confirmation: Always ask user before proceeding
```

**Rationale**: Critical blind spots benefit from multi-perspective expert debate. This hook reduces friction by pre-loading discovery findings as panel topics.

### 2. Post-Panel → Doc-Concretize Auto-Suggest

**Type**: PostToolUse (after expert-panel Phase 2 completion)
**Purpose**: When panel produces consensus with action items, suggest documentation

```
Hook trigger: expert-panel generates SUMMARY.md with action items
Action: Suggest "/doc-concretize" with consensus items as input
Confirmation: Always ask user before proceeding
```

**Rationale**: Panel consensus decisions need documentation for stakeholder communication. This hook bridges analysis to artifact creation.

### 3. Post-Concretize → Doc-Polish Auto-Run

**Type**: PostToolUse (after doc-concretize Phase 5 completion)
**Purpose**: Auto-run quality check on freshly generated documents

```
Hook trigger: doc-concretize outputs a completed document
Action: Auto-run "/doc-polish --fix" on the generated document
Confirmation: No confirmation needed (non-destructive, editor-only)
```

**Rationale**: Freshly generated documents always benefit from mechanical quality checks. Since doc-polish is non-destructive (editor, not writer), this can safely auto-run.

### 4. Diverse-Sampling → Expert Panel Bridge

**Type**: Manual invocation
**Purpose**: When brainstorming produces diverse options, use expert panel to evaluate them

```
Pattern: User runs /diverse-sampling --all → gets 5+ options
User says: "이 옵션들을 전문가 토론으로 평가해줘"
Action: Load diverse-sampling results as expert-panel topics
```

**Rationale**: Diverse options need structured evaluation. This bridge connects creative generation with analytical assessment.

## Implementation Notes

These hooks are suggestions for users who want tighter integration between skills. The `thought-chain` skill itself implements this pipeline without hooks — hooks are for users who want automatic suggestions when using skills individually.

**Note**: Claude Code hooks cannot currently distinguish which skill triggered a tool call. Therefore, these hooks should be implemented as prompt-based suggestions within each skill's post-completion flow, not as `settings.json` hook matchers. Example concept (not a literal config):

```
# Conceptual: After unknown-discovery Phase 3 completes with Critical findings,
# the skill itself suggests: "Critical 발견이 있습니다. /expert-panel로 전문가 토론을 진행할까요?"
```
