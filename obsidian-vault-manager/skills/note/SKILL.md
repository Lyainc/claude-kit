---
name: note
description: "새 노트를 생성하고 관련 MOC에 연결한다. 사용 예: '/note kubernetes 네트워킹 기초'"
allowed-tools: Read Write Edit Bash Glob Grep
---

`$ARGUMENTS` 주제로 `~/vault/30_Notes/`에 새 노트를 생성한다.

## 절차

1. **도메인 판별**: 주제에서 관련 도메인을 결정한다.
2. **중복 확인**: `mdfind -onlyin ~/vault/30_Notes "$ARGUMENTS"` 또는 `ls ~/vault/30_Notes/ | grep -i {keyword}`로 기존 노트 확인.
   - 동일/유사 노트가 있으면 사용자에게 알리고 덮어쓰기/이름변경/병합 중 선택 요청.
3. **파일 생성**: `30_Notes/{topic-in-kebab-case}.md`
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [domain, keyword]
   ---
   ```
4. **MOC 연결**:
   - `10_MOC/{domain}.md`가 있으면 → 백링크 추가
   - 없으면 → 새 도메인 MOC 생성 후 `Home.md`에도 링크 추가 (사용자 확인 필요)
   - 여러 도메인에 걸치면 → 모든 관련 MOC에 링크
5. **결과 출력**: 생성된 파일 경로 + 업데이트된 MOC 목록

## 규칙

- `30_Notes/` 안에 하위 폴더를 만들지 않는다.
- 사용자 확인 후에 파일을 생성한다 (생성 계획을 먼저 보여준다).
- 한국어로 응답한다.
