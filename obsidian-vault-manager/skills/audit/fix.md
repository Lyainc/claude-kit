# audit — Phase 4 OPTIONAL-FIX procedure

`SKILL.md` Phase 4 sends you here before ANY write. Read this file in full and follow it as written. If you
cannot read it, STOP and apply no fix. Nothing below relaxes the gate in `SKILL.md`: no vault write without the
approval of Step 1, E2 only, provenance never a placeholder.

## Phase 4 — OPTIONAL-FIX

**Purpose**: Apply frontmatter-only fixes for auto-fixable findings, gated behind explicit user confirmation. OFF by default.

**Inputs**: Findings list filtered to `auto_fix_eligible == true`.

**Tools used**: AskUserQuestion, Edit (frontmatter-only).

**Auto-fix eligible types**:
- `missing_required_fields` (E2): add missing `tags`, `type`, `created` fields with inferred values.
  `provenance` is required but NOT auto-fillable — surface it in the confirmation gate per-file
  and ask the user for the real origin, never a placeholder. Full rationale:
  `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **Auto-fix eligibility**.

**Tag inference**: when `tags:` is missing, do NOT insert an empty `tags: []` — derive a
proposal via ONE batched `ovm-primitives.sh infer-tags <relpath1> <relpath2> ...` call, never
one per finding. Tier rules and examples: `${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md`
→ **E2 tag inference**. Never auto-committed — previewed in the confirmation gate below.

**Auto-fix NOT eligible** (never mutate): E1, E3, E5, E6, E9, E10, E11, E12, E13. The binding list,
with each type's reason for needing a human decision:
`${CLAUDE_PLUGIN_ROOT}/reference/vault-audit-rules.md` → **Auto-fix eligibility**.

**Procedure**:

1. If `auto_fix_eligible` count > 0, first compute the tag proposals for every
   E2 finding whose missing fields include `tags` in ONE batched call (pass all
   such relpaths as arguments — see **Tag inference** above):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" infer-tags <relpath1> <relpath2> ...
   # >~200 paths (ARG_MAX headroom)? Pipe one per line into `infer-tags -` instead.
   ```
   Match each element's `path` back to its finding. A per-file failure surfaces as
   `error` + `inferred_tags: []` on that element and the batch still succeeds (exit
   is non-zero only when EVERY path failed). Then ask (single AskUserQuestion),
   showing each inferred proposal on its own line as `추론된 태그: [X, Y, Z]`:
   ```
   AskUserQuestion:
     question: "다음 F건의 frontmatter 이슈를 자동으로 수정할까요?"
     context: |
       수정 대상:
       • missing_required_fields: X건 (tags/type/created 추가)

       추론된 태그 (제안):
       • notes/llm/decision-2026-04-12-context-window.md → [decision, context, window, llm]
       • sources/capture-2026-05-01-obsidian-api.md → [capture, obsidian, api]

       provenance 누락 (자동 추론 불가, 개별 확인 필요):
       • sources/capture-2026-05-03-untitled-clip.md → 출처를 알려주시면 채워 넣을게요

       태그는 type·파일명·폴더에서 추론한 제안입니다. frontmatter만 수정하며
       파일 이름 · 내용 · 위치는 변경하지 않습니다.
     options:
       - "수정 실행"
       - "건너뜀"
   ```

2. If "건너뜀": exit without mutation. Mark scanned files clean in audit sidecar.

3. If "수정 실행":
   - For each `missing_required_fields` finding: use Edit to add the missing fields to the existing frontmatter block.
     - When `tags` is missing, write the inferred proposal from Step 1 (never an empty `tags: []`).
     - When `provenance` is missing, do NOT write a placeholder — ask the user for the real origin
       (or skip that field on this file if they don't know it) rather than fabricate one.
   - All edits are **frontmatter-only** — never touch the markdown body.

4. After all fixes, mark all processed files clean:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" audit-state mark-clean <relpath>
   ```

5. Stop metrics (`token`):
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics stop <token>
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/ovm-primitives.sh" metrics report <token>
   ```
   Output:
   ```
   완료: 이슈 K건 발견, F건 자동 수정됨
   소요 시간: {elapsed}ms
   ```

**Termination condition**: All confirmed fixes applied (or skipped), audit sidecar updated, metrics reported.
