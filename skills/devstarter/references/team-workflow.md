# Team Workflow Reference

Detailed procedures for Team Mode development with multi-agent coordination.

## Git Worktree + Branch Setup

### Initial Setup

When Team Mode starts, the team-lead sets up the workspace:

1. **Create worktrees** for each agent from the main branch:
   ```bash
   git worktree add ../project-agent-1 -b agent-1/task-name main
   git worktree add ../project-agent-2 -b agent-2/task-name main
   ```

2. **Assign working directories**: Each agent operates exclusively in its own worktree. Agents must never modify files in another agent's worktree.

3. **Branch naming convention**: `{agent-name}/{task-summary}` (e.g., `agent-1/add-auth-api`, `agent-2/update-dashboard-ui`).

### Branch Separation Strategy

| Principle | Rule |
|-----------|------|
| One branch per agent | Each agent commits only to its assigned branch |
| No cross-branch edits | Agents do not checkout or modify other branches |
| Merge through team-lead | Only team-lead performs merge/rebase operations |
| Common base | All branches start from the same commit on main |

### File Ownership

To prevent conflicts, the team-lead should partition files before work begins:

1. Identify the files each task will touch.
2. If overlap exists, either:
   - Reassign tasks to eliminate overlap, or
   - Sequence the overlapping tasks (one completes before the other starts).
3. Document ownership in the task descriptions.

## Team-Lead Checkpoint Process

At each agent completion checkpoint, the team-lead performs these checks:

### Physical Conflict Check (Merge Test)

```bash
# From the main worktree:
git checkout main
git merge --no-commit --no-ff agent-1/task-name
# If conflicts arise:
git merge --abort
# Record which files conflict and coordinate resolution
```

Run this for each completed branch against main and against other in-progress branches.

### Logical Conflict Check (Change Review)

Even without merge conflicts, changes can logically conflict. The team-lead reviews:

| Check | What to Look For |
|-------|-----------------|
| API contracts | Did one agent change an interface another agent depends on? |
| Shared state | Did both agents modify the same state/store/config? |
| Import paths | Did one agent move/rename a file another agent imports? |
| Test assumptions | Do tests from one branch assume state that another branch changed? |
| Database schema | Did both agents modify migrations or schema files? |

### Resolution Process

1. **No conflicts**: Merge the completed branch into main.
   ```bash
   git checkout main
   git merge --no-ff agent-1/task-name
   ```

2. **Physical conflict**: Coordinate with both agents. Decide whose changes take priority, merge manually, and run tests.

3. **Logical conflict**: Pause the affected agent. Resolve the logic issue first, then update the agent's branch with the fix before continuing.

### After Merge

After merging a completed branch into main:
```bash
# Update other agents' branches to include the merged changes
git checkout agent-2/task-name
git rebase main
```

This keeps all agents working against the latest integrated codebase.

## Agent Completion Coordination

### Completion Signal

When an agent finishes its task:
1. Agent runs all tests in its worktree and confirms they pass.
2. Agent commits all changes with atomic commit discipline.
3. Agent notifies the team-lead via message: task complete, ready for review.

### Team-Lead Response

1. Run the checkpoint process (physical + logical conflict checks).
2. If clean, merge into main and rebase other agents.
3. Assign next task to the idle agent or shut it down if no tasks remain.

### Staggered Completion

When agents finish at different times:

```
Agent-1 completes → Checkpoint → Merge → Rebase Agent-2
                                       → Assign Agent-1 next task (or shutdown)
Agent-2 completes → Checkpoint → Merge → Assign Agent-2 next task (or shutdown)
```

### Final Integration

After all agents complete:
1. Merge any remaining branches into main.
2. Run the full test suite on main.
3. Clean up worktrees:
   ```bash
   git worktree remove ../project-agent-1
   git worktree remove ../project-agent-2
   git branch -d agent-1/task-name agent-2/task-name
   ```

## Solo Mode vs Team Mode

| Aspect | Solo Mode | Team Mode |
|--------|-----------|-----------|
| Branching | Work on current branch | Worktree per agent |
| Commits | Direct to working branch | Per-agent branches, merged by lead |
| Conflict risk | None | Managed via checkpoints |
| Coordination | N/A | Team-lead orchestrates |
| Test scope | Run before each commit | Run per agent + full suite on merge |
| Complexity | Low | Higher, justified by parallelism |

## Troubleshooting

### Worktree Creation Fails
- Ensure the branch name doesn't already exist: `git branch -D old-branch-name`
- Ensure the target directory doesn't exist: remove stale worktree directories

### Rebase Conflicts After Merge
- If rebasing an agent's branch onto updated main causes conflicts, the team-lead resolves them before the agent continues.
- Never ask an agent to resolve conflicts in files it didn't modify.

### Agent Stuck on Build Error
- Use the `build-fixer` agent to resolve with minimal changes.
- If the error is caused by another agent's merged changes, the team-lead coordinates the fix.
