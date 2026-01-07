#!/bin/bash
# =============================================================================
# Claude Code 글로벌 설정 설치 스크립트 (선택적 병합 방식)
# =============================================================================
#
# 사용법:
#   ./setup-claude-global.sh              # 기본 설치 (기존 파일만 백업)
#   ./setup-claude-global.sh --dry-run    # 실제 설치 없이 미리보기
#   ./setup-claude-global.sh --force      # 백업 없이 덮어쓰기
#
# 동작 방식:
#   - ~/.claude/ 폴더의 기존 내용물은 모두 유지
#   - template/에서 복사할 파일만 선택적으로 병합
#   - 덮어쓸 파일이 이미 존재하면 해당 파일만 백업
#
# =============================================================================

set -e

# 스크립트 위치 기준 template 경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/template"
CLAUDE_DIR="$HOME/.claude"

# 옵션 파싱
DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --version|-v)
            if [ -f "$HOME/.claude/.claude-kit-version" ]; then
                cat "$HOME/.claude/.claude-kit-version"
            else
                echo "버전 정보 없음 (install.sh로 설치 시 기록됨)"
            fi
            exit 0
            ;;
        --help|-h)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  --dry-run      실제 설치 없이 미리보기"
            echo "  --force        백업 없이 덮어쓰기"
            echo "  --version, -v  설치된 버전 정보 표시"
            echo "  --help, -h     이 도움말 표시"
            echo ""
            echo "동작 방식:"
            echo "  - ~/.claude/ 내 기존 파일들은 모두 유지"
            echo "  - template/의 파일들만 선택적으로 병합"
            echo "  - 덮어쓸 기존 파일이 있으면 개별 백업"
            exit 0
            ;;
    esac
done

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Claude Code 글로벌 설정 설치 (선택적 병합)                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# template 폴더 존재 확인
if [ ! -d "$TEMPLATE_DIR" ]; then
    echo -e "${RED}오류: template/ 폴더를 찾을 수 없습니다.${NC}"
    echo "경로: $TEMPLATE_DIR"
    exit 1
fi

# ~/.claude 디렉토리 생성 (없는 경우)
mkdir -p "$CLAUDE_DIR"

# 백업 타임스탬프
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$CLAUDE_DIR.file-backups.$TIMESTAMP"

# 파일 복사 함수 (재귀적)
# $1: 소스 경로
# $2: 대상 경로
# $3: 상대 경로 (로깅용)
copy_file_with_backup() {
    local src="$1"
    local dest="$2"
    local rel_path="$3"

    # _TEMPLATE 패턴 제외
    if [[ "$rel_path" == *_TEMPLATE* ]]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "  ${YELLOW}⏭️  [제외]${NC} $rel_path"
        fi
        return
    fi

    # Dry-run 모드
    if [ "$DRY_RUN" = true ]; then
        if [ -e "$dest" ]; then
            echo -e "  ${CYAN}🔄 [덮어쓰기]${NC} $rel_path"
        else
            echo -e "  ${GREEN}➕ [새 파일]${NC} $rel_path"
        fi
        return
    fi

    # 실제 복사 로직
    if [ -e "$dest" ] && [ "$FORCE" = false ]; then
        # 기존 파일 백업
        local backup_path="$BACKUP_DIR/$rel_path"
        mkdir -p "$(dirname "$backup_path")"
        cp -a "$dest" "$backup_path"
        echo -e "  ${CYAN}🔄${NC} $rel_path ${YELLOW}(백업됨)${NC}"
    elif [ -e "$dest" ] && [ "$FORCE" = true ]; then
        echo -e "  ${CYAN}🔄${NC} $rel_path ${YELLOW}(강제 덮어쓰기)${NC}"
    else
        echo -e "  ${GREEN}➕${NC} $rel_path"
    fi

    # 파일 복사
    cp -a "$src" "$dest"
}

# 디렉토리 재귀 처리 함수
# $1: 소스 디렉토리
# $2: 대상 디렉토리
# $3: 상대 경로 prefix
process_directory() {
    local src_dir="$1"
    local dest_dir="$2"
    local prefix="$3"

    # 대상 디렉토리 생성
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$dest_dir"
    fi

    # 항목 순회
    for item in "$src_dir"/*; do
        [ -e "$item" ] || continue  # glob 실패 시 건너뛰기

        local basename_item=$(basename "$item")
        local rel_path="$prefix$basename_item"

        # _TEMPLATE 패턴 제외
        if [[ "$basename_item" == _TEMPLATE* ]]; then
            if [ "$DRY_RUN" = true ]; then
                echo -e "  ${YELLOW}⏭️  [제외]${NC} $rel_path"
            fi
            continue
        fi

        if [ -d "$item" ]; then
            # 디렉토리인 경우 재귀 호출
            process_directory "$item" "$dest_dir/$basename_item" "$rel_path/"
        else
            # 파일인 경우 복사
            copy_file_with_backup "$item" "$dest_dir/$basename_item" "$rel_path"
        fi
    done
}

# Dry-run 모드 헤더
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN] 설치될 내용 미리보기:${NC}"
    echo ""
    echo "소스: $TEMPLATE_DIR"
    echo "대상: $CLAUDE_DIR"
    echo ""
    echo "변경 사항:"
else
    echo "📁 설정 파일 병합 중..."
    echo ""
fi

# 메인 복사 프로세스
process_directory "$TEMPLATE_DIR" "$CLAUDE_DIR" ""

# .DS_Store 제거
if [ "$DRY_RUN" = false ]; then
    find "$CLAUDE_DIR" -name ".DS_Store" -delete 2>/dev/null || true
fi

# 빈 백업 디렉토리 제거
if [ "$DRY_RUN" = false ] && [ -d "$BACKUP_DIR" ]; then
    if [ -z "$(ls -A "$BACKUP_DIR")" ]; then
        rm -rf "$BACKUP_DIR"
    else
        echo ""
        echo -e "${YELLOW}📦 백업된 파일 위치:${NC} $BACKUP_DIR"
    fi
fi

# 완료 메시지
echo ""
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}실제 설치하려면 --dry-run 옵션을 제거하세요.${NC}"
else
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✅ 설치 완료!                                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📁 ${BLUE}설치 위치:${NC} $CLAUDE_DIR"
    echo -e "💾 ${BLUE}기존 파일 보존:${NC} 플러그인, 대화 이력 등 모두 유지됨"

    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  다음 단계                                                     ║${NC}"
    echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  1. Claude Code 재시작                                         ║${NC}"
    echo -e "${YELLOW}║  2. 설정 테스트: \"안녕, 자기소개 해줘\"                            ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
fi
