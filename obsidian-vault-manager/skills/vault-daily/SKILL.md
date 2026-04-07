---
name: vault-daily
description: "Create a daily note and integrate previous day review. Example: '/vault-daily', '/vault-daily --review'"
allowed-tools: Read Write Edit Bash Glob Grep
---

오늘의 데일리 노트를 생성하거나 전날 리뷰를 수행한다.

## 절차

### 기본 모드 (`/vault-daily`)

1. **날짜 확인**: 오늘 날짜(YYYY-MM-DD) 확인
2. **중복 확인**: `~/vault/00_Inbox/YYYY-MM-DD-daily.md` 존재 여부 확인
   - 이미 존재하면: 기존 파일 내용을 보여주고 "이어서 작성할까요?" 확인
3. **전날 요약 로드** (자동):
   - 전날 daily 노트가 있으면 읽어서 미완료 항목을 수집
   - 전날 `session-wrapup` 노트가 있으면 참조
4. **데일리 노트 생성**:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [daily]
   ---
   # Daily — YYYY-MM-DD

   ## Carry-over
   {전날 미완료 항목 — 없으면 섹션 생략}

   ## Today's Focus
   - 

   ## Notes
   - 

   ## End of Day
   - [ ] Inbox 정리 완료
   - [ ] 주요 작업 노트 작성 완료
   ```
5. **출력**: 생성된 파일 경로 + 전날 carry-over 항목 수

### 리뷰 모드 (`/vault-daily --review`)

1. **전날 데일리 노트 로드**: 전날 `YYYY-MM-DD-daily.md` 읽기
   - 없으면: "전날 데일리 노트가 없습니다" 출력 후 종료
2. **active handoff 탐색**: `~/vault/20_Projects/*/handoff-*.md` 및 `~/vault/00_Inbox/*-handoff.md`에서 `status: active`인 handoff 노트를 탐색한다.
   - active handoff가 있으면: "다음 단계" 항목을 Carry-over 후보에 포함한다.
3. **완료 상태 분석**:
   - `End of Day` 체크리스트 완료 여부 확인
   - `Today's Focus` 항목의 달성 여부 확인
4. **리뷰 요약 출력**:
   ```
   ## Daily Review — YYYY-MM-DD

   ### 완료 상태
   - Today's Focus: {N}/{M} 완료
   - End of Day checklist: {완료/미완료}

   ### 미완료 → Carry-over
   - {item 1}
   - {item 2}

   오늘의 데일리 노트를 생성할까요?
   ```
5. 사용자 확인 시 기본 모드로 전환하여 carry-over 포함 데일리 노트 생성

## Wrapup 연동

`/wrapup` 실행 시 당일 daily 노트가 있으면:
- wrapup 요약을 daily 노트의 `## Notes` 섹션에 추가 제안
- daily 노트의 `End of Day` 체크리스트 업데이트 제안

## 규칙

- 데일리 노트는 `00_Inbox/`에 생성한다 (MOC 링크 없음).
- `--review`는 전날 노트만 대상으로 한다.
- 한국어로 응답한다.
