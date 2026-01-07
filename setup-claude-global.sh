#!/bin/bash
# =============================================================================
# Claude Kit Setup Script
# =============================================================================
#
# Usage:
#   ./setup-claude-global.sh [MODE] [OPTIONS]
#
# MODES:
#   install       First-time installation (copies all files, warns if exists)
#   update        Update existing installation (adds new files only)
#   reset         Reset to template (backup and replace all)
#
# OPTIONS:
#   --dry-run     Preview changes without applying
#   --force       Skip backups (use with caution)
#   --cleanup     Remove orphaned files not in template/
#   --show-diff   Show diff for changed files
#   --help, -h    Show this help message
#
# =============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/template"
CLAUDE_DIR="$HOME/.claude"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$CLAUDE_DIR.backup.$TIMESTAMP"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# ============================================================================
# Option Parsing
# ============================================================================

MODE=""
DRY_RUN=false
FORCE=false
CLEANUP=false
SHOW_DIFF=false

show_help() {
    cat << EOF
🔧 Claude Kit Setup

Usage: $0 [MODE] [OPTIONS]

MODES:
  install       First-time installation (fails if files exist)
  update        Update mode (adds new files only, keeps existing)
  reset         Reset mode (backup and replace all)

OPTIONS:
  --dry-run     Preview changes without applying
  --force       Skip backups (dangerous!)
  --cleanup     Remove orphaned files not in template/
  --show-diff   Show diff for changed files
  --help, -h    Show this help message

EXAMPLES:
  $0 install                    # First installation
  $0 update --dry-run           # Preview updates
  $0 reset --show-diff          # Reset with diff preview
  $0 update --cleanup           # Update and clean orphaned files

EOF
}

# Parse arguments
for arg in "$@"; do
    case $arg in
        install|update|reset)
            MODE="$arg"
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --cleanup)
            CLEANUP=true
            ;;
        --show-diff)
            SHOW_DIFF=true
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            show_help
            exit 1
            ;;
    esac
done

# ============================================================================
# Interactive Mode (no MODE specified)
# ============================================================================

interactive_mode() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    🔧 Claude Kit Setup                       ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
        echo -e "${YELLOW}Detected existing installation at ~/.claude/${NC}"
        echo ""
        echo "1) Update (add new files only)"
        echo "2) Reset (backup and replace all)"
        echo "3) Dry-run (preview changes)"
        echo "4) Exit"
        echo ""
        read -p "Select (1-4): " choice

        case $choice in
            1)
                MODE="update"
                ;;
            2)
                MODE="reset"
                ;;
            3)
                DRY_RUN=true
                MODE="update"
                ;;
            4)
                echo "Cancelled."
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                exit 1
                ;;
        esac
    else
        echo -e "${GREEN}No existing installation detected.${NC}"
        echo ""
        echo "1) Install (first-time setup)"
        echo "2) Dry-run (preview installation)"
        echo "3) Exit"
        echo ""
        read -p "Select (1-3): " choice

        case $choice in
            1)
                MODE="install"
                ;;
            2)
                DRY_RUN=true
                MODE="install"
                ;;
            3)
                echo "Cancelled."
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                exit 1
                ;;
        esac
    fi

    echo ""
}

if [ -z "$MODE" ]; then
    interactive_mode
fi

# ============================================================================
# Validation
# ============================================================================

# Check template directory exists
if [ ! -d "$TEMPLATE_DIR" ]; then
    echo -e "${RED}❌ Error: template/ directory not found${NC}"
    echo "Path: $TEMPLATE_DIR"
    exit 1
fi

