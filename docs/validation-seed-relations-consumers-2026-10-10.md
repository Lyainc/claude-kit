# Seed 관계 소비자 실행 검증 · 2026-10-10

## 범위와 기준

활성 `docs/specs/seed-relations-graph.yaml`의 acceptance-2, constraint-11,
acceptance-10을 실제 소스 소비자 실행으로 검증했다. 기준 SHA는
`4115e574a998d6f8276f275f8b31b35202ad97f6`이다. 관련 metadata 선행·Refine 보존 계약인
constraint-7·constraint-12도 확인했다. 나머지 Seed 요구를 새로 완료 판정하지 않았다.

기존 미커밋 29개 파일을 패치와 SHA-256으로 보존한 격리 worktree에서 진행했다.
원본 checkout은 작업 중 `ae3cd60b3f3b8b967b7992313ca308035fc557ca`으로 독립적으로 이동했고
기존 파일 세 개의 내용도 바뀌었다. 변경 주체는 확인하지 않았으며 덮어쓰거나 복구하지 않았다.
격리 사본의 기존 WIP 29개 해시는 모두 처음과 같다. 검토 기준은 처음의 고정 SHA를 유지한다.

소스 worktree:
`/Users/Lyainc/.codex/worktrees/seed-relations-live-consumer/claude-kit`.
원시 증거 루트:
`/private/tmp/seed-relations-live-evidence-20261010`.
`preexisting.patch`, `main-wip-hashes.json`, `preservation-check.json`이 보존·변동 근거다.

관계가 있는 임시 저장소를 생성해 실제 native 도구로 소비했다. 기대 출력을 미리 적어
테스트한 것으로 대체하지 않았다. 이는 합성 관계에 대한 **소스 소비자 실행 증거**이며,
실제 제품 도메인이나 설치된 플러그인의 실행 증거는 아니다. fixture Git은 unborn 상태이며
`git rev-parse HEAD` exit 128을 별도로 기록했다. 소스 SHA를 fixture HEAD라고 하지 않는다.

## 소스·설치·발견·실행

| 단계 | 직접 관찰 | 범위·한계 |
|---|---|---|
| 기준 소스 | 위 SHA의 스킬·스크립트와 보존한 WIP를 사용 | next-goal 소비자는 별도 깨끗한 worktree의 같은 SHA, Refine은 WIP 사본 사용 |
| 설치본 | thinking-tools 6.0.0; 기준 소스 16개 파일 중 13개 일치, 3개 차이 | next-goal/build-spec SKILL과 lifecycle reference에 metadata 선행 계약이 빠져 있음 |
| 최종 소스 비교 | 같은 16개 중 설치본과 8개 일치, 8개 차이 | 기존 WIP 문서·템플릿과 이번 renderer 수정까지 구분해 기록 |
| 새 세션 발견 | `codex debug prompt-input` 1회 시도, `Operation not permitted`로 렌더 전 실패 | 미확인; 설치·설정 변경이나 재시도 없음 |
| 실행 | source next-goal native 에이전트와 main 소유 build-spec Refine | 설치 캐시 실행·새 설치본 발견을 주장하지 않음 |

해시는 `inventory/source-sha256.txt`, `inventory/final-source-sha256.txt` 및
각 installed/comparison 파일에 있다. 새 세션 실패 원문은
`inventory/prompt-input-probe.txt`에 있다. 설치된 renderer는 `return lines`,
수정한 소스는 각 출력 필드의 개행을 공백으로 연결한다.

## 실제 metadata 선행 기록

아래 시각은 2026-10-10 KST다. 원시 기록에는 UTC가 유지돼 있다.
`native-order-proof.json`에는 call ID, 원본 JSONL 줄 번호와 export 줄 번호가 있다.

| 소비자 | metadata 성공 | 후속 실제 호출 |
|---|---|---|
| next-goal run2 | 02:36:35.946, `call_eb81301e520a4057ad819200fe4e2fc8`, exit 0 | walk 02:36:43.233 → 적격 6개 본문 read 02:36:55.066 |
| build-spec Refine | 02:32:17.223, `call_6f81bfa2692e487cb436c6859faca3ae`, exit 0 | 원본 자식 cat 02:32:30.515, `call_19f5ab6d84364036b98ea4b1b8e66ff7` |

