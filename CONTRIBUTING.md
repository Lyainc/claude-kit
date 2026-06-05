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

## Code Review Rounds (round cap policy)

CI claude-code-review와 사람 리뷰 모두 무한 수렴(끝없는 nit 핑퐁)을 막기 위해 종료조건을 둡니다 (#169).

- **severity 분류 강제**: 모든 리뷰 지적은 P0(blocking) / P1(should-fix) / P2(nit) 중 하나로 태깅합니다.
- **추가 라운드 트리거**: 미해결 **P0/P1만** 그 PR에서 추가 리뷰 라운드를 정당화합니다. **P2 nit은 추가 라운드를 요구하지 않습니다.**
- **P2 nit defer (silent drop 금지)**: P2는 그 PR에서 고치지 말고 PR당 하나의 백로그 이슈(`chore: deferred review nits PR #N`)로 묶습니다. 메인테이너가 그 이슈를 triage합니다.
- **재지적 금지**: 이전 라운드에서 이미 다뤘거나 해결된 지적은 다시 제기하지 않습니다.
- **shift-left 경계**: substantive(P0/P1) 품질 게이팅의 1차 책임은 프리푸시 quality 게이트(#134)에 있고, CI 리뷰는 그것이 놓친 것을 잡는 fresh-eyes 안전망입니다 — 같은 규칙을 CI에서 재정의하지 않습니다.

## 개발 가이드

[CLAUDE.md](CLAUDE.md) 참조
