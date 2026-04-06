---
name: archive
description: "프로젝트를 아카이브하고 관련 MOC/Home.md를 정리한다. 사용 예: '/archive api-gateway'"
allowed-tools: Read Write Edit Bash Glob Grep
---

`$ARGUMENTS` 프로젝트를 아카이브한다.

## 절차

1. **프로젝트 확인**: `~/vault/20_Projects/$ARGUMENTS/` 디렉토리 존재 여부를 확인한다.
   - 없으면: "프로젝트를 찾을 수 없습니다: $ARGUMENTS" 출력 후 종료.
   - `_index.md`의 `status` frontmatter를 확인한다. (필수 형식: `status: active|completed|archived`. 없으면 경고 후 `active`로 간주)
2. **상태 확인**: 현재 상태가 `active`인지 확인한다.
   - 이미 `archived`이면: "이미 아카이브된 프로젝트입니다" 출력 후 종료.
3. **아카이브 계획 제시**: 사용자에게 아카이브 계획을 보여주고 확인을 받는다:
   ```
   ## 아카이브 계획 — {project-name}

   1. 20_Projects/{name}/ → 50_Archive/{name}/ 이동
   2. _index.md status: active → archived 변경
   3. Home.md "Active Projects"에서 링크 제거
   4. 관련 30_Notes/ 노트의 MOC 링크는 유지 (노트 이동 없음)

   진행할까요?
   ```
4. **실행** (사용자 확인 후):
   a. `_index.md`의 `status`를 `archived`로 변경, `archived` 날짜 추가
   b. `20_Projects/{name}/` → `50_Archive/{name}/`으로 이동
   c. `Home.md`의 "Active Projects" 섹션에서 해당 링크 제거
   d. 관련 MOC에서 프로젝트 참조가 있으면 `(archived)` 표시 추가
5. **결과 출력**:
   ```
   ✓ 아카이브 완료: {project-name}
     - 이동: 50_Archive/{name}/
     - Home.md 업데이트 완료
     - 관련 노트 MOC 링크 유지됨
   ```

## Status Lifecycle

```
active → completed → archived
```

- `active`: 진행 중인 프로젝트
- `completed`: 작업 완료, 아직 vault에 활성 상태
- `archived`: 50_Archive/로 이동 완료

`/archive`는 `active` 또는 `completed` 상태의 프로젝트를 `archived`로 전환한다.

## 규칙

- 아카이브 전 반드시 사용자 확인을 받는다.
- `30_Notes/`의 노트는 이동하지 않는다 — MOC 링크만 유지.
- 한국어로 응답한다.
