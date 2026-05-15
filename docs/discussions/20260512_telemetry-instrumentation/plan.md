# Claude-Kit Telemetry — 개발 계획 (Phase 1)

**일자**: 2026-05-12
**범위**: claude-kit 세 plugin(thinking-tools / obsidian-vault-manager / vault-bridge) dogfooding용 로컬 사용 로깅 도입
**선행 문서**: [discussion.md](./discussion.md)
**Phase**: 1 (개인 dogfooding) — Phase 2/3 진화 경로는 §10 참고

---

## 1. 목표 (Goals)

- 사용자(개발자)가 본인 claude-kit 플러그인 사용 패턴을 jsonl 이벤트 로그로 수집해 dogfooding 인사이트 추출
- 외부 영향 0 — plugin manifest 0 수정, 다른 사용자에게 흔적 0
- Phase 2/3 전환 비용 최소화 (env gate, plugin-agnostic, 풍부한 스키마)

## 2. 비목표 (Non-Goals)

- 원격 전송
- 다른 사용자 데이터 수집
- 일반 사용자에게 노출
- 모든 Tool 호출(Read/Edit/Bash 등) 세밀 로깅 — skill/agent/command만
- Web 대시보드, 시각화 UI — Phase 1은 CLI 스크립트로 충분

---

## 3. 아키텍처 개요

```
┌─────────────────────────────────────────────┐
│  Claude Code 세션 (사용자 머신)               │
│                                              │
│  Hook 발동 (PreToolUse:Skill/Agent,          │
│             UserPromptSubmit, Stop,          │
│             PostToolUse, SessionStart/End)   │
│                  │                           │
│                  ▼                           │
│  event-logger.sh   ← .claude/settings.local  │
│       │            │  .json 에서 호출         │
│       ▼                                      │
│  events-YYYY-MM-DD.jsonl  (flock append)     │
└─────────────────────────────────────────────┘
                  │
                  ▼  (오프라인 분석)
        report.py / sequence.py
                  │
                  ▼
            사용자 인사이트
```

핵심: hook 핸들러는 **빠른 shell append만 수행**, 분석은 후처리. LLM 호출 0회.

---

## 4. 디렉토리 / 파일 매니페스트

```
claude-kit/
├── .gitignore                              # /telemetry/ 한 줄 추가
├── telemetry/                              # 디렉토리 전체 gitignored
│   ├── event-logger.sh                     # 단일 hook handler (Phase 1 핵심)
│   ├── plugin-map.json                     # bare-name → plugin 매핑 lookup
│   ├── events/
│   │   ├── events-2026-05-13.jsonl         # 날짜별 append
│   │   ├── events-2026-05-14.jsonl
│   │   └── …
│   ├── scripts/
│   │   ├── report.py                       # summary / weekly trend
│   │   ├── sequence.py                     # (W3) 시퀀스 패턴 추출
│   │   └── validate-schema.py              # jsonl 스키마 검증
│   └── README.md                           # 본인용 운영 메모 (env 설정/조회 명령)
└── .claude/
    └── settings.local.json                 # hook 등록 (이미 gitignored)
```

Plugin 디렉토리(`thinking-tools/`, `obsidian-vault-manager/`, `vault-bridge/`)는 **수정 0**.

---

## 5. 이벤트 스키마 (v1)

**한 줄 jsonl**:

```json
{
  "ts": "2026-05-13T14:32:11Z",
  "session_id": "abc123",
  "cwd": "/Users/Lyainc/dev/prj/claude-kit",
  "plugin": "vault-bridge",
  "event": "skill_invoke",
  "name": "save-session",
  "qualified_name": "vault-bridge:save-session",
  "trigger": "explicit",
  "outcome": "success",
  "duration_ms": 1234,
  "tool_use_id": "toolu_01ABC",
  "meta": {}
}
```

### 필드 정의

