---
goal_id: G8
title: OVM audit 결정론 검사 4종 확장
issues: [126, 128, 129, 130]
wave: 독립
depends_on: []
recommended_model: sonnet
status: ready
work_type: feature-full
created: 2026-06-03
---

# G8 — OVM audit 결정론 검사 4종 확장

## 배경 / 목적

obsidian-vault-manager `/audit` 스킬의 CLASSIFY 단계는 현재 E1–E8 8종을 탐지해요. 그런데 사용자에게 "이게 잘못됐어요"라고만 말하고 **어떻게 고쳐야 하는지** 를 알려주지 않는 이슈(E3, E5)와, 아예 탐지하지 못하는 구조적 위반(E10, E11)이 남아있어요.

이 4종은 모두 **결정론적(LLM=0)이고 표시 전용(auto-fix 아님)** 이라는 공통 성질을 가져요:
- E3: rename은 inbound wikilink에 영향 → 제안만
- E5: 링크 삽입 위치는 사용자 결정 → 후보 표시만
- E10/E11: 파일 이동은 inbound wikilink에 영향 → 경고만

같은 파일군(`audit-validate.py`, `vault-audit-rules.md`, `audit/SKILL.md`, `gen-fixture.sh`)을 건드리므로 한 번에 처리하면 패치 충돌 없이 깔끔하게 완료할 수 있어요. 4종 모두 기존 SCAN 데이터(`frontmatter_records`, `filename_records`, `inbound_links`)만 쓰기 때문에 SCAN 단계 변경이 필요 없어요.

## 포함 이슈

- #126: E3 파일명 위반 시 구체적 rename 제안 추가 — `filename_conforms()` 위반 시 `suggested_filename` 계산 후 finding `detail`에 포함
- #128: E10 misplaced_file — type↔폴더 배치 일관성 검사 신규 구현 (P1)
- #129: E11 unstructured_path — canonical 폴더(inbox/notes/assets/) 외부 파일 검사 신규 구현 (P1)
- #130: E5 orphan 노트에 tag 기반 연결 후보 top3 제안 추가 (exact match only)

## 완료 조건 (Definition of Done)

### #126 (E3 제안)
- [ ] `audit-validate.py` `classify()` 내 E3 블록: `filename_conforms()` 위반 시 `suggested_filename` 계산 함수 `_compute_suggested_filename(rel, fm)` 구현
  - `type: note` → `{slug}.md` (date prefix 제거)
  - `type: decision` / `type: plan` → `{type}-{YYYY-MM-DD}-{slug}.md`
  - `type: capture` / `type: session` → `{type}-{YYYY-MM-DD}.md`
  - `type:` 또는 `created:` 둘 다 없는 경우 → `None` (기존 메시지 유지)
- [ ] E3 finding `detail`에 `"권장 파일명: {suggested_filename}"` 줄 포함 (계산 가능한 경우만)
- [ ] `vault-audit-rules.md` E3 섹션에 `suggested_filename` 계산 pseudocode 추가
- [ ] gen-fixture E3 시드 파일(`2026-04-audit-e3-bad-NNN.md`)에 `type:` + `created:` 포함됨을 확인 — 이미 포함되어 있으므로 별도 변경 불필요
- [ ] `audit-validate.py --dod` 실행 시 E3 finding 중 `"권장 파일명:"` 문자열 포함 여부 검증 (dod_report 확장 또는 별도 assertion)

### #128 (E10 신규)
- [ ] `audit-validate.py`에 `EXPECTED_FOLDER` 상수 정의:
  ```python
  EXPECTED_FOLDER = {
      "session": "inbox", "capture": "inbox",
      "note": "notes", "decision": "notes", "plan": "notes",
  }
  ```
