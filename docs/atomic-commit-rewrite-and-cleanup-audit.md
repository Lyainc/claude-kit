# 원자적 커밋 재구성과 정리 점검 영수증

미공개 변경을 claude-kit 8개, local-harness 5개 원자적 커밋으로 재구성했고, 두 저장소의 main 교체가 완료됐어요. `reconstruction.json`의 두 `activated` 값은 모두 `true`예요. 최종 파일 트리는 기존 묶음 커밋과 같고, 변경 목적별 이력만 분리했어요.

이 영수증은 재구성한 13개 커밋만 증명해요. 새 P3 정책(`9453fb0`), kit AGENTS 지침(`ad31246`), 연구 문서(`10e7412`)는 별도 후속 커밋으로 완료됐고, 이 13개 재구성 범위에 포함하지 않아요. 이 영수증의 저장 커밋은 별도예요.

## 재구성 기준과 복구 지점

| 저장소 | 기존 기준(base) | 기존 끝(old tip) | 새 끝(new tip) | 동일한 최종 tree | 복구 ref |
|---|---|---|---|---|---|
| claude-kit | `944ab951a119f7c3320cbc83d2d2154eb206fd2f` | `bdf385731ab6d8ac5c3ca42d3f1204affb11de57` | `044346a9c3c5df7e1995ef32c85c550b0630a5c3` | `e16800c369e876fdbb085ba3e086e71309eadfc1` | `refs/backup/atomic-split-20260916/kit` |
| local-harness | `a7797a2b2bd817d5073b2579509362059eb623ad` | `1fbf937d0233705a2f9061c0e0fbbee90ff8fd81` | `c52271588e19f8515e4d8a1eb484f505420af479` | `7c780a4a1580d6e3a7aef964a6c40d8674bdc98d` | `refs/backup/atomic-split-20260916/harness` |

각 복구 ref는 기존 tip을 보존해요. 사용자 worktree의 branch·HEAD·미커밋 상태와 기존 stash는 재구성 전후 그대로 유지됐어요. 임시 재구성 worktree는 아래 경로를 사용했어요.

- kit: `/private/tmp/atomic-rewrite-20260916/kit-worktree`
- harness: `/private/tmp/atomic-rewrite-20260916/harness-worktree`

## 분리한 커밋

| 저장소 | 순서 | 짧은 SHA | 목적 |
|---|---:|---|---|
| claude-kit | 1 | `96405a5` | 응집된 완료조건과 후보 판단 계약 — `refactor(next-goal): define cohesive completion conditions` |
| claude-kit | 2 | `03e558f` | 필요 없는 백로그 수집 지연 — `perf(next-goal): defer unused backlog collection` |
| claude-kit | 3 | `5aa1199` | 스킬 목록과 본문 예산 회귀 분리 — `test(budget): separate listing and invocation regressions` |
| claude-kit | 4 | `038cd95` | 네이티브 정책 배치와 hook 승인 경계 — `fix(feedback-loop): preserve native policy and hook gates` |
| claude-kit | 5 | `39c2057` | 승인된 Git 완료조건 복원 — `fix(next-goal): preserve authorized Git completion` |
| claude-kit | 6 | `381e447` | 실제 loop·hook 실행 증거 검사 — `test(native): verify loop and hook execution evidence` |
| claude-kit | 7 | `0320a02` | 미적용 전역 지침 변경 위험 보고 — `docs(safety): assess pending native instruction changes` |
| claude-kit | 8 | `044346a` | 네이티브 loop와 종료 검증 기록 — `docs(validation): record native loop and closure evidence` |
| local-harness | 1 | `ded3b98` | 최소 크기·위임 할당 없이 유용한 범위 선택 — `fix(policy): permit useful bounded delegation without scope floors` |
| local-harness | 2 | `54eac1f` | 호출 방식 전체의 검증 라운드 제한 — `fix(policy): bound verification across review methods` |
| local-harness | 3 | `7e6cffa` | runtime 참조 지연 로딩과 종료 수집 재사용 — `refactor(session-close): load runtime workflows lazily` |
| local-harness | 4 | `ca2bc50` | 공통 Git 완료 backstop과 PR 준비도 복원 — `fix(session-close): restore shared git completion backstop` |
| local-harness | 5 | `c522715` | 관리 가능한 네이티브 Codex 지침 원본 — `feat(codex): add managed native instruction source` |

## 사용자 작업 보존

아래는 재구성 전 상태로 저장된 사용자 작업이에요. main 이력과 별개로 보존했고, 재구성에서 stage·commit·삭제하지 않았어요.

| 저장소 | 사용자 worktree | 보존한 상태 |
|---|---|---|
| claude-kit | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/agent-spawn-delegation` | 삭제 표시 3개와 수정 파일 4개 |
| claude-kit | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/fix-infra-recovered` | 미추적 `.verify-out.json` |
| claude-kit | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/fix-trash-put-738` | 깨끗한 작업트리 |
| claude-kit | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/gar` | 깨끗한 작업트리 |
| local-harness | `/Users/Lyainc/dev/prj/local-harness/.worktrees/skill-bindings-737` | 수정된 `rules/check-skill-bindings.sh` |
| local-harness | `/Users/Lyainc/dev/prj/local-harness/.worktrees/unused-policy-retirement` | 깨끗한 작업트리 |

