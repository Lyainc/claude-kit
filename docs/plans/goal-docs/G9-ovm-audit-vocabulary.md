---
goal_id: G9
title: OVM audit vocabulary 일관성 + E2 tag 추론
issues: [119, 127]
wave: 독립·게이트
depends_on: []
recommended_model: sonnet
status: gated
created: 2026-06-03
---

# G9 — OVM audit vocabulary 일관성 + E2 tag 추론

## 배경 / 목적

kepano(Obsidian 제작자)의 운용 원칙은 "Property names and values should aim to be reusable across categories"와 "Always pluralize categories and tags"를 명시해요. claude-kit는 현재 파일명 컨벤션(pre-write-guard)만 강제하고 태그·프로퍼티 vocabulary 일관성은 전혀 audit하지 않아요. 같은 vault 안에 `api`/`apis`, `source_url`/`sourceUrl`이 혼재해도 아무것도 잡지 못해요.

E9(#119)는 이 공백을 결정론적으로 메우는 새 error type이에요. E2 auto-fix(#127)는 현재 사실상 빈 배열 삽입과 다름없는 tag 추론 로직을 type/파일명/폴더 계층 기반으로 구체화해요. #127의 추론 태그는 E9가 확정한 vocabulary 기준(singular/plural + camel/snake 정책)을 따라야 하므로 두 이슈는 같은 goal로 묶어요.

## 포함 이슈

- #119: `enhance(ovm/audit): add E9 tag/property vocabulary consistency check` — vault-wide 태그·프로퍼티 키를 집계해 E9a singular/plural 불일치, E9b camelCase/snake_case 혼재를 감지하는 새 error type 추가 (backlog — 착수 게이트 있음)
- #127: `enhance(ovm/audit): E2 auto-fix tag 추론을 type/파일명 기반으로 개선` — E2 OPTIONAL-FIX 시 추론 태그(1순위 type값, 2순위 파일명 슬러그, 3순위 부모폴더명)를 미리보기로 제안하도록 개선

## 완료 조건 (Definition of Done)

### #119 (E9) — backlog 해제 게이트 통과 후 적용

- [ ] 착수 게이트 통과: open questions(finding granularity, DoD 카운팅 단위) 결정 완료 후 backlog 라벨 제거 확인
- [ ] `reference/vault-audit-rules.md`에 E9 섹션 추가 — E9a(singular/plural) + E9b(camelCase/snake_case) detection pseudocode, FP guard(빈도 임계값 N≥3, allowlist), priority P2 명시
- [ ] `skills/audit/SKILL.md` Phase 2 CLASSIFY 테이블에 E9 행 추가 (`E9 | tag_vocabulary_inconsistency | Warning | P2 | vault-wide tag/property index | —`)
- [ ] `scripts/test/audit-validate.py` — `classify()` 함수에 E9a + E9b 구현, `PRIORITY_BY_TYPE` 상수에 `"E9_tag_vocabulary_inconsistency": "P2"` 추가
- [ ] `SEED_PREFIXES`에 E9 항목 추가 (`("path", "audit-e9-")` 또는 pair-level 카운팅 단위로 확정한 방식)
- [ ] `scripts/test/gen-fixture.sh --with-audit-errors`에 E9 시드 주입 + `--dod` 결과에 `seeded_detected.E9 ≥ 1` 포함
- [ ] E9c(semantic synonym) scope 제외 — 별도 이슈 분리 명시
- [ ] path 처리 정책 결정 후 구현: `path: ""` (vault-level) 또는 대표 위반 파일 경로 중 하나를 선택해 REPORT 출력과 일관성 유지

### #127 (E2 tag 추론)

- [ ] `scripts/ovm-primitives.sh`에 `infer-tags <file>` 서브커맨드 추가 (또는 SKILL.md 인라인 로직) — 결정론적, LLM 없음
  - 1순위: `type:` 필드값
  - 2순위: 파일명에서 날짜 prefix + type prefix 제거 후 `-`/`_` 분리 슬러그
  - 3순위: 부모 폴더명 (e.g., `notes/llm/` → `llm`)
  - 빈 슬러그(파일명이 날짜만인 경우) graceful 처리 (태그 없이 type만 반환)
- [ ] `skills/audit/SKILL.md` Phase 4 OPTIONAL-FIX 확인 화면에 "추론된 태그: [X, Y, Z]" 미리보기 추가
- [ ] `scripts/test/audit-validate.py` E2 auto-fix 시뮬레이션 케이스에 추론 결과 검증 로직 추가 (추론 태그가 빈 배열이 아님을 확인)
- [ ] 추론 태그는 E9가 확정한 vocabulary 기준(singular 우선, snake_case 우선 등)을 준수

### 공통

- [ ] 기존 DoD 검증 전체 패스:
  ```bash
  rm -rf /tmp/ovm-fixture-audit-recheck
  OVM_FIXTURE_DIR=/tmp/ovm-fixture-audit-recheck \
    bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors
  python3 obsidian-vault-manager/scripts/test/audit-validate.py \
    /tmp/ovm-fixture-audit-recheck --dod
  ```
  기존 E1–E8 `seeded_detected` 수치 회귀 없음, `priority_mismatches: []`, `fp_on_clean` per type = 0 유지

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| E9 finding granularity: `path` 필드를 어떻게 쓸지 | A) `path: ""` (vault-level, pair 단위 보고) vs B) 대표 위반 파일 경로 사용 | A 권장 | E9는 파일-level이 아닌 pair-level finding이라 대표 파일 선택이 자의적; vault-level로 두면 REPORT 그룹 처리는 추가되지만 의미가 더 정확함. SEED_PREFIXES 카운팅은 `detail` 필드에 pair 식별자를 넣어 대체 가능 |
| E9 DoD 카운팅 단위 | A) pair 개수 (E9a 쌍 수 + E9b 쌍 수) vs B) finding 개수 | A 권장 | "pair 개수"로 정의하면 시딩도 pair 단위로 명확히 대응; `seeded_detected.E9` = 시드된 pair 수로 정의 |
| #119 backlog 해제 조건 | open questions(granularity, DoD 단위) 설계 결정만 필요 — 코드 난이도가 게이트가 아님 | 설계 결정 → backlog 라벨 제거 → S1 착수 | 이슈 코멘트에 결정 내용 기록 후 PR에서 진행 |
| E9b camelCase 검출 정밀도 | regex `[a-z][A-Z]` 패턴으로 camelCase 키 감지 → snake_case 등가 추정 후 양쪽 등장 시 보고 | 현재 이슈 approach 그대로 | stdlib만 사용, FP는 allowlist로 완화 |
| FP 완화: 빈도 임계값 N | N=3 (양쪽 모두 3개 파일 이상) vs N=2 | N=3 권장 | 이슈 원문 명시; 단발성 오타 억제 효과 |
| E9c semantic synonym | scope 포함 vs 제외 | 제외 (이슈 원문 결정) | LLM 판단 필요 + FP 과다 + 유지보수 비용. 별도 이슈(`--deep` opt-in)로 분리 |
| #127 infer-tags 위치 | `ovm-primitives.sh` 서브커맨드 vs SKILL.md 인라인 | `ovm-primitives.sh` 서브커맨드 권장 | primitives의 역할(shell 계층 로직)과 일치; SKILL.md는 orchestration만 담당하는 원칙 유지 |
| 추론 태그 적용 방식 | 자동 확정 vs 제안(확인 게이트) | 제안 유지 (이슈 원문 결정) | 추론이 틀릴 수 있음; 사용자 확인 게이트가 안전망 |

