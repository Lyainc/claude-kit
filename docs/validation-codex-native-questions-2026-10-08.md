# Codex 질문 계약 실행 검증 · 2026-10-08

## 범위와 기준

- 기준 커밋: `ac95e788018c9e1fc171bc432ac2505e2b41b4d7`
- 요구사항: [#827](https://github.com/Lyainc/claude-kit/issues/827), [#750](https://github.com/Lyainc/claude-kit/issues/750)의 남은 설치본 호출 조건.
- 런타임: Codex CLI `0.161.0`, Default 모드, ChatGPT 로그인. 새 app-server 세션은 현재 설정의 `gpt-6.1-sol` / high를 사용했다. 모델 설정은 변경하지 않았다.
- 실제 호출은 읽기 전용·ephemeral 세션과 빈 임시 fixture에서 수행했다. 질문·게이트의 제한된 진입 경로를 확인했으며, 두 인터뷰를 끝까지 완료하거나 Seed를 생성한 시험은 아니다.
- 원시 기록(app-server JSONL)은 실행 머신에만 있고 저장소에는 넣지 않았다. 아래 호출 ID·이벤트는 그 기록에서 옮긴 것이다.

## 소스, 설치, 발견, 실행

| 단계 | 직접 관측한 증거 | 판정 |
|---|---|---|
| 소스 질문 계약 | 네 사본의 내용이 동일하고, 19개 스킬 모두 plugin-local 계약을 참조한다 | 소스 확인 |
| 개인 설치 | 사용자 명시적 승인 후 계획에 있는 10개 파일의 기존 해시 확인 → 백업 → 교체 → 새 해시 대조 | 설치 확인 |
| 설정 보존 | `~/.codex/config.toml` 변경 전후 SHA-256 동일 | 확인 |
| 새 세션 발견 | 갱신 후 `codex debug prompt-input`에서 네 플러그인의 19개 스킬 이름과 설치 경로를 확인 | 발견 확인; 본문 주입 증거와 구별 |
| build-spec 호출 | CLI 진입 확인에 이어 새 app-server 원시 기록에서 실제 async 질문·접수 → 미답 보류 → 부모 대화 실제 Goal 답변 전달 → Goal만 채점 → 다음 질문 보류를 확인 | 설치본 네이티브 호출·답변 전후 전환 확인; 직접 새 UI 클릭과 부모 답변 전달을 구별 |
| unknown-discovery 호출 | 새 app-server에서 구조화된 `type: skill` 입력과 설치 경로를 전달; raw Responses 이벤트에 실제 비동기 질문 호출과 `accepted: true` 출력이 존재 | 실제 설치본의 네이티브 호출 확인 |
| 실제 사람 답변 | 이 대화에서 네이티브 질문 접수 후 실제 사용자 메시지의 두 답변을 수신했다 | 실제 수신 확인; 새 클라이언트 직접 클릭과 구별 |
| next-goal 호출 | 최신 설치본의 명시적 `$thinking-tools:next-goal`, 도구 사용 없는 종료, `turn.completed`, 마지막 규칙 재현 | #750의 설치본 호출 조건 충족 |

설치는 `6.0.0`을 유지한 로컬 미릴리스 갱신이다. 원격 마켓플레이스나 릴리스를 갱신했다는 뜻이 아니다.
설치 승인 대상은 공통 계약 4개, build-spec·unknown-discovery·issue-raise·distill·retro 본문 5개,
feedback-loop 회귀 스크립트 1개였다. 이후 소스 검사 보강으로 회귀 스크립트가 다시 바뀌었으므로,
설치된 그 **검사용 파일 1개**는 최종 소스와 다르다. 런타임 계약·스킬 본문은 동일하다.

설정의 보존 해시: `c44565fdf482234282dacbfe0ed7cdb1e16faacd1758b1a8fc9260e6069fcb56`.
갱신 후 공통 계약 해시: `16879b11b46cd7b080d61842f8458b4c650fa56b0a08a6b466fa3c1624a5ec82`.

## 질문·답변·보류 증거

현재 대화의 `request_user_input_async` 호출 `call_8f2971ede68942d4af83b5f58a137b8e`는 질문 세 개를
접수했다. 접수 시점에는 채점 근거를 비워 두고 build-spec의 게이트를 closed,
unknown-discovery의 분야와 종합 게이트를 pending으로 유지했다.

그 뒤 실제 사용자 메시지에서 받은 답변은 다음 두 개다.

1. build-spec Goal: `반복 입력 시간을 줄이도록 CSV 자동 변환`.
2. unknown-discovery 분야: `Creative: 표현과 사용 경험의 가정`.

답변 후에만 build-spec의 Goal 체크리스트와 unknown-discovery의 분야를 반영했다.
build-spec의 미답 제약·완료 기준과 unknown-discovery의 미진행 영역은 완료로 바꾸지 않았다.
파일에 Seed를 쓰거나 기존 요구사항을 활성화하지 않았다. 내부 복원용 STATE 기록은 임시 증거
파일에만 남겼으며 Seed에 작업 기록을 추가하지 않았다.

새 설치본의 unknown-discovery 호출에서는
`call_f6f4af72425b44d793c459fd40ce83a0`의 `function_call` 이름이
`request_user_input_async`이고, 같은 call ID의 `function_call_output`이
`{"accepted":true}`다. 실제 답변 없이 Phase 0 분야 확인을 유지하고 후속 질문·채점·종합을
진행하지 않았다. 이것은 접수 증거이며 사람 답변 증거가 아니다.

복수 선택은 독립 항목 A=CSV 한글 인코딩, B=완료 항목 숨기기, C=빈 파일 처리를 대상으로,
옵션 없는 자유 입력 질문에 유지할 ID를 모두 적도록 요청했다. `A,C`나 `없음`을 받을 수 있게
의미를 보존했으며 단일 선택으로 바꾸지 않았다. 이 fixture는 실제 Phase 2.5 결과나 요구사항이
아니다. 첫 자유 입력 질문 자체의 답변은 수신되지 않았다.

이어서 같은 의미를 항목별 유지/폐기 질문 세 개로 표현해 네이티브 도구에 제출했다.
`call_3705be11b0e64d96bc036519cfe1c9d1`의 실제 사용자 답변은 **A 폐기, B 유지, C 유지**다.
최신 증거 STATE의 choice_adapter에만 keep=[B,C], dismiss=[A]를 반영했다.
같은 결정에 대한 명시적 답변을 재사용하므로 원래 자유 입력 질문을 다시 요구하지 않는다.
A의 기본 선택과 다른 실제 폐기 답변도 보존했으며, 기본 선택·접수·시간 경과를 답변이나
승인으로 취급하지 않았다. 이 세 항목은 Seed·실제 요구사항으로 적용하지 않았다.


추가 새 설치본 탐침에서는 이 대화의 실제 Creative 답변을 같은 임시 app-server 세션의
두 번째 `text` 사용자 턴으로 전달했다. 원시 기록에 첫 async 접수 → Phase 0 보류 →
실제 답변 문자열 입력 → Creative 확인 → Phase 1 / Assumptions 첫 네이티브 질문 →
다시 답변 대기가 순서대로 남았고 두 턴이 완료됐다. 이는 **기존의 실제 사람 답변을 검증
클라이언트로 전달한 증거**다. 새 클라이언트에서 사용자가 직접 클릭한 결과로 세지 않는다.

이 전달 탐침의 최초 실행은 150초 제한에 걸렸다. TextIO 선읽기 버퍼에 남은 JSON 행을
읽기 전에 selector에서 기다린 임시 클라이언트의 결함이었다. binary pipe의 완성된 행을
먼저 소비하도록 고친 뒤 실패한 탐침만 다시 실행해 성공했다. 최초 실패 기록도 보존했다.
저장소의 스킬·도구 구현을 바꾼 수정이나 독립 검토의 재실행은 아니다.


추가 build-spec 원시 기록에서도 `call_af65c703598e4c2e9073aca9e2d1e4a1`의 실제
`request_user_input_async`와 `accepted: true`를 확인했다. 첫 턴에는 채점하지 않고
답변을 기다렸다. 다음 사용자 text 턴으로 이미 수신한 `반복 입력 시간을 줄이도록 CSV 자동 변환`을
전달한 뒤에만 Goal 체크리스트를 평가했다. 새 네이티브 질문
`call_9348bab7d48f43d69615d7e6a404246e`에는 원본·결과 예시를 요청하고,
STATE에 미답 Round 2, 게이트 pending, consecutive_gate=0, Seed 미생성을 유지했다.
두 턴은 모두 완료됐다. 부모 대화 답변의 전달 증거이며 새 UI의 직접 응답으로 표현하지 않는다.

이 읽기 전용 build-spec 호출은 uv 캐시의 `.git` 접근 제한으로 백로그 스크립트를 실행하지
못했다. 모델은 백로그를 unavailable로 남기고 충돌 없음으로 판정하지 않았다. 그러므로 이
기록을 전체 백로그·전체 인터뷰의 end-to-end 통과로 확대하지 않는다.

## 도구 제한과 fallback

- 현재 Default 모드에서는 비동기 도구를 사용했고 Plan 전용 `request_user_input`을 호출하거나
  이를 위해 모드를 바꾸지 않았다.
- 별도 호출에서 모든 도구 사용이 금지된 fixture를 명시했다. 설치된 unknown-discovery가
  일반 대화로 분야 확인을 요청하고 실제 답변을 기다렸다. 이 호출은 도구 실행 항목 없이
  완료됐으며 채점·종합·쓰기 없이 질문을 보류했다.
- 앱 연결을 비활성화하고 폼 확장을 선언하지 않은 새 app-server 클라이언트에도
  `request_user_input_async`가 실제 제공됐다. 따라서 이 환경을 물리적인 도구 부재로
  판정하지 않았다. **네이티브 도구가 실제로 없는 런타임에서의 end-to-end fallback은 미검증**이다.
- 추가로 실제 CLI 기능인 `code_mode_host`와 `code_mode`를 임시 app-server 호출에서만
  비활성화했다. 그래도 원시 이벤트에 `request_user_input_async` 두 번의 실제 호출이 남았다
  (`call_6bed8ed921134632980b852188d58639`, `call_34aad221adda421d911a11ebfb335f72`).
  설정 플래그를 껐다는 사실만으로 도구 부재를 추정하지 않았다. 같은 세션의 실제 부모 답변
  전달 뒤 Phase 1로 진행하고 다음 실제 답변 전에는 계속 보류했다. 개인 설정은 변경하지 않았다.
- [공식 설정 문서](https://learn.chatgpt.com/docs/config-file/config-reference)와 현재 app-server
  설정 스키마에서 native input을 제거하는 지원 옵션은 찾지 못했다. 앱별 도구 설정을 native
  입력 제거 옵션으로 가정하거나, 임의 설정 키를 만들어 재시도하지 않는다. 확인한 모든
  허용된 현재 실행 조건에 실제 비동기 도구가 있었으므로 물리적 부재 조건에는 외부 런타임
  제공 또는 실제 도구 목록의 변경이 필요하다.
- 필수 인터뷰·승인에 대한 무응답은 pending으로 남긴다. optional clarification의 런타임
  fallback을 인터뷰 답변이나 승인으로 쓰지 않는 규칙은 소스와 회귀 검사에서 확인했으며,
  모든 용도·모드 조합을 실제 호출한 증거는 아니다.

## 19개 스킬과 개별 어댑터

소스의 명시적 질문 소비자는 다음 15개다. 질문 없는 단계에 새 질문을 강요하지 않았다.

| 플러그인 | 명시적 질문 소비 경로 |
|---|---|
| thinking-tools | build-spec, unknown-discovery, adversarial-review, expert-panel, diverse-sampling, doc-concretize, issue-raise |
| feedback-loop | distill, add-policy, retro |
| vault-bridge | vault-link, vault-commit, wiki |
| obsidian-vault-manager | audit, base |

doc-polish, next-goal, vault-manifest-refresh, vault-save도 공통 계약을 참조한다.
실제 상황에 질문이 필요한 때 계약을 적용하며, 이번 시험을 위해 질문을 추가하지 않았다.

issue-raise는 `gh issue create` 전 승인 게이트를 보존하면서 공통 네이티브 질문 경로를 사용한다.
retro는 Claude telemetry 수집 대신 현재 대화의 관측 가능한 낭비를 쓰고, 이슈 생성 전 실제
확인을 요구한다. distill은 중복 검사와 확정 제안을 보존하며 add-policy의 별도 배치 승인으로
이어진다. 이 세 개별 Codex 지침은 소스 대조·회귀 검사에서 확인했다. 실제 이슈 생성이나
개인 정책 매립을 수행한 증거는 아니다.

## #750 판정

`next-goal/SKILL.md`는 설치본과 기준 소스가 동일하고 7,981바이트였다.
새 ephemeral 읽기 전용 세션의 명시적 `$thinking-tools:next-goal` 호출은 도구 실행 없이
NEXT·FROM·SKIPPED·GOAL을 반환했고 `turn.completed`가 1개였다. `/goal` fence,
`exceeded the main prompt context limit`, description 축약 경고는 없었다.

목록 발견만으로 본문 주입을 추정하지 않기 위해 별도 탐침에서 파일 읽기를 금지하고,
주입된 본문의 마지막 Rules 문장을 반환하도록 요청했다. 아래 문장을 정확히 반환하고
`turn.completed`로 끝났다.

> Before emitting, reread the paragraph for required scope, supported facts, explicit protections and
> proof; a negative decision counts only with its named evidence.

실행 명령·프롬프트를 원래 부모 대화의 `exec_command` 인자에서 사후 복사한
`next-goal-invocation-manifest.json`에 JSONL의 thread ID·완료 수·설치본 해시를 연결했다.
독립 CLI 입력 recorder로 가장하지 않고 provenance를 명시했다. 원래 호출 증거는 부모
대화의 도구 호출이다.

이는 최신 설치본의 명시적 호출이 본문 끝까지 로딩되어 완료된 기록이다.
#750의 남은 판정 조건은 충족했으나 GitHub 댓글 게시·이슈 종료는 하지 않았다.

## 발견한 검사 공백과 수정

기존 `check-codex-portability.py`는 네 계약 사본의 동일성만 확인했다. 네 사본을 모두 수정 전
일반 대화 계약으로 치환하는 읽기 전용 mutation에서 오류 0개로 통과했다.

네이티브 우선, 비동기 실제 답변 대기, 모드·용도 제한, 독립 선택 의미, 기존 답변 재사용과
무응답 처리, 도구 미지원 fallback을 검사하도록 보강했다. 같은 legacy mutation은 이제
24개 오류로 차단된다. retro·distill의 네이티브 경로 누락과 옛 chat-only override도 차단한다.
새 feedback-loop self-test에서 금지 문장을 Codex 절 밖에 넣은 fixture 오류가 발생했고,
실제 Codex 절 안으로 옮겨 바로 수정했다. 스킬 동작을 바꾼 실패가 아니다.

| 변경·실패와 관련된 검사 | 최종 결과 |
|---|---|
| Codex 질문 계약 self-test | 9/9 통과 |
| Codex portability 실제 소스 검사 | 19개 분류 통과 |
| feedback-loop portability self-test | 8/8 통과 |
| feedback-loop 실제 계약 검사 | 3/3 통과 |
| CI 등록 검사 `--strict` | 120/120 연결 |
| legacy 네 사본 동시 회귀 mutation | 변경 전 미탐지, 변경 후 24개 오류로 탐지 |

이 목표 전 통과했던 도구 선언·스킬 참조·tiktoken 크기 검사는 해당 스킬 본문이나 도구 선언이
추가로 바뀌지 않았으므로 반복하지 않았다. 새 검사·문서·CI 변경과 self-test 실패 관련 검사만
재실행했다.

## 남은 미검증 조건

1. 복수 선택 의미 보존과 실제 결정 수신은 항목별 네이티브 질문의 A 폐기/B·C 유지로
   확인했다. 자유 입력 UI가 실제로 어떻게 보였는지는 미검증이며, Computer Use의 Codex 앱
   접근이 도구 자체에서 차단돼 직접 관측할 수 없었다. 이를 질문 미표시로 추정하지 않는다.
2. 실제 네이티브 질문 도구가 없는 허용된 Codex 런타임이 확보되면 unknown-discovery의
   첫 분야 질문을 호출해 대화 fallback과 실제 답변 수신까지 기록한다. 현재의 도구 금지 fixture나
   지침 대조를 물리적 도구 부재의 실증으로 대체하지 않는다.
3. 전체 build-spec·unknown-discovery 인터뷰의 게이트 통과·격리 채점·Seed/리포트 생성은
   확인하지 못했다. 이 부분을 진입 시험의 통과로 확대하지 않는다. 필요하면 새 disposable
   target에서 실제 답변으로 검증한다.
