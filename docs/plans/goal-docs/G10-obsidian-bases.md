---
goal_id: G10
title: Obsidian Bases (.base) 뷰 생성
issues: [118]
wave: 독립
depends_on: []
recommended_model: sonnet
status: ready
created: 2026-06-03
---

# G10 — Obsidian Bases (.base) 뷰 생성

## 배경 / 목적

obsidian-vault-manager(OVM)는 `type` / `tags` / `status` / `created` frontmatter를 모든 관리 대상 노트에 강제해요(v4 §2.2 type opt-in, audit E1·E2). 이 일관된 스키마 위에 Obsidian Bases(`.base` 파일)를 올리면 MOC를 손으로 유지하지 않아도 live, non-destructive 뷰를 즉시 얻을 수 있어요.

kepano(Obsidian 제작자)가 실제로 이 방식을 써요. 폴더 계층 대신 `categories` property 기준의 Bases dynamic view로 vault를 항법해요. `.base` 파일은 source note를 전혀 수정하지 않는 순수 YAML 정의 파일이에요. table / cards / list / map 뷰 + filter(tag/folder/property/date) + formula + summary(Sum/Avg 등)를 지원해요.

현재 OVM은 v4 §9.5에서 MOC 별도 type 슬롯을 거부했는데, `.base` view는 그 대안을 자동화·구조화하면서 **new-file-only 원칙을 하나도 깨지 않아요** — `.base`는 새 파일이고, 기존 노트를 절대 덮어쓰지 않아요.

## 포함 이슈

- #118: feat(ovm): generate Obsidian Bases (.base) views from enforced frontmatter — 신규 `/base` 스킬 + 3종 기본 템플릿 + pre-write-guard `notes/` 패턴 확장 + 회귀 테스트 추가

## 완료 조건 (Definition of Done)

- [ ] `/base {view-name}` 실행 시 `notes/{view-name}.base` 신규 생성되고, 기존 `.md` 노트는 무수정
- [ ] 파일 충돌 시 `-v2`, `-v3` suffix 자동 부여 (덮어쓰기 금지, 기존 `note` 스킬 패턴 일치)
- [ ] 3종 기본 템플릿 생성 가능:
  - `inbox-raw` — `inbox/` 폴더에서 `status: raw` 필터
  - `draft-notes` — `notes/` 폴더에서 `status: draft` 필터 + `created` 기준 내림차순 sort
  - `evergreen` — `notes/` 폴더에서 `status: evergreen` 필터
- [ ] 각 템플릿의 `.base` 필터에 `type:` 조건이 포함되어 `type:` 없는 노트는 뷰에서 자동 제외
- [ ] `obsidian-vault-manager/skills/base/SKILL.md` 신규 생성 (frontmatter 포함, CLAUDE.md SKILL.md 구조 준수)
- [ ] `vault-knowledge-manager` agent `skills:` frontmatter에 `base` 등록
- [ ] `obsidian-vault-manager/.claude-plugin/plugin.json` `keywords`에 `base`, `obsidian-bases` 추가 + version 범프
- [ ] `/.claude-plugin/marketplace.json` 해당 플러그인 항목 version/description/keywords 동기화
- [ ] `vault-bridge/hooks/pre-write-guard.sh` `notes/` 패턴을 `\.(md|base)$`로 확장 (A안)
- [ ] `vault-bridge/scripts/test/test-pre-write-guard.py`에 `.base` 케이스 최소 2개 추가:
  - `case_notes_base_valid_filename` — `notes/{slug}.base` → exit 0, stdout empty
  - `case_notes_base_violation_strict` — `notes/MyBase.base` + `VAULT_BRIDGE_STRICT_NAMING=1` → exit 2
- [ ] 회귀 테스트 전 케이스 green: `python3 vault-bridge/scripts/test/test-pre-write-guard.py` (현재 16개 + 신규 2개 = 18개)
- [ ] `reference/obsidian-bases-schema.md` 신규 생성 — 사용된 `.base` YAML 스키마 버전 명기 + 템플릿 3종 인라인 수록
- [ ] pre-write-guard `bash -n` 문법 검사 통과: `bash -n vault-bridge/hooks/pre-write-guard.sh`
- [ ] JSON 유효성 검사 통과: `python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null`
- [ ] JSON 유효성 검사 통과: `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null`

## 쟁점과 트레이드오프

| 쟁점 | 선택지 | 권장 | 근거 |
|------|--------|------|------|
| pre-write-guard `notes/` 패턴 확장 방식 | A안: `notes/` 패턴을 `\.(md\|base)$`로 확장 / B안: 상단 whitelist에 `*.base` glob 전역 추가 | A안 | 범위가 `notes/`로 한정되어 의도가 명확하고 `inbox/`에 `.base` 실수 쓰기를 방어할 수 있어요 |
| `.base` 생성 위치 스킬 | 신규 `skills/base/SKILL.md` vs 기존 `note` 스킬에 `--base` 플래그 추가 | 신규 스킬 | scope가 명확하고 `note` 스킬의 흐름(confirm-then-write)과 `.base` 생성 흐름이 달라요. 이슈 #118도 신규 스킬 선호 |
| vendor lock-in 긴장 | `.base` 파일 생성 / `.base` 파일 생성 안 함 | opt-in 생성 (사용자 명시 요청 시만) | `.base`는 부가 뷰이며 원본 `.md`는 100% 이식 가능 — 뷰가 깨져도 노트는 안 깨져요. opt-in으로 방어 |
| Bases YAML 스키마 안정성 | 템플릿 하드코드 / `reference/` 에 버전 명기 | `reference/obsidian-bases-schema.md` 버전 명기 | Bases는 2026년 신규 기능 — 스키마 변경 시 어느 버전 기준인지 추적 가능해야 해요 |
| MOC whitelist 정리 (`_index.md`, `moc-*.md`) | 이 PR에서 함께 제거 / 별도 cleanup issue | 별도 issue | 이 G10 스코프 밖이에요. 제거하면 기존 `moc-*.md` 파일 쓰기가 갑자기 막힐 수 있어요 — 안전하게 분리해요 |

