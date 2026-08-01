# vault-bridge

**Obsidian vault ↔ external project bridge** plugin for Claude Code. Access vault knowledge from external projects, save reference material into it with `/vault-save`, and commit it with `/vault-commit`. Knowledge *compilation* (`/wiki`) and vault curation stay with obsidian-vault-manager.

> **Renamed from `vault-reader` (≤ v0.3.0) at v1.0.0.** The plugin's scope expanded beyond read-only search (session-note creation, vault I/O hooks), so the name now reflects the two-way bridge role. See [Migration](#migration-from-vault-reader) below.

## Install

```bash
claude plugin install vault-bridge@Lyainc-claude-kit
```

## Agent

| Agent | Model | Description |
| --- | --- | --- |
| `vault-searcher` | Haiku | Vault read/search agent (read-only since v1.9.0) — search notes, load domain context, restore session context |

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

Load MOC and related notes for a specific domain. Lightweight read-only version for external projects. For domain context within vault management sessions, use `obsidian-vault-manager`'s `vault-knowledge-manager` agent (OVM-internal, direct mdfind/grep) instead.

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

## Write Workflow

vault-searcher is read-only. Vault *content* writes are user-initiated slash commands executed inline in the main context — never a subagent (see [Write Role Contract](#write-role-contract)):

| Command | Plugin | Destination |
|---------|--------|-------------|
| `/vault-save` | **vault-bridge** | source text as-is → `~/vault/inbox/`, prose you wrote → `~/vault/notes/` |
| `/wiki` | obsidian-vault-manager | compiled AI-recall domain knowledge → `~/vault/wiki/` |

`/vault-save` is the single reference-material entry — it replaced OVM's `/capture` and `/note` in #480, when B stopped being a promotion pipeline and became a reference warehouse (v5 §5). It writes no `status:` field and always writes `provenance:`. A past-tense session summary is just a `/vault-save`; distilled session knowledge for later AI recall compiles to `/wiki` (`/save-session` was retired 2026-07-10, #331).

For committing vault changes to git, use vault-bridge's `/vault-commit`. Next-session handoff is no longer a vault-bridge command — see [Session Handoff](#session-handoff).

## Session Handoff

Next-session handoff is **no longer a vault-bridge command**. The `/handoff` command and its `resume.md` mechanism were retired in G26 (decision G25 D4); the handoff function — authoring a next-session continuation / START-PROMPT — now lives in the machine-level `session-close` skill, part of the owner's personal kit and **not shipped in this plugin**. Use `/vault-save` (or `/wiki` for compiled knowledge) to record a past-tense session into the vault; the next-session continuation is handled outside claude-kit.

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
      "path": "notes/claude-kit/plan-2026-04-18-vault-bridge-value-prop.md",
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

### `/vault-manifest-refresh` skill

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

`.vault-link` is a pointer file that binds a code repository to a specific vault project. When present, it scopes vault-searcher's domain-context (Mode 2) and session-restore (Mode 1) searches. It does **not** affect `/vault-save`, which always writes to `~/vault/inbox/` regardless of `.vault-link` (see [Write Workflow](#write-workflow)).

### Schema

**`.vault-link`** (commit this file):

```yaml
version: 1                          # optional; v1 assumed if absent
vault_path: notes/my-project  # required; relative to vault root
```

**Format constraint** — `.vault-link` and `.vault-link.local` are flat key:value YAML files. Do **not** wrap the body with `---` frontmatter delimiters; the parser treats the whole file as a single key:value scope and silently drops fields below the first `---` if any are present.

**`.vault-link.local`** (gitignore this file):

```yaml
vault_root: /Users/me/work-vault    # optional; overrides default ~/vault/
```

### Discovery

vault-searcher walks upward from CWD (git-style) until it finds `.vault-link`. The first file found is used. If `.vault-link.local` exists at the same level, its `vault_root` overrides the default `~/vault/`.

### Effect on vault-searcher modes and skills

| Surface | Without `.vault-link` | With `.vault-link` |
|---------|-----------------------|--------------------|
| **vault-searcher Mode 2 (Domain Context Load)** | Searches all of `~/vault/` | Searches only `{vault_root}/{vault_path}/` |

vault-searcher Mode 3 (Keyword Search) is unaffected by `.vault-link` scope. `/vault-save` always writes to `~/vault/inbox/`, `.vault-link` or not.

### Recovery

If the `vault_path` directory does not exist, vault-searcher checks `notes/` for candidates with edit distance ≤ 2 and asks the user to confirm. If no candidates are found, it falls back silently to full-vault scope and inbox save target.

### `/vault-link` skill

Create or update `.vault-link` in the current directory:

```
/vault-link
```

The skill scans `~/vault/notes/` and presents a selection list. For new projects, create the vault project note via `obsidian-vault-manager`'s `vault-knowledge-manager` agent first, then run `/vault-link` to bind it. It never auto-modifies `.gitignore` — only suggests adding `.vault-link.local` to it.

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to skip `.vault-link` discovery entirely (useful in CI or remote environments where the vault is not available).

## Write Role Contract

vault-bridge v1.5.0 introduced vault write governance; v1.9.0 narrows vault-searcher to read-only and restricts vault writes to slash commands executed in the main context (see [Write Role Policy](#write-role-policy) below).

### Permitted writes

| Target | File types |
|--------|-----------|
| `inbox/` | `session-*`, `capture-*` (new files only) |
| `notes/{project}/` | `session-*`, `capture-*`, `plan-*` (new files only, when `.vault-link` resolves to that project) |

### Forbidden writes

| Target | Reason |
|--------|--------|
| `notes/` from a subagent | Only the main-context `/vault-save` may create notes — the contract is about *who* writes, not which folder |
| Any existing file (overwrite) | Immutable vault contract — vault-bridge never modifies existing files |
| Any existing file (append) | Same as overwrite — existing content is never touched |
| `assets/` | Binary asset management belongs to obsidian-vault-manager |

### Same-date collision handling

If `capture-2026-04-18-{slug}.md` already exists, `/vault-save` tries `-v2`, `-v3`, … The existing file is never touched, and no confirmation is shown — it saves immediately.

## File Naming Convention

vault-bridge v1.5.0 adds a **PreToolUse hook** (`hooks/pre-write-guard.sh`) that validates filenames when Claude writes to `~/vault/` with the `Write` or `Edit` tool.

### Per-directory patterns

| Directory | Required pattern | Example |
|-----------|-----------------|---------|
| `inbox/` | `^(session\|capture)-YYYY-MM-DD[-topic][-vN].md$` | `session-2026-04-18.md`, `capture-2026-04-18-jwt-debug.md` |
| `notes/` | `^[a-z0-9-]+\.md$` (no date prefix) | `oauth-flow.md` |
| `notes/{project}/` | `^(session\|plan\|capture\|decision)-YYYY-MM-DD[-topic][-vN].md$` | `plan-2026-04-18-vault-bridge-value-prop.md` |

### Whitelist — always allowed

The following filenames pass unconditionally regardless of directory: `_index.md`, `Home.md`, `home.md`.

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

## Write Role Policy

vault-bridge v1.9.0 adds an explicit Write Role Policy enforced by `hooks/pre-write-guard.sh`. Vault writes must originate from the main context (user-initiated skills). Subagent vault writes — identified by a non-empty agent identifier in the `PreToolUse` payload — are **blocked by default** (or warned / disabled) per the `VAULT_BRIDGE_WRITE_CONTRACT` environment variable.

The guard covers `Write`, `Edit` **and `Bash`** (#381). On the Bash path it denies commands whose write *target* resolves inside the vault — redirections (`echo x > ~/vault/notes/x.md`, `>>`, fd-prefixed `2>`, the compound forms `&>` / `&>>` / `>&` / `>|`, heredocs), `mv`/`cp`/`tee`/`touch`/`mkdir`/`rm`/`sed -i`/`dd of=` — including GNU `-t` / `--target-directory=` destinations and targets relative to a preceding `cd ~/vault` — while every read passes (`grep -r x ~/vault`, `cat ~/vault/notes/x.md`, `cd ~/vault && git status`, `cp ~/vault/notes/x.md /tmp/` — the vault is the source there, not the target). `assets/` stays a passthrough.

**Threat model: an honest subagent, not an adversary.** Detection is static and command-position-based (same discipline as this repo's `scripts/subagent-git-guard.sh`), so indirection that carries the command as data — `eval`, `sh -c "…"`, backticks, `xargs`, `python3 -c "open(...).write()"` — is deliberately *not* defeated: catching it would cost false denials on ordinary reads, which is the worse failure for a read-delegation layer. The guard closes the realistic bypass a well-behaved agent would reach for; it is not a sandbox.

| Mode | Behavior | When |
|------|----------|------|
| `enforce` (default) | Emits `permissionDecision: deny` + a `systemMessage`; the subagent vault write is blocked | Default |
| `warn` | Injects a `systemMessage` warning; the write is allowed to proceed | `VAULT_BRIDGE_WRITE_CONTRACT=warn` |
| `off` | No check performed | `VAULT_BRIDGE_WRITE_CONTRACT=off` |

```bash
# Subagent vault writes are blocked by default (enforce mode).
# Relax to warn (log + allow):
VAULT_BRIDGE_WRITE_CONTRACT=warn claude

# Disable the policy check entirely
VAULT_BRIDGE_WRITE_CONTRACT=off claude
```

**Exempt paths**: Naming convention enforcement via `VAULT_BRIDGE_STRICT_NAMING` applies regardless of agent vs. main-context origin. No top-level folder is exempt from the Write Role Policy.

## Relationship with obsidian-vault-manager

| Aspect | vault-bridge | obsidian-vault-manager |
| --- | --- | --- |
| Use context | External project access | Internal vault management session |
| Write scope | `/vault-save` reference material (`inbox/`, `notes/`) + `.vault-link` binding + git commits (`/vault-commit`) | `/wiki` compilation + audit/views |
| Role | Cross-session bridge (read + git commit) | Full knowledge management |

- vault-bridge **never modifies or deletes existing vault content files** — `/vault-save` only creates new ones, and knowledge compilation (`/wiki`) belongs to obsidian-vault-manager.
- For vault curation (audit, Bases views, wiki compilation), use `obsidian-vault-manager`.

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to suppress all vault-bridge hooks (useful in CI or environments without a vault).

```bash
VAULT_BRIDGE_DISABLE=1 claude  # no vault-bridge hooks fire
```

## Notes

- Same-date collisions auto-increment with `-v2`, `-v3` suffixes
- **SessionStart hook** (`hooks/session-start-manifest.sh`): checks manifest staleness and regenerates `manifest.json` in the background. Never blocks session startup. (The Stop / SessionEnd session-lifecycle auto-hooks and the SessionStart resume auto-injection were removed in G24; the `/handoff` command + `resume.md` mechanism were retired in G26 — see [Session Handoff](#session-handoff).)
- **PreToolUse hook (Write/Edit/Bash)** (`hooks/pre-write-guard.sh`): validates vault file naming conventions (Write/Edit only) AND enforces the Write Role policy on all three tools — a subagent's `echo > ~/vault/x.md` / `mv` / `tee` is denied like a `Write` would be (#381), while vault reads (`grep`, `cat`, `cd … && git status`) pass untouched — vault writes must be user-initiated (main context, executed by skills). Subagent vault writes (any non-empty agent identifier in the PreToolUse payload) are blocked (default) or warned per `VAULT_BRIDGE_WRITE_CONTRACT` mode (default `enforce`, supports `warn` / `off`). Naming convention is log-only by default (`exit 0` always); set `VAULT_BRIDGE_STRICT_NAMING=1` to block non-conforming writes (`exit 2`)
- **`/vault-manifest-refresh` skill**: force-regenerate the vault manifest cache; reports result in Korean

## Session Auto-Commit

vault-bridge v1.4.0 adds `/vault-commit`, a skill that commits uncommitted vault changes to git with user approval.

### Purpose

When vault-bridge writes session notes, captures, or plan files to a git-tracked vault, those changes accumulate as uncommitted working tree modifications. `/vault-commit` surfaces this cleanly — showing a grouped diff summary, generating a descriptive commit message, and requiring explicit approval before touching git history.

### `/vault-commit` flow

1. Check `VAULT_BRIDGE_DISABLE=1` — skip with notice if set
2. Resolve vault root: `VAULT_BRIDGE_VAULT_ROOT` > `VAULT_BRIDGE_VAULT_PATH` (userConfig) > `~/vault`
3. Verify vault is a git repository (`git rev-parse --git-dir`) — stop with notice if not
4. Run `git status --porcelain` — stop with "nothing to commit" if clean
5. Analyze changed files: count by type (`session`, `capture`, `note`, `plan`); collect project names from `notes/{project}/`
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

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to suppress the `/vault-commit` skill. (The Stop-hook auto-suggestion of `/vault-commit` was removed in G24 — run `/vault-commit` manually when the vault has uncommitted changes.)

```bash
VAULT_BRIDGE_DISABLE=1 claude  # no vault-bridge hooks fire
```

## Skills

Migrated from `commands/*.md` to `skills/*/SKILL.md` in #94 — invocation (`/vault-link` etc.) and behavior are unchanged.

| Skill | Description |
|---------|-------------|
| `/vault-save` | Save reference material into the vault — source text as-is → `inbox/`, prose you wrote → `notes/`. Saves immediately, no confirmation, `provenance:` always written, no `status:` (#480) |
| `/vault-link` | Create or update `.vault-link` in CWD — bind the repository to a vault project |
| `/vault-manifest-refresh` | Force-regenerate `~/vault/.vault-bridge/manifest.json` — bypasses staleness check |
| `/vault-commit` | Commit uncommitted vault changes to git — shows diff summary, generates commit message, requires user approval |

## Configuration

vault-bridge exposes a `userConfig` field in `plugin.json` so you can set your vault location once in Claude Code's plugin settings:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vault_path` | string | `~/vault` | Absolute path to your Obsidian vault root. Exposed to hooks as `VAULT_BRIDGE_VAULT_PATH`. |

**Vault root resolution priority** (highest → lowest):

1. `VAULT_BRIDGE_VAULT_ROOT` env var — explicit runtime override (CI/scripts)
2. `VAULT_BRIDGE_VAULT_PATH` env var — set from `userConfig.vault_path` by Claude Code
3. `~/vault` — built-in default

Tilde (`~`) in either env var is expanded to `$HOME` automatically.

```bash
# Temporary override for a single session
VAULT_BRIDGE_VAULT_ROOT=/Volumes/Shared/vault claude

# Or set via plugin settings (persists across sessions):
# claude plugin config vault-bridge vault_path /Volumes/Shared/vault
```

## Prerequisites

- An Obsidian vault at your configured vault path (default `~/vault/`)
- [`jq`](https://jqlang.github.io/jq/) on PATH (used by hooks to parse JSON payloads)

## Migration from vault-reader

`vault-bridge` v1.0.0 supersedes `vault-reader` v0.3.0. Plugin name changed — existing installations must re-install under the new name. Vault data (`~/vault/`) is fully compatible; no file migration needed.

```bash
claude plugin uninstall vault-reader
claude plugin install vault-bridge@Lyainc-claude-kit
```

Behavior and trigger phrases are unchanged at the v1.0.0 migration boundary. The `vault-searcher` agent kept the same 4 modes (restore, domain context, keyword search, session-note creation) through v1.8.x; v1.9.0 narrowed it to 3 read-only modes (write operations moved to user-initiated slash commands, executed inline in main context).

If you reference the agent by qualified name in prompts or scripts, update `vault-reader:vault-searcher` → `vault-bridge:vault-searcher`.

## License

MIT
