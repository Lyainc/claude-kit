# GitHub Actions Workflows

Template 및 manifest 무결성을 자동 검증하는 CI/CD workflows입니다.

## validate.yml

**트리거**: PR 생성/업데이트 또는 main push 시 (template/ 변경된 경우)

**검증 항목**:

1. Template validation: SKILL.md/Agent frontmatter 검증
2. Manifest integrity: Hash 일치 여부 확인

**실패 시**:

```bash
# Template 오류
./scripts/validate-templates.sh

# Manifest 불일치
./scripts/generate-manifest.sh
git add template/.claude-kit-manifest.json
git commit --amend --no-edit
```

## 로컬 실행

```bash
brew install act
act pull_request
```
