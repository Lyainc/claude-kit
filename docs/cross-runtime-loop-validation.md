# Claude Code·Codex 공통 loop 검증 기록

2026-09-15 작업 기록이에요. `Claude 100·Codex 20 → 90·90`은 방향을 나타내며,
측정 호환 점수로 보고하지 않아요. Claude 모델 실행은 조직 인증 HTTP 403으로 막혔고,
사용자가 별도로 검증하기로 했어요. 이번 완료 범위는 구현·설치·양쪽 발견과 Codex 실행
증거예요. 동일 시나리오의 Claude 실행 결과와 양쪽 비용 비교는 검증 완료로 주장하지 않아요.

## 기준과 보호 상태

- claude-kit 기준 `944ab951a119f7c3320cbc83d2d2154eb206fd2f`, local-harness 기준
  `a7797a2b2bd817d5073b2579509362059eb623ad`에서 시작했고 두 origin fetch가 성공했어요.
  원격 main에 추가 이력은 없었어요. 이 기준에서 작성했고 버전 5.1.0을 유지해요.
- 다른 worktree의 `agent-spawn-delegation` 변경(예산 검사·report·문서·삭제 상태),
  `fix-infra-recovered/.verify-out.json`, `skill-bindings-737` 변경을 확인하고 그대로 보존해요.
  다른 worktree 변경은 병합하거나 덮어쓰지 않았어요. 이전 예산·위임 report 변경은 현재
  HEAD의 기존 기능과 겹치므로 다시 가져오지 않았어요.
- 두 저장소 모두 기존 stash 1개가 있어요. worktree·stash·다른 세션 프로세스는 정리하지 않아요.
- 전역 설정·관련 캐시 백업은 `/private/tmp/claude-kit-loop-backup-20260915-231437/manifest.json`에 있어요.
  버전 bump·push·PR 생성·merge는 수행하지 않아요.

## 공통 계약과 런타임 분기

| 흐름 | 입력·판단 규칙 | 결과·승인·완료 증거 | Claude 네이티브 | Codex 네이티브 |
|---|---|---|---|---|
| next-goal | 세션 후보·현재 상태·재개 지점·관련 파일·보호 조건, 실용적 가치와 관련성, 최소 크기 없음 | NEXT/FROM/SKIPPED + 관찰 가능한 GOAL; 무가치 후보는 GOAL 없음; 읽기 전용 | 직접 호출은 `/goal` 4,000자 이내, caller는 결과를 한 번 배치 | 일반 GOAL, 호출 API를 흉내 내지 않고 설치된 계약을 직접 적용 |
| 실행 중 위임 | 기존 머신 P9, 독립된 구체적 작업과 실제 병렬 이득이 있어야 해요 | 작은 유효 작업은 직접, 불필요한 spawn·범위 확대 없음 | 현재 CLI Agent 기능만 사용해요 | 현재 런타임의 subagent 기능만 사용해요 |
| 검증·리뷰 | 기존 P18, 합계 2라운드 기본값, 도구·호출 방식·새 에이전트로 초기화하지 않아요 | 통과 검사는 관련 변경·실패·미해결 중대 문제에만 반복; 인프라 리뷰 실패는 별도 직접 검사 | 네이티브 검사·독립 검토 | 네이티브 검사·독립 검토 |
| retro | 관측 낭비, 중복 후보 병합, 유효한 열린 이슈 비교 집합 | 정확한 이슈 draft 승인 후 생성; 낭비 없음은 후보 없음 | 기존 opt-in telemetry 또는 대화 관측 | 대화 관측; Claude telemetry payload를 빈 데이터로 간주하지 않아요 |
| distill | 절차 기법·2개 이상 분리 관측·기본 행동 제외·기존 native 지침/skill 확인 | what/why/provenance/inviolability proposal, discovery 승인 후 handoff | 기존 Skill handoff | 현재 컨텍스트에서 add-policy 계약을 이어 적용; 별도 placement 승인 유지 |
| add-policy | 사용자 명시 규칙 또는 확인된 distill 제안, 충돌·필요성·사용자 skill 보호 | 정확한 변경 1회 승인, artifact 검사, 자동 activation 없음 | reminder·command hook·skill | 기존 공통 catalogue 우선, 관리 원본·설치본 동기화 승인; .agents/skills·native hooks.json; hook trust 별도, PreToolUse ask는 지원 공백 |
| session-close | 공통 Git 책임·thread readiness·관련 PR 우선, 승인된 누락 commit backstop; collector·이슈·후보 데이터 | commit 허가와 publishing 제외를 구분; outward/삭제 승인과 qualifies:true, fetch-failed 보존 | 필요한 Claude workflow만 읽어요 | 누락 commit·PR 없는 작업을 처리하고 기존 collector를 stage별 배치해요 |

