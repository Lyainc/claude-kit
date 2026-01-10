#!/usr/bin/env bash
# Branch creation helper with timestamp
# Usage: ./scripts/new-branch.sh <type> <description>
# Example: ./scripts/new-branch.sh feature add-new-skill

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check arguments
if [ $# -lt 2 ]; then
    log_error "Usage: $0 <type> <description>"
    echo ""
    echo "Examples:"
    echo "  $0 feature add-new-skill"
    echo "  $0 fix typo-in-readme"
    echo "  $0 docs update-workflow"
    echo ""
    echo "Valid types: feature, fix, docs, refactor, test, chore"
    exit 1
fi

TYPE="$1"
DESCRIPTION="$2"

# Validate type
VALID_TYPES=("feature" "fix" "docs" "refactor" "test" "chore")
if [[ ! " ${VALID_TYPES[@]} " =~ " ${TYPE} " ]]; then
    log_error "Invalid type: $TYPE"
    echo "Valid types: ${VALID_TYPES[*]}"
    exit 1
fi

# Generate timestamp (YYYYMMDD-HHMM)
TIMESTAMP=$(date +"%Y%m%d-%H%M")

# Create branch name
BRANCH_NAME="${TYPE}/${TIMESTAMP}-${DESCRIPTION}"

# Verify we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

# Sync with remote
log_info "Syncing with remote..."
git fetch origin

# Switch to main and update
log_info "Updating main branch..."
git checkout main
git pull origin main

# Create new branch
log_info "Creating branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

log_info "✓ Branch created successfully!"
log_info "Branch name: $BRANCH_NAME"
echo ""
log_info "When done, merge with:"
echo "  ./scripts/safe-merge.sh $BRANCH_NAME"