- [ ] `PRIORITY_BY_TYPE`에 `"E10_misplaced_file": "P1"` 추가
- [ ] `classify()` E10 블록 구현: E1/E2가 있는 파일은 스킵, `assets/` 파일 exempt, 숨김 경로 exempt
- [ ] `vault-audit-rules.md`에 E10 섹션 추가 (detection pseudocode, guard, P1)
- [ ] `audit/SKILL.md` Phase 2 CLASSIFY 테이블에 E10 행 추가
- [ ] `gen-fixture.sh --with-audit-errors`에 E10 시드 추가:
  - `notes/audit-e10-misplaced-session-NNN.md` (type: session, notes/에 위치) 5건
- [ ] `SEED_PREFIXES`에 `"E10_misplaced_file": ("path", "audit-e10-")` 추가
- [ ] `--dod` 출력 `seeded_detected.E10 ≥ 5` + `fp_on_clean.E10 == 0` 확인
- [ ] E1/E2가 있는 파일에서 E10 오탐 없음 (FP guard) 확인

### #129 (E11 신규)
- [ ] `PRIORITY_BY_TYPE`에 `"E11_unstructured_path": "P1"` 추가
- [ ] `collect()` 단계에서 모든 `.md` 파일(숨김 디렉토리 제외 현행 규칙 유지) 수집 확인 — E11은 CLASSIFY에서 파일 경로 기반 판별
- [ ] `classify()` E11 블록 구현:
  - `CANONICAL_FOLDERS = {"inbox", "notes", "assets"}`
  - `EXEMPT_FILES = {"_index.md"}`
  - `top_folder.startswith(".")` → exempt
  - `top_folder in CANONICAL_FOLDERS` → 정상
  - 그 외 → `unstructured_path`
  - 루트 직속 파일(`"/" not in str(rel)`) 포함
- [ ] `vault-audit-rules.md`에 E11 섹션 추가 (detection pseudocode, exempt list, P1)
- [ ] `audit/SKILL.md` Phase 2 CLASSIFY 테이블에 E11 행 추가
- [ ] `gen-fixture.sh --with-audit-errors`에 E11 시드 추가:
  - `20_Projects/audit-e11-misplaced-NNN.md` (임의 폴더) 5건 또는
  - `audit-e11-root-NNN.md` (루트 직속 파일) 5건
