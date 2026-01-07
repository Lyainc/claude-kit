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
FORCE_UPDATE=false
CLEANUP=false
SHOW_DIFF=false

show_help() {
    cat << EOF
🔧 Claude Kit Setup

Usage: $0 [MODE] [OPTIONS]

MODES:
  install       First-time installation (fails if files exist)
  update        Add new files, preserve existing (recommended)
  reset         Replace all files with template (use with caution)
  doctor        Check installation health and integrity

OPTIONS:
  --dry-run       Preview changes without applying
  --force         Skip backups (dangerous!)
  --force-update  Update even user-modified modules (with backup)
  --cleanup       Remove orphaned files not in template/
  --show-diff     Show diff for changed files
  --help, -h      Show this help message

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
        install|update|reset|doctor)
            MODE="$arg"
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --force-update)
            FORCE_UPDATE=true
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
        echo "1) Update (add new files, keep customizations)"
        echo "2) Reset (backup and replace all - removes custom files)"
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
# Manifest System
# ============================================================================

# Check jq availability
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: jq not found. Install: brew install jq${NC}"
    echo "Falling back to hash-only mode..."
    USE_MANIFEST=false
else
    USE_MANIFEST=true
fi

# Load manifests
TEMPLATE_MANIFEST="$TEMPLATE_DIR/.claude-kit-manifest.json"
LOCAL_MANIFEST="$CLAUDE_DIR/.claude-kit-manifest.json"

if [ "$USE_MANIFEST" = true ] && [ ! -f "$TEMPLATE_MANIFEST" ]; then
    echo -e "${YELLOW}⚠️  Warning: Template manifest not found${NC}"
    echo "Run: ./scripts/generate-manifest.sh"
    USE_MANIFEST=false
fi

# Version comparison (using sort -V for semantic versioning)
version_greater() {
    local ver1="$1"
    local ver2="$2"
    [ "$ver1" != "$ver2" ] && [ "$ver1" = "$(echo -e "$ver1\n$ver2" | sort -V | tail -n1)" ]
}

# Get module info from manifest
get_module_version() {
    local manifest="$1"
    local module_path="$2"
    jq -r ".modules[\"$module_path\"].version // \"0.0.0\"" "$manifest" 2>/dev/null || echo "0.0.0"
}

get_module_hash() {
    local manifest="$1"
    local module_path="$2"
    jq -r ".modules[\"$module_path\"].hash // \"\"" "$manifest" 2>/dev/null || echo ""
}

get_module_type() {
    local manifest="$1"
    local module_path="$2"
    jq -r ".modules[\"$module_path\"].type // \"file\"" "$manifest" 2>/dev/null || echo "file"
}

# ============================================================================
# File Processing Functions
# ============================================================================

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

# Calculate folder hash (all files combined)
folder_hash() {
    local folder="$1"
    find "$folder" -type f ! -name ".DS_Store" -print0 2>/dev/null | \
        sort -z | \
        xargs -0 md5 2>/dev/null | \
        sort | \
        md5 -q 2>/dev/null || echo "unknown"
}

# Calculate hash based on type
calculate_hash() {
    local path="$1"
    local type="$2"

    if [ "$type" = "folder" ]; then
        folder_hash "$path"
    else
        file_hash "$path"
    fi
}

# Check if file should be excluded
is_excluded() {
    local path="$1"
    [[ "$path" == *_TEMPLATE* ]] && return 0
    [[ "$(basename "$path")" == ".DS_Store" ]] && return 0
    [[ "$path" == ".claude-kit-manifest.json" ]] && return 0
    return 1
}

