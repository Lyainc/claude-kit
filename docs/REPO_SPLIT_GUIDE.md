# Repository Split Guide

claude-kit에서 개발 워크플로우 템플릿을 별도 레포로 분리하는 가이드입니다.

## 배경

현재 claude-kit 레포에는 두 가지 성격의 코드가 혼재되어 있습니다:

1. **claude-kit 고유 기능**: Template validation, manifest integrity (이 레포에 유지)
2. **재사용 가능한 개발 도구**: Generic git hooks, CI patterns (분리 대상)

## 분리 시점 판단

다음 중 **하나라도 해당**되면 분리를 고려하세요:

- [ ] 다른 개발 프로젝트에서 hooks/CI를 재사용하고 싶을 때
- [ ] 외부 기여자가 "이 템플릿을 내 프로젝트에 쓰고 싶다" 요청
- [ ] Python/TypeScript 등 다른 언어 템플릿 추가 계획
- [ ] claude-kit 이슈 트래커에 워크플로우 관련 이슈가 섞여서 혼란

## 분리 대상 분석

### ✅ 별도 레포로 이동할 파일

| 파일 | 분류 | 이유 |
|------|------|------|
| `scripts/setup-hooks.sh` | 일부 재사용 가능 | Generic hook 구조는 재사용 가능 |
| `.pre-commit-config.yaml` | 재사용 가능 | 일반적인 pre-commit 패턴 |
| `CONTRIBUTING.md` | 일부 재사용 가능 | Git workflow 설명 부분만 |
| `.github/workflows/validate.yml` | 일부 재사용 가능 | 구조는 재사용, 로직은 커스터마이징 |

### ❌ claude-kit에 유지할 파일

| 파일 | 이유 |
|------|------|
| `scripts/validate-templates.sh` | claude-kit 전용 (SKILL.md 검증) |
| `scripts/generate-manifest.sh` | claude-kit 전용 (manifest 관리) |
| `.github/workflows/validate.yml` 내 template 검증 | claude-kit 전용 로직 |

## 분리 절차

### Phase 1: 새 레포 생성

```bash
# 1. GitHub에서 새 레포 생성
# Repository name: dev-workflow-template
# Description: Generic development workflow templates (hooks, CI, git workflow)

# 2. 로컬 클론
cd ~/projects
git clone https://github.com/Lyainc/dev-workflow-template.git
cd dev-workflow-template
```

### Phase 2: 템플릿 구조 생성