기존 stash도 동일하게 보존했어요.

- claude-kit: `2879ded65620c290b3a5dff8b101cb3d415589c4`
- local-harness: `41938b24c416fe266e7c9121b6c3a7286b237415`

## 역사적 session-close dogfooding과 13개 보존 후보

종료 점검은 기존 SHA에서 수행한 역사적 실행 증거예요. claude-kit 실행 시점은 `519d69cbd70cc78374ea87eaff6ab05b9a1a0842`, local-harness는 `1fbf937d0233705a2f9061c0e0fbbee90ff8fd81`이고, kit의 최종 영수증 커밋은 `bdf385731ab6d8ac5c3ca42d3f1204affb11de57`예요. 이 기록은 이력 재구성 후에도 당시 실행 근거로 유효하지만, 새 SHA에서 live 재실행한 결과는 아니에요. 아래 표 역시 그때 수집한 sweep 결과이며 현재 삭제 승인을 대신하지 않아요.

정확히 13개 후보가 모두 `qualifies:false`였어요. 9개의 `ancestry_count=0`은 작업 완료 증명이 아니에요. dirty 작업트리와 통합되지 않은 커밋은 별도로 구분해 보존해요.

| 저장소 | branch | worktree 경로 또는 없음 | qualifies | false 사유 |
|---|---|---|---|---|
| claude-kit | `fix/706-delegation-distribution` | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/agent-spawn-delegation` | `false` | ancestry=0: 완료·통합 증명 없음; dirty 작업트리; cherry_clean=false |
| claude-kit | `Lyainc/fix-infra-next-goal-l2-seed` | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/fix-infra-recovered` | `false` | dirty 작업트리; cherry_clean=true여도 미커밋 작업 보호 |
| claude-kit | `fix/738-trash-put-absolute-path` | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/fix-trash-put-738` | `false` | 미통합 커밋: cherry_clean=false |
| claude-kit | `Lyainc/chore-ponytail-full-2` | `/Users/Lyainc/dev/prj/claude-kit/.claude/worktrees/claude-kit/gar` | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/chore-enable-ponytail-full` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/chore-enable-ponytail-full-2` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/chore-enable-ponytail-full-3` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/chore-ponytail-full` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/enable-ponytail-full` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/enable-ponytail-mode` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| claude-kit | `Lyainc/ponytail-full-mode` | 없음 | `false` | ancestry=0: 완료·통합 증명 없음; cherry_clean=false |
| local-harness | `feat/737-skill-bindings` | `/Users/Lyainc/dev/prj/local-harness/.worktrees/skill-bindings-737` | `false` | dirty 작업트리; 미통합 커밋: cherry_clean=false |
| local-harness | `feat/unused-policy-retirement` | `/Users/Lyainc/dev/prj/local-harness/.worktrees/unused-policy-retirement` | `false` | 미통합 커밋: cherry_clean=false |

원래 dogfooding에서 push·PR 생성·merge·삭제·이슈 쓰기는 모두 0건이었어요. 이번 재구성도 push·PR 생성·merge와 사용자 작업 정리를 수행하지 않았어요. 공개·삭제 권한을 이력 재구성 권한으로 확장하지 않았어요.

## 검사와 원본 보존

기존 commit hook은 생략하거나 우회하지 않고 13개 커밋 모두에서 정상 실행했어요. 주 작업 컨텍스트가 확인한 로그는 `/private/tmp/atomic-rewrite-20260916/` 아래에 있어요.

| 로그 | 확인 결과 |
|---|---|
| `harness-1-commit.log`, `harness-2-commit.log` | `rules/: all suites passed` |
| `kit-2-check-1.log` | hook 21 cases 통과 |
| `kit-3-check-1.log` | budget 65 cases 통과 |
| `kit-4-check-1.log` | portability 19개 통과 |
| `kit-4-check-2.log` | feedback contracts 3개 통과 |
| `kit-4-check-3.log` | version sync clean |
| `harness-3-check-1.log`, `harness-4-check-1.log` | adapter PASS |

역사적 dogfooding 로그는 `/private/tmp/session-close-git-dogfood-20260915-145626/`에 있어요.

기존 최종 Codex reference의 EOF 빈 줄은 정확한 tree 보존을 위해 유지했어요. 재구성의 whitespace 검사는 `core.whitespace=-blank-at-eof` 조건으로 수행했어요. 새 문서나 동작 변경을 숨기기 위한 예외가 아니며, 다른 내용은 원본 최종 tree와 같아요.

## 근거와 범위

- 재구성과 활성화: `/private/tmp/atomic-rewrite-20260916/reconstruction.json`
- 종료 sweep: `/private/tmp/session-close-git-dogfood-20260915-145626/summary.json`

이 문서 작성은 위 두 JSON과 주 작업 컨텍스트의 재구성 완료·보존·hook 실행 확인만 사용했어요. 문서 작성 과정에서는 Git 명령, 저장소 수정, ref 변경, cleanup을 수행하지 않았어요.
