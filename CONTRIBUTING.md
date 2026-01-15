# Contributing

claude-kit에 기여해주셔서 감사합니다.

## Template 수정 시

```bash
# 1. 파일 수정
vim template/skills/expert-panel/SKILL.md

# 2. Validation
./scripts/validate-templates.sh

# 3. Commit
git add template/
git commit -m "feat: Update expert-panel skill"
```

## Commit Message

Conventional Commits 사용:

```
feat: Add new skill
fix: Resolve validation error
docs: Update README
```

## 추가 문서

- Git workflow: [CLAUDE.md - Git Workflow](CLAUDE.md#git-workflow)
- Git 상세 가이드: [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md)