# Validate CLAUDE.md references
validate_claude_md_references() {
    local claude_md="$TEMPLATE_DIR/CLAUDE.md"

    if [ ! -f "$claude_md" ]; then
        return 0
    fi

    local missing_refs=()

    # Extract @~/.claude/... references
    while IFS= read -r line; do
        if [[ $line =~ @(~/.claude/[^[:space:]]+) ]]; then
            local ref="${BASH_REMATCH[1]}"
            local expanded_ref="${ref/#\~/$HOME}"
            local template_path="${TEMPLATE_DIR}/${ref#*/.claude/}"

            # Check if referenced file exists in template
            if [ ! -f "$template_path" ]; then
                missing_refs+=("$ref")
            fi
        fi
    done < "$claude_md"

    if [ ${#missing_refs[@]} -gt 0 ]; then
        echo -e "${RED}❌ Error: CLAUDE.md references missing files:${NC}"
        for ref in "${missing_refs[@]}"; do
            echo -e "   - $ref"
        done
        echo ""
        echo "Fix template/ or use --force-broken to proceed anyway."
        exit 1
    fi
}

# Run validation
echo -e "${CYAN}🔍 Validating template...${NC}"
validate_claude_md_references
echo -e "${GREEN}✓ Validation passed${NC}"
echo ""

# ============================================================================
# File Processing Functions
# ============================================================================

# Safe array assignment (Bash 3.x compatible)
# Usage: read_array_from_command array_name "command"
read_array_from_command() {
    local array_name="$1"
    local command="$2"
    local line
    local i=0

    eval "$array_name=()"

    while IFS= read -r line; do
        eval "${array_name}[$i]=\"\$line\""
        i=$((i + 1))
    done < <(eval "$command")
}

# Calculate file hash
file_hash() {
    if command -v md5 &> /dev/null; then
        md5 -q "$1"
    elif command -v md5sum &> /dev/null; then
        md5sum "$1" | awk '{print $1}'
    else
        # Fallback to file size + modification time
        stat -f "%z-%m" "$1" 2>/dev/null || stat -c "%s-%Y" "$1"
    fi
}

# Check if file should be excluded
is_excluded() {
    local path="$1"
    [[ "$path" == *_TEMPLATE* ]] && return 0
    [[ "$(basename "$path")" == ".DS_Store" ]] && return 0
    return 1
}

# Collect all files from template
collect_template_files() {
    local files=()
    while IFS= read -r -d '' file; do
        local rel_path="${file#$TEMPLATE_DIR/}"
        if ! is_excluded "$rel_path"; then
            files+=("$rel_path")
        fi
    done < <(find "$TEMPLATE_DIR" -type f -print0)
    printf '%s\n' "${files[@]}"
}

# Collect all files from target
collect_target_files() {
    local files=()
    if [ -d "$CLAUDE_DIR" ]; then
        while IFS= read -r -d '' file; do
            local rel_path="${file#$CLAUDE_DIR/}"
            # Exclude .claude-kit-version and backup folders
            if [[ "$rel_path" != ".claude-kit-version" ]] && [[ "$rel_path" != .backup.* ]]; then
                files+=("$rel_path")
            fi
        done < <(find "$CLAUDE_DIR" -type f -print0)
    fi
    printf '%s\n' "${files[@]}"
}

# Process a single file based on mode
process_file() {
    local rel_path="$1"
    local src="$TEMPLATE_DIR/$rel_path"
    local dest="$CLAUDE_DIR/$rel_path"
    local action=""

    # Determine action based on mode
    if [ "$MODE" = "install" ] || [ "$MODE" = "reset" ]; then
        if [ -e "$dest" ]; then
            action="replace"
        else
            action="add"
        fi
    elif [ "$MODE" = "update" ]; then
        if [ -e "$dest" ]; then
            # Check if content differs
            local src_hash=$(file_hash "$src")
            local dest_hash=$(file_hash "$dest")

            if [ "$src_hash" != "$dest_hash" ]; then
                if [ "$SHOW_DIFF" = true ]; then
                    echo -e "${CYAN}📝 Diff for $rel_path:${NC}"
                    diff -u "$dest" "$src" || true
                    echo ""
                fi
                action="skip"  # In update mode, keep existing
            else
                action="unchanged"
            fi
        else
            action="add"
        fi
    fi

    # Execute action
    case $action in
        add)
            if [ "$DRY_RUN" = true ]; then
                echo -e "  ${GREEN}➕ [NEW]${NC} $rel_path"
            else
                mkdir -p "$(dirname "$dest")"
                cp -a "$src" "$dest"
                echo -e "  ${GREEN}➕${NC} $rel_path"
            fi
            ;;
        replace)
            if [ "$DRY_RUN" = true ]; then
                echo -e "  ${CYAN}🔄 [REPLACE]${NC} $rel_path"
            else
                if [ "$FORCE" = false ]; then
                    mkdir -p "$(dirname "$BACKUP_DIR/$rel_path")"
                    cp -a "$dest" "$BACKUP_DIR/$rel_path"
                fi
                cp -a "$src" "$dest"
                if [ "$FORCE" = true ]; then
                    echo -e "  ${CYAN}🔄${NC} $rel_path ${YELLOW}(forced)${NC}"
                else
                    echo -e "  ${CYAN}🔄${NC} $rel_path ${YELLOW}(backed up)${NC}"
                fi
            fi
            ;;
        skip)
            if [ "$DRY_RUN" = true ]; then
                echo -e "  ${YELLOW}⏭️  [SKIP]${NC} $rel_path ${CYAN}(exists, differs)${NC}"
            else
                echo -e "  ${YELLOW}⏭️${NC} $rel_path ${CYAN}(keeping existing)${NC}"
            fi
            ;;
        unchanged)
            # Silently skip unchanged files
            ;;
    esac
}

