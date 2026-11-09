# 활성 Seed 종료 실측 기록 (2026-11-09)

활성 Seed 여섯 개를 닫으려면 실제 세션 실행이 필요한 항목이 있었어요. 이 문서는 그 실측 결과를 저장소에 남긴 기록이에요. 각 Seed의 `lifecycle.evidence`가 이 문서의 절을 가리켜요.

## 공통 조건

- 런타임: Claude Code 2.1.319(headless `claude -p`, sonnet, 일부 opus), codex-cli 0.167.0
- 로드 방식: Claude는 `--plugin-dir <해당 바이트>/thinking-tools`로 로드했고, 측정 세션에서만 설치본 thinking-tools를 껐어요. Codex는 일회용 `CODEX_HOME`에 local marketplace로 설치했고, 훅 신뢰는 `--dangerously-bypass-hook-trust`로 해당 실행에만 우회했어요.
- 사용자 `~/.claude/settings.json`과 `~/.codex/config.toml`의 해시는 모든 라운드에서 전후가 같았어요. 사용자 설치본(7.5.0)은 측정하지 않았어요.
- fixture는 scratch git 저장소에 만든 합성 Seed예요. 칸마다 한 번씩 관찰했어요.
- 사용자 답이 필요한 세션은 세션 질문을 사용자에게 그대로 전달하고, 사용자 답을 받아 세션에 넘겼어요.

## 1. thinking-tools-persona-library

바이트는 `540809043da303ce804d5ec69f1ba8ac4388427d`이에요. `b476edc`와 비교하면 `thinking-tools/reference/personas.md`는 같고, expert-panel·adversarial-review SKILL.md는 언어 지시 한 줄만 달라요. 아래 STATE는 각 세션의 최종 result 이벤트에서 뽑았어요.

| run | 입력 | STATE |
|---|---|---|
| panel1 | `/thinking-tools:expert-panel` 풀 안 주제(로그인 토큰 인증 + 응답 캐시) | `Personas: [security-expert performance-expert] adhoc:1` |
| panel2 | 같은 주제, 별도 세션 | `Personas: [security-expert performance-expert] adhoc:1` |
| panel-off | 풀 밖 주제(강변 산책로 벚나무) | `Personas: [] adhoc:3` |
| adv | `/thinking-tools:adversarial-review` 풀 안 주제 | `Angle: security-expert` |

- acceptance-2: 두 세션의 Personas 집합과 순서가 같아요. `test-persona-selection.py`의 `select`로 미리 계산한 값과도 같아요.
- acceptance-3: 풀 밖 주제에서 `adhoc:3`이 표시됐어요.
- acceptance-5: adversarial-review의 Angle이 같은 주제에서 expert-panel이 고른 1순위 풀 ID와 같아요.

## 2. seed-relations-graph

### acceptance-2 (next-goal의 walk 호출과 후보화)

바이트는 `540809043da3`이에요. `b476edc`와 비교하면 `seed-relations.py`와 `next-goal-render.py`는 같고, next-goal SKILL.md는 언어 지시와 겹치는 문장 하나(pick change 금지, `reference.md:222`에 남음)만 달라요. 이 저장소의 Seed에는 relations 엣지가 없어서, 부모 1개(acceptance-1 충족, acceptance-2 미충족)와 자식 2개로 fixture를 만들었어요. `seed-relations.py check`는 세 파일 모두 OK였어요.

- `/thinking-tools:next-goal ... docs/specs/toy-child-a.yaml`을 실행했어요. 첫 두 도구 호출이 `seed-relations.py metadata --json`과 `walk`였고, Read는 0회였어요.
- 최종 출력은 `NEXT 형제 Seed child B의 farewell.txt 생성 (parent acceptance-2 충족)` / `FROM Seed toy-child-b`였고, 이미 충족된 child A는 `SKIPPED`였어요.

### acceptance-10 (Phase 0 관계 구분, Refine의 자식 비이동, 승인된 관계 변경의 양쪽 일치)

- Refine 세션(아래 3절 세션 2)에서 사용자가 자식 수정을 후속으로 남겼고, `toy-child-a`·`toy-child-b`의 sha256은 전후가 같았어요.
- 새 Seed 세션에서는 Phase 0이 관련 Seed 3개와 "독립 Seed"를 선택지로 제시했어요. 사용자가 `toy-parent`를 고르자 "새 자식(refines)", "depends_on/참조", "먼저 확인" 중에서 연결 방식을 다시 물었어요. 사용자는 `refines: [acceptance-2]`인 자식을 승인했어요.
- 결과는 `farewell-goodbye-validator.yaml`이에요. `parent: docs/specs/toy-parent.yaml`, `refines: [acceptance-2]`이고, 부모 `children`에 이 Seed가 추가됐어요. 네 파일 모두 `seed-relations.py check`가 OK였어요(부모는 `3 edge(s) consistent`).

## 3. thinking-tools-ud-bs-boundary

### acceptance-2 (UD→BS 왕복)

