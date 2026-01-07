#!/usr/bin/env bash
set -euo pipefail

# Git Hooks Installer for claude-kit
# Installs advisory hooks to help prevent multi-session conflicts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Installing Git Hooks for claude-kit...${NC}\n"

# Check if .git directory exists
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${YELLOW}Error: Not a git repository${NC}"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# ============================================================
# Pre-commit Hook
# ============================================================
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/usr/bin/env bash
# Advisory pre-commit hook for claude-kit
# Warns about remote changes but doesn't block commit

# Colors
YELLOW='\033[1;33m'
NC='\033[0m'

# Fetch remote status (quietly)
git fetch origin --dry-run 2>&1 | grep -q "new" || true

if [ $? -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Warning: Remote has new commits.${NC}"
    echo -e "${YELLOW}   Consider running 'git pull' before committing.${NC}"
    echo ""
fi

# Always allow commit (advisory only)
exit 0
EOF

chmod +x "$HOOKS_DIR/pre-commit"
echo -e "${GREEN}✓${NC} Installed: pre-commit (warns about remote changes)"

# ============================================================
# Post-merge Hook
# ============================================================
cat > "$HOOKS_DIR/post-merge" << 'EOF'
#!/usr/bin/env bash
# Advisory post-merge hook for claude-kit
# Reminds to delete merged branches

# Colors
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}✓ Merge complete!${NC}"
echo ""
echo "Don't forget to delete the merged branch:"
echo "  git branch -d <branch-name>"
echo "  git push origin --delete <branch-name>"
echo ""
EOF

chmod +x "$HOOKS_DIR/post-merge"
echo -e "${GREEN}✓${NC} Installed: post-merge (reminds to delete branches)"

# ============================================================
# Pre-push Hook
# ============================================================
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/usr/bin/env bash
# Advisory pre-push hook for claude-kit
# Warns if pushing to main without being up-to-date

# Get current branch
current_branch=$(git symbolic-ref --short HEAD)

if [ "$current_branch" = "main" ]; then
    # Check if local main is behind remote
    git fetch origin main --quiet
    LOCAL=$(git rev-parse main)
    REMOTE=$(git rev-parse origin/main)

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo ""
        echo "⚠️  Warning: Your local 'main' is not up-to-date with 'origin/main'"
        echo "   Consider pulling first: git pull origin main"
        echo ""
        read -p "Continue pushing anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"
echo -e "${GREEN}✓${NC} Installed: pre-push (checks main is up-to-date)"

# ============================================================
# Summary
# ============================================================
echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo -e "${GREEN}Git Hooks Installation Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""
echo "Installed hooks:"
echo "  • pre-commit  - Warns about remote changes"
echo "  • post-merge  - Reminds to delete branches"
echo "  • pre-push    - Checks main is up-to-date"
echo ""
echo "These are advisory hooks - they won't block your work,"
echo "just provide helpful reminders."
echo ""
echo "To uninstall, run:"
echo "  rm .git/hooks/pre-commit .git/hooks/post-merge .git/hooks/pre-push"
echo ""