원시 native 도구 이벤트는 `native-traces/nextgoal_live_consumer.jsonl`과
`native-traces/root.jsonl`에 export했고, 원본 session 파일과 해시는 `native-traces/index.json`에 있다.
단순 명령 목록뿐 아니라 실제 tool call/output을 대조할 수 있다.
처음 원본 Seed를 상태 확인용으로 cat한 사전 조사는 metadata보다 앞섰다.
그 호출을 소비자 순서 준수 증거로 세지 않았고, 이후 분리한 관계 소비 실행으로 확인했다.

## next-goal: 자격·남은 요구·선행 판단

명명한 시작점은 `docs/specs/origin-closed.yaml`이다. walk에서 부모·형제·선행 등 12개를
방문했고, 외부 선행은 GH_BIN을 존재하지 않는 경로로 고정해 조회하지 않았다.
`FAILED`를 미확인으로 보존했으며 네트워크나 다른 저장소의 완료 판정은 하지 않았다.

| 대상 | 실제 관찰·판단 |
|---|---|
| 활성 부모 | acceptance-3의 직접 proof 부재, acceptance-1은 명시적 자식을 통해 판정 |
| 활성 형제·착수 가능한 선행 | 각 proof 부재, active·eligible이며 의존 없음; 이 남은 부분만 같은 묶음으로 제안 |
| 로컬 의존 후보 | predecessor-active proof 부재로 선행 요구 미완료; `held` |
| 외부 의존 후보 | 외부 predecessor 조회 실패, 완료 상태 미확인; `held` |
| 외부 선행 노드 | `external` 링크만 유지, 후보 순위·완료 판정 없음 |
| sibling-done | 실제 proof 내용 `ready\n`, trimmed ready=true; `done`, 재제안하지 않음 |
| paused·closed·unknown | eligibility=false; 본문·현재 요구 적용 없이 보류 |
| 철회 부모 acceptance-2와 영향 불명 자식 | 부모 항목 제외, 자식 review_required로 보류; 자동 선택 없음 |
| 닫힌 시작점·형제 | 조회 기록에 남지만 자동 후보로 선택하거나 과거 종료 결과를 재판정하지 않음 |

첫 실행은 fixture의 자식 `refines`가 비어 있어 철회 영향 불명으로 모든 자식이 보류됐다.
소스의 올바른 방어였지만 필요한 분기 증거가 부족했다. 명시적 활성 항목 매핑과 부모 직접
항목을 fixture에 추가한 후 두 번째 실제 소비 실행을 했다. 이는 변경된 fixture 검증이며
인프라 실패 재시도나 최종 검토 재실행이 아니다. 첫 실행은 보존했다.

`evidence/nextgoal-consumer-run2/judgment.json`, `04-proof.stdout`, `05-render.stdout`,
`commands.txt`, `goal.txt`가 실제 결과다. `nextgoal-assertions.json`은 후보·held·done·외부 링크와
소비 전후 fixture 해시 일치를 확인한다. 부모 acceptance-1 전체 완료는 주장하지 않았다.

## build-spec: 실제 Refine 왕복과 승인 보류

원본은 임시 `refine-fixture/docs/specs/refine-child.yaml`이다. metadata 후 ID·issues·관계를
복원하고 Phase 0과 하위 피처 질문을 건너뛰었다. 기존 최저 clarity 제약부터 인터뷰했다.
main이 질문·STATE·게이트·쓰기 모두를 소유했고, 에이전트에는 채점과 맹점 확인만 맡겼다.

실제 native 질문과 실제 사용자 답변은 다음 네 건이다.

| 질문 call ID | 실제 답변·권한 |
|---|---|
| `call_6a0f0255b4b046c69f4351a9dd2d1c32` | 제약 확정, 새 v2 활성화와 부모 연결 승인 |
| `call_cT87vK1F1XyOjsZaRCmrh8sD` | 기존 목표·성공 기준과 명시한 범위 유지 |
| `call_43b3d02886094b7b9bd291563879c54b` | 앞뒤 공백·끝 개행을 제거한 값이 ready면 통과 |
| `call_PYOwJxTLTtQa9E2bBIJaUxVw` | 새 constraint-2: 실패 시 부분 연결 원상 복구, 완료 불인정 |

