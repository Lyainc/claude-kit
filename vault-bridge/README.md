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
| `vault-searcher` | Haiku | Vault I/O agent — search notes, load domain context, restore session, create session notes and artifacts (single vault write entry point) |

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

Search the entire vault by keyword. If Obsidian CLI is available and responsive, vault-searcher may use `obsidian search` as an indexed search path before falling back to manifest/mdfind/grep behavior.

```
"JWT 인증 설계 결정 기록 있어?"
"이전에 정리한 배포 파이프라인 문서"
```

### 4. Vault Write (session + artifact)

Create a new vault file — session notes, captures, or plan documents. vault-searcher is the **single entry point** for all vault writes; the main agent must never write to `~/vault/` directly. Three session modes:

| Mode | When to use | Sections |
|------|------------|----------|
| `record` | No continuation work — past summary only | Summary, Done, Related Files, Reference Context |
| `handoff` | Next session will continue this work | All sections + Next Steps, In Progress, Blockers |
| `quick` | Minimal capture | Summary, Related Files (+ Next Steps if handoff) |

The agent uses **AskUserQuestion** at every discrete choice: type/mode selection, path confirmation, same-date collision resolution, and final save confirmation. Free-form content (edit instructions) uses plain text.

```
"세션 정리해줘"
"작업 기록 남겨줘"
"session note 생성"
"세션 노트 --quick"
"세션 저장 --hours 3"
"capture 저장해줘"
"plan 파일 만들어줘"
```

## Optional Obsidian CLI integration

When `obsidian` is installed, registered in `PATH`, and the Obsidian app is running, vault-searcher may use `obsidian search query="..."` for indexed keyword searches. This is an optimization only: manifest-first loading and filesystem fallback remain the correctness path, and `.vault-link` scoped searches must preserve their project boundary.

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

## Write Role Contract

vault-bridge v1.5.0 formalizes vault-searcher as the **single entry point** for all vault writes from external projects.

### Permitted writes

| Target | File types |
|--------|-----------|
| `00_Inbox/` | `session-*`, `capture-*`, `plan-*` (new files only) |
| `20_Projects/{name}/` | `session-*`, `capture-*`, `plan-*` (new files only, when `.vault-link` resolves to that project) |

### Forbidden writes

| Target | Reason |
|--------|--------|
| `30_Notes/` | Note creation is exclusively handled by obsidian-vault-manager's `note` skill |
| Any existing file (overwrite) | Immutable vault contract — vault-bridge never modifies existing files |
| Any existing file (append) | Same as overwrite — existing content is never touched |
| `50_Archive/` | Archiving belongs to obsidian-vault-manager |
| `10_MOC/`, `Home.md`, system files | MOC management belongs to obsidian-vault-manager |

### Same-date collision handling

If `session-2026-04-18.md` already exists, vault-searcher tries `-v2`, `-v3`, … up to `-v9`. A collision `AskUserQuestion` is shown before creating `-v2` or higher. The existing file is never touched.

## Structured Error Protocol

When a vault write fails or is forbidden, vault-searcher returns a structured error block to the calling context. The main agent reads this and decides how to respond.

```
<vault-bridge-error>
kind: permission | path_invalid | convention_violation | name_collision | disabled
path: {attempted_path}
detail: {human-readable explanation}
suggestion: {alternative action}
</vault-bridge-error>
```

**Error kind reference**:

| kind | When | Example |
|------|------|---------|
| `permission` | Write target is in a forbidden zone | Tried to write `30_Notes/oauth.md` directly |
| `path_invalid` | `.vault-link` resolution failed completely, no fuzzy candidates | `vault_path` points to non-existent directory |
| `convention_violation` | Filename does not conform to the required pattern for that directory | `00_Inbox/random-file.md` (missing type prefix and date) |
| `name_collision` | All `-v2` through `-v9` suffixes are already taken | `session-2026-04-18-v9.md` already exists |
| `disabled` | `VAULT_BRIDGE_DISABLE=1` is set | Kill switch active |

## File Naming Convention

vault-bridge v1.5.0 adds a **PreToolUse hook** (`hooks/pre-write-guard.sh`) that validates filenames when Claude writes to `~/vault/` with the `Write` or `Edit` tool.

### Per-directory patterns

