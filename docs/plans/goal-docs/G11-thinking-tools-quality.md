---
goal_id: G11
title: thinking-tools 품질 강화 + stale ref 청소
issues: [106, 107, 110, 120]
wave: 독립
depends_on: []
recommended_model: sonnet
status: ready
created: 2026-06-03
---

# G11 — thinking-tools 품질 강화 + stale ref 청소

## 배경 / 목적

세 묶음이 하나의 goal로 응집되는 이유는 공통 완료 조건이 `check-trigger-regression.py origin/main` 통과이고, 모두 `thinking-tools` 플러그인의 SKILL.md·보조 파일을 건드리기 때문이에요. 독립 wave라 선행 goal 없이 즉시 착수 가능해요.

- **#106·#107**: expert-panel 다양성 원천(역할 프롬프트)·격리모드 다라운드 지원 검증 + saturation 종료조건 dedup — 설계 부채 해소
- **#120**: adversarial-review Evidence Attack에 vault 결정 기록 근거 주입 — 사용자 맥락 밀착 공격 벡터 강화
- **#110**: 제거된 CLI 플래그 + auto_capture stale ref 정리 — "죽은 인터페이스" 노출 방지

## 포함 이슈

- #106: expert-panel 역할프롬프트 차별화 강도 검증 (D4a) — 다양성 원천이 역할 프롬프트임을 문서화, C1 STATE 격리모드 다라운드 지원 확인, full-spawn-default 금지 유지
- #107: C2 saturation 종료조건 일반화 + shared STATE 헤더 dedup — expert-panel·unknown-discovery·adversarial-review 3스킬 간 중복 directive 단일출처화
- #110: 제거된 CLI 플래그(--all/--best/--quick/--refine) aux 파일 자연어 전환 + auto_capture stale ref(README:70, thought-chain-checkpoint-vault-integration.md:109) 정정
- #120: adversarial-review Evidence Attack을 vault-searcher 경유 `type:decision` 검색으로 grounding — Steelman 확정 직후 1회 Agent 호출, 최대 3건 발췌, graceful degrade

## 완료 조건 (Definition of Done)

### #106 (expert-panel 역할프롬프트 차별화)
- [ ] `expert-panel/reference.md` §2 참여자 구성에 "다양성 원천 = 역할 프롬프트(ChatEval/Du et al.)" 문구 명시 — spawn count·temperature 조작이 다양성 원천이 아님을 일문장으로 못 박아둬요
- [ ] `expert-panel/SKILL.md` 격리 실행 모드(isolated) 설명에 C1 STATE `Mode: [isolated:on]` 필드가 다라운드에 걸쳐 보존됨을 확인 및 문구 명확화 (현행 SKILL.md:108 `Mode` 필드 read point가 Phase 2 item 1에만 언급 — Phase 1 라운드 간 보존 명시 추가)
- [ ] `full-spawn-default 금지` 제약이 SKILL.md 또는 reference.md에 한 곳에 명시 (현재 미명시 — 이슈 코멘트만 존재)
- [ ] trigger-regression green

### #107 (saturation 종료조건 일반화 + dedup)
- [ ] expert-panel·unknown-discovery 두 스킬 SKILL.md에 saturation 종료조건이 **동일한 canonical 1문구**로 존재 (adversarial-review SKILL.md:127 기존 문구 기준으로 통일; 이미 존재하면 reference로 교차 참조)
- [ ] 3스킬(expert-panel·unknown-discovery·adversarial-review) 중 **공유 internal-only directive 문장**이 중복된 파일을 식별하고, 한 파일에서 제거하거나 단일 출처 참조로 교체
- [ ] STATE compaction 불변 — 기존 STATE 블록 포맷(필드명·enum값)이 변경되지 않음을 grep으로 확인
- [ ] trigger-regression green

### #110 (stale ref 청소)
- [ ] `grep -rn -- '--all\|--best\|--quick\|--refine\|--deep\|--brief' thinking-tools/skills` 결과 = 0 (test 파일·"Removed:" 주석 제외)
- [ ] `README.md:70` — `auto_capture: true` → `snapshot_export: true` / `snapshot_import: true` 두 키 설명으로 정정
- [ ] `docs/design/thought-chain-checkpoint-vault-integration.md:109` — `"honors auto_capture alias"` 삭제
- [ ] `docs/discussions/20260510_*`·`20260416_*` transcript의 `auto_capture`는 **건드리지 않음** (역사 기록 보존)
- [ ] trigger-regression green

