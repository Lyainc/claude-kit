# Contributing

claude-kit에 기여해주셔서 감사합니다.

## Template 수정 시

```bash
# 1. 파일 수정
vim template/skills/expert-panel/SKILL.md

# 2. 버전 업데이트 (기능 변경 시)
jq '.modules["skills/expert-panel"].version = "1.1.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json

# 3. Validation
./scripts/validate-templates.sh

# 4. Manifest 재생성
./scripts/generate-manifest.sh

# 5. Commit
git add template/
git commit -m "feat: Update expert-panel v1.1.0"
```

**중요**: Manifest 재생성을 잊으면 CI가 실패합니다.

## 버전 관리

Semantic Versioning 사용:

- **Major (X.0.0)**: Breaking changes
- **Minor (x.Y.0)**: 새 기능, 개선
- **Patch (x.y.Z)**: 버그 수정, 문서

자세한 내용: [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md)

## Commit Message

Conventional Commits 사용:

```
feat: Add new skill
fix: Resolve validation error
docs: Update README
```

## 추가 문서

- Git workflow: [CLAUDE.md - Git Workflow](CLAUDE.md#git-workflow)
- 버전 관리: [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md)
- 레포 분리: [docs/REPO_SPLIT_GUIDE.md](docs/REPO_SPLIT_GUIDE.md)
