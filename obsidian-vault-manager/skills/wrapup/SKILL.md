---
name: wrapup
description: "세션에서 작업한 내용을 요약하고 Inbox에 세션 정리 노트를 저장한다. 사용 예: '/wrapup'"
allowed-tools: Read Write Bash Glob
---

현재 세션에서 생성/수정한 파일들을 요약한다.

## 절차

1. **파일 변경 추적**: 세션 중 생성/수정한 파일 목록을 정리한다.
   - `find ~/vault -newer /tmp/session-marker -type f 2>/dev/null` 또는 세션 중 기록한 파일 목록 활용.
2. **요약 생성**: 3줄 이내로 세션 핵심 내용을 요약한다.
3. **저장 제안**: `00_Inbox/YYYY-MM-DD-session-wrapup.md`로 저장할지 사용자에게 묻는다.
4. **저장 시 포맷**:
   ```markdown
   ---
   created: YYYY-MM-DD
   tags: [session-wrapup]
   ---
   # Session Wrapup — YYYY-MM-DD

   ## 요약
   {3줄 요약}

   ## 생성/수정된 파일
   - [[path/to/file1]]
   - [[path/to/file2]]
   ```

## 규칙

- 한국어로 응답한다.
