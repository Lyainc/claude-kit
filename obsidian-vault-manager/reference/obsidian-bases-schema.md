# Obsidian Bases (.base) 스키마 레퍼런스

`base` 스킬이 생성하는 `.base` 파일의 문법과 예시예요. 공식 문서와 실행 검증 범위를 구분해요. 생성 뷰가 깨지면 실제 Obsidian 버전과 이 문서의 검증 기준을 대조하세요.

- **공식 문법 기준**: [Bases syntax](https://obsidian.md/help/bases/syntax), [Functions](https://obsidian.md/help/bases/functions). 공식 문서는 별도 “Bases 1.0” 스키마 버전을 명시하지 않아요.
- **재검증**: 2026-10-01에 공식 문서(`https://obsidian.md/help/bases/syntax`, `https://obsidian.md/help/bases/functions`)와 대조해 filters·views·날짜 함수 문법을 바로잡았어요 (#760). 이전 판은 존재하지 않는 `property.` 접두어를 규정해서 생성된 뷰가 전부 빈 표로 렌더됐어요.
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

`filters`는 `and` / `or` / `not` 아래에 **표현식 문자열 목록**을 중첩해서 써요. 표현식은 전부 YAML 문자열이에요. `file.hasTag("book")`처럼 그대로 써도 되지만, 따옴표로 시작하거나 `: `·` #`이 들어가면 YAML이 다르게 읽으니까 비교식은 공식 문서처럼 작은따옴표로 감싸는 게 안전해요.

property 참조 방식은 세 가지예요. `property.` 접두어는 **없어요**.

| 종류 | 문법 | 예시 |
|------|------|------|
| 노트 property (frontmatter) | `note.<key>` 또는 접두어 없는 `<key>` | `note.author`, `author` |
| 파일 property | `file.<name>` | `file.name`, `file.ext`, `file.mtime` |
| 수식 property | `formula.<name>` | `formula.price` |

접두어를 생략하면 note property로 해석돼요.

| 패턴 | 예시 | 의미 |
|------|------|------|
| 동등 비교 | `'note.type == "capture"'` | type이 capture인 노트 |
| 존재 확인 | `file.hasProperty("type")` | type property가 있는 노트 (type opt-in 가드) |
| 폴더 조건 | `file.inFolder("sources")` | sources/ 하위 파일 |
| 태그 조건 | `file.hasTag("book")` | book 태그가 붙은 파일 |
| 날짜 조건 | `'file.mtime > now() - "14d"'` | 최근 14일 안에 수정된 파일 |
| 논리 결합 | `and:` / `or:` / `not:` + 하위 목록 | 모두 만족 / 하나 이상 / 부정 |

커스텀 조건도 type 가드와 최상위 `and`로 묶어요. 사용자 정의 `status`는 사용자가 명시한 값으로 비교할 수 있어요. #480에서 폐기한 것은 플러그인의 내장 상태 머신이며, 사용자 속성 조회를 금지한 것이 아니에요.

**날짜 함수**: `now()`, `today()`, `date("2024-12-01")`. duration 산술도 돼요 (`today() + "7d"`, `now() - "14d"`). 단위는 `y` / `M` / `d` / `w` / `h` / `m` / `s`예요.

**type opt-in 가드 (필수)**: 모든 필터는 `file.hasProperty("type")` 조건을 포함해야 해요. `type:` 없는 노트(다이어리·책 노트·자유 폴더)는 claude-kit 관리 대상이 아니므로 뷰에서 invisible 상태를 유지해야 하거든요 (v4 §2.2). 공식 문서에 있는 함수라서 `!= null` 비교 대신 이걸 써요.

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
    groupBy:             # 그룹화 (선택)
      property: note.type
      direction: DESC    # ASC | DESC
    limit: 100           # 표시 개수 제한 (선택)
```

view 옵션으로 `order` / `sort` / `groupBy` / `limit` / `summaries`를 쓸 수 있어요. 템플릿 3종은 `order`와 `sort`만 써요.

`order`는 표시할 컬럼의 순서이며 행 정렬과 구분해요. 공식 syntax 예시는 `order`와 `groupBy`를 문서화하지만 테이블의 `sort` 저장 형식은 나열하지 않아요. 위 `sort`는 기존 빌트인의 저장 형식이며 실제 앱의 Bases 질의로 검증해야 해요. 미지정 커스텀 정렬은 `sort` 자체를 생략하고, 정렬값이 없는 행을 임의로 제외하거나 추가 동률 정렬을 넣지 않아요.

## 빌트인 템플릿 3종

`base` 스킬이 제공하는 3종 뷰 — 각 필터는 B층 폴더 분할(v5 §5: 원문 `sources/`, 내가 쓴 것 `notes/`)과 정렬되고, `file.hasProperty("type")` opt-in 가드를 반드시 포함해요. status machine은 #480에서 폐기돼 필터 조건에서 빠졌어요.

### sources — sources/ 전체 (원문 그대로 보관한 자료)

```yaml
filters:
  and:
    - file.inFolder("sources")
    - file.hasProperty("type")
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
    - file.hasProperty("type")
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
        direction: DESC
```

### recent — 최근 저장한 것 전체 (폴더 무관)

```yaml
filters:
  and:
    - file.hasProperty("type")
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

## 커스텀 입력과 네 사용 사례 (#762)

자연어와 `--filter '<표현식>' [--sort '<속성>:ASC|DESC']`를 받아요. 최소 계약은 단일 필터 표현식과 선택적 단일 정렬 키예요. 표현식 안에서 `&&`, `||` 또는 아래처럼 YAML의 `and`/`or`를 사용해 조건을 결합할 수 있어요. 플래그는 텍스트로만 해석하며 셸로 실행하지 않아요.

속성·조건·필요한 값이 없거나 모순되면 질문하고 답변을 기다려요. 존재 조건에는 비교 값이 필요하지 않아요. “오래된 것”만으로 기간이나 속성을 추측하지 않고, “status_since 오름차순”이면 날짜 하한을 추가하지 않아요. 정렬 요청이 없으면 생략하지만 요청이 있으면 속성과 방향을 확인해요. 잘못된 템플릿·플래그·표현식·정렬 방향, 중복 플래그도 질문 대상이에요. 내장 템플릿과 커스텀 필터가 혼용되면 AND 결합할지 커스텀 뷰로 전환할지 먼저 질문해요.

네 예시는 사용자가 확인한 이슈 조건을 그대로 사용해요. `track != null` / `related != null`은 **값 비교**이며 키 존재 확인인 `file.hasProperty(...)`와 바꾸어 쓰지 않아요. 누락·명시적 null·빈 문자열의 세부 의미는 공식 문서만으로 같다고 단정하지 말고 실제 앱에서 확인하세요. type opt-in은 언제나 `file.hasProperty("type")`예요.

### 업무 항목 전체

자연어: `/base work 업무 항목: track이 null이 아닌 것`. 플래그: `/base work --filter 'track != null'`.

```yaml
filters:
  and:
    - 'file.hasProperty("type")'
    - 'track != null'
views:
  - type: table
    name: "업무 항목 전체"
    order:
      - file.name
      - track
```

### 오래 안 움직인 것

자연어: `/base waiting status가 대기 또는 진행중인 것을 status_since 오름차순으로`. 플래그: `/base waiting --filter '(status == "대기" || status == "진행중")' --sort 'status_since:ASC'`. 문자열 OR 또는 아래 재귀 OR는 같은 조건이며, type 가드가 OR 밖에 있어야 해요.

```yaml
filters:
  and:
    - 'file.hasProperty("type")'
    - or:
        - 'status == "대기"'
        - 'status == "진행중"'
views:
  - type: table
    name: "오래 안 움직인 것"
    order:
      - file.name
      - status
      - status_since
    sort:
      - property: status_since
        direction: ASC
```

완료·보류 등의 값은 위 두 값에 해당하지 않아 제외돼요. `status_since`가 없는 행도 상태 조건을 만족하면 포함하며, 누락값 위치와 동률 순서는 Obsidian 동작에 따라요.

### 산출물 없는 것

자연어: `/base no-output output_at이 "없음"인 것`. 플래그: `/base no-output --filter 'output_at == "없음"'`. 속성 누락을 문자열 “없음”과 같다고 추측하지 않아요.

```yaml
filters:
  and:
    - 'file.hasProperty("type")'
    - 'output_at == "없음"'
views:
  - type: table
    name: "산출물 없는 것"
    order:
      - file.name
      - output_at
```

### 업무별 문서

자연어: `/base work-docs related가 null이 아닌 문서`. 플래그: `/base work-docs --filter 'related != null'`. 이 예시에 특정 업무 값이나 그룹화를 임의로 추가하지 않아요.

```yaml
filters:
  and:
    - 'file.hasProperty("type")'
    - 'related != null'
views:
  - type: table
    name: "업무별 문서"
    order:
      - file.name
      - related
```

작성 전 실제 대상 경로·전체 YAML·필터와 정렬 설명을 보여주고 확인을 기다려요. 기존 노트나 뷰를 읽어서 속성·값을 추론하지 않아요. YAML 파싱 성공이나 파일 생성만으로 렌더 성공을 주장하지 않으며, 실제 Obsidian에서 포함·제외·정렬을 확인하지 못했다면 미검증으로 표시해요. 빈 표는 데이터가 없을 수도, 조건이 맞지 않을 수도 있어요.

## 파일명·경로 규칙

- 경로: `notes/{view-name}.base` (또는 사용자 지정 sub-folder).
- 파일명: `{view-name}.base`, `{lowercase-kebab}` 형태.
- pre-write-guard `notes/` 패턴이 `^[a-z0-9][a-z0-9-]*(-v[0-9]+)?\.(md|base)$`로 `.base`를 허용해요 (#118).
- 동일 stem 충돌 시 `-v2`, `-v3` 증가.
