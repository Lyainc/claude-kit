# CLAUDE.md (for claude-kit contributors)

This file provides guidance to Claude Code when **developing/contributing to this repository**. Runtime behavior rules (how Claude should act when these plugins are active in external projects) live in each plugin's agent/skill `description` fields, which are the single source of truth for runtime delegation.

Codex/OMX parity note: the Codex-active migration of this root guidance lives in `AGENTS.md`, with the surface-by-surface parity matrix in `docs/codex-claude-parity.md`.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 세 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 7개 + 에이전트 1개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, thought-chain, adversarial-review + thinking-facilitator agent)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 (vault-knowledge-manager, vault-file-organizer) + 스킬 3개 (capture, note, audit) + reference docs (`reference/vault-audit-rules.md` 등) + shell primitives (`scripts/ovm-primitives.sh`)
- **vault-bridge** (`vault-bridge/`): Obsidian vault I/O 브릿지 플러그인 — 에이전트 1개 (vault-searcher, haiku) + 훅 5종 (Stop / SessionEnd command+prompt / SessionStart / PreToolUse Read|Grep|Glob / PreToolUse Write|Edit) + 슬래시 커맨드 6개 (`/save-session`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`, `/save-plan-doc`, `/handoff`) + Python scripts (`generate-manifest.py`, `plan-doc-syncer.py`). vault 검색 + slash command 기반 session-note/capture/plan 작성 + 세션 생명주기 안전망 + 외부 plan-doc 자동 캡처.

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
- **PR descriptions**: Korean
- **Branches**: `feat/`, `fix/`, `docs/`, `refactor/` prefixes

## PR Workflow

- **Merge strategy**: rebase merge by default (atomic commits preserved, linear history). `--merge` only when an explicit merge commit is needed.
- **Chained PRs** (child PR base = parent's feature branch):
  - Before merging parent with `--delete-branch`: update child's base to `main` first (`gh pr edit <child> --base main`). GitHub auto-closes PRs whose base branch is deleted, and closed PRs cannot have their base changed — recreate the PR instead.
  - After parent rebase-merges, child branch likely has SHAs that diverged from main (rebase merge rewrites them). Rebase locally with `git rebase --onto origin/main <old-parent-tip>` to drop the now-duplicate commits, then `git push --force-with-lease`.
- **WIP across rebases**: stash unrelated WIP (`.gitignore`, `AGENTS.md`, untracked files etc.) with `git stash push -u -m <msg> -- <paths>` before rebasing, restore after. Rebasing with a dirty tree fails.
- **PR descriptions**: Korean. Reference the master plan or vault spec when applicable so the trail stays searchable.

## Language Policy

All plugins (thinking-tools, obsidian-vault-manager, vault-bridge) follow a unified policy:

- **Skill instructions** (SKILL.md body): English for LLM-optimized parsing
- **Agent instructions** (agents/*.md body): English for LLM-optimized parsing
- **Metadata** (frontmatter keys, section headers): English
- **User-facing output**: Korean (each file contains a Korean I/O directive)
- **README descriptions**: English by default (consistent with skill/agent body)
- **README trigger examples**: Korean OK (user-facing trigger phrases)
- **Reference docs / examples** (`reference/`, `examples.md`): Korean (user-facing content)
- **Korean text in templates/examples** representing actual vault content: preserved as Korean

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
│   ├── skills/                          # 3개 스킬 (capture, note, audit)
│   ├── agents/                          # 2개 에이전트
│   ├── reference/                       # vault-audit-rules.md, obsidian-cli.md, obsidian-format.md
│   └── scripts/                         # ovm-primitives.sh, audit-validate.py, gen-fixture.sh
├── vault-bridge/                        # plugin: vault-bridge
│   ├── .claude-plugin/plugin.json
│   ├── agents/                          # vault-searcher (haiku, 3 modes, read-only)
│   ├── commands/                        # 6개 슬래시 커맨드 정의
│   ├── hooks/                           # 5개 hook handler (stop-check, session-end-pre, session-start-manifest, pre-access-guard, pre-write-guard)
│   └── scripts/                         # generate-manifest.py, plan-doc-syncer.py + tests/
├── docs/
│   ├── design/                          # 설계 문서
│   └── discussions/                     # 의사결정 토론 transcripts (`YYYYMMDD_topic/`)
├── CLAUDE.md
├── AGENTS.md                            # Codex/OMX parity (canonical: CLAUDE.md, mirror: AGENTS.md)
└── README.md
```

## Marketplace Structure

- `marketplace.json`: 전체 플러그인 목록. 각 항목의 `source` 필드가 플러그인 루트 경로
- `plugin.json`: 개별 플러그인 메타데이터 (name, version, keywords)
- `skills/*/SKILL.md`: Claude Code가 자동 검색하는 스킬 정의 파일
- `agents/*.md`: 에이전트 정의 파일 (두 플러그인 모두 보유)

## Validation

```bash
# JSON 유효성 검사
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null

# 플러그인 스펙 전체 검증 (frontmatter·hooks 스키마 포함)
# claude plugin validate  # Claude Code 설치 환경에서 실행

# 스킬 파일 존재 확인
find thinking-tools/skills -name "SKILL.md" | sort
find obsidian-vault-manager/skills -name "SKILL.md" | sort

# vault-bridge gate + discover unit tests
python3 vault-bridge/scripts/test/test-discover.py
# Expected: OK: all cases passed (currently 18 cases)

# vault-bridge pre-write-guard regression (Write Role Contract + naming)
python3 vault-bridge/scripts/test/test-pre-write-guard.py

# vault-bridge pre-access-guard regression (vault-searcher self-exemption + counter)
python3 vault-bridge/scripts/test/test-pre-access-guard.py

# vault-bridge manifest type opt-in regression (v4 §2.2)
python3 vault-bridge/scripts/test/test-manifest-type-optin.py

# telemetry schema self-test
python3 telemetry/scripts/validate-schema.py --self-test

# Shell hook syntax check
bash -n vault-bridge/hooks/*.sh
bash -n telemetry/event-logger.sh

# parse_created_date unit test (audit-validate Phase 2 helper)
python3 obsidian-vault-manager/scripts/test/test-parse-created-date.py
# Expected: OK: all 13 cases passed

# read_manifest_summary schema_version gate (None vs 0 semantics)
python3 obsidian-vault-manager/scripts/test/test-read-manifest-summary.py
# Expected: OK: all cases passed (7 cases)

# E8 promotion candidate finding regression
python3 obsidian-vault-manager/scripts/test/test-promotion-finding.py
# Expected: OK: all 6 cases passed

# vault-audit DoD 측정 (mechanical reference impl)
# gen-fixture.sh --with-audit-errors now internally calls generate-manifest.py
# and patches access_count=5 for the E8 access-target seed.
rm -rf /tmp/ovm-fixture-audit-recheck
OVM_FIXTURE_DIR=/tmp/ovm-fixture-audit-recheck \
  bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod
# Expected (PR 4d+):
#   dod.seeded_detected = {E1:5, E2:10, E3:5, E4:5, E5:5, E6:5, E7:5, E8:2}
#     (E2 has 10: 5 base + 5 status-missing; E6=stale_inbox; E7=stale_draft;
#      E8 has 2: promotion-target via refs_in=3, access-target via manifest patch)
#   dod.fp_on_clean per type = 0
#   dod.findings_missing_priority = 0
#   dod.priority_mismatches = []
# Note: dod.priority_counts is informational only (P1 includes existing
# fixture inbox captures with old created: dates, varies by run date).
```

## SKILL.md Frontmatter

```yaml
---
name: skill-name              # 필수: kebab-case
description: "One-line summary"  # Required: skill purpose + usage example
allowed-tools: Read Write Bash  # 필수: 스킬이 사용하는 도구 목록
# context: fork                # 선택: fork 시 별도 에이전트에서 실행
# agent: Explore               # 선택: fork 시 사용할 에이전트 타입
# model: haiku                 # 선택: 스킬 실행 시 사용할 모델 (haiku|sonnet|opus|inherit)
---
```

## Vault File Conventions

Files written to `~/vault/` by OVM or vault-bridge follow a unified convention (vault second brain v4 — see `docs/design/vault-second-brain-v4.md`).

**Folder layout** (v4 §3.1): three top-level folders only — `inbox/` (raw input), `notes/` (all content; free sub-folders allowed), `assets/` (attachments).

**Filename pattern** (v4 §3.6): `{type}-YYYY-MM-DD[-{topic}][-vN].md` for dated types, `{slug}.md` for evergreen notes.

| Type | Example | Path |
|------|---------|------|
| `session` | `session-2026-04-12.md` | `inbox/` |
| `capture` | `capture-2026-04-12-api-changes.md` | `inbox/` |
| `note` | `{topic}.md` (no date) | `notes/` |
| `decision` | `decision-2026-04-12-{topic}.md` | `notes/` |
| `plan` | `plan-2026-04-12-{topic}.md` | `notes/{project}/` (linked via `.vault-link`) |

Same-date collisions: `-v2`, `-v3` increment.

**Frontmatter standard**:
```yaml
created: YYYY-MM-DD                            # required, all files
tags: [{type}, {domain}]                       # required
type: capture|note|decision|session|plan       # required — type opt-in (v4 §2.2): files without `type:` are invisible to claude-kit
status: raw|draft|evergreen|archived           # required for note/decision (status machine, v4 §3.3); session/capture/plan: optional
source: web-clipper|manual|...                 # capture only, optional
url: ...                                       # capture only, optional
```

**type opt-in** (v4 §2.2): a `type:` field is the marker that opts a note into claude-kit's management. Files without it remain invisible — users keep diary, book notes, free folders untouched.

## vault-bridge Hooks & Commands

vault-bridge registers 5 hook handlers + 6 slash commands. All hooks are **deterministic shell scripts** unless explicitly noted otherwise — no per-turn LLM cost.

**Vault root configuration** (all hooks + Python scripts share the same 3-level priority):
1. `VAULT_BRIDGE_VAULT_ROOT` env var — explicit runtime override (CI/scripts, highest priority)
2. `VAULT_BRIDGE_VAULT_PATH` env var — set from `userConfig.vault_path` in plugin settings
3. `~/vault` — built-in default. Tilde in either var is expanded to `$HOME`.

**Hooks**:

- **Stop** (`hooks/stop-check.sh`, deterministic): per-turn. Reads transcript JSONL, regex-matches the last user text against closing keywords (`세션 끝`, `마무리`, `wrap up`, `end session`, etc.), and emits a `systemMessage` suggesting `/save-session` only on match. **No LLM call** → no per-turn cost, no infinite-loop risk (the prior prompt-based hook looped because every response — even "(silent pass-through)" — re-fired the Stop hook).
- **SessionEnd** (chained `hooks/session-end-pre.sh` → prompt): session close. Shell pre-hook collects deterministic state (vault-link gate flags, plan-doc candidates, direct-access counter) and writes JSON to `/tmp/vault-bridge-session-${SID}/session-end-state.json`; prompt then reads it via `jq`, decides whether work was meaningful, writes the safety-net session-note. Pre-hook uses `${CLAUDE_PROJECT_ROOT:-$PWD}` so a session-internal `cd` doesn't break `.vault-link` discovery. The prompt body is compressed (~1000 chars) to keep token overhead minimal.
- **SessionStart** (`hooks/session-start-manifest.sh`, deterministic): incremental manifest refresh — checks staleness and updates `{vault_root}/.vault-bridge/manifest.json` only for changed files (background, never blocks session start).
- **PreToolUse Read|Grep|Glob** (`hooks/pre-access-guard.sh`, deterministic): emits `systemMessage` warning when the configured vault root is accessed directly; counts direct-access events for the SessionEnd summary. Soft warning, never blocks. As of v1.9.0, this hook exempts vault-searcher's own reads to avoid the self-reference loop that previously caused haiku to misinterpret its own warning as a denial.
- **PreToolUse Write|Edit** (`hooks/pre-write-guard.sh`, deterministic): validates vault file naming conventions AND enforces the Write Role policy — vault writes must be user-initiated (main context, executed by slash commands). Subagent vault writes (any non-empty agent identifier in the PreToolUse payload) are blocked or warned per `VAULT_BRIDGE_WRITE_CONTRACT` mode (default `warn`, supports `enforce` / `off`). `50_Archive/` is exempt (OVM territory). Naming convention is log-only by default; `VAULT_BRIDGE_STRICT_NAMING=1` blocks on violation.

**Slash commands** (`commands/*.md`):

- **`/save-session`**: executes the session-note recipe inline in main context (record/handoff/quick mode selection). As of v1.9.0, no longer delegates to vault-searcher — vault writes are user-initiated slash commands only.
- **`/vault-link`**: creates a `.vault-link` pointer file binding the current project to a vault location.
- **`/vault-manifest-refresh`**: forces a full manifest rebuild (skips staleness check).
- **`/vault-commit`**: commits uncommitted vault changes with user-approved message.
- **`/save-plan-doc`**: snapshots external `docs/discussions/`, `docs/design/`, `docs/plans/` markdown into the bound vault project. 2-layer opt-in gate — L1 `snapshot_export: true` in `.vault-link` (project owner), L2 `snapshot_import: true` in vault `_index.md` (vault owner, managed via OVM `/project --enrich`). `auto_capture` remains as a 4-week deprecation alias for both layers; `VAULT_BRIDGE_SUPPRESS_DEPRECATION=1` silences the stderr warning for non-interactive callers (set by `session-end-pre.sh` so the deprecation notice doesn't pollute `discovery_error`).
- **`/handoff`**: generates a continuation prompt for the next session — paste-ready one-liner, structured summary, or saved as `.claude-kit/vault-bridge/resume.md`. Does not write to vault paths; resume.md is a local gitignored file only.

The split (deterministic Stop + 2-step SessionEnd + explicit slash commands) ensures zero per-turn LLM cost, no loops, safety-net auto-save on `/exit`, and a clear user-driven path for full session notes and plan-doc snapshots.

## Cross-Plugin MECE Boundaries

Skills across `obsidian-vault-manager` and `vault-bridge` share overlapping domains. Boundaries:

| Area | obsidian-vault-manager | vault-bridge |
|------|----------------------|--------------|
| Note creation | `note` skill (evergreen notes + decision records, `notes/`) | N/A |
| Session record | N/A (use vault-bridge's session-note) | `/save-session` slash command (inline in main context — record/handoff/quick modes) |
| Domain context search | `vault-knowledge-manager` (direct mdfind/grep, OVM-internal) | `vault-searcher` Mode 2 (external, read-only lightweight) |

Within `thinking-tools`:
- `diverse-sampling`: creative generation (brainstorming, alternatives)
- `expert-panel`: evaluative debate (multi-perspective assessment, decision-making)
- Trigger "여러 관점" → `expert-panel` only (evaluative, not creative)

## Adding a New Skill

1. 해당 플러그인의 `skills/{skill-name}/SKILL.md` 생성
2. `plugin.json`의 `keywords`에 스킬명 추가
3. 상위 `marketplace.json`의 해당 플러그인 항목 버전 범프
4. 에이전트가 해당 스킬을 사용해야 하면: 에이전트 `.md`의 `skills:` frontmatter에 추가

## Adding a New Agent

1. 해당 플러그인의 `agents/{agent-name}.md` 생성 (frontmatter: name, description, model, skills)
2. `plugin.json`의 `keywords`에 에이전트명 추가
3. 상위 `marketplace.json`의 해당 플러그인 항목 버전 범프

## Version Sync Rule

`plugin.json`과 `marketplace.json`의 다음 필드는 항상 동기화:
- `version`: 양쪽 동일하게 범프
- `description`: 양쪽 동일한 문자열 유지
- `keywords`: 양쪽 동일한 배열 유지

## Adding a New Plugin

1. `{plugin-name}/` 디렉토리 생성
2. `{plugin-name}/.claude-plugin/plugin.json` 작성
3. `{plugin-name}/skills/` 하위에 스킬 추가
4. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목 추가 (`source` 경로 지정)
5. `{plugin-name}/README.md` 작성
6. 루트 `README.md`에 플러그인 소개 추가
