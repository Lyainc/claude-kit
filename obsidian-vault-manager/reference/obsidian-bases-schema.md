# Obsidian Bases (.base) 스키마 레퍼런스

`base` 스킬이 생성하는 `.base` 파일의 YAML 스키마를 버전 고정(version-pin)하는 문서예요. Bases는 비교적 신규 기능(2026)이라 스키마가 바뀔 수 있어요. 생성 템플릿이 깨지면 이 문서의 핀 버전과 실제 Obsidian 버전을 대조하세요 (#118 Risk 완화).

- **핀 기준 스키마 버전**: Obsidian Bases 1.0 (2026 GA)
- **출처**: Obsidian Help — Bases (`https://help.obsidian.md/bases`), Bases syntax / filters / views. kepano vault 사용 사례(`https://stephango.com/vault`).
- **갱신 규칙**: Obsidian이 `.base` 스키마를 변경하면 이 문서의 키 표와 템플릿을 함께 갱신하고, `base` 스킬의 템플릿 YAML도 맞춰서 수정하세요.

## .base 파일이란

`.base`는 원본 `.md` 노트를 **전혀 수정하지 않는** 순수 YAML 정의 파일이에요. frontmatter property(`type` / `created` / `tags` / `provenance`) 기준으로 live·non-destructive 뷰(table / cards / list)를 만들어요. 폴더 계층 대신 property 기반 dynamic view로 vault를 항법하는 방식(kepano)을 자동화해요.

- **new-file-only**: `.base`는 항상 새 파일이고, 노트를 덮어쓰지 않아요. claude-kit의 new-file-only 원칙과 정합해요.
- **opt-in 뷰**: 부가 뷰일 뿐, 원본 `.md`는 100% 이식 가능해요. 뷰가 죽어도 노트는 안 죽어요.

## 최상위 키

| 키 | 필수 | 의미 |
|----|------|------|
| `filters` | 권장 | 어떤 노트를 뷰에 포함할지 결정하는 조건. `and` / `or` / `not` 중첩 가능. |
| `properties` | 선택 | property별 표시 설정(`displayName` 등). |
| `views` | 필수 | 뷰 목록. 각 뷰는 `type`(table/cards/list) + `name` + 선택적 `order`/`sort`/`limit`. |
| `formulas` | 선택 | 파생 컬럼 정의(계산식). 템플릿에서는 미사용. |

## filters 문법

property 비교는 `property.{key}` 형태로 참조해요. 함수형 비교를 씁니다.

| 패턴 | 예시 | 의미 |
|------|------|------|
| 동등 비교 | `property.type == "capture"` | type이 capture인 노트 |
| 함수 비교 | `property.type != null` | type property가 존재하는 노트 (type opt-in 가드) |
| 폴더 조건 | `file.inFolder("sources")` | sources/ 하위 파일 |
| 폴더 조건 | `file.inFolder("notes")` | notes/ 하위 파일 |
| 논리 결합 | `and: [...]` | 모든 하위 조건 만족 |

**type opt-in 가드 (필수)**: 모든 필터는 `property.type != null` 조건을 포함해야 해요. `type:` 없는 노트(다이어리·책 노트·자유 폴더)는 claude-kit 관리 대상이 아니므로 뷰에서 invisible 상태를 유지해야 하거든요 (v4 §2.2).

## views 문법

```yaml
views:
  - type: table          # table | cards | list
    name: "표시 이름"
    order:               # 표시할 컬럼 순서 (선택)
      - file.name
      - tags
      - created
    sort:                # 정렬 (선택)
      - property: created
        direction: ASC   # ASC | DESC
    limit: 100           # 표시 개수 제한 (선택)
```

## 빌트인 템플릿 3종

`base` 스킬이 제공하는 3종 뷰 — 각 필터는 B층 폴더 분할(v5 §5: 원문 `sources/`, 내가 쓴 것 `notes/`)과 정렬되고, `property.type != null` opt-in 가드를 반드시 포함해요. status machine은 #480에서 폐기돼 필터 조건에서 빠졌어요.

### sources — sources/ 전체 (원문 그대로 보관한 자료)

```yaml
filters:
  and:
    - file.inFolder("sources")
    - property.type != null
views:
  - type: table
    name: "Sources"
    order:
      - file.name
      - type
      - created
    sort:
      - property: created
        direction: DESC
```

### notes — notes/ 전체 (내가 쓴 서술, created 최신순)

```yaml
filters:
  and:
    - file.inFolder("notes")
    - property.type != null
views:
  - type: table
    name: "Notes"
    order:
      - file.name
      - type
      - tags
      - created
    sort:
      - property: created
        direction: ASC
```

### recent — 최근 저장한 것 전체 (폴더 무관)

```yaml
filters:
  and:
    - property.type != null
views:
  - type: table
    name: "Recent"
    order:
      - file.name
      - type
      - tags
      - created
    sort:
      - property: created
        direction: DESC
```

## 파일명·경로 규칙

- 경로: `notes/{view-name}.base` (또는 사용자 지정 sub-folder).
- 파일명: `{view-name}.base`, `{lowercase-kebab}` 형태.
- pre-write-guard `notes/` 패턴이 `^[a-z0-9][a-z0-9-]*(-v[0-9]+)?\.(md|base)$`로 `.base`를 허용해요 (#118).
- 동일 stem 충돌 시 `-v2`, `-v3` 증가.
