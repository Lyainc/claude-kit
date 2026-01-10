# Contributing to Claude Kit

claude-kit에 기여해주셔서 감사합니다! 이 문서는 프로젝트 기여 방법을 안내합니다.

## 시작하기

### 1. Repository Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/claude-kit.git
cd claude-kit
```

### 2. Hooks 설치 (권장)

로컬에서 자동 validation을 받으려면 hooks를 설치하세요:

```bash
./scripts/setup-hooks.sh
```

이 단계는 선택사항이지만, PR 제출 전에 로컬에서 빠르게 오류를 발견할 수 있습니다.

## 기여 워크플로우

### Template 파일 수정 시

Template 파일을 수정할 때는 **반드시** 다음 순서를 따르세요:

```bash
# 1. 파일 수정
vim template/skills/expert-panel/SKILL.md

# 2. 버전 업데이트 (기능 변경 시)
jq '.modules["skills/expert-panel"].version = "1.2.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json

# 3. Validation
./scripts/validate-templates.sh

# 4. Manifest 재생성
./scripts/generate-manifest.sh

# 5. 변경사항 확인
git diff template/

# 6. Commit
git add template/
git commit -m "feat: Enhance expert-panel discussion format"
```

**중요**: Manifest 재생성을 잊으면 CI가 실패합니다.

### 버전 관리 규칙

Semantic Versioning을 따릅니다:

- **Major (X.0.0)**: Breaking changes, API 변경
- **Minor (x.Y.0)**: 새 기능, 개선 (backward compatible)
- **Patch (x.y.Z)**: 버그 수정, 문서 업데이트

자세한 내용은 [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md)를 참조하세요.

### Branch 전략

```bash
# Feature 추가
./scripts/new-branch.sh feature add-new-skill

# Bug 수정
./scripts/new-branch.sh fix validation-error

# 브랜치명 형식: feature/YYYYMMDD-HHMM-description
```

**AI 에이전트로 작업 시**: 브랜치명에 `agent-`  접두사 사용 권장

```bash
git checkout -b agent-update-skill-v2
```

### Commit Message 컨벤션

Conventional Commits을 따릅니다:

```
feat: Add new documentation skill
fix: Resolve YAML parsing error in validation
docs: Update installation guide
refactor: Simplify manifest generation logic
chore: Update dependencies
```

**언어**: 커밋 메시지는 영어, PR 설명은 한국어 또는 영어

## Template 작성 가이드

### Skill 추가

```bash
# 1. Template 복사
cp -r template/skills/_TEMPLATE template/skills/my-skill

# 2. SKILL.md 작성
vim template/skills/my-skill/SKILL.md
```

**필수 요구사항**:

- `name`: 소문자/숫자/하이픈, 64자 이하
- `description`: 1024자 이하, "Use when..." 패턴 사용
- SKILL.md: ~100줄 권장, 500줄 이하

**Validation**:

```bash
./scripts/validate-templates.sh --skills
```

### Agent 추가

```bash
# 1. Template 복사
cp template/agents/_TEMPLATE.md template/agents/my-agent.md

# 2. Frontmatter 작성
vim template/agents/my-agent.md
```

**필수 필드**:

- `name`, `description`, `tools`, `model`

## Pull Request 제출

### PR 생성 전 체크리스트

- [ ] Validation 통과: `./scripts/validate-templates.sh`
- [ ] Manifest 재생성: `./scripts/generate-manifest.sh`
- [ ] 변경사항 확인: `git diff template/`
- [ ] Commit message 컨벤션 준수
- [ ] 버전 업데이트 (기능 변경 시)

### PR 제출

```bash
git push origin feature/my-branch
```

GitHub에서 PR을 생성하면:

1. **자동 CI 검증** 실행
   - Template validation
   - Manifest integrity check

2. CI 실패 시:
   - 에러 메시지 확인
   - 로컬에서 수정 후 재푸시

### PR 설명 작성

```markdown
## Summary

이 PR은 expert-panel 스킬에 새로운 토론 형식을 추가합니다.

## Changes

- `template/skills/expert-panel/SKILL.md`: 3-round discussion 형식 추가
- `template/skills/expert-panel/examples.md`: 예제 업데이트

## Version

- `skills/expert-panel`: 1.0.0 → 1.1.0

## Test Plan

- [ ] Validation 통과
- [ ] 로컬 설치 후 스킬 동작 확인
- [ ] 예제 시나리오 테스트 완료
```

## 문제 해결

### CI 실패: Template validation error

```bash
# 로컬에서 재현
./scripts/validate-templates.sh

# 에러 메시지 확인 후 수정
# 주로 frontmatter의 name, description 누락
```

### CI 실패: Manifest out of sync

```bash
# Manifest 재생성
./scripts/generate-manifest.sh

# 변경사항 커밋
git add template/.claude-kit-manifest.json
git commit --amend --no-edit
git push --force-with-lease
```

### Pre-commit hook 우회

```bash
# 권장하지 않지만 필요 시
git commit --no-verify
```

**주의**: CI는 우회할 수 없으므로, hook을 우회해도 PR 시 검증됩니다.

## 코드 리뷰

Maintainer가 리뷰 시 다음을 확인합니다:

- [ ] Template 품질 (명확성, 완결성)
- [ ] 버전 업데이트 적절성
- [ ] Commit message 명확성
- [ ] Breaking change 여부 (CHANGELOG 업데이트 필요)

## 커뮤니티 가이드라인

- **존중**: 모든 기여자를 존중합니다
- **명확성**: 모호한 표현보다 명확한 설명 선호
- **피드백**: 건설적인 피드백을 환영합니다
- **인내**: 리뷰에 시간이 걸릴 수 있습니다

## 추가 자료

- [CLAUDE.md](CLAUDE.md) - 프로젝트 아키텍처 및 워크플로우
- [docs/VERSION_MANAGEMENT.md](docs/VERSION_MANAGEMENT.md) - 버전 관리 상세 가이드
- [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) - Git 워크플로우 상세
- [.github/workflows/README.md](.github/workflows/README.md) - CI/CD 설명

## 질문이 있나요?

- GitHub Issues에 질문 등록
- Discussions에서 토론 참여

감사합니다! 🎉