# Find orphaned files
find_orphaned_files() {
    local template_files=()
    local target_files=()
    read_array_from_command template_files "collect_template_files"
    read_array_from_command target_files "collect_target_files"
    local orphaned=()

    for target_file in "${target_files[@]}"; do
        local found=false
        for template_file in "${template_files[@]}"; do
            if [ "$target_file" = "$template_file" ]; then
                found=true
                break
            fi
        done
        if [ "$found" = false ]; then
            orphaned+=("$target_file")
        fi
    done

    printf '%s\n' "${orphaned[@]}"
}

# ============================================================================
# Main Processing
# ============================================================================

# Header
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN] Preview of changes:${NC}"
else
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║               🚀 Processing Installation                    ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
fi
echo ""
echo "Mode: $MODE"
echo "Source: $TEMPLATE_DIR"
echo "Target: $CLAUDE_DIR"
echo ""

# Create target directory if needed
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$CLAUDE_DIR"
fi

# Process files
echo "📁 Processing files..."
echo ""

template_files=()
read_array_from_command template_files "collect_template_files"

# Install mode: Check for existing files first
if [ "$MODE" = "install" ]; then
    existing_count=0
    for rel_path in "${template_files[@]}"; do
        if [ -e "$CLAUDE_DIR/$rel_path" ]; then
            existing_count=$((existing_count + 1))
        fi
    done

    if [ $existing_count -gt 0 ]; then
        echo ""
        echo -e "${RED}❌ Error: Existing installation detected${NC}"
        echo ""
        echo "Found $existing_count existing file(s) in ~/.claude/"
        echo ""
        echo "Please use one of these modes instead:"
        echo -e "  ${CYAN}./setup-claude-global.sh update${NC}    # Add new files only"
        echo -e "  ${CYAN}./setup-claude-global.sh reset${NC}     # Backup and replace all"
        echo ""
        exit 1
    fi
fi

for rel_path in "${template_files[@]}"; do
    process_file "$rel_path"
done

# Handle orphaned files
if [ "$CLEANUP" = true ]; then
    echo ""
    echo "🧹 Checking for orphaned files..."
    orphaned_files=()
    read_array_from_command orphaned_files "find_orphaned_files"

    if [ ${#orphaned_files[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}📋 Orphaned files (not in template/):${NC}"
        for file in "${orphaned_files[@]}"; do
            if [ "$DRY_RUN" = true ]; then
                echo -e "  ${RED}🗑️  [DELETE]${NC} $file"
            else
                if [ "$FORCE" = false ]; then
                    mkdir -p "$(dirname "$BACKUP_DIR/$file")"
                    cp -a "$CLAUDE_DIR/$file" "$BACKUP_DIR/$file"
                fi
                rm -f "$CLAUDE_DIR/$file"
                echo -e "  ${RED}🗑️${NC} $file ${YELLOW}(removed)${NC}"
            fi
        done
    else
        echo -e "${GREEN}✓ No orphaned files found${NC}"
    fi
else
    orphaned_files=()
    read_array_from_command orphaned_files "find_orphaned_files"
    if [ ${#orphaned_files[@]} -gt 0 ]; then
        echo ""
        echo -e "${CYAN}ℹ️  Found ${#orphaned_files[@]} orphaned file(s) not in template/${NC}"
        echo -e "   Run with --cleanup to remove them."
    fi
fi

# Clean up .DS_Store
if [ "$DRY_RUN" = false ]; then
    find "$CLAUDE_DIR" -name ".DS_Store" -delete 2>/dev/null || true
fi

# Clean up empty backup directory
if [ "$DRY_RUN" = false ] && [ -d "$BACKUP_DIR" ]; then
    if [ -z "$(ls -A "$BACKUP_DIR")" ]; then
        rm -rf "$BACKUP_DIR"
    else
        echo ""
        echo -e "${YELLOW}📦 Backup location:${NC} $BACKUP_DIR"
    fi
fi

# ============================================================================
# Completion Message
# ============================================================================

echo ""
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                  Dry-run completed                           ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "To apply these changes, run without --dry-run:"
    echo -e "  ${CYAN}$0 $MODE${NC}"
else
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  ✅ Installation Complete!                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📁 ${BLUE}Install location:${NC} $CLAUDE_DIR"

    if [ -d "$BACKUP_DIR" ]; then
        echo -e "💾 ${BLUE}Backups saved to:${NC} $BACKUP_DIR"
    fi

    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  Next Steps                                                  ║${NC}"
    echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  1. Restart Claude Code                                      ║${NC}"
    echo -e "${YELLOW}║  2. Test: \"안녕, 자기소개 해줘\"                                  ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
fi
echo ""
