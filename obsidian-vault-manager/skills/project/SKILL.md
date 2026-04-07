---
name: project
description: "Create a new project and register it in Home.md. Example: '/project api-gateway'"
allowed-tools: Read Write Edit Bash Glob
---

`$ARGUMENTS` 이름으로 새 프로젝트를 생성한다.

## 절차

1. **중복 확인**: `~/vault/20_Projects/$ARGUMENTS/` 존재 여부 확인.
   - 이미 있으면 사용자에게 알리고 중단.
2. **디렉토리 + _index.md 생성**:
   ```
   ~/vault/20_Projects/{project-name}/_index.md
   ```
   ```markdown
   ---
   created: YYYY-MM-DD
   status: active
   ---
   # {Project Name}
   ## Overview
   ## Goals
   ## Outputs
   ## Related Notes
   ```
3. **Home.md 업데이트**: "Active Projects" 섹션에 `[[20_Projects/{project-name}/_index|{Project Name}]]` 링크 추가.
4. **결과 출력**: 생성된 경로.

## 규칙

- 사용자 확인 후에 생성한다 (계획을 먼저 보여준다).
- 한국어로 응답한다.
