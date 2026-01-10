#!/usr/bin/env bash
# Safe merge script for multi-agent Git workflow
# Usage: ./scripts/safe-merge.sh <branch-name> [--yes|-y]
# Options:
#   --yes, -y: Skip confirmation prompt

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if branch name is provided
if [ $# -eq 0 ]; then
    log_error "Usage: $0 <branch-name>"
    exit 1
fi

BRANCH_NAME="$1"
MAIN_BRANCH="main"

# Verify we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

# Check if branch exists
if ! git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    log_error "Branch '$BRANCH_NAME' does not exist"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    log_error "You have uncommitted changes. Commit or stash them first."
    git status --short
    exit 1
fi

log_info "Starting safe merge process for branch: $BRANCH_NAME"
echo ""
echo "This script will:"
echo "  1. Fetch latest from remote"
echo "  2. Check for diverged branches"
echo "  3. Test merge for conflicts"
echo "  4. Merge to main (--no-ff)"
echo "  5. Push to remote"
echo "  6. Delete branch (local + remote)"
echo ""

# Interactive confirmation (optional - can be disabled with --yes flag)
if [[ "${2:-}" != "--yes" ]] && [[ "${2:-}" != "-y" ]]; then
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Merge cancelled by user"
        exit 0
    fi
fi

# Step 1: Fetch latest from remote
log_info "Fetching latest changes from remote..."
git fetch origin

# Step 2: Switch to main branch
log_info "Switching to $MAIN_BRANCH..."
git checkout "$MAIN_BRANCH"

# Step 3: Check if main has diverged from remote
LOCAL_MAIN=$(git rev-parse "$MAIN_BRANCH")
REMOTE_MAIN=$(git rev-parse "origin/$MAIN_BRANCH")

if [ "$LOCAL_MAIN" != "$REMOTE_MAIN" ]; then
    # Check if we can fast-forward
    MERGE_BASE=$(git merge-base "$MAIN_BRANCH" "origin/$MAIN_BRANCH")

    if [ "$MERGE_BASE" = "$LOCAL_MAIN" ]; then
        # We're behind, can fast-forward
        log_warn "Local main is behind remote. Fast-forwarding..."
        git pull origin "$MAIN_BRANCH"
    elif [ "$MERGE_BASE" = "$REMOTE_MAIN" ]; then
        # Remote is behind (shouldn't happen normally)
        log_warn "Remote main is behind local. This is unusual."
    else
        # Diverged - conflict situation
        log_error "Local and remote main have diverged!"
        log_error "Another agent may have pushed changes."
        log_error "Please run: git pull origin $MAIN_BRANCH"
        exit 1
    fi
fi

# Step 4: Check if feature branch can be merged cleanly
log_info "Checking if merge will be clean..."
if ! git merge --no-commit --no-ff "$BRANCH_NAME" > /dev/null 2>&1; then
    log_error "Merge conflicts detected!"
    log_error "Please resolve conflicts manually:"
    log_error "  1. git merge $BRANCH_NAME"
    log_error "  2. Resolve conflicts"
    log_error "  3. git commit"
    log_error "  4. git push origin $MAIN_BRANCH"
    git merge --abort
    exit 1
fi

# Abort the test merge
git merge --abort

# Step 5: Perform actual merge with --no-ff
log_info "Merging $BRANCH_NAME into $MAIN_BRANCH (--no-ff)..."
git merge --no-ff "$BRANCH_NAME" -m "Merge branch '$BRANCH_NAME' into $MAIN_BRANCH"

# Step 6: Push to remote
log_info "Pushing to origin/$MAIN_BRANCH..."
if ! git push origin "$MAIN_BRANCH"; then
    log_error "Push failed! Another agent may have pushed meanwhile."
    log_error "Your merge is committed locally. You can:"
    log_error "  1. git pull --rebase origin $MAIN_BRANCH"
    log_error "  2. git push origin $MAIN_BRANCH"
    exit 1
fi

# Step 7: Delete local branch
log_info "Deleting local branch $BRANCH_NAME..."
git branch -d "$BRANCH_NAME"

# Step 8: Delete remote branch (if exists)
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME"; then
    log_info "Deleting remote branch origin/$BRANCH_NAME..."
    git push origin --delete "$BRANCH_NAME"
fi

log_info "✓ Merge completed successfully!"
log_info "✓ Branch $BRANCH_NAME has been merged and deleted"
