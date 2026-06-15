---
goal_id: G7
title: retro 스킬 + telemetry meta 확장
issues: [123, 121]
wave: 5
depends_on: [G6]
recommended_model: sonnet
status: gated
work_type: feature-full
created: 2026-06-03
---

# G7 — retro 스킬 + telemetry meta 확장

> **⛔ SUPERSEDED (#217 + 현재값 재배치).** 이 계획은 [`G14`](G14-self-hosting-bootstrap.md)가
> "현재값으로 대체"했고, 실제로 배포됐어요 — retro(#123) → `feedback-loop/skills/retro/`,
> telemetry meta(#121) → `feedback-loop/scripts/`. #217이 ⑤ 하네스를 dev-harness(개발 거버넌스)/feedback-loop(자기개선)로
> 분리했고, retro·telemetry는 자기개선이라 **feedback-loop**로 안착해서 본문 플러그인 이름을 현재값으로 갱신했어요
> (단 "## 포함 이슈"의 `feat(workflow-harness):`는 #123 이슈 제목 인용이라 보존). 현재 실재 상태는 G14 배너 참조.

## 배경 / 목적

D4 결정(2026-06-03)에서 회고는 단순 노트가 아니라 **E8 임계승격 + 3갈래 출력 + dedup + 회고예산** 4가지를 묶은 구조화 루프로 정의됐어요. 현재 OVM `audit` 스킬은 E8(`promotion_candidate`)을 찾아서 보고만 하고, 승격 실행과 후처리는 사용자 수동이에요. `retro` 스킬이 이 gap을 메우는 ⑤실행 레이어의 핵심 workflow예요.

두 이슈를 같이 묶은 이유는 응집도 때문이에요. `retro`가 dedup 이력 확인에 telemetry meta 데이터를 사용하거든요 — `meta.duration_ms`와 토큰 카운트가 채워져야 비용·효율 분석과 세션 간 dedup이 의미 있어져요. D8 결정("D8에서 동시 설계 권장")이 이 묶음의 직접 근거예요.

두 작업 모두 기존 leaf 플러그인(OVM, vault-bridge)을 **읽기만** 하고 수정하지 않아요. 단방향 의존(harness→leaf) 경계를 지키는 첫 번째 실제 구현 케이스가 돼요.

## 포함 이슈

- #121: enhance(telemetry): expand meta fields with token count and duration_ms — `telemetry/event-logger.sh`의 `meta: {}` 하드코딩을 실제 `duration_ms` / 토큰 카운트로 채우기. `validate-schema.py` self-test 케이스 추가, README 갱신, `report.py` latency 섹션 활성화.
- #123: feat(workflow-harness): add retro skill — E8 promotion + 3-branch output + dedup + budget — `feedback-loop/skills/retro/SKILL.md` 작성. 4단계 파이프라인(COLLECT→PROMOTE→OUTPUT→BUDGET), E8 임계 재확인 + user-confirmed 승격 게이트, 3갈래 출력(액션/기억/규칙), dedup, 회고예산.

## 완료 조건 (Definition of Done)

### #121 — telemetry meta 확장

- [ ] `telemetry/event-logger.sh` §7의 `meta: {}` 하드코딩 제거 — `skill_invoke_end` / `agent_spawn_end` 이벤트에 `duration_ms` (값 없으면 null), `input_tokens` / `output_tokens` / `cache_read_tokens` (값 없으면 키 생략) 채워짐
- [ ] `stop` 이벤트에 `turn_input_tokens` / `turn_output_tokens` 추출 (Stop hook payload에 usage 있는 경우만)
- [ ] 빈 값 폴백: jq `// empty` 패턴 사용, 없으면 키 자체 생략 (스키마 오염 방지)
- [ ] 라인 크기 3500B 미만 유지 — `validate-schema.py --self-test` 통과로 확인
- [ ] `telemetry/scripts/validate-schema.py` self-test에 `meta.duration_ms` 포함 케이스 추가 (good line에 `"meta": {"duration_ms": 42}` 포함)
- [ ] `telemetry/README.md` Event schema (v1) 코드블록에 `meta` 예시 필드 추가, `duration_ms` 행 설명 갱신
- [ ] `telemetry/scripts/report.py` latency 분석 섹션 활성화 — `meta.duration_ms` 있는 이벤트 대상 p50/p95 계산
- [ ] `bash -n telemetry/event-logger.sh` 통과 (구문 오류 없음)
- [ ] `python3 telemetry/scripts/validate-schema.py --self-test` → `OK: self-test passed`

### #123 — retro 스킬

- [ ] `feedback-loop/skills/retro/SKILL.md` 작성 완료 (4단계 파이프라인 명시: COLLECT → PROMOTE → OUTPUT → BUDGET)
- [ ] `feedback-loop/.claude-plugin/plugin.json` 작성 (신설 또는 기존 G6 PR과 통합)
- [ ] `.claude-plugin/marketplace.json` 에 feedback-loop 항목 등록 또는 버전 범프
- [ ] **COLLECT 단계**: OVM audit E8 findings를 입력으로 받는 계약 명시 (audit 스킬 호출 또는 findings JSON 직접 수신)
- [ ] **PROMOTE 단계**: refs_in / access_count 임계값 재확인 로직, user-confirmed 승격 게이트 (AskUserQuestion), `status: evergreen` frontmatter-only 패치. silent auto-fix 금지 명문화
- [ ] **OUTPUT 단계**: 3갈래 출력 opt-in 명세
  - 액션 갈래: 반복 패턴 → gh CLI (`gh issue create`) 또는 `/issue` slash command (기본 활성)
  - 기억 갈래: 세션 인사이트 → vault capture via `/save-session` (prompt 기반 opt-in)
  - 규칙 갈래: 검증된 패턴 → `.claude/*.local.md` 직접 편집 (prompt 기반 opt-in)
  - vault 쓰기는 vault-bridge Write Role Contract 준수 (user-initiated slash command 경유)
- [ ] **BUDGET 단계**: `RETRO_BUDGET` env var (기본값 10) 읽기, 초과 시 P0→P1→P2 우선순위 순 절사, 잔여 건수 보고
- [ ] **dedup**: 동일 session 내 중복 항목 제거 (동일 파일·동일 error_type 쌍 기준), telemetry meta로 이전 retro 처리 이력 확인 후 스킵
- [ ] **telemetry meta 확장**: `meta` 필드에 `{retro_items_processed, items_promoted, items_deduped, budget_used}` 포함
- [ ] JSON 유효성: `python3 -m json.tool feedback-loop/.claude-plugin/plugin.json > /dev/null`
- [ ] JSON 유효성: `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null`

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| telemetry `duration_ms` 소스 | A) `tool_response.duration_ms` / B) hook payload 타임스탬프 직접 계산 | A, null 폴백 | hook payload 구조에 duration 필드가 있으면 그대로 읽는 게 단순. 없으면 null — 키 생략 패턴 일관 적용 |
| meta 키 생략 vs null | A) 없으면 null 명시 / B) 키 자체 생략 | B (토큰·캐시), A (duration_ms) | duration_ms는 null 명시가 "측정 시도했으나 없음"을 표현. 토큰 카운트는 이벤트마다 의미가 달라 있을 때만 기록이 노이즈 최소화 |
| retro COLLECT 입력 계약 | A) audit 스킬 자동 호출 / B) findings JSON 파일 경로 인수 / C) 직전 audit 결과를 메모리에서 수신 | B (파일 경로) | 단방향 경계(harness→OVM) 준수. audit 호출 자동화는 결합도 높음. 파일 인수가 테스트 가능하고 명시적 |
| E8 임계 재확인 기준 | A) manifest의 `promotion_candidate: true` 신뢰 / B) refs_in ≥ 3 OR access_count ≥ 5 를 retro에서 재계산 | A + 재확인 표시 | manifest는 generate-manifest.py가 이미 임계 계산한 결과. retro는 값 표시 후 사용자 확인만 받으면 충분 — 이중 계산은 오히려 불일치 위험 |
| feedback-loop 플러그인 신설 타이밍 | A) G7에서 신설 / B) G6(#122)에서 신설 후 G7에 retro 추가 | B (G6 의존 게이트) | #122가 plugin.json 골격을 만드는 이슈. G7은 그 위에 retro 스킬을 얹음. G6 미완료면 G7 착수 불가 — **게이트 조건**: G6(#122) PR 머지 완료 |
| 기억 갈래 기본 활성화 | A) 기억·규칙 갈래 기본 OFF, prompt 후 opt-in / B) 3갈래 전부 기본 ON | A | vault-bridge Write Role Contract — vault 쓰기는 사용자가 명시적으로 시작해야 함. 기본 OFF + prompt가 계약 준수 |
| report.py latency 섹션 | A) #121 범위 내 활성화 / B) 데이터 충분 후 별도 이슈 | A | #121 이슈 자체가 "이 이슈 완료 후 활성화 가능"으로 명시. 구현은 단순 p50/p95 계산 — 범위 내 |

