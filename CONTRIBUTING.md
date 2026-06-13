# Contributing

claude-kit에 기여해주셔서 감사합니다.

## Commit Convention

Conventional Commits 사용 (영어):

```text
feat: Add new skill
fix: Resolve issue
docs: Update README
refactor: Simplify code
```

커밋 메시지는 릴리즈 노트의 1차 소스입니다 (`scripts/gen-release-notes.py`가 파싱).
`feat:`→Added, `fix:`→Fixed, `refactor:`/`perf:`→Changed, `feat!:`/`BREAKING CHANGE:`→
Breaking Changes로 분류되고, 변경한 파일 경로로 플러그인 섹션이 정해집니다. scope는
가능하면 플러그인 단위로 (`feat(vault-bridge): ...`). 자세한 매핑은 [RELEASING.md](RELEASING.md) 참조.

## Code Review Rounds (round cap policy)

CI claude-code-review와 사람 리뷰 모두 무한 수렴(끝없는 nit 핑퐁)을 막기 위해 종료조건을 둡니다 (#169).

- **severity 분류 강제**: 모든 리뷰 지적은 P0(blocking) / P1(should-fix) / P2(nit) 중 하나로 태깅합니다.
- **추가 라운드 트리거**: 미해결 **P0/P1만** 그 PR에서 추가 리뷰 라운드를 정당화합니다. **P2 nit은 추가 라운드를 요구하지 않습니다.**
- **P2 nit defer (silent drop 금지)**: P2는 그 PR에서 고치지 말고 PR당 하나의 백로그 이슈(`chore: deferred review nits PR #N`)로 묶습니다. 메인테이너가 그 이슈를 triage합니다.
- **재지적 금지**: 이전 라운드에서 이미 다뤘거나 해결된 지적은 다시 제기하지 않습니다.
- **shift-left 경계**: substantive(P0/P1) 품질 게이팅의 1차 책임은 프리푸시 quality 게이트(#134)에 있고, CI 리뷰는 그것이 놓친 것을 잡는 fresh-eyes 안전망입니다 — 같은 규칙을 CI에서 재정의하지 않습니다.
- **Self-review 제약**: `claude-code-review.yml` 기반 self-review 시에도 코드 작성자 스스로 무한정 라운드를 반복하지 않도록, 미해결 P0/P1에 대해서만 추가 라운드를 허용하는 제약을 따릅니다.

## Issue Labels

최소 세트로 유지합니다 (두문자어 없이 직관적으로):

- **type**: `bug` / `enhancement` / `documentation` / `redesign`(레이어 재설계)
- **priority**: `priority: high`(지금 처리) — 나머지는 라벨 없음(=보통)
- **status**: `backlog`(나중·결정 보류), `duplicate`

이슈 제목은 Conventional Commit prefix를 그대로 씁니다 (`feat:`/`fix:`/`docs:`/`chore:`/
`refactor:`/`decide:`/`design:`). 추적 ID 체계(U/P/W/G 등)는 별도 정리 대상입니다 (#214).

## Releasing

claude-kit은 lockstep 릴리즈입니다 — 모든 플러그인이 같은 버전을 공유하고 단일 태그
`vX.Y.Z`로 함께 배포됩니다. 릴리즈는 Actions 탭의 `Release` 워크플로(workflow_dispatch)로
수동 실행합니다. 버전 정책·SemVer 판단·절차는 [RELEASING.md](RELEASING.md) 참조.

## 개발 가이드

[CLAUDE.md](CLAUDE.md) 참조
