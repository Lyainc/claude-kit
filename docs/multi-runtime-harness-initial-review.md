# 멀티 런타임 하네스 초기 비교 검토

2026-09-16 기준의 독립 비교 보고서예요. 다음 세션에서는 **기존 검증 문서에 기능별 capability 증거표부터 채우는 방향**을 우선 검증하는 게 맞아요. 현재 구현에 부족한 것은 새로운 어댑터 구조보다 지원 선언과 실제 증거 사이의 구분이에요.

## 검토 범위와 한계

- 입력은 `/Users/Lyainc/vault/notes/multi-runtime-harness-research.md`와 직접 관련된 claude-kit·local-harness 파일, 기존 disposable 실행 원본이에요. 원본 note는 수정하지 않았어요.
- 외부 사례의 설명은 제공 note의 조사 내용으로만 취급해요. Ouroboros·Superpowers·agent-harness·oneharness 저장소의 최신 사실이나 현재 동작을 이번 검토에서 공식 원본으로 재확인하지 않았어요.
- 기존 Codex 기록은 `--audit-only`로 재확인했어요. 새로운 모델 시나리오, 설치, 전역 설정·trust 변경은 수행하지 않았어요.
- 보고서는 파일 내용과 기존 실행 기록에 근거해요. Git 이력 재작성 중의 HEAD·diff·원격 상태를 읽거나 검증하지 않았으므로, 이 보고서가 최종 커밋 구성을 증명하지는 않아요.
- Claude 실행은 사용자가 직접 검증하기로 한 경계를 유지해요. 기존 조직 인증 차단 기록을 기능 미지원이나 현재 인증 상태로 확대하지 않아요.

## 이미 반영된 계약

| 조사 note의 방향 | 현재 반영된 내용 | 근거와 증명 범위 |
|---|---|---|
| 공통 작업 계약 | next-goal의 입력·현재 상태·재개 지점·보호 조건·관찰 가능한 완료기준, 후보 없음 허용 | [next-goal 본문](../thinking-tools/skills/next-goal/SKILL.md), 입력 계약 17–29행과 판단·조건 31–81행. 소스 계약이며 양쪽 live 실행 성공과는 별개예요. |
| 판단과 네이티브 절차 분리 | 기존 머신 P9/P18가 유용한 독립 위임과 공유 리뷰 한도를 소유해요. session-close는 공통 Git 책임과 필요한 runtime reference만 읽어요. | `local-harness/rules/README.md:26,34`, `local-harness/skills/session-close/SKILL.md:23–57`. 새 공통 실행 API는 추가하지 않았어요. |
| 승인·권한 보존 | add-policy는 관리 원본·설치본의 정확한 변경 승인을 유지하고 hook placement와 native trust를 분리해요. | [add-policy 본문](../feedback-loop/skills/add-policy/SKILL.md), 18–34행 및 [Codex hook 분기](../feedback-loop/skills/add-policy/codex.md), 13–29행. 정상 trust activation 전체의 실행 증거는 아니에요. |
| 설치·발견·행동 증거 분리 | source/cache equality, fresh loader discovery, native 시나리오와 hook router 기록을 따로 보고해요. | [기존 검증 기록](cross-runtime-loop-validation.md), 38–57행·94–122행. Claude는 등록 확인과 실행 차단을 구분해요. |
| 다른 런타임의 상세 지침은 필요할 때만 로드 | 공통 portability 계약과 선택한 runtime reference를 사용하며 Claude 도구·hook payload의 동등성을 추정하지 않아요. | [공통 도구 계약](../thinking-tools/reference/codex-portability.md), 12–20행 및 `local-harness/skills/session-close/references/codex.md:27–51`. |

설치 위치의 과거 가정도 구분해야 해요. 이번 확인에서 실제 session-close는 `~/.agents/skills/session-close`가 source를 가리켰고, legacy `~/.codex/skills/session-close`는 없었어요. 제공 note에 적힌 외부 프로젝트의 `.codex/skills` 설치 설명을 현재 local-harness의 설치 규칙으로 가져오면 안 돼요.

Claude 전용 hook 형식·payload의 비동등성과 Codex native hook 자체의 부재도 다른 주장이지요. 현재 [Codex hook 분기](../feedback-loop/skills/add-policy/codex.md)와 기존 native fixture에는 deny·recovery 증거가 있어요. `ask`, Claude telemetry, ExitWorktree까지 동등 지원이라고 주장하지 않아요.

## 초기 채택·검증 후보

