#!/bin/bash
# =============================================================================
# claude-kit 템플릿 검증 스크립트
# =============================================================================
#
# 사용법:
#   ./scripts/validate-templates.sh           # 전체 검증
#   ./scripts/validate-templates.sh --skills  # 스킬만 검증
#   ./scripts/validate-templates.sh --agents  # 에이전트만 검증
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$ROOT_DIR/template"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

errors=0
warnings=0

# 옵션 파싱
VALIDATE_SKILLS=true
VALIDATE_AGENTS=true

for arg in "$@"; do
    case $arg in
        --skills)
            VALIDATE_AGENTS=false
            ;;
        --agents)
            VALIDATE_SKILLS=false
            ;;
        --help|-h)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  --skills   스킬만 검증"
            echo "  --agents   에이전트만 검증"
            echo "  --help     도움말 표시"
            exit 0
            ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              claude-kit 템플릿 검증                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# =============================================================================
# 유틸리티 함수
# =============================================================================

# YAML frontmatter에서 필드 추출
extract_field() {
    local file="$1"
    local field="$2"

    # frontmatter 추출 후 필드 검색
    sed -n '/^---$/,/^---$/p' "$file" | grep "^${field}:" | sed "s/^${field}:[[:space:]]*//" | tr -d '"' | tr -d "'"
}

# name 필드 검증 (공통)
validate_name() {
    local name="$1"
    local file="$2"
    local type="$3"

    # 필수 체크
    if [ -z "$name" ]; then
        echo -e "${RED}ERROR${NC}: $file - 'name' 필드 누락"
        ((errors++))
        return 1
    fi

    # 길이 체크 (64자)
    if [ ${#name} -gt 64 ]; then
        echo -e "${RED}ERROR${NC}: $file - 'name' 64자 초과 (${#name}자)"
        ((errors++))
    fi

    # 형식 체크 (소문자, 숫자, 하이픈)
    if ! echo "$name" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
        echo -e "${RED}ERROR${NC}: $file - 'name' 형식 오류 (소문자/숫자/하이픈만 허용)"
        ((errors++))
    fi

    # 금지어 체크
    if echo "$name" | grep -qiE '(anthropic|claude)'; then
        echo -e "${RED}ERROR${NC}: $file - 'name'에 금지어 포함 (anthropic, claude)"
        ((errors++))
    fi

    return 0
}

# description 필드 검증 (공통)
validate_description() {
    local file="$1"
    local type="$2"

    # description 추출
    local desc
    desc=$(extract_field "$file" "description")

    # 멀티라인 description 처리 (| 로 시작하는 경우)
    if [ -z "$desc" ] || [ "$desc" = "|" ]; then
        desc=$(sed -n '/^---$/,/^---$/p' "$file" | sed -n '/^description:/,/^[a-z_-]*:/p' | grep -v "^description:" | grep -v "^[a-z_-]*:" | tr -d '\n' | sed 's/^[[:space:]]*//')
    fi

    # 필수 체크
    if [ -z "$desc" ]; then
        echo -e "${RED}ERROR${NC}: $file - 'description' 필드 누락"
        ((errors++))
        return 1
    fi

    # 길이 체크 (1024자) - 대략적 체크
    local desc_len=${#desc}
    if [ $desc_len -gt 1024 ]; then
        echo -e "${RED}ERROR${NC}: $file - 'description' 1024자 초과 (~${desc_len}자)"
        ((errors++))
    fi

    return 0
}

# =============================================================================
# 스킬 검증
# =============================================================================

validate_skills() {
    echo "📦 스킬 검증 중..."
    echo ""

    local skill_count=0

    for skill_dir in "$TEMPLATE_DIR"/skills/*/; do
        # _TEMPLATE 제외
        [[ "$skill_dir" == *_TEMPLATE* ]] && continue
        [ ! -d "$skill_dir" ] && continue

        local dir_name=$(basename "$skill_dir")
        local skill_file="$skill_dir/SKILL.md"

        ((skill_count++))

        # SKILL.md 존재 확인
        if [ ! -f "$skill_file" ]; then
            echo -e "${RED}ERROR${NC}: $dir_name/ - SKILL.md 파일 없음"
            ((errors++))
            continue
        fi

        # name 추출 및 검증
        local name
        name=$(extract_field "$skill_file" "name")
        validate_name "$name" "$skill_file" "skill"

        # 디렉토리명과 name 일치 확인
        if [ -n "$name" ] && [ "$name" != "$dir_name" ]; then
            echo -e "${YELLOW}WARN${NC}: $skill_file - 'name'($name)과 디렉토리명($dir_name) 불일치"
            ((warnings++))
        fi

        # description 검증
        validate_description "$skill_file" "skill"

        # 성공 시 출력
        if [ $errors -eq 0 ] || [ -n "$name" ]; then
            echo -e "${GREEN}✓${NC} skills/$dir_name"
        fi
    done

    echo ""
    echo "  스킬 검증 완료: ${skill_count}개"
}

# =============================================================================
# 에이전트 검증
# =============================================================================

validate_agents() {
    echo "🤖 에이전트 검증 중..."
    echo ""

    local agent_count=0

    for agent_file in "$TEMPLATE_DIR"/agents/*.md; do
        # _TEMPLATE 제외
        [[ "$agent_file" == *_TEMPLATE* ]] && continue
        [ ! -f "$agent_file" ] && continue

        local file_name=$(basename "$agent_file" .md)

        ((agent_count++))

        # name 추출 및 검증
        local name
        name=$(extract_field "$agent_file" "name")
        validate_name "$name" "$agent_file" "agent"

        # 파일명과 name 일치 확인
        if [ -n "$name" ] && [ "$name" != "$file_name" ]; then
            echo -e "${YELLOW}WARN${NC}: $agent_file - 'name'($name)과 파일명($file_name) 불일치"
            ((warnings++))
        fi

        # description 검증
        validate_description "$agent_file" "agent"

        # model 검증 (있는 경우)
        local model
        model=$(extract_field "$agent_file" "model")
        if [ -n "$model" ]; then
            case "$model" in
                sonnet|opus|haiku|inherit|claude-*)
                    # 유효한 값
                    ;;
                *)
                    echo -e "${YELLOW}WARN${NC}: $agent_file - 'model' 값 확인 필요: $model"
                    ((warnings++))
                    ;;
            esac
        fi

        # 성공 시 출력
        if [ $errors -eq 0 ] || [ -n "$name" ]; then
            echo -e "${GREEN}✓${NC} agents/$file_name.md"
        fi
    done

    if [ $agent_count -eq 0 ]; then
        echo "  (에이전트 없음)"
    else
        echo ""
        echo "  에이전트 검증 완료: ${agent_count}개"
    fi
}

# =============================================================================
# 메인 실행
# =============================================================================

if [ "$VALIDATE_SKILLS" = true ]; then
    validate_skills
    echo ""
fi

if [ "$VALIDATE_AGENTS" = true ]; then
    validate_agents
    echo ""
fi

# 결과 요약
echo "══════════════════════════════════════════════════════════════"
if [ $errors -gt 0 ]; then
    echo -e "${RED}검증 실패${NC}: 에러 ${errors}개, 경고 ${warnings}개"
    exit 1
elif [ $warnings -gt 0 ]; then
    echo -e "${YELLOW}검증 완료${NC}: 경고 ${warnings}개"
    exit 0
else
    echo -e "${GREEN}검증 성공${NC}: 모든 템플릿 정상"
    exit 0
fi