판단 규칙은 기존 next-goal 본문과 머신 P9/P18에 두었어요. 다른 런타임의 상세 절차는
필요할 때만 읽어요. collector 결과는 상태가 같을 때 재사용하고, merge 뒤 sweep 및
승인된 삭제 직전 영향을 받은 repo의 재검증을 유지해요. 영속 snapshot 캐시는 추가하지
않아서 서로 다른 프로세스의 변경을 시간 TTL로 숨기지 않아요.

## 소스·설치·발견·실행

| 항목 | 소스 | 설치 | 새 세션 발견/실행 |
|---|---|---|---|
| thinking-tools·feedback-loop | 변경 본문과 공통 도구 계약, 버전 5.1.0 | Codex 정상 remove/add, Claude local marketplace 등록 후 user/project 정상 update, 본문 byte equality 확인 | Codex loader의 5.1.0 roots와 개선된 description, Claude init의 5.1.0 plugin/skill 등록 확인 |
| session-close | 약 3.7KB 공통 진입점 + 런타임 reference, 기존 collector 유지 | Claude 기존 source symlink, Codex `home/bootstrap.sh --target codex`로 `.agents/skills/session-close` 링크 복구 | Codex fresh discovery와 실제 risk/sweep 실행; Claude 등록 확인, 모델 실행은 403 |
| 머신 판단 | rules/README.md P9/P18와 기존 linked rationale | Claude 기존 rules source link; Codex 전역 지침의 P9/P18 포인터 | 새 Codex prompt에서 강제 spawn 문구가 없고 포인터가 주입되는 것을 확인 |
| Codex 전역 지침 | 관리 원본을 local-harness/home/AGENTS.md로 명시 | 기존 regular file identity를 보존하고 백업 후 원본과 같게 설치 | 설치 및 실제 prompt 주입은 별도 확인했어요 |
| native command hook | add-policy/codex.md에 deny·recovery·approval·trust 분기 | production hook은 등록·활성화하지 않았어요 | disposable native fixture에서 실제 event와 쓰기 전 deny·쓰기 후 recovery를 검사해요 |

독립 검토의 P1 수정 뒤 feedback-loop만 정상 재설치했어요. Claude의 같은 버전 update는
cache를 바꾸지 않아 user/project를 `--keep-data`로 정상 uninstall/install했고 최신 본문
equality를 확인했어요. 다른 worktree pin과 persistent data는 보존해요. Codex도 해당 plugin만
정상 remove/add했고 새 prompt discovery와 관리 원본·전역 파일 equality를 다시 확인했어요.

기존 진단의 변경된 사실만 갱신했어요: portable manifest가 런타임 호환을 증명하지 않는다는
경계는 유지하고, session-close Codex 설치 경로는 과거 `.codex/skills` 대신 현재
`.agents/skills`로 바로잡아요. 기존 “Codex에는 hook 자체가 없다”는 가정은 현재 공식 문서와
네이티브 fixture 증거로 철회해요. Claude용 Skill hook matcher와 telemetry schema, Codex
ExitWorktree 및 PreToolUse ask까지 같은 기능이라고 주장하지 않아요.

## 본문 제한과 비용

현재 Claude Code 2.1.267 코드에서 default listing cap 1,536자, listing fraction 1%, 압축 복원
개별 skill cap 5,000토큰·합계 25,000토큰을 확인했어요. 복원 시 truncation marker가 있고,
재확인을 위해 skill path를 읽도록 안내해요. 3,000토큰을 초기 호출 본문 제한으로 단정할
증거는 없어요. 도구 출력 preview 잘림과 목록·압축 복원 예산을 구분해요.
Codex 0.154.0의 공식 문서는 초기 name/description/path 목록에 known context의 2% 또는
unknown context의 8,000자를 배정하며, 선택한 SKILL.md 전체를 읽는다고 설명해요.

| 파일 | 기준 o200k 토큰 | 현재 o200k 토큰 | 의미 |
|---|---:|---:|---|
| next-goal/SKILL.md | 2,543 | 1,277 | 필요한 판단·handoff와 caller Git 완료 계약 |
| next-goal/reference.md | 2,275 | 461 | 중복 강제 절차 제거, 필요할 때만 읽어요 |
| session-close/SKILL.md | 10,245 | 741 | 공통 Git 계약을 복원하고 다른 런타임 상세 본문을 분리했어요; runtime reference 비용은 별도예요 |

같은 tokenizer로 측정한 소스 크기이며 Claude 실제 토큰이나 런타임 총량 절감률이 아니에요.
새 목록/본문 독립 회귀 fixture는 짧은 description으로 큰 본문을 숨기는 경우와 작은 본문으로
긴 description을 숨기는 경우를 따로 실패 판정해요. native 시나리오 기록에서 next-goal 실제
마지막 문장과 선택한 session-close reference의 마지막 행까지 읽은 증거를 확인해요.

