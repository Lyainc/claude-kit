---
name: context
description: "Load existing notes and context for a specific domain. Example: '/context kubernetes', '/context devops,kubernetes --exclude private'"
allowed-tools: Read Bash Glob Grep
context: fork
agent: Explore
---

`$ARGUMENTS` 도메인의 맥락을 로드한다.

## 절차

1. `~/vault/10_MOC/$ARGUMENTS.md` (또는 유사 이름)를 읽는다.
   - MOC가 없으면 플랫폼에 따라 검색:
     - macOS (`uname -s` = `Darwin`): `mdfind -onlyin ~/vault "$ARGUMENTS"`
     - 그 외: `grep -rl "$ARGUMENTS" ~/vault --include="*.md"`
   - **크로스도메인**: `$ARGUMENTS`에 쉼표가 포함되면 (예: `devops,kubernetes`) 각 도메인을 개별 조회 후 결과를 병합한다.
2. MOC에 링크된 노트들의 제목과 태그를 수집한다.
3. 해당 도메인에 `status: active`인 handoff 노트가 있으면 "진행 중인 작업" 섹션으로 우선 표시한다.
4. 최근 수정된 관련 노트를 우선 표시한다.
5. 결과를 정리하여 출력한다:
   ```
   ## {domain} 도메인 맥락

   ### 진행 중인 작업
   - handoff-2025-01-15.md — {현재 상태 요약}

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

## Options

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--exclude {tag}` | 지정 태그의 노트 제외 | `/context kubernetes --exclude private` |
| `--limit N` | 표시할 최대 노트 수 (양의 정수, 기본: 20) | `/context devops --limit 10` |

**Validation**: `--limit`은 양의 정수만 허용 (0 이하/비숫자 → 기본값 20). `--exclude`에 존재하지 않는 태그 지정 시 무시하고 계속 진행.
