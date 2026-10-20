# Seed 수명주기 승인 쓰기 실행 검증 · 2026-10-20

## 범위와 기준

`docs/specs/seed-lifecycle-residual-validation.yaml`(#814)의 acceptance-3만 검증했다.
실제 사용자 답변과 제한된 fixture의 before/after·공통 검증 결과로 승인된 수명주기 쓰기를 확인하는
항목이다. 검증 전에 `seed-relations.py metadata`로 대상을 읽었고, 상태는 active, 적격(eligible)이었다.
기준 SHA는 `origin/main` 908fb7c이고 작업 브랜치는 `feat/seed-lifecycle-approved-writes`다.
검증기는 이 worktree의 `thinking-tools/scripts` 소스이며 main과 같다. 실행 중에는 빈 prior를
새 Seed로 보는 임시 수정을 넣어 검증했지만 리뷰 후 되돌렸다(아래 "빈 prior 관찰"). 그 수정은
빈 prior 경로만 바꿨고 쓰기 2~6과 거부 사례의 prior는 모두 비어 있지 않았으므로 해당 결과는 main
검증기와 같다. 쓰기 1은 되돌린 main 검증기로 다시 검증했다.

제외한 범위는 다음과 같다.

- acceptance-2의 Codex 트레이스 실행
- acceptance-4
- 설치된 플러그인 캐시 실행
- local-harness와 session-close 경로

설치본은 수정하지 않았다. 나머지 Seed 요구를 새로 완료 판정하지 않는다.

fixture는 세션 scratchpad에 만든 합성 git 저장소이며 이 저장소에는 커밋하지 않았다. 최신
`skills/build-spec/templates/SEED_SPEC.yaml`(헤더 계약, version 7.2.0, relations version 3)로
Seed를 만들었다. 사용자가 fixture Seed를 최신 build-spec으로 갱신하라고 요청해서, 쓰기 전에
있던 더 작은 초기 fixture(커밋 3536a1a, 테스트 헬퍼 형태)는 폐기하고 교체했다. 기준 커밋은
`20b211909eb9a6ee6e7371095c625ce96692df63`(fx-parent-a, fx-parent-b)이다. fixture 커밋은
6aedad6(쓰기 1), 29c9606(쓰기 2), eadac7d(쓰기 3), f9eca18(쓰기 4 분할 중간 상태),
f367cd9(쓰기 4), 3b0955a(쓰기 5), 71df750(쓰기 6)이다.

## 소스·설치·런타임 구분

| 구분 | 직접 관찰 | 범위·한계 |
|---|---|---|
| 합성 fixture 실행 | 이 worktree 소스의 `seed-lifecycle.py check --before`, `seed-relations.py check`를 쓰기마다 실행 | 합성 Seed에 대한 소스 검증기 실행 증거다. 제품 Seed가 아니다 |
| 라이브 런타임 훅 | Claude Edit 도구로 쓴 쓰기 2, 3, 4(최종), 5, 6과 거부 R1~R3이 훅을 통과하거나 거부됨 | 훅의 출처는 추론이다. 설치 캐시 thinking-tools 6.0.0/6.0.2에는 kept_provenance와 append-only 메시지가 없다. marketplace Lyainc-claude-kit은 메인 체크아웃(`/Users/Lyainc/dev/prj/claude-kit`, main 908fb7c)을 가리키는 디렉터리 소스이고 거부 문구가 거기에만 있어서, 라이브 훅은 그 메인 체크아웃 소스에서 실행됐을 가능성이 가장 크다. `CLAUDE_PLUGIN_ROOT`는 직접 관찰하지 못했다 |
| 소스 훅 함수 | worktree의 `seed-append-check.py`를 Write 페이로드로 호출 (거부 R1~R3) | 라이브 훅과 별개의 소스 실행이다 |
| 설치 캐시 | 실행하지 않음 | 설치 캐시 실행을 주장하지 않는다 |

## 실제 승인

승인은 `AskUserQuestion`의 실제 사용자 답변이다. 처음 묶음(쓰기 1~4)은 사용자가 도구 호출을
거절하고 내용을 명확히 하도록 요청했으므로 쓰기를 하나도 하지 않고 보류했다. 같은 내용을 다시
물어 쓰기 1~4는 "승인", 쓰기 5~6은 "승인"이라는 답을 받았다. fixture의 `approved_by` 문자열은
이 답변을 인용한다. 아래 해시는 sha256이고 exit는 각각 `seed-lifecycle.py check --before <prior>`와
`seed-relations.py check`의 종료 코드다. `<prior>`는 쓰기 전 내용을 mktemp로 보존한 파일이다.
신규 파일인 쓰기 1의 fx-child만 문서화된 절차대로 `--before` 없이 검사했다.

| 쓰기 | 대상 | 사용자 답변 | 쓰기 경로 | before | after | seed-lifecycle exit | seed-relations exit |
|---|---|---|---|---|---|---|---|
| 1 신규 활성화 | fx-child.yaml | 승인 | 파일 복사 | (없음) | `5d136acfc09d0fa7c1fd3fb9eb2ce47153213e7def7473b3c501ea388ad7856e` | 0 | 0 |
| 1 부모 링크 | fx-parent-a.yaml | 승인 | python 스크립트 | `8f0dc99cbf414675db69b9ac9277a3e54c6e4c8f1c81827086ae20390864f085` | `64af5d19bc721cbb2efbcb51c5ffffeb0d5d0c98cdc301a6960444373bd1602f` | 0 | 0 |
| 2 active→paused | fx-child.yaml | 승인 | Edit 도구 | `5d136acfc09d0fa7c1fd3fb9eb2ce47153213e7def7473b3c501ea388ad7856e` | `21756f90e22247c98ab89e1d66d483326d934d7008e8f16403d09eb3cde6c9fa` | 0 | 0 |
| 3 항목 철회(constraint-2) | fx-child.yaml | 승인 | Edit 도구 | `21756f90e22247c98ab89e1d66d483326d934d7008e8f16403d09eb3cde6c9fa` | `c54165aa9304e39f746d76b3130ca173b1ac1ce6c85f60c51f4ef148acd0d975` | 0 | 0 |
| 4 재연결 (단일 Edit) | fx-child.yaml | 승인 | Edit 도구 | `c54165aa9304e39f746d76b3130ca173b1ac1ce6c85f60c51f4ef148acd0d975` | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` | 0 | 0 |
| 4 이전 부모 A | fx-parent-a.yaml | 승인 | python 스크립트 | `64af5d19bc721cbb2efbcb51c5ffffeb0d5d0c98cdc301a6960444373bd1602f` | `8f0dc99cbf414675db69b9ac9277a3e54c6e4c8f1c81827086ae20390864f085` | 0 | 0 |
| 4 새 부모 B | fx-parent-b.yaml | 승인 | python 스크립트 | `32c245381f179f27acde557440aa2ff59d5a31042075b14a9984d2ce07cfef5c` | `e8ef63de478907ab0fad8996ee09d03fac27d290860cbd89d06be29d9eab4d93` | 0 | 0 |
| 5 completed 종료 | fx-child.yaml | 승인 | Edit 도구 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` | `e778e6b5629d68dc499b2333e4809d7ed89fe57b8a8ba98911566f425843d006` | 0 | 0 |
| 6 discontinued 종료 | fx-parent-a.yaml | 승인 | Edit 도구 | `8f0dc99cbf414675db69b9ac9277a3e54c6e4c8f1c81827086ae20390864f085` | `aea71262d538b682bf5664761aeb16cbe5a5584db1a66791cb4bad9fc516eff3` | 0 | 0 |

쓰기 4의 부모 A와 B 행은 child 재수행 뒤 최종 상태에서 측정한 값이다. 관찰 결과는 다음과 같다.

- 쓰기 1: 두 파일 모두 exit 0, fx-child는 `OK: 2 edge(s) consistent`, fx-parent-a는 `OK: 1 edge(s) consistent`
- 쓰기 2: `eligible: false, reason: paused`, `OK: 2 edge(s) consistent`
- 쓰기 3: `excluded_items: ["constraint-2"]`
- 쓰기 4: 새 부모 B에서 `OK: 1 edge(s) consistent`, 이전 부모 A에서 `OK: 0 edge(s) consistent`
- 쓰기 5: `closed: completed`
- 쓰기 6: `closed: discontinued`

모든 seed-relations 출력에는 `UNRECORDED ... issues.source is not recorded`가 포함된다. 합성
fixture에 이슈 출처가 없어서 나온 알림이며 실패가 아니다.

쓰기 1의 자식 파일은 파일 복사로 만들었고, 부모의 children 목록 수정(쓰기 1, 4)은 python
스크립트로 했다. 이 경로들은 런타임 훅을 거치지 않았다. 쓰기 2, 3, 4(최종), 5, 6은 Claude Edit
도구로 써서 라이브 훅을 통과했다.

## 빈 prior 관찰

쓰기 1에서 새 Seed를 `seed-lifecycle.py check <new> --before <빈 mktemp prior>`로 검사하면
exit 1과 `lifecycle transition must preserve original requirement contents and IDs`가 나온다.
빈 prior가 요구 항목 없는 기존 Seed로 파싱되기 때문이다. 편집 훅은 없는 파일의 전이 검사를 건너뛰므로
두 경로의 판정이 다르다.

이를 결함으로 보고 빈 prior를 새 Seed로 처리하는 수정을 시도했지만 되돌렸다. 검증기는 "원래 없던
파일"과 "보존에 실패해 비어 버린 기존 파일의 prior"를 구별할 수 없다. 그 수정은 후자에서 닫힌 Seed의
재작성까지 전이 검사 없이 통과시킨다. 현재 동작은 그 경우를 거부하므로 안전한 쪽의 실패다.
신규 파일은 문서화된 절차(`build-spec/reference.md`의 "For a new file omit `--before`")대로 `--before`를
생략한다.

main 검증기로 쓰기 1 상태(fixture 커밋 6aedad6, fx-child sha256
`5d136acfc09d0fa7c1fd3fb9eb2ce47153213e7def7473b3c501ea388ad7856e`)를 다시 확인했다.

| 명령 | exit | 출력 |
|---|---|---|
| `seed-lifecycle.py check fx-child.yaml` (`--before` 생략) | 0 | `OK: lifecycle valid` |
| `seed-relations.py check fx-child.yaml` | 0 | `OK: 2 edge(s) consistent` |
| `seed-lifecycle.py check fx-child.yaml --before <빈 mktemp>` | 1 | `INVALID: lifecycle transition must preserve original requirement contents and IDs` |

## 분할 Edit 관찰

쓰기 4를 Edit 두 번으로 나누어 시도했다. 첫 Edit은 `approved_by`와 `reason`만 바꿨고 훅을
통과했다. 둘째 Edit은 parent와 provenance를 바꾸는 것이었는데, 라이브 훅이
`transition requires a new explicit approval reference`로 거부했다. 훅이 직전 Edit이 끝난
파일을 기준으로 비교해서, 이미 바뀐 `approved_by`가 새 승인으로 인정되지 않았기 때문이다.

이 중간 상태(fx-child.yaml before `c54165aa9304e39f746d76b3130ca173b1ac1ce6c85f60c51f4ef148acd0d975`,
after `4bb4943a928fa5695f1f81bdd1e0a6a90fcbc64a28691d23b7d02225623648da`)를 fixture 커밋
f9eca18로 남기고 검증기를 돌렸다.

| 대상 | seed-lifecycle exit | seed-relations exit | 결과 |
|---|---|---|---|
| fx-child.yaml | 0 | 1 | `MISMATCH docs/specs/fx-parent-a.yaml children is missing docs/specs/fx-child.yaml` |
| fx-parent-a.yaml | 0 | 0 | `OK: 0 edge(s) consistent` |
| fx-parent-b.yaml | 0 | 1 | `MISMATCH docs/specs/fx-child.yaml parent does not point back to docs/specs/fx-parent-b.yaml` |

중간 상태에서는 자식 관계가 양쪽으로 불일치했다. 이후 자식을 prior(`c54165aa...`)로 복원하고
쓰기 4를 단일 Edit 하나로 다시 수행해 통과했다. 전이는 하나의 Edit/Write로 착지해야 한다.

## 거부 사례

별도 detached worktree(fixture 저장소 f367cd9)에서 확인했고 승인된 fixture는 건드리지 않았다.
세 경우의 prior는 모두 `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25`다.
후보를 제자리에 쓴 상태에서 검증기를 돌린 뒤 prior로 복원했다.

- R1 미승인 전이: paused→active로 바꾸고 reason을 바꿨지만 `approved_by`는 그대로 뒀다.
- R2 이전 reason 재사용: provenance 커밋을 20b2119에서 6aedad6으로 바꾸고 새 `approved_by`를 넣었지만 reason은 그대로 뒀다.
- R3 고정 provenance 삭제: `provenance: []`로 비웠다.

| 사례 | prior 해시 | 후보 해시 | 라이브 훅 결과 | 소스 훅 결과 | seed-lifecycle exit와 메시지 | seed-relations exit | 복원 후 해시 |
|---|---|---|---|---|---|---|---|
| R1 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` | `e15b60b0c448000b4c5b9a13269773b0d49511f67c866bd10758e581993798e0` | 거부, 파일 해시 유지: `transition requires a new explicit approval reference` | 거부: `Seed 수명주기 변경이 유효하지 않아요: transition requires a new explicit approval reference` | 1, `INVALID: transition requires a new explicit approval reference` | 0 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` |
| R2 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` | `1ae235ac6f4208839d7530671a8db95a9b2bda894d014d0163bcdbd8ddb2c445` | 거부, 파일 해시 유지: `relations.provenance row {...20b2119..., items [acceptance-1]} was dropped or rewritten; pinned provenance is append-only unless a new user approval and a new reason correct it` | 거부: 같은 provenance 메시지 | 1, `INVALID: relations.provenance row {'seed': 'docs/specs/fx-parent-a.yaml', 'commit': '20b211909eb9a6ee6e7371095c625ce96692df63', 'items': ['acceptance-1']} was dropped or rewritten; pinned provenance is append-only unless a new user approval and a new reason correct it` | 0 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` |
| R3 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` | `44ad1be965741127f0ce71c198b1d5770fb3eace9884c6b98963ee004df831e3` | 거부, 파일 해시 유지: R2와 같은 provenance 메시지 | 거부: 같은 provenance 메시지 | 1, R2와 같은 `INVALID: relations.provenance row ... pinned provenance is append-only unless a new user approval and a new reason correct it` | 0 | `e18ec251c466b0d5c7d4fa964ab77681d519a32f99e2a4430afefcda8b1c0f25` |

거부를 만든 검사는 `seed-lifecycle.py`와 편집 훅이다. `seed-relations.py check`는 세 후보
모두 exit 0이다. 이 검사는 관계 일관성을 보지 전이 승인이나 provenance 보존을 보지 않으므로,
이 사례들에서 거부한 검사가 아니다.

## 회귀 테스트

worktree에서 실행했다.

| 테스트 | 결과 | exit |
|---|---|---|
| `test-seed-lifecycle.py` | `OK: all 38 ...` | 0 |
| `test-seed-relations.py` | `OK: all 31 ...` | 0 |

## 한계

- 검증기는 승인을 인증하지 못한다. 바뀐 문자열(`approved_by`)만 보며, 그 문자열이 실제 사용자 답변인지는 `AskUserQuestion` 기록과 대조해야 한다.
- 원시 증거(해시, 검증기 출력)는 실행 머신의 임시 디렉터리에 있고 이 저장소에 커밋하지 않았다. 임시 경로는 정리될 수 있어서 이 문서만으로 원시 증거를 다시 열람하거나 재현할 수 있다고 주장하지 않는다.
- fixture는 합성 Seed이며 제품 Seed가 아니다. 제품 도메인에서의 동작은 검증하지 않았다.
- `CLAUDE_PLUGIN_ROOT`를 직접 관찰하지 못했다. 라이브 훅이 메인 체크아웃 소스에서 실행됐다는 판단은 추론이다.
- 쓰기 1의 자식 파일 생성(파일 복사)과 부모 children 목록 수정(python 스크립트)은 훅을 거치지 않았다. 이 쓰기들의 근거는 검증기 실행뿐이다.
- 설치 캐시, Codex, local-harness 경로는 실행하지 않았다.