# Smart update logic with manifest support
should_update_module() {
    local module_path="$1"
    local src="$TEMPLATE_DIR/$module_path"
    local dest="$CLAUDE_DIR/$module_path"

    # If manifest system not available, fallback to hash-only
    if [ "$USE_MANIFEST" = false ] || [ ! -f "$LOCAL_MANIFEST" ]; then
        # Simple check: if exists and differs, skip (keep existing)
        if [ -e "$dest" ]; then
            return 1  # Skip
        else
            return 0  # Install
        fi
    fi

    # Get module info from manifests
    local module_type=$(get_module_type "$TEMPLATE_MANIFEST" "$module_path")
    local template_version=$(get_module_version "$TEMPLATE_MANIFEST" "$module_path")
    local local_version=$(get_module_version "$LOCAL_MANIFEST" "$module_path")
    local manifest_hash=$(get_module_hash "$LOCAL_MANIFEST" "$module_path")

    # Module doesn't exist locally
    if [ ! -e "$dest" ]; then
        echo "install:$template_version"
        return 0
    fi

    # Calculate current local hash
    local current_hash=$(calculate_hash "$dest" "$module_type")

    # Check if template version is newer
    if version_greater "$template_version" "$local_version"; then
        # Version is newer - check if user has modified
        if [ "$current_hash" = "$manifest_hash" ]; then
            # User hasn't modified - safe to update
            echo "update:$local_version:$template_version"
            return 0
        else
            # User has modified
            if [ "$FORCE_UPDATE" = true ]; then
                echo "force-update:$local_version:$template_version"
                return 0
            else
                echo "skip-modified:$local_version:$template_version"
                return 1
            fi
        fi
    else
        # Same or older version
        if [ "$current_hash" != "$manifest_hash" ] && [ -n "$manifest_hash" ]; then
            echo "modified"
        else
            echo "unchanged"
        fi
        return 1
    fi
}

# Process a module (file or folder) with manifest-aware logic
process_module() {
    local module_path="$1"
    local src="$TEMPLATE_DIR/$module_path"
    local dest="$CLAUDE_DIR/$module_path"
    local module_type=$(get_module_type "$TEMPLATE_MANIFEST" "$module_path")

    # In update mode, use smart logic
    if [ "$MODE" = "update" ]; then
        local update_status=$(should_update_module "$module_path")
        local update_action="${update_status%%:*}"

        case "$update_action" in
            install)
                local version="${update_status#*:}"
                if [ "$DRY_RUN" = true ]; then
                    echo -e "  ${GREEN}➕ [NEW]${NC} $module_path (v$version)"
                else
                    mkdir -p "$(dirname "$dest")"
                    cp -a "$src" "$dest"
                    echo -e "  ${GREEN}➕${NC} $module_path (v$version)"
                fi
                ;;
            update)
                local old_ver=$(echo "$update_status" | cut -d: -f2)
                local new_ver=$(echo "$update_status" | cut -d: -f3)
                if [ "$DRY_RUN" = true ]; then
                    echo -e "  ${CYAN}🔄 [UPDATE]${NC} $module_path (v$old_ver → v$new_ver)"
                else
                    # Backup before update
                    if [ "$FORCE" = false ]; then
                        mkdir -p "$(dirname "$BACKUP_DIR/$module_path")"
                        cp -a "$dest" "$BACKUP_DIR/$module_path"
                    fi
                    cp -a "$src" "$dest"
                    echo -e "  ${CYAN}🔄${NC} $module_path (v$old_ver → v$new_ver)"
                fi
                ;;
            force-update)
                local old_ver=$(echo "$update_status" | cut -d: -f2)
                local new_ver=$(echo "$update_status" | cut -d: -f3)
                if [ "$DRY_RUN" = true ]; then
                    echo -e "  ${MAGENTA}⚡ [FORCE-UPDATE]${NC} $module_path (v$old_ver → v$new_ver)"
                else
                    # Backup user's modifications
                    mkdir -p "$(dirname "$BACKUP_DIR/$module_path")"
                    cp -a "$dest" "$BACKUP_DIR/$module_path"
                    cp -a "$src" "$dest"
                    echo -e "  ${MAGENTA}⚡${NC} $module_path (v$old_ver → v$new_ver) ${YELLOW}(user modified, backed up)${NC}"
                fi
                ;;
            skip-modified)
                local old_ver=$(echo "$update_status" | cut -d: -f2)
                local new_ver=$(echo "$update_status" | cut -d: -f3)
                if [ "$DRY_RUN" = true ]; then
                    echo -e "  ${YELLOW}⏭️  [SKIP]${NC} $module_path ${CYAN}(user modified, v$old_ver, update v$new_ver available)${NC}"
                else
                    echo -e "  ${YELLOW}⏭️${NC} $module_path ${CYAN}(user modified, keeping v$old_ver)${NC}"
                fi
                ;;
            modified)
                # Modified but no update available - silent
                ;;
            unchanged)
                # No changes - silent
                ;;
        esac
    else
        # Install/Reset mode - use original process_file logic
        process_file "$module_path"
    fi
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
                # Skip individual backup in reset mode (already have full backup)
                if [ "$MODE" != "reset" ] && [ "$FORCE" = false ]; then
                    mkdir -p "$(dirname "$BACKUP_DIR/$rel_path")"
                    cp -a "$dest" "$BACKUP_DIR/$rel_path"
                fi
                cp -a "$src" "$dest"

                # Adjust message based on mode
                if [ "$MODE" = "reset" ]; then
                    echo -e "  ${CYAN}🔄${NC} $rel_path"
                elif [ "$FORCE" = true ]; then
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

