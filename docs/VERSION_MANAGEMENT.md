# Version Management Guide

Claude Kit의 manifest 기반 버전 관리 시스템 가이드입니다.

## 📋 Overview

v1.1.0부터 모든 template/ 파일은 manifest로 버전 관리됩니다.
파일을 수정할 때마다 **반드시** 버전을 업데이트해야 합니다.

## 🔴 Critical Rule

**Template 파일 수정 시 필수 작업**:

1. 파일 수정
2. Manifest 버전 업데이트
3. Manifest 재생성 (hash 갱신)
4. Commit

이 순서를 지키지 않으면 사용자 업데이트가 제대로 작동하지 않습니다.

## 📝 Standard Workflow

### 1. 기존 모듈 수정

```bash
# Step 1: 파일 수정
vim template/skills/expert-panel/SKILL.md

# Step 2: 버전 업데이트 (jq 사용)
jq '.modules["skills/expert-panel"].version = "1.1.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json

# Step 3: Hash 재생성
./scripts/generate-manifest.sh

# Step 4: Commit
git add template/
git commit -m "feat: Enhance expert-panel skill v1.1.0

- Add new discussion format
- Improve moderator logic"
```

### 2. 새 모듈 추가

```bash
# Step 1: 파일 생성
cp -r template/skills/_TEMPLATE template/skills/new-skill

# Step 2: 내용 작성
vim template/skills/new-skill/SKILL.md

# Step 3: Manifest 재생성 (자동으로 v1.0.0 추가됨)
./scripts/generate-manifest.sh

# Step 4: Commit
git add template/
git commit -m "feat: Add new-skill v1.0.0"
```

### 3. 모듈 삭제

```bash
# Step 1: 파일 삭제
rm -rf template/skills/old-skill

# Step 2: Manifest 재생성
./scripts/generate-manifest.sh

# Step 3: Commit
git add template/
git commit -m "feat: Remove deprecated old-skill"
```

## 🏷️ Semantic Versioning Rules

### Major Version (X.0.0)

Breaking changes, API 변경

**예시**:
- 스킬 인터페이스 변경
- 필수 파일 구조 변경
- 이전 버전과 호환 불가능한 수정

```bash
jq '.modules["skills/expert-panel"].version = "2.0.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json
```

### Minor Version (x.Y.0)

새 기능 추가, 기능 개선 (backward compatible)

**예시**:
- 새로운 기능 추가
- 기존 기능 개선
- 선택적 파일 추가

```bash
jq '.modules["skills/expert-panel"].version = "1.1.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json
```

### Patch Version (x.y.Z)

버그 수정, 문서 업데이트

**예시**:
- 오타 수정
- 버그 수정
- 문서/예제 개선

```bash
jq '.modules["skills/expert-panel"].version = "1.0.1"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json
```

## 🔍 Manifest Structure

```json
{
  "version": "1.0.0",
  "generated_at": "2026-01-07T22:58:14Z",
  "commit": "3e4c88f",
  "modules": {
    "skills/expert-panel": {
      "version": "1.2.0",        // 수동 관리
      "hash": "abc123...",        // 자동 생성
      "type": "folder"            // 자동 감지
    },
    "modules/principles.md": {
      "version": "2.0.0",         // 수동 관리
      "hash": "def456...",        // 자동 생성
      "type": "file"              // 자동 감지
    }
  }
}
```

### 필드 설명

- **version**: 개발자가 수동으로 관리 (semantic versioning)
- **hash**: `generate-manifest.sh`가 자동 계산
- **type**: `generate-manifest.sh`가 자동 감지 (file/folder)
- **generated_at**: 생성 시각 (자동)
- **commit**: Git commit hash (자동)

## 🚀 Update Behavior

사용자가 `./setup-claude-global.sh update` 실행 시:

### Case 1: 버전 동일, Hash 동일

→ **Skip** (조용히)

### Case 2: 버전 동일, Hash 다름

→ **Skip** (사용자 수정으로 간주)

```
⏭️  modules/principles.md (v1.0.0, user modified)
```

### Case 3: 버전 상승, Hash 동일 (로컬 == manifest)

→ **Auto-update** (사용자 수정 없음)