## 슬라이스 순서

1. **S1 설계 확정 + backlog 해제** → 바인딩: `executor` (gh CLI + 이슈 코멘트) | 대상 파일: GitHub issue #119 코멘트 | 산출: granularity(path="")+DoD단위(pair) 결정 기록, backlog 라벨 제거 | 검증: `gh issue view 119` 에서 backlog 라벨 소실 확인

2. **S2 E9 규칙 문서화** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/reference/vault-audit-rules.md` | 산출: E9 섹션(E9a pseudocode, E9b pseudocode, FP guard N≥3, allowlist, P2 priority, E9c 제외 명시) | 검증: `python3 -m json.tool` 해당 없음(MD 파일), 수동 리뷰

3. **S3 SKILL.md CLASSIFY 테이블 업데이트** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/skills/audit/SKILL.md` | 산출: Phase 2 CLASSIFY 테이블에 E9 행 추가 | 검증: S2와 테이블 일치 확인 (code-reviewer)

4. **S4 audit-validate.py E9 구현** → 바인딩: `executor` (model=sonnet) | 대상 파일: `obsidian-vault-manager/scripts/test/audit-validate.py` | 산출: `classify()` 내 E9a + E9b 로직, `PRIORITY_BY_TYPE`에 `"E9_tag_vocabulary_inconsistency": "P2"` 추가, `SEED_PREFIXES`에 E9 추가 | 검증:
   ```bash
   python3 obsidian-vault-manager/scripts/test/audit-validate.py --help
   ```
   구문 오류 없음 확인

