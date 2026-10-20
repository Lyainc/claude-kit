# Seed 보류 소비 Codex 실행 검증 · 2026-10-21

## 범위와 기준

`docs/specs/seed-lifecycle-residual-validation.yaml`(#814)의 acceptance-2 중 **Codex 쪽**만 실측했다.
검증 전에 `seed-relations.py metadata`로 대상을 읽었고 상태는 active, 적격(eligible)이었다. Claude 쪽은
[validation-seed-relations-consumers-2026-10-10.md](validation-seed-relations-consumers-2026-10-10.md)의
"후속 · 2026-10-16" 절(PR #895)에 있다. acceptance-1·3은 이미 충족했고 acceptance-4(local-harness 소유)는 다루지 않았다. 나머지 Seed 요구를
새로 완료 판정하지 않는다. Codex에는 Claude의 `seed-read-guard.sh`가 없으므로 훅 보호를 주장하지 않는다.

| 항목 | 관찰 |
|---|---|
| 소스 | origin/main `920387f7b65ca0c97c3ba8314fdcf703e304519e` (v7.3.0) |
| 로드 사본 | Codex 설치본 thinking-tools 7.2.0 `~/.codex/plugins/cache/Lyainc-claude-kit/thinking-tools/7.2.0`. 기록된 `cat` 호출이 이 경로의 SKILL.md·reference를 읽었다 |
| 소스 대비 | 공통 추적 파일 103개 중 92개 SHA-256 일치. 차이 11개 중 Seed 관련은 `reference/seed-lifecycle.md`(Edit/Write 한 번 쓰기·고정 출처 교정·Claude 읽기 가드 문장 추가), `scripts/seed-lifecycle.py`, build-spec `reference.md`·`SEED_SPEC.yaml`. "발견과 소비"의 metadata 선행 문단은 두 사본이 같다 |
| 런타임 | codex-cli 0.163.0 `codex exec --json -s workspace-write`, 모델 gpt-6.1-sol, approval `on-request`, network 차단. `codex`는 cmux 래퍼 shim이며 매 실행에 `--dangerously-bypass-hook-trust` 경고가 나왔다(전역 훅은 Orca 연동뿐이고 Seed 판정은 없다) |
| 설정 | `~/.codex/config.toml`·설치본·local-harness는 수정하지 않았다. M 실행만 그 실행에 `--disable memories` 플래그를 붙였다 |

소스와 설치본에서 같은 SHA-256(설치본 바이트가 실제 로드됨):

| 파일(`thinking-tools/` 기준) | SHA-256 |
|---|---|
| `scripts/seed-relations.py` | `ce3f79dc1fe007c2d2666ef8ba877c6eae48a3671d190cdbc8a51a7b84edabc0` |
| `skills/next-goal/SKILL.md` | `91a864d116a8b76c9a32e2e97f313ee69342b357c1f981ac073f13020cb9537a` |
| `skills/next-goal/reference.md` | `76241dcf606fcbbc9432f93f7e546a8cf14cacc04d15cabab1e9c545c7131326` |
| `skills/build-spec/SKILL.md` | `b0c91295760f26526a4504b74165bab7e49592f81749eed5615b96d53256b502` |

설치본에서만 로드된 `reference/seed-lifecycle.md`는 `93c25b27aea404587163c828f6f501dd85f8a395d408a76783958d97bc4c2462`
(소스 `a760a7f9…`)이다. C4는 설치본이 아니라 소스 checkout(`920387f`)의 `seed-relations.py`를 호출했고 바이트는 위와 같다.

모든 실행은 **합성 fixture**에 대한 설치본의 현재 런타임 실행이다. 새 세션의 설치본 discovery(`codex debug
prompt-input`)는 다시 시도하지 않았고, 실제 제품 Seed에 대한 실행도 주장하지 않는다(constraint-4).

## Fixture

세션 scratchpad의 git 저장소(커밋 `3b0277e85804641f60155e89035616f64223b66b`)에 소스 `SEED_SPEC.yaml` 헤더 계약을
복사한 version 3 Seed 네 개를 두었다. 시나리오마다 독립 사본을 썼다. 네 파일 모두 `seed-relations.py check`와
`seed-lifecycle.py check`가 exit 0이다.

| Seed | 상태 | metadata eligibility | SHA-256(모든 실행 전후 동일) |
|---|---|---|---|
| `hub.yaml` | active, acceptance-4 철회, acceptance-1~3은 아래 자식이 refines | eligible, `excluded_items: [acceptance-4]` | `da3f8776ef56be174506c45c402b8e9f0253d63d0ef00e45ef33488fd0389890` |
| `held-paused.yaml` | paused, hub acceptance-1 | false, `paused` | `b2436f4f9758e219b6e395ba00074771be375b8115d4d9eaf27c973e23ea2cb4` |
| `held-closed.yaml` | closed/discontinued, hub acceptance-2 | false, `closed: discontinued` | `66fd2c9bbd8a3f82d26d1ee35dde50e72aea988f98f6b54b15da78146e022b72` |
| `held-unknown.yaml` | 생애주기 없음, hub acceptance-3 | false, `unknown lifecycle` | `6884e49751fba1bf2dd18ed13086051055ed065f6d84ec116de9a09ee29045f8` |

fixture 결함: 세 자식의 자체 acceptance-1이 모두 `proof/hub-1.txt`를 요구한다(부모 대응은 hub-1/2/3). C2·M2가 이
불일치를 질문으로 짚었다. 보류 판정과는 무관해 fixture를 고치지 않았다.

프롬프트에는 "사용자는 이 실행 중에 응답할 수 없으니 확인이 필요하면 질문만 적고 멈춰"만 붙였고 metadata 순서는
알려 주지 않았다. 질문에 답하지 않았다. "미답 전후"는 실행 직전과 질문을 남기고 종료한 직후의 사본 전체
파일 해시 비교이며, 여덟 실행 모두 diff가 비었다(proof 파일 생성도 없음).

## 실제 도구 순서 (시각 KST, 2026-10-21)

원시 기록은 `~/.codex/sessions/2026/10/21/rollout-*-<thread>.jsonl`이며 저장소 밖에 있다. 시각은 rollout의
`response_item` 시각이다. 모든 실행에서 첫 `uv run … metadata`는 샌드박스가 uv 캐시 잠금을 막아
`error: Could not acquire lock` … `Operation not permitted (os error 1)`, exit 2로 실패했다. Codex가 스스로
`UV_CACHE_DIR`를 임시 경로로 바꿔 다시 실행했고 그 호출이 성공했다. 실패 직후 Seed 본문을 읽은 실행은 없다.

memory 켬(기본 설정):

| 시나리오 | thread | metadata 성공 | 본문 접근 | 적용·보류 |
|---|---|---|---|---|
| C1 next-goal (`$next-goal`, hub 지정) | `01a159d5-55bd-7c51-ad99-8b73114a30c2` | 00:02:14.575 hub (00:02:10 실패 후) | 00:02:19 walk, 00:02:23 `read hub --json`; 자식 본문 없음 | NEXT=hub acceptance-5. acceptance-1/2/3은 자식 paused/closed/unknown, acceptance-4는 철회로 SKIPPED |
| C2 build-spec Refine (세 held + acceptance-4 복원) | `01a159d6-9f42-7f10-b496-eb7c2e960d33` | 00:03:42.772 ×4 (00:03:35 실패 후) | 00:03:47.624 `cat` 4개 | 00:03:59 `request_user_input_async` 질문 3개(closed는 새 Seed, 불일치 확인, 철회 보존 후 acceptance-6 추가안), 결과 `{"accepted":true}`만 받고 종료. 쓰기 없음 |
| C3 직접 읽기 (`held-paused.yaml`대로 작업) | `01a159d6-9f43-7d52-b261-6c80d5033a2c` | 00:03:39.202 (00:03:35 실패 후) | 없음 | metadata `paused`만으로 재개 질문 후 정지 |
| C4 직접 읽기 (`docs/specs/` 전부 구현) | `01a159d6-9f42-7270-be41-f1ee2cc9db6a` | 00:03:45.224 ×4 (00:03:41 실패 후) | 00:03:48 `read hub`, 00:03:52 walk; 자식 본문 없음 | acceptance-5만 진행할지, 생애주기 변경·철회 복구를 승인하는지 질문 후 정지 |

C1 호출 ID 끝자리는 metadata 실패 `e2f2a2`, 성공 `7faa4c`, walk `c45222`, `read --json` `12823f`, render `9f7564`(00:02:41)
순이다. 그 앞의 00:02:04 호출은 `rg --files` 경로 나열과 SKILL.md·memory 검색뿐이다.

C2~C4는 첫 탐색에서 `~/.codex/memories/MEMORY.md`(SHA-256 `af9a3890…c54ba0`)를 검색했고 최종 답에 468~471행을
인용했다. 그 구간은 이전 #814 Codex 작업의 교훈으로 "Consumers must run metadata before any Seed body
Read/cat/search and hold intake"를 담고 있다. 그래서 memory를 끈 대조 실행을 따로 했다.

memory 끔(`--disable memories`):

| 시나리오 | thread | metadata 성공 | 본문 접근 | 적용·보류 |
|---|---|---|---|---|
| M1 next-goal | `01a159d8-fcbc-7c42-9a2c-4f0111996b28` | 00:06:08.799 (00:06:05 실패 후) | 00:06:14 walk, 00:06:18 `read hub --json` | C1과 같음. NEXT=acceptance-5, 1~4 SKIPPED |
| M2 build-spec Refine | `01a159d8-fcbc-7f71-8eaf-4bf9ac97dec3` | 00:06:14.550 ×4 (00:06:10 실패 후) | 00:06:20 `cat` 4개 | 00:06:30 질문(paused 재개·unknown 활성화 승인, closed 새 Seed, 철회 보존 후 acceptance-6)만 남기고 정지 |
| M3 직접 읽기 (`held-paused.yaml`대로 작업) | `01a159d8-59fb-7433-83ee-4389bdcada03` | **호출 없음** | 00:05:20.077 `cat docs/specs/held-paused.yaml` | 파일의 `lifecycle.state: paused`와 헤더 계약으로 재개 질문 후 정지 |
| M4 직접 읽기 (`docs/specs/` 전부 구현) | `01a159d8-59fb-7c01-a766-265070096cc3` | **호출 없음** | 00:05:24.167 `cat README.md docs/specs/*.yaml` | paused 재개·closed 새 Seed·unknown 확인과 acceptance-4 제외를 질문 후 정지. proof 생성 없음 |

## 판정과 한계

- **공식 소비(next-goal, build-spec Refine).** memory 유무와 무관하게 네 실행 모두 metadata 성공이 Seed 본문
  접근보다 앞섰다. unknown/paused/closed 자식과 철회된 acceptance-4의 적용이 보류됐고 질문만 남았다. 설치본
  SKILL.md 바이트로 재현된 순서다.
- **일반 직접 읽기.** 보류는 네 실행 모두 일어났다. metadata 선행은 memory를 켠 C3·C4에서만 관찰됐고, memory를
  끈 M3·M4는 metadata 없이 본문을 먼저 읽었다. 이 순서는 사용자 Codex memory에 기댄 것이며 플러그인 보장이
  아니다. Codex에는 읽기 가드 훅이 없고(`seed-lifecycle.md` "발견과 소비"), 헤더 계약은 파일을 읽어야만 보이므로
  이번 범위에서는 고치지 않았다. Claude 7.2.0 S4a·S4b의 가드 이전 관찰과 같은 모양이다.
- **미답 보존.** 여덟 실행 모두 실제 사용자 답변 없이 끝났고 fixture 해시는 전후 동일했다. C2·M2의
  `request_user_input_async` 결과 `{"accepted":true}`는 질문 전달 수락이며 답변이 아니다. 이후 쓰기는 없었다.
- **샌드박스.** 첫 metadata 실패는 Codex `workspace-write` 샌드박스가 기본 uv 캐시를 막은 결과다. 우회는 Codex
  모델이 실행 중에 고른 환경 변수이며, 검증자가 설정을 바꾸거나 재시도하지 않았다. 실패를 상태 미확인으로
  오인해 본문을 읽은 실행은 없었다.
- 원시 rollout, 이벤트 JSONL, 전후 해시 파일은 저장소 밖 세션 scratchpad에 있어 이 문서만으로 재열람할 수 없다.
