# GitHub Actions Workflows

Template을 자동 검증하는 CI/CD workflows입니다.

## validate.yml

**트리거**: PR 생성/업데이트 또는 main push 시 (template/ 변경된 경우)

**검증 항목**:

- Template validation: SKILL.md/Agent frontmatter 검증 (name, description 필수)

**실패 시**:

```bash
# Template 오류 확인 및 수정
./scripts/validate-templates.sh
```

## claude.yml / claude-code-review.yml

Claude Code GitHub Action 설정. PR/Issue에서 `@claude` 멘션으로 Claude 호출.

## 로컬 실행

```bash
brew install act
act pull_request
```
