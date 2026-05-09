# Note ↔ Project 양방향 바인딩 레퍼런스

W7 구현 기준. `_index.md` 스키마, 필드 사전, Dataview 쿼리, 양방향 링크 감사 규약을 정의합니다.

---

## 1. `_index.md` 스키마

### 최소 템플릿 (생성 시 6필드 필수)

```yaml
---
created: YYYY-MM-DD
tags: [project, {name}]
type: project
status: active
domain: [{domain1}]
auto_capture: false  # 생성 시 AskUserQuestion으로 묻고 명시 기입 (기본 No)
---
# {Project Name}
## Overview
## Goals
## Outputs
## Related Notes
```

### 점진 enrichment 템플릿 (필요 시점에 추가)

```yaml
---
created: YYYY-MM-DD
tags: [project, {name}]
type: project
status: active
domain: [{domain1}, {domain2}]
auto_capture: true
last_session: 20_Projects/{name}/session-YYYY-MM-DD.md
vault_link_source: /abs/path/to/code-repo
absorbs:
  - 30_Notes/{origin-topic}.md
related_notes:
  - 30_Notes/{topic-a}.md
  - 30_Notes/{topic-b}.md
related_plans:
  - 20_Projects/{name}/plan-YYYY-MM-DD-{topic}.md
---
```

---

## 2. 필드 사전

### Project `_index.md` 필드

| 필드 | 타입 | 기수 | 의미 | 예시 |
|------|------|------|------|------|
| `created` | date | 1 | 생성일 | `2026-04-18` |
| `tags` | array | 1..N | 태그 (`project` 필수 포함) | `[project, claude-kit]` |
| `type` | enum | 1 | 반드시 `project` | `project` |
| `status` | enum | 1 | `active \| paused \| completed \| archived` | `active` |
| `domain` | array | 1..N | 연관 MOC 도메인 | `[api, infra]` |
| `last_session` | path | 0..1 | 최신 세션 파일 (vault 루트 기준 상대 경로) | `20_Projects/foo/session-2026-04-15.md` |
| `vault_link_source` | abs-path | 0..1 | `.vault-link`와 연결된 코드베이스 절대 경로 (vault-bridge W0 연동) | `/Users/x/dev/prj/foo` |
| `absorbs` | array[path] | 0..N | 이 프로젝트가 승격된 기반 note (vault 루트 기준) | `[30_Notes/api-redesign.md]` |
| `related_notes` | array[path] | 0..N | 작업 중 참조하는 note | `[30_Notes/oauth.md]` |
| `related_plans` | array[path] | 0..N | 프로젝트 내부 `plan-*.md` 파일 | `[20_Projects/foo/plan-2026-04-16-api.md]` |
| `auto_capture` | bool | 1 | W8 자동 저장 opt-in (기본 `false`) | `false` |

### Note (`30_Notes/*.md`) 전용 필드

| 필드 | 타입 | 기수 | 의미 | 예시 |
|------|------|------|------|------|
| `promoted_to_project` | string | 0..1 | 이 note가 승격된 primary 프로젝트 이름 | `foo` |
| `also_related_projects` | array[string] | 0..N | 이 note가 추가 연관된 프로젝트들 | `[bar, baz]` |

---

## 3. Note → Project 승격 워크플로

`/project {name} --promote-from 30_Notes/{topic}.md` 실행 시:

1. `~/vault/20_Projects/{name}/_index.md` 생성 (최소 6필드 + `absorbs` 포함)
2. `_index.absorbs`에 `30_Notes/{topic}.md` 기입
3. 원본 note frontmatter에 `promoted_to_project: {name}` 추가 (다른 필드 보존)
4. `_index.md` body의 "Overview" 섹션을 note의 첫 문단으로 프리필
5. `Home.md` Active Projects 섹션에 링크 추가

### 승격 전후 예시

**Before — `30_Notes/api-redesign.md`**:
```yaml
---
created: 2026-04-10
tags: [note, api, architecture]
type: note
---
```

**After — `30_Notes/api-redesign.md`**:
```yaml
---
created: 2026-04-10
tags: [note, api, architecture]
type: note
promoted_to_project: api-gateway
---
```

**생성됨 — `20_Projects/api-gateway/_index.md`**:
```yaml
---
created: 2026-04-18
tags: [project, api-gateway]
type: project
status: active
domain: [api, architecture]
auto_capture: false
absorbs:
  - 30_Notes/api-redesign.md
---
# Api-Gateway
## Overview
{note의 첫 문단이 여기에 프리필됩니다}
## Goals
## Outputs
## Related Notes
```

---

## 4. Dataview 쿼리 예시

### 쿼리 1: 특정 프로젝트와 연관된 note 리스트

```dataview
TABLE created, tags
FROM "30_Notes"
WHERE contains(also_related_projects, "api-gateway")
   OR promoted_to_project = "api-gateway"
SORT created DESC
```

### 쿼리 2: Orphan note 찾기 (프로젝트 연결 없는 note)

```dataview
TABLE created, tags
FROM "30_Notes"
WHERE !promoted_to_project
  AND !also_related_projects
SORT created ASC
```

### 쿼리 3: 프로젝트 상태별 count

```dataview
TABLE length(rows) AS "개수"
FROM "20_Projects"
WHERE file.name = "_index"
GROUP BY status
```

---

## 5. 양방향 링크 감사 규약 (W2 preparation)

W2 (vault 감사 기능) 구현 시 아래 규약에 따라 링크 정합성을 검증합니다.

| 방향 | 표현 위치 | 검증 대상 |
|------|---------|---------|
| Project → Note | `_index.md` frontmatter `related_notes`, `absorbs` | 파일 존재 여부 (`~/vault/{path}` 실재) |
| Note → Project | `30_Notes/{topic}.md` frontmatter `promoted_to_project` 또는 `also_related_projects` | `~/vault/20_Projects/{name}/` 디렉토리 존재 여부 |
| Note → MOC | note body `[[10_MOC/{domain}]]` wiki-link | 기존 규약 유지 (MOC 파일 실재) |

### 감사 스크립트 패턴 (W2 참고용)

```bash
# Project → Note 링크 정합성 확인
# _index.md의 related_notes / absorbs 경로가 실제 존재하는지 확인
python3 - <<'EOF'
import os, re, glob

vault = os.path.expanduser("~/vault")
broken = []

for index_path in glob.glob(f"{vault}/20_Projects/**/_index.md", recursive=True):
    with open(index_path) as f:
        content = f.read()
    # 간단한 YAML 배열 항목 추출 (W2에서 완전한 YAML 파서로 교체 권장)
    for match in re.finditer(r'- (30_Notes/[^\n]+)', content):
        note_path = os.path.join(vault, match.group(1).strip())
        if not os.path.exists(note_path):
            broken.append((index_path, match.group(1).strip()))

for idx, note in broken:
    print(f"BROKEN: {idx} → {note}")
EOF
```

---

## 6. 기존 파일 마이그레이션 가이드

기존 `_index.md`가 최소 6필드를 충족하지 않는 경우, **자동 수정하지 않습니다** (`auto_capture` absent는 `false`로 해석). 아래 방법으로 점진 마이그레이션하세요:

```bash
# 특정 프로젝트에 domain 필드 추가
/project {name} --enrich domain=api

# related_notes 배열에 note 추가
/project {name} --enrich related_notes=30_Notes/oauth.md
```

또는 `_index.md`를 직접 열어 YAML frontmatter에 필드를 추가하세요. 기존 필드는 그대로 유지됩니다.
