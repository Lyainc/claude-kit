# Obsidian Web Clipper 템플릿 — vault v4

Obsidian Web Clipper 브라우저 확장으로 웹 페이지를 vault v4 형식으로 바로 저장하는 템플릿입니다. OVM `/capture` 스킬과 동일한 frontmatter 규약(`type: capture`, `source: web-clipper`)을 따릅니다.

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
      "value": "[\"capture\", \"web\"]",
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
  "noteNameFormat": "capture-{{date:YYYY-MM-DD}}-{{title|lower|truncate:40}}",
  "path": "inbox"
}
```

## 생성되는 노트 예시

파일: `inbox/capture-2026-05-26-how llms work from scratch.md`

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
> `noteNameFormat`의 `{{title|lower|truncate:40}}`는 소문자 변환 후 40자 제한을 적용합니다. 공백이 그대로 남으므로 Obsidian에서는 정상 동작하지만 파일시스템에 따라 공백이 보기 불편할 수 있어요. 공백 제거가 필요하면 파일명을 직접 편집하거나 아래 커스터마이즈 팁을 참고하세요.

## 주요 설정 설명

| 필드 | 값 | 설명 |
|------|----|------|
| `path` | `inbox` | vault root 기준 상대 경로. `~/vault/inbox/`에 저장. |
| `behavior` | `create` | 항상 새 파일 생성. 기존 파일 덮어쓰지 않음. |
| `type` | `capture` | **type opt-in 마커** — 이 필드가 있어야 claude-kit이 파일을 관리 대상으로 인식 (vault v4 §2.2). |
| `source` | `web-clipper` | OVM `/capture` URL 캡처(`url-capture`)와 출처 구분. |
| `title` | `{{title}}` | 페이지 `<title>` 태그 값. frontmatter에 별도 저장해 검색 편의 제공. |

## OVM `/capture`와 비교

| | `/capture <URL>` (OVM) | Web Clipper |
|---|---|---|
| 트리거 | Claude Code 세션 내 명령 | 브라우저에서 직접 |
| 파서 | Defuddle CLI (H1 title 추출 포함) | 확장 내장 파서 |
| `source` 값 | `url-capture` | `web-clipper` |
| 인터넷 필요 | 필요 | 필요 |
| 태그 커스터마이즈 | topic 태그 자동 추출 | 템플릿 수동 편집 |

두 방식 모두 vault `/audit`의 E1–E5 검사 대상이 됩니다 (`type: capture` opt-in 기준).

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

`{{title|lower|truncate:40}}` 필터는 Obsidian Web Clipper **0.9.0 이상**에서 동작합니다. 구버전이면 `noteNameFormat`을 `"capture-{{date:YYYY-MM-DD}}-{{title}}"` 단순형으로 변경하세요.
