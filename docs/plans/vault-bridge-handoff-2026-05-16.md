# 구현 플랜: `/handoff` 커맨드 + `.claude-kit/` 통합

> **상태 (2026-06-03 갱신): ✅ SHIPPED.** `/handoff` 커맨드·resume.md 생명주기(SessionStart 소비형)·`/save-session` redirect·`/save-plan-doc defer` resume 생성 전부 구현·배포됨(`vault-bridge/commands/handoff.md` 등 존재 확인). 계획상 1.11.0 범프는 이후 v2.0.0에 흡수. 아래는 구현 당시 설계 기록(보존).

**작성일**: 2026-05-16  
**버전 범프**: `1.10.0` → `1.11.0`  
**브랜치 제안**: `feature/vault-bridge-v1.11-handoff`  
**Status**: ✅ shipped (was: pending approval) — vault-bridge v2.0.0에 흡수됨

---

## Requirements Summary

| # | 요구사항 | 출처 |
|---|---------|------|
| R1 | `/handoff` 신규 커맨드 — 3옵션(복붙 한 줄 / 복붙 요약 / 파일 저장) | 세션 설계 합의 |
| R2 | `.claude-kit/vault-bridge/` — first-use auto-create, 전체 gitignore | 세션 설계 합의 |
| R3 | SessionStart — resume.md 감지 시 조건부 systemMessage, 소비 후 삭제 | 세션 설계 합의 |
| R4 | `/save-plan-doc` `intent == defer` → resume.md 자동 생성 | 세션 설계 합의 |
| R5 | `/save-session` — handoff 모드 제거, `/handoff` redirect 안내 | 세션 설계 합의 |
| R6 | `session-note-recipe.md` — handoff synonym/템플릿 정리 | R5 연동 |

---

## Acceptance Criteria

- [ ] `/handoff` 실행 시 AskUserQuestion 1회로 완료 (추가 인터랙션 없음)
- [ ] 옵션③ 선택 시 `.claude-kit/vault-bridge/resume.md` 생성, `.claude-kit/` gitignore 추가 제안
- [ ] 다음 세션 시작 시 resume.md 존재하면 systemMessage 발생, 발생 후 파일 삭제
- [ ] `/save-plan-doc defer` 완료 시 resume.md 자동 생성 (별도 `/handoff` 불필요)
- [ ] `/save-session`에서 `handoff` 키워드 입력 시 `/handoff` 사용 안내 출력 후 중단
- [ ] `bash -n vault-bridge/hooks/*.sh` 통과
- [ ] 기존 Python 테스트 전원 통과

---

## Background

이번 세션(2026-05-16)에서 아래 논의를 거쳐 설계가 확정됐다:

- `/save-session` 저사용률 원인 분석: 아카이브(vault 기록)와 인계(다음 세션 이어받기)가 혼재
- handoff를 독립 커맨드로 분리하는 것이 MECE 원칙상 올바름
- `.claude-kit/` 디렉토리 설계: OMC `.omc/`와 동일한 역할 범위(runtime state 전용, gitignore)
- PSM / omc plan / ralph 등 기존 OMC 스킬과 충돌 없음 확인
- `/expert-panel` 토론 결과: 6개 합의 사항 도출

---

## Implementation Steps

### Step 1 — `vault-bridge/commands/handoff.md` (신규)

```markdown
---
description: Transfer context to the next session — short prompt / summary block / local file
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# /handoff

**User language: Korean.**

## Step 0 — Kill switch
VAULT_BRIDGE_DISABLE=1 → 중단

## Step 1 — 컨텍스트 생성 (공통 로직)
대화 컨텍스트 skim:
- 이번 세션에서 한 작업 핵심 (1줄)
- 다음 세션에서 이어받을 것 (1줄)
- vault에 저장된 관련 파일 경로 (있으면)

## Step 2 — AskUserQuestion
"다음 세션으로 어떻게 인계할까요?"
① 복붙용 한 줄     → 1-2줄 프롬프트, 대화 출력
② 복붙용 요약      → Summary + Next Steps 블록, 대화 출력
③ 파일로 저장      → .claude-kit/vault-bridge/resume.md 저장
                     (다음 세션 시작 시 1회 안내 후 자동 삭제)

## Step 3 — 출력
①②: 코드블록으로 출력 (복붙 용이)
③: mkdir -p + Write + gitignore 체크 + 완료 메시지
```

**옵션③ Bash 로직**:
```bash
PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
CLAUDE_KIT_DIR="${PROJECT_ROOT}/.claude-kit/vault-bridge"
mkdir -p "$CLAUDE_KIT_DIR"
# .gitignore에 .claude-kit/ 없으면 추가 제안 (AskUserQuestion)
```

---

### Step 2 — `vault-bridge/hooks/session-start-manifest.sh` (수정)

마지막 `exit 0` 앞에 추가:

