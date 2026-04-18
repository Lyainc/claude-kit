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

## Vault Manifest

vault-bridge v1.2.0 introduces a manifest cache that compresses vault metadata into a single JSON file, enabling Claude to select target files before reading any content.

### Purpose

Without a manifest, loading vault context requires reading 20+ files at ~50 KB each (~1,000 KB total). With a manifest, Claude reads one ~25 KB index first and then reads only the relevant files — a **97% reduction** in token consumption for typical domain context loads.

### Schema

`~/vault/.vault-bridge/manifest.json`:

```json
{
  "generated_at": "2026-04-18T14:32:00+09:00",
  "vault_root": "/Users/Lyainc/vault",
  "schema_version": 1,
  "file_count": 142,
  "files": [
    {
      "path": "20_Projects/claude-kit/plan-2026-04-18-vault-bridge-value-prop.md",
      "type": "plan",
      "status": "active",
      "workstream": "W10",
      "tags": ["plan", "claude-kit", "vault-bridge"],
      "title": "W10 — vault-bridge Value Proposition & Enforcement",
      "summary": "Phase A manifest generator spec — token cost reduction via compressed metadata index.",
      "mtime": 1747612320,
      "size_bytes": 4820
    }
  ]
}
```

**Field rules**:

| Field | Source | Notes |
|-------|--------|-------|
| `path` | filesystem | Relative to `vault_root` |
| `type` | frontmatter `type` | `session/capture/note/project/plan`; `"unknown"` if absent |
| `status` | frontmatter `status` | Omitted when not present |
| `workstream` | frontmatter `workstream` | Omitted when not present |
| `tags` | frontmatter `tags` | Empty array if absent |
| `title` | first `# H1` in body | Filename stem fallback |
| `summary` | first body paragraph | Truncated at 200 chars |
| `mtime` | filesystem | Unix epoch (seconds) |
| `size_bytes` | filesystem | File size in bytes |

### Trigger strategy

The manifest is regenerated automatically via the **SessionStart hook** (`hooks/session-start-manifest.sh`) using mtime-based staleness detection:

| Condition | Action |
|-----------|--------|
| `manifest.json` absent | Full scan (generate from scratch) |
| Any vault file mtime > manifest mtime | Incremental update (changed files only) |
| `schema_version` mismatch | Full scan |
| `/vault-manifest-refresh` invoked | Full scan (`--force`) |

The hook runs the Python generator in the background (10 s kill guard). Session startup is never blocked.

### Token savings estimate

For a 142-file vault (typical):

| Approach | Files read | Estimated tokens |
|----------|-----------|-----------------|
| Full scan (no manifest) | 20 files × ~50 KB | ~25,000 tokens |
| Manifest-first | 1 manifest (~25 KB) + 3–5 target files | ~750–1,500 tokens |
| **Reduction** | | **~97%** |

### `/vault-manifest-refresh` command

Force-regenerate the manifest on demand:

```
/vault-manifest-refresh
```

Runs the generator with `--force`, bypassing the staleness check. Reports file count and elapsed time in Korean.

### Generator script

`scripts/generate-manifest.py` — Python 3, standard library only.

```bash
python3 vault-bridge/scripts/generate-manifest.py \
  --vault-root ~/vault \
  [--force] \
  [--out /custom/path/manifest.json]
```

stdout: `{"generated": 142, "updated": 3, "removed": 1, "elapsed_ms": 450}`

## Vault-Project Link

`.vault-link` is a pointer file that binds a code repository to a specific vault project. When present, it scopes Mode 2 searches and determines the Mode 4 save path automatically — zero user intervention required.

### Schema

**`.vault-link`** (commit this file):

```yaml
version: 1                          # optional; v1 assumed if absent
vault_path: 20_Projects/my-project  # required; relative to vault root
```

**`.vault-link.local`** (gitignore this file):

```yaml
vault_root: /Users/me/work-vault    # optional; overrides default ~/vault/
```

### Discovery

vault-searcher walks upward from CWD (git-style) until it finds `.vault-link`. The first file found is used. If `.vault-link.local` exists at the same level, its `vault_root` overrides the default `~/vault/`.

### Effect on Modes

| Mode | Without `.vault-link` | With `.vault-link` |
|------|-----------------------|--------------------|
| **2. Domain Context Load** | Searches all of `~/vault/` | Searches only `{vault_root}/{vault_path}/` |
| **4. Session Note Creation** | Saves to `~/vault/00_Inbox/` | Saves to `{vault_root}/{vault_path}/` |

Modes 1 and 3 are unaffected.

### Recovery

If the `vault_path` directory does not exist, vault-searcher checks `20_Projects/` for candidates with edit distance ≤ 2 and asks the user to confirm. If no candidates are found, it falls back silently to full-vault scope and Inbox save target.

### `/vault-link` command

Create or update `.vault-link` in the current directory:

```
/vault-link
```

The command scans `~/vault/20_Projects/` and presents a selection list. For new projects, it directs you to `obsidian-vault-manager`'s `/project` skill first. It never auto-modifies `.gitignore` — only suggests adding `.vault-link.local` to it.

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to skip `.vault-link` discovery entirely (useful in CI or remote environments where the vault is not available).

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
- **SessionStart hook** (`hooks/session-start-manifest.sh`): checks manifest staleness and regenerates `manifest.json` in the background. Never blocks session startup
- **SessionEnd hook**: auto-saves a quick-mode session-note as a safety net when meaningful work happened but the user exited without saving
- **`/save-session` command**: explicit user trigger that delegates to vault-searcher Mode 4 with full mode selection (record/handoff/quick)
- **`/vault-manifest-refresh` command**: force-regenerate the vault manifest cache; reports result in Korean

## Slash Commands

| Command | Description |
|---------|-------------|
| `/save-session` | Delegate to vault-searcher Mode 4 — full session note creation with mode selection (record/handoff/quick) |
| `/vault-link` | Create or update `.vault-link` in CWD — bind the repository to a vault project |
| `/vault-manifest-refresh` | Force-regenerate `~/vault/.vault-bridge/manifest.json` — bypasses staleness check |

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
