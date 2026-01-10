# Git Hooks (Optional)

This directory contains optional Git hooks for enhanced safety in multi-agent workflows.

## Available Hooks

### pre-push

Prevents pushing to main when local branch has diverged from remote.

**Installation** (optional, not recommended):

```bash
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Recommendation

**We do NOT recommend using hooks** for this project. Instead, use the automation scripts:

- `./scripts/new-branch.sh` - Create branches
- `./scripts/safe-merge.sh` - Merge safely (REQUIRED)

The `safe-merge.sh` script already includes all safety checks that the hook provides, without the complexity of hook management.

## When to Use Hooks

Consider using hooks only if:

- Team size grows beyond 5+ developers
- Junior developers frequently make mistakes
- Multiple different workflows coexist
- You cannot enforce script usage

For current project scale (1 developer + agents), hooks add unnecessary complexity.
