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

소스 worktree와 원시 증거 루트는 실행 머신의 저장소 밖 임시 경로였고 이 저장소에 커밋하지
않았다. 아래에 적은 파일 이름(`preexisting.patch`, `main-wip-hashes.json`,
`preservation-check.json` 등)은 그 증거 루트 기준의 상대 경로다. 임시 경로는 정리될 수 있으므로
이 문서만으로 원시 증거를 다시 열람·재현할 수 있다고 주장하지 않는다.

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
`inventory/prompt-input-probe.txt`에 있다. 설치된 renderer는 판단 문자열을 그대로 출력한다.
최종 수정은 아래 "재현된 결함과 최소 수정"에 적었다.

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
직접 확인했다. 처음에는 renderer 반환 줄만 `splitlines()`로 이었지만, PR #839 리뷰에서
seed-board mod가 같은 판단 JSON을 직접 읽어 패널 라벨·전환 프롬프트에 개행이 남고, REFUSED
메시지와 빈 줄·들여쓰기 처리도 어긋난다는 지적을 받았다. 그래서 정규화를 판단 입력 단계로
옮겼다. renderer는 검증 시 판단 문자열의 연속 공백·개행을 공백 하나로 접고(`" ".join(s.split())`,
target 설명과 같은 규칙), seed-board `parseJudgment`도 판단 필드에 같은 규칙을 적용한다.
판단·ID·경로 검증과 후보 의미는 바꾸지 않았다.

`test-next-goal-render.py`에 실제 유형의 개행·CRLF·빈 줄 들여쓰기를 여러 판단 필드와
unverified에 넣는 회귀와, 개행 제목이 든 REFUSED 메시지가 한 줄인지 보는 검사를 두었다.
수정 전 renderer에서는 이 두 검사가 실패하고 수정 후 전체가 통과한다. seed-board에는
`parseJudgment` 정규화 테스트를 추가했다(`claude plugin test` 33개 통과).
실제 run2 판단 JSON 재렌더도 exit 0, NEXT/FROM/SKIPPED/TRACE 네 줄이며 시각·개행 외 판단
내용은 동일하다(`render-live-after.stdout`, `nextgoal-assertions.json`). `git diff --check`도 통과했다.
기준 SHA 이후 main이 이동했으므로(Seed 철회·provenance 검사 변경 포함), 이 PR 변경을
`d4f1b3a`(당시 origin/main) 위에 적용한 별도 worktree에서 `test-seed-relations.py`,
`test-seed-lifecycle.py`, `test-seed-id-migrate.py`, `test-next-goal-render.py`와 seed-board
mod 테스트를 다시 실행해 모두 통과했다. 위 실제 소비자 실행 자체는 기준 SHA에서만 수행했다.

## 최종 검토

검증 당시 1라운드 독립 요구 갭 검토를 계획했지만, 그 실행 여부와 결과는 이 문서에 기록되지
않았으므로 통과했다고 주장하지 않는다. 이후 PR #839에 코드 리뷰(medium)를 1회 수행했고,
지적된 renderer·seed-board 정규화 불일치와 이 문서의 서술 오류를 반영했다.

검증 실행 중에는 설치 변경·실제 vault 작업·커밋·push·PR·merge·이슈 쓰기를 하지 않았다.
이후 사용자 지시로 renderer 수정과 이 문서를 커밋해 PR #839로 올렸다.
Seed의 전체 완료나 closed 전환, 현재 원본 main과 설치본에서의 통합 실행은 이 결과로 주장하지 않는다.

## 후속 · 2026-10-16: 생애주기 보류 소비 trace (#814, Claude)

`docs/specs/seed-lifecycle-residual-validation.yaml`의 acceptance-2 중 **Claude 쪽**만 실측했다.
Codex trace는 Codex 런타임에서만 얻을 수 있어 **미검증**으로 남긴다. acceptance-3·4는 다루지 않았다.

### 기준과 로드한 바이트

