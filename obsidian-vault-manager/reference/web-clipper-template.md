# Obsidian Web Clipper 템플릿 — vault v4

Obsidian Web Clipper 브라우저 확장으로 웹 페이지를 vault v4 형식으로 바로 저장하는 템플릿입니다. vault-bridge `/vault-save` 스킬과 동일한 frontmatter 규약(`type: capture`, `source: web-clipper`)을 따릅니다.

## 빠른 시작

1. [Obsidian Web Clipper](https://obsidian.md/clipper) 설치 (Chrome / Firefox / Safari)
2. **Settings → Web Clipper → Templates → Import** 클릭
3. 아래 JSON을 붙여넣기 → Import

## 템플릿 JSON

```json
{
  "schemaVersion": "0.1.0",
  "name": "vault v4 capture",
  "behavior": "create",
  "noteContentFormat": "{{content}}",
  "properties": [
    {
      "name": "created",
      "value": "{{date:YYYY-MM-DD}}",
      "type": "date"
    },
    {
      "name": "tags",
      "value": "capture, web",
      "type": "multitext"
    },
    {
      "name": "type",
      "value": "capture",
      "type": "text"
    },
    {
      "name": "source",
      "value": "web-clipper",
      "type": "text"
    },
    {
      "name": "url",
      "value": "{{url}}",
      "type": "text"
    },
    {
      "name": "title",
      "value": "{{title}}",
      "type": "text"
    }
  ],
  "noteNameFormat": "capture-{{date:YYYY-MM-DD}}-{{title|lower|replace: :-|truncate:40}}",
  "path": "inbox"
}
```

## 생성되는 노트 예시

파일: `inbox/capture-2026-05-26-how-llms-work-from-scratch.md`

```yaml
---
created: 2026-05-26
tags:
  - capture
  - web
type: capture
source: web-clipper
url: https://example.com/how-llms-work
title: How LLMs Work From Scratch
---

{Web Clipper가 추출한 본문}
```

> [!tip] 파일명 슬러그
> `|replace: :-` 필터가 공백을 하이픈으로 치환해 kebab-case 파일명을 생성합니다. Web Clipper **0.9.0 이상** 필요. 구버전이면 `"capture-{{date:YYYY-MM-DD}}-{{title|lower|truncate:40}}"` 단순형으로 변경하세요 (공백이 파일명에 그대로 남음).

> [!note] 비ASCII 제목 (한국어 등)
> `|lower|replace: :-` 필터는 비ASCII 문자를 제거하지 않아요. 한국어 제목은 파일명에 그대로 유지됩니다 — Obsidian과 macOS/Linux 파일시스템은 이를 정상 처리해요. ASCII 전용 파일명이 필요하다면 `noteNameFormat`에서 `{{title}}` 대신 URL 경로 기반 템플릿(예: `{{url|split:/|-2}}`)을 사용하세요.

## 주요 설정 설명

| 필드 | 값 | 설명 |
|------|----|------|
| `path` | `inbox` | vault root 기준 상대 경로. `~/vault/inbox/`에 저장. |
| `behavior` | `create` | 항상 새 파일 생성. 기존 파일 덮어쓰지 않음. |
| `type` | `capture` | **type opt-in 마커** — 이 필드가 있어야 claude-kit이 파일을 관리 대상으로 인식 (vault v4 §2.2). |
| `source` | `web-clipper` | `/vault-save` URL 캡처(`provenance: url-capture`)와 출처 구분. |
| `title` | `{{title}}` | 페이지 `<title>` 태그 값. frontmatter에 별도 저장해 검색 편의 제공. |

## `/vault-save`와 비교

| | `/vault-save <URL>` (vault-bridge) | Web Clipper |
|---|---|---|
| 트리거 | Claude Code 세션 내 명령 | 브라우저에서 직접 |
| 파서 | Defuddle CLI (H1 title 추출 포함) | 확장 내장 파서 |
| `source` 값 | `url-capture` | `web-clipper` |
| 인터넷 필요 | 필요 | 필요 |
| 태그 커스터마이즈 | topic 태그 자동 추출 | 템플릿 수동 편집 |

두 방식 모두 vault `/audit`의 E1–E12 검사 대상이 됩니다 (`type: capture` opt-in 기준).

## 커스터마이즈 팁

**도메인 태그 추가**
```json
{"name": "tags", "value": "[\"capture\", \"web\", \"research\"]", "type": "multitext"}
```

**본문 앞에 요약 callout 삽입**
```json
"noteContentFormat": "> [!info] 원문 요약\n> {{description}}\n\n{{content}}"
```

**저자 정보 추가**
```json
{"name": "author", "value": "{{author}}", "type": "text"}
```

## 버전 호환

`|replace: :-` 필터(공백→하이픈)와 `|lower|truncate:40` 필터는 Obsidian Web Clipper **0.9.0 이상**에서 동작합니다. 구버전이면 `noteNameFormat`을 `"capture-{{date:YYYY-MM-DD}}-{{title}}"` 단순형으로 변경하세요.

`tags` 프로퍼티는 `multitext` 타입으로 설정 시 Obsidian이 YAML 리스트(`tags:\n  - capture\n  - web`)로 자동 변환합니다. 문자열로 출력된다면 Web Clipper 버전을 업그레이드하세요.

`schemaVersion: "0.1.0"`은 Web Clipper **0.9.x** 템플릿 포맷입니다. 향후 1.x 릴리스에서 스키마 버전이 올라가면 Import 시 마이그레이션 안내가 표시됩니다 — 그 시점에 이 값을 업데이트하세요.