```bash
# 기본 구조
mkdir -p .github/workflows
mkdir -p scripts

# README 작성
cat > README.md << 'EOF'
# Dev Workflow Template

Generic development workflow template for any project.

## Quick Start

\`\`\`bash
# Clone this template
git clone https://github.com/Lyainc/dev-workflow-template.git my-project
cd my-project

# Run setup
./setup.sh

# Initialize your own git
rm -rf .git
git init
\`\`\`

## Features

- Pre-commit hooks (validation, linting)
- GitHub Actions CI/CD
- Branch workflow scripts
- Contributing guidelines

## Customization

Edit these files for your project:
- `.github/workflows/*.yml`: CI triggers and jobs
- `scripts/setup-hooks.sh`: Hook logic
- `CONTRIBUTING.md`: Project-specific guidelines

## License

MIT
EOF
```

### Phase 3: 파일 추출 및 일반화

#### 3.1. setup-hooks.sh 일반화

```bash
# claude-kit 버전에서 복사
cp ~/projects/claude-kit/scripts/setup-hooks.sh scripts/

# 일반화 작업
vim scripts/setup-hooks.sh
```

**제거할 부분**:
- Template validation 로직 (claude-kit 전용)
- Manifest integrity check (claude-kit 전용)

**유지할 부분**:
- Hook 설치 구조 (native vs pre-commit)
- Generic validation 패턴

#### 3.2. CI Workflow 일반화

```bash
cp ~/projects/claude-kit/.github/workflows/validate.yml .github/workflows/

# 일반화: template 검증 제거, generic linting 추가
vim .github/workflows/validate.yml
```

**변경 예시**:
```yaml
# Before (claude-kit 전용)
- name: Validate templates
  run: ./scripts/validate-templates.sh

# After (generic)
- name: Run linter
  run: |
    # Add your linting commands
    # Example: npm run lint
    echo "Add your linting here"
```

#### 3.3. CONTRIBUTING.md 추출

```bash
# claude-kit 버전에서 Git workflow 부분만 추출
cat > CONTRIBUTING.template.md << 'EOF'
# Contributing Guidelines

## Git Workflow

[claude-kit의 CONTRIBUTING.md에서 Git workflow 섹션 복사]

## Customization

Replace PROJECT_NAME with your actual project name.
EOF
```

### Phase 4: Setup Script 작성

```bash
cat > setup.sh << 'EOF'
#!/bin/bash
# Project initialization script

set -e

echo "🔧 Setting up development workflow..."
echo ""

# 1. Get project info
read -p "Project name: " PROJECT_NAME
read -p "Repository URL: " REPO_URL

# 2. Replace placeholders
find . -type f -not -path "./.git/*" -exec sed -i.bak "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" {} \;
find . -type f -not -path "./.git/*" -exec sed -i.bak "s|{{REPO_URL}}|$REPO_URL|g" {} \;
find . -name "*.bak" -delete

# 3. Install hooks (optional)
read -p "Install git hooks? (y/n): " INSTALL_HOOKS
if [ "$INSTALL_HOOKS" = "y" ]; then
    ./scripts/setup-hooks.sh
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Review and customize .github/workflows/"
echo "  2. Update CONTRIBUTING.md for your project"
echo "  3. git init && git add . && git commit -m 'Initial commit'"
echo ""
EOF

chmod +x setup.sh
```

### Phase 5: 문서화

```bash
# Installation guide
cat > INSTALL.md << 'EOF'
# Installation Guide

## Method 1: Git Clone (Recommended)

\`\`\`bash
git clone https://github.com/Lyainc/dev-workflow-template.git my-project
cd my-project
./setup.sh
\`\`\`

## Method 2: Download ZIP

1. Download from GitHub: [Releases](https://github.com/Lyainc/dev-workflow-template/releases)
2. Extract to your project folder
3. Run `./setup.sh`

## What Gets Installed

- `.github/workflows/`: CI/CD workflows
- `scripts/`: Development scripts
- `.pre-commit-config.yaml`: Pre-commit hooks config
- `CONTRIBUTING.md`: Contributor guidelines (template)

## Customization

After installation, customize these files:
- **Required**: Update `CONTRIBUTING.md` with project-specific info
- **Optional**: Modify CI workflows in `.github/workflows/`
- **Optional**: Adjust hook behavior in `scripts/setup-hooks.sh`
EOF
```

### Phase 6: 초기 커밋 및 릴리스

```bash
git add .
git commit -m "feat: Initial dev workflow template

Features:
- Generic git hooks setup
- GitHub Actions CI/CD template
- Branch workflow scripts
- Contributing guidelines template

Usage:
  git clone https://github.com/Lyainc/dev-workflow-template.git
  cd dev-workflow-template
  ./setup.sh
"

git push origin main

# Tag release
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

## Phase 7: claude-kit 업데이트

### 7.1. README에 링크 추가

```bash
cd ~/projects/claude-kit
```

`README.md`에 추가:

```markdown
## Related Projects

- **[dev-workflow-template](https://github.com/Lyainc/dev-workflow-template)**: Generic development workflow template (git hooks, CI/CD, branch workflow) - extracted from claude-kit for reusable use in any project.
```

### 7.2. CLAUDE.md 업데이트

`CLAUDE.md`의 Git Workflow 섹션에 추가:

```markdown
## Git Workflow

**Note**: This project uses custom validation hooks specific to claude-kit (template validation, manifest integrity). For a **generic version** suitable for any project, see [dev-workflow-template](https://github.com/Lyainc/dev-workflow-template).

[... 기존 내용 ...]
```

### 7.3. CONTRIBUTING.md 업데이트

```markdown
## Alternative: Generic Template

If you're looking for a generic development workflow template (without claude-kit-specific validation), check out [dev-workflow-template](https://github.com/Lyainc/dev-workflow-template).
```

## 체크리스트

분리 작업 전 확인:

- [ ] 새 레포 생성 (GitHub)
- [ ] 로컬 클론
- [ ] 템플릿 구조 생성
- [ ] claude-kit에서 파일 추출
- [ ] claude-kit 전용 로직 제거
- [ ] setup.sh 작성
- [ ] README.md 작성
- [ ] INSTALL.md 작성
- [ ] 초기 커밋 및 릴리스 태그
- [ ] claude-kit README 링크 추가
- [ ] claude-kit CLAUDE.md 링크 추가
- [ ] claude-kit CONTRIBUTING.md 링크 추가
- [ ] 양쪽 레포 테스트

## 유지보수 전략

분리 후:

1. **독립 진화**: 각 레포는 독립적으로 버전 관리
2. **개선사항 공유**:
   - claude-kit에서 개선 → dev-workflow-template에 수동 반영 (선택)
   - dev-workflow-template에서 개선 → claude-kit에 수동 반영 (선택)
3. **이슈 관리**:
   - claude-kit 이슈: Template/manifest 관련
   - dev-workflow-template 이슈: 일반 워크플로우 관련

## 예상 소요 시간

- **Phase 1-2**: 30분 (레포 생성, 구조 설정)
- **Phase 3**: 1-2시간 (파일 추출 및 일반화)
- **Phase 4-5**: 30분 (스크립트 및 문서)
- **Phase 6-7**: 30분 (커밋 및 양쪽 레포 업데이트)

**총 예상 시간**: 3-4시간

## 트러블슈팅

### Q: 두 레포의 코드가 너무 비슷해서 혼란스러워요

A: 이건 정상입니다. 핵심 차이:
- **claude-kit**: Template validation 포함
- **dev-workflow-template**: Generic linting만

### Q: 개선사항을 두 곳에 반영해야 하나요?

A: 아니요. 각 레포는 독립적으로 진화합니다. 필요 시에만 선택적으로 포팅하세요.

### Q: 나중에 다시 합칠 수 있나요?

A: 가능하지만 권장하지 않습니다. 분리는 명확성을 위한 것이므로 유지하는 게 좋습니다.

## 참고 자료

- 전문가 패널 토론 결과: `docs/discussions/YYYYMMDD_dev-templates/`
- Cookiecutter 대안 분석: 위 토론 참조
- 업계 Best Practices: 토론 내 웹 검색 결과