## 슬라이스 순서

1. **S1 telemetry meta 채우기** → 바인딩: executor (sonnet) | 대상 파일: `telemetry/event-logger.sh` | 산출: `skill_invoke_end` / `agent_spawn_end` / `stop` 이벤트의 `meta` 필드에 duration_ms + 토큰 카운트 채워짐, jq `// empty` 폴백 적용 | 검증: `bash -n telemetry/event-logger.sh` 통과, 라인 크기 3500B 미만

2. **S2 validate-schema self-test 확장** → 바인딩: executor (sonnet) | 대상 파일: `telemetry/scripts/validate-schema.py` | 산출: `run_self_test()` 내 good line에 `"meta": {"duration_ms": 42, "input_tokens": 100}` 포함 케이스 추가, `--strict` 모드에서 meta 비어있는 `skill_invoke_end` 경고 옵션 검토 | 검증: `python3 telemetry/scripts/validate-schema.py --self-test` → `OK: self-test passed`

3. **S3 telemetry README + report.py 갱신** → 바인딩: executor (sonnet) | 대상 파일: `telemetry/README.md`, `telemetry/scripts/report.py` | 산출: README Event schema 코드블록 `meta` 예시 필드 추가·갱신, report.py latency p50/p95 섹션 활성화 (`meta.duration_ms` 있는 이벤트 필터) | 검증: `python3 telemetry/scripts/report.py --since=7d` 오류 없이 실행

