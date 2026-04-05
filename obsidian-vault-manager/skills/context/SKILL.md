---
name: context
description: "특정 도메인의 기존 노트와 맥락을 로드한다. 사용 예: '/context kubernetes'"
allowed-tools: Read Bash Glob Grep
context: fork
agent: Explore
---

`$ARGUMENTS` 도메인의 맥락을 로드한다.

## 절차

1. `~/vault/10_MOC/$ARGUMENTS.md` (또는 유사 이름)를 읽는다.
   - MOC가 없으면 `mdfind -onlyin ~/vault "$ARGUMENTS"` 로 관련 노트를 검색한다.
2. MOC에 링크된 노트들의 제목과 태그를 수집한다.
3. 최근 수정된 관련 노트를 우선 표시한다.
4. 결과를 정리하여 출력한다:
   ```
   ## {domain} 도메인 맥락

   ### MOC: 10_MOC/{domain}.md
   - 노트 N개 연결됨

   ### 관련 노트 (최근 수정순)
   1. note-a.md — 2025-01-15
   2. note-b.md — 2025-01-10

   무엇을 작업할까요?
   ```

## 규칙

- 읽기 전용 작업이므로 파일을 수정하지 않는다.
- 한국어로 응답한다.