### #120 (adversarial-review vault grounding)
- [ ] `adversarial-review/SKILL.md` Phase 0 완료 직후·Phase 1 시작 전 vault-searcher Agent 1회 호출 절차 명시 (Agent tool 사용, MECE 준수 — 직접 Grep/Read vault 접근 금지 조항 포함)
- [ ] `reference/patterns.md` `[Evidence Attack]` 템플릿의 `{counter_evidence_or_missing_data}` 슬롯에 vault 조회 결과 삽입 방법 기술
- [ ] graceful degrade 분기 문서화: 결과 ≥1건 → vault-grounded mode; 결과 0건 / vault-bridge 미설치 → 기존 Evidence Attack 폴백 (사용자 알림 없음)
- [ ] vault-bridge 미설치 환경에서 adversarial-review 오류 없이 동작함을 검증 (vault-searcher Agent 호출 실패 catch 처리)
- [ ] 토큰 오버헤드 바운드: 섹션 발췌 3건 상한 + haiku 모델 → Phase 1 기준 +1500 토큰 이하 (SKILL.md에 바운드 명시)
- [ ] trigger-regression green

### 공통
- [ ] `python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test` → `OK: all 9 self-test cases passed`
- [ ] `python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main` → `RESULT: no trigger removals`
- [ ] `python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null` 통과

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| #106 — 역할프롬프트 차별화 강도 검증 위치 | (A) SKILL.md 본문에 직접 명시 (B) reference.md §2 참여자 구성에 삽입 | **B** | SKILL.md는 이미 간결; 전문가 페르소나 강화 원칙이 reference.md §2에 있으므로 단일 출처 원칙 준수 |
| #106 — `full-spawn-default 금지` 표현 강도 | (A) WARNING 박스로 강조 (B) 일반 텍스트 한 문장 | **B** | 지시 중복이 오히려 conflict; 한 곳에 명확하게가 원칙 |
| #107 — saturation canonical 문구 위치 | (A) 각 스킬 SKILL.md에 동일 문구 복사 (B) 한 스킬에 두고 나머지는 교차 참조 | **A (동일 문구 인라인)** | 스킬 간 참조 체인은 load-on-demand 패턴과 충돌; 각 스킬은 독립 실행 단위 — 동일 1문구 복사가 실용적 |
| #107 — 공유 internal-only directive가 실제 어느 스킬에 존재하는지 | 집행 전 grep 확인 필요 | **S2에서 실측 후 결정** | 이슈가 "3스킬 중복"이라 했으나 현재 코드에서 어느 문장인지 미확인; grep 없이 가정하면 과잉/과소 수정 위험 |
| #120 — vault-searcher 호출 실패 처리 방식 | (A) try/catch 절차를 SKILL.md에 의사코드로 명시 (B) "결과 없으면 폴백" 한 줄 | **B** | SKILL.md는 자연어 지시서 — 의사코드는 파싱 부하; 폴백 결과가 동일하면 간결 우선 |
| #120 — Counter-scenario 벡터에도 vault 근거 적용 | (A) Evidence Attack + Counter-scenario 두 벡터 적용 (B) Evidence Attack만 | **B** | 이슈 Scope 표에서 Counter-scenario는 "부(부가적)" 표기; 두 벡터 동시 적용은 +1500 토큰 바운드 초과 위험 |

## 슬라이스 순서

1. **S1 stale-ref 청소** → 바인딩: executor (sonnet) | 대상 파일: `thinking-tools/skills/diverse-sampling/examples.md`, `thinking-tools/skills/diverse-sampling/reference.md`, `thinking-tools/skills/spec-first/reference.md`, `thinking-tools/skills/spec-first/templates/SEED_SPEC.yaml`, `thinking-tools/skills/thought-chain/reference.md`, `README.md`, `docs/design/thought-chain-checkpoint-vault-integration.md` | 산출: CLI 플래그(`--all`/`--best`/`--quick`/`--refine`) → 자연어 등가로 전환, `auto_capture` 두 곳 정정 | 검증: `grep -rn -- '--all\|--best\|--quick\|--refine\|--deep\|--brief' thinking-tools/skills` = 0, `grep -n 'auto_capture' README.md` = 0 (live docs)

2. **S2 중복 directive 실측 + dedup** → 바인딩: executor (sonnet) | 대상 파일: `thinking-tools/skills/expert-panel/SKILL.md`, `thinking-tools/skills/unknown-discovery/SKILL.md`, `thinking-tools/skills/adversarial-review/SKILL.md` | 산출: 3스킬 간 공유 internal-only directive 문장을 grep으로 실측 → 중복 제거, saturation 종료조건 canonical 1문구 expert-panel·unknown-discovery에 동기화 (adversarial-review SKILL.md:127 기존 문구 기준) | 검증: STATE compaction 필드명 변경 없음(grep으로 확인), saturation 문구 두 파일에 존재

