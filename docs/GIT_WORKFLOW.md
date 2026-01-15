# Git Workflow Guide

> claude-kit 프로젝트 Git 관리 전략

---

## 브랜치 전략

### Main Branch

**용도**: Production-ready 코드만 포함

**규칙**:
- 항상 stable 상태 유지
- CI 통과 필수 (template validation)

### Feature/Fix Branches

**명명 규칙**:
```
feature/descriptive-name   # 새 기능
fix/issue-description      # 버그 수정
docs/topic                 # 문서만 수정
refactor/component-name    # 리팩토링
```

**수명 주기**:
- 생성 → 작업 → 머지 → 삭제: **당일 완료**
- 최대 3 커밋 이내

---

## 커밋 메시지

**포맷**:
```
<type>: <subject>

<body (optional)>
```

**Type 종류**:
- `feat`: 새 기능 추가
- `fix`: 버그 수정
- `docs`: 문서만 변경
- `refactor`: 리팩토링 (동작 변경 없음)
- `chore`: 빌드, 도구, 의존성 업데이트

**언어 규칙**:
- 커밋 메시지: 영어 (Conventional Commits 표준)
- PR 설명: 한글

**예시**:
```bash
git commit -m "feat: Add expert-panel skill

Implements multi-perspective dialectical analysis."
```

---

## 참고 자료

- [Conventional Commits](https://www.conventionalcommits.org/)
- [프로젝트 CLAUDE.md](../CLAUDE.md)
