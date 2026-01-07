#!/bin/bash
# =============================================================================
# claude-kit 설치/업데이트 스크립트
# =============================================================================
#
# 사용법:
#   curl -fsSL https://raw.githubusercontent.com/USERNAME/claude-kit/main/install.sh | bash
#   curl -fsSL ... | bash -s -- --dry-run    # 미리보기
#   curl -fsSL ... | bash -s -- --force      # 강제 덮어쓰기
#
# =============================================================================

set -e

# 설정
REPO_URL="${CLAUDE_KIT_REPO:-https://github.com/Lyainc/claude-kit.git}"
INSTALL_DIR="${CLAUDE_KIT_DIR:-$HOME/.claude-kit}"
CLAUDE_DIR="$HOME/.claude"

# 색상
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    claude-kit installer                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Git 확인
if ! command -v git &> /dev/null; then
    echo -e "${RED}오류: git이 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 설치 또는 업데이트
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}기존 설치 발견. 업데이트 중...${NC}"
    cd "$INSTALL_DIR"

    # 로컬 변경사항 확인
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}로컬 변경사항이 있습니다. stash 후 업데이트합니다.${NC}"
        git stash
        git pull --rebase
        git stash pop 2>/dev/null || true
    else
        git pull --rebase
    fi
else
    echo -e "${GREEN}새로 설치 중...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo ""

# 설치 스크립트 실행
./setup-claude-global.sh "$@"

# 버전 정보 기록
mkdir -p "$CLAUDE_DIR"
cat > "$CLAUDE_DIR/.claude-kit-version" << EOF
{
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "commit": "$(git rev-parse HEAD)",
  "branch": "$(git branch --show-current)",
  "source": "$INSTALL_DIR"
}
EOF

echo ""
echo -e "${GREEN}버전 정보가 기록되었습니다: ~/.claude/.claude-kit-version${NC}"
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  유용한 명령어                                                 ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║  업데이트:  동일한 curl 명령어 재실행                            ║${NC}"
echo -e "${BLUE}║  설정 편집: cd ~/.claude-kit && code .                        ║${NC}"
echo -e "${BLUE}║  재설치:    ~/.claude-kit/setup-claude-global.sh              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
