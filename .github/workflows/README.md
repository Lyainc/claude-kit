# GitHub Actions Workflows

이 디렉토리는 claude-kit의 CI/CD workflows를 포함합니다.

## Workflows

### validate.yml

**목적**: Template 및 manifest 무결성 자동 검증

**트리거**:

- Pull Request 생성/업데이트 시 (template/ 수정된 경우)
- Main 브랜치 push 시 (template/ 수정된 경우)

**검증 항목**:

1. **Template Validation**: `./scripts/validate-templates.sh` 실행
   - SKILL.md frontmatter 검증 (name, description 필수)
   - Agent frontmatter 검증
   - ERROR 레벨 실패 시 workflow 실패

2. **Manifest Integrity**: Manifest hash 일치 여부 확인
   - `generate-manifest.sh` 실행 후 diff 확인
   - Hash 불일치 시 실패 (개발자가 재생성 누락)

**실패 시 해결 방법**:

```bash
# Template validation 실패
./scripts/validate-templates.sh
# 에러 메시지 확인 후 수정

# Manifest integrity 실패
./scripts/generate-manifest.sh
git add template/.claude-kit-manifest.json
git commit --amend --no-edit
```

## Branch Protection

Main 브랜치는 다음 규칙으로 보호됩니다:

- ✅ Require status checks to pass before merging
  - `validate` workflow 필수 통과
- ✅ Require branches to be up to date before merging
- ✅ Restrict direct push to main

## 로컬에서 CI 재현

[act](https://github.com/nektos/act)를 사용하여 로컬에서 GitHub Actions 실행 가능:

```bash
# act 설치 (macOS)
brew install act

# Workflow 실행
act pull_request

# 특정 job만 실행
act -j validate
```

## Workflow 확장 계획

**Phase 2 (향후)**:
- Manifest 버전 충돌 감지
- Main 브랜치 주기적 검증 (scheduled workflow)
- Release automation (tag 생성 시 release notes 자동 생성)

확장 시 이 파일을 업데이트하세요.