3. **S3 expert-panel 역할프롬프트 차별화 + 격리모드 다라운드 보존** → 바인딩: executor (sonnet) | 대상 파일: `thinking-tools/skills/expert-panel/reference.md`, `thinking-tools/skills/expert-panel/SKILL.md` | 산출: reference.md §2에 "다양성 원천 = 역할 프롬프트 (ChatEval/Du et al.); spawn count·temperature 조작 불가" 1문구 추가, SKILL.md Mode 필드 보존 설명 명확화, full-spawn-default 금지 한 곳 명시 | 검증: 해당 단어 grep으로 존재 확인

4. **S4 adversarial-review vault grounding** → 바인딩: executor (sonnet) | 대상 파일: `thinking-tools/skills/adversarial-review/SKILL.md`, `thinking-tools/skills/adversarial-review/reference/patterns.md` | 산출: SKILL.md Phase 0 완료 후 vault-searcher Agent 1회 호출 절차 + 직접 vault 접근 금지 조항 추가, patterns.md Evidence Attack 템플릿에 vault 조회 결과 삽입 방법 + graceful degrade 분기 기술, 토큰 바운드(+1500) 명시 | 검증: `allowed-tools: AskUserQuestion Read Write Agent` 유지 확인, vault 직접 접근 금지 조항 grep 존재 확인

5. **S5 trigger-regression + JSON validation** → 바인딩: verifier (또는 executor 자가검증) | 대상: 위 4슬라이스 결과물 전체 | 산출: 검증 리포트 | 검증: 아래 E2E 명령 전부 통과

## E2E 자가검증

```bash
# S1 검증 — CLI 플래그 잔존 0
grep -rn -- '--all\|--best\|--quick\|--refine\|--deep\|--brief' thinking-tools/skills \
  | grep -v 'test\|Removed:' | wc -l
# 기대: 0

# S1 검증 — auto_capture live docs 잔존 0
grep -n 'auto_capture' README.md
grep -n 'auto_capture' docs/design/thought-chain-checkpoint-vault-integration.md
# 기대: 두 명령 모두 출력 없음

# S2 검증 — STATE 블록 포맷 불변 확인
grep -n 'STATE:CHECKPOINT\|/STATE' thinking-tools/skills/expert-panel/SKILL.md
grep -n 'STATE:CHECKPOINT\|/STATE' thinking-tools/skills/unknown-discovery/SKILL.md
grep -n 'STATE:CHECKPOINT\|/STATE' thinking-tools/skills/adversarial-review/SKILL.md
# 기대: 각 파일에 열기/닫기 쌍 존재, 필드명 변경 없음

# S3 검증 — 역할프롬프트 차별화 문구 존재
grep -n 'ChatEval\|Du et al\|역할 프롬프트' thinking-tools/skills/expert-panel/reference.md
grep -n 'full-spawn' thinking-tools/skills/expert-panel/SKILL.md thinking-tools/skills/expert-panel/reference.md
# 기대: 각각 1건 이상

# S4 검증 — vault-searcher 호출 절차 + 금지 조항 존재
grep -n 'vault-searcher\|vault.*직접.*금지\|직접 Grep\|직접 Read' thinking-tools/skills/adversarial-review/SKILL.md
grep -n '1500\|token.*bound\|토큰.*바운드' thinking-tools/skills/adversarial-review/SKILL.md
# 기대: 각각 1건 이상

# 공통 — trigger-regression self-test
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
# 기대: OK: all 9 self-test cases passed

# 공통 — trigger-regression diff (trigger 제거 없어야 함)
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
# 기대: RESULT: no trigger removals

# 공통 — JSON 유효성
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null && echo "OK"
# 기대: OK
```

- 통과 기준: 모든 명령이 기대 결과와 일치. `check-trigger-regression.py origin/main`은 exit 0 + "no trigger removals" 출력.

## 의존성 / 순서 주의

- **선행 goal 없음** — wave=독립, 즉시 착수 가능해요.
- **슬라이스 간 순서**: S1(stale ref) → S2(dedup) → S3(expert-panel) → S4(vault grounding) → S5(검증). S2·S3는 병렬 가능하나 S2에서 어떤 directive가 중복인지 확인한 결과가 S3 작업에 영향을 줄 수 있으므로 S2 완료 후 S3 착수를 권장해요.
- **#120과 vault-bridge**: vault-searcher는 이미 v1.9.0에 존재해요. vault-bridge 설치 여부에 관계없이 graceful degrade로 동작해야 하므로 vault-bridge 관련 goal이 먼저 완료될 필요 없어요.
- **transcript 보존**: `docs/discussions/20260510_*`·`20260416_*` 내 `auto_capture` 는 절대 건드리지 않아요 — 역사 기록이에요.
- **graphify 캐시**: `graphify-out/cache/*.json` 수동 수정 불필요 — 재생성 아티팩트예요.
- **cross-chunk**: 다른 G-goal과 파일 중복 없어요. thinking-tools SKILL.md만 건드리는 독립 묶음이에요.
