# PR 6 Dogfood Findings — v4 Migration

> 작성: 2026-05-28
> 브랜치: main (hotfix commit 0ddb8a6 포함)
> 기반: PR #91 (4e) + PR #92 (5) + PR #93 모두 머지 후 main `e7d6191`

---

## 1. 마이그레이션 결과 요약

### 전/후 vault 구조

| 전 (7 폴더) | 후 (3 폴더) |
|-------------|-------------|
| 00_Inbox (7 files) | inbox/ (7 files) |
| 10_MOC (5 files) | notes/ (124 files) |
| 20_Projects (101 files) | assets/ (1 file) |
| 30_Notes (9 files) | 20_Projects/ 잔류 (1 dir, type 없는 파일) |
| 40_Resources (10 files) | 50_Archive/ 잔류 (1 subdir, 딥러닝 과제) |
| 50_Archive (6 files, subdir) | |
| 90_Assets (0 files) | |

- 이동된 파일: 109개 (Python script) + shell 1:1 매핑
- wikilink 자동 수정: 4개 파일
- manifest 재생성: 134 entries, schema_version=3
- 마이그레이션 커밋: `210b3fe`

### 마이그레이션 전/후 audit 결과

| 항목 | 마이그레이션 전 | 마이그레이션 후 |
|------|----------------|----------------|
| audit findings | 미측정 (snapshot 이전) | **0개** |
| E3 filename violations | 미측정 | 0 |
| schema_version | 3 (기존) | 3 |

마이그레이션 후 audit 0 findings — 기존 파일들의 frontmatter가 온전히 보존되고 type 옵트인 원칙 준수.

---

## 2. 발견된 버그 및 핫픽스

### BUG-01: vault-commit.md 상대경로 포터빌리티 문제

**발견**: dogfood 시작 전 코드 리뷰 중 발견  
**증상**: `/vault-commit` 실행 시 `python3 vault-bridge/scripts/vault-commit-message.py` 경로가 개발 레포 외부에서 실패  
**원인**: `vault-commit.md` Step 4c가 하드코딩 상대경로 사용. 다른 커맨드(vault-manifest-refresh.md, save-plan-doc.md)는 이미 `${CLAUDE_PLUGIN_ROOT}/scripts/` 패턴 사용.  
**수정**: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/vault-commit-message.py"` 로 변경  
**커밋**: `0ddb8a6` `fix(vault-bridge): use CLAUDE_PLUGIN_ROOT for vault-commit-message.py path`  
**버전**: vault-bridge 1.17.0 → **1.17.1** (patch bump)

---

## 3. 발견된 spec gap

### GAP-01: migration script의 _index.md 이중 처리 버그

**발견**: Python migration script 실행 중  
**증상**: `process_project_dir`에서 `_index.md → notes/{name}.md` rename이 충돌(이미 존재)로 실패하면, 두 번째 루프(type 있는 .md 이동)가 동일 `_index.md`를 `notes/_index.md`로 이동시킴  
**결과**: `notes/_index.md` 라는 모호한 이름의 파일 생성 (claude-kit project index가 의도치 않게 `_index.md` 네이밍됨)  
**수동 fix**: `notes/_index.md` → `notes/claude-kit-project.md` 으로 rename

**수정 방향**: `docs/plans/vault-second-brain-v4-migration.md`의 Python script (§3.3 Step 4) `process_project_dir` 함수 두 번째 루프에서 `_index.md` 파일 skip 추가:

```python
for f in os.listdir(proj_dir):
    full = os.path.join(proj_dir, f)
    if not os.path.isfile(full) or not f.endswith(".md"):
        continue
    if f == "_index.md":  # 첫 번째 단계에서 이미 처리됨 (성공/실패 무관)
        continue
    ...
```

**우선순위**: Medium — 두 개의 같은 이름 노트(e.g., `notes/claude-kit.md` MOC + `20_Projects/claude-kit/_index.md` project index)가 있을 때만 발생.

### GAP-02: 50_Archive 하위폴더 처리 미지원

**발견**: 마이그레이션 중  
**증상**: `50_Archive/딥러닝의통계적이해_과제/` 같은 2단계 중첩 구조는 Python script가 처리하지 않음  
**결과**: 원위치 유지 (의도된 동작 — migration doc §9 알려진 한계)  
**조치 불필요**: 사용자 수동 검토 후 결정 사항. doc에 이미 명시됨.

---

## 4. 신규 기능 검증 결과

| 기능 | 상태 | 비고 |
|------|------|------|
| vault-commit status 전이 메시지 | ✅ 14 cases passed | `test-vault-commit-message.py` |
| SessionStart additionalContext surface | ✅ 정상 구현 확인 | `session-start-manifest.sh` |
| stop-check hook UTF-8 locale | ✅ syntax OK | `bash -n` 통과 |
| pre-access-guard self-exemption | ✅ all cases passed | `test-pre-access-guard.py` |
| pre-write-guard subagent block | ✅ all cases passed | `test-pre-write-guard.py` |
| manifest type-optin | ✅ all cases passed | `test-manifest-type-optin.py` |
| git activity summary (18 cases) | ✅ all 18 passed | `test-git-activity.py` |
| DoD fixture E1-E8 | ✅ 모두 정확히 감지, FP=0 | `audit-validate.py --dod` |

---

## 5. 회귀 테스트 결과

```
OVM:
  test-git-activity.py:        OK: all 18 cases passed
  test-promotion-finding.py:   OK: all 8 cases passed
  test-read-manifest-summary.py: OK: all cases passed (7 cases)
  test-parse-created-date.py:  OK: all 13 cases passed

vault-bridge:
  test-vault-commit-message.py: OK: all cases passed (14 cases)
  test-discover.py:             OK: all cases passed
  test-pre-write-guard.py:      OK: all cases passed
  test-pre-access-guard.py:     OK: all cases passed
  test-manifest-type-optin.py:  OK: all cases passed
  bash -n hooks/*.sh:           OK

DoD fixture:
  seeded_detected: E1:5/E2:10/E3:5/E4:5/E5:5/E6:5/E7:5/E8:2
  fp_on_clean: all 0
  findings_missing_priority: 0
```

---

## 6. 핫픽스 PR 목록

| PR | 내용 | 커밋 |
|----|------|------|
| 직접 main 커밋 | fix(vault-bridge): CLAUDE_PLUGIN_ROOT portability | `0ddb8a6` |

규모가 작은 단일 파일 fix라 별도 PR 분리 없이 main에 직접 커밋.

---

## 7. 후속 조치 항목

- [ ] **GAP-01 수정**: `docs/plans/vault-second-brain-v4-migration.md` Python script `_index.md` skip 로직 추가
- [ ] **vault 정리 (선택)**: `notes/claude-kit.md` (MOC) vs `notes/claude-kit-project.md` (project index) 통합 여부 사용자 결정
- [ ] **PhototicketMaker 잔여**: `20_Projects/PhototicketMaker/session-2026-05-27-phase-c-f-complete.md` — type 없어서 원위치 유지됨. 사용자 직접 type 추가 후 이동 결정
- [ ] **50_Archive 딥러닝**: 하위폴더 수동 검토 후 처리 결정
- [ ] **PR 7 README**: v4 반영 README 작업 (다음 세션)
