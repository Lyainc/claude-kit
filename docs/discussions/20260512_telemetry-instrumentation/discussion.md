# 로컬 사용 로깅(Telemetry) 도입 논의

**일자**: 2026-05-12
**주제**: claude-kit 세 플러그인(thinking-tools / obsidian-vault-manager / vault-bridge)에 dogfooding용 로컬 사용 로깅 도입
**산출물**: 본 논의 transcript + [plan.md](./plan.md)

---

## 1. 배경 / 동기

- 사용자는 본인이 개발한 claude-kit 세 플러그인을 직접 dogfooding 중
- 사용 패턴을 데이터로 확인해 개발 방향에 반영하려 함
- 초기 표현은 "텔레메트리"였으나 실제 의도는 원격 전송 없는 **로컬 사용 로깅(local usage instrumentation)**임을 합의

---

## 2. 라운드 1 — 설계 공간 탐색

### 2.1 핵심 fork 4개 제시

1. **배포 모델**: plugin repo 내장(opt-in env) vs. 본인 머신 전용
2. **통합 범위**: plugin별 분리 vs. claude-kit 통합
3. **수집 메커니즘**: Claude Code Hook API 활용 (`SessionStart/End`, `UserPromptSubmit`, `PreToolUse/PostToolUse`, `Stop`)
4. **저장**: jsonl append-only, 날짜별 파일 회전

### 2.2 1차 추천 (이후 사용자 결정으로 수정됨)

- 배포: plugin 내장 + opt-in env → 사용자 결정 후 본인 머신 전용으로 좁힘
- 통합: claude-kit 통합 — plugin 필드로 구분, cross-plugin 시퀀스 분석 가능
- 저장: `~/.claude/telemetry/claude-kit/events-YYYY-MM-DD.jsonl` 제안 → 최종은 `claude-kit/telemetry/events/`로 이동

### 2.3 짚은 위험

- **Hook 비용**: PostToolUse 같은 고빈도 이벤트에 무거운 처리 넣으면 응답 지연
- **컨텍스트 오염**: hook stdout이 LLM 컨텍스트에 흘러들면 응답 이상해짐 → file-only write 강제
- **다른 사용자 영향**: opt-in 보장 약하면 신뢰 깨짐
- **N=1 의미적 한계**: 한 명 데이터는 "본인 사용 일지"로만 활용 가능, 일반화 금지

---

## 3. 라운드 2 — 1차 결정과 critic

### 3.1 사용자 결정

1. 본인만 사용 / gitignore 처리
2. 처음부터 3개 plugin 동시 적용
3. 이벤트 범위: **skill / agent / plugin이 호출한 command**만 — 모든 tool_use는 안 잡음

### 3.2 짚은 함정 — "gitignore만으로 끝"

- Plugin manifest(`plugin.json`, `hooks/*.json`)에 hook 등록을 commit하면 다른 사용자에게도 전달됨
- 핸들러 스크립트만 gitignore하면 → 다른 사용자는 "등록만 있고 스크립트 없음"으로 hook 에러
- **깨끗한 분리 합의**:
  - 핸들러/분석 도구 → `claude-kit/telemetry/` 전체 gitignored
  - Hook 등록 → `.claude/settings.local.json` (이미 gitignored)
  - Plugin manifest는 **0 수정**

### 3.3 이벤트 매핑 확정

| 이벤트 | Hook | 추출 |
|---|---|---|
| `skill_invoke` | `PreToolUse` (matcher=`Skill`) | `tool_input.skill` |
| `agent_spawn` | `PreToolUse` (matcher=`Agent`) | `tool_input.subagent_type` |
| `command_run` | `UserPromptSubmit` | 첫 토큰이 `/`로 시작 시 |

보조:
- `SessionStart` / `SessionEnd`: 세션 경계 마커
- `Stop`: 응답 단위 카운터
- `PostToolUse`: Skill/Agent 결과 매칭해 `duration_ms`, `outcome` 보강 (tool_use_id로 join)

### 3.4 Plugin 식별

