# obsidian-vault-manager

Claude Code용 **Obsidian vault 지식 관리 플러그인**. 2개 에이전트 + 7개 스킬로 vault를 체계적으로 관리합니다.

## 설치

```bash
claude plugin install obsidian-vault-manager@Lyainc-claude-kit
```

## 포함된 에이전트

| Agent | Model | Description |
| --- | --- | --- |
| `vault-knowledge-manager` | Sonnet | 메인 에이전트 — 노트 생성, MOC 관리, 프로젝트 추적 |
| `vault-file-organizer` | Haiku | 경량 subagent — 파일 이동, 이름 변경, 아카이브 |

## 포함된 스킬

| Skill | Description |
| --- | --- |
| `capture` | 즉시 Inbox에 메모 저장 (`/capture 내용`); URL 입력 시 Defuddle CLI가 있으면 본문 Markdown 추출 |
| `note` | 새 노트 생성 + MOC 연결 + 프로젝트 연결 옵션 (`/note 주제`) |
| `project` | 프로젝트 생성 / 노트 승격 / 필드 enrichment (`/project 이름`) |
| `inbox-review` | Inbox 파일 일괄 정리 (분류/이동/삭제) |
| `context` | vault 내부 도메인 맥락 로드 (Explore fork); Obsidian CLI가 있으면 indexed search 우선 |
| `archive` | 완료 프로젝트 아카이브 + MOC/Home.md 정리; Obsidian CLI가 있으면 property:set 우선 |
| `vault-audit` | vault 구조 무결성 감사 (9-error taxonomy: orphans, broken wikilinks, filename, frontmatter, note↔project bidirectional) |

## `_index.md` 스키마 (W7)

### 최소 템플릿 (생성 시 6필드 필수)

```yaml
---
created: YYYY-MM-DD
tags: [project, {name}]
type: project
status: active
domain: [{domain}]
auto_capture: false  # 생성 시 AskUserQuestion으로 묻고 명시 기입 (기본 No)
---
```

### 점진 enrichment 필드 (필요 시점에 추가)

```yaml
last_session: 20_Projects/{name}/session-YYYY-MM-DD.md
vault_link_source: /abs/path/to/code-repo
absorbs:
  - 30_Notes/{origin-topic}.md
related_notes:
  - 30_Notes/{topic-a}.md
related_plans:
  - 20_Projects/{name}/plan-YYYY-MM-DD-{topic}.md
```

전체 필드 사전 및 Dataview 쿼리는 [reference/note-project-binding.md](reference/note-project-binding.md) 참조.

## Reference docs

- [Obsidian format reference](reference/obsidian-format.md): wikilinks, embeds, callouts, comments, and YAML property conventions for generated notes.
- [Obsidian CLI reference](reference/obsidian-cli.md): optional CLI-first patterns with raw file I/O fallback.
- [Note-project binding reference](reference/note-project-binding.md): `_index.md` field dictionary and Dataview query examples.

## 스킬 사용 예시

### `project` — Note → Project 승격

```
/project api-gateway --promote-from 30_Notes/api-redesign.md
```

- `20_Projects/api-gateway/_index.md` 생성 (최소 6필드 + `absorbs`)
- `30_Notes/api-redesign.md` frontmatter에 `promoted_to_project: api-gateway` 추가
- `Home.md` Active Projects 섹션 업데이트

### `project` — 기존 프로젝트 enrichment

```
/project api-gateway --enrich related_notes=30_Notes/oauth.md
```

### `capture` — URL 저장 with optional Defuddle

```
/capture https://example.com/article
```

`defuddle` CLI가 설치되어 있으면 `defuddle parse <url> --md` 결과를 Inbox 노트 본문에 함께 저장합니다. 설치되어 있지 않거나 추출에 실패하면 URL만 저장하고 capture 흐름은 계속됩니다.

### `note` — 프로젝트 연결 옵션

```
/note kubernetes networking basics
```

note 생성 시 `~/vault/20_Projects/` 를 스캔하여 관련 프로젝트가 있으면 연결 여부를 질문합니다. 선택하면 `also_related_projects` 필드가 frontmatter에 기록됩니다. "나중에 정할게" 선택 시 건너뜁니다.

### Note optional 필드

| 필드 | 설명 |
| --- | --- |
| `also_related_projects` | 이 note와 연관된 프로젝트들 (복수 가능) |
| `promoted_to_project` | 이 note가 승격된 프로젝트 (`/project --promote-from` 이 자동 설정) |

## vault-bridge와의 관계

| 영역 | obsidian-vault-manager | vault-bridge |
| --- | --- | --- |
| 사용 맥락 | vault 관리 세션 내부 | 외부 프로젝트에서 vault 접근 |
| 쓰기 범위 | 노트/MOC/프로젝트 전체 생성·수정·삭제 | 새 session-note 생성만 가능 |
| `context` vs `vault-searcher` | MOC 기반 도메인 로드 + `--exclude`/`--limit` 옵션 | MOC 기반 도메인 로드 (읽기 전용, 외부 접근용) |
| 세션 기록 | 해당 없음 (vault-bridge의 session-note 사용) | session-note 생성 (과거 기록 + 미래 계획 통합) |

## 사전 요구사항

- `~/vault/` 경로에 Obsidian vault가 존재해야 합니다
- macOS 환경 권장 (vault 검색에 `mdfind` 사용, 미지원 시 `grep` fallback)

## 아키텍처

자세한 설계 문서는 [ARCHITECTURE.md](ARCHITECTURE.md) 참조.

## 라이선스

MIT