Codex 동일 대표 시나리오 한 새 세션은 206.23초, shell calls 30회·fixture edit calls 3회예요.
작은 검사 1회·번들 검사 1회·실패 전후 검사 2회, collector risk/sweep 각각 1회,
추가 후보 조회·위임·외부 쓰기·통과 검사 불필요 반복은 0회예요. 두 파서도 수 줄짜리여서
병렬 이득이 없다고 판단했어요. 별도 독립 작업 fixture에서 JSONL reader와 filter를 격리된
worktree에 구현하고 통합 검사를 1회 실행해 `NATIVE_PARALLEL_PASS`, exit 0을 확인했어요.
전체 컨텍스트 포크는 `no thread with id`로 실패했고 독립 컨텍스트 helper 경로가 성공한
것으로 보고됐어요. 두 워커의 병렬 상태·완료 시각은 최종 응답의 보고이며 JSON stream에는
spawn handle과 실제 상태 응답이 없어 겹친 시간의 독립 검증 증거로 확대하지 않아요.
현재 CLI stream의 관측 한계와 최초 포크 실패를 명시하고, 통합 산출물의 성공과 구분해요.
input 509,606 / cached input 419,328 / output 8,819 / reasoning output 4,281토큰이 기록됐어요.
reasoning은 output에 포함되어 있으므로 합산하지 않아요. 과거 동일 fixture의 전체 call/token
기록이 없어서 총 런타임 비용이 얼마나 줄었는지는 비교할 수 없어요. 기존 hook의 eager gh
조회는 현재 local-only 회귀 검사에서 0회로 확인됐고, repo별 collector tool 호출은 stage별
배치로 줄었어요. 안전 재조회 자체는 제거하지 않았어요.

## 검사와 미충족 조건

- local-harness `LOCAL_HARNESS_CHECK_CODEX_SESSION=1 bash rules/run-tests.sh`: exit 0,
  `rules/: all suites passed`; collector orphan-process 보호는 ps 가능한 환경에서 통과했어요.
- claude-kit 관련 검사: portability 19/19 supported, version-sync, skill-reference 184건,
  agent-tools 24건, 기존 feedback gate/routing/telemetry 검사, token-budget self-test 65건과
  실제 예산, next-goal hook 21건·candidate 6건, language/type/banned-words/CI coverage,
  diff whitespace 검사가 통과했어요. 전체 무관한 plugin suite 통과로 확대 주장하지 않아요.
- Codex 작은 작업·독립된 소규모 묶음·검증 실패 후 수정·무가치 후보·종료는 실행 증거가 있어요.
- 실행 verifier는 기록된 command 순서·횟수, 실패 뒤 clamp 수정, risk/sweep 1회씩을
  직접 확인해요. native hook은 실제 router의 deny·recovery 피드백을 확인해요.
  기존 성공 기록 재검사와 실패 검사 누락·collector 누락·통과 반복·조기 수정·피드백 누락의
  변조 기록 거부를 확인했어요. 성공한 모델 시나리오는 반복하지 않았어요.
- Claude는 새 session init의 최신 plugin/skill 발견까지 증명했어요. 조직에서 Claude Code
  subscription access를 disabled하여 API 403으로 실행 전에 종료했어요. API key도 현재
  환경에 없어요. 사용자에게 동일 시나리오 수행·본문 전체·효율 비교 검증을 넘겼어요.
- 추가 전역 AGENTS 문구 변경은 자동 승인 검토에서 거절되어 적용하지 않았어요. 기존
  승인된 강제 spawn 제거 및 P9/P18 포인터는 설치됐어요. 별도 제안은
  `/private/tmp/loop-native-refinement-AGENTS.md`이며 보호 승인 경계를 유지하는 표현만 담아요.
  사용자가 별도 리스크 검토를 요청했고 [검토 보고서](native-instruction-risk-review.md)에
  원래 거절 묶음과 좁은 제안의 영향·복구 조건을 나눠 남겼어요. 적용은 보류해요.
- 최종 production diff 독립 검토 1회는 `REVISE`, P0 0건·P1 2건이었어요.
  관리 원본을 우회하던 add-policy 분기와 부족한 event verifier를 수정하고 관련 검사를
  통과했어요. 재검토 에이전트는 호출하지 않았으며, 수정 뒤 독립 ACCEPT 판정은 없어요.

재개할 때 Claude 인증을 먼저 복구하고 `python3 scripts/test-native-loop.py claude --records
/tmp/<new-directory>`를 실행해 같은 다섯 입력의 실행·본문·call/token 증거를 수집해요.
현재 성공한 Codex 시나리오는 관련 변경이나 실패 없이는 다시 돌리지 않아요.
Claude 실행 결과와 독립 검증 가능한 병렬 상태 기록은 현재 증거의 한계로 남겨요.

