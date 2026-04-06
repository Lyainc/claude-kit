---
name: wrapup
description: "세션에서 작업한 내용을 요약하고 Inbox에 세션 정리 노트를 저장한다. 사용 예: '/wrapup', '/wrapup --hours 3'"
allowed-tools: Read Write Bash Glob
---

현재 세션에서 생성/수정한 파일들을 요약한다.

## 절차

1. **파일 변경 추적**: 세션 중 생성/수정한 파일 목록을 정리한다.
   - 대화 컨텍스트에서 이번 세션에 생성/수정한 파일 경로들을 수집한다.
   - 컨텍스트에 기록이 없으면 `find ~/vault -mmin -{minutes} -type f -not -path '*/\.*'` 로 최근 변경 파일을 탐색한다. (`{minutes}` = `--hours N` 값 × 60, 기본: 60분)
2. **요약 생성**: 3줄 이내로 세션 핵심 내용을 요약한다.
3. **저장 제안**: `00_Inbox/YYYY-MM-DD-session-wrapup.md`로 저장할지 사용자에게 묻는다.
   - `--no-save` 옵션이 있으면 이 단계를 건너뛰고 요약만 출력한다.
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

## Metrics

저장 시 파일 목록 외에 작업 메트릭을 포함한다:

```markdown
## Metrics
- 생성: {N}개 파일
- 수정: {N}개 파일
- 이동: {N}개 파일
- 삭제: {N}개 파일
- MOC 업데이트: {N}건
```

## Options

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--hours N` | 파일 변경 탐색 범위 (양의 정수, min 1, max 24. 범위 밖/비숫자 → 기본 1) | 1 |
| `--no-save` | 요약만 출력, 파일 저장 안 함 | false |
