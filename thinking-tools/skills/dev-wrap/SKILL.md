---
name: dev-wrap

description: |
  This skill should be used when the user asks to "작업 마무리", "커밋 정리",
  "dev wrap", "dev-wrap", "wrap up", "commit changes", or invokes "/dev-wrap".
  Analyzes uncommitted changes, runs verification, organizes into atomic commits,
  and produces a structured handoff summary. Does NOT modify code — only commits.
---

# dev-wrap

Post-work skill: verify uncommitted changes, organize into atomic commits, and produce a handoff summary.

**Key constraint**: This skill does NOT modify code. It only stages, commits, and reports.

**Idempotent**: Based on `git diff` — safe to re-run after code changes (e.g., after /simplify).

## Phase 1: Inventory

Collect all uncommitted changes:

```bash
git status
git diff              # unstaged changes
git diff --cached     # staged changes
```

**If diff is empty**: Print "커밋할 변경사항이 없습니다." and suggest reviewing code quality as a next step. Stop here.

Classify each changed file by logical unit (feature, fix, refactor, test, docs, chore).

## Phase 2: Verify

Run the project's verification commands. Check for these in order and run whichever exist:

| Check | Common commands |
|-------|----------------|
| Test | `npm test`, `pytest`, `go test ./...`, `cargo test` |
| Build | `npm run build`, `tsc --noEmit`, `go build ./...` |
| Lint | `npm run lint`, `ruff check`, `golangci-lint run` |

**On failure**: Stop immediately. Output a detailed error report:

```
[dev-wrap] Verification failed

Command: npm test
Exit code: 1

Error output:
  <full error output here>

Failed files:
  - src/auth/validation.ts:42 — TypeError: ...
```

Do NOT attempt to fix the error. The report should contain enough context for the user or a follow-up agent to resolve it.

## Phase 3: Organize

Group changes into atomic commit units using Conventional Commits types:

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Build, config, dependency changes |

**Rules**:
- One logical change = one commit. A feature + its tests = one commit. An unrelated fix = separate commit.
- If grouping is ambiguous, use AskUserQuestion to confirm the split.
- For large changes (50+ files), adjust atom granularity — broader grouping is acceptable to keep commit count manageable.

## Phase 4: Commit

Execute commits sequentially:

1. Stage only related files per commit (`git add <specific files>`). Never use `git add -A`.
2. Write imperative commit messages — "why over what".
3. Format:
   ```
   <type>: <concise description>

   <optional body explaining why>

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
4. Commits execute automatically. Only ask for confirmation (AskUserQuestion) when the grouping was ambiguous in Phase 3.

## Phase 5: Handoff

Output a structured summary:

```
[dev-wrap complete]

Commits:
  <hash> <type>: <message>
  <hash> <type>: <message>

Summary: <N> files changed, <new/modified/deleted counts> | <N> commits

Changed areas:
  - <path> (<brief context>)
  - <path> (<brief context>)
```

Do NOT suggest specific next skills or commands. The changed-areas context enables natural routing by the agent.