- Qualified name namespace로 매핑: `vault-bridge:save-session` → `plugin=vault-bridge`
- Bare name(예: `save-session`)은 외부 lookup table(`telemetry/plugin-map.json`)로 보강

---

## 4. 라운드 3 — Phase 진화와 2차 결정

### 4.1 사용자 결정

1. Phase 1은 본인 dogfooding, "유의미"하면 → Phase 2(사용자 옵트인 로깅) + Phase 3(인사이트 스킬)
2. 현재 설계 방향 OK

### 4.2 Phase 정의

- **Phase 1 (now)**: 개인 dogfooding. 외부 노출 0. plugin repo 0 수정.
- **Phase 2**: 사용자 옵트인 로깅. `CLAUDE_KIT_TELEMETRY=1` 환경변수로만 동작. 데이터는 사용자 본인 머신에만(외부 전송 0). 핸들러를 plugin 또는 별도 plugin으로 이전.
- **Phase 3**: 사용자가 자기 jsonl을 읽어 자기 패턴을 보는 인사이트 스킬. plugin별로 분산할지 통합 스킬로 둘지는 Phase 2 데이터 보고 결정.

### 4.3 Phase 1에서 챙길 호환성 3개

1. **환경변수 게이트 처음부터** — `event-logger.sh` 첫 줄에서 `[ "$CLAUDE_KIT_TELEMETRY" = "1" ] || exit 0`. Phase 2 전환 시 코드 수정 0.
2. **Plugin-agnostic 핸들러** — lookup table은 외부 파일로 분리, plugin 추가/제거에 코드 변경 없음.
3. **풍부한 스키마** — 빈도뿐 아니라 `outcome` / `duration_ms` / `trigger` / `session_id` / `qualified_name`까지 전부 수집. 분석 시점에 의미를 발견하는 게 dogfooding의 본질.

### 4.4 Phase Gate 기준 (제안)

4주 dogfooding 후 다음 충족 시 Phase 2 진입:
- 스키마 변경 마지막 1주간 0회 (안정화)
- 액션 가능한 인사이트 3개 이상 발견 (예: "auto-trigger 한 번도 안 된 skill 발견 → description 손봐야겠다")
- 데이터 공백 영역 1개 이상 식별 (Phase 2에서 뭘 보강할지 알아야 함)

미충족 시 2주 연장 → 그래도 안 되면 telemetry 자체 가치 재평가(sunk cost 함정 회피).

---

## 5. 최종 합의 사항 요약

| 항목 | 결정 |
|---|---|
| 의도 | 로컬 사용 로깅 (원격 전송 0) |
| Phase 1 배포 | plugin manifest 0 수정, 외부 레이어로만 |
| 적용 범위 | 3개 plugin 동시 + 외부 plugin(OMC 등)도 같이 잡아 비교군화 |
| 이벤트 종류 | skill_invoke / agent_spawn / command_run + 보조 마커 |
| 저장 | `claude-kit/telemetry/events/events-YYYY-MM-DD.jsonl`, flock으로 race 방지 |
| Hook 등록 | `.claude/settings.local.json` |
| 호환성 | env gate + plugin-agnostic + 풍부한 스키마 — Phase 2/3 전환 비용 최소화 |
| Phase Gate | 4주 + 3개 기준 |

---

## 6. 미해결 / 후속 검토

- **skill_invoke가 `PreToolUse(Skill)`로 실제 잡히는지** 1주 드라이런으로 검증 필요 (일부 skill 우회 가능성)
- **UserPromptSubmit에서 slash command 식별**: 텍스트 멘션 `/cmd`와 실제 invocation 구분 — 첫 줄 + 첫 토큰만 매칭하는 룰로 시작
- **인사이트 스킬 배치**: plugin별 분산(`vault-bridge:insights`) vs. 통합(`claude-kit:insights`) — Phase 2 데이터 후 결정
- **데이터 회전 정책**: 30일 자동 회전? 영구 보관? 압축 정책? — Phase 1 마지막 주에 결정
