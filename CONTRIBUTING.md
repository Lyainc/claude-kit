# Contributing

claude-kit에 기여해주셔서 감사합니다.

## 컴포넌트 수정 시

```bash
# 1. 파일 수정
vim skills/expert-panel/SKILL.md

# 2. Validation
./scripts/validate-templates.sh

# 3. Commit
git add skills/
git commit -m "feat: Update expert-panel skill"
```

## Commit Message

Conventional Commits 사용:

```
feat: Update expert-panel skill
fix: Resolve validation error
docs: Update README
```

## 추가 문서

- 개발 가이드: [CLAUDE.md](CLAUDE.md)
- Git 상세 가이드: [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md)
