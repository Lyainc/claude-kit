# vault-reader

Lightweight **Obsidian vault I/O plugin** for Claude Code. Access vault knowledge from external projects.

## Install

```bash
claude plugin install vault-reader@Lyainc-claude-kit
```

## Agent

| Agent | Model | Description |
| --- | --- | --- |
| `vault-searcher` | Haiku | Vault I/O agent — search notes, load domain context, restore/create session notes |

## Modes

vault-searcher auto-selects the appropriate mode based on natural language requests.

### 1. Session Restore

Load the most recent active session note to restore session context.

```
"이전 세션 불러와"
"megabox-auto-booking 진행 상황"
"지난번 어디까지 했지?"
```

### 2. Domain Context Load

Load MOC and related notes for a specific domain. Lightweight read-only version for external projects. For advanced filtering (`--exclude`, `--limit`), use `obsidian-vault-manager`'s `context` skill instead.

```
"vault에서 kubernetes 관련 노트 찾아줘"
"api-design 맥락 불러와"
```

### 3. Keyword Search

Search the entire vault by keyword.

```
"JWT 인증 설계 결정 기록 있어?"
"이전에 정리한 배포 파이프라인 문서"
```

### 4. Session Note Creation

Create a session note recording the current session's work. Supports three modes: **record** (past-focused summary), **handoff** (past + future plan), and **quick** (minimal).

```
"세션 정리해줘"
"작업 기록 남겨줘"
"session note 생성"
"세션 노트 --quick"
"세션 저장 --hours 3"
```

## Relationship with obsidian-vault-manager

| Aspect | vault-reader | obsidian-vault-manager |
| --- | --- | --- |
| Use context | External project access | Internal vault management session |
| Write scope | Create new session notes only | Full note/MOC/project management |
| Role | Read-focused I/O | Full knowledge management |

- vault-reader **never modifies or deletes existing vault files**. It can only create new session notes.
- For full vault management (note creation, MOC updates, inbox review), use `obsidian-vault-manager`.

## Notes

- Multiple session notes on the same day auto-increment with `-v2`, `-v3` suffixes
- Session end triggers automatic suggestion to create a session note (Stop hook)

## Prerequisites

- `~/vault/` must contain an Obsidian vault

## License

MIT
