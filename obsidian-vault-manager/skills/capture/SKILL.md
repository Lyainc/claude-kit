---
name: capture
description: "빠른 메모 캡처. 즉시 Inbox에 저장하고 파일 경로만 출력한다. 사용 예: '/capture 오늘 회의에서 나온 API 변경 사항'"
allowed-tools: Read Write Bash
---

$ARGUMENTS 내용을 즉시 `~/vault/00_Inbox/`에 저장한다.

## 규칙

1. 파일명: `YYYY-MM-DD-{2-3 word topic summary in kebab-case}.md`
2. frontmatter:
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [inbox]
   ---
   ```
3. 본문에 `$ARGUMENTS` 내용을 기록한다.
4. **디렉토리 검증**: `~/vault/00_Inbox/`가 없으면 자동 생성(`mkdir -p`)한다.
5. **중복 감지**: 동일 날짜+토픽 파일이 이미 존재하면 파일명 뒤에 `-v2`, `-v3` 등을 붙인다.
6. **확인 없이 즉시 저장**한다. 이것이 이 skill의 핵심이다.
7. 출력은 저장된 파일 경로만. 후속 질문 없음.
8. 한국어로 응답한다.