## 슬라이스 순서

1. **S1 pre-write-guard 패턴 확장 + 회귀 테스트** → 바인딩: executor | 대상 파일: `vault-bridge/hooks/pre-write-guard.sh` (line 163 `notes/` 패턴), `vault-bridge/scripts/test/test-pre-write-guard.py` | 산출: `notes/` 패턴 `\.(md|base)$` 확장, `.base` 케이스 2개 추가(16→18개) | 검증: `bash -n vault-bridge/hooks/pre-write-guard.sh` + `python3 vault-bridge/scripts/test/test-pre-write-guard.py`

2. **S2 `.base` 스키마 레퍼런스 문서** → 바인딩: executor | 대상 파일: `obsidian-vault-manager/reference/obsidian-bases-schema.md` (신규) | 산출: 사용 중인 Obsidian Bases YAML 스키마 버전 + 3종 템플릿(`inbox-raw`, `draft-notes`, `evergreen`) YAML 본문 수록 | 검증: 파일 존재 확인 + `.base` YAML 구조 사람이 리뷰

3. **S3 `/base` 스킬 SKILL.md 작성** → 바인딩: executor | 대상 파일: `obsidian-vault-manager/skills/base/SKILL.md` (신규) | 산출: frontmatter(`name: base`, `model: sonnet`, `allowed-tools: Read Write Bash`) + 3종 템플릿 파라미터 파싱 + 충돌 시 `-v2` suffix 로직 + new-file-only 보존 + S2 `reference/obsidian-bases-schema.md` 참조 | 검증: `find obsidian-vault-manager/skills -name "SKILL.md" | sort` 목록에 `base/SKILL.md` 포함

4. **S4 vault-knowledge-manager 에이전트 + 매니페스트 동기화** → 바인딩: executor | 대상 파일: `obsidian-vault-manager/agents/vault-knowledge-manager.md` (`skills:` frontmatter에 `base` 추가), `obsidian-vault-manager/.claude-plugin/plugin.json` (`keywords` + version 범프), `.claude-plugin/marketplace.json` (해당 플러그인 version/keywords 동기화) | 산출: agent가 `/base` 스킬을 인식하는 상태 | 검증: `python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null` + `python3 -m json.tool .claude-plugin/marketplace.json > /dev/null` + version sync 확인

5. **S5 code-review** → 바인딩: code-reviewer | 대상 파일: S1-S4 전체 변경 diff | 산출: CRITICAL/WARNING 항목 목록 | 검증: CRITICAL 0건 확인 후 완료

## E2E 자가검증

```bash
# 1. pre-write-guard 문법 체크
bash -n vault-bridge/hooks/pre-write-guard.sh

# 2. pre-write-guard 회귀 (16 → 18케이스)
python3 vault-bridge/scripts/test/test-pre-write-guard.py
# 기대: OK: all cases passed

# 3. 신규 스킬 파일 존재 확인
find obsidian-vault-manager/skills -name "SKILL.md" | sort
# 기대: base/SKILL.md 포함

# 4. reference 문서 존재 확인
ls obsidian-vault-manager/reference/obsidian-bases-schema.md

# 5. JSON 유효성 검사
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null && echo "plugin.json OK"
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "marketplace.json OK"

# 6. version sync 확인 (plugin.json vs marketplace.json)
python3 -c "
import json
p = json.load(open('obsidian-vault-manager/.claude-plugin/plugin.json'))
m = json.load(open('.claude-plugin/marketplace.json'))
ovm = next(x for x in m['plugins'] if x['name'] == 'obsidian-vault-manager')
assert p['version'] == ovm['version'], f'version mismatch: {p[\"version\"]} vs {ovm[\"version\"]}'
assert 'base' in p['keywords'], 'base keyword missing from plugin.json'
assert 'base' in ovm['keywords'], 'base keyword missing from marketplace.json'
print('version sync OK')
"

# 7. agent skills frontmatter 확인
python3 -c "
txt = open('obsidian-vault-manager/agents/vault-knowledge-manager.md').read()
assert '- base' in txt or 'base' in txt, 'base not registered in agent skills'
print('agent registration OK')
"

# 8. 기존 전체 회귀 (기타 vault-bridge 테스트 영향 없음 확인)
python3 vault-bridge/scripts/test/test-discover.py
python3 vault-bridge/scripts/test/test-pre-access-guard.py
python3 vault-bridge/scripts/test/test-manifest-type-optin.py
```

- 통과 기준: 모든 명령 exit 0, "OK: all cases passed" 출력, version sync 스크립트 정상 종료

## 의존성 / 순서 주의

- **이슈 #118이 언급한 #104 의존성**: #104(vault-bridge slim)는 이미 완료 상태(vault-bridge v2.0.0, `auto_capture` 제거 완료). Write Role Contract 경계 확정되어 있어 G10 착수에 블로커 없어요.
- **슬라이스 내부 순서**: S1(pre-write-guard 패턴 확장)을 먼저 완료해야 S3(스킬)이 생성하는 `.base` 파일이 naming violation 경고 없이 통과해요. S2는 S1과 병렬 가능. S4는 S3 완료 후 진행해요.
- **크로스청크 게이트**: 없음 — `depends_on: []`, wave=독립. 다른 goal-doc과 파일 충돌 없어요.
- **MOC whitelist 정리** (`_index.md`, `moc-*.md`): 이 G10 스코프에서 제외. 별도 cleanup issue로 분리해요.