| 필드 | 타입 | 값 |
|---|---|---|
| `ts` | string (ISO8601 UTC) | 이벤트 발생 시각 |
| `session_id` | string | Claude Code hook payload에서 추출 |
| `cwd` | string | 작업 디렉토리 (어떤 repo에서 발동했는지) |
| `plugin` | string | `vault-bridge` / `thinking-tools` / `obsidian-vault-manager` / `omc` / `unknown` |
| `event` | enum | `skill_invoke` / `agent_spawn` / `command_run` / `session_start` / `session_end` / `stop` |
| `name` | string | skill/agent/command 이름 (namespace 제거 후) |
| `qualified_name` | string | `plugin:name` 풀 네임 (있는 경우) |
| `trigger` | enum | `explicit` (slash command) / `auto` (system trigger) / `keyword` (description match) — 알 수 있는 한 |
| `outcome` | enum | `started` / `success` / `blocked` / `error` (PostToolUse 시점에 보강) |
| `duration_ms` | int | PostToolUse 시점에 보강 |
| `tool_use_id` | string | PreToolUse↔PostToolUse 매칭 키 |
| `meta` | object | plugin-specific 추가 필드 (W2에서 채움) |

### 이벤트 매핑

| 이벤트 | Hook | matcher | 추출 방법 |
|---|---|---|---|
| `skill_invoke` (started) | `PreToolUse` | `Skill` | `tool_input.skill` |
| `skill_invoke` (success/error) | `PostToolUse` | `Skill` | `tool_use_id`로 update |
| `agent_spawn` (started) | `PreToolUse` | `Agent` | `tool_input.subagent_type`, `tool_input.description` |
| `agent_spawn` (success/error) | `PostToolUse` | `Agent` | `tool_use_id`로 update |
| `command_run` | `UserPromptSubmit` | — | prompt 첫 줄 첫 토큰이 `/`로 시작 시 |
| `session_start` | `SessionStart` | — | session_id만 |
| `session_end` | `SessionEnd` | — | session_id만 |
| `stop` | `Stop` | — | 응답 종료 카운터 |

PostToolUse의 update 방식: Phase 1에서는 단순화해 **두 줄로 append**(started/finished). join은 분석 시점에 `tool_use_id`로.

---

## 6. 컴포넌트 상세

### 6.1 `event-logger.sh`

**역할**: hook stdin JSON 받아 스키마 조합 후 jsonl append.

**인터페이스**:
```bash
./event-logger.sh <event_type> < hook_payload.json
# event_type: skill_invoke_start, skill_invoke_end, agent_spawn_start,
#             agent_spawn_end, command_run, session_start, session_end, stop
```

**필수 안전장치**:
- 첫 줄 `[ "$CLAUDE_KIT_TELEMETRY" = "1" ] || exit 0` — opt-in gate
- 모든 출력 file-only (`>/dev/null 2>&1` 또는 jsonl로만) — **stdout 절대 금지**
- `flock`으로 동시 세션 append race 방지
- `jq` 실패 시 silent exit 0 (LLM 컨텍스트 보호 최우선)
- qualified_name 파싱은 `:` split, namespace 없으면 `plugin-map.json` lookup

**스켈레톤**:
```bash
#!/usr/bin/env bash
[ "$CLAUDE_KIT_TELEMETRY" = "1" ] || exit 0
set -e

EVENT_TYPE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/events"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/events-$(date -u +%Y-%m-%d).jsonl"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

PAYLOAD=$(cat) || exit 0
# … jq로 필드 추출 + plugin 매핑 …

{
  flock -x 200
  echo "$EVENT_JSON" >> "$LOG_FILE"
} 200>"$LOG_FILE.lock" 2>/dev/null

exit 0
```

### 6.2 `.claude/settings.local.json`

