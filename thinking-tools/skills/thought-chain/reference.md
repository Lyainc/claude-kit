# Thought Chain — Reference

## Deepen Prompts (per stage)

When the user selects the deepen option, re-invoke the current stage's skill with the prior output as context plus one of these instructions:

### Stage 1: unknown-discovery — 더 인터뷰

```
Prior output: {discovery_report}

Continue the blind-spot interview with deeper focus on the findings already surfaced.
Goals:
- Ask follow-up questions on the Critical/Important items found
- Probe for second-order consequences the initial interview may have missed
- Raise depth metric toward 85%+
Do not restart from scratch — build on the prior report.
```

### Stage 2: expert-panel — 더 토론

```
Prior output: {panel_summary}

Resume the expert panel debate with sharper focus on unresolved tension.
Goals:
- Attack the remaining dissenting views — experts must defend or revise
- Re-examine any consensus item that relied on a contested premise
- Re-synthesize: produce an updated SUMMARY.md reflecting the deeper debate
Do not restart the panel from scratch — continue from where the prior summary ended.
```

### Stage 3: doc-concretize — 더 구체화

```
Prior output: {concretized_document}

Deepen the document one level further.
Goals:
- Expand each section with more specific details, examples, or sub-sections
- Add recursive depth: break high-level items into actionable sub-items
- Ensure every recommendation has a concrete "how" attached
Do not rewrite the structure — expand within it.
```

### Stage 4: doc-polish — 더 다듬기

```
Prior output: {polished_document}

Apply a stricter quality pass.
Goals:
- Layer 2 (consistency): check term consistency, sentence length, and tone uniformity
- Layer 3 (semantic): flag vague claims, unexplained terms, or missing context
- Check that all action items from the expert panel appear in the document
Report remaining issues after the pass.
```

---

## Vault Destination Routing Examples

### Full pipeline → Plan doc save

```
→ Stage 4 완료
→ Vault Destination: "Plan doc로 vault에 저장" 선택
→ Invoke: vault-bridge:save-session plan
   Context passed: polished document body + thought_chain: frontmatter metadata
→ Result: vault에 plan-2026-05-16-{topic}.md 저장
```

### Mid-stop at Stage 2 → Session note save

```
→ Stage 2 체크포인트: "멈추고 vault 저장" 선택
→ Mini-polish: Stage 2 결과(consensus + dissents)를 markdown으로 패키징 → doc-polish 호출
→ Vault Destination: "Session note로 vault에 저장" 선택
→ Invoke: vault-bridge:save-session (record mode)
   Context passed: mini-polished document embedded in record body
   thought_chain.stopped_at: "panel"
→ Result: vault에 session-2026-05-16-{topic}.md 저장
```

### Gate closed → terminal fallback

```
→ Stage 4 완료
→ Vault Destination: vault_linked = false
→ Plan doc / Session note options hidden; hint displayed
→ User picks "터미널만"
→ Result: 터미널에 전체 문서 출력
```

---

## Thought Chain Metadata — Tags Reference

The `thought_chain:` frontmatter block structure lives in SKILL.md (§Metadata Aggregation). This section covers the one piece SKILL.md doesn't detail: how `tags` are built.

**Tags auto-extraction**:
- Source: `unknown-discovery` finding domains + `expert-panel` expert specializations
- Deduplication: remove overlaps between the two sources
- Always prepend `thought-chain` as the first tag

Example: discovery finds security/performance issues; panel adds UX/infra experts →
`tags: [thought-chain, security, performance, ux, infra]`

---

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

---

## Implementation Notes

Hooks above are suggestions for users who want tighter integration between skills. The `thought-chain` skill itself implements this pipeline without hooks — hooks are for users who want automatic suggestions when using skills individually.

**Note**: Claude Code hooks cannot currently distinguish which skill triggered a tool call. Therefore, these hooks should be implemented as prompt-based suggestions within each skill's post-completion flow, not as `settings.json` hook matchers.