```
🔄 modules/principles.md (v1.0.0 → v1.1.0)
```

### Case 4: 버전 상승, Hash 다름 (로컬 ≠ manifest)

→ **Skip** (사용자 수정 보호)

```
⏭️  modules/principles.md (user modified, v1.0.0, update v1.1.0 available)
```

사용자는 `--force-update`로 강제 업데이트 가능 (백업 후):

```bash
./setup-claude-global.sh update --force-update
```

## 🛠️ Helper Scripts

### Version Bump Helper (예정)

```bash
# scripts/bump-version.sh
./scripts/bump-version.sh skills/expert-panel minor
# → 1.0.0 → 1.1.0

./scripts/bump-version.sh modules/principles.md patch
# → 1.0.0 → 1.0.1
```

### Batch Version Update

여러 모듈을 동시에 업데이트:

```bash
# 모든 스킬을 1.1.0으로
for skill in skills/*; do
  jq ".modules[\"$skill\"].version = \"1.1.0\"" \
    template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
    mv /tmp/manifest.tmp template/.claude-kit-manifest.json
done

./scripts/generate-manifest.sh
```

## 📊 Checking Versions

### 현재 버전 확인

```bash
# 특정 모듈
jq '.modules["skills/expert-panel"]' template/.claude-kit-manifest.json

# 모든 모듈
jq '.modules' template/.claude-kit-manifest.json
```

### 설치된 버전 확인

```bash
jq '.modules' ~/.claude/.claude-kit-manifest.json
```

### 업데이트 가능 여부 확인

```bash
./setup-claude-global.sh doctor
```

## ⚠️ Common Mistakes

### ❌ 잘못된 워크플로우

```bash
# 파일만 수정하고 commit
vim template/skills/expert-panel/SKILL.md
git commit -m "Update skill"  # 🔴 버전 업데이트 누락!
```

**문제**: 사용자가 업데이트해도 hash만 다르고 버전이 같아서 skip됨

### ❌ 버전만 올리고 manifest 재생성 안함

```bash
# 버전만 수동 변경
vim template/.claude-kit-manifest.json  # version: 1.1.0
git commit  # 🔴 hash가 구버전 그대로!
```

**문제**: Hash가 업데이트되지 않아 변경 감지 실패

### ✅ 올바른 워크플로우

```bash
# 1. 파일 수정
vim template/skills/expert-panel/SKILL.md

# 2. 버전 업데이트
jq '.modules["skills/expert-panel"].version = "1.1.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json

# 3. Hash 재생성
./scripts/generate-manifest.sh

# 4. Commit
git add template/ && git commit -m "feat: Update expert-panel v1.1.0"
```

## 🔧 Troubleshooting

### Manifest 손상 시

```bash
# 완전 재생성
./scripts/generate-manifest.sh
```

**주의**: 모든 버전이 현재 manifest 기준으로 유지됩니다.

### 버전 충돌 시

로컬 버전 > 템플릿 버전인 경우:

```bash
./setup-claude-global.sh doctor
# ⚠️  modules/principles.md (v2.0.0 local, v1.0.0 template)
```

해결: Template 버전을 로컬보다 높게 설정

```bash
jq '.modules["modules/principles.md"].version = "2.1.0"' \
  template/.claude-kit-manifest.json > /tmp/manifest.tmp && \
  mv /tmp/manifest.tmp template/.claude-kit-manifest.json

./scripts/generate-manifest.sh
```

## 📚 References

- [CLAUDE.md - Version Management Workflow](../CLAUDE.md#version-management-workflow)
- [README.md - 버전 관리 시스템](../README.md#버전-관리-시스템)
- [scripts/generate-manifest.sh](../scripts/generate-manifest.sh)

## 🎯 Quick Reference

| 작업 | 명령어 |
|------|--------|
| 버전 확인 | `jq '.modules["path"].version' template/.claude-kit-manifest.json` |
| 버전 업데이트 | `jq '.modules["path"].version = "X.Y.Z"' ... ` |
| Hash 재생성 | `./scripts/generate-manifest.sh` |
| Health check | `./setup-claude-global.sh doctor` |
| 강제 업데이트 | `./setup-claude-global.sh update --force-update` |
