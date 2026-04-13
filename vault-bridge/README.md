# vault-bridge

**Obsidian vault ↔ external project bridge** plugin for Claude Code. Access vault knowledge from external projects and record session notes back into the vault.

> **Renamed from `vault-reader` (≤ v0.3.0) at v1.0.0.** The plugin's scope expanded beyond read-only search (session-note creation, Stop/SessionEnd hooks, `/save-session` command), so the name now reflects the two-way bridge role. See [Migration](#migration-from-vault-reader) below.

## Install

```bash
claude plugin install vault-bridge@Lyainc-claude-kit
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

Create a session note recording the current session's work. Three modes:

| Mode | When to use | Sections |
|------|------------|----------|
| `record` | No continuation work — past summary only | Summary, Done, Related Files, Reference Context |
| `handoff` | Next session will continue this work | All sections + Next Steps, In Progress, Blockers |
| `quick` | Minimal capture | Summary, Related Files (+ Next Steps if handoff) |

The agent uses **AskUserQuestion** at two points: mode selection (before drafting) and save confirmation (before writing).

```
"세션 정리해줘"
"작업 기록 남겨줘"
"session note 생성"
"세션 노트 --quick"
"세션 저장 --hours 3"
```

## Relationship with obsidian-vault-manager

| Aspect | vault-bridge | obsidian-vault-manager |
| --- | --- | --- |
| Use context | External project access | Internal vault management session |
| Write scope | Create new session notes only | Full note/MOC/project management |
| Role | Cross-session bridge (read + append) | Full knowledge management |

- vault-bridge **never modifies or deletes existing vault files**. It can only create new session notes.
- For full vault management (note creation, MOC updates, inbox review), use `obsidian-vault-manager`.

## Notes

- Filename: `session-YYYY-MM-DD.md` (type-first convention)
- Frontmatter: `created`, `tags: [session, {project}]`, `type: session`, `status: active` (handoff mode only)
- Same-date collisions auto-increment with `-v2`, `-v3` suffixes
- **Stop hook** (deterministic shell script `hooks/stop-check.sh`): silently checks the user's last message for session-closing keywords; injects a one-line `systemMessage` suggesting `/save-session` only when a closing signal is detected. No LLM call → no per-turn cost, no infinite-loop risk
- **SessionEnd hook**: auto-saves a quick-mode session-note as a safety net when meaningful work happened but the user exited without saving
- **`/save-session` command**: explicit user trigger that delegates to vault-searcher Mode 4 with full mode selection (record/handoff/quick)

## Prerequisites

- `~/vault/` must contain an Obsidian vault
- [`jq`](https://jqlang.github.io/jq/) on PATH (used by the Stop hook to parse the transcript JSONL)

## Migration from vault-reader

`vault-bridge` v1.0.0 supersedes `vault-reader` v0.3.0. Plugin name changed — existing installations must re-install under the new name. Vault data (`~/vault/`) is fully compatible; no file migration needed.

```bash
claude plugin uninstall vault-reader
claude plugin install vault-bridge@Lyainc-claude-kit
```

Behavior and trigger phrases are unchanged. The `vault-searcher` agent keeps the same 4 modes (restore, domain context, keyword search, session-note creation), the Stop hook still watches for closing keywords, and `/save-session` works identically.

If you reference the agent by qualified name in prompts or scripts, update `vault-reader:vault-searcher` → `vault-bridge:vault-searcher`.

## License

MIT