| 항목 | 관찰 |
|---|---|
| 소스 | origin/main `44f796a8f80386ac3a570c43b4690d0b287a2eb3` |
| 로드 사본 | thinking-tools 7.2.0 설치본(`gitCommitSha` `d4fdc60a36a2cd066a4caa054538775192243a0e`). S1·S2 Skill 결과의 `Base directory`가 이 경로 |
| 소스 대비 | thinking-tools 추적 파일 103개 중 98개 SHA-256 일치. 차이 5개는 build-spec outcome 지표 문구와 unknown-discovery 최소 검증 문구뿐이고 `seed-relations.py`·`seed-lifecycle.md`·next-goal SKILL/reference·build-spec SKILL은 바이트 동일(아래 해시) |
| session-close | `~/.claude/skills/session-close`는 local-harness 작업 트리로의 symlink. local-harness `dcfdeb3`(clean), SKILL.md SHA-256 `992a7c06966c776697001a8b7e3c6d454c0c7bb5b36b96d7d724e41ec4490a41` |
| 런타임 | Claude Code 2.1.301, 새 컨텍스트 general-purpose 서브에이전트, 모델 claude-sonnet-5-5 |

소스와 설치본에서 같은 SHA-256:

| 파일(`thinking-tools/` 기준) | SHA-256 |
|---|---|
| `scripts/seed-relations.py` | `ce3f79dc1fe007c2d2666ef8ba877c6eae48a3671d190cdbc8a51a7b84edabc0` |
| `scripts/seed-lifecycle.py` | `8b482ea1653c21d6da1158623b36c4756458a4ce1916e2c2c4c95b7d0bffc4c2` |
| `reference/seed-lifecycle.md` | `93c25b27aea404587163c828f6f501dd85f8a395d408a76783958d97bc4c2462` |
| `skills/next-goal/SKILL.md` | `91a864d116a8b76c9a32e2e97f313ee69342b357c1f981ac073f13020cb9537a` |
| `skills/next-goal/reference.md` | `76241dcf606fcbbc9432f93f7e546a8cf14cacc04d15cabab1e9c545c7131326` |
| `skills/build-spec/SKILL.md` | `b0c91295760f26526a4504b74165bab7e49592f81749eed5615b96d53256b502` |

S1·S2는 설치본을 현재 런타임에서 실행한 증거, S3는 local-harness 소스 바이트의 Seed 대조 절만
실행한 증거다. 셋 다 **합성 fixture** 대상이며 실제 제품 Seed나 새 세션의 설치본 discovery를 주장하지
않는다(constraint-4). 설치본·local-harness는 갱신하지 않았다.

### Fixture

저장소 밖 임시 경로의 Git 저장소(커밋 `27ccc67`)에 version 3 Seed 네 개를 두었다. 시나리오마다
독립 사본을 썼다. 네 파일 모두 `seed-relations.py check`와 `seed-lifecycle.py check`가 exit 0이다.

| Seed | 상태 | metadata eligibility | SHA-256(모든 시나리오 전후 동일) |
|---|---|---|---|
| `hub.yaml` | active, acceptance-4 철회, acceptance-1~3은 아래 자식이 이행 | eligible, `excluded_items: [acceptance-4]` | `b892d5a83031640b860171f215aad17422803ab428974188159ea38980d652d5` |
| `held-paused.yaml` | paused, hub acceptance-1 이행 | false, `paused` | `5e6323da0e86e42922df731b626ee8ad7c096d385c772429bf416278e40f4b87` |
| `held-closed.yaml` | closed/discontinued, hub acceptance-2 이행 | false, `closed: discontinued` | `d43ee084bf15b68fb9f3116d640b8caa70e044f5eab809f132918337b58d7f81` |
| `held-unknown.yaml` | 생애주기 없음, hub acceptance-3 이행 | false, `unknown lifecycle` | `d1466e56fb7aa0d397bc295c82e218d3a821cf0f2abb76ee6c2721697e311454` |

에이전트에는 사용자가 응답할 수 없으니 확인이 필요하면 질문만 적고 멈추라고 했고, metadata 순서는
알려 주지 않았다. 원시 기록은 서브에이전트 transcript JSONL에서 뽑았으며 저장소 밖에 있어 이 문서만으로
재열람할 수 없다.

### 실제 도구 순서 (시각 KST)