## 추가 Git 계약 복원

사용자 점검에서 goal의 커밋·push 책임과 session-close의 PR 없는 작업 판단이 Claude
reference에만 남고 Codex 계약에 빠진 것을 확인했어요. 의도된 축소가 아니라 이식 누락이에요.
공통 entrypoint가 Git 책임과 thread readiness를 소유하고, 양쪽 reference가 그 계약을
사용하도록 바꿨어요. next-goal도 caller의 승인된 Git 완료조건과 명시 제외를 이어받아요.
push·PR 제외가 local commit 제외까지 뜻하지는 않아요.

이번 추가 수정의 독립 검토는 `REVISE`, P1 1건이었어요. Claude의 오래된 silent skip과
reports-only 문구가 승인된 commit backstop을 우회하는 충돌을 수정했어요. collector 자체는
읽기·보고 전용으로 유지하고, main context의 stage①만 이미 승인된 검증 작업을 커밋해요.
adapter 회귀 검사와 portability·reference·본문 예산·언어·type·금지어·CI coverage 검사가
통과했어요. 현재 양쪽 next-goal cache는 수정 소스와 바이트 단위로 같고 session-close는
source link로 최신 본문을 읽어요. 이 사용자 요청은 두 저장소의 이번 변경 commit과 실제
dogfooding을 승인했으며, 기존 push·PR·merge 제외와 추가 전역 문구 변경 보류는 유지해요.

### 실제 session-close Git dogfood

현재 Codex native 세션에서 수정된 `.agents/skills/session-close/SKILL.md`와 Codex reference를
끝까지 읽고 실제 두 저장소를 종료 점검했어요. source 작업은 claude-kit `519d69c`와
local-harness `1fbf937`로 커밋됐어요. 전자는 검증된 작업 21개 경로, 후자는 9개 경로만
stage했고 기존 hook을 유지했어요. harness commit hook의 전체 검사가 exit 0,
`rules/: all suites passed`였어요. 커밋 후 두 main 작업트리는 미커밋·untracked 0개였어요.

열린 PR은 양쪽 모두 0개였어요. native loop 복원이라는 리뷰 가능한 작업 단위가 있지만,
publish는 명시적으로 제외되어 push·PR·merge를 실행하지 않았어요. claude-kit에는 기존
5개와 이번 source commit을 합쳐 미푸시 6개, harness에는 이번 commit 1개가 있었어요.
risk/sweep는 각각 두 repo에 배치 1회 수행했고 정리 후보 13개가 모두 `qualifies:false`라
삭제하지 않았어요. stash 각각 1개와 다른 worktree는 보존해요. #750의 Claude 실행 검증과
추가 전역 문구 검토는 사용자에게 남아 있어 이슈를 닫지 않았어요.

실행 원본·읽은 전체 스킬·본문 hash·PR·collector·새 discovery 증거는
`/private/tmp/session-close-git-dogfood-20260915-145626/summary.json`에 있어요.
양쪽 next-goal cache는 수정 소스와 같고 새 Codex prompt에서 skill 발견을 확인했어요.
이 결과 기록은 같은 승인 범위의 커밋 대상으로 마무리하고, 이후 달라진 claude-kit의
위험 정보만 갱신해요. backlog 비교 집합은 이슈 변경이 없어 재사용해 #2를 다음 목표로
유지해요. 이 점검은 Claude 실행이나 미승인 publication까지 성공했다는 증거가 아니에요.

## 이번 모델 가이드 반영

[GPT 5.6](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.6)의 중복 지침 제거,
목표·제약·승인·완료기준 중심 prompting과 대표 시나리오 비교를 적용해요.
[Astra](https://developers.openai.com/api/docs/guides/latest-model)의 강한 지침 민감도,
clarification으로 인한 중단 위험, 과도한 검증 가능성을 고려해 강제 위임·범위 확대를 제거하고
반복 조건과 도구 간 공유 리뷰 제한을 명시했어요. API async·configuration_update·explicit
cache 기능은 CLI에 같은 설정이 있다는 검증 없이 추가하지 않아요. configured model/effort를
바꾸지 않고 지금 사용 가능한 네이티브 도구와 background process handle을 사용해요.

공식 근거: [스킬 목록/본문](https://learn.chatgpt.com/docs/build-skills),
[Codex hooks와 trust·지원 이벤트](https://learn.chatgpt.com/docs/hooks),
[plugin 환경 변수](https://developers.openai.com/plugins/build/plugins#bundled-mcp-servers-and-lifecycle-hooks).
