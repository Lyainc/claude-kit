#!/bin/bash
# =============================================================================
# Claude Kit Manifest Generator
# =============================================================================
#
# Automatically generates .claude-kit-manifest.json from template/ directory
#
# Usage:
#   ./scripts/generate-manifest.sh
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$PROJECT_ROOT/template"
MANIFEST_FILE="$TEMPLATE_DIR/.claude-kit-manifest.json"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ============================================================================
# Hash Calculation Functions
# ============================================================================

# Calculate file hash (compatible with macOS and Linux)
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
    find "$folder" -type f ! -name ".DS_Store" -print0 | \
        sort -z | \
        xargs -0 md5 2>/dev/null | \
        sort | \
        md5 -q 2>/dev/null || echo "unknown"
}

# ============================================================================
# Validation
# ============================================================================

if [ ! -d "$TEMPLATE_DIR" ]; then
    echo -e "${RED}❌ Error: template/ directory not found${NC}"
    echo "Path: $TEMPLATE_DIR"
    exit 1
fi

# Check jq availability (optional but recommended)
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: jq not installed${NC}"
    echo "Install: brew install jq"
    echo "Continuing without pretty-printing..."
    USE_JQ=false
else
    USE_JQ=true
fi

# ============================================================================
# Generate Manifest
# ============================================================================

echo -e "${BLUE}🔨 Generating manifest from template/${NC}" >&2
echo "" >&2

# Get Git info if available
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Start JSON manually
{
    echo "{"
    echo "  \"version\": \"1.0.0\","
    echo "  \"generated_at\": \"$TIMESTAMP\","
    echo "  \"commit\": \"$COMMIT\","
    echo "  \"modules\": {"

    first=true

    # Process skills (folders)
    echo -e "${BLUE}📦 Scanning skills...${NC}" >&2
    for skill_dir in "$TEMPLATE_DIR/skills/"*; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")

        # Skip template
        [[ "$skill_name" == "_TEMPLATE" ]] && continue

        hash=$(folder_hash "$skill_dir")
        echo -e "  ${GREEN}✓${NC} skills/$skill_name (hash: ${hash:0:8}...)" >&2

        # Add comma if not first
        [ "$first" = false ] && echo ","
        first=false

        # Output JSON entry (no trailing comma yet)
        echo -n "    \"skills/$skill_name\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"folder\""
        echo -n " }"
    done

    # Process agents (files)
    echo -e "${BLUE}📦 Scanning agents...${NC}" >&2
    for agent_file in "$TEMPLATE_DIR/agents/"*.md; do
        [ -f "$agent_file" ] || continue
        agent_name=$(basename "$agent_file")

        # Skip template
        [[ "$agent_name" == "_TEMPLATE.md" ]] && continue

        hash=$(file_hash "$agent_file")
        rel_path="agents/$agent_name"
        echo -e "  ${GREEN}✓${NC} $rel_path (hash: ${hash:0:8}...)" >&2

        [ "$first" = false ] && echo ","
        first=false

        echo -n "    \"$rel_path\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"file\""
        echo -n " }"
    done

    # Process modules (files)
    echo -e "${BLUE}📦 Scanning modules...${NC}" >&2
    for module_file in "$TEMPLATE_DIR/modules/"*.md; do
        [ -f "$module_file" ] || continue
        module_name=$(basename "$module_file")

        hash=$(file_hash "$module_file")
        rel_path="modules/$module_name"
        echo -e "  ${GREEN}✓${NC} $rel_path (hash: ${hash:0:8}...)" >&2

        [ "$first" = false ] && echo ","
        first=false

        echo -n "    \"$rel_path\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"file\""
        echo -n " }"
    done

    # Process characters (files)
    echo -e "${BLUE}📦 Scanning characters...${NC}" >&2
    for char_file in "$TEMPLATE_DIR/characters/"*.md; do
        [ -f "$char_file" ] || continue
        char_name=$(basename "$char_file")

        # Skip template
        [[ "$char_name" == "_TEMPLATE.md" ]] && continue

        hash=$(file_hash "$char_file")
        rel_path="characters/$char_name"
        echo -e "  ${GREEN}✓${NC} $rel_path (hash: ${hash:0:8}...)" >&2

        [ "$first" = false ] && echo ","
        first=false

        echo -n "    \"$rel_path\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"file\""
        echo -n " }"
    done

    # Process output-styles (files)
    echo -e "${BLUE}📦 Scanning output-styles...${NC}" >&2
    for style_file in "$TEMPLATE_DIR/output-styles/"*.md; do
        [ -f "$style_file" ] || continue
        style_name=$(basename "$style_file")

        # Skip template
        [[ "$style_name" == "_TEMPLATE.md" ]] && continue

        hash=$(file_hash "$style_file")
        rel_path="output-styles/$style_name"
        echo -e "  ${GREEN}✓${NC} $rel_path (hash: ${hash:0:8}...)" >&2

        [ "$first" = false ] && echo ","
        first=false

        echo -n "    \"$rel_path\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"file\""
        echo -n " }"
    done

    # Process commands (files)
    echo -e "${BLUE}📦 Scanning commands...${NC}" >&2
    for cmd_file in "$TEMPLATE_DIR/commands/"*.md; do
        [ -f "$cmd_file" ] || continue
        cmd_name=$(basename "$cmd_file")

        # Skip template
        [[ "$cmd_name" == "_TEMPLATE.md" ]] && continue

        hash=$(file_hash "$cmd_file")
        rel_path="commands/$cmd_name"
        echo -e "  ${GREEN}✓${NC} $rel_path (hash: ${hash:0:8}...)" >&2

        [ "$first" = false ] && echo ","
        first=false

        echo -n "    \"$rel_path\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"file\""
        echo -n " }"
    done

    # Process CLAUDE.md (main config)
    if [ -f "$TEMPLATE_DIR/CLAUDE.md" ]; then
        echo -e "${BLUE}📦 Scanning CLAUDE.md...${NC}" >&2
        hash=$(file_hash "$TEMPLATE_DIR/CLAUDE.md")
        echo -e "  ${GREEN}✓${NC} CLAUDE.md (hash: ${hash:0:8}...)" >&2

        [ "$first" = false ] && echo ","
        first=false

        echo -n "    \"CLAUDE.md\": {"
        echo -n " \"version\": \"1.0.0\","
        echo -n " \"hash\": \"$hash\","
        echo -n " \"type\": \"file\""
        echo -n " }"
    fi

    # Close modules and root
    echo ""
    echo "  }"
    echo "}"

} > "$MANIFEST_FILE"

# Pretty-print with jq if available
if [ "$USE_JQ" = true ]; then
    jq . "$MANIFEST_FILE" > "$MANIFEST_FILE.tmp" && mv "$MANIFEST_FILE.tmp" "$MANIFEST_FILE"
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  ✅ Manifest Generated!                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📄 ${BLUE}Output:${NC} $MANIFEST_FILE"
echo -e "📊 ${BLUE}Commit:${NC} $COMMIT"
echo -e "🕐 ${BLUE}Generated:${NC} $TIMESTAMP"
echo ""

# Count modules
module_count=$(grep -c "\"version\":" "$MANIFEST_FILE" || echo "0")
echo -e "${BLUE}Total modules:${NC} $module_count"
echo ""
