---
created: 2026-05-13
type: plan
status: active
revision: 3
consensus: approved (ralplan Architect+Critic, 2026-05-13)
workstream: claude-kit-unified-2026-Q2
tags: [unified-plan, claude-kit, dogfooding, telemetry, thought-chain, setup-wizard]
related:
  - docs/design/setup-wizard.md
  - docs/design/thought-chain-checkpoint-vault-integration.md
  - docs/discussions/20260512_telemetry-instrumentation/plan.md
  - vault://20_Projects/claude-kit/plan-2026-05-12-vault-bridge-enforcement-fixes.md
  - vault://20_Projects/claude-kit/plan-2026-05-12-thought-chain-checkpoint-vault-integration.md
revision_history:
  - rev1 2026-05-13 초안 작성
  - rev2 2026-05-13 Architect+Critic 1st round 피드백 통합 (Critical 6 + Non-critical 5 반영)
  - rev3 2026-05-13 Architect 2nd round 5개 정밀 fix (N1 recommended 필드 제거, N2 D5 preflight dump 모드, N3 drop 의미 정의, Principle #6 portability 정밀화, ≤3일→3-4일 정직 수치)
---

# claude-kit 통합 개발 계획 (2026-05-13)

## 0. RALPLAN-DR Summary

### Principles (6, revised)
1. **Dogfooding infrastructure first** — 측정 인프라(telemetry)를 먼저 깔되, 그 정당성은 "N=1 statistical baseline"이 아닌 **"schema/cost validation 1주"**다. (rev2: Architect steelman 반영해 wording 변경)
2. **Phase 1 plugin manifest 0 수정 — Phase 2 전환 시 명시적 재평가 필요** — `.claude/settings.local.json`만 사용. Phase 2 진입 시 manifest-based hook 등록(`${CLAUDE_PLUGIN_ROOT}`)으로 마이그레이션하면서 본 원칙은 "전환 게이트"에서 expiration. (rev2: Critic Critical #1 반영)
3. **vault writes는 main context slash command가 단일 책임** — v1.9.0 invariant 유지. Skill-dispatched slash command가 main context attribution을 유지하는지는 W1 D5 preflight test로 사전 검증.
4. **변경은 모두 가역적** — kill switch 4종 enumeration: `VAULT_BRIDGE_DISABLE` (v-b 전체), `CLAUDE_KIT_TELEMETRY` (telemetry opt-in/out), `VAULT_BRIDGE_WRITE_CONTRACT=off` (contract enforce), `CLAUDE_KIT_WELCOME_DISABLE` (welcome wizard, **NEW**). (rev2: Critic Critical #4 반영)
5. **Hub & Spoke 확장 구조** — 신설 플러그인(`claude-kit-welcome`)이 미래 플러그인을 자연 흡수.
6. **Phase 2 portability invariant** (**NEW, rev3 정밀화**) — Phase 1 동안 작성된 telemetry 핸들러는 절대 경로/유저 특화 환경변수를 hard-code하지 않음. Phase 1은 `${CLAUDE_PROJECT_ROOT:-$PWD}` 기반 relative path로 실행 (`.claude/settings.local.json`-registered hook은 `${CLAUDE_PLUGIN_ROOT}` 변수를 받지 못하므로 사용 불가). Phase 2 마이그레이션 시 1-line search-replace map(`$CLAUDE_PROJECT_ROOT/telemetry/` → `${CLAUDE_PLUGIN_ROOT}/scripts/`)으로 변환 가능하도록 경로 conv를 유지. (rev2: Architect §2 tension, rev3: Architect 2nd round N1 변경)

### Decision Drivers (Top 3)
1. **사용자의 N=1 dogfooding 사이클 가속** — schema/cost validation 후 Phase 2 결정 가능한 데이터 확보
2. **vault-bridge v1.9.0 안정화 + Skill-dispatched attribution 검증이 thought-chain의 vault 저장 전제** — 사전 검증 없이 enforce flip 시 R2 회귀
3. **신규 사용자 진입 경험은 외부 가치 — 내부 dogfooding과 직교** — setup-wizard는 data 의존성 0, 다만 marketplace.json 편집 충돌 가능

### Viable Options Considered (rev2: honest rebuttal 강화)
- **(A) 통합 빅뱅 PR** — 4개 워크 단일 PR. Rejected: 리뷰 불가능, 회귀 추적 불가, 사용자 결정 #3 위반.
- **(B) 사용자 가치 우선 (W3 → W4 → W1)** — Architect의 steelman: N=1 baseline은 통계적 의미 부족 + W3는 dead exit 해결로 가장 실용. **Honest rebuttal (rev3)**: 본 plan은 (B)의 절반을 수용 — telemetry의 정당화를 "statistical baseline"에서 "schema/cost validation"으로 약화하고, W3 머지가 W1 완료를 기다리지 않는 병렬 진행을 채택해 user-value 지연을 **3-4일**로 압축 (Alt B 절대 비교 시 D2-D3 vs 본 plan D5-D6 first reviewable W3 PR, rev2의 "≤3일" 수치는 정직하지 않아 rev3에서 3-4일로 정정). 다만 telemetry hook 8종이 thought-chain 작업 중 settle하면 schema 안정성 측정이 어려워지므로 telemetry MVP 머지(~2일)만 선행하고 thought-chain은 W1 D3부터 시작.
- **(C) 통합 telemetry MVP 선행(2일) + 그 후 W2/W3/W4 병렬** — Selected. 사용자 결정 #3과 일치하되, "telemetry 1주 baseline"이 아닌 "telemetry MVP 2일 + 즉시 병렬"로 압축.

### Pre-Mortem (Deliberate Mode — 5 시나리오, rev2: hard-failure 2개 추가)
1. **시나리오 X (soft): telemetry hook이 응답 지연 유발**
   - 시그널: 8개 hook 동시 등록으로 hook 실행 누적 budget이 p95 > 200ms
   - 완화: W1 첫 3일 dry-run에서 cumulative latency 측정. `report.py --metric=hook_latency --percentile=95` 결과 50ms 초과 시 hook 통합(단일 진입점) 또는 async fire-and-forget 전환
2. **시나리오 Y (soft): thought-chain 자동 vault 저장이 false positive noise 생성**
   - 시그널: `--auto-vault plan` 사용 시 `quality_score < 70`인 문서가 vault에 쌓임
   - 완화: 메타데이터 `quality_score` 필드 + Phase 3 인사이트 스킬에서 저품질 검출 → policy 조정
3. **시나리오 Z (soft): SessionStart 3-hook 텍스트 충돌**
   - 시그널: 한 응답 내 vault-bridge manifest 알림 + welcome 안내 + telemetry session_start 메시지 동시 노출
   - 완화: welcome은 grace 3 세션 + 200자 cap, vault-bridge manifest는 silent background, telemetry는 file-only invariant
4. **시나리오 W (hard, NEW): vault corruption — thought-chain auto-save와 OVM 동시 write race**
   - 시그널: 동일 `plan-YYYY-MM-DD-{topic}.md` 경로에 thought-chain `--auto-vault` 저장 + OVM `note` skill이 동시 invoke되어 한 쪽 write가 다른 쪽을 덮어씀
   - 완화: thought-chain의 vault save 호출 직전에 `Read`로 file existence 체크 + 충돌 시 `-v2`/`-v3` suffix. vault-bridge 의 `pre-write-guard`에 collision check 추가 검토 (W3 acceptance test 7번)
5. **시나리오 V (hard, NEW): telemetry jsonl unbounded growth**
   - 시그널: 일평균 1000+ 이벤트 × 4주 = 12만 줄. `events/` 디렉토리 디스크 사용량 폭증
   - 완화: telemetry W1 W4 작업에 rotation policy 명시 — 30일 후 gzip 압축, 90일 후 삭제. `cron` 없이 매주 `report.py` 실행 시 자동 회전 트리거

### Acceptance — Expanded Test Plan (rev2: concrete test cases)
- **Unit**:
  - W1: `validate-schema.py` jsonl 파싱 — 누락 필드 검출 케이스 5개 (필수 필드별)
  - W2: `test-pre-write-guard.py` (이미 정의됨, 6 케이스) + enforce 모드 회귀 케이스 2개 추가
  - W3: `thought_chain:` frontmatter 직렬화 단위 테스트 — `stages_run`/`deepen_counts`/`stopped_at` 5 케이스
  - W4: `welcome` skill 페이지 스캐너 — frontmatter 파싱 + appliesTo 매칭 4 케이스
- **Integration**:
  - 4개 SessionStart hook 동시 발화 — `bash -n` syntax + stdout-clean assertion (telemetry stdout 0 bytes 검사)
  - W3 5-option checkpoint 흐름 — 4 stage × 5 option = 20 분기 sample 4개
- **E2E**:
  - W1+W3 통합: thought-chain 풀 파이프라인 + vault 저장 + telemetry skill_invoke 6 이벤트 매칭률 100%
  - W2 contract preflight: `/save-plan-doc` Skill dispatch → PreToolUse payload `agent_name` field 채워지는지 1회 sampling
- **Observability**:
  - `events-YYYY-MM-DD.jsonl` 1주 누적 — schema_violations==0, hook_latency_p95 < 50ms, plugin_unknown_ratio < 5%

---

## 1. 배경

2026-05-12에 5개 계획 문서가 작성됐어요. 그 중 1개는 이미 코드에 반영되어 closed 상태고, 4개는 미구현 상태로 남았어요.

| # | 계획 문서 | 상태 | 잔여 작업 |
|---|----------|------|----------|
| P1 | `docs/design/setup-wizard.md` | draft | 전체 |
| P2 | `docs/design/thought-chain-checkpoint-vault-integration.md` | draft | 전체 |
| P3 | `docs/discussions/20260512_telemetry-instrumentation/plan.md` | draft | 전체 |
| P4 | `plan-2026-05-12-vault-bridge-enforcement-fixes.md` (vault) | **mostly closed** | Phase 2.B(enforce 기본값) + Phase 4(1주 측정) |
| P5 | `plan-2026-05-12-thought-chain-checkpoint-vault-integration.md` (vault) | draft (P2와 동일) | 전체 |

본 통합 계획은 P1, P2, P3과 P4의 잔여 작업을 단일 프로그램으로 묶고, 의존성을 명시한 실행 순서를 정의해요.

---

## 2. 워크스트림 정의

### W1. Telemetry Instrumentation (Phase 1 dogfooding)
**Source**: `docs/discussions/20260512_telemetry-instrumentation/plan.md`
**Priority**: P0 (다른 워크 효과 측정 + W3 attribution preflight 호스트)
**Owner**: claude-kit repo (plugin 비변경)
**예상 작업량**: MVP ~6h + 분석 도구 ~6h + 4주 dogfooding

**Scope**:
- `claude-kit/telemetry/` 디렉토리 (gitignored)
- `event-logger.sh` — opt-in gate + flock + stdout-clean + jq 파싱. **rev3**: 경로를 `${CLAUDE_PROJECT_ROOT:-$PWD}` 기반 relative path로 작성, Phase 2 마이그레이션을 위한 search-replace map은 telemetry README에 명시 (Principle #6 정밀화)
- `.claude/settings.local.json`에 8개 hook 등록
- `plugin-map.json` (3 → 4 plugin: welcome 포함)
- `report.py` / `sequence.py` / `validate-schema.py`
- **rev2 추가**: rotation policy — 30일 gzip, 90일 삭제. `report.py` 매 실행 시 자동 트리거
- **rev3 추가**: D5 preflight 지원용 env-var 게이트 `VAULT_BRIDGE_DUMP_PAYLOAD=1` — pre-write-guard.sh가 이 env를 감지하면 PreToolUse payload를 `telemetry/preflight-d5-payloads.jsonl`로 file-only dump 후 기존 enforcement 로직 진행. preflight 종료 후 env unset.

**Out of Scope**: 원격 전송, 다른 사용자 노출, Plugin manifest 수정

**D5 Preflight (rev3: Architect 2nd round N2 visibility gap 보정)**:
caller side에서 PreToolUse payload를 직접 inspect 불가하므로, **hook-side dump 모드**로 진행:
1. D1-D2에서 `pre-write-guard.sh`에 `VAULT_BRIDGE_DUMP_PAYLOAD=1` env-var 게이트 추가 (rev3 scope 추가). env 활성화 시 stdin payload를 `telemetry/preflight-d5-payloads.jsonl`에 file-only로 append + 기존 enforcement 로직 그대로 실행 (단일 진입점)
2. D5에 `VAULT_BRIDGE_WRITE_CONTRACT=enforce` + `VAULT_BRIDGE_DUMP_PAYLOAD=1` 동시 활성화
3. main context에서 `Skill("vault-bridge:save-plan-doc", "...")` 1회 호출 (fixture 입력)
4. `telemetry/preflight-d5-payloads.jsonl`에서 해당 호출의 payload entry 추출, `agent_name // subagent_type // agent.name // agent.type // attributionAgent` 5필드 검사
5. 모두 empty + Write 통과 → W2 enforce flip 안전. 하나라도 채워지거나 deny 발생 → pre-write-guard 검출 로직에 skill-frame 식별자 화이트리스트 추가 또는 W3 디자인 변경 후 W2 진행
6. preflight 종료 후 `--dump-payload` 옵션 off (telemetry dir gitignored이므로 fixture jsonl은 자동 격리)

이 테스트가 통과해야 W2가 enforce flip 가능. **W3는 attribution test 결과와 무관하게 진행 가능** (warn 모드 fallthrough가 보장하므로).

### W2. Vault-Bridge Enforcement 잔여 (Phase 2.B + Phase 4)
**Source**: `plan-2026-05-12-vault-bridge-enforcement-fixes.md` (vault, mostly closed)
**Priority**: P1 (W3와 독립, 다만 W1 D5 preflight 통과 필요)
**Owner**: vault-bridge plugin
**예상 작업량**: ~20분 코드 + 1주 측정

**Scope**:
- Phase 2.B: `pre-write-guard.sh`에서 `contract_mode` 기본값 `warn` → `enforce`로 전환
- vault-bridge minor 버전 범프 (v1.10.0)
- marketplace.json 동기화
- Phase 4: 머지 후 1주간 transcript 검색 + direct-access-log sampling으로 false positive 0건 확인

**전환 게이트**:
- (a) W1 D5 attribution preflight 통과 (rev2 추가)
- (b) Phase 2.A(warn) 머지 후 7일간 `CONTRACT WARNING` stderr 로그가 0건이거나 모두 vault-searcher 식별자 부재 케이스인 경우

### W3. thought-chain Checkpoint & Vault Integration
**Source**: `docs/design/thought-chain-checkpoint-vault-integration.md`
**Priority**: P0 (사용자 가치: dead exit 해결)
**Owner**: thinking-tools plugin
**예상 작업량**: ~8h
**Status**: ✅ Implementation complete (2026-05-16, commit `acd1fbc`). P0+P1 단일 커밋. ai-slop-cleaner + simplify pass 적용 완료. **Deviations**: (a) `save-plan-doc` 라우팅 → `save-session plan` argument override (in-memory 결과 전달 / `.omc/` 의존 회피), (b) `duration_seconds` 메타데이터 제거 (LLM 컨텍스트에 wall-clock 측정 수단 없음), (c) collision check (시나리오 W) **미구현** — Week 2 acceptance test 단계로 이월.

**Scope**:
- 3-option → 5-option checkpoint (deepen 추가)
- Pre-pipeline gate check + vault destination 질문
- Mid-stop polish guarantee
- `--autopilot` / `--auto-vault` 플래그
- `thought_chain:` frontmatter metadata
- thinking-tools minor 버전 범프
- **rev2 추가**: vault save 직전 collision check (시나리오 W 완화) — `Read` existence + `-v2` suffix fallback

**선행 조건 (rev2)**:
~~W2 (Phase 2.B 머지) 완료 후 시작 권장~~ — **삭제**. warn 모드 fallthrough로 W3는 W2와 독립. 다만 W3 첫 PR에 W1 D5 preflight 결과를 cite 필수.

### W4. Setup Wizard (claude-kit-welcome 신설 플러그인)
**Source**: `docs/design/setup-wizard.md`
**Priority**: P1 (외부 사용자 진입 경험)
**Owner**: 신설 `claude-kit-welcome` 플러그인
**예상 작업량**: ~10h

**Scope**:
- 4번째 플러그인 디렉토리 스캐폴드
- SessionStart hook + `/welcome` slash command + welcome skill
- `~/.claude/.claude-kit/state.json` + `progress.json`
- `pages/{plugin-id}.md` 5개 (hub + 3 plugins + closing)
- `marketplace.json`에 claude-kit-welcome 등록 — **rev3**: array 마지막에 append (텍스트 충돌 회피). "첫 위치/recommended" 의미는 **welcome plugin 자체의 SessionStart hook + `/welcome` slash command가 self-advertise**하므로 array 순서 불요. marketplace.json schema에 검증되지 않은 `recommended` 필드는 도입하지 않음 (Architect 2nd round N1). plugin.json의 `description` 첫 줄에 "Recommended first-stop for claude-kit newcomers" 표기로 discovery hint만 제공.
- CONTRIBUTING.md에 페이지 동봉 의무 섹션 추가
- **rev2 추가**: SessionStart hook 첫 줄 `[ "$CLAUDE_KIT_WELCOME_DISABLE" = "1" ] && exit 0` + welcome skill body 첫 줄 동일 가드. Principle #4 kill switch 완전화.
- **rev2 추가**: W4 PR에 `telemetry/plugin-map.json` 갱신 (welcome 4 entry: `welcome`, slash command 4개) 명시 — 자체 skill이 telemetry에서 `unknown`으로 분류되지 않게.

**P0 결정 (구현 시작 전)**:
- 플러그인 이름 확정: `claude-kit-welcome` (default) / `claude-kit-tour` / `claude-kit-onboarding`
- AskUserQuestion `maxItems: 4` 제약 검증

---

## 3. 의존성 그래프 (rev2: W2 ⟂ W3 분리)

```
                    ┌─────────────────────────────────┐
                    │  W1 Telemetry MVP (D1-D2)       │
                    │  - manifest 0 수정              │
                    │  - .claude/settings.local만     │
                    └──────────────┬──────────────────┘
                                   │ D5 attribution preflight
                                   ▼
                     ┌─────────────────────────────┐
                     │  W1 D5 Preflight Test       │
                     │  (Skill-dispatched Write    │
                     │   → enforce 안전 검증)      │
                     └──────┬──────────────┬───────┘
                            │              │
                  pass=true │              │ pass=true (W3는 fail에도 진행)
                            ▼              ▼
                  ┌───────────────────┐  ┌──────────────────────────┐
                  │  W2 Phase 2.B+4   │  │  W3 thought-chain        │
                  │  (enforce flip)   │  │  integration             │
                  └───────────────────┘  └──────────────────────────┘

                                          ┌──────────────────────────┐
                                          │  W4 setup-wizard         │
                                          │  (독립, marketplace.json │
                                          │   append-only 정책)      │
                                          └──────────────────────────┘
```

**Critical path**: W1 MVP(D1-D2) → W1 D5 preflight → (병렬: W2 enforce, W3, W4)
**Independent**: W4는 W1과도 병렬 가능 (data 의존성 0). 다만 marketplace.json 충돌 회피를 위해 W4가 마지막 머지 (rev2: Critic Critical #3 (b)안 보조).

---

## 4. Phase Plan

### Week 1 (telemetry MVP + preflight + 병렬 착수)
- **D1-D2**: W1 MVP (8 항목 체크리스트). Phase 2 portability 검증 (`${CLAUDE_PLUGIN_ROOT}` 호환 경로).
- **D3**: W3 코드 착수 (warn 모드 의존, W1 D5 결과 대기 불요) — ✅ 완료 (commit `acd1fbc`, 2026-05-16)
- **D3**: W4 P0 결정 (플러그인 이름, AskUserQuestion 제약 검증) + 스캐폴드 시작
- **D5**: **W1 D5 Preflight** (Critical) — Skill-dispatched Write에서 enforce 안전 확인
  - pass: W2 enforce flip 진행 가능 (D6 머지)
  - fail: pre-write-guard agent-id 검출 로직 보정 → 재테스트 → 통과 후 W2 진행
- **D6-D7**: W2 코드 변경 + 머지. W1 dry-run 누적

### Week 2 (수렴)
- W1 W2 작업 (report.py, validate-schema.py, plugin-specific meta 보강)
- W2 Phase 4 측정 시작 (1주 transcript/log 관찰)
- W3 acceptance test 6개 시나리오 + 시나리오 W collision check
- W4 코어 구현 (hooks/, commands/, skills/welcome/SKILL.md, pages/ 초안 3개)

### Week 3 (W4 머지 + 통합 검증)
- W1 W3 (sequence.py + 주간 리포트)
- W2 Phase 4 종료 + false positive 0건 확인
- W3 PR review 완료, 머지
- **W4 머지 (last)**: marketplace.json append-only (array 끝), plugin-map.json 갱신, plugin.json description에 "Recommended first-stop" 표기

### Week 4 (Phase Gate)
- W1 4주 Phase Gate 평가:
  - `validate-schema.py --since=7d` → 변경 0회 확인
  - `report.py --top=10` → 액션 가능 인사이트 ≥3개 식별
  - 데이터 공백 영역 1개 이상 — Phase 2 backlog 1줄 노트
- W2 측정 마감 + false positive 0건 archival
- 통합 retrospective: Architect+Critic 재호출로 Phase 2 진입 결정 (단일 사용자 자체 평가 bias 완화, rev2 Hidden Assumption #3 반영)

---

## 5. 충돌 해결 사항 (사용자 결정 반영)

### 결정 #1 — vault-bridge-enforcement 위치
**선택**: 잔여만 워크스트림으로 (Recommended)
**근거**: P4 plan은 사실상 closed. Phase 2.B + Phase 4만 W2로 추출.

### 결정 #2 — SessionStart hook 경합
**선택**: 독립 등록 + 병렬 실행 (Recommended)
**근거 (rev2: 약화)**: ~~Claude Code hook 시스템이 동일 matcher 다중 등록을 병렬 실행~~ — 이는 **검증되지 않은 가정**. §8 Open Questions로 이동.
**검증 조건**: W1 첫 주 dry-run에서 SessionStart 총 hook 시간 < 100ms 확인. 미달 시 fallback — 단일 coordinating handler로 통합.

### 결정 #3 — 작업 순서
**선택**: telemetry MVP(2일) 선행 + W2/W3/W4 즉시 병렬 (rev2: "1주 baseline"을 "2일 MVP + 즉시 병렬"로 압축, Alternative B 부분 수용)
**근거**: 측정 인프라 schema/cost validation 후 thought-chain/setup-wizard/vault-bridge 잔여를 병렬. user-value 지연 ≤3일.

---

## 6. Acceptance Criteria (rev2: 기계적 검증 가능 형태)

### 통합 계획 전체
- [ ] 4개 워크스트림 모두 W4 종료 시점에 머지 완료 또는 명시적 보류 (사유 기재)
- [ ] `events-YYYY-MM-DD.jsonl`가 working day마다 누적 — **drop 정의 (rev3)**: working day는 `git log --since=4w --format=%cd --date=short | sort -u`로 산정한 사용자 활동 일수. drop = working day인데도 해당 날짜 jsonl 부재 또는 user-prompt-submit 이벤트 0건. 휴무·휴식일은 drop이 아님. 4주 working day의 ≥90% 충족
- [ ] hook 비용 p95 < 50ms — `report.py --metric=hook_latency --percentile=95` 결과
- [ ] 통합 계획 문서 자체가 vault에 plan-doc으로 스냅샷됨 (snapshot_export/import gate 통과 시)

### 워크스트림별 (rev2: 메타 deferral 제거)
- **W1 Phase Gate (W4 D28)**:
  - `validate-schema.py --since=7d` 출력: schema 변경 0회
  - `report.py --top=10` 출력에서 액션 가능 인사이트 항목 ≥3개 식별 (인사이트 목록을 `.omc/research/telemetry-w4-insights.md`로 commit)
  - Phase 2 backlog 노트 ≥1개 (`docs/discussions/.../phase2-backlog.md`)
- **W2**:
  - enforce 머지 후 7일 transcript 검색에서 `CONTRACT WARNING` deny 0건
  - `direct-access-log` sampling 50건 중 vault-searcher 외부 정당한 read만 존재
- **W3** (구현: ✅ commit `acd1fbc` 2026-05-16, 검증: 대기):
  - 6개 manual test scenarios 모두 PASS (thought-chain-checkpoint-vault-integration.md §5.1)
  - 시나리오 W collision check: 동일 경로 동시 write fixture에서 `-v2` suffix 적용 확인 — 구현 미포함, Week 2 검증 단계에서 추가
  - vault 저장 문서 frontmatter에 `thought_chain:` block 검증 — `save-session` invocation context 자연어 의존 동작 manual 검증 필요
- **W4**:
  - 첫 SessionStart 안내 노출 + `/welcome` 실행 + state.json 정상 누적 (`pagesViewed` 길이 > 0)
  - `CLAUDE_KIT_WELCOME_DISABLE=1` 설정 시 SessionStart 안내 + `/welcome` 모두 silent exit
  - `telemetry/plugin-map.json`에 welcome 항목 4개 추가 commit

---

## 7. Risks & Mitigations (rev2: R2/R5 승격, R6 cumulative budget 명시)

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| R1 | telemetry hook이 LLM 컨텍스트 오염 | Low | High | event-logger.sh 첫 줄 opt-in gate + `>/dev/null 2>&1` 강제. Dry-run 1주차 stdout 청결성 검증 |
| **R2** (승격) | thought-chain Skill-dispatched save가 enforce contract 위반 | **High** | **High** | **W1 D5 preflight test로 사전 검증 — 통과 못 하면 pre-write-guard agent-id 검출 로직 보정 또는 W3 디자인 변경 후 W2 enforce flip** (rev2: Critical #5) |
| R3 | claude-kit-welcome SessionStart가 grace period 동안 노이즈 | Medium | Low | 3-세션 grace + 200자 cap + telemetry로 "skip" 비율 측정 + `CLAUDE_KIT_WELCOME_DISABLE` env |
| R4 | marketplace.json 동시 수정으로 PR 충돌 | Low | Low | **rev3**: W4가 array 끝에 append (텍스트 conflict 회피). "first position/recommended" 의미는 welcome plugin의 SessionStart hook + `/welcome` self-advertise로 처리, marketplace.json schema에 미검증 필드 도입 없음. W4가 last commit, W2/W3 version-bump 라인은 textually independent |
| **R5** (승격) | telemetry plugin-map.json이 welcome 추가 누락 → unknown 분류 | Medium | Low | W4 PR checklist에 plugin-map.json 갱신 명시. validate-schema 결과에서 `plugin_unknown_ratio > 5%` 알림 |
| R6 | hook 누적 latency가 budget 초과 | Medium | Medium | **rev2**: cumulative budget 모델링 — vault-bridge 5 hook (timeout 3-5s) + telemetry 8 hook + welcome 1 hook = 14 hook 총합. 각 hook actual latency 측정 + `report.py --hook-latency-distribution` 분포 확인. p95 > 50ms 미달 시 hook 통합 |
| **R7** (NEW) | settings.local.json이 claude-kit 재clone 시 손실 | Low | Low | telemetry README에 "재설치 후 hook 재등록 절차" 1줄 명시. (rev2 Hidden Assumption #2) |
| **R8** (NEW) | vault corruption — thought-chain auto-save vs OVM concurrent write | Low | High | W3 시나리오 W collision check (Read existence + `-v2` suffix) (rev2 Pre-mortem #4) |
| **R9** (NEW) | telemetry jsonl unbounded growth | Medium | Low | W1 W4 rotation policy: 30일 gzip, 90일 삭제 (rev2 Pre-mortem #5) |

---

## 8. ADR (Architecture Decision Record)

### Decision
2026-05-12에 도출된 4개 plan을 단일 4주 프로그램으로 묶고, **telemetry MVP(2일) → W1 D5 preflight → (병렬: enforcement 잔여, thought-chain, setup-wizard)** 순으로 실행한다.

### Drivers
1. 사용자의 N=1 dogfooding 사이클 가속이 본질
2. vault-bridge v1.9.0 안정화 + Skill-dispatched attribution 검증이 thought-chain의 vault 저장 전제
3. 신규 사용자 진입 경험과 내부 측정/도구는 직교

### Alternatives Considered
- (A) 통합 빅뱅 PR — Rejected
- (B) 사용자 가치 우선 (W3 → W4 → W1) — **Partial accept** (rev2): telemetry 정당화를 "statistical baseline"에서 "schema/cost validation"으로 약화. user-value 지연을 1주에서 ≤3일로 압축. 다만 telemetry MVP는 여전히 선행해 attribution preflight 인프라 확보

### Why Chosen
사용자 결정 #3 + Architect steelman 부분 수용. telemetry MVP(2일)만 선행하고 즉시 W2/W3/W4 병렬 진행으로 user-value 지연 최소화 + 측정 인프라 baseline 확보.

### Consequences
- Positive: 모든 후속 변경의 효과를 jsonl 시계열로 정량화. 4주 후 Phase 2 진입 데이터.
- **Negative (rev2: honest)**: N=1 데이터는 통계적 일반화 불가 — "본인 사용 일지"로만 가치. W3 머지가 telemetry MVP 머지 후 1-2일 지연 (user-value 손실 미세).

### Follow-ups (rev2 확장)
- W4 D28 Phase Gate 평가 후 Phase 2(사용자 옵트인 telemetry) 진입 결정
- **Principle #2 expiration 평가** — Phase 2 진입 시 manifest hook 등록으로 마이그레이션. Principle #6 portability invariant 검증
- Phase 3 인사이트 스킬 배치 결정
- AskUserQuestion `maxItems: 4` 제약 검증 후 multi-step selection 전략
- **W4 D28 retrospective**: Architect+Critic 재호출 (단일 사용자 자체 평가 bias 완화)
- **SessionStart parallel execution model 문서 확인**: Claude Code 공식 docs 또는 hook 시스템 소스에서 동일 matcher 다중 등록 동작 검증

---

## 9. Open Questions (rev2 신설)

1. **SessionStart 다중 hook 실행 모델** — 직렬/병렬/random order? 공식 문서 미확인. W1 dry-run에서 실측 + Context7 docs 확인 필요
2. **Skill-dispatched slash command의 PreToolUse attribution 필드 값** — W1 D5 preflight의 핵심 question. fail 시 pre-write-guard 보정 방향 결정
3. **`AskUserQuestion` maxItems=4 제약이 5+ 플러그인 환경에서 어떻게 작동하는지** — W4 dogfooding에서 검증

---

## 10. Hidden Assumptions (rev2 신설)

1. **hook timeout이 누적이 아닌 개별이라는 가정** — vault-bridge `plugin.json`이 hook별 3-5s timeout. 14 hook 동시 발화 시 cumulative wall-time budget 모델 불명확. R6 mitigation으로 측정 후 결정.
2. **`.claude/settings.local.json`이 repo reinstall에 survival** — 보장 없음. R7 mitigation으로 README 명시.
3. **W4 Phase Gate 단독 평가자(N=1) 자체 평가 bias** — Critic이 지적. mitigation: W4 D28에 Architect+Critic agent 재호출로 외부 시각 확보.

---

## 11. Related Sub-Plans

| Sub-plan | 위치 | 상태 | 본 계획에서의 위치 |
|---------|------|------|-------------------|
| Setup Wizard 설계 | `docs/design/setup-wizard.md` | draft | W4 (직접 실행) |
| thought-chain Checkpoint & Vault Integration | `docs/design/thought-chain-checkpoint-vault-integration.md` | draft | W3 (직접 실행) |
| thought-chain Checkpoint & Vault Integration (vault snapshot) | `vault://20_Projects/claude-kit/plan-2026-05-12-thought-chain-checkpoint-vault-integration.md` | snapshot | W3 (참조) |
| Claude-Kit Telemetry Phase 1 | `docs/discussions/20260512_telemetry-instrumentation/plan.md` | draft | W1 (직접 실행) |
| vault-bridge enforcement fixes | `vault://20_Projects/claude-kit/plan-2026-05-12-vault-bridge-enforcement-fixes.md` | **mostly closed** | W2 (잔여 Phase 2.B + 4만) |

---

## 12. Execution Log

### W1 D1-D2 (2026-05-15) — Telemetry MVP complete

코드/구성 항목 8개 전부 완료, 드라이런 1개 항목 진행 중 (Claude Code 재시작 + 누적).

원안 대비 의사결정 변경 3건 (상세는 `docs/discussions/20260512_telemetry-instrumentation/plan.md` §W1 구현 노트):
- **Lock 전략**: `flock` → lockless POSIX O_APPEND 채택. macOS 기본 toolchain에 `flock` 부재 + 라인 < PIPE_BUF로 atomicity 보장. `validate-schema.py`에 3500B size guard.
- **plugin-map 보강**: skill 19 entries + agent 4 entries (`vault-searcher`, `vault-knowledge-manager`, `vault-file-organizer`, `thinking-facilitator`). agent_spawn 이벤트도 동일 lookup 사용.
- **측정 범위 = Option A (project-local)**: hook은 `.claude/settings.local.json`에만 등록. claude-kit repo cwd에서 시작한 세션에서만 발동. discussion §2.1 "외부 plugin 비교군화" 의도와 부분 어긋나지만 plan 충실 + Phase 2 옵트인 UX와 분리 명확. global 이전은 W2~W4 사이 필요 시 hook 블록 복사 1분 작업.

**rev3 D5 preflight 지원** (`vault-bridge/hooks/pre-write-guard.sh`): `VAULT_BRIDGE_DUMP_PAYLOAD=1` 게이트 추가. 활성 시 payload를 `telemetry/preflight-d5-payloads.jsonl`에 append 후 기존 enforcement 로직 fall-through. 단일 진입점 유지.

검증 (전부 PASS):
- JSON valid (settings.local.json, plugin-map.json)
- Python compile (3 scripts)
- Bash syntax (event-logger.sh, pre-write-guard.sh)
- `validate-schema.py --self-test`: 10 expected errors detected
- functional smoke 8 event types + DUMP gate on/off
- 기존 vault-bridge 회귀 18 cases

**Next**: ~~사용자가 `~/.zshrc` 활성화 후 Claude Code 재시작 → ~3일 누적 → D5 preflight~~ → **D5 완료 (아래 참조)**. 다음: `CLAUDE_KIT_TELEMETRY=1` 활성화 후 Claude Code 재시작 → 이벤트 누적 시작.

### W1 D5 (2026-05-15) — D5 Preflight complete

**VERDICT: PASS** — W2 enforce flip 안전 확인. Write/Edit PreToolUse 페이로드에 5개 agent 식별 필드 모두 EMPTY.

**실행 방식 (원안 대비 3가지 조정)**:

1. **test vehicle 오류 발견**: 원안이 save-plan-doc을 fixture로 지정했으나, plan-doc-syncer.py가 Python 파일 I/O로 vault에 쓰기 때문에 Write 도구를 거치지 않아 pre-write-guard hook이 발동하지 않음. save-plan-doc은 Write 도구 attribution 테스트 차량으로 부적합. → **계획 문서 §2.W1 D5 항목 보정 필요** (W2 진행 전 save-session 등 Write 도구 사용 스킬로 재테스트 권장, 단 현재 PASS 결과로 W2 진행 가능).

2. **활성 hook 버전 불일치**: 설치된 vault-bridge 버전이 v1.8.3 캐시이고 DUMP_PAYLOAD 게이트는 dev v1.9.0에만 존재. `~/.claude/plugins/cache/.../1.8.3/hooks/pre-write-guard.sh`를 **wrapper 스크립트**로 교체 (DUMP_PAYLOAD=1 + WRITE_CONTRACT=enforce 하드코딩 후 dev v1.9.0 hook exec). 테스트 종료 후 1.8.3 원본으로 복원 완료.

3. **cross-session dump**: wrapper가 캐시된 플러그인 경로에 설치되어 있어 동시에 실행 중이던 PhototicketMaker 세션의 Write/Edit 15개도 같이 캡처됨. CLAUDE_PROJECT_ROOT 하드코딩으로 dump 경로가 claude-kit telemetry로 고정됐기 때문. → 향후 preflight wrapper는 세션 격리 방식(settings.local.json 임시 hook 등록)으로 개선 권장.

**5필드 검사 결과** (15개 페이로드 전체):

| 필드 | 값 |
|------|-----|
| `agent_name` | empty (15/15) |
| `subagent_type` | empty (15/15) |
| `agent.name` | empty (15/15) |
| `agent.type` | empty (15/15) |
| `attributionAgent` | empty (15/15) |

→ main context Write/Edit 도구 호출은 어떤 agent 식별자도 포함하지 않음. enforce 모드는 이 경우 deny를 내리지 않음.

**부가 결과**: save-plan-doc으로 `docs/plans/unified-dev-plan-2026-05-13.md` → vault `plan-2026-05-13-unified-dev-plan-2026-05-13-v2.md` 저장 완료 (commit 61ffd0c, L2 1회 우회).

**CLAUDE_KIT_TELEMETRY 상태**: `events/` 비어 있음 — `CLAUDE_KIT_TELEMETRY=1`이 `~/.zshrc`에 미설정 상태. Claude Code 재시작 후 이벤트 누적 시작 필요.

**Next**: W2 enforce flip 진행 가능 (D6). `CLAUDE_KIT_TELEMETRY=1` ~/.zshrc 추가 + Claude Code 재시작으로 dry-run 누적 시작.

---

### W1 D6 (2026-05-15)

**완료 항목**:

1. **CLAUDE_KIT_TELEMETRY 확인**: `~/.zshrc` line 140에 이미 `export CLAUDE_KIT_TELEMETRY=1` 존재. 별도 추가 불필요.
2. **첫 이벤트 파일 확인**: `telemetry/events/events-2026-05-15.jsonl` 생성됨 — telemetry 파이프라인 정상 동작 확인.
3. **W2 enforce flip**: `vault-bridge/hooks/pre-write-guard.sh:105` — `contract_mode` 기본값 `warn` → `enforce` 변경. `VAULT_BRIDGE_WRITE_CONTRACT` 미설정 시 서브에이전트 vault write를 deny로 처리.
4. **버전 범프 v1.9.0 → v1.10.0**: `vault-bridge/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` 동기 업데이트.
5. **회귀 테스트**: `python3 vault-bridge/scripts/test/test-discover.py` → `OK: all cases passed` (18 cases).
6. **훅 문법 검사**: `bash -n` 5개 훅 전부 OK.

**Next**: W1 완료. W2 머지 준비 — PR 생성 후 vault-bridge v1.10.0 릴리즈.

---

*작성: 2026-05-13 · 상태: rev2 (Architect+Critic 1st round 통합 반영) · 실행 로그 W1 D1-D2: 2026-05-15 · W1 D5: 2026-05-15 · W1 D6: 2026-05-15*