4. **S4 feedback-loop 플러그인 기반** → 바인딩: executor (sonnet) | 대상 파일: `feedback-loop/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | 산출: plugin.json 작성(name, version, keywords에 retro 포함), marketplace.json 등록 또는 기존 항목 버전 범프 | 검증: `python3 -m json.tool feedback-loop/.claude-plugin/plugin.json > /dev/null`, `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` | **전제**: G6(#122) 완료 또는 이 슬라이스에서 신설 — 둘 다 미완이면 이 슬라이스에서 골격 생성

5. **S5 retro SKILL.md — COLLECT + PROMOTE 단계** → 바인딩: executor (sonnet) | 대상 파일: `feedback-loop/skills/retro/SKILL.md` | 산출: COLLECT 단계(findings JSON 파일 경로 인수 계약, E8 항목 파싱), PROMOTE 단계(refs_in/access_count 표시 + AskUserQuestion 승격 게이트 + frontmatter-only Edit, silent auto-fix 금지 명문화) | 검증: SKILL.md frontmatter 유효성(`name`, `description`, `allowed-tools` 필수 키 존재), PROMOTE 단계에 AskUserQuestion 사용 명시 확인

6. **S6 retro SKILL.md — OUTPUT + BUDGET 단계** → 바인딩: executor (sonnet) | 대상 파일: `feedback-loop/skills/retro/SKILL.md` (S5 계속) | 산출: OUTPUT 단계(3갈래 opt-in 명세, vault 쓰기는 user-initiated slash command 경유 명시), BUDGET 단계(`RETRO_BUDGET` env var 읽기, P0→P1→P2 절사, 잔여 보고), dedup 로직(동일 session 파일·error_type 쌍 기준), telemetry meta 확장(`retro_items_processed` 등) | 검증: SKILL.md 4단계 파이프라인 헤더 전부 존재 확인, `RETRO_BUDGET` 참조 확인

7. **S7 code-review** → 바인딩: code-reviewer (sonnet) | 대상 파일: S1~S6 변경 전체 | 산출: 리뷰 리포트 — vault Write Role Contract 위반 여부, silent auto-fix 금지 준수, PIPE_BUF 임계 위반, jq 오류 삼킴 누락 여부 집중 검토 | 검증: CRITICAL 0건

## E2E 자가검증

```bash
# 1. telemetry event-logger 구문 검사
bash -n telemetry/event-logger.sh

# 2. validate-schema self-test (meta.duration_ms 포함 케이스 통과 확인)
python3 telemetry/scripts/validate-schema.py --self-test
# 기대: OK: self-test passed

# 3. report.py 실행 오류 없음 확인
python3 telemetry/scripts/report.py --since=7d --format=json > /dev/null && echo "report.py OK"

# 4. E8 promotion-finding 회귀 (retro 입력 계약 기반 데이터 소스 검증)
python3 obsidian-vault-manager/scripts/test/test-promotion-finding.py
# 기대: OK: all 8 cases passed