- 측정 바이트와 `b476edc`의 차이: unknown-discovery·build-spec SKILL.md의 언어 지시, 산출물 언어 예외, 바이트 상한 때문에 줄인 중복 문장, 그리고 build-spec STATE의 `skipped: reason` 칸이에요. 인터뷰 단계, 라운드 한도, Refine 절차는 같아요.
- 세션 1(UD Quick Discovery, `540809043da3`): `toy-parent.yaml`을 대상으로 질문 5개에 사용자가 답했어요. 리포트는 `docs/discovery/toy-parent/report.md`에 저장됐고 Seed는 바뀌지 않았어요. 세션은 BS Refine을 다음 세션으로 안내했어요.
- 세션 2(별도 세션, build-spec Refine): 위 리포트를 `<feedback>`으로 넣었고, 사용자 답 6라운드 뒤 게이트가 통과해 `refine_generation: 1`이 산출됐어요. `seed-lifecycle.py check --before`와 `seed-relations.py check`가 OK였어요. active Seed라서 `-v2` 새 파일이 아니라 제자리에서 개정됐어요.

### acceptance-3 (STATE에 skipped와 사유)

- `540809043da3`에서는 STATE에 `blindspot_pass: skipped`만 있고 사유가 없었어요. STATE 템플릿에 사유 칸이 없었기 때문이에요.
- 사유 칸과 두 건너뛰기 경로의 사유를 넣은 바이트(PR #932, main `0cdd0506c7ac9dd87985c95688031c8e8cd9e4be`와 같은 내용)로 UD 리포트를 받는 Refine을 다시 돌렸어요. 결과는 `blindspot_pass: skipped: covered by UD report`였어요.

## 4. seed-lifecycle-residual-validation

### acceptance-2 (metadata 선행과 보류 항목 미적용)

가드 바이트는 PR #931의 최종 head `73a1647b7ff618aadfcf0a293259e88aafcfdca1`이에요. main `b476edc72152d8a20cde8af70c30bb8cb0cda37f`의 가드 파일과 sha256이 같아요. `plugin.json`만 릴리스 버전 번호가 달라요.

| 파일 | sha256 앞 8자리 |
|---|---|
| `thinking-tools/hooks/codex-hooks.json` | 50eeac9c |
| `thinking-tools/hooks/seed-read-guard.sh` | 91529a5f |
| `thinking-tools/hooks/seed-read-output-guard.sh` | e84c58e8 |
| `thinking-tools/scripts/seed-read-check.py` | 26bfc84f |

next-goal과 build-spec 칸(CN, CB, XN, XB)의 소비자 바이트는 `73a1647`과 `b476edc` 사이에서 PR #932·#933의 문구 변경(언어 지시, STATE 사유 칸)만 달라요. `seed-relations.py`와 `next-goal-render.py`는 같아요.

fixture는 hub 1개(active, acceptance-4 철회)와 자식 3개로 구성했어요. 자식은 각각 paused, closed/discontinued, unknown 상태이고 hub acceptance-1~3을 refines해요.

| 칸 | 런타임 | 결과 |
|---|---|---|
| CDS 명령 치환 읽기 | Claude | 사전 통과, PostToolUse 차단 사유가 모델에 도달, metadata 실행 후 정지 |
| CD1·CD2 자연 프롬프트 | Claude | 사전 DENY, 이후 metadata |
| CDG `cat docs/specs/*` | Claude | 사전 DENY, 이후 metadata |
| CN next-goal | Claude | metadata → walk → render, `NEXT 없음` |
| CB build-spec Refine | Claude | metadata만 실행, 본문 읽기 없음 |
| XDS 명령 치환 읽기 | Codex | 도구 출력이 차단 사유로 대체됨, 이후 metadata |
| XD 자연 프롬프트 | Codex | 사전 DENY, 이후 metadata |
| XN next-goal | Codex | metadata → walk → read → render |
| XB build-spec Refine | Codex | metadata만 실행 |

10칸 모두 보류·철회 항목을 적용하지 않았고, fixture 해시는 전후가 같았어요. 명령 치환 읽기는 막지 못하고, 사후 단계가 적용만 막아요. Claude `--no-session-persistence`에서는 가드가 fail-open이에요.

### acceptance-4 (외부 session-close)

대상은 `~/.claude/skills/session-close`(local-harness `b372896abf5b`의 symlink, SKILL.md sha256 `6a099870cfb0…`)예요. 외부 소유라서 수정하지 않았어요.

| 분기 | 현재 실행 결과 | 구분 |
|---|---|---|
| 로드 사본 불명 → 계약 불가 | 세 run 모두 발동하지 않았어요. 사본이 여러 개여도 `installed_plugins.json`의 핀으로 사본을 확정했어요. | 미지원 한계 |
| cross-repo hold | 다른 레포 항목을 "링크만, 범위 밖"으로 보류하고 보고했어요(next-goal 렌더 경로). | 지원 |
| closed Seed 원본 보존 | closed Seed의 sha256이 세 run 모두 같았어요. | 지원 |
| 절대 경로 + `--before` | 승인된 전환 run에서 `seed-lifecycle.py check <절대 경로> --before /tmp/seed-prior.*` rc=0이었어요. | 지원 |