# Find orphaned files (Bash 3.2 compatible - no process substitution)
find_orphaned_files() {
    local orphaned=()

    if [ ! -d "$CLAUDE_DIR" ]; then
        return 0
    fi

    # For each file in target, check if it exists in template
    find "$CLAUDE_DIR" -type f -print0 2>/dev/null | while IFS= read -r -d '' target_file; do
        local rel_path="${target_file#$CLAUDE_DIR/}"

        # Skip exclusions
        if [[ "$rel_path" == ".claude-kit-version" ]] || [[ "$rel_path" == .backup.* ]]; then
            continue
        fi

        # Check if corresponding template file exists
        local template_file="$TEMPLATE_DIR/$rel_path"
        if [ ! -f "$template_file" ]; then
            echo "$rel_path"
        fi
    done
}

# ============================================================================
# Doctor Mode
# ============================================================================

if [ "$MODE" = "doctor" ]; then
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║            🏥 Installation Health Check                     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    issues_found=0

    # Check if installation exists
    if [ ! -d "$CLAUDE_DIR" ]; then
        echo -e "${RED}❌ Installation not found${NC}"
        echo "   Location: $CLAUDE_DIR"
        echo ""
        echo "Run: ./setup-claude-global.sh install"
        exit 1
    fi

    echo -e "${CYAN}Checking installation integrity...${NC}"
    echo ""

    # Check manifest
    if [ ! -f "$LOCAL_MANIFEST" ]; then
        echo -e "${YELLOW}⚠️  Local manifest not found${NC}"
        echo "   Run 'update' to migrate to manifest system"
        issues_found=$((issues_found + 1))
    else
        echo -e "${GREEN}✓${NC} Local manifest exists"

        # Check manifest validity
        if ! jq empty "$LOCAL_MANIFEST" 2>/dev/null; then
            echo -e "${RED}✗${NC} Manifest is corrupted"
            issues_found=$((issues_found + 1))
        else
            echo -e "${GREEN}✓${NC} Manifest is valid JSON"
        fi
    fi

    # Check template manifest
    if [ ! -f "$TEMPLATE_MANIFEST" ]; then
        echo -e "${RED}✗${NC} Template manifest not found"
        echo "   Run: ./scripts/generate-manifest.sh"
        issues_found=$((issues_found + 1))
    else
        echo -e "${GREEN}✓${NC} Template manifest exists"
    fi

    echo ""

    # Check modules
    if [ "$USE_MANIFEST" = true ] && [ -f "$LOCAL_MANIFEST" ]; then
        echo -e "${CYAN}Checking modules...${NC}"
        echo ""

        missing=0
        modified=0
        updates_available=0

        for module_path in $(jq -r '.modules | keys[]' "$LOCAL_MANIFEST" 2>/dev/null); do
            dest="$CLAUDE_DIR/$module_path"
            module_type=$(get_module_type "$LOCAL_MANIFEST" "$module_path")

            if [ ! -e "$dest" ]; then
                echo -e "${RED}✗${NC} Missing: $module_path"
                missing=$((missing + 1))
            else
                # Check if modified
                local_version=$(get_module_version "$LOCAL_MANIFEST" "$module_path")
                manifest_hash=$(get_module_hash "$LOCAL_MANIFEST" "$module_path")
                current_hash=$(calculate_hash "$dest" "$module_type")

                if [ -f "$TEMPLATE_MANIFEST" ]; then
                    template_version=$(get_module_version "$TEMPLATE_MANIFEST" "$module_path")

                    if version_greater "$template_version" "$local_version"; then
                        if [ "$current_hash" != "$manifest_hash" ]; then
                            echo -e "${YELLOW}⚠️${NC}  $module_path (v$local_version, user modified, update v$template_version available)"
                            modified=$((modified + 1))
                            updates_available=$((updates_available + 1))
                        else
                            echo -e "${CYAN}ℹ️${NC}  $module_path (v$local_version → v$template_version update available)"
                            updates_available=$((updates_available + 1))
                        fi
                    elif [ "$current_hash" != "$manifest_hash" ]; then
                        echo -e "${YELLOW}⚠️${NC}  $module_path (v$local_version, user modified)"
                        modified=$((modified + 1))
                    fi
                fi
            fi
        done

        echo ""
        echo -e "${CYAN}Module Status:${NC}"
        [ $missing -eq 0 ] && echo -e "${GREEN}✓${NC} No missing modules" || echo -e "${RED}✗${NC} $missing missing module(s)"
        [ $modified -eq 0 ] && echo -e "${GREEN}✓${NC} No user modifications" || echo -e "${YELLOW}ℹ️${NC} $modified modified module(s)"
        [ $updates_available -eq 0 ] && echo -e "${GREEN}✓${NC} All modules up to date" || echo -e "${CYAN}ℹ️${NC} $updates_available update(s) available"
    fi

    echo ""

    # Check orphaned files
    orphaned_count=$(find_orphaned_files | wc -l | tr -d ' ')
    if [ "$orphaned_count" -gt 0 ]; then
        echo -e "${YELLOW}ℹ️${NC}  $orphaned_count orphaned file(s) (not in template)"
        echo "   Run with --cleanup to remove"
    else
        echo -e "${GREEN}✓${NC} No orphaned files"
    fi

    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    if [ $issues_found -eq 0 ]; then
        echo -e "${GREEN}║                 ✅ Health Check Passed                       ║${NC}"
    else
        echo -e "${YELLOW}║              ⚠️  Issues Found: $issues_found                          ║${NC}"
    fi
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    exit 0
fi

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