Round 4의 판정 입력에는 정확한 영향 파일·코드 확인 근거가 부족해 게이트가 닫혔다.
Round 5와 6의 실제 답변·맥락을 독립 채점한 결과 각 차원이 0.9로 두 연속 게이트를 통과했다.
맹점 확인은 1회였고 답변을 새 constraint-2로 반영했다. 미답 동안 새 파일이 없고 기존 해시가
그대로인 사실은 `refine-pending-snapshot.json`과 `refine-blindspot-pending-snapshot.json`에 있다.
접수·기본 선택·시간 경과를 답변으로 취급하지 않았다.

새 `refine-child-v2.yaml`은 constraint-1·acceptance-1 ID, issues.source/tracking,
relations.version/parent/refines/link_reason/depends_on/refines_map/provenance/replaces/transfers를
보존했다. constraint-2만 새 ID로 추가했다. 새 children은 비워 원래 손자를 자동 이동하지 않았다.
원본 자식·손자·선행의 바이트 해시는 모두 불변이며, 부모는 승인된 v2 children 추가만 바뀌었다.
`refine-artifact.diff`에서 확인할 수 있다. 진행·실행·검토 기록은 Seed에 추가하지 않았다.

첫 후속 증거 비교에서 main의 코드가 없는 `Seed.issues` 속성을 사용해 실패했다.
공통 lifecycle/관계 검사는 이미 통과했지만 이 시도를 완료로 인정하지 않았다.
부분 v2를 저장소 밖에 보존하고 부모를 원상 복구해 모든 기존 해시 일치를 확인했다.
`refine-validation/first-attempt-rollback.json`과 native 도구 기록이 근거다.
실제 속성 `source`·`tracking`으로 비교를 고쳐 같은 승인안만 다시 작성했다.

최종 신규 lifecycle 검사, 부모 `--before` 검사, 새 자식·부모·원본 자식·손자의 양방향 관계
검사 6개가 모두 exit 0이다. 최종 비교는 `refine-validation-final/assertions.json`,
실제 명령·출력은 같은 폴더의 `commands.json`에 있다. 새 파일은 신규라 lifecycle `--before`를
붙이지 않고 별도 ID·필드·해시 비교를 적용했으며 기존 부모에는 정확한 before를 사용했다.
최종 소비 출력은 `build-spec-result.md`에 있다. 이슈 저작은 실행하지 않았다.

## 재현된 결함과 최소 수정

실제 run2의 done 사유에 포함된 개행이 `SKIPPED`를 둘로 나눴다. 같은 판단 JSON으로
직접 확인했으며 source renderer가 각 완성 출력 필드의 `splitlines()`를 공백으로 연결하도록
반환 한 줄만 바꿨다. 판단·ID·경로 검증과 후보 의미는 바꾸지 않았다.

`test-next-goal-render.py`에 실제 유형의 개행을 여러 판단 필드에 넣는 회귀 한 건을 추가했다.
수정 전 해당 검사만 실패(exit 1), 수정 후 관련 전체 검사 통과(exit 0)를 확인했다.
`render-regression-before.log`, `render-regression-after.log`가 근거다.
실제 run2 판단 JSON 재렌더도 exit 0, NEXT/FROM/SKIPPED/TRACE 네 줄이며 시각·개행 외 판단
내용은 동일하다(`render-live-after.stdout`, `nextgoal-assertions.json`). `git diff --check`도 통과했다.
이미 통과한 관계·lifecycle 전체 회귀는 소스 변화가 없어서 반복하지 않았다.

## 최종 요구 갭 검토 입력

독립 검토는 1회, 상한 1라운드다. 동일 기준 SHA와 `task-code.diff`, 이 검증 문서의 신규 diff,
원시 native 도구 기록·실제 결과·`refine-artifact.diff`를 제공하고
`thinking-tools/reference/seed-diff-grading.md`를 첨부한다. 기존 WIP는 검토의 신규 변경에서 제외한다.
검토 결과는 별도 검증 산출물에 보존한다. 검토 인프라 실패 시 재시도 없이 main 직접 대조로
보완하고 근거 한계를 기록한다.

설치 변경·실제 vault 작업·push·PR·merge·이슈 쓰기는 수행하지 않았다. local commit도 하지 않았다.
Seed의 전체 완료나 closed 전환, 현재 원본 main과 설치본에서의 통합 실행은 이 결과로 주장하지 않는다.
