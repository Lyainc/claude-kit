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

vault-searcher auto-selects the appropriate mode based on natural language requests:

### 1. Handoff Restore

Load the most recent active handoff note to restore session context.

```
"이전 handoff 불러와"
"megabox-auto-booking 진행 상황"
"지난번 어디까지 했지?"
```

### 2. Domain Context Load

Load MOC and related notes for a specific domain.

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

Create a structured handoff note for the next session to resume.

```
"handoff 생성해줘"
"다음 세션 준비"
"인수인계 노트 만들어"
"handoff 생성해줘 --quick"
"handoff 생성해줘 --hours 3"
```

## Relationship with obsidian-vault-manager

| Direction | Plugin | Role |
| --- | --- | --- |
| Vault management | `obsidian-vault-manager` | Full vault management (notes, MOC, projects, inbox) |
| External access | `vault-reader` | Vault search + handoff I/O from external projects |

- vault-reader **never modifies or deletes existing vault files**. It can only create new handoff notes.
- For full vault management (note creation, MOC updates, inbox review), use `obsidian-vault-manager`.

## Notes

- 같은 날 여러 handoff를 생성하면 자동으로 `-v2`, `-v3` suffix가 붙습니다
- vault-searcher는 기존 vault 파일을 수정/삭제하지 않습니다. 새 handoff 노트 생성만 가능합니다

## Prerequisites

- `~/vault/` must contain an Obsidian vault
- Handoff restore works best when paired with `obsidian-vault-manager`'s wrapup/context/vault-daily integration