# Reset mode: Full backup before processing
if [ "$MODE" = "reset" ] && [ "$FORCE" = false ] && [ -d "$CLAUDE_DIR" ]; then
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Would create full backup: $BACKUP_DIR${NC}"
        echo ""
    else
        echo -e "${CYAN}📦 Creating full backup of ~/.claude/ ...${NC}"
        cp -a "$CLAUDE_DIR" "$BACKUP_DIR"
        echo -e "${GREEN}✓ Backup saved to: $BACKUP_DIR${NC}"
        echo ""
    fi
fi

# Install mode: Check for existing files FIRST (before processing)
if [ "$MODE" = "install" ]; then
    existing_count=0
    find "$TEMPLATE_DIR" -type f -print0 2>/dev/null | while IFS= read -r -d '' file; do
        rel_path="${file#$TEMPLATE_DIR/}"
        if is_excluded "$rel_path"; then
            continue
        fi
        if [ -e "$CLAUDE_DIR/$rel_path" ]; then
            existing_count=$((existing_count + 1))
            # Can't modify parent shell var from subshell - use exit code instead
            exit 1
        fi
    done

    if [ $? -eq 1 ]; then
        echo ""
        echo -e "${RED}❌ Error: Existing installation detected${NC}"
        echo ""
        echo "Found existing file(s) in ~/.claude/"
        echo ""
        echo "Please use one of these modes instead:"
        echo -e "  ${CYAN}./setup-claude-global.sh update${NC}    # Add new files only"
        echo -e "  ${CYAN}./setup-claude-global.sh reset${NC}     # Backup and replace all"
        echo ""
        exit 1
    fi
