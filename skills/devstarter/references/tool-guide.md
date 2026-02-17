# Tool Guide Reference

Usage guides for each tool available in the devstarter workflow.

## serena (LSP Code Analysis)

LSP-based code exploration for accurate, context-aware analysis.

### When to Use
- Understanding unfamiliar code before modifying it
- Tracing function call chains and dependencies
- Finding all references before renaming or refactoring
- Verifying type signatures and API contracts

### Key MCP Tools

| Tool | Purpose | Example Use |
|------|---------|-------------|
| `lsp_hover` | Type info and docs at a position | Check a function's return type |
| `lsp_goto_definition` | Jump to where a symbol is defined | Find where a class is implemented |
| `lsp_find_references` | All usages of a symbol | Check impact before changing a function |
| `lsp_document_symbols` | File outline (functions, classes) | Understand file structure quickly |
| `lsp_workspace_symbols` | Search symbols across project | Find a class without knowing the file |
| `lsp_diagnostics` | Errors and warnings for a file | Check for type errors after editing |

### Best Practices
- Always use `lsp_find_references` before modifying a public function or type.
- Use `lsp_hover` to verify types rather than guessing from variable names.
- Use `lsp_document_symbols` to orient yourself in large files before reading line-by-line.
- After edits, run `lsp_diagnostics` on changed files to catch errors early.

## /chrome-devtools (Live Verification)

Browser-based verification of UI and functionality on the live running application.

### Live Verification Procedure

1. **Pre-check**: Ensure the dev server is running. If not, start it.
2. **Navigate**: Open the relevant page in the browser.
3. **Verify**: Check the specific feature or UI change:
   - Visual: Does it render correctly?
   - Functional: Does the interaction work as expected?
   - Console: Are there any errors in the browser console?
4. **Record**: Describe what was verified and the result.

### When to Use
- After implementing a user-visible UI change
- After fixing a frontend bug — confirm it's resolved
- When testing interactive features (forms, modals, navigation)
- Before committing a frontend change

### Tips
- Check both desktop and mobile viewport if responsive design matters.
- Open DevTools Network tab to verify API calls are correct.
- Clear cache if changes aren't reflected.

## /team (Team Coordination)

Multi-agent parallel work via shared task list.

### Setup Flow
1. Skill invokes `Skill("oh-my-claudecode:team")`.
2. Team skill handles: team creation, task decomposition, agent spawning.
3. Team-lead assigns tasks and manages agent lifecycle.

### Guidelines for Task Decomposition
- Break work into tasks that touch **separate files** whenever possible.
- Each task should be independently testable.
- Include clear acceptance criteria in task descriptions.
- Estimate relative complexity to balance agent workload.

### Communication
- Agents report status via the task list (TaskUpdate).
- Team-lead monitors and coordinates via messages (SendMessage).
- Use broadcasts sparingly — prefer targeted messages.

## /ralph (Self-Referential Loop)

Iterative development with architect verification at each loop.

### Setup Flow
1. Skill invokes `Skill("oh-my-claudecode:ralph")`.
2. Ralph skill handles: task definition, implementation loop, architect review.
3. Loop continues until architect approves or max iterations reached.

### When to Prefer Over /team
- Single coherent task that benefits from iterative refinement
- Quality-critical work needing architectural oversight
- Tasks where parallelism doesn't help (sequential dependencies)

### Combining with Other Tools
- Use serena within ralph loops for accurate code analysis.
- Use chrome-devtools for live verification at each iteration checkpoint.

## git-master (Atomic Commit Style)

Guidelines for commit discipline. Not directly invoked — applied as rules throughout the session.

### Commit Rules

| Rule | Description |
|------|-------------|
| Atomic | One logical change per commit. A feature + its tests = one commit. An unrelated fix = separate commit. |
| Imperative | Message starts with verb: "Add", "Fix", "Update", "Remove", "Refactor" |
| Why over what | Message explains intent, not mechanics. "Fix auth token expiry check" not "Change line 42" |
| Test first | All tests pass before committing. No broken commits in history. |
| Stage selectively | `git add` specific files. Never `git add -A` without reviewing. |

### Commit Message Format
```
<type>: <concise description>

<optional body explaining why>

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Examples
```
feat: add email validation to signup form

Prevent invalid email formats from reaching the API.
Previously, malformed emails caused 500 errors on the backend.
```

```
fix: resolve race condition in WebSocket reconnection

Multiple reconnection attempts could fire simultaneously when
the connection dropped during a network switch.
```

## build-fix (Build Error Recovery)

Automated build error resolution. Not directly invoked — triggered when build errors occur.

### When It Activates
- TypeScript compilation errors (`tsc --noEmit` failures)
- Build tool errors (webpack, vite, esbuild)
- Lint errors that block the build pipeline

### How to Use
1. When a build error occurs, invoke the `build-fixer` agent: `oh-my-claudecode:build-fixer`.
2. The agent analyzes the error and applies minimal fixes.
3. Review the fix — it should not change architecture or add features.

### Principles
- **Minimal diffs**: Fix only what's broken. No refactoring.
- **No architecture changes**: If the fix requires structural changes, escalate to the user.
- **Preserve intent**: The fix should not alter the intended behavior of the code.

### Common Scenarios

| Error Type | Typical Fix |
|-----------|-------------|
| Missing import | Add the import statement |
| Type mismatch | Correct the type annotation or cast |
| Undefined variable | Fix typo or add declaration |
| Module not found | Install dependency or fix path |
| Syntax error | Fix the syntax issue |
