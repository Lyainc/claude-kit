# Repository Split Guide

claude-kit에서 개발 워크플로우를 별도 레포로 분리하는 절차입니다.

## 분리 시점

다음 중 하나라도 해당되면 분리 고려:

- [ ] 다른 프로젝트에서 hooks/CI 재사용 필요
- [ ] 외부 기여자의 템플릿 재사용 요청
- [ ] 다른 언어 템플릿 추가 계획
- [ ] 이슈 트래커 혼란

## 분리 대상

### 이동할 파일

- `scripts/setup-hooks.sh` (일반화)
- `.pre-commit-config.yaml`
- `CONTRIBUTING.md` (Git workflow 부분)
- `.github/workflows/validate.yml` (구조만)

### claude-kit 유지

- `scripts/validate-templates.sh`
- `scripts/generate-manifest.sh`
- Template 검증 로직

## 절차 요약

### 1. 새 레포 생성

```bash
# GitHub: dev-workflow-template 생성
git clone https://github.com/Lyainc/dev-workflow-template.git
cd dev-workflow-template
mkdir -p .github/workflows scripts
```

### 2. 핵심 파일 복사 및 일반화

```bash
# claude-kit 전용 로직 제거:
# - Template validation
# - Manifest integrity check

# Generic 로직 유지:
# - Hook 설치 구조
# - CI/CD 기본 틀
```

### 3. Setup Script

```bash
cat > setup.sh << 'EOF'
#!/bin/bash
read -p "Project name: " PROJECT_NAME
# Replace placeholders, install hooks
EOF
chmod +x setup.sh
```

### 4. 문서화

- `README.md`: Quick start
- `INSTALL.md`: 설치 방법

### 5. 릴리스

```bash
git add . && git commit -m "feat: Initial dev workflow template"
git tag -a v1.0.0 -m "Initial release"
git push origin main --tags
```

### 6. claude-kit 업데이트

README/CLAUDE.md에 링크 추가:

```markdown
## Related Projects

- [dev-workflow-template](https://github.com/Lyainc/dev-workflow-template): Generic workflow (extracted from claude-kit)
```

## 체크리스트

- [ ] 새 레포 생성
- [ ] 파일 추출 및 일반화
- [ ] setup.sh 작성
- [ ] 문서 작성
- [ ] 릴리스 태그
- [ ] claude-kit 링크 추가
- [ ] 양쪽 레포 테스트

## 유지보수

- 각 레포 독립 버전 관리
- 개선사항 선택적 포팅
- 이슈 명확히 분리

**예상 시간**: 3-4시간

**참고**: 전문가 패널 토론 결과 `docs/discussions/`