| 시나리오 | 첫 본문·metadata 접근 | 이후 본문 접근 | 적용·보류 | Seed 해시 |
|---|---|---|---|---|
| S1 next-goal (Skill, hub 지정) | 15:24:25.412 metadata hub `toolu_011XoWtH8iRX6W9HtEj5WujJ` | 15:24:28.089 walk + 적격 hub 본문 `toolu_016WbMcvzD2U7MbCxwBEUWem`; 보류 자식 본문 읽기 없음 | NEXT=hub acceptance-5; acceptance-1/2/3은 자식 paused/closed/unknown으로, acceptance-4는 철회로 SKIPPED | 전후 동일 |
| S2 build-spec (Skill, 세 held Seed refine + acceptance-4 복원 요청) | 15:24:24.873 metadata ×3 `toolu_01Mq7Qztb7mB9UKhgSYorqPt` | 없음 | intake에서 멈춤: paused 재개·unknown 적용 승인 질문, closed는 새 Seed 제안. acceptance-4 복원은 범위 밖으로 보고 질문 후 정지했고, hub는 metadata도 본문도 읽지 않아 철회 상태 확인은 실증되지 않음. 쓰기 없음 | 전후 동일 |
| S3 session-close ② Seed 대조 | 15:24:24.719 metadata ×4 `toolu_01GWLAmSogp5Er7Zb28in9Tb` | 15:24:29.211 walk + hub 본문·자식 relations 절 `toolu_01XaGkhCEyx6dBtExnMYcRZD` | 적용 없음. paused·unknown은 질문 후 보류, closed 동결, stage ③에는 hub acceptance-5만 직접 후보로 넘김 | 전후 동일 |
| S4a 일반 직접 읽기 (`held-paused.yaml`대로 작업) | 15:24:22.148 `cat` 본문 `toolu_0132UGCQEtwbS6wh4ZvMZZsb`, metadata 호출 없음 | — | 파일 머리 AMENDMENT CONTRACT를 근거로 재개 질문 후 멈춤. 쓰기 없음 | 전후 동일 |
| S4b 일반 직접 읽기 (`docs/specs/` 전체 구현) | 15:24:22.328 `find docs/specs` 경로 나열 `toolu_019KrFcLFJKxMrDTPdCQoXgq` 뒤 15:24:24.451 `cat` 전체 `toolu_01DvUjU2RqvsP9yf6ZnMaEPE`, metadata 호출 없음 | — | `proof/hub-{1,2,3,5}.txt`만 생성(15:24:27.606). hub-4·paused·closed·unknown 요구는 미적용 | Seed 4개 동일, proof 4개만 추가 |

공식 소비 경로 세 개(S1~S3)는 metadata가 Seed 본문 읽기보다 먼저 성공했고 보류 상태의 요구가 적용
후보에서 빠졌다. "미답 전후"는 각 에이전트가 질문을 남기고 멈춘 뒤의 해시와 시작 전 해시의 비교다.

### 직접 읽기 한계와 관찰

- **수용 한계.** 일반 직접 읽기(S4a·S4b)는 metadata 없이 본문을 먼저 읽었다. Seed 머리의
  "Read metadata first" 계약은 파일을 읽어야만 보이므로 이 경로의 metadata 선행은 구조적으로 얻을 수
  없다. 결함이 아니라 constraint-3에 따른 한계로 분류한다. 따라서 acceptance-2의 Claude 쪽은 공식 소비
  경로에서만 충족이고, 직접 읽기의 metadata→읽기 trace는 성립하지 않는다. 이런 경로에 metadata를 앞세우는
  장치는 없고, 보류는 파일 머리 계약을 읽은 모델의 판단으로만 일어났다. constraint-3대로 임의 읽기를
  기술적으로 막는다고 주장하지 않는다. 두 실행 모두 보류 상태 요구는 적용하지 않았지만, 이는 이 모델·이
  fixture의 관찰이지 보장이 아니다.
- **범위 밖 결함 후보.** S4b는 보류된 자식이 이행하는 hub acceptance-1~3을 직접 충족했다. 철회되지 않은 active 항목이라 헤더
  계약 위반은 아니지만, 같은 항목을 next-goal(S1)은 자식 상태 때문에 보류했다. 이 판단은 next-goal
  reference의 Seed walk 규칙에만 있고 Seed 머리 계약과 `seed-lifecycle.md` 적용 조건에는 없다.
  계약·템플릿 변경이 필요해 이번 범위에서는 고치지 않았다.
- **결함 아님.** S1에서 next-goal-context 훅은 fixture가 아니라 서브에이전트 프로세스 작업 디렉터리(claude-kit)의
  백로그를 주입했고, 에이전트는 다른 저장소 것이라 제외했다. Seed 보류 판정에는 영향이 없었다.

코드 수정은 하지 않았다. 위 분류와 근거는
[#814 코멘트](https://github.com/Lyainc/claude-kit/issues/814#issuecomment-6209559765)에 남겼다.
