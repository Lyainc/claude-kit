# obsidian-vault-manager

Claude Code용 **Obsidian vault 지식 관리 플러그인** (v4). 2개 에이전트 + 5개 스킬로 vault를 체계적으로 관리합니다.

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
| `audit` | vault 구조 무결성 감사 — E1-E11 오류 감지 (P0-P2 우선순위), stale 노트·promotion candidate 추적 |
| `wiki` | 작업 중 알게 된 도메인 지식을 `~/vault/wiki/` 페이지로 컴파일 (LLM wiki, AI recall용 A 레이어; 게이트된 명시 액션) |
| `base` | enforced frontmatter로 비파괴 Obsidian Bases(.base) 뷰 생성 — 기존 노트 불변, 내장 템플릿(inbox-raw/draft-notes/evergreen) |

## v4 파일 컨벤션

v4는 3-폴더 구조 (`inbox/`, `notes/`, `assets/`)와 `type:` 옵트인을 사용해요.

```yaml
---
created: YYYY-MM-DD          # 필수
tags: [{type}, {domain}]     # 필수
type: capture|note|decision|session|plan  # 필수 — type 없으면 claude-kit에 invisible
status: raw|draft|evergreen|archived      # note/decision 필수; session/capture 선택
---
```

**파일명 패턴**: `{type}-YYYY-MM-DD[-{topic}].md` (dated) / `{slug}.md` (evergreen note)

## Reference docs

- [Obsidian format reference](reference/obsidian-format.md): wikilinks, embeds, callouts, comments, and YAML property conventions for generated notes.
- [Obsidian CLI reference](reference/obsidian-cli.md): optional CLI-first patterns with raw file I/O fallback.
- [Web Clipper template](reference/web-clipper-template.md): Obsidian web clipper JSON template for `capture` type notes.
- [Vault audit rules](reference/vault-audit-rules.md): E1-E11 error taxonomy and P0-P2 priority definitions.

## 스킬 사용 예시

### `capture` — 즉시 inbox 저장

```
/capture 중요한 아이디어 메모
/capture https://example.com/article
```

`defuddle` CLI가 설치되어 있으면 URL에서 본문 Markdown을 추출해 `~/vault/inbox/capture-YYYY-MM-DD-{slug}.md`로 저장해요. 설치되어 있지 않거나 추출 실패 시 URL만 저장하고 흐름은 계속됩니다.

### `note` — evergreen 노트 생성

```
/note kubernetes networking basics
/note api-design --type decision
```

`~/vault/notes/` 에 `{slug}.md` (evergreen) 또는 `decision-YYYY-MM-DD-{slug}.md` 형태로 저장해요. `--type decision` 시 문제·선택지·결정·근거 4섹션 템플릿이 적용됩니다.

### `audit` — vault 무결성 감사

```
/audit
```

E1-E11 오류(frontmatter 누락, stale inbox/draft, promotion candidate 등)를 P0-P2 우선순위로 정렬해 보고해요. REPORT에 지난 7일 git 활동 요약도 포함됩니다.

## vault-bridge와의 관계

| 영역 | obsidian-vault-manager | vault-bridge |
| --- | --- | --- |
| 사용 맥락 | vault 관리 세션 내부 | 외부 프로젝트에서 vault 접근 |
| 쓰기 범위 | 노트 전체 생성·수정 (`inbox/`, `notes/`) | 새 session-note/capture/plan 생성만 (`inbox/`, `notes/{project}/`) |
| 도메인 컨텍스트 로드 | `vault-knowledge-manager` 에이전트 (OVM 내부, mdfind/grep 직접 접근) | `vault-searcher` Mode 2 (읽기 전용, 외부 접근용) |
| 세션 기록 | 해당 없음 (vault-bridge의 session-note 사용) | `/save-session` 슬래시 커맨드로 session-note 생성 (inline, main context) |

## 사전 요구사항

- `~/vault/` 경로에 Obsidian vault가 존재해야 합니다
- macOS 환경 권장 (vault 검색에 `mdfind` 사용, 미지원 시 `grep` fallback)

## 아키텍처

자세한 설계 문서는 [ARCHITECTURE.md](ARCHITECTURE.md) 참조.

## 라이선스

MIT
