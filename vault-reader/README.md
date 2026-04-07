# vault-reader

Lightweight **Obsidian vault I/O plugin** for Claude Code. Access vault knowledge from external projects.

## Install

```bash
claude plugin install vault-reader@Lyainc-claude-kit
```

## Agent

| Agent | Model | Description |
| --- | --- | --- |
| `vault-searcher` | Haiku | Vault I/O agent — search notes, load domain context, restore/create handoff notes |

## Modes

vault-searcher auto-selects the appropriate mode based on natural language requests.

### 1. Handoff Restore

Load the most recent active handoff note to restore session context.

```
"이전 handoff 불러와"
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

### 4. Handoff Creation

Create a structured handoff note (forward-looking continuation plan) for the next session to resume. Complementary to `obsidian-vault-manager`'s `wrapup` skill (backward-looking session summary).

```
"handoff 생성해줘"
"다음 세션 준비"
"인수인계 노트 만들어"
"handoff 생성해줘 --quick"
"handoff 생성해줘 --hours 3"
```

## Relationship with obsidian-vault-manager

| Aspect | vault-reader | obsidian-vault-manager |
| --- | --- | --- |
| Use context | External project access | Internal vault management session |
| Write scope | Create new handoff notes only | Full note/MOC/project management |
| Role | Read-focused I/O | Full knowledge management |

- vault-reader **never modifies or deletes existing vault files**. It can only create new handoff notes.
- For full vault management (note creation, MOC updates, inbox review), use `obsidian-vault-manager`.

## Notes

- Multiple handoffs on the same day auto-increment with `-v2`, `-v3` suffixes
- Works best when paired with `obsidian-vault-manager`'s wrapup/context/vault-daily integration

## Prerequisites

- `~/vault/` must contain an Obsidian vault

## License

MIT
