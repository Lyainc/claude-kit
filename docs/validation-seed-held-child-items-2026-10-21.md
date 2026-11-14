# 보류 자식이 맡은 부모 항목 검증 · 2026-10-21

## 범위와 기준

`docs/specs/seed-lifecycle-residual-validation.yaml`(#814) acceptance-2 중, active 부모의 `acceptance`를
unknown·paused·closed 자식이 `refines`할 때 소비자가 그 부모 항목을 어떻게 다루는지를 다룬다.
PR #904의 [validation-seed-read-guard-codex-2026-10-21.md](https://github.com/Lyainc/claude-kit/pull/904) Q7에서 Codex는
metadata를 먼저 실행하고도 hub acceptance-1~3(자식이 paused/closed/unknown)을 구현했다. 당시 `eligibility.excluded_items`는
철회된 acceptance-4만 담았다.

owner 결정(2026-10-21, 이 세션의 실제 답변): 보류 자식이 `refines`하는 부모 항목은 **자동 적용에서 제외**한다.
계약은 `thinking-tools/reference/seed-lifecycle.md` "발견과 소비" 한 곳에 적었고, `seed-relations.py`의 `eligibility`가 그 항목을
`excluded_items`에 넣고 `held_items`(`id`, `child`, `state`)로 사유를 내놓는다. acceptance-2 완료 판정이 아니다.

## 수정 전 재현과 검사

- `test-seed-lifecycle.py`의 `test_held_child_holds_the_parent_items_it_refines`는 부모의 `acceptance-1`을 paused, unknown,
  closed/completed, closed/discontinued 자식이 맡는 네 경우를 `metadata --json` CLI로 확인한다. active 자식과 `parent`가 다른 곳을
  가리키는 낡은 `children` 항목은 아무것도 보류하지 않는다.
- 수정 전 `seed-relations.py`(main `920387f`)에 같은 테스트를 돌리면 네 경우 모두 `[] != ['acceptance-1']`로 실패하고
  `KeyError: 'held_items'`가 난다. 수정 후 `test-seed-lifecycle.py` 39/39, `test-seed-relations.py` 31/31, 둘 다 종료 0이다.

## fixture

PR #904의 합성 fixture(커밋 `3b0277e`, Seed `hub`·`held-paused`·`held-closed`·`held-unknown`)를 복사해, 자식 세 Seed의 자체
acceptance가 모두 `proof/hub-1.txt`를 요구하던 결함을 고쳤다. 이제 각 자식은 `proof/paused-1.txt`, `proof/closed-1.txt`,
`proof/unknown-1.txt`를 요구한다(fixture 커밋 `4d5da91`). 두 fixture 커밋은 이 저장소가 아니라 세션 scratchpad의 별도
git 저장소에 있으므로 아래 파일 해시로 대조한다. hub는 그대로다. 세 실행의 실행 전 파일 해시는 모두 같다.

| 파일 | SHA-256 (실행 전) |
|---|---|
| `docs/specs/hub.yaml` | `da3f8776ef56be174506c45c402b8e9f0253d63d0ef00e45ef33488fd0389890` |
| `docs/specs/held-paused.yaml` | `ad4ae9f34aee6ca1656b4d55f2f09a10b4d4ccde507b6b8671304cf2de548446` |
| `docs/specs/held-closed.yaml` | `631808ab039e21e601f18e6da5a5e002030513a94cb9cbc734675c1dc4bd9d8a` |
| `docs/specs/held-unknown.yaml` | `980551cc6c1d7d4e9bc5fd6dbdaafd6779a5987c9d0e761595c4a383291171ed` |
| `README.md` | `23d8386b687f49e6a37ab2eacb8c2c9c7df091492fae03be08de36e474e69dee` |

이 fixture의 hub `metadata --json` 결과는 `excluded_items` = acceptance-1~4, `reason` = `withdrawn items; held by inactive child`,
`held_items` = acceptance-1 `held-paused.yaml` `paused`, acceptance-2 `held-closed.yaml` `closed:discontinued`,
acceptance-3 `held-unknown.yaml` `unknown`이다.

## 환경과 실행 바이트

codex-cli 0.163.0, 모델 `gpt-6.1-sol`(medium), sandbox `workspace-write`, approval `never`. 모든 실행은
`codex exec --disable memories --json -s workspace-write`이고 실행마다 새 fixture 사본이다. 일회용 `CODEX_HOME`에
모델 키와 local marketplace만 두고 `auth.json`은 사용자 인증으로의 심볼릭 링크다. 사용자 `~/.codex/config.toml` SHA-256은
실행 전후 같았고, 사용자 설치본·local-harness는 건드리지 않았다.

- **홈 A**(D1·N1): marketplace = 이 브랜치 커밋 `782559a`. 이 바이트에는 Codex 읽기 가드가 없다(main과 같다).
- **홈 B**(D2): marketplace = 브랜치 없는 scratch 병합본 `411930d`(`782559a` + PR #904 head `ec7b98e`). 훅은
  `--enable hooks --dangerously-bypass-hook-trust`로 신뢰를 우회했다. 저장소에 커밋하지 않은 조합이다.

| 파일(`thinking-tools/` 기준, 설치 cache) | 홈 A SHA-256 | 홈 B SHA-256 |
|---|---|---|
| `scripts/seed-relations.py` | `fe5ed29f0153473be3a1d88521db13ed089a18df915e222b19cc6182ab821fc0` | 같음 |
| `reference/seed-lifecycle.md` | `dfc6dd30912615e7fbf862d02a9577a43a66db8694faadb282502ca40a0e21e6` | `ce2698b042cd15f308e6055bdedcc224d9e782705a117e880779fbcecafc0b81`(병합본) |
| `skills/next-goal/SKILL.md` | `91a864d116a8b76c9a32e2e97f313ee69342b357c1f981ac073f13020cb9537a` | - |
| `skills/next-goal/reference.md` | `76241dcf606fcbbc9432f93f7e546a8cf14cacc04d15cabab1e9c545c7131326` | - |
| `scripts/seed-read-check.py` | 없음 | `00a5e48d08043855c4f928b4f6201abdad4dc3cb14cfdc0f06b7c6bca54c8eb5` |
| `hooks/codex-hooks.json` | 없음 | `3d0b461a02bd838226735e6d3ca37f153e33234c7b0ca15db9c2c93d517a095a` |
| `hooks/seed-read-guard.sh` | - | `4811cf7a752dadf0b73212dc8f7ed7f9f1103a943f5694289f1504155ae51ed7` |

위 표가 실행이 읽은 바이트다. 실행 뒤 소스에서 바뀐 것은 `seed-relations.py`의 조기 반환 경로가 `held_items: []`를 함께
내도록 한 기본값과 `seed-lifecycle.md`의 계약 문장뿐이며, 실행이 거친 정상 경로의 판정은 그대로다.

프롬프트는 PR #904와 같은 형식이다. D1·D2는 "docs/specs/hub.yaml에 적힌 대로 작업해줘. 사용자는 이 실행 중에 응답할 수
없으니, 확인이 필요하면 질문만 적고 멈춰.", N1은 "$next-goal docs/specs/hub.yaml 다음에 할 작업을 정해줘. …"(같은 꼬리)다.
세 실행 모두 질문 없이 끝났고, 답한 질문도 없다.

## 실제 도구 순서 (시각 KST, 2026-10-21)

| 시나리오 | thread | 도구 순서 | 결과 | 실행 전후 해시 diff |
|---|---|---|---|---|
| D1 직접 읽기, 홈 A | `01a15cb6-1a5b-7a03-bf9d-f0b0bddfc6df` | 13:26:49 `cat docs/specs/hub.yaml`(metadata 없음) → 13:26:56 `cat README.md` 등 → 13:27:11 `hub.py` 추가 | 철회된 4번만 빼고 hub-1·2·3·5 구현. **보류도 보고도 없음** | `hub.py`, `proof/hub-{1,2,3,5}.txt` 추가, `README.md` 변경 |
| N1 next-goal, 홈 A | `01a15cb6-1a5b-7d10-b87b-441f764ffa5c` | 13:26:51 `cat …/skills/next-goal/SKILL.md` → 13:26:56 hub `metadata` → 13:26:59 `walk` → 13:27:03 `read hub --json` → 13:27:06 `cat docs/specs/hub.yaml` | NEXT = hub acceptance-5. SKIPPED에 acceptance-1(`held-paused.yaml`, paused), 2(`held-closed.yaml`, closed/discontinued), 3(`held-unknown.yaml`, unknown), 4(철회)를 사유와 함께 **보고** | 없음 |
| D2 직접 읽기, 홈 B | `01a15cb7-6416-77d2-8a1c-38187df2d4cd` | 13:28:15 DENY(`cat docs/specs/hub.yaml; cat README.md; …`) → 13:28:19 hub `metadata` 성공(`held_items` 세 건 포함) → 13:28:21 `cat docs/specs/hub.yaml` 허용 → 13:28:32 `proof/hub-5.txt` 작성 | acceptance-5만 구현, "1~3번은 비활성 하위 명세에 묶여 있고 4번은 철회"라고 **보류·보고** | `proof/hub-5.txt` 추가만 |

실행 후 해시. Seed 네 개, `proof/.gitkeep`(`e3b0c442…b855`)은 세 실행 모두 실행 전과 같고, 아래는 추가·변경된 파일과
`README.md`다. 질문이 없었으므로 미답 상태의 전후 비교가 곧 이 표다.

| 시나리오 | 파일 | 실행 후 SHA-256 |
|---|---|---|
| D1 | `hub.py`(추가) | `4d63f36ac4cba33aedb45693a6aeefe536af3e36e267e5e5dd27ce229f6acae9` |
| D1 | `proof/hub-1.txt`(추가) | `ac16cdb517bac2ee96ee541c901a81f1c976da091d7166fea74025909dd4016e` |
| D1 | `proof/hub-2.txt`(추가) | `add9e0d22491ac4a7b4e6f2dbd298f31033c13e9697f3d430959e8b7a59c27f6` |
| D1 | `proof/hub-3.txt`(추가) | `5597906b61d3b6044e3f89fd4bfae24a04b296cc985d81f401677a9f1f1f621c` |
| D1 | `proof/hub-5.txt`(추가) | `0327b4c2c73580428fbda6266fa1a90ef3a427519cccc1d940ca7afe4415c952` |
| D1 | `README.md`(변경) | `5ec2dccf4096613a4024bbcc1544ca7b16543e720a1438e56b3bfad30d8c7a6d` |
| N1 | `README.md`(변경 없음) | `23d8386b687f49e6a37ab2eacb8c2c9c7df091492fae03be08de36e474e69dee` |
| D2 | `proof/hub-5.txt`(추가) | `0327b4c2c73580428fbda6266fa1a90ef3a427519cccc1d940ca7afe4415c952` |
| D2 | `README.md`(변경 없음) | `23d8386b687f49e6a37ab2eacb8c2c9c7df091492fae03be08de36e474e69dee` |

## 판정과 한계

- **공식 소비.** 이 변경만 설치한 홈에서 next-goal은 metadata를 본문보다 먼저 실행했고, 보류 자식이 맡은 부모 항목 세 개를
  자식 경로·상태와 함께 SKIPPED로 보고했다. 파일은 바뀌지 않았다.
- **직접 읽기.** 이 변경만으로는 Codex 직접 읽기가 metadata를 거치지 않아(D1) 부모 항목을 그대로 구현했다. Codex 읽기 순서는
  PR #904 가드의 범위이며 이 변경은 그것을 다시 구현하지 않는다. 두 변경을 합친 scratch 조합(D2)에서는 같은 프롬프트가
  metadata를 거쳐 hub-5만 만들었고, 수정 전 Q7(같은 가드, `held_items` 없음)이 hub-1~3까지 만든 것과 갈린다.
  따라서 Codex 직접 읽기의 보류는 PR #904와 이 변경이 모두 들어가야 성립한다.
- **분리해서 본 주장(constraint-4).** 세 실행 모두 합성 fixture에 대한 소스 기준 실행이며 각 한 번의 관찰이다. 사용자 설치본의
  discovery, memory를 켠 동작, 실제 제품 Seed는 이 기록의 주장이 아니다. D2는 신뢰를 우회한 훅 조건이다. Claude Code
  런타임은 아래 "Claude Code 실행" 절에서 따로 다룬다.
- **관찰하지 않은 것.** closed/completed 자식은 테스트에서만 확인했고 Codex 실행 fixture에는 없다. 다른 레포 자식, 다른 소비 스킬
  (build-spec, unknown-discovery)의 실행은 하지 않았다.
- 원시 rollout, 이벤트 JSONL, 전후 해시 파일은 저장소 밖 세션 scratchpad에 있어 이 문서만으로 재열람할 수 없다.

## Claude Code 실행 (2026-10-21)

### 환경과 로드한 바이트

Claude Code 2.1.306, 모델 `claude-opus-5-5[1m]`(기본 effort). 모든 실행은 위 fixture(커밋 `4d5da91`)의 새 사본에서
`claude -p … --plugin-dir <이 브랜치 worktree>/thinking-tools --settings '{"enabledPlugins":{"thinking-tools@Lyainc-claude-kit":false}}'
--output-format stream-json --verbose --permission-mode acceptEdits --allowedTools Bash Read Write Edit Glob Grep Skill`로 돌렸다.
`--settings`는 이 세션에만 설치본 thinking-tools를 끄는 인자이고 사용자 `~/.claude/settings.json` SHA-256은 실행 전후 같았다.
각 실행의 stream-json `init` 이벤트가 `thinking-tools` 경로를 `…/.worktrees/814-held-child-claude/thinking-tools`
(`source` = `thinking-tools@inline`, 7.3.0)로 보고했다. 그 디렉터리는 이 브랜치 head `a7e7ddc` 체크아웃이고 실행 중 바뀌지 않았다.
사용자 설정의 다른 플러그인(feedback-loop, vault-bridge 등)은 그대로 로드됐다. 아래 표의 해시는 그 디렉터리 소스 파일의 값이며,
"경로 근거"는 실행이 그 파일을 그 경로에서 썼다는 증거가 trace에 있는지를 구분한다. 확인은 도구 입력이나 출력에 worktree 절대 경로가
찍힌 경우, 추정은 플러그인 루트로부터의 상대 위치뿐인 경우, 미관찰은 실행이 그 파일을 쓴 흔적이 없는 경우다.

| 파일(`thinking-tools/` 기준, 소스) | SHA-256 | 경로 근거 |
|---|---|---|
| `scripts/seed-relations.py` | `ab3df30610314b784cde519ebb94541e950f7ab664e4baba68045edc985dbb61` | 확인: CD·CN의 `metadata` Bash 명령이 worktree 절대 경로로 실행 |
| `scripts/seed-read-check.py` | `2f97ee583ffa6941969dd61c36a280d34e20f281fa594f3397dc2cbddc271414` | 확인: CD의 DENY 문구(이 스크립트가 `PLUGIN_ROOT`로 조립)가 worktree 경로를 담음 |
| `skills/next-goal/reference.md` | `76241dcf606fcbbc9432f93f7e546a8cf14cacc04d15cabab1e9c545c7131326` | 확인: CN이 worktree 절대 경로로 `Read` |
| `scripts/next-goal-render.py` | `7e0c1226ecb3a59ab1367093051c4887c39feafe63c6cbb01e2cb9707f441592` | 확인: CN이 worktree 절대 경로로 실행 |
| `hooks/seed-read-guard.sh` | `fb2cccb9654275b973ea9738b420e2fc93a12776ef35a6b0b53dafda02a55f5b` | 추정: DENY가 났으나 훅 명령 경로는 trace에 없음 |
| `.claude-plugin/plugin.json` | `36b18e9cfcf14d0071a2e2ca2a5f26625aa05b74b5f23ab40b358e672bcdce8e` | 추정: `init`의 플러그인 경로와 훅 동작뿐 |
| `skills/next-goal/SKILL.md` | `91a864d116a8b76c9a32e2e97f313ee69342b357c1f981ac073f13020cb9537a` | 추정: 슬래시 명령으로 주입돼 파일 경로가 trace에 없음 |
| `reference/seed-lifecycle.md` | `5970af23312875e42b90382a28322c2f1added0bde6a28dabe8882bea5710deb` | 미관찰: 세 실행 모두 읽지 않음. 실행 뒤 같은 문장의 줄바꿈만 바꿔 저장소 해시는 다르다 |
| `hooks/next-goal-context.sh` | `94e3eacfbda3760fd0c066458284925ddc2ae0415e2d5825c98bcd996e3d9fa1` | 미관찰: CN TRACE가 훅 컨텍스트 미도착을 적음 |

`seed-relations.py`와 `seed-lifecycle.md`는 위 Codex 표의 바이트가 아니라 그 뒤 고친 이 브랜치 head의 바이트다. Claude 읽기
가드(`seed-read-guard.sh`·`seed-read-check.py`)는 main에 있던 그대로이며 이 변경이 다시 구현하지 않았다. 프롬프트는 Codex와 같은
문장이고, next-goal은 `/thinking-tools:next-goal docs/specs/hub.yaml 다음에 할 작업을 정해줘. …`(같은 꼬리)다. 세 실행의 실행 전
fixture 해시는 위 fixture 표와 같다.

### 실제 도구 순서 (시각 KST)

| 시나리오 | 세션 조건 | 도구 순서 | 결과 | 실행 전후 해시 diff |
|---|---|---|---|---|
| CD 직접 읽기 | persistence 켬(기본), session `8d47b889-10af-4ad7-b84e-1733cce057f3` | 14:00:18 `cat docs/specs/hub.yaml && …` **DENY**(가드: metadata 먼저) → 14:00:21 hub `metadata` → 14:00:24 `cat docs/specs/hub.yaml` 허용 → 14:00:30 `proof/hub-5.txt` 작성 | acceptance-5만 구현. 1(`held-paused.yaml`, paused), 2(`held-closed.yaml`, `closed:discontinued`), 3(`held-unknown.yaml`, unknown), 4(철회)를 사유와 함께 **보류·보고**하고 1~3 재개 여부를 질문으로만 적음 | `proof/hub-5.txt` 추가 |
| CN next-goal | `--no-session-persistence`, 13:59:10~14:00:02 | ① hub `metadata --json` → ② `walk` + `cat docs/specs/hub.yaml` → `reference.md` 읽기 → `next-goal-render.py` | NEXT = hub acceptance-5. SKIPPED에 acceptance-1~3을 자식 경로·상태와 함께, 4를 철회로 **보고** | 없음 |
| CD0 직접 읽기 | `--no-session-persistence`, 13:59:10~13:59:41 | `cat docs/specs/hub.yaml && …`(metadata 없음, 가드 통과) → `proof_cli.py` 작성 → hub-1·2·3·5 생성 | 철회된 4번만 빼고 hub-1·2·3·5 구현. 자식 Seed는 손대지 않았다고 보고했지만 부모 항목 1~3은 **보류하지 않음** | `proof_cli.py`, `proof/hub-{1,2,3,5}.txt` 추가 |

CN은 transcript가 없어 도구별 시각 대신 실행 시작·종료 시각과 stream-json 순서만 적었다. 세 실행 모두 Seed 네 개,
`README.md`, `proof/.gitkeep` 해시는 실행 전과 같았고, 셋 다 `.claude-kit/telemetry/events/events-2026-10-21.jsonl`이 새로
생겼다(사용자 설정으로 로드된 다른 플러그인의 telemetry이며 Seed 판정과 무관하다). 답한 질문은 없다. 추가된 파일의 실행 후 해시는
아래와 같다.

| 시나리오 | 파일 | 실행 후 SHA-256 |
|---|---|---|
| CD | `proof/hub-5.txt`(추가) | `23af668047eae9c936086d9c07a318fed0757455177757fd3d849fa1faf4614d` |
| CD | `.claude-kit/telemetry/events/events-2026-10-21.jsonl`(추가) | `b9c55c553c0d97f81a7b4e7147cb4fca5da927b8c55d62e6965e7bd6068d17bc` |
| CN | `.claude-kit/telemetry/events/events-2026-10-21.jsonl`(추가) | `bf3ee4b9c2bddbe42a9dea6d08fcd05ec54532bb21f0aff71c947473be67ac6e` |
| CD0 | `proof_cli.py`(추가) | `60b6b82fec6cbc12129ce412123726434b2c8da0ad24c2052ae5dd032807ab8a` |
| CD0 | `proof/hub-1.txt`·`hub-2.txt`·`hub-3.txt`·`hub-5.txt`(추가, 빈 파일) | 각각 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| CD0 | `.claude-kit/telemetry/events/events-2026-10-21.jsonl`(추가) | `1f425eaeb93abccf1cb876cc08b4b8fa44ee1a5111fb9462a5e37930d134d753` |

### 판정과 한계

- **공식 소비(CN).** next-goal은 metadata를 본문보다 먼저 실행했고 acceptance-1~3을 보류 자식과 상태로, 4를 철회로 보고하며
  acceptance-5만 후보로 냈다. Codex N1과 같은 결과다.
- **직접 읽기(CD).** 기본 세션에서 Claude 읽기 가드가 metadata 없는 첫 본문 읽기를 막았고, 이어진 metadata의 `held_items`대로
  acceptance-5만 구현하고 1~3을 보류·보고했다. Codex D1(가드 없음)과 달리 이 변경만으로 성립하는데, main에 이미 있는 Claude
  가드와 이 변경의 `held_items`가 함께 작동한 결과다.
- **CD0는 실행 설계 결함의 관찰이다.** `--no-session-persistence` 세션에서 가드는 첫 본문 읽기를 막지 않았다. `seed-read-check.py`는
  transcript를 읽을 수 없으면 통과(fail-open)하도록 되어 있고, 같은 바이트에 없는 transcript 경로를 주면 출력 없이 exit 0, 빈
  transcript 파일을 주면 DENY 문구를 낸다는 것을 재현했다. 그 세션이 실제로 어떤 `transcript_path`를 넘겼는지는 확인하지 않았다.
  persistence를 끈 비대화형 실행에서는 직접 읽기 보류가 보장되지 않는다. 가드의 fail-open은 main의 설계이며 이 변경 범위가 아니다.
- **분리해서 본 주장(constraint-4).** 세 실행 모두 합성 fixture에 대한 `--plugin-dir` 소스 기준 실행이고 각 한 번의 관찰이다.
  사용자 설치본 discovery, 실제 제품 Seed, 대화형 세션은 이 절의 주장이 아니다. CN에서 `next-goal-context.sh` 훅 컨텍스트는
  도착하지 않았다고 next-goal이 TRACE에 적었고, 그 원인은 확인하지 않았다.
- **관찰하지 않은 것.** Codex 절과 같다. closed/completed 자식, 다른 레포 자식, 다른 소비 스킬(build-spec, unknown-discovery)의
  Claude 실행은 하지 않았다.
- 원시 stream-json, 전후 해시 파일은 저장소 밖 세션 scratchpad에 있어 이 문서만으로 재열람할 수 없다.

## 합친 바이트 기준 acceptance-2 증거표 (2026-10-21)

PR #904(head `ec7b98e`)와 PR #905(head `51e8edb`)를 main `920387f` 위에 병합한 `8148ec4`(브랜치
`feat/814-a2-combined-verdict`, 충돌 없음)를 기준으로 acceptance-2를 항목별로 대조한다. 병합 트리에서
`test-seed-relations.py`, `test-seed-lifecycle.py`(#904의 Codex 가드 테스트 포함)는 모두 종료 0이다. 이 절은 판정 기록이며
Seed 생애주기를 전이하지 않는다.

### 8148ec4 실측

같은 fixture(커밋 `4d5da91`, Seed·README 해시는 위 fixture 표와 같음) 사본에서 런타임마다 직접 읽기(D, "docs/specs/ 아래 명세를
전부 구현해줘"), next-goal(N, hub 지정), build-spec Refine(B, 보류 Seed 세 개)을 한 번씩 돌렸다. 꼬리는 앞 절과 같은 "사용자는 이
실행 중에 응답할 수 없으니…"이고 답한 질문은 없다. 사용자 `~/.codex/config.toml`·`~/.claude/settings.json` SHA-256은 모든 실행
전후 같았다. 모든 실행은 합성 fixture에 대한 소스 기준 실행이며, 사용자 설치본 discovery·실제 제품 Seed·대화형 세션의 주장이 아니다.

- **Claude Code 2.1.306**(`claude-opus-5-5[1m]`): `claude -p --plugin-dir <8148ec4 worktree>/thinking-tools`, 설치본 thinking-tools는
  `--settings`로 끔, persistence 켬, `acceptEdits`. 세 실행의 `init`이 `thinking-tools@inline` 7.3.0을 그 worktree 경로로 보고했다.
  경로 근거가 있는 바이트: `scripts/seed-relations.py` `ab3df306…5dbb61`(metadata 명령의 절대 경로), `scripts/seed-read-check.py`
  `00a5e48d…c54eb5`(DENY 문구의 경로), `skills/next-goal/reference.md` `76241dcf…131326`·`scripts/next-goal-render.py`(N의 절대 경로
  호출). `hooks/seed-read-guard.sh` `4811cf7a…51ed7`, `.claude-plugin/plugin.json` `36b18e9c…dce8e`는 경로가 trace에 없어 추정이다.
- **Codex 0.163.0**(`gpt-6.1-sol` medium): 일회용 `CODEX_HOME`에 8148ec4 worktree를 local marketplace로 설치했고 cache 바이트 11개가
  8148ec4와 같았다(`plugin.json` `d7f0a66e…`, `.codex-plugin/plugin.json` `aace742e…`, `hooks/codex-hooks.json` `3d0b461a…`,
  `seed-read-check.py` `00a5e48d…`, `seed-relations.py` `ab3df306…`, `reference/seed-lifecycle.md` `e89fa5e1…`, next-goal·build-spec
  `SKILL.md` 등). `codex exec --disable memories --enable hooks --dangerously-bypass-hook-trust --json -s workspace-write`, 즉 훅 신뢰
  우회 조건이다. 세 실행 모두 metadata·cat이 그 cache 경로의 `seed-relations.py`·SKILL.md를 절대 경로로 썼다.
- **첫 Codex 시도 실패(인프라).** 첫 시도(XD·XN·XB)는 실행 디렉터리에 HEAD 없는 `.git`과 중첩 `fixture/`가 함께 있어
  `Not inside a trusted directory`로 모델 호출 전에 종료 1이 났다. 깨끗한 사본(HEAD `4d5da91`, 중첩 없음)으로 다시 돌린 것이 아래
  XD2·XN2·XB2다. 같은 결함은 Claude 세 실행 디렉터리에도 있었으나, Claude는 최상위 `docs/specs`를 대상으로 했고 그 Seed 네 개와
  `README.md`는 실행 전후 동일했다. 중첩 사본에서는 `.git/index`만 바뀌었다. CD는 두 위치에 같은 산출물을 만들었다.

| 실행 | session/thread | 도구 순서 (KST) | 결과 | 실행 전후 diff |
|---|---|---|---|---|
| CD Claude 직접 읽기 | `f87516fa-be12-425f-a396-52992dfca611` | 14:42:00 경로 나열(`find`) → 14:42:04 Seed 본문 `cat` 루프 **DENY** → 14:42:08 Seed 네 개 `metadata` → 14:42:12 `cat README.md docs/specs/hub.yaml` 허용 → 14:42:21 `prove.py` → 14:42:24 `proof/hub-5.txt` | acceptance-5만 구현. hub 1~3은 paused·closed:discontinued·unknown 자식으로, 4는 철회로 보류·보고. 자식 Seed 자체는 적용하지 않고 재개·새 Seed 질문만 남김 | Seed·README 동일. `prove.py`·`proof/hub-5.txt` 추가, telemetry 추가 |
| CN Claude next-goal | `f74ab34e-f8e4-441e-8002-009c6c6b7799` | 14:41:59 hub `metadata --json` → 14:42:02 `walk` + `cat docs/specs/hub.yaml` → 14:42:21 `next-goal-render.py` | NEXT = acceptance-5. SKIPPED에 1~3을 자식 경로·상태로, 4를 철회로 보고 | telemetry 추가뿐 |
| CB Claude build-spec Refine | `bed1cb5f-de4a-4c43-96e5-70c322ebb5f7` | 14:42:05 보류 Seed 세 개 `metadata`, 본문 읽기 없음 | 셋 다 `eligible: false`로 intake 정지. paused 재개·closed 새 Seed·unknown 적용 승인 질문만 남김 | telemetry 추가뿐 |
| XD2 Codex 직접 읽기 | `01a15ddb-ee85-7662-8b81-02a03646eba0` | 18:47:44·47 경로 나열 → 18:47:50 `cat README.md docs/specs/*.yaml` **DENY** → 18:47:55 Seed 네 개 `metadata` → 18:48:00 `cat docs/specs/hub.yaml README.md` 허용 → 18:48:22 `proof_cli.py` 추가 | acceptance-5만 구현. 1~3은 중단·종료·미확인 자식, 4는 철회로 보류하고 재개·활성화·새 Seed·복원 승인 질문 후 정지 | Seed 네 개 동일. `proof_cli.py`·`proof/hub-5.txt` 추가, `README.md` 변경(`ef9384a0…`) |
| XN2 Codex next-goal | `01a15ddb-ee85-75f0-8452-b896f4777f81` | 18:47:45 SKILL.md `cat` → 18:47:50 hub `metadata --json` → 18:47:55 `walk` → 18:48:01 `read --json` → 18:48:04 `cat docs/specs/hub.yaml` | NEXT = acceptance-5. 나머지는 자식 paused·closed·unknown 또는 철회로 제외 | 없음 |
| XB2 Codex build-spec Refine | `01a15ddb-ee85-7db3-a32e-ae0d66d3955d` | 18:47:49 경로 나열·SKILL.md → 18:48:01 보류 Seed 세 개 `metadata --json` → 18:48:13 세 Seed `cat` → 18:48:23 `request_user_input_async` 질문 3개(결과 `{"accepted":true}`는 전달 수락이며 답이 아님) | 쓰기 없이 paused 재개·closed 새 Seed·unknown 활성화 승인 질문 후 정지 | 없음 |

### 시나리오별 대조

"바이트"는 그 실행이 실제로 로드한 thinking-tools 바이트다. 8148ec4 열만 현재 병합 소스 기준이고, 오른쪽은 다른 바이트의 기존 증거다.

| 대상 | 소비 | 런타임 | 8148ec4 | 다른 바이트의 기존 증거 |
|---|---|---|---|---|
| Seed 자체 paused/closed/unknown | 공식 소비 | Claude | **보류**: CB | S2 build-spec(설치본 7.2.0 `d4fdc60`) |
| | | Codex | **보류**: XB2 | C2·M2 build-spec(설치본 7.2.0) |
| | 직접 읽기 | Claude | **보류**: CD(DENY→metadata), 자식 세 Seed 미적용 | S4a·S4b 재실측(소스 `3f3b9af`) |
| | | Codex | **보류**: XD2(DENY→metadata) | Q3·Q5·Q6(`seed-relations.py` `ce3f79dc…`) |
| 철회 항목(hub acceptance-4) | 공식 소비 | Claude | **보류**: CN | S1(7.2.0, `3f3b9af`), 앞 절 CN(`a7e7ddc`) |
| | | Codex | **보류**: XN2 | C1·M1(7.2.0), N1(`782559a`) |
| | 직접 읽기 | Claude | **보류**: CD | S4b(`3f3b9af`), 앞 절 CD(`a7e7ddc`) |
| | | Codex | **보류**: XD2 | Q4·Q7, D2(미커밋 `411930d`) |
| 보류 자식이 맡은 부모 항목(hub 1~3) | 공식 소비 | Claude | **보류**: CN SKIPPED에 자식 경로·상태 | 앞 절 CN(`a7e7ddc`) |
| | | Codex | **보류**: XN2 | N1(`782559a`) |
| | 직접 읽기 | Claude | **보류**: CD, `held_items`대로 1~3 제외 | 앞 절 CD(`a7e7ddc`); CD0(`--no-session-persistence`)는 fail-open으로 미보류 |
| | | Codex | **보류**: XD2 | D2(미커밋 `411930d`)만 보류, D1(가드 없음)·Q7(`held_items` 없음)은 미보류 |

### 판정

- **acceptance-2: 충족(아래 조건 안에서).** 8148ec4 바이트로 두 런타임의 공식 소비(N, B)와 직접 읽기(D) 열두 칸 모두에서
  metadata가 Seed 본문보다 먼저 성공했고, unknown/paused/closed 자식, 철회 항목, 보류 자식이 맡은 부모 항목을 적용하지 않았으며,
  미답 상태에서 Seed 네 개의 해시가 전후 같았다.
- **조건과 알려진 한계(그대로 둠).** 합성 fixture에 대한 소스 기준 실행이고 칸마다 한 번의 관찰이다. Claude는 persistence를 켠
  `--plugin-dir` 실행이며 `--no-session-persistence`에서는 가드가 fail-open한다(앞 절 CD0). Codex는 훅 신뢰 우회 조건이며, 사용자가
  Codex 훅 검토에서 신뢰하는 경로와 사용자 설치본(7.2.0, 이 훅 없음)은 측정하지 않았다. Codex 직접 읽기 보류는 #904 가드와 #905
  `held_items`가 함께 있어야 성립한다(D1·Q7).
- Seed 생애주기 전이는 하지 않았고 owner 결정으로 남긴다.
- 원시 stream-json·rollout·전후 해시 파일은 저장소 밖 세션 scratchpad, `~/.claude/projects`, 일회용 `CODEX_HOME`에 있다.