# 5. OVM audit E2E (retro 입력으로 사용하는 E8 findings 생성 검증)
rm -rf /tmp/ovm-fixture-retro-g7
OVM_FIXTURE_DIR=/tmp/ovm-fixture-retro-g7 \
  bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-retro-g7 --dod
# 기대: dod.seeded_detected 에 E8:2 포함

# 6. feedback-loop plugin.json 유효성
#    전제: G6(#122) 완료 또는 S4에서 디렉토리 생성됨. clean repo(미생성)에서는 SKIP — 그냥 실행하면 FileNotFoundError로 실패해요.
if [ -f feedback-loop/.claude-plugin/plugin.json ]; then
  python3 -m json.tool feedback-loop/.claude-plugin/plugin.json > /dev/null && echo "plugin.json OK"
else
  echo "SKIP: feedback-loop/ 미생성 — G6 머지 또는 S4 완료 후 재실행"
fi

# 7. marketplace.json 유효성
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace.json OK"

# 8. telemetry 수동 페이로드 주입 — skill_invoke_end meta 채워짐 확인
echo '{"session_id":"test","cwd":"/tmp","tool_input":{"skill":"thinking-tools:retro"},"tool_response":{"duration_ms":1234,"usage":{"input_tokens":100,"output_tokens":50,"cache_read_input_tokens":20}}}' \
  | CLAUDE_KIT_TELEMETRY=1 bash telemetry/event-logger.sh skill_invoke_end
# 기대: telemetry/events/events-$(date -u +%F).jsonl 마지막 줄에 meta.duration_ms=1234 포함
tail -1 telemetry/events/events-$(date -u +%F).jsonl | python3 -c "
import json,sys
e=json.load(sys.stdin)
assert e['meta'].get('duration_ms')==1234, f'duration_ms mismatch: {e[\"meta\"]}'
assert e['meta'].get('input_tokens')==100, f'input_tokens mismatch: {e[\"meta\"]}'
print('meta fields OK')
"

# 9. 라인 크기 3500B 미만 확인
python3 telemetry/scripts/validate-schema.py --since=1d --strict
# 기대: All schema checks passed (또는 violation 0건)
```

통과 기준:
- 1~3: 오류 없이 실행 완료
- 4: `OK: all 8 cases passed`
- 5: `dod.seeded_detected` 에 E8:2 포함
- 6~7: JSON 유효성 통과
- 8: `meta fields OK` 출력
- 9: PIPE_BUF 경고 0건

## 의존성 / 순서 주의

- **게이트 조건**: G6(#122, ⑤ 하네스 플러그인 신설) PR 머지 완료 후 착수 권장. G6 미완료 시 S4에서 plugin.json 골격을 G7 내에서 직접 생성 가능하나, G6와 충돌 방지를 위해 G6 담당자와 사전 조율 필요
- **S1 선행 필수**: S2(validate-schema 확장)와 S3(README/report.py)는 S1 완료 후 진행. S1에서 meta 필드 구조가 확정돼야 self-test 케이스와 문서 예시를 정확히 쓸 수 있음
- **S4 선행 필수**: S5/S6(SKILL.md 작성)은 plugin.json 골격이 있어야 frontmatter의 `name` 필드를 일치시킬 수 있음
- **S5 선행 필수**: S6은 S5 파일을 이어서 작성하는 슬라이스이므로 순서 강제
- **S7(리뷰) 마지막**: S1~S6 전 변경이 완료된 뒤 단일 review pass
- **크로스청크 게이트**: retro의 dedup 이력 확인은 `meta.duration_ms` 및 토큰 데이터가 실제로 쌓인 이후에야 의미 있음 — S1 완료 후 최소 1 dogfooding 세션이 지나면 데이터 존재 확인 가능. 초기 구현에서는 현재 session 내 dedup(메모리 기반)만 구현하고, telemetry 기반 세션 간 dedup은 데이터 축적 후 확장 검토
- **OVM 수정 금지**: retro 스킬은 OVM audit 결과를 읽기만 함. `obsidian-vault-manager/` 하위 파일 수정 금지 — 단방향 경계(harness→leaf) 불변
- **vault-bridge 수정 금지**: 기억 갈래는 `/save-session` slash command를 사용자가 직접 실행하도록 안내. retro 스킬이 vault-bridge 파일을 수정하거나 vault-searcher를 직접 호출하면 Write Role Contract 위반
