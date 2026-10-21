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
  discovery, memory를 켠 동작, 실제 제품 Seed, Claude Code 런타임은 이 기록의 주장이 아니다. D2는 신뢰를 우회한 훅 조건이다.
- **관찰하지 않은 것.** closed/completed 자식은 테스트에서만 확인했고 Codex 실행 fixture에는 없다. 다른 레포 자식, 다른 소비 스킬
  (build-spec, unknown-discovery)의 실행은 하지 않았다.
- 원시 rollout, 이벤트 JSONL, 전후 해시 파일은 저장소 밖 세션 scratchpad에 있어 이 문서만으로 재열람할 수 없다.