**Hook 등록 (8종)**:

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Skill",  "hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh skill_invoke_start"}]},
      {"matcher": "Agent",  "hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh agent_spawn_start"}]}
    ],
    "PostToolUse": [
      {"matcher": "Skill",  "hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh skill_invoke_end"}]},
      {"matcher": "Agent",  "hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh agent_spawn_end"}]}
    ],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh command_run"}]}],
    "Stop":            [{"hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh stop"}]}],
    "SessionStart":    [{"hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh session_start"}]}],
    "SessionEnd":      [{"hooks": [{"type": "command", "command": "/Users/Lyainc/dev/prj/claude-kit/telemetry/event-logger.sh session_end"}]}]
  }
}
```

### 6.3 `report.py`

**옵션**:
```
--since=7d|24h|all
--plugin=vault-bridge|thinking-tools|obsidian-vault-manager|omc|all
--event=skill_invoke|agent_spawn|command_run|all
--top=N
--format=table|json
```

**출력**:
- Top N events (count + plugin breakdown)
- Outcome 분포 (success / blocked / error 비율)
- Latency p50 / p95 (duration_ms 있는 이벤트만)
- Weekly trend (날짜별 count line chart — ascii)

### 6.4 `sequence.py` (W3 이후)

- 동일 세션 내 이벤트 sequence 추출
- 빈도 높은 2-gram, 3-gram (예: `unknown-discovery → expert-panel → doc-concretize`)
- plugin-cross 시퀀스 강조 (thinking-tools → vault-bridge 등)

### 6.5 `plugin-map.json`

```json
{
  "save-session": "vault-bridge",
  "vault-link": "vault-bridge",
  "vault-manifest-refresh": "vault-bridge",
  "vault-commit": "vault-bridge",
  "save-plan-doc": "vault-bridge",
  "doc-concretize": "thinking-tools",
  "doc-polish": "thinking-tools",
  "unknown-discovery": "thinking-tools",
  "expert-panel": "thinking-tools",
  "adversarial-review": "thinking-tools",
  "diverse-sampling": "thinking-tools",
  "thought-chain": "thinking-tools",
  "capture": "obsidian-vault-manager",
  "note": "obsidian-vault-manager",
  "project": "obsidian-vault-manager",
  "inbox-review": "obsidian-vault-manager",
  "context": "obsidian-vault-manager",
  "archive": "obsidian-vault-manager",
  "vault-audit": "obsidian-vault-manager"
}
```

(누락 시 `unknown` plugin으로 분류 — W1 후 갱신)

### 6.6 `validate-schema.py`

- 최근 N일치 jsonl 읽고 필수 필드 누락/타입 오류 카운트
- 스키마 변경 검출 (Phase Gate 판단 자료)

---

## 7. 작업 단위 (체크리스트)

### W1 — MVP (목표 1주)

- [x] 루트 `.gitignore`에 `telemetry/events/` + `telemetry/preflight-d5-payloads.jsonl` 추가 (2026-05-15)
- [x] `telemetry/` 디렉토리 + `events/`, `scripts/` 하위 생성 (2026-05-15)
- [x] `telemetry/event-logger.sh` 작성 — opt-in gate / **lockless POSIX O_APPEND** / stdout-clean / jq 파싱 (2026-05-15)
- [x] `telemetry/plugin-map.json` 초기 버전 (skill + agent 23 entries) (2026-05-15)
- [x] `.claude/settings.local.json`에 hook 8종 등록 (2026-05-15)
- [x] `telemetry/README.md` — 본인용 운영 메모 (env 설정, 확인 명령, 로그 위치, R7 복구 절차) (2026-05-15)
- [x] **rev3 add**: `vault-bridge/hooks/pre-write-guard.sh` `VAULT_BRIDGE_DUMP_PAYLOAD=1` 게이트 (D5 preflight 지원) (2026-05-15)
- [x] 환경변수 `CLAUDE_KIT_TELEMETRY=1` 셸 프로파일(`~/.zshrc`)에 추가 (2026-05-15)
- [ ] **드라이런 시작** — Claude Code 재시작 후 평소 작업 중 jsonl 쌓이는지 확인 (진행 중)

### W1 구현 노트 (2026-05-15)

원안에서 의도적으로 변경/보강한 사항 3건:

1. **Lock 전략 — flock 제거, lockless POSIX O_APPEND 채택** (§6.1 변경)
   - 원안: `flock -x 200`. macOS Darwin 기본 toolchain에는 `flock`(util-linux) 부재 — hard dependency 추가하지 않기로.
   - 근거: POSIX `O_APPEND` + 단일 `write()` syscall은 `PIPE_BUF`(4096B macOS/Linux) 이하 페이로드에 대해 atomic offset+write 보장. 본 schema 라인은 ~400-600B로 한참 안쪽. N=1 dogfooding에서 multi-session 동시 발화 자체가 드문 데다, 발생해도 atomicity 보장.
   - Guard: `validate-schema.py`가 라인 사이즈 > 3500B 시 경고 — W2에서 `meta` 필드 확장 시 임계 접근 가능. 임계 넘으면 mkdir-based atomic lock 도입 재검토.

2. **plugin-map.json — agent name 추가 보강** (§6.5 변경)
   - 원안: skill bare-name lookup만. agent_spawn 이벤트의 `subagent_type`이 bare name이면 매칭 실패 → 모두 `unknown` 분류.
   - 변경: `vault-searcher`, `vault-knowledge-manager`, `vault-file-organizer`, `thinking-facilitator` 4개 agent 추가. 총 23 entries (skill 19 + agent 4).

3. **측정 범위 결정 — Option A (project-local)** (§6.2 명시화)
   - hook 등록 위치: `.claude/settings.local.json` (원안 §6.2 그대로).
   - 함의: telemetry는 **claude-kit repo cwd에서 시작한 Claude Code 세션**에서만 발동. 다른 repo 작업은 측정 대상 아님.
   - discussion.md §2.1의 "외부 plugin(OMC 등)도 같이 잡아 비교군화" 의도와 부분 어긋나지만, plan 충실 + 데이터 범위 명확 + Phase 2 의사결정 시 사용자별 옵트인 UX와 깔끔히 분리 가능한 장점. Option B(`~/.claude/settings.json` global)로의 이전은 hook 블록 복사 1분 작업이라 W2~W4 사이 cross-context 비교 필요해지면 옮기기로.

검증 결과 (2026-05-15):
- `python3 -m json.tool` settings.local.json + plugin-map.json: OK
- `python3 -m py_compile` 3 scripts: OK
- `bash -n` event-logger.sh + pre-write-guard.sh: OK
- `validate-schema.py --self-test`: PASS (10 expected errors detected on bad line)
- functional smoke (8 event types, plugin-map lookup, DUMP gate on/off): PASS
- 기존 vault-bridge 회귀 (`test-discover.py`): OK (18 cases pass)

### W2 — 분석 도구 + 보강

- [ ] `scripts/report.py` 작성 (table/json 출력)
- [ ] `scripts/validate-schema.py` 작성
- [ ] Plugin-specific `meta` 필드 보강:
  - vault-bridge: vault-searcher mode (1/2/3/4), Write Role 거부 플래그, manifest staleness 히트
  - obsidian-vault-manager: capture/note 분기, MOC append 여부, vault-audit DoD 위반 종류
  - thinking-tools: thought-chain pipeline 단계 여부
- [ ] `unknown` plugin 분류된 이벤트 보고 `plugin-map.json` 갱신

### W3 — 시퀀스 분석

- [ ] `scripts/sequence.py` 작성 (2-gram, 3-gram)
- [ ] Cross-plugin 시퀀스 추출
- [ ] 주간 리포트 생성 자동화 (스크립트 단발 실행, cron 없이)

### W4 — Phase Gate 평가

- [ ] Validate-schema 결과 정리 (마지막 1주 변경 0회 확인)
- [ ] 액션 가능한 인사이트 3개 이상 추출 가능한지 확인
- [ ] 데이터 공백 영역 식별
- [ ] Phase 2 진입 / Phase 1 연장 / 폐기 판단

---

## 8. 검증 계획

| 항목 | 방법 | 기준 |
|---|---|---|
| Opt-in 게이트 | `CLAUDE_KIT_TELEMETRY` unset 상태에서 hook 발동 → events/ 빈 상태 확인 | 파일 생성 0 |
| Stdout 청결성 | hook 발동 후 응답에 핸들러 출력 흘러들지 않음 | 응답 정상, 컨텍스트 깨끗 |
| Race 안전성 | 다중 세션 동시 작업 → jsonl 줄 깨짐 검사 (`jq .` 전체 통과) | 파싱 오류 0 |
| 스키마 일관성 | `validate-schema.py` 통과 | 필수 필드 누락 0 |
| 이벤트 누락 | 알려진 invocation(예: 직접 `/save-session`) 후 해당 이벤트 jsonl에 존재 | 매칭률 100% |
| Plugin 매핑 | `unknown` plugin 비율 | < 5% (claude-kit 외 plugin 제외) |
| Hook 비용 | hook 실행 시간 측정 (시간 기록) | p95 < 50ms |

---

## 9. 위험 / 완화

| 위험 | 완화 |
|---|---|
| Hook stdout이 LLM 컨텍스트 오염 | 모든 출력 file-only, jq 실패도 silent exit 0 |
| 동시 세션 jsonl 깨짐 | flock 사용, lock 파일 별도 |
| Skill 호출이 `PreToolUse(Skill)`로 안 잡힘 | W1 드라이런에서 검증, 미캡처 시 다른 추출 경로 모색 |
| `UserPromptSubmit`에서 텍스트 멘션 `/cmd` 오탐 | 첫 줄 + 첫 토큰만 매칭, 더 정교한 규칙은 W2 |
| 데이터 의미 과대해석 (N=1) | 본인 사용 일지 expectation 명시, 일반화 금지 |
| Plugin manifest 수정 유혹 | 작업 단위에서 명시적으로 금지, PR review 시 차단 |
| Sunk cost로 Phase 2 무리 진행 | §10 Phase Gate 기준 엄격 적용, 미충족 시 폐기 옵션 유지 |

---

## 10. Phase 진화 경로

### Phase 1 → 2 진입 조건 (4주 후 평가)

모두 충족 시 Phase 2 진입:
- [ ] 스키마 변경 마지막 1주간 0회 (안정화)
- [ ] 액션 가능한 인사이트 3개 이상 발견
- [ ] 데이터 공백 영역 1개 이상 식별 (Phase 2에서 뭘 보강할지)

미충족 시 2주 연장 → 그래도 안 되면 telemetry 자체 가치 재평가.

### Phase 2 — 사용자 옵트인 로깅

- 핸들러를 plugin 또는 별도 plugin으로 이전 (manifest에 hook 등록)
- `CLAUDE_KIT_TELEMETRY=1` 환경변수로만 동작 (default OFF)
- 데이터는 사용자 본인 머신에만 — 외부 전송 0
- 문서 / 프라이버시 정책 / opt-in UX 추가

### Phase 3 — 인사이트 스킬

- 사용자가 자기 jsonl 읽어 자기 패턴 보는 스킬
- 예시 인사이트:
  - "이번 주 안 쓴 skill 목록" (auto-trigger 효과 측정)
  - "doc-concretize → doc-polish 후속 호출 비율" (pipeline 사용률)
  - "Write Role enforce에서 막힌 패턴" (안전망 효과)
- 배치(plugin별 vs. 통합)는 Phase 2 데이터 후 결정

---

## 11. 즉시 다음 액션

W1 첫 단계는 다음 4개를 한 번에 묶어 진행 가능:

1. 루트 `.gitignore`에 `/telemetry/` 한 줄 추가
2. `claude-kit/telemetry/` 디렉토리 골격 + `event-logger.sh` v0
3. `telemetry/plugin-map.json` 초기 버전
4. `.claude/settings.local.json`에 hook 8종 등록

작업 시작 명령은 사용자 결정 후 진행.
