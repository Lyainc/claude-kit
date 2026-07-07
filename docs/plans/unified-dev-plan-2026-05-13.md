---
created: 2026-05-13
type: plan
status: closed
workstream: claude-kit-unified-2026-Q2
tags: [unified-plan, claude-kit, dogfooding, telemetry, thought-chain, setup-wizard]
---

# claude-kit 통합 개발 계획 (2026-05-13) — ✅ W1~W3 완료 / W4 → #117

> **상태 (2026-06-03 갱신)**: 2026-05-12 5개 plan 중 4개를 묶은 4주 프로그램. W1(telemetry)·W2(vault-bridge enforce)·W3(thought-chain checkpoint) 완료. W4(setup-wizard)는 미착수 backlog로 **#117** 이관. 계획·예측 스캐폴딩(pre-mortem, 확장 테스트플랜, open questions, hidden assumptions)은 해소되어 제거하고, 결정 기록(ADR)·실행 로그만 보존.

## 워크스트림 최종 현황

| WS | 내용 | 상태 |
|---|---|---|
| W1 | Telemetry Instrumentation (Phase 1 dogfooding) | ✅ 완료 — `event-logger.sh` + 8 hook + report/sequence/validate-schema |
| W2 | vault-bridge enforcement 잔여 (Phase 2.B + Phase 4) | ✅ enforce flip + 버전 범프 완료 (D5 preflight PASS). Phase 4 1주 측정은 dogfooding으로 흡수 |
| W3 | thought-chain Checkpoint & Vault Integration | ✅ 완료 (`acd1fbc`, 5-option checkpoint) — 단 이후 재설계 **#105**에서 dissolve 대상이 됨. **(2026-07-07 확인: #105 CLOSED, thought-chain 스킬 자체가 완전히 해체됨 — 이 W3 "완료"는 이제 지어졌다가 통째로 없어진 기능의 기록일 뿐, 살아있는 코드가 아니에요.)** |
| W4 | Setup Wizard (claude-kit-welcome 신설) | ⏸ 미착수 → **#117 backlog**. 06-02 재설계 미언급, 재평가 전 보류. **(2026-07-07 확인: #117 CLOSED — 재평가 결과 마법사는 안 짓기로 하고 훨씬 작은 `session-start-welcome.sh` 힌트만 shipped, `docs/design/setup-wizard.md` SUPERSEDED 배너 참조.)** |

## ADR (요지)

telemetry MVP(2일) → W1 D5 attribution preflight → (병렬: W2 enforce / W3 / W4) 순으로 실행.
- **경계**: Phase 1은 plugin manifest 0 수정(`.claude/settings.local.json`만), Phase 2 전환 시 `${CLAUDE_PLUGIN_ROOT}` manifest hook으로 마이그레이션(재평가 게이트).
- **invariant**: vault writes는 main context slash command 단일 책임 (vault-bridge v1.9.0).
- **portability**: telemetry 핸들러는 `${CLAUDE_PROJECT_ROOT:-$PWD}` relative path — Phase 2 시 1-line search-replace로 변환.
- **honest**: N=1 데이터는 통계적 일반화 불가 — "본인 사용 일지"로만 가치.
- **kill switch 4종**: `VAULT_BRIDGE_DISABLE`, `CLAUDE_KIT_TELEMETRY`, `VAULT_BRIDGE_WRITE_CONTRACT=off`, `CLAUDE_KIT_WELCOME_DISABLE`.

## 실행 로그 (보존 — 비자명 결정 기록)

### W1 D1-D2 (2026-05-15) — Telemetry MVP
- **Lock 전략**: `flock` → lockless POSIX O_APPEND (macOS 기본 toolchain `flock` 부재 + 라인 < PIPE_BUF atomicity). `validate-schema.py` 3500B size guard.
- **plugin-map**: skill 19 + agent 4 entries.
- **측정 범위 = project-local**: hook은 `.claude/settings.local.json`에만 등록 (claude-kit cwd 세션 한정). global 이전은 hook 블록 복사 1분.
- D5 preflight 지원: `pre-write-guard.sh`에 `VAULT_BRIDGE_DUMP_PAYLOAD=1` file-only dump 게이트 추가(단일 진입점).

### W1 D5 (2026-05-15) — Attribution Preflight: PASS
Write/Edit PreToolUse 페이로드 15개 전체에서 5개 agent 식별 필드(`agent_name`/`subagent_type`/`agent.name`/`agent.type`/`attributionAgent`) 모두 EMPTY → main context write는 agent 식별자 없음 → enforce 모드가 deny 안 함 → **W2 enforce flip 안전**.
- **비자명 발견 ①**: `save-plan-doc`은 Python 파일 I/O라 Write 도구 미경유 → pre-write-guard hook 미발동 → attribution 테스트 차량 부적합.
- **비자명 발견 ②**: preflight wrapper가 캐시된 플러그인 경로에 설치돼 동시 실행 중이던 타 세션(PhototicketMaker) Write 15개도 함께 캡처됨 → 향후 preflight는 세션 격리(settings.local.json 임시 hook 등록) 권장.

### W1 D6 (2026-05-15) — W2 enforce flip
`pre-write-guard.sh` `contract_mode` 기본값 `warn`→`enforce`. vault-bridge v1.9.0→v1.10.0 + marketplace 동기화. 회귀 18 cases PASS, hook 문법 5개 OK.

---
*W1~W3 완료 + W4 #117 이관으로 본 통합계획 종료 (2026-06-03). 후속 = 레이어 재설계 Epic #108. 원본 rev1-3 계획 상세(pre-mortem/acceptance test plan/risk table/open questions)는 갱신 시 해소되어 제거.*