fi

# Process files
echo "📁 Processing modules..."
echo ""

# Migration: Create local manifest if it doesn't exist (first run with manifest system)
if [ "$USE_MANIFEST" = true ] && [ ! -f "$LOCAL_MANIFEST" ] && [ -d "$CLAUDE_DIR" ]; then
    echo -e "${CYAN}🔄 Migrating to manifest system...${NC}"
    # Generate manifest for current installation
    if [ "$DRY_RUN" = false ]; then
        {
            echo "{"
            echo "  \"version\": \"1.0.0\","
            echo "  \"generated_at\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
            echo "  \"commit\": \"migration\","
            echo "  \"modules\": {"

            first=true
            # Copy module info from template manifest but with current hashes
            if [ -f "$TEMPLATE_MANIFEST" ]; then
                for module_path in $(jq -r '.modules | keys[]' "$TEMPLATE_MANIFEST"); do
                    module_type=$(get_module_type "$TEMPLATE_MANIFEST" "$module_path")
                    dest_path="$CLAUDE_DIR/$module_path"

                    if [ -e "$dest_path" ]; then
                        current_hash=$(calculate_hash "$dest_path" "$module_type")
                        version=$(get_module_version "$TEMPLATE_MANIFEST" "$module_path")

                        [ "$first" = false ] && echo ","
                        first=false

                        echo -n "    \"$module_path\": {"
                        echo -n " \"version\": \"$version\","
                        echo -n " \"hash\": \"$current_hash\","
                        echo -n " \"type\": \"$module_type\""
                        echo -n " }"
                    fi
                done
            fi

            echo ""
            echo "  }"
            echo "}"
        } > "$LOCAL_MANIFEST"

        # Pretty-print if jq available
        jq . "$LOCAL_MANIFEST" > "$LOCAL_MANIFEST.tmp" 2>/dev/null && \
            mv "$LOCAL_MANIFEST.tmp" "$LOCAL_MANIFEST" || true
    fi
    echo -e "${GREEN}✓ Migration complete${NC}"
    echo ""
fi

# Use manifest-based processing if available
if [ "$USE_MANIFEST" = true ] && [ -f "$TEMPLATE_MANIFEST" ]; then
    # Process modules from manifest
    for module_path in $(jq -r '.modules | keys[]' "$TEMPLATE_MANIFEST" 2>/dev/null); do
        process_module "$module_path"
    done
else
    # Fallback: Process all files
    find "$TEMPLATE_DIR" -type f -print0 2>/dev/null | while IFS= read -r -d '' file; do
        rel_path="${file#$TEMPLATE_DIR/}"
        if ! is_excluded "$rel_path"; then
            process_file "$rel_path"
        fi
    done
fi

# Copy manifest to target after successful update
if [ "$USE_MANIFEST" = true ] && [ "$DRY_RUN" = false ] && [ -f "$TEMPLATE_MANIFEST" ]; then
    cp "$TEMPLATE_MANIFEST" "$LOCAL_MANIFEST"
fi

# Handle orphaned files
if [ "$CLEANUP" = true ]; then
    echo ""
    echo "🧹 Checking for orphaned files..."

    orphaned_count=0
    find_orphaned_files | while IFS= read -r file; do
        orphaned_count=$((orphaned_count + 1))
        if [ $orphaned_count -eq 1 ]; then
            echo ""
            echo -e "${YELLOW}📋 Orphaned files (not in template/):${NC}"
        fi

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

    # Check if we found any (can't use var from subshell)
    if [ "$(find_orphaned_files | wc -l)" -eq 0 ]; then
        echo -e "${GREEN}✓ No orphaned files found${NC}"
    fi
else
    # Count orphaned files without processing
    orphaned_count=$(find_orphaned_files | wc -l | tr -d ' ')
    if [ "$orphaned_count" -gt 0 ]; then
        echo ""
        echo -e "${CYAN}ℹ️  Found $orphaned_count orphaned file(s) not in template/${NC}"
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
