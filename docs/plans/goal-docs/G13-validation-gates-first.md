---
goal_id: G13
title: ⑤ 검증 게이트 1차 — CI 리뷰 종료조건 + 마켓플레이스 거버넌스 가드 (의존-0)
issues: [169]
wave: 독립
depends_on: []
recommended_model: sonnet
status: ready
work_type: feature-full
applies_tiers: [default]
schema_version: 1
created: 2026-06-05
---

# G13 — ⑤ 검증 게이트 1차 (CI 종료조건 + 거버넌스 가드)

## 배경 / 목적

self-hosting 부트스트랩(sub-epic #172)의 **의존-0 첫 조각**이에요. #172의 나머지(#123 retro=G7, #171 handoff)는 G6(workflow-harness 신설, `status: gated`)에 hard 의존해서 지금 당장 착수 못 해요 — G7 frontmatter가 `depends_on: [G6]`이고 G6는 게이트 대기거든요.

반면 이 묶음은 **하네스 없이 즉시 가능**해요. `.github/workflows/claude-code-review.yml`과 `validate.yml`이 이미 존재하니 설정·스크립트·정책만 손대면 되고, 둘 다 deterministic이라 헌법(CON-2)에 안전해요. 게다가 CI 종료조건(#169)은 review-round 낭비를 *직접* 줄여서 측정-개선 효과가 retro 없이도 바로 나요.

두 슬라이스를 한 goal로 묶는 응집 근거: 둘 다 **검증 게이트 · deterministic · 하네스 불요 · 즉시 ROI · file-disjoint(병렬 가능)**.

> 인사이트 출처: 2026-06-05 insight-mining 세션. review-fix 50건 분류(~85% nit, ~15% substantive), version-sync 14개 수작업 커밋, validate.yml이 CLAUDE.md 등록 테스트 ~15개 중 3개만 실행.

## 포함 이슈

- **#169** (완전 닫음): CI claude-review 종료조건 — severity 게이트 + P2 nit defer + 재지적 금지 + #134 shift-left 경계.
- **#134** (부분 진행 — 거버넌스 가드 2항목만): version-sync drift guard + CI 테스트 커버리지 guard. **게이트 체인 전체(프리커밋·슬라이스 critique·프리푸시 quality·retro 오케스트레이션)는 G6 harness 후이므로 #134는 열어둠.**

## 완료 조건 (Definition of Done)

### #169 (CI 리뷰 종료조건)
- [ ] `claude-code-review.yml` 프롬프트에 **severity 분류(P0 blocking / P1 should-fix / P2 nit)** 강제 지침 추가
- [ ] **P2 이하 nit defer**: 그 PR에서 고치지 말고 백로그 이슈로 묶으라는 지침 (silent drop 금지)
- [ ] **재지적 금지**: 이전 라운드에서 이미 다룬 점 재제기 금지 지침
- [ ] **shift-left 경계 명시**: substantive(P0/P1)는 #134 프리푸시 quality 대상, CI는 fresh-eyes 안전망 — 중복 정의 금지로 주석
- [ ] 라운드 cap 정책을 `CONTRIBUTING.md` 또는 PR 워크플로우 문서에 기록 (substantive만 그 PR, nit은 이슈)

### #134 거버넌스 가드 (부분)
- [ ] **version-sync drift guard**: plugin.json↔marketplace.json의 `version`/`description`/`keywords` 동기화를 deterministic 체크하는 스크립트 (drift 시 비제로 exit)
- [ ] **CI 테스트 커버리지 guard**: `validate.yml` 실행 테스트 목록 ↔ CLAUDE.md Validation 섹션 등록 테스트 목록 동기화 체크 (누락 시 비제로 exit 또는 경고)
- [ ] 두 guard를 `validate.yml`에 단계로 등록 + CLAUDE.md Validation 섹션에 명령 추가
- [ ] #134 본문 acceptance의 거버넌스 항목 체크 + 게이트 체인 잔여 범위를 G6 후속으로 명시

### 공통 검증 게이트 (CLAUDE.md Validation 섹션 실제 명령)
- [ ] 기존 회귀 테스트 전부 green (변경한 스크립트 포함)
- [ ] `python3 -m json.tool`로 모든 manifest 유효
- [ ] `bash -n`으로 셸 스크립트 문법 OK

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| CI 리뷰 존치 | 제거 / 유지+종료조건 / 현행 | **유지+종료조건** | substantive 15%(실버그·보안)는 진짜라 제거 시 머지됨. CI=fresh-eyes(CON-3 외부 구현) 고유 가치. 문제는 리뷰가 아니라 무한 수렴 종료조건 (2026-06-05 AskUserQuestion 결정) |
| 거버넌스 가드 위치 | #134 흡수 / 별도 이슈 | **#134 흡수** | deterministic 가드라 게이트 체인 프리커밋/CI 린터에 자연 귀속 (#138 흡수와 동일 패턴) |
| 첫 조각 선택 | retro 먼저 / 게이트 먼저 | **게이트 먼저** | retro(G7)는 G6 harness `gated` 의존이라 즉시 불가. 게이트/거버넌스는 의존-0. retro는 G6 ready 전환 후 |
| guard 강도 | block(비제로 exit) / warn(경고만) | **version-sync=block, CI커버리지=warn 시작** | version drift는 릴리스 깨짐 = 강제. 커버리지 누락은 점진 도입이라 경고로 시작해 안정화 후 block |

## 슬라이스 순서

> **S1 ∥ S2 병렬** (file-disjoint — S1=`.github/workflows/claude-code-review.yml`+docs, S2=`scripts/`+`validate.yml`+`CLAUDE.md`). dynamic workflow로 동시 처리 가능. 각 슬라이스는 자체 커밋 단위.

1. **CI 리뷰 종료조건** → 바인딩: `직접(메인 컨텍스트, 프롬프트 설계)` → `code-reviewer (게이트 지침 정합 검토)` | 대상 파일: `.github/workflows/claude-code-review.yml`, `CONTRIBUTING.md`(라운드 cap 정책) | 산출: severity 게이트 + P2 defer + 재지적 금지 프롬프트, 라운드 cap 정책 문서 | 검증: YAML 유효 + 프롬프트에 P0/P1/P2 + defer + 재지적 금지 키워드 존재

2. **마켓플레이스 거버넌스 가드** → 바인딩: `executor (deterministic 스크립트 저작)` → `code-reviewer (drift 케이스 커버 검토)` | 대상 파일: `scripts/check-version-sync.py`(신규), `scripts/check-ci-coverage.py`(신규), `.github/workflows/validate.yml`, `CLAUDE.md`(Validation 섹션) | 산출: version-sync drift guard(block) + CI 커버리지 guard(warn) + CI 등록 + CLAUDE.md 명령 | 검증: 정상 트리에 exit 0, 의도적 drift 주입 시 version-sync는 비제로 exit

> spec 단계는 경량(이슈 #169/#134 acceptance가 spec 역할) — feature-full이나 spec-first 슬라이스 생략, impl→critique 중심.

## E2E 자가검증

```bash
cd "$(git rev-parse --show-toplevel)"

# === S1: CI 리뷰 종료조건 ===
# YAML 구조 유효성: yaml 모듈 있으면 로컬 체크, 없으면 CI(push)가 검증 (로컬 dogfood 환경엔 pyyaml 부재)
python3 -c "import yaml" 2>/dev/null \
  && python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/claude-code-review.yml')); print('S1 YAML OK')" \
  || echo "S1 YAML: pyyaml 없음 → CI(push)가 워크플로우 파싱으로 검증"
# severity 게이트 + defer + 재지적 금지 지침 존재 (프롬프트 키워드)
grep -qiE "P0|P1|P2|severity" .github/workflows/claude-code-review.yml && echo "S1 severity 게이트 present"
grep -qiE "defer|nit.*issue|별도 이슈|backlog" .github/workflows/claude-code-review.yml && echo "S1 nit defer present"
grep -qiE "already|이미 다룬|재지적|previous round|prior" .github/workflows/claude-code-review.yml && echo "S1 재지적 금지 present"

# === S2: 거버넌스 가드 ===
# 정상 트리: 통과 (exit 0)
python3 scripts/check-version-sync.py && echo "S2 version-sync clean OK"
# 의도적 drift 주입 → 비제로 exit 기대 (임시 복사본으로 비파괴 테스트)
tmp=$(mktemp -d); cp -r .claude-plugin "$tmp/"; \
  python3 - "$tmp" <<'PY'
import json,sys,glob,os
mp=os.path.join(sys.argv[1],".claude-plugin","marketplace.json")
d=json.load(open(mp)); d["plugins"][0]["version"]="0.0.0-drift"; json.dump(d,open(mp,"w"))
print("drift injected into copy")
PY
# (가드가 --root 인자 또는 환경변수로 대상 경로 받도록 구현 — 아래는 인터페이스 예시)
python3 scripts/check-version-sync.py --root "$tmp" && echo "S2 FAIL: drift 미탐지" || echo "S2 drift 탐지 OK (비제로 exit)"
rm -rf "$tmp"

# CI 커버리지 guard: CLAUDE.md 등록 vs validate.yml 실행 diff
python3 scripts/check-ci-coverage.py && echo "S2 CI coverage check ran"

# === 공통 게이트 ===
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "manifest valid"
for p in thinking-tools obsidian-vault-manager vault-bridge; do
  python3 -m json.tool "$p/.claude-plugin/plugin.json" > /dev/null; done && echo "plugin manifests valid"
bash -n .github/workflows/*.yml 2>/dev/null; echo "shell/yaml syntax checked"
```

**통과 기준**: S1 4줄(YAML+severity+defer+재지적) 전부 출력, S2 정상 클린 + drift 탐지(비제로 exit) + 커버리지 체크 실행, 공통 게이트 green.

## 의존성 / 순서 주의

- **착수 조건**: 의존-0. `status: ready`이므로 즉시 S1 착수 가능 (G6/G7과 무관).
- **scope 처리**: 구현 중 발견한 문제는 이 scope에 넣을 수 있으면 즉시 흡수, 아니면 새 이슈로 분리(silent drop 금지). 하네스 레벨 이슈 vs 로컬 리포 이슈 구분.
- **후속 연결**: 이 goal 완료 후 #172 sub-epic의 다음 조각은 G6(harness, opus, gated→ready 전환 필요) → 그 후 G7 retro / #171 handoff. CI 종료조건이 만든 review-round 측정치는 G7 retro 낭비탐색의 입력이 됨.
- **#134 잔여**: 게이트 체인 오케스트레이션(프리커밋·슬라이스 critique·프리푸시 quality·retro 자동)은 harness 주체라 G6 후. 이 goal은 #134의 deterministic 거버넌스 가드 2항목만 충족.