| Directory | Required pattern | Example |
|-----------|-----------------|---------|
| `00_Inbox/` | `^(session\|capture\|plan)-YYYY-MM-DD[-topic][-vN].md$` | `session-2026-04-18.md`, `capture-2026-04-18-jwt-debug.md` |
| `30_Notes/` | `^[a-z0-9-]+\.md$` (no date prefix) | `oauth-flow.md` |
| `20_Projects/{name}/` | `_index.md` or `^(session\|plan\|capture)-YYYY-MM-DD[-topic][-vN].md$` | `plan-2026-04-18-vault-bridge-value-prop.md` |
| `50_Archive/` | Any filename (warning logged for awareness) | — |
| `10_MOC/` | `MOC-*.md` pattern (whitelist only) | `MOC-api.md` |

### Whitelist — always allowed

The following filenames pass unconditionally regardless of directory: `_index.md`, `Home.md`, `home.md`, `MOC-*.md` (case-insensitive `MOC` prefix).

### Log-only vs strict mode

| Mode | Behavior | When |
|------|----------|------|
| **Log-only** (default) | `exit 0` always — injects a `systemMessage` warning; never blocks | Default |
| **Strict** | `exit 2` on violation — blocks the write tool call | `VAULT_BRIDGE_STRICT_NAMING=1` |

```bash
# Enable strict enforcement (blocks non-conforming vault writes)
VAULT_BRIDGE_STRICT_NAMING=1 claude
```

### Kill switch

`VAULT_BRIDGE_DISABLE=1` suppresses the pre-write-guard entirely (same kill switch as other vault-bridge hooks).

## Relationship with obsidian-vault-manager

| Aspect | vault-bridge | obsidian-vault-manager |
| --- | --- | --- |
| Use context | External project access | Internal vault management session |
| Write scope | New session notes, captures, plans in Inbox/Projects | Full note/MOC/project management |
| Role | Cross-session bridge (read + write) | Full knowledge management |

- vault-bridge **never modifies or deletes existing vault files**. It only creates new files.
- For full vault management (note creation, MOC updates, inbox review), use `obsidian-vault-manager`.

## Direct Access Guard

vault-bridge v1.3.0 adds a **PreToolUse hook** (`hooks/pre-access-guard.sh`) that detects when Claude directly reads vault files with `Read`, `Grep`, or `Glob` tools, bypassing the vault-searcher agent.

### Purpose

