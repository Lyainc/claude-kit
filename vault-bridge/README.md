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

## Write Workflow (since v1.9.0)

vault-searcher is read-only. All vault writes route through user-initiated slash commands executed inline in main context. The session-note flow (`/save-session`) supports two modes:

| Mode | When to use | Sections |
|------|------------|----------|
| `record` | Past summary of completed work | Summary, Done, Related Files, Reference Context |
| `quick` | Minimal capture | Summary, Related Files |

For captures and plan documents, use `/save-plan-doc`. For committing vault changes to git, use `/vault-commit`. To hand work off to the next session, use `/handoff` (see [Session Handoff](#session-handoff)).

Use `/save-session` to trigger session note creation from the main context. The command handles type/mode selection, path confirmation, same-date collision resolution, and final save confirmation inline.

```
/save-session
"세션 정리해줘"
"작업 기록 남겨줘"
"session note 생성"
"세션 노트 --quick"
"세션 저장 --hours 3"
```

## Session Handoff

`/handoff` (vault-bridge v1.11.0) generates a continuation handoff for the next session — distinct from `/save-session`, which records a past-tense session note into the vault. `/handoff` summarizes the current work state and delivers it in one of three forms:

| Option | Delivery | Use when |
|--------|----------|----------|
| 복붙 한 줄 | One-line prompt printed to the terminal | Quick continuation, paste into the next session |
| 복붙 요약 | Structured summary printed to the terminal | Richer context, paste into the next session |
| 파일 저장 | `resume.md` written to `.claude-kit/vault-bridge/` | Hands off automatically — no copy-paste |

`/save-plan-doc` run with the "다음 세션으로" (defer) intent also writes a `resume.md`.

### resume.md auto-pickup

When a `resume.md` is written under the project root (`.claude-kit/vault-bridge/resume.md`), the **SessionStart hook** detects it on the next session, injects its body into the model context via `additionalContext`, then deletes the file (single-use). The `.claude-kit/` directory is ephemeral — keep it gitignored.

```
/handoff
"다음 세션 인수인계"
"이어서 작업할 수 있게 정리해줘"
```

## Handoff Term Convention

`handoff` has a single canonical meaning in vault-bridge: **the `/handoff` command** that generates a next-session continuation handoff (see [Session Handoff](#session-handoff)). All other historical usages are deprecated.

| Context | Allowed? | Replacement |
|---------|----------|-------------|
| `/handoff` command (next-session continuation) | **Allowed (canonical)** | — |
| Standalone `handoff-*.md` filename | **Forbidden (legacy only)** | Use `session-*.md` |
| Redundant tag `tags: [session, handoff, ...]` | **Forbidden** | Omit `handoff` — `type:` already conveys artifact role |
| thinking-tools stage-to-stage data contract | **Domain prefix required** | Use `inter-stage handoff` or `stage-transition` |
| "Project-level handover document" | **Forbidden** | Write `plan-YYYY-MM-DD-{topic}.md`, then run `/handoff` to point the next session at it |

vault-searcher Mode 1 no longer matches the legacy `handoff-*.md` / `*-handoff.md` patterns (removed in v1.7.x). Existing legacy files have been renamed or absorbed.

**Migration for vaults that still contain `handoff-*.md` files** — Mode 1 will not surface these files. Three options:

1. **Rename** to `session-YYYY-MM-DD[-topic].md` (preferred — restores Mode 1 discovery and matches the canonical naming).
2. **Convert** to a `plan-YYYY-MM-DD-{topic}.md` if the file is closer to a project-level design doc than a session record.
3. **Leave as-is** if the file is purely historical reference and you no longer need it surfaced. Tag-based search (`tags: [session]`) and direct path access still work.

Pure rename is safe: vault-bridge does not read filename for semantics — `type:` in frontmatter is the source of truth.

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

`.vault-link` is a pointer file that binds a code repository to a specific vault project. When present, it scopes vault-searcher's domain-context (Mode 2) searches and determines the `/save-session` / `/save-plan-doc` save path automatically — zero user intervention required.

### Schema

**`.vault-link`** (commit this file):

```yaml
version: 1                          # optional; v1 assumed if absent
vault_path: notes/my-project  # required; relative to vault root
auto_capture: true                  # optional; W8 plan-doc autosync gate (default: false)
autosync_paths_include:             # optional v1.1; extra plan-doc patterns merged with defaults
  - notes/specs/*.md
  - adrs/**/*.md
autosync_paths_exclude:             # optional v1.1; extra exclude patterns merged with defaults
  - notes/specs/draft-*.md
```

`autosync_paths_include` / `autosync_paths_exclude` are appended to spec §3.2 default patterns; both are optional and the file remains fully backward-compat with v1 (`vault_path` only).

**Format constraint** — `.vault-link` and `.vault-link.local` are flat key:value YAML files. Do **not** wrap the body with `---` frontmatter delimiters; the parser treats the whole file as a single key:value scope and silently drops fields below the first `---` if any are present. The syncer emits a warning to stderr when it sees `---` in a `.vault-link` body.

**Accepted list forms** — both work:

```yaml
autosync_paths_include:        # block list (preferred for readability)
  - notes/specs/*.md
  - adrs/**/*.md

autosync_paths_include: [notes/specs/*.md, adrs/**/*.md]   # flow array
```

**Exclude pattern semantics**:

| Form | Match scope | Example |
|------|-------------|---------|
| `path/to/dir/` (trailing `/`) | Substring match anywhere in the path | `node_modules/`, `vendor/` |
| `**` glob | Cross-segment regex (zero or more dirs) | `proposals/**/draft-*.md` |
| Plain glob (`*`, `?`) | fnmatch on basename or full relative path | `*.tmp.md`, `CHANGELOG.md` |

To suppress a default include, write an exclude that covers it (e.g. `docs/discussions/**/*.md` blocks the default `docs/discussions/**/*.md` include for that project).

**Lax boolean** — `auto_capture` accepts `true`, `yes`, `1` (case-insensitive). The hook (bash) and the syncer (Python) treat them identically.

**`.vault-link.local`** (gitignore this file):

```yaml
vault_root: /Users/me/work-vault    # optional; overrides default ~/vault/
```

### Discovery

vault-searcher walks upward from CWD (git-style) until it finds `.vault-link`. The first file found is used. If `.vault-link.local` exists at the same level, its `vault_root` overrides the default `~/vault/`.

### Effect on vault-searcher modes and slash commands

| Surface | Without `.vault-link` | With `.vault-link` |
|---------|-----------------------|--------------------|
| **vault-searcher Mode 2 (Domain Context Load)** | Searches all of `~/vault/` | Searches only `{vault_root}/{vault_path}/` |
| **`/save-session`** | Saves to `~/vault/inbox/` | Saves to `{vault_root}/{vault_path}/` |
| **`/save-plan-doc`** | Cannot run (requires `.vault-link`) | Saves snapshots to `{vault_root}/{vault_path}/` |

vault-searcher Modes 1 and 3 (Session Restore, Keyword Search) are unaffected by `.vault-link` scope.

### Recovery

If the `vault_path` directory does not exist, vault-searcher checks `notes/` for candidates with edit distance ≤ 2 and asks the user to confirm. If no candidates are found, it falls back silently to full-vault scope and inbox save target.

### `/vault-link` command

Create or update `.vault-link` in the current directory:

```
/vault-link
```

The command scans `~/vault/notes/` and presents a selection list. For new projects, create the vault project note via `obsidian-vault-manager`'s `vault-knowledge-manager` agent first, then run `/vault-link` to bind it. It never auto-modifies `.gitignore` — only suggests adding `.vault-link.local` to it.

### Kill switch

Set `VAULT_BRIDGE_DISABLE=1` to skip `.vault-link` discovery entirely (useful in CI or remote environments where the vault is not available).

## Write Role Contract

vault-bridge v1.5.0 introduced vault write governance; v1.9.0 narrows vault-searcher to read-only and restricts vault writes to slash commands executed in the main context (see [Write Role Policy](#write-role-policy) below).

### Permitted writes

| Target | File types |
|--------|-----------|
| `inbox/` | `session-*`, `capture-*`, `plan-*` (new files only) |
| `notes/{project}/` | `session-*`, `capture-*`, `plan-*` (new files only, when `.vault-link` resolves to that project) |

### Forbidden writes

| Target | Reason |
|--------|--------|
| `notes/` (direct note creation) | Note creation is exclusively handled by obsidian-vault-manager's `note` skill |
| Any existing file (overwrite) | Immutable vault contract — vault-bridge never modifies existing files |
| Any existing file (append) | Same as overwrite — existing content is never touched |
| `assets/` | Binary asset management belongs to obsidian-vault-manager |

### Same-date collision handling

If `session-2026-04-18.md` already exists, `/save-session` tries `-v2`, `-v3`, … up to `-v9`. A collision confirmation is shown before creating `-v2` or higher. The existing file is never touched.

## Structured Error Protocol

When a vault write fails or is forbidden, `/save-session` (or another vault-write slash command) emits a structured error block to the user. Since v1.9.0 the block originates from the slash command running in main context — vault-searcher itself no longer writes and therefore no longer issues these errors.

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
| `permission` | Write target is in a forbidden zone | Tried to write `notes/oauth.md` directly (OVM territory) |
| `path_invalid` | `.vault-link` resolution failed completely, no fuzzy candidates | `vault_path` points to non-existent directory |
| `convention_violation` | Filename does not conform to the required pattern for that directory | `inbox/random-file.md` (missing type prefix and date) |
| `name_collision` | All `-v2` through `-v9` suffixes are already taken | `session-2026-04-18-v9.md` already exists |
| `disabled` | `VAULT_BRIDGE_DISABLE=1` is set | Kill switch active |

## File Naming Convention

vault-bridge v1.5.0 adds a **PreToolUse hook** (`hooks/pre-write-guard.sh`) that validates filenames when Claude writes to `~/vault/` with the `Write` or `Edit` tool.

### Per-directory patterns

| Directory | Required pattern | Example |
|-----------|-----------------|---------|
| `inbox/` | `^(session\|capture\|plan)-YYYY-MM-DD[-topic][-vN].md$` | `session-2026-04-18.md`, `capture-2026-04-18-jwt-debug.md` |
| `notes/` (evergreen) | `^[a-z0-9-]+\.md$` (no date prefix) | `oauth-flow.md` |
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

vault-bridge v1.9.0 adds an explicit Write Role Policy enforced by `hooks/pre-write-guard.sh`. Vault writes must originate from the main context (user-initiated slash commands). Subagent vault writes — identified by a non-empty agent identifier in the `PreToolUse` payload — are blocked or warned depending on the `VAULT_BRIDGE_WRITE_CONTRACT` environment variable.

| Mode | Behavior | When |
|------|----------|------|
| `warn` (default) | Injects a `systemMessage` warning; write is allowed to proceed | Default |
| `enforce` | Blocks the write (`exit 2`) — subagent vault writes are rejected | `VAULT_BRIDGE_WRITE_CONTRACT=enforce` |
| `off` | No check performed | `VAULT_BRIDGE_WRITE_CONTRACT=off` |

```bash
# Block all subagent vault writes
VAULT_BRIDGE_WRITE_CONTRACT=enforce claude

# Disable the policy check entirely
VAULT_BRIDGE_WRITE_CONTRACT=off claude
```

**Exempt paths**: Naming convention enforcement via `VAULT_BRIDGE_STRICT_NAMING` applies regardless of agent vs. main-context origin. No top-level folder is exempt from the Write Role Policy.

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
- **Informs at milestones**: a `systemMessage` is injected into Claude's context on the 1st, 5th, and 10th direct access of the session, suggesting vault-searcher as the more efficient path. Subsequent accesses still increment the counter but emit no notice — keeps hot-path sessions quiet while preserving telemetry.
- **Counts silently**: each direct access increments a session counter at `/tmp/vault-bridge-session-{session_id}/direct-access-count` (every call, not just milestones).
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
- Frontmatter: `created`, `tags: [session, {project}]`, `type: session` (no `status` field — `status: active` applies to `plan` artifacts only)
- Same-date collisions auto-increment with `-v2`, `-v3` suffixes
- **Stop hook** (deterministic shell script `hooks/stop-check.sh`): silently checks the user's last message for session-closing keywords; injects a one-line `systemMessage` suggesting `/save-session` only when a closing signal is detected. No LLM call → no per-turn cost, no infinite-loop risk
- **SessionStart hook** (`hooks/session-start-manifest.sh`): checks manifest staleness and regenerates `manifest.json` in the background; also detects `.claude-kit/vault-bridge/resume.md`, injects its body into the model context via `additionalContext`, and consumes (deletes) the file. Never blocks session startup
- **SessionEnd hook** (chained `hooks/session-end-pre.sh` → prompt): the shell pre-hook collects all deterministic state — `.vault-link` presence + Layer 1 `auto_capture`, `_index.md` Layer 2 `auto_capture`, plan-doc candidates, direct-access counter, plan-doc-asked flag — and writes a JSON file. The prompt then makes the LLM-judgment calls (meaningful-work check, Summary composition, conditional sections) and writes the safety-net session-note. The shell step uses `${CLAUDE_PROJECT_ROOT:-$PWD}` so a session-internal `cd` does not break `.vault-link` discovery
- **PreToolUse hook (Read/Grep/Glob)** (`hooks/pre-access-guard.sh`): detects direct `Read`/`Grep`/`Glob` calls targeting `~/vault/`; emits a soft notice with vault-searcher as alternative; increments session counter; never blocks
- **PreToolUse hook (Write/Edit)** (`hooks/pre-write-guard.sh`): validates vault file naming conventions AND enforces the Write Role policy — vault writes must be user-initiated (main context, executed by slash commands). Subagent vault writes (any non-empty agent identifier in the PreToolUse payload) are blocked or warned per `VAULT_BRIDGE_WRITE_CONTRACT` mode (default `warn`, supports `enforce` / `off`). Naming convention is log-only by default (`exit 0` always); set `VAULT_BRIDGE_STRICT_NAMING=1` to block non-conforming writes (`exit 2`)
- **`/save-session` command**: explicit user trigger for inline session note creation (main context) with mode selection (record/quick)
- **`/handoff` command**: generates a next-session continuation handoff (one-liner / summary / `resume.md` file) — main-context user trigger
- **`/vault-manifest-refresh` command**: force-regenerate the vault manifest cache; reports result in Korean

## Session Auto-Commit

vault-bridge v1.4.0 adds `/vault-commit`, a slash command that commits uncommitted vault changes to git with user approval.

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
| `/save-session` | Inline session note creation in main context — mode selection (record/quick), path confirmation, collision resolution |
| `/handoff` | Generate a next-session continuation handoff — one-line prompt, summary, or `resume.md` file |
| `/save-plan-doc` | Snapshot external plan/design docs into the bound vault project — 2-layer opt-in gate |
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
- [`jq`](https://jqlang.github.io/jq/) on PATH (used by the Stop hook to parse the transcript JSONL)

## Migration from vault-reader

`vault-bridge` v1.0.0 supersedes `vault-reader` v0.3.0. Plugin name changed — existing installations must re-install under the new name. Vault data (`~/vault/`) is fully compatible; no file migration needed.

```bash
claude plugin uninstall vault-reader
claude plugin install vault-bridge@Lyainc-claude-kit
```

Behavior and trigger phrases are unchanged at the v1.0.0 migration boundary. The `vault-searcher` agent kept the same 4 modes (restore, domain context, keyword search, session-note creation) through v1.8.x; v1.9.0 narrowed it to 3 read-only modes (write operations moved into the `/save-session` slash command — same UX, executed inline in main context).

If you reference the agent by qualified name in prompts or scripts, update `vault-reader:vault-searcher` → `vault-bridge:vault-searcher`.

## License

MIT