5. **S5 gen-fixture.sh E9 시드 주입** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/scripts/test/gen-fixture.sh` | 산출: `--with-audit-errors` 에 E9a 시드(singular/plural 혼재 태그 파일 쌍) + E9b 시드(camel/snake 혼재 키 파일 쌍) 주입 | 검증: gen-fixture.sh syntax check
   ```bash
   bash -n obsidian-vault-manager/scripts/test/gen-fixture.sh
   ```

6. **S6 E2 infer-tags 구현** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/scripts/ovm-primitives.sh` | 산출: `infer-tags <vault_root> <rel_path>` 서브커맨드 (type→슬러그→부모폴더 3순위, 빈 슬러그 graceful) | 검증:
   ```bash
   bash -n obsidian-vault-manager/scripts/ovm-primitives.sh
   ```

7. **S7 SKILL.md OPTIONAL-FIX 미리보기 업데이트** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/skills/audit/SKILL.md` | 산출: Phase 4 OPTIONAL-FIX 확인 화면에 "추론된 태그: [X, Y, Z]" 미리보기 추가 | 검증: S3와 함께 code-reviewer 리뷰

8. **S8 audit-validate.py E2 추론 검증 추가** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/scripts/test/audit-validate.py` | 산출: E2 finding의 추론 태그 시뮬레이션 케이스 추가 (빈 배열이 아님 확인) | 검증: S9 DoD 전체 패스에서 확인

9. **S9 DoD 전체 패스 + 코드 리뷰** → 바인딩: `verifier` + `code-reviewer` | 대상 파일: 변경된 모든 파일 | 산출: DoD 통과 증거 + 리뷰 통과 | 검증: 아래 E2E 자가검증 전체

## E2E 자가검증

```bash
# 1. syntax check (shell scripts)
bash -n obsidian-vault-manager/scripts/ovm-primitives.sh
bash -n obsidian-vault-manager/scripts/test/gen-fixture.sh

# 2. audit-validate.py import 오류 없음
python3 -c "import obsidian-vault-manager.scripts.test.audit-validate" 2>/dev/null || \
  python3 obsidian-vault-manager/scripts/test/audit-validate.py --help > /dev/null

# 3. DoD 전체 패스 (기존 E1-E8 회귀 없음 + E9 추가 검증)
rm -rf /tmp/ovm-fixture-audit-recheck
OVM_FIXTURE_DIR=/tmp/ovm-fixture-audit-recheck \
  bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod

# 4. 기존 단위 테스트 회귀 없음
python3 obsidian-vault-manager/scripts/test/test-parse-created-date.py
python3 obsidian-vault-manager/scripts/test/test-git-activity.py
python3 obsidian-vault-manager/scripts/test/test-promotion-finding.py
python3 obsidian-vault-manager/scripts/test/test-read-manifest-summary.py

# 5. JSON 매니페스트 유효성
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
```

통과 기준:
- `bash -n` 오류 없음
- DoD `dod.seeded_detected` — E1:5, E2:10, E3:5, E4:5, E5:5, E6:5, E7:5, E8:2 **회귀 없음**; E9 ≥ 1(시드된 pair 수)
- `dod.priority_mismatches: []`
- `dod.fp_on_clean` per type = 0 (E9 포함)
- `dod.findings_missing_priority: 0`
- 단위 테스트 4종 전부 "OK: all cases passed"
- JSON 유효성 검사 통과

## 의존성 / 순서 주의

- **착수 게이트**: #119는 backlog 라벨 — S1(설계 확정)이 완료되어 backlog 라벨이 제거될 때까지 S2 이후 구현 착수 불가
- **#127 → #119 선행 권장**: E2 추론 태그는 E9가 확정한 vocabulary 기준(singular 우선, snake_case 우선 등)을 따라야 함. S6(E2 infer-tags)은 S2(E9 규칙 문서화) 완료 후 착수 권장. 단 S6의 type/슬러그 기반 설계 자체는 S1 완료 시점부터 선행 가능
- **S4(audit-validate.py) → S5(gen-fixture.sh)**: gen-fixture.sh의 E9 시드가 의미 있으려면 audit-validate.py의 E9 감지 로직이 먼저 있어야 함
- **크로스청크 게이트 없음**: G9는 다른 goal에 의존하지 않음 (E9는 E1~E8 schema와 독립적으로 추가 가능, 이슈 원문 확인)
- **PRIORITY_BY_TYPE 동기화**: `audit-validate.py`의 `PRIORITY_BY_TYPE` 상수와 `reference/vault-audit-rules.md` Priority Mapping 테이블은 항상 동기화 유지. S4 완료 후 drift 검사 필수 (`dod.priority_mismatches: []` 조건으로 기계적 확인)
