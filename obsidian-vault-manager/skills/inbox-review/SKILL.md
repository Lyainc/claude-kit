---
name: inbox-review
description: "Organize Inbox notes. Shows a batch list and decides move/delete/keep by number selection. Example: '/inbox-review'"
allowed-tools: Read Write Edit Bash Glob Grep
---

`~/vault/00_Inbox/`에 있는 파일들을 정리한다.

## 절차

1. **목록 조회**: `ls -1t ~/vault/00_Inbox/` 로 전체 파일 목록을 날짜순으로 가져온다.
   - 파일이 없으면 "인박스가 비어 있습니다" 출력 후 종료.
2. **일괄 표시**: 전체 목록을 번호와 함께 표시한다. 각 항목에 파일명 + 첫 5줄 미리보기 (frontmatter 제외)를 포함한다.
   ```
   1. 2025-01-15-api-design.md — API 설계 회의에서 나온 ...
   2. 2025-01-14-todo.md — 이번 주 할 일 목록 ...
   3. 2025-01-13-idea.md — 새로운 기능 아이디어 ...
   ```
3. **사용자 선택 대기**: 사용자가 번호와 액션을 지정할 수 있게 한다.
   - 예: "1,3 → Notes로 이동", "2 → 삭제", "나머지 유지"
4. **이동 처리** (Notes로 이동 시):
   - 도메인을 판별하고 `30_Notes/{topic}.md`로 이동
   - 동명 파일 충돌 시 사용자에게 확인
   - 관련 MOC에 백링크 추가
5. **삭제 처리**: 삭제 전 최종 확인을 받는다.

## 규칙

- 하나씩 묻지 않고 일괄 목록을 먼저 보여준다 (대화 턴 절약).
- 사용자가 한 번에 여러 항목을 처리할 수 있도록 한다.
- 한국어로 응답한다.

## Input Grammar

사용자 입력은 다음 형식을 인식한다:

| 형식 | 예시 | 해석 |
|------|------|------|
| `{번호} → Notes` | `1,3 → Notes로 이동` | 지정 항목을 30_Notes/로 이동 |
| `{번호} → 삭제` | `2 → 삭제` | 사용자에게 수동 삭제를 안내 (vault-file-organizer는 삭제 불가) |
| `{번호} → {project}` | `4 → api-project` | 지정 항목을 20_Projects/{project}/로 이동 |
| `나머지 유지` / `keep rest` | `나머지 유지` | 미지정 항목은 Inbox에 유지 |
| `전체 이동` / `move all` | `전체 Notes로` | 모든 항목을 30_Notes/로 이동 |

**인식 불가 입력 시**: "입력을 이해하지 못했습니다. 예: `1,3 → Notes로 이동`" 출력 후 재입력 대기.