- [ ] `SEED_PREFIXES`에 `"E11_unstructured_path": ("path", "audit-e11-")` 추가
- [ ] `--dod` 출력 `seeded_detected.E11 ≥ 5` + `fp_on_clean.E11 == 0` 확인
- [ ] `.obsidian/`, `.vault-bridge/`, `.ovm/`, `_index.md` 오탐 없음 확인 — **(#129 Acceptance)** clean fixture **루트에 `_index.md`를 실제로 시드**하여 `fp_on_clean.E11 == 0`이 이 exempt 가드를 실측 통과하는지 검증 (가드가 테스트되지 않으면 회귀 위험)

### #130 (E5 후보 제안)
- [ ] `classify()` E5 블록에 tag-intersection 후보 계산 로직 추가:
  - `frontmatter_records`에서 `notes/` 파일의 `(path, tags)` 인덱스 선 구성
  - orphan P마다 다른 notes/ 파일 Q와 태그 교집합 크기 계산
  - `shared ≥ 1`인 후보를 `shared desc, path asc` 정렬 후 top3 선택
  - exact match only (semantic synonym 처리 금지)
- [ ] **(#130 Acceptance)** E5 finding 구조에 `candidates: [{path, shared_tags}]` **structured 필드** 추가 — `detail` 문자열뿐 아니라 구조화 필드로도 노출 (REPORT 렌더러는 이 필드를 읽어 "연결 후보" 줄 생성)
- [ ] E5 finding `detail`에 `"연결 후보: [[X]] (공유 태그: a, b)"` 형식 포함 (후보 있는 경우)
- [ ] 후보 없는 경우 `"연결 후보 없음 (공유 태그 없음)"` 표시 — E2E assertion으로 후보-없음 출력 경로 검증
- [ ] tags 비어있는 orphan → 후보 계산 불가, graceful 처리 (`candidates: []`, 에러 없음) — E2E에서 빈 tags orphan 케이스 커버
- [ ] gen-fixture E5 시드(`audit-e5-orphan-NNN.md`)에 공통 태그가 있는 다른 notes/ 파일 연결 가능하도록 시드 frontmatter 태그 확인 — 현재 `tags: [note]`로 공통 태그 존재, candidates 비어있지 않을 것
- [ ] `audit-validate.py --dod --findings` 출력에서 E5 finding의 `detail` 필드에 `"연결 후보"` 포함 여부 assertion (별도 스크립트 또는 수동 확인)

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| E10/E11 collect() 범위 | 현행: 숨김 디렉토리 `.`으로 시작하면 skip. E11은 canon-외 top-folder도 수집해야 함 | collect()는 현행 그대로 유지, classify()에서 분기 | collect()는 이미 canonical 외 폴더 파일도 수집함(`.`으로 시작하는 parts만 제외). classify()에서 top_folder 체크로 충분 |
| E11 루트 직속 파일 시드 방법 | (A) 루트에 `audit-e11-root-NNN.md` 작성 / (B) `20_Projects/audit-e11-NNN.md` | (A) 루트 직속 파일 + (B) 임의 폴더 둘 다 시드 | 두 케이스 모두 spec에 명시됨. 루트 직속은 E11 특유의 엣지 케이스 |
| E10 시드 파일 위치 | type:session을 notes/에 두는 방식 vs type:note를 inbox/에 두는 방식 | type:session을 notes/에 배치 | session→inbox 규칙이 직관적이고 E6(stale_inbox)와 간섭 없음 |
| E10/E11 SKILL.md 코드 번호 | E10/E11을 CLASSIFY 테이블에 추가, Severity/Priority 명시 | E10=P1/Warning, E11=P1/Warning | 이슈 spec과 동일. 폴더 구조 위반은 무결성(P0)은 아니나 정체보다 심각(P1) |
| E5 tag 인덱스 구성 시점 | classify() 시작 시 전체 notes/ fm_records 선 인덱스 vs orphan 탐지 루프 내 즉석 계산 | classify() 시작 시 선 구성 | orphan 탐지 루프가 O(N²)이 되는 걸 방지. notes 수 수천 개 고려 |
| E3 suggested_filename의 slug 추출 | 현재 파일명에서 date prefix + type prefix 제거 / created 필드 우선 | 파일명 slug 추출(파일명이 truth) | created는 날짜만, slug는 사용자가 파일명으로 지정한 값이 정확 |
| `audit/SKILL.md` CLASSIFY 테이블 코드 범위 표기 | "8 types" → "10 types"로 description 업데이트 | description 업데이트 | skill description은 탐지 가능 error 수를 명시하므로 동기화 필요 |

## 슬라이스 순서

1. **S1 audit-validate.py 확장 (E3 제안 + E10/E11 신규 + E5 후보)** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/scripts/test/audit-validate.py` | 산출: `PRIORITY_BY_TYPE` 업데이트, `EXPECTED_FOLDER` 상수, `_compute_suggested_filename()` 함수, E3/E5/E10/E11 classify 블록, `SEED_PREFIXES` 업데이트 | 검증: `python3 audit-validate.py /tmp/sample-vault` 로컬 스모크

2. **S2 gen-fixture.sh 시딩 (E10/E11)** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/scripts/test/gen-fixture.sh` | 산출: `--with-audit-errors` 플래그에 E10 시드 5건(`notes/audit-e10-*`) + E11 시드 5건(`audit-e11-root-*` 루트 직속 + `20_Projects/audit-e11-*` 임의 폴더) 추가, **추가로 clean(비-에러) 영역 fixture 루트에 `_index.md` 시드**(E11 exempt 가드 회귀 커버, #129) + E5 시드에 공유 태그 보장(#130 candidates 비어있지 않게), 로그 업데이트 | 검증: 로컬 `bash gen-fixture.sh --with-audit-errors` 실행 → 파일 존재 확인 + 루트 `_index.md` 존재 확인

3. **S3 vault-audit-rules.md 레퍼런스 업데이트** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/reference/vault-audit-rules.md` | 산출: E3 섹션에 `suggested_filename` 계산 pseudocode 추가, E10/E11 섹션 신규 추가, Priority Mapping 테이블 E10/E11 행 추가 | 검증: Markdown 렌더링 확인(헤더·코드블록 구조)

4. **S4 audit/SKILL.md CLASSIFY 테이블 업데이트** → 바인딩: `executor` | 대상 파일: `obsidian-vault-manager/skills/audit/SKILL.md` | 산출: Phase 2 CLASSIFY 테이블에 E10/E11 행 추가 (Warning/P1), description의 "8 error types" → "10 error types" 업데이트, E5 찾기 설명에 "tag 기반 연결 후보" 언급 추가 | 검증: frontmatter valid YAML 확인

5. **S5 DoD 자가검증 실행** → 바인딩: `verifier` | 대상: 픽스처 생성 + `audit-validate.py --dod` 실행 | 산출: `seeded_detected.E10 ≥ 5`, `seeded_detected.E11 ≥ 5`, `fp_on_clean.E{10,11} == 0`, `priority_mismatches == []` 확인 | 검증: E2E 자가검증 섹션 명령 실행

## E2E 자가검증

```bash
# 기존 fixture 제거 후 재생성
rm -rf /tmp/ovm-fixture-audit-recheck
OVM_FIXTURE_DIR=/tmp/ovm-fixture-audit-recheck \
  bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors

# DoD 측정 실행
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod --findings

# E10/E11 시드 탐지 확인 (seeded_detected 필드)
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod | python3 -c "
import json, sys
d = json.load(sys.stdin)['dod']
sd = d['seeded_detected']
fp = d['fp_on_clean']
mm = d['priority_mismatches']
assert sd.get('E10_misplaced_file', 0) >= 5, f'E10 under-detected: {sd}'
assert sd.get('E11_unstructured_path', 0) >= 5, f'E11 under-detected: {sd}'
assert fp.get('E10_misplaced_file', 0) == 0, f'E10 FP on clean: {fp}'
assert fp.get('E11_unstructured_path', 0) == 0, f'E11 FP on clean: {fp}'
assert mm == [], f'priority mismatches: {mm}'
assert d['findings_missing_priority'] == 0, f'findings missing priority: {d[\"findings_missing_priority\"]}'
print('OK: E10/E11 seeded_detected pass, fp_on_clean=0, no priority mismatches')
"

# E3 제안 포함 확인
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --findings | python3 -c "
import json, sys
data = json.load(sys.stdin)
e3_findings = [f for f in data['findings'] if f['type'] == 'E3_filename_convention_violation' and 'audit-e3-' in f.get('path','')]
with_suggestion = [f for f in e3_findings if '권장 파일명' in f.get('detail', '')]
assert len(with_suggestion) > 0, f'E3 suggestions missing: {e3_findings}'
print(f'OK: E3 suggested_filename present in {len(with_suggestion)} findings')
"

# E5 연결 후보 포함 확인
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --findings | python3 -c "
import json, sys
data = json.load(sys.stdin)
e5_findings = [f for f in data['findings'] if f['type'] == 'E5_orphan_note' and 'audit-e5-' in f.get('path','')]
with_candidates = [f for f in e5_findings if '연결 후보' in f.get('detail', '')]
assert len(with_candidates) > 0, f'E5 candidates missing: {e5_findings}'
print(f'OK: E5 candidates present in {len(with_candidates)} findings')
"

# E5 structured candidates 필드 + graceful 처리 확인 (#130 Acceptance)
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --findings | python3 -c "
import json, sys
data = json.load(sys.stdin)
e5 = [f for f in data['findings'] if f['type'] == 'E5_orphan_note']
assert any('candidates' in f for f in e5), 'E5 structured candidates field missing'
for f in e5:
    c = f.get('candidates', [])
    assert isinstance(c, list), f'candidates not a list: {f}'
    for item in c:
        assert 'path' in item and 'shared_tags' in item, f'candidate missing keys: {item}'
print(f'OK: E5 candidates structured field present ({len(e5)} orphans; 빈 tags/후보없음 graceful)')
"

# 기존 E1–E8 seeded_detected 회귀 없음 확인 (기존 DoD 기준 유지)
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod | python3 -c "
import json, sys
d = json.load(sys.stdin)['dod']
sd = d['seeded_detected']
expected = {'E1_missing_frontmatter': 5, 'E2_missing_required_fields': 10,
            'E3_filename_convention_violation': 5, 'E4_broken_wikilink': 5,
            'E5_orphan_note': 5, 'E6_stale_inbox': 5, 'E7_stale_draft': 5}
for k, v in expected.items():
    assert sd.get(k, 0) >= v, f'{k} regression: expected >={v}, got {sd.get(k,0)}'
print('OK: E1-E8 regression clean')
"

# JSON 유효성 검사 (plugin.json, marketplace.json)
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null && echo "OK: plugin.json valid"

# SKILL.md frontmatter YAML 확인 (기본 구조 검사)
python3 -c "
import re
with open('obsidian-vault-manager/skills/audit/SKILL.md') as f:
    content = f.read()
assert content.startswith('---\n'), 'Missing frontmatter opening'
end = content.index('\n---\n', 4)
fm = content[4:end]
assert 'name:' in fm and 'description:' in fm and 'allowed-tools:' in fm, 'Missing required frontmatter keys'
print('OK: SKILL.md frontmatter valid')
"
```

- 통과 기준:
  - `seeded_detected.E10 ≥ 5`, `seeded_detected.E11 ≥ 5`
  - `fp_on_clean.E10 == 0`, `fp_on_clean.E11 == 0`
  - `priority_mismatches == []`
  - `findings_missing_priority == 0`
  - E3 finding 중 하나 이상 `detail`에 "권장 파일명" 포함
  - E5 finding 중 하나 이상 `detail`에 "연결 후보" 포함
  - E1–E8 기존 seeded_detected 회귀 없음

## 의존성 / 순서 주의

- **선행 goal 없음**: 이 G8은 완전 독립(wave=독립). E1/E2/E3/E4/E5/E6/E7/E8 현행 구현을 전제로 확장만 함
- **내부 슬라이스 순서**: S1(코드) → S2(fixture) → S3(ref doc) → S4(SKILL.md) → S5(DoD 검증). S2는 S1 완료 후 실행 가능(SEED_PREFIXES 확정 필요). S3/S4는 S1과 병렬 가능하나 S1 설계 확정 후 작성 권장
- **크로스청크 게이트 없음**: E9, E10, E11 번호 충돌 가능성 — 이슈 #119(E9c semantic synonym)와 번호 체계 확인 필요. E10/E11은 이슈 #128/#129에서 명시한 번호 사용
- **착수 조건**: 현재 `gen-fixture.sh --with-audit-errors` + `audit-validate.py --dod` 모두 정상 동작 확인 후 착수 권장 (`rm -rf /tmp/ovm-fixture-audit-recheck` 후 테스트)
- **주의**: `gen-fixture.sh`에 E11 루트 직속 파일(`audit-e11-root-NNN.md`) 추가 시 fixture dir 루트에 `.md` 파일이 생기므로, `collect()`의 숨김 디렉토리 필터 로직이 루트 직속 파일을 수집하는지 먼저 확인 필요 (현행 `vault.rglob("*.md")` → 수집함)
