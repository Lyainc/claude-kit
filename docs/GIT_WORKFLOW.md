# Git Workflow Guide

> claude-kit 프로젝트 Git 관리 전략 및 상세 가이드

---

## 목차

1. [설계 배경](#설계-배경)
2. [브랜치 전략](#브랜치-전략)
3. [작업 단계별 가이드](#작업-단계별-가이드)
4. [트러블슈팅](#트러블슈팅)
5. [예외 상황 처리](#예외-상황-처리)

---

## 설계 배경

### 왜 이 워크플로우인가?

**프로젝트 특성**:
- 작은 코드베이스 (주로 설정 파일과 스크립트)
- 단독 개발자, 다중 Claude 세션 사용
- 빠른 반복 개발 (설정 테스트 → 수정 → 재배포)

**발생했던 문제**:
- 다른 세션에서 동시 작업 시 브랜치 충돌
- 중복 커밋 (같은 변경사항을 다른 해시로)
- 머지된 브랜치가 리모트에 계속 남아있음

**설계 원칙**:
1. **단순성**: 규칙 3-5개로 제한
2. **명시성**: 각 단계마다 명확한 커맨드 제공
3. **방어성**: 다중 세션 충돌 최소화
4. **가역성**: 실수해도 쉽게 복구 가능

---

## 브랜치 전략

### Main Branch

**용도**: Production-ready 코드만 포함

**규칙**:
- 항상 stable 상태 유지
- CI 통과 필수 (template validation)
- Direct push 가능 (trivial changes만)

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
- 하루 끝에 머지 못하면 폐기 권장

**금지 사항**:
- Long-lived feature branches (2일 이상)
- 머지된 브랜치를 리모트에 방치
- Stale branches (마지막 커밋 7일 이상)

---

## 작업 단계별 가이드

### 1. 새 작업 시작

#### 체크리스트

- [ ] Remote 최신 상태 확인
- [ ] Main 브랜치에서 시작
- [ ] 브랜치 이름이 명확한가?

#### 커맨드

```bash
# 1. Remote 동기화 (다른 세션 작업 확인)
git fetch origin

# 2. Main으로 전환 및 업데이트
git checkout main
git pull origin main

# 3. 새 브랜치 생성
git checkout -b feature/add-new-skill

# 4. 상태 확인
git status
```

#### 언제 브랜치를 생략하는가?

다음 경우 main에 직접 커밋 가능:
- Typo 수정 (1-2줄)
- README/문서만 수정
- .gitignore 같은 메타 파일 수정
- 긴급 hotfix (30분 이내 완료 예상)

**예시**:
```bash
# Typo 수정 - 브랜치 불필요
git checkout main
git pull origin main
# ... 파일 수정 ...
git add README.md
git commit -m "docs: Fix typo in installation section"
git push origin main
```

---

### 2. 작업 중

#### 주기적 동기화

**권장**: 1시간마다 또는 세션 전환 시

```bash
# Main의 변경사항 확인
git fetch origin

# Main에 새 커밋이 있는지 확인
git log HEAD..origin/main --oneline

# 새 커밋이 있다면 rebase (선택)
git rebase origin/main
```

#### 커밋 가이드

**좋은 커밋**:
- 단일 목적 (한 가지만 변경)
- 명확한 메시지
- 테스트 통과 상태

**커밋 메시지 포맷**:
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Type 종류**:
- `feat`: 새 기능 추가
- `fix`: 버그 수정
- `docs`: 문서만 변경
- `refactor`: 리팩토링 (동작 변경 없음)
- `test`: 테스트 추가/수정
- `chore`: 빌드, 도구, 의존성 업데이트

**예시**:
```bash
git commit -m "feat: Add expert-panel skill

Implements multi-perspective dialectical analysis for decision-making.
- Optimistic/Critical practitioner + Domain expert personas
- Thesis-antithesis-synthesis methodology

Refs: #12"
```

#### 언어 규칙

**커밋 메시지**: 영어 (Conventional Commits 표준 준수)

**PR 설명**: 한글 (달리 지정하지 않는 한)

**이유**:

- 커밋 메시지는 글로벌 표준 도구와 호환성 유지
- PR은 프로젝트 컨텍스트 설명이므로 모국어가 더 명확

**PR 예시**:

```markdown
## 변경사항

Git 워크플로우 문서화

## 상세 내용

- CLAUDE.md에 Git 워크플로우 체크리스트 추가
- docs/GIT_WORKFLOW.md 상세 가이드 작성

## 테스트

- [ ] 템플릿 검증 통과
- [ ] 다중 세션 시나리오 확인
```

---

### 3. 작업 완료 및 머지

#### 체크리스트

- [ ] Remote 최신 상태 재확인
- [ ] 충돌 해결 완료
- [ ] CI 통과 (로컬에서 `./scripts/validate-templates.sh` 실행)
- [ ] Uncommitted changes 없음

#### 커맨드

```bash
# 1. 최종 동기화 (CRITICAL)
git fetch origin
git checkout main
git pull origin main

# 2. 충돌 확인 (dry-run)
git merge --no-commit --no-ff feature/xyz
git merge --abort  # dry-run이므로 취소

# 3. 실제 머지
git merge --no-ff feature/xyz -m "Merge branch 'feature/xyz'

<간단한 설명>"

# 4. Remote 푸시
git push origin main

# 5. 브랜치 즉시 삭제 (로컬 + 리모트)
git branch -d feature/xyz
git push origin --delete feature/xyz

# 6. 최종 확인
git branch -a  # 삭제 확인
```

#### --no-ff 플래그를 사용하는 이유

```
# --ff (fast-forward, 기본값)
main: A---B---C---D  (선형 히스토리, 브랜치 흔적 없음)

# --no-ff (머지 커밋 생성)
main: A---B-------M  (브랜치 작업 명확히 구분)
            \     /
feature:     C---D
```

**장점**:
- 브랜치 작업 단위를 히스토리에서 구분 가능
- 롤백 시 머지 커밋만 revert하면 됨
- 코드 리뷰 흔적 보존

---

### 4. 다중 세션/에이전트 작업 시

#### 시나리오: 2개 이상의 Claude 세션 또는 에이전트에서 작업

**문제**:

- Session/Agent A: `feature/add-skill` 작업 중
- Session/Agent B: `fix/typo` 작업 중
- 둘 다 모르고 main에 머지 → 충돌

**해결책**: Safe-Merge 스크립트 + 명확한 프로토콜

#### 권장 워크플로우 (자동화)

```bash
# 1. 작업 시작 - 일반적인 브랜치 생성
git fetch origin
git checkout main
git pull origin main
git checkout -b feature/add-new-skill

# 2. 작업 완료 후 - Safe-Merge 스크립트 사용 (권장)
./scripts/safe-merge.sh feature/add-new-skill
```

**Safe-Merge가 자동으로 처리하는 것**:

- Remote 최신 상태 확인
- Local/Remote diverge 감지
- 충돌 사전 체크 (dry-run merge)
- 안전한 머지 + 푸시
- 브랜치 자동 삭제 (local + remote)

#### 수동 워크플로우 (기존 방식)

Safe-Merge 스크립트를 사용할 수 없는 경우:

```bash
# Session A 시작 전
git fetch && git status
git log origin/main --oneline -5  # 다른 세션 작업 확인

# Session B 시작 전 (동일)
git fetch && git status
```

**핵심 규칙**:

1. **세션 시작 전 반드시 fetch**
2. **머지 전 다시 fetch**
3. **브랜치 이름으로 작업 내용 표시** (다른 세션에서 확인 가능)

#### 추가 보호 옵션 (선택적)

프로젝트에 Git hooks가 준비되어 있으나, **사용을 권장하지 않습니다**.

**이유**:

- `safe-merge.sh`가 이미 모든 안전장치 제공
- Hook 설치/관리 복잡도 불필요
- 현재 프로젝트 규모에서는 과도

**Hook 사용이 필요한 경우** (팀 5명+ 규모):
```bash
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

자세한 내용: `hooks/README.md`

#### 충돌 발생 시

```bash
# 머지 중 충돌 발생
git merge feature/xyz
# CONFLICT (content): Merge conflict in template/CLAUDE.md

# 1. 충돌 파일 확인
git status

# 2. 충돌 해결
# ... 파일 수동 편집 ...

# 3. 해결 완료 표시
git add <충돌-파일>
git commit  # 머지 커밋 완성

# 4. 푸시
git push origin main
```

#### 다중 에이전트 협업 팁

**가시성 확보**:
```bash
# 다른 에이전트 작업 확인
git fetch origin
git branch -r  # Remote 브랜치 목록
git log origin/main --oneline -10  # 최근 커밋

# 특정 브랜치 상태 확인
git log origin/feature/some-work --oneline
```

**작업 충돌 방지**:

- 브랜치 이름에 작업 내용 명시: `feature/add-expert-panel-skill`
- 같은 파일 동시 수정 피하기: 시작 전 `git fetch`로 확인
- 긴급 작업은 즉시 공유: 커밋 메시지에 명확히 표시

**권장 브랜치 네이밍 (타임스탬프 포함)**:
```bash
# 충돌 가능성을 더욱 줄이려면
feature/20260111-1430-add-new-skill
fix/20260111-0920-typo-in-readme
```

타임스탬프 포함 시 장점:

- 브랜치 생성 시점 명확
- 동일 작업 이름 충돌 방지
- 자동 정리 스크립트 작성 가능

---

## 트러블슈팅

### 문제 1: "다른 세션에서 이미 같은 변경을 했는데 모르고 또 했어요"

**증상**:
```bash
git log --oneline
46fda43 Fix GitHub Actions permissions for PR comments  # Session A
76c3bd0 Fix GitHub Actions permissions for PR comments  # Session B (중복)
```

**예방**:
```bash
# 작업 시작 전 항상
git fetch origin
git log origin/main --oneline -10  # 최근 커밋 확인
```

**사후 처리**:
```bash
# 중복 커밋 제거 (rebase)
git rebase -i HEAD~2
# 편집기에서 중복 커밋을 'drop'으로 변경
```

---

### 문제 2: "브랜치가 너무 많아요"

**증상**:
```bash
git branch -a
  feature/old-work
  fix/something
  remotes/origin/feature/merged-last-week
  remotes/origin/fix/already-done
```

**정리**:
```bash
# 로컬 머지된 브랜치 일괄 삭제
git branch --merged main | grep -v "main" | xargs git branch -d

# 리모트 브랜치 확인 후 삭제
git fetch --prune  # 이미 삭제된 리모트 브랜치 정리
git push origin --delete <branch-name>

# 또는 GitHub UI에서 PR 머지 시 "Delete branch" 체크
```

---

### 문제 3: "실수로 main에 바로 커밋했어요"

**증상**:
```bash
# main에서 작업하다가 실수로 커밋
git log --oneline
abc1234 (HEAD -> main) WIP: half-done feature
```

**복구**:
```bash
# 1. 커밋을 브랜치로 옮기기
git branch feature/rescued-work  # 새 브랜치 생성 (현재 HEAD)
git reset --hard HEAD~1          # main을 1 커밋 뒤로

# 2. 브랜치로 전환해서 작업 계속
git checkout feature/rescued-work
```

---

### 문제 4: "머지하려는데 'diverged' 에러가 나요"

**증상**:
```bash
git status
Your branch and 'origin/main' have diverged,
and have 2 and 1 different commits each, respectively.
```

**원인**: 로컬 main과 리모트 main이 다른 방향으로 진행됨

**해결**:
```bash
# 1. 상황 파악
git log --oneline --graph --all -10

# 2. 리모트 우선 (권장)
git reset --hard origin/main  # 로컬 변경 폐기
git checkout -b feature/recovered  # 로컬 작업 살리고 싶으면 사전에 브랜치

# 3. 또는 로컬 우선 (신중하게)
git push --force-with-lease origin main  # 주의: 협업 시 절대 금지
```

---

## 예외 상황 처리

### 긴급 Hotfix

**상황**: Main이 broken 상태, 즉시 수정 필요

**프로세스**:
```bash
# 1. Main에서 직접 수정 (브랜치 생략)
git checkout main
git pull origin main

# 2. 수정 작업
# ... fix ...

# 3. 즉시 커밋 & 푸시
git add <파일>
git commit -m "hotfix: Fix critical template validation error"
git push origin main

# 4. 다른 세션에 알림 (주석으로)
# Slack, 메모 등에 "긴급 hotfix 푸시됨" 기록
```

---

### 실험적 작업 (Spike)

**상황**: 방향성 불확실, 여러 번 롤백 예상

**프로세스**:
```bash
# 1. 별도 실험 브랜치
git checkout -b spike/experiment-approach

# 2. 자유롭게 커밋 (메시지 대충도 OK)
git commit -m "WIP"
git commit -m "try this"

# 3. 완성 시 스쿼시
git rebase -i main
# 여러 커밋을 하나로 합침

# 4. 또는 실패 시 폐기
git checkout main
git branch -D spike/experiment-approach
```

---

### Force Push가 필요한 경우

**원칙**: 절대 `main`에는 force push 금지

**허용 케이스**: 자신의 feature 브랜치만

```bash
# Feature 브랜치 히스토리 정리 후
git push --force-with-lease origin feature/xyz

# --force-with-lease: 리모트가 예상한 상태일 때만 푸시
# (다른 사람이 푸시했으면 실패 → 안전)
```

---

## 요약: 체크리스트

### 작업 시작 전
- [ ] `git fetch origin`
- [ ] `git checkout main && git pull`
- [ ] 브랜치 이름 결정

### 작업 완료 시
- [ ] 다시 `git fetch origin`
- [ ] CI 통과 확인
- [ ] `git merge --no-ff`
- [ ] 브랜치 삭제 (로컬 + 리모트)

### 매일 종료 전
- [ ] 모든 브랜치 머지 또는 폐기
- [ ] `git branch -a`로 정리 확인

---

## 참고 자료

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2)
- [프로젝트 CLAUDE.md](../CLAUDE.md) - 간단 체크리스트