| 순위 | 후보와 현재 근거 | 실용적 영향 | 가장 저렴한 다음 검증 산출물 |
|---|---|---|---|
| 1 | **기능별 capability 증거표**. [portability 검사](../scripts/check-codex-portability.py)의 86–99행은 manifest·adapter·계약 존재를 확인하고, [검증 기록](cross-runtime-loop-validation.md)의 53–57행은 ask·telemetry·ExitWorktree의 차이를 명시해요. | `19 supported`를 모든 기능의 동등 지원으로 오해하지 않도록 구조적 분류와 실제 검증을 구분해요. | 기존 검증 문서에 `기능 / runtime·version / 지원 선언 / 필요 권한·trust / 검증 상태 / 증거 경로·hash / 검증일 / 공백 영향` 표를 채워요. 새 capability 저장소는 필요 없어요. |
| 2 | **Claude 동일 다섯 시나리오의 사용자 직접 검증**. [기존 기록](cross-runtime-loop-validation.md) 107–122행과 `/private/tmp/loop-claude-scenarios-1/events.jsonl:12–13`에는 `oauth_org_not_allowed`, HTTP 403이 있어요. [기존 실행기](../scripts/test-native-loop.py) 121–156행은 양쪽 입력과 검사를 제공해요. | Claude의 본문 전체 적용·수정 회복·무가치 후보·종료·비용은 등록 확인만으로 증명되지 않아요. | 사용자 접근 복구 후 같은 실행기 한 번의 events·summary·audit 결과를 받아 비교해요. 차단이 유지되면 terminal reason과 재개 지점만 남기고 반복 호출하지 않아요. |
| 3 | **일반 native trust와 도구 권한 경계**. [hook 분기](../feedback-loop/skills/add-policy/codex.md) 13–29행은 trust를 분리하지만, [fixture](../scripts/test-native-hooks.py) 63–65행은 해당 호출에 한해 trust를 우회해요. | deny·recovery 성공은 미신뢰 정의의 비활성 상태, 정상 신뢰 승인, 정의 변경 후 재승인이나 sandbox 거절까지 증명하지 않아요. | 임시 HOME에서 `미신뢰 / 명시 신뢰 / 정의 변경 / 도구 권한 거절`별 이벤트·파일 상태·거절 사유 표를 남겨요. 사용자 전역 trust·권한은 변경하지 않아요. |
| 4 | **병렬 작업·세션 handle의 독립 관측**. [한계 기록](cross-runtime-loop-validation.md) 82–87행은 병렬 완료 보고와 spawn·상태 원본의 차이를 밝혀요. [event verifier](../scripts/test-native-loop.py) 16–54행은 command/edit만 처리하고 실행은 122–125행에서 ephemeral/no-persistence를 사용해요. | 통합 artifact 성공만으로 실제 병렬 중첩·live/terminal 상태·재개·취소까지 주장할 수 없어요. persistent resume은 미검증이며 미지원으로 단정하지 않아요. | 필요한 네이티브 경로에 한해 독립 작업 두 개의 `spawn handle → 관측 상태 → 시작·종료 시각 → terminal reason` 기록을 확보해요. 재개·취소 검증은 실제 지원 주장이 필요한 경우만 추가해요. |
| 5 | **유효 distill → add-policy 승인 handoff**. [distill](../feedback-loop/skills/distill/SKILL.md) 12–19행은 proposal·inviolability 보존과 별도 placement 승인을 요구해요. [add-policy](../feedback-loop/skills/add-policy/SKILL.md) 18–34행은 관리 원본·설치본·사용자 skill을 보호해요. [대표 시나리오](../scripts/test-native-loop.py) 98–113행은 후보 없음과 hook 분기 보고까지예요. | 긍정 후보가 두 승인 경계를 유지하는지, 거절 후 무변경인지, 관리 원본과 설치본이 동기화되는지 live 증거가 부족해요. | 임시 managed catalogue/skill fixture 하나에서 proposal 필드, 정확한 승인 diff, 거절 후 hash 불변, 승인 후 source/install equality를 기록해요. production 정책은 저장하지 않아요. |

기능 증거표의 상태는 최소한 **현재 소스에 선언됨 / 설치·발견 확인 / 실제 경로 검증 / 대체 경로만 검증 / 미검증 / 명시 지원 공백**을 구분해야 해요. 인증 차단·관측 한계·권한 거절은 각각 사유를 기록하고 모두 `unsupported`로 뭉치지 않아요. 검증 시점의 성공을 현재 상태로 자동 승격하지도 않아요.

## 실행 원본이 이미 증명하는 부분

`/private/tmp/loop-codex-scenarios-1`의 기존 events를 현재 verifier로 읽었을 때 작은 검사와 묶음 검사는 각각 한 번 통과했고, 실패 검사 41번 이벤트 → clamp 수정 43번 → 성공 검사 45번 순서가 확인됐어요. risk/sweep는 72번·74번 이벤트에서 각각 한 번 통과했어요. 이는 verifier가 처리하는 command/edit 순서와 횟수의 증거이며 병렬 handle 관측까지 포함하지 않아요.

`/private/tmp/loop-codex-hooks-5`의 기존 router 기록도 deny 2행 → recovery 3행 순서가 확인됐어요. 이는 disposable trust 우회 fixture의 native 실행 증거예요. 기존 summary는 당시 필드 구조를 사용하므로, 최신 summary 필드가 없다는 사실을 실행 실패나 자동 최신 검증으로 해석하지 않고 원본·audit 결과와 함께 읽어야 해요.

## 보류할 구조 확장

현재 범위는 Claude Code와 Codex 두 런타임이에요. OpenCode나 세 번째 어댑터, 설치 세대·activation manifest를 관리하는 framework, 공통 session API, 별도의 `state/runs`·`state/capabilities` 계층은 보류해요. 기존 스킬·runtime reference·disposable records·검증 문서로 현재 질문을 표현할 수 있거든요. 확장 필요성은 위 후보 검증에서 기존 구조로 남길 수 없는 구체적 계약이 발견될 때 판단해요.

## 다음 세션 thinking-tools 검증 질문

1. 기능별 증거표를 현재 원본 기록만으로 채울 때, 지원 선언·설치·발견·live 동작 중 어떤 주장이 아직 증거를 잇지 못하나요?
2. 사용자가 직접 수행한 Claude 다섯 시나리오 결과에서 계약 결함과 인증·네이티브 기능·관측 한계를 어떻게 구분할 수 있나요?
3. trust를 우회하지 않은 disposable 경로에서 placement 승인, activation 승인, tool permission이 각각 독립적으로 보존되나요?
4. 실제 병렬 작업의 handle·상태·terminal reason을 현재 네이티브 기록으로 증명할 수 있나요? 재개·취소는 현재 범위에서 지원 주장이 필요한 기능인가요?
5. 유효 distill proposal이 add-policy로 전달될 때 별도 승인을 유지하고, 거절 시 무변경·승인 시 관리 원본과 설치본의 일치를 증명하나요?
