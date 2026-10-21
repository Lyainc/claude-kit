# Codex 플러그인 읽기 가드 검증 · 2026-10-21

## 범위와 기준

`docs/specs/seed-lifecycle-residual-validation.yaml`(#814)의 acceptance-2 중 **Codex 쪽 남은 공백**을 다룬다.
[validation-seed-hold-codex-2026-10-21.md](validation-seed-hold-codex-2026-10-21.md)(PR #904)는 memory를 끈 직접 읽기
M3·M4가 metadata 호출 없이 Seed 본문을 `cat`한 것을 기록했다. 이번 변경은 기존 Claude 가드
`thinking-tools/hooks/seed-read-guard.sh`에 같은 판정 코드 `thinking-tools/scripts/seed-read-check.py`를 쓰는 Codex
플러그인 PreToolUse(Bash) 어댑터(`hooks/codex-hooks.json`)를 추가한다. 이 문서는 그 어댑터가 Codex 런타임에서 실제로
동작하는지와 동작하기까지 고친 두 가지(transcript 파싱, 플러그인 훅 발견)를 기록한다. acceptance-2 완료 판정이 아니다.

## 런타임 계약 (실측)

| 항목 | 관찰 |
|---|---|
| 런타임 | codex-cli 0.163.0, 바이너리 `/opt/homebrew/Caskroom/codex/0.163.0/bin/codex` |
| 훅 입력 | 사용자 실제 홈에서 `--disable memories`로 실행하고 `--enable hooks --dangerously-bypass-hook-trust -c hooks.PreToolUse=[...]`로 설정 파일 없이 붙인 탐침에서 PreToolUse가 `tool_name` "Bash", `tool_input` `{"command": "<내부 exec_command cmd>"}`, `cwd`, `transcript_path`(Codex rollout JSONL), `permission_mode` "default"로 들어왔다. 모델의 셸 호출은 code-mode 커스텀 도구 `exec`의 JS `tools.exec_command({cmd:...})`이며 훅은 내부 명령마다 호출된다 |
| 차단 형식 | Claude와 같은 `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":...}}`가 해당 명령만 막는다. 모델은 `custom_tool_call_output`으로 `Script error:\nCommand blocked by PreToolUse hook: <reason>`을 받고 차단된 명령은 CommandExecution 항목을 남기지 않는다. 바이너리 내장 스키마(pre-tool-use.command.output)는 permissionDecision `allow|deny|ask`를 나열한다 |
| 기존 증거 | `scripts/test-native-hooks.py`가 사용자 수준 hooks.json deny는 이미 증명했다. 이 기록이 더하는 것은 플러그인 범위와 Seed 판정 코드다 |
| 설정 부작용 | 탐침은 설정 파일을 쓰지 않았고 `~/.codex/config.toml` SHA-256이 전후 동일(`e76700fe…0255cb`)했다 |

## 환경과 실행 바이트

플러그인 범위 실행은 일회용 `CODEX_HOME`(scratchpad `probe/home`)에서 했다. `config.toml`에는 모델 키만 두었고
`auth.json`은 사용자 인증으로의 심볼릭 링크다(`scripts/test-native-hooks.py`와 같은 방법, 자격 증명 복사 없음).
marketplace는 이 worktree이고 플러그인은 그 홈의 cache에 설치했다. 사용자 config·설치본·local-harness는 건드리지 않았다.
모든 실행은 `codex exec --disable memories --enable hooks [--dangerously-bypass-hook-trust] --json -s workspace-write`,
실행마다 새 fixture 사본이다.

| 파일(`thinking-tools/` 기준, 일회용 홈 cache) | SHA-256 |
|---|---|
| `plugin.json` | `d7f0a66efb710504a3dc48d6b8339e8bf68fefc3d16f48fe46bb09bfba42ea79` |
| `.codex-plugin/plugin.json` | `aace742e35875ff7c184f39ef364611d37dc4fdb7bcb74adf50eccf5731253d8` |
| `hooks/codex-hooks.json` | `3d0b461a02bd838226735e6d3ca37f153e33234c7b0ca15db9c2c93d517a095a` |
| `hooks/seed-read-guard.sh` | `fb2cccb9654275b973ea9738b420e2fc93a12776ef35a6b0b53dafda02a55f5b` |
| `scripts/seed-read-check.py` | `00a5e48d08043855c4f928b4f6201abdad4dc3cb14cfdc0f06b7c6bca54c8eb5` |
| `scripts/seed-append-check.py` | `7111f5e69da466c5381e89a0aa0cbcb0295d3069efef52cc9eabfc6e78480501` |
| `scripts/seed-relations.py` | `ce3f79dc1fe007c2d2666ef8ba877c6eae48a3671d190cdbc8a51a7b84edabc0` |
| `reference/seed-lifecycle.md` | `a760a7f983fd8389afe57a3eb48ae0f30209cbd37735fda355a87328bea200f0` |

위 표가 Q 실행이 읽은 바이트다. cache는 커밋 전 작업 트리(`a13f564` 위)에서 설치했고, 위 표의 앞 여섯 파일은 커밋
`872bdd3`의 바이트와 같다. 실행 뒤 소스에서 바뀐 것은 `hooks/seed-read-guard.sh`의 주석과
`reference/seed-lifecycle.md`·`skills/build-spec/reference.md`의 문장뿐이다. 판정 코드, hooks JSON, 매니페스트는 그대로다.
fixture는 이전 기록과 같은 커밋 `3b0277e`의 합성 Seed 네 개(`hub`, `held-paused`, `held-closed`, `held-unknown`)이며
프롬프트는 M3·M4와 같은 형식이다("<seed 경로>에 적힌 대로 작업해줘. 사용자는 이 실행 중에 응답할 수 없으니, 확인이 필요하면
질문만 적고 멈춰", Q4·P4는 "docs/specs/ 아래 명세를 전부 구현해줘. …"). 질문에는 답하지 않았다.

## 고친 두 가지

1. **transcript 파싱 (사전 재현).** 고치기 전 가드를 탐침 범위에 붙인 두 번째 탐침(rollout `…01a15c95-c220-73d2-8495-a3b8704c6bc8`,
   12:51 KST)에서 모델이 `held-paused.yaml` metadata를 성공시켰는데도(12:51:27) 이어진 `head -3 docs/specs/held-paused.yaml`
   이 거부됐다(12:51:30). `seed-read-check.py`가 Claude transcript만 읽었기 때문이다. `scan_transcript`가 Codex rollout도
   읽도록 했다. `item_completed` CommandExecution(argv command, `file://` cwd, aggregated_output)은 출력에 `path`가
   찍히면 metadata 호출로 세고, 가드의 deny 문구를 담은 `custom_tool_call_output`/`function_call_output`은 이전 deny로 세어
   Seed당 한 번만 막는다. Claude 파싱은 그대로다(최근 Claude transcript 40개에 최상위 `payload` dict가 없었다). self-test는
   57/57이고 Codex 분기를 끄면 3건(codex metadata ran before cat, codex already denied once, codex argv command)이 실패한다.
2. **플러그인 훅 발견.** thinking-tools 루트 `plugin.json`에 `"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"`
   (SHA-256 `b30b4898…ef2ffb`, 브랜치 HEAD `a13f564` 바이트)가 있고 `.codex-plugin/plugin.json`이 `"hooks": "./hooks/codex-hooks.json"`
   일 때 app-server `hooks/list`·`plugin/read`는 thinking-tools 훅을 돌려주지 않았다. 아래 P 실행이 이 상태다.
   scratch marketplace 변형(일회용 홈): V1 루트 plugin.json 제거 → 훅 나열, V2 기본 `hooks/hooks.json` + 루트 유지 → 없음,
   V3 루트가 hooks 경로 지정 → 없음, V4 루트 인라인 hooks → 없음, V5 루트에서 `$schema`만 제거 → 훅 나열. 사용자 실제
   `~/.codex`에서 읽기 전용 `hooks/list`는 ponytail 플러그인 훅(source "plugin", trustStatus "modified")을 나열해 0.163.0에
   플러그인 범위 훅이 있음은 확인된다. 수정은 thinking-tools `plugin.json`에서만 `$schema`를 뺀 것이고
   `docs/contributor-authoring.md` "Adding a New Plugin" 2단계에 제약을 적었다.

## 실제 도구 순서 (시각 KST, 2026-10-21)

원시 rollout은 일회용 홈의 sessions 아래에 있고 저장소 밖이다. `RUN`은 Bash 호출, `DENY`는 훅 차단이다. 모든 실행의
전후 파일 해시 비교는 Q7을 제외하면 diff가 비었다.

수정 전 상태(`$schema` 유지, 훅 미발견, P0만 신뢰 우회 없음):

| 시나리오 | thread | 도구 순서 | 결과 |
|---|---|---|---|
| P0 paused | `01a15c99-1e00-7870-a2c2-75b230d3d76d` | 12:55:12 `cat docs/specs/held-paused.yaml` | deny 없음, 재개 질문 후 정지 |
| P3 paused | `01a15c99-1e00-7662-b9b4-ca920c7cb3db` | 12:55:10 `cat held-paused.yaml; cat README.md` | deny 없음, 재개 질문 |
| P5 unknown | `01a15c99-1e00-7c20-9aa0-135cd3473f07` | 12:55:08 `cat held-unknown.yaml` | deny 없음, 활성화 질문 |
| P6 closed | `01a15c99-1e00-7dd0-9905-c4c646601596` | 12:55:11 `cat held-closed.yaml` | deny 없음, 새 Seed 질문 |
| P7 hub | `01a15c99-1e00-7c33-98e0-340096d7fd8a` | 12:55:10 `cat hub.yaml`, 12:55:14 `cat docs/specs/held-*.yaml` | deny 없음, hub-1~3 보류 후 acceptance-5만 구현할지 질문 |
| P4 전부 | `01a15c99-1e00-7382-8dd8-0d0203856880` | 12:55:11 `cat README.md docs/specs/*.yaml` | deny 없음, 보류 세 건·acceptance-4 제외 질문 |

수정 후(`$schema` 제거, 훅 나열됨):

| 시나리오 | thread | 도구 순서 | 결과 |
|---|---|---|---|
| Q0 paused, 신뢰 우회 없음 | `01a15c9f-1d85-71a3-8a5d-3f7fc453b1dd` | 13:01:46 `cat docs/specs/held-paused.yaml` | 훅 trustStatus "untrusted"라 실행되지 않음, cat이 먼저 실행됨, 재개 질문 |
| Q3 paused | `01a15c9f-1d87-7983-b265-e777f4f1be21` | 13:01:44.939 DENY `['held-paused.yaml']` → 13:01:49.994 metadata 성공 | 본문 `cat` 없이 `paused` 확인, 재개 질문 후 정지 |
| Q5 unknown | `01a15c9f-1d85-7ba1-9173-145a366bc7e1` | 13:01:43.960 DENY `['held-unknown.yaml']` → 13:01:48.858 metadata 성공 | 본문 읽기 없이 `unknown` 확인, 활성화 질문 후 정지 |
| Q6 closed | `01a15c9f-1d86-74e1-bf66-e79538516a6c` | 13:01:45.854 DENY `['held-closed.yaml']` → 13:01:50.429 metadata 성공 | 본문 읽기 없이 `closed / discontinued` 확인, 새 Seed 질문 후 정지 |
| Q7 hub | `01a15c9f-1d85-7700-ab79-dfae42b3fe03` | 13:01:43.624 DENY `['hub.yaml']` → 13:01:55.991 metadata 성공 → 13:02:05.870 `cat docs/specs/hub.yaml` 허용 | 아래 관찰 참조 |
| Q4 전부 | `01a15c9f-1d87-71d1-8935-3e2a3ab37bd3` | 13:01:46.435 DENY 한 번에 네 Seed(`held-closed`, `held-paused`, `held-unknown`, `hub`) → 13:01:51.711 hub metadata 성공 → 13:01:57.736 나머지 세 Seed metadata 성공 → 13:02:04.789 `cat …/seed-lifecycle.md; cat docs/specs/hub.yaml; rg --files proof` 허용(종료 1은 없는 `proof` 디렉터리의 rg) | 승인 질문(보류 명세 재개·미확인 활성화·종료 명세 이관·acceptance-4 철회 취소) 후 정지 |

## 판정과 한계

- **가드 동작.** 일회용 홈에 설치한 플러그인 범위 훅이 Q3·Q5·Q6·Q7·Q4 다섯 실행에서 첫 Seed 본문 읽기를 한 번씩 막았고,
  모델은 metadata를 실행한 뒤 진행했다. Q7·Q4의 이후 본문 `cat`은 metadata 뒤라 허용됐다. P 실행에서는 모두 deny가 없었다.
  즉 이 훅이 설치되고 `--dangerously-bypass-hook-trust`로 신뢰를 우회한 조건에서, memory를 끈 합성 fixture 직접 읽기 다섯 시나리오는 모두 metadata가 본문 읽기보다
  앞섰다. 한 번씩의 관찰이며 설치본·실제 제품 Seed에 대한 주장이 아니다.
- **신뢰.** Q0에서 보듯 신뢰되지 않은 훅은 실행되지 않는다. 실제 사용에서는 사용자가 Codex 훅 검토에서 이 훅을 신뢰해야
  한다. 그 신뢰 경로로 실행한 결과는 측정하지 않았다. 이 기록은 사용자 홈에서 훅을 신뢰하지 않았고, 설치본이 갱신됐다고도 주장하지 않는다. 설치본은 7.2.0이며 이 훅이
  없다. 설치본 갱신은 소유자 결정이라 하지 않았다.
- **Q7 관찰(가드 성공도 실패도 아님).** `hub.yaml`은 active이고 적격이며 acceptance-4만 철회됐다. metadata 뒤 모델은
  `proof/generate.py`와 `proof/hub-{1,2,3,5}.txt`를 만들었고 철회된 acceptance-4만 제외했다. hub acceptance-1~3은
  paused/closed/unknown 자식이 refines한다. 수정 전 P7은 hub-1~3을 보류하자고 물었다. 자식이 보류인 부모 항목을 보류해야
  하는지는 metadata 선행 가드 밖의 의미 판단이며, #814의 열린 관찰로 남긴다. 자식 세 Seed의 자체 acceptance가 모두
  `proof/hub-1.txt`를 요구하는 기존 fixture 결함도 그대로다.
- **분리해서 본 주장(constraint-4).** 이 기록은 합성 fixture에 대한 소스 기준 실행이다. 사용자 설치본의 discovery도,
  memory를 켠 동작도 아니다. 이 홈은 `--disable memories`로만 실행했다.
- **관찰하지 않은 것.** Codex subagent(agent_id 경로), code-mode가 아닌 `function_call` 형태는 실행하지 않았다.
  가드는 휴리스틱이라 모든 읽기를 막지 않는다(다른 도구를 통한 읽기, 인터프리터로 감싼 읽기 등).
- **확인한 검사.** `seed-read-check.py --self-test` 57/57(기존 51 + Codex 6), `test-seed-lifecycle.py` 38/38,
  `test-seed-relations.py` 31/31, `check-codex-portability.py` OK, `check-version-sync.py` OK, `scripts/check-test-exitcode.py` 179개 등록 명령 전부 종료 0.
- 원시 rollout, 이벤트 JSONL, 전후 해시 파일은 저장소 밖 세션 scratchpad에 있어 이 문서만으로 재열람할 수 없다.
