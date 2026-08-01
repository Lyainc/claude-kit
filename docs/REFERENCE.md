# claude-kit Reference

Lookup-only sections split out of `CLAUDE.md` (2026-08-02, #473) so the project's always-loaded
memory file stays under the same 5,000-token budget `scripts/check-skill-token-budget.py` holds
every SKILL.md to (CLAUDE.md measured 5,510 tokens before this split — over budget, dilution
rationale in that script's docstring). This doc is loaded on demand, not on every turn.
`CLAUDE.md`'s original sections now just point here — no instruction was deleted, only moved.

## Abandon-priority table

Which CLAUDE.md sections count as "lookup-only" (movable here) is not a per-edit judgment call —
it is decided once, as data, so a future trim is reproducible instead of re-litigated. When
CLAUDE.md goes back over budget, move sections here starting from the **highest** number, until
the guard passes again. `0` = load-bearing, never move.

| Section | Priority | Why |
|---|---|---|
| vault-bridge Hooks & Skills | 50 | Implementation detail — read on demand, not needed to act every turn |
| Directory Structure | 40 | A tree listing — regenerable from `find`/`ls`, not a decision input |
| Vault File Conventions | 30 | Schema tables also carried by `docs/design/vault-second-brain-v4.md`/`v5.md`; only vault-writing skills need it |
| Project Overview — 변경 이력 | 20 | Completed migrations/retirements (past tense) — don't change what to do next |
| Project Overview — 현재 상태 | 10 | Current plugin composition — needed to orient in the repo |
| Cross-Plugin MECE Boundaries | 5 | Directly disambiguates which skill to route to |
| Git Conventions / PR Workflow / Language Policy / SKILL.md Frontmatter / Version Sync Rule / Adding a New Skill·Agent·Plugin | 0 | Action rules read every time that action is taken |

This split moved priority 20-50 (the four highest). Priority 5 and below stayed in `CLAUDE.md`.

## Directory Structure

```
claude-kit/                              # marketplace repo (Lyainc-claude-kit)
├── .claude-plugin/
│   └── marketplace.json                 # 마켓플레이스 매니페스트 (플러그인 목록 + source 경로)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── thinking-tools/                      # plugin: thinking-tools
│   ├── .claude-plugin/plugin.json       # 플러그인 매니페스트
│   ├── skills/                          # 스킬 디렉토리 (SKILL.md 기반 자동 검색)
│   ├── agents/                          # 에이전트 디렉토리 (thinking-facilitator)
│   ├── reference/
│   └── docs/
├── obsidian-vault-manager/              # plugin: obsidian-vault-manager
│   ├── .claude-plugin/plugin.json
│   ├── skills/                          # 3개 스킬 (wiki, audit, base)
│   ├── agents/                          # 2개 에이전트
│   ├── reference/                       # vault-audit-rules.md, obsidian-cli.md, obsidian-format.md, obsidian-bases-schema.md
│   └── scripts/                         # ovm-primitives.sh + test/ (audit-validate.py, gen-fixture.sh, ...)
├── vault-bridge/                        # plugin: vault-bridge
│   ├── .claude-plugin/plugin.json
│   ├── agents/                          # vault-searcher (haiku, 3 modes, read-only)
│   ├── skills/                          # 4개 스킬 (vault-save, vault-link, vault-manifest-refresh, vault-commit)
│   ├── hooks/                           # 2개 hook handler (session-start-manifest, pre-write-guard)
│   └── scripts/                         # generate-manifest.py + tests/
├── feedback-loop/                       # plugin: feedback-loop (⑤ 자기개선, 외부 배포 — #217)
│   ├── .claude-plugin/plugin.json       # hooks 키: 8 event-type 등록 (opt-in telemetry)
│   ├── skills/                          # retro (#123 — E8 승격 + 3갈래 출력 + dedup + 회고예산)
│   ├── scripts/                         # telemetry: event-logger.sh, report.py, sequence.py, validate-schema.py, plugin-map.json + test/
│   └── README.md                        # measure→review→keep, opt-in·local-only·per-turn LLM 0
├── docs/                                # 살아있는 계약만 — 완료된 계획·죽은 설계는 삭제(근거는 GitHub 이슈)
│   ├── design/                          # 현행 설계 계약 (boundary SSOT, 어댑터 계약, vault v4/v5, 4-흐름)
│   ├── specs/                           # spec-first Seed (YAML)
│   ├── VALIDATION.md                    # 검증 명령 단일 출처 (CI가 이 파일을 읽음)
│   ├── REFERENCE.md                     # CLAUDE.md에서 분리된 조회용 섹션 (이 파일)
│   └── discussions/                     # 스킬이 쓰는 로컬 워킹 드래프트 (gitignored)
├── CLAUDE.md
└── README.md
```

## vault-bridge Hooks & Skills

vault-bridge registers 2 hook handlers + 4 skills. All hooks are **deterministic shell scripts**
unless explicitly noted otherwise — no per-turn LLM cost.

**Read/write asymmetry (Write Role Contract)**: vault-bridge is a "haiku delivery" layer for
**reads only**. Vault *reads* are delegated to the haiku `vault-searcher` agent; vault *writes*
cannot be delegated — `pre-write-guard.sh` (default `enforce`) blocks subagent writes, so all
writes are main-context user-initiated skills. Both vault-content ③ delivery adapters that
vault-bridge once carried are now retired: the `session` adapter (`docs/design/output-adapter-contract.md`
§2 row #5 — formerly `/save-session`) was **retired 2026-07-10 (#331)** when the session-knowledge
path was redefined wiki-first (session knowledge → OVM `/wiki` + native memory), and the
`handoff` adapter (row #4 — formerly `/handoff`, vault-bypassing) was **retired in G26 (decision
G25 D4)**; the handoff function now lives in the machine-level `session-close` skill, outside
claude-kit. vault-bridge's remaining write skill is `/vault-commit` (git commit); vault *content*
authoring (`/vault-save`) belongs to vault-bridge, compilation (`/wiki`) to obsidian-vault-manager. vault-bridge is still
claude-kit's **③ delivery layer** (`claude-kit-boundary.md` line 26). Per the G3 #102 ADR the
output layer is **distributed in-place**, so these delivery adapters live here rather than in a
separate plugin.

**Vault root configuration** (all hooks + Python scripts share the same 3-level priority):
1. `VAULT_BRIDGE_VAULT_ROOT` env var — explicit runtime override (CI/scripts, highest priority)
2. `VAULT_BRIDGE_VAULT_PATH` env var — set from `userConfig.vault_path` in plugin settings
3. `~/vault` — built-in default. Tilde in either var is expanded to `$HOME`.

**Hooks**:

- **SessionStart** (`hooks/session-start-manifest.sh`, deterministic): incremental manifest
  refresh — checks staleness and updates `{vault_root}/.vault-bridge/manifest.json` only for
  changed files (background, never blocks session start).
- **PreToolUse Write|Edit|Bash** (`hooks/pre-write-guard.sh`, deterministic): validates vault
  file naming conventions AND enforces the **Write Role Contract** — the read/write asymmetry at
  the core of vault-bridge. Vault *reads* are haiku-delegable (the `vault-searcher` agent), but
  vault *writes* are NOT: they must be user-initiated (main context, executed by skills).
  Subagent vault writes (any non-empty agent identifier in the PreToolUse payload) are denied or
  warned per `VAULT_BRIDGE_WRITE_CONTRACT` mode (default `enforce` — deny; supports `warn` /
  `off`). Naming convention is log-only by default; `VAULT_BRIDGE_STRICT_NAMING=1` blocks on
  violation.
  - **Bash coverage (#381)**: matching on tool name alone left the contract bypassable — a
    subagent holding `Bash` could write the vault with `echo > ~/vault/x.md`, `mv`, `tee`. The
    guard now also fires on `Bash` and denies commands whose write *target* resolves inside the
    vault (quote-aware tokenizer, command-position verb detection, redirection targets, `cd`
    tracking), while every read (`grep ~/vault`, `cat ~/vault/x.md`, `cd ~/vault && git status`,
    `cp ~/vault/x.md /tmp/`) passes. Naming validation is not applied on the Bash path
    (contract-only). Same **honest-subagent threat model** as `scripts/subagent-git-guard.sh`
    (#209): indirection that takes the command as data (`eval`, `sh -c`, backticks, `xargs`,
    `python3 -c "open(...)"`) is *not* defeated — catching it statically would cost false denies
    on reads. Those gaps are pinned as KNOWN_EVASIONS in
    `scripts/test/test-pre-write-guard.py`.

**Skills** (`skills/*/SKILL.md`; migrated from `commands/*.md` in #94):

- **`/vault-save`**: the single reference-material entry (#480) — source text as-is → `inbox/`,
  prose you wrote → `notes/`. Saves immediately with no confirmation, always writes `provenance:`,
  never writes `status:`. Replaced OVM's retired `/capture` and `/note`.
- **`/vault-link`**: creates a `.vault-link` pointer file binding the current project to a vault
  location.
- **`/vault-manifest-refresh`**: forces a full manifest rebuild (skips staleness check).
- **`/vault-commit`**: commits uncommitted vault changes with user-approved message.

(`/handoff` was retired in G26 — the next-session continuation function moved to the
machine-level `session-close` skill, outside claude-kit.)

The remaining hooks (deterministic SessionStart manifest refresh + PreToolUse write-role guard) and
explicit skills ensure zero per-turn LLM cost, no loops. The session-lifecycle auto-hooks (Stop
capture suggestion, SessionEnd safety-net auto-save) were cut in G24; capture ore is written only
via vault-bridge's explicit `/vault-save` skill.

## Vault File Conventions

Files written to `~/vault/` by OVM or vault-bridge follow a unified convention (vault second
brain v4, extended by v5 — see `docs/design/vault-second-brain-v4.md` and
`docs/design/vault-second-brain-v5.md`).

**Folder layout** (v4 §3.1; v5 §3 adds `wiki/`): four top-level folders — `inbox/` (raw input),
`notes/` (all content; free sub-folders allowed), `wiki/` (LLM-compiled domain knowledge — the v5
A layer, AI-recall primary; free sub-folders allowed), `assets/` (attachments).

**Filename pattern** (v4 §3.6): `{type}-YYYY-MM-DD[-{topic}][-vN].md` for dated types,
`{slug}.md` for evergreen notes and wiki pages.

| Type | Example | Path |
|------|---------|------|
| `session` | `session-2026-04-12.md` | `inbox/` |
| `capture` | `capture-2026-04-12-api-changes.md` | `inbox/` |
| `note` | `{topic}.md` (no date) | `notes/` |
| `decision` | `decision-2026-04-12-{topic}.md` | `notes/` |
| `plan` | `plan-2026-04-12-{topic}.md` | `notes/{project}/` (linked via `.vault-link`) |
| `wiki` | `{topic}.md` (no date) | `wiki/` (v5 A layer; written by the `wiki` skill) |

Same-date collisions: `-v2`, `-v3` increment. For `wiki`, same-topic is an **update**
(compounding), never a `-vN` duplicate.

**Frontmatter standard**:
```yaml
created: YYYY-MM-DD                            # required, all files
tags: [{type}, {domain}]                       # required
type: capture|note|decision|session|plan|wiki  # required — type opt-in (v4 §2.2): files without `type:` are invisible to claude-kit
# status: ABOLISHED — the v4 §3.3 status machine died with the promotion gate (v5 §5/§6, #480). Nothing writes it; an older file that still carries one is not an error
anchor: <local path/URL>                       # wiki only, optional — present only for source-anchored (cache-type) pages; absent = source-free (store-type). Staleness classification axis (#305)
verified: YYYY-MM-DD                           # wiki only, auto-stamped on every write — last-touched, not an active verification; exposes page age for staleness hedging (#305)
provenance: <query/session/URL>                # required — wiki (v5 §4.1 U3 traceability) and every file written by /vault-save (v5 §5). Older B files predate the rule and are not backfilled yet (#480 follow-up)
source: web-clipper|manual|...                 # capture only, optional
url: ...                                       # capture only, optional
```

**type opt-in** (v4 §2.2): a `type:` field is the marker that opts a note into claude-kit's
management. Files without it remain invisible — users keep diary, book notes, free folders
untouched.

## Project Overview — 변경 이력

Historical/retirement detail pulled out of `CLAUDE.md`'s Project Overview bullets — what each
plugin *was* or used to carry, not what it currently does (that stays in `CLAUDE.md`).

- **vault-bridge**: `commands/*.md`→`skills/` 포맷 마이그레이션 완료 (#94). `/handoff`은 G26에서
  retire — 인수인계 기능은 머신 레벨 `session-close` 스킬로 이관, claude-kit 외부. `/save-session`은
  #331에서 retire — 세션지식 경로가 wiki-first로 재정의되어 OVM `/wiki` + native memory로 이관.
  세션 생명주기 자동 훅은 G24에서 cut.
- **feedback-loop**: #217로 ⑤ 하네스에서 분리된 외부 배포 단위가 됨. `add-policy`는 매립 엔진으로
  G19/#255에서 도입. `distill`은 SIS(claude-self-improving-skills)에서 이식, #202.