Direct file access skips the manifest-first approach that delivers [97% token savings](#token-savings-estimate). The guard makes this visible by emitting a soft notice whenever it happens — it never blocks the operation.

### Soft enforcement philosophy

- **Never blocks**: `exit 0` always. User workflow is never interrupted.
- **Informs only**: a `systemMessage` is injected into Claude's context suggesting vault-searcher as the more efficient path.
- **Counts silently**: each direct access increments a session counter at `/tmp/vault-bridge-session-{session_id}/direct-access-count`.
- **Reports at session end**: the SessionEnd hook reads the counter and appends a one-line note to the auto-saved session note.

### Counter file structure

```
/tmp/vault-bridge-session-{CLAUDE_SESSION_ID}/
  direct-access-count   # plain integer, total count for this session
  direct-access-log     # tab-separated: timestamp + tool + abs_path (debug)
```

`CLAUDE_SESSION_ID` from environment; falls back to `pid-{PID}` if absent. The directory is deleted at SessionEnd.

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to suppress all vault-bridge hooks including this guard (useful in CI or environments without a vault).

```bash
VAULT_BRIDGE_DISABLE=1 claude  # no vault-bridge hooks fire
```

## Notes

- Filename: `session-YYYY-MM-DD.md` (type-first convention)
- Frontmatter: `created`, `tags: [session, {project}]`, `type: session`, `status: active` (handoff mode only)
- Same-date collisions auto-increment with `-v2`, `-v3` suffixes
- **Stop hook** (deterministic shell script `hooks/stop-check.sh`): silently checks the user's last message for session-closing keywords; injects a one-line `systemMessage` suggesting `/save-session` only when a closing signal is detected. No LLM call → no per-turn cost, no infinite-loop risk
- **SessionStart hook** (`hooks/session-start-manifest.sh`): checks manifest staleness and regenerates `manifest.json` in the background. Never blocks session startup
- **SessionEnd hook** (chained `hooks/session-end-pre.sh` → prompt): the shell pre-hook collects all deterministic state — `.vault-link` presence + Layer 1 `auto_capture`, `_index.md` Layer 2 `auto_capture`, plan-doc candidates, direct-access counter, plan-doc-asked flag — and writes a JSON file. The prompt then makes the LLM-judgment calls (meaningful-work check, Summary composition, conditional sections) and writes the safety-net session-note. The shell step uses `${CLAUDE_PROJECT_ROOT:-$PWD}` so a session-internal `cd` does not break `.vault-link` discovery
- **PreToolUse hook (Read/Grep/Glob)** (`hooks/pre-access-guard.sh`): detects direct `Read`/`Grep`/`Glob` calls targeting `~/vault/`; emits a soft notice with vault-searcher as alternative; increments session counter; never blocks
- **PreToolUse hook (Write/Edit)** (`hooks/pre-write-guard.sh`): validates filenames when writing to `~/vault/`; emits a `systemMessage` warning on convention violation; log-only by default (`exit 0` always); set `VAULT_BRIDGE_STRICT_NAMING=1` to block non-conforming writes (`exit 2`)
- **`/save-session` command**: explicit user trigger that delegates to vault-searcher Mode 4 with full mode selection (record/handoff/quick)
- **`/vault-manifest-refresh` command**: force-regenerate the vault manifest cache; reports result in Korean

## Session Auto-Commit

vault-bridge v1.4.0 adds `/vault-commit`, a slash command that commits uncommitted vault changes to git with user approval.

### Purpose

When vault-bridge writes session notes, captures, or plan files to a git-tracked vault, those changes accumulate as uncommitted working tree modifications. `/vault-commit` surfaces this cleanly — showing a grouped diff summary, generating a descriptive commit message, and requiring explicit approval before touching git history.

### `/vault-commit` flow

1. Check `VAULT_BRIDGE_DISABLE=1` — skip with notice if set
2. Resolve vault root: `VAULT_BRIDGE_VAULT_ROOT` > `~/vault`
3. Verify vault is a git repository (`git rev-parse --git-dir`) — stop with notice if not
4. Run `git status --porcelain` — stop with "nothing to commit" if clean
5. Analyze changed files: count by type (`session`, `capture`, `note`, `plan`, `project`); collect project names from `20_Projects/{name}/`
6. Generate auto commit message: `"vault session YYYY-MM-DD: 2 plans, 1 note in claude-kit"`
7. **AskUserQuestion** with 3 options (approval required — no silent commit):
   - **이 메시지로 커밋**: use auto-generated message
   - **메시지 직접 입력 후 커밋**: freeform message input via second AskUserQuestion
   - **커밋 안 함**: no-op, exit cleanly
8. On approval: `git add -A && git commit -m "{msg}"`
9. Report result in Korean: `✓ 커밋됨: {hash} — {msg}` on success, stderr + manual action hint on failure

### Auto commit message examples

| Scenario | Generated message |
|----------|-------------------|
| One session note | `vault session 2026-04-18: 1 session-note` |
| Two plans + one note in a project | `vault session 2026-04-18: 2 plans, 1 note in claude-kit` |
| Mixed types, no clear project | `vault session 2026-04-18: 3 files` |

### Stop hook integration

The Stop hook (`hooks/stop-check.sh`) already suggests `/save-session` when a closing keyword (`세션 끝`, `wrap up`, etc.) is detected. With v1.4.0 it additionally checks whether the vault has uncommitted changes and, if so, appends a suggestion to run `/vault-commit` in the same `systemMessage`. This is fully deterministic (no LLM call) and adds negligible latency.

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to suppress both the `/vault-commit` command and the Stop hook's vault dirty check.

```bash
VAULT_BRIDGE_DISABLE=1 claude  # no vault-bridge hooks or commit suggestions fire
```

## Slash Commands

| Command | Description |
|---------|-------------|
| `/save-session` | Delegate to vault-searcher Mode 4 — full session note creation with mode selection (record/handoff/quick) |
| `/vault-link` | Create or update `.vault-link` in CWD — bind the repository to a vault project |
| `/vault-manifest-refresh` | Force-regenerate `~/vault/.vault-bridge/manifest.json` — bypasses staleness check |
| `/vault-commit` | Commit uncommitted vault changes to git — shows diff summary, generates commit message, requires user approval |

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
