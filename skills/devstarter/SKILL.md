---
name: devstarter

description: |
  This skill should be used when the user asks to "개발 시작", "dev start",
  "작업 시작", "팀 작업 시작", "start development", or invokes "/devstarter".
  Initializes consistent development workflow with tool selection,
  atomic commits, testing, and optional team coordination.
---

# Development Starter

Initialize a consistent development workflow with tool selection, commit discipline, and optional team coordination.

## Step 1: Tool Selection

Present tool selection using AskUserQuestion (multiSelect: true):

```
Question: "이번 작업에서 사용할 도구를 선택하세요."
Header: "Tools"
Options:
  - label: "serena (LSP 코드 분석)"
    description: "LSP 기반 코드 탐색, 심볼 검색, 참조 추적으로 정확한 코드 분석"
  - label: "/team (팀 협업)"
    description: "다수 에이전트가 task list 기반으로 병렬 작업"
  - label: "/ralph (자기참조 루프)"
    description: "architect 검증 루프를 통한 반복 개선 작업"
  - label: "/chrome-devtools (라이브 검증)"
    description: "브라우저에서 실제 UI/기능 동작을 라이브로 확인"
```

## Step 2: Mode Detection

Determine the working mode based on tool selection:

- **/team** or **/ralph** selected → **Team Mode**: Read and apply [references/team-workflow.md](references/team-workflow.md) before proceeding.
- Neither selected → **Solo Mode**: Skip team-specific rules.

## Step 3: Core Rules

Apply these rules throughout the entire development session:

### Atomic Commits
- One logical change = one commit. Follow `git-master` style conventions.
- Write a clear, imperative commit message describing the "why".
- Stage only related files per commit. Never bundle unrelated changes.

### Test on Every Commit
- Run unit tests before each commit. Do not commit if tests fail.
- If no test suite exists, state what was verified manually.

### Live Verification (when /chrome-devtools selected)
- After implementing a user-visible feature, verify it on the live page.
- Capture or describe the result before moving to the next task.

### Build Error Recovery
- When a build or typecheck error occurs, use the `build-fixer` agent (`oh-my-claudecode:build-fixer`) to resolve it with minimal changes.
- Do not attempt architectural changes to fix build errors.

### Team Mode Rules (summary)
- Each agent works on a separate git branch via worktree.
- Team-lead checks for conflicts at each agent completion checkpoint.
- See [references/team-workflow.md](references/team-workflow.md) for full procedures.

## Step 4: Skill Chaining

Invoke selected tools after setup:

| Selection | Action |
|-----------|--------|
| /team | Call `Skill("oh-my-claudecode:team")` to start team coordination |
| /ralph | Call `Skill("oh-my-claudecode:ralph")` to start self-referential loop |
| serena | Use LSP MCP tools (`lsp_hover`, `lsp_goto_definition`, `lsp_find_references`, `lsp_document_symbols`) for code analysis throughout the session |
| /chrome-devtools | Follow live verification procedure in [references/tool-guide.md](references/tool-guide.md) |

**Important**: Only invoke /team OR /ralph, not both. If both are selected, ask the user to choose one.

## Step 5: Context Recording

Record the session setup using the notepad MCP tool:

```
Tool: notepad_write_working
Content: "[{date}] devstarter: {mode} | {selected tools comma-separated}"
```

Example: `[2026-02-17] devstarter: Team Mode | serena, /team, /chrome-devtools`

## Step 6: Begin Work

After setup is complete:
1. Confirm the selected tools, mode, and rules to the user.
2. If a skill was chained (Step 4), follow that skill's workflow.
3. If Solo Mode with no chained skill, ask the user for the first task.

## References

- **Team workflow details**: [references/team-workflow.md](references/team-workflow.md) — git worktree setup, branch strategy, conflict checking, agent coordination
- **Tool usage guides**: [references/tool-guide.md](references/tool-guide.md) — serena, chrome-devtools, /team, /ralph, git-master, build-fix