```bash
# Resume prompt detection — consume-on-read (fires once, then deletes)
PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-${PWD}}"
RESUME_FILE="${PROJECT_ROOT}/.claude-kit/vault-bridge/resume.md"

if [ -f "$RESUME_FILE" ]; then
  RESUME_CONTENT="$(cat "$RESUME_FILE" 2>/dev/null)"
  rm -f "$RESUME_FILE"
  printf '{"type":"systemMessage","message":"이전 세션 인계가 있어요.\\n\\n%s\\n\\n위 내용으로 이어받으려면 resume.md 읽어줘 라고 하거나 그냥 이어서 작업을 시작하세요."}\n' \
    "$RESUME_CONTENT"
fi
```

> cat 후 rm 순서로 race condition 방지. systemMessage는 stdout으로 출력.

---

### Step 3 — `vault-bridge/commands/save-plan-doc.md` (수정)

Step 6 — `intent == defer` closing line 뒤에 추가:

```markdown
**Intent-aware resume generation** (`intent == defer` 시):

```bash
PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-$PWD}"
mkdir -p "${PROJECT_ROOT}/.claude-kit/vault-bridge"
```

Write tool로 `.claude-kit/vault-bridge/resume.md` 생성:
```
이전 세션에서 {vault_path}에 {저장된 파일명} 계획을 저장했어요.
vault에서 {vault_path}/{저장된 파일명} 읽고 이어서 구현해줄래요?
```

완료 메시지 추가:
> 다음 세션 인계 파일도 `.claude-kit/vault-bridge/resume.md`에 저장됐어요 — 세션 시작 시 자동으로 안내해드릴게요.
```

---

### Step 4 — `vault-bridge/commands/save-session.md` (수정)

Step 0.5 추가 (Step 1 앞):

```markdown
## Step 0.5 — Handoff redirect check

If $ARGUMENTS contains: handoff, continue, resume, 인수인계, 이어서, 다음 세션

출력 후 중단:
> `/handoff` 커맨드를 사용해 주세요 — 인계 전용으로 분리됐어요.
> `/save-session`은 vault 아카이브 전용이에요 (record / quick 모드).
```

frontmatter description 업데이트:
```yaml
description: Archive the current session to vault — record / quick modes (handoff → use /handoff)
```

---

### Step 5 — `vault-bridge/reference/session-note-recipe.md` (수정)

**§2 Synonym dictionary** — handoff 행 제거:

| mode   | EN tokens            | KR tokens               |
|--------|----------------------|-------------------------|
| record | record, log, archive | 기록, 정리, 회고         |
| quick  | quick, brief, summary | 간단히, 짧게, 빠르게, 요약 |

**Tier 2 default** 수정:
```
대화 5턴 미만 → quick; 그 외 → record
```

**Templates** — handoff 전용 섹션 제거:
- `In Progress` 섹션 제거
- `Blockers / Warnings` 섹션 제거  
- `Next Steps` 섹션 제거
- `status: active` frontmatter 제거

**Scope** 업데이트:
```
Scope: artifact types session (record / quick), capture, plan.
```

---

### Step 6 — `vault-bridge/.claude-plugin/plugin.json` + `marketplace.json` (수정)

```json
"version": "1.11.0",
"keywords": [...기존..., "handoff", "claude-kit"]
```

description: `handoff command for next-session context transfer` 추가.  
marketplace.json: version + description 동기화 (Version Sync Rule).

---

## Risks and Mitigations

| 위험 | 완화 |
|------|------|
| `session-start-manifest.sh` systemMessage JSON 포맷 오류 시 훅 깨짐 | `bash -n` + 실제 세션 시작 테스트 |
| `CLAUDE_PROJECT_ROOT` 없는 환경에서 잘못된 경로 생성 | `${CLAUDE_PROJECT_ROOT:-$PWD}` fallback, 미발견 시 무해 |
| `save-plan-doc` defer에서 resume.md Write 실패 | 실패해도 silent — vault 저장은 이미 완료된 후 |
| `session-note-recipe.md` handoff 제거 시 save-session 깨짐 | Step 0.5 redirect가 recipe 도달 전에 막아줌 |

---

## Verification Steps

```bash
# Shell 문법 검사
bash -n vault-bridge/hooks/session-start-manifest.sh

# JSON 유효성
python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null

# 기존 Python 테스트
python3 vault-bridge/scripts/test/test-discover.py
python3 vault-bridge/scripts/test/test-pre-write-guard.py
python3 vault-bridge/scripts/test/test-pre-access-guard.py

# resume.md 수동 검증
echo "테스트 인계" > .claude-kit/vault-bridge/resume.md
# → 새 세션 시작 시 systemMessage 발생 확인
# → 발생 후 파일 삭제 확인
```

---

## Related Discussions

이 플랜 도출 과정의 논의 기록:
- expert-panel: vault-bridge 커맨드 체계 MECE 재설계 (2026-05-16, 이번 세션)
- thought-chain: `.claude-kit/` 디렉토리 설계 (2026-05-16, 이번 세션)
