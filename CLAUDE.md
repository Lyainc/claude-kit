# CLAUDE.md (for claude-kit contributors)

This file provides guidance to Claude Code when **developing/contributing to this repository**. Runtime behavior rules (how Claude should act when these plugins are active in external projects) live in each plugin's agent/skill `description` fields, which are the single source of truth for runtime delegation.

Codex/OMX parity note: the Codex-active migration of this root guidance lives in `AGENTS.md`, with the surface-by-surface parity matrix in `docs/codex-claude-parity.md`.

Design Principles & boundary: the single source of truth for the claude-kit↔harness boundary (evolutionary boundary A), the 5-layer model, and the one-way dependency rule is `docs/design/claude-kit-boundary.md`.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 네 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 7개 + 에이전트 1개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, adversarial-review, build-spec + thinking-facilitator agent)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 (vault-knowledge-manager, vault-file-organizer) + 스킬 5개 (capture, note, wiki, audit, base) + reference docs (`reference/vault-audit-rules.md`, `reference/obsidian-bases-schema.md` 등) + shell primitives (`scripts/ovm-primitives.sh`). wiki = v5 A-layer LLM wiki 컴파일(`vault/wiki/`, AI recall 主, provenance 추적, 게이트된 명시 액션).
- **vault-bridge** (`vault-bridge/`): Obsidian vault I/O 브릿지 플러그인 — 에이전트 1개 (vault-searcher, haiku) + 훅 3종 (SessionStart / PreToolUse Read|Grep|Glob / PreToolUse Write|Edit) + 스킬 3개 (`/vault-link`, `/vault-manifest-refresh`, `/vault-commit`; `commands/*.md`→`skills/`포맷 마이그레이션 완료 #94; `/handoff`은 G26에서 retire — 인수인계 기능은 머신 레벨 `session-close` 스킬로 이관, claude-kit 외부; `/save-session`은 #331에서 retire — 세션지식 경로가 wiki-first로 재정의되어 OVM `/wiki` + native memory로 이관) + Python scripts (`generate-manifest.py`, `vault-commit-message.py`). vault 검색 + git 커밋. vault 콘텐츠 쓰기(capture/note/wiki)는 OVM 소유. (세션 생명주기 자동 훅은 G24에서 cut.)
- **feedback-loop** (`feedback-loop/`): layer ⑤ 자기개선 루프 (measure→review→keep, **실행/이터레이션 엔진 아님** — #217로 ⑤ 하네스에서 분리된 **외부 배포** 단위). 스킬 3개 (retro — audit E8 user-confirmed 승격 + 3갈래 출력 + dedup + 회고예산, #123 / distill — 세션 절차 기법의 user-confirmed **발견**: 자연어 제안 객체 emit, 저작은 안 함(매립은 add-policy 소유), SIS 이식, #202 / add-policy — **매립 엔진**(G19/#255): 자연어 규칙·distill 제안을 분류해 매립지 3개(CLAUDE.md/hook/skill) 중 한 곳에 1클릭 배치, 머신-중립·커밋 안 함, user-authored 스킬 inviolable) + telemetry 흡수 (event-logger hooks 8 event-type, report.py lifecycle, opt-in `CLAUDE_KIT_TELEMETRY=1` 아니면 silent·per-turn LLM 0·외부 유출 0). **단방향 의존(CON-5)**: feedback-loop은 leaf OUTPUT(audit·manifest·telemetry events)만 읽고 leaf code import 0; 외부 배포지만 ⑤ harness 계열(배포단위≠레이어).

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `enhance:`, `test:`, `nit:`)
- **PR descriptions**: Korean
- **Branches**: `feat/`, `fix/`, `docs/`, `refactor/` prefixes

## PR Workflow

- **Merge strategy**: **rebase-merge by default** (`gh pr merge --rebase`) — atomic commits preserved, linear history.
  - **Squash is NOT the default**: squash only when the repo owner (the human maintainer) explicitly asks, or to collapse genuinely noisy junk history (e.g. a `wip` auto-checkpoint) — and only after confirming with the repo owner.
  - `--merge` only when an explicit merge commit is needed.
  - **Never force-push `main` to convert a merge strategy after the fact** — if the wrong method was used, recover via the PR mechanism, not a raw push to the default branch.
  - If a `wip` commit would otherwise land on main via rebase-merge, fold it into its slice before merging rather than reaching for squash.
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
│   ├── skills/                          # 5개 스킬 (capture, note, wiki, audit, base)
│   ├── agents/                          # 2개 에이전트
│   ├── reference/                       # vault-audit-rules.md, obsidian-cli.md, obsidian-format.md, obsidian-bases-schema.md
│   └── scripts/                         # ovm-primitives.sh + test/ (audit-validate.py, gen-fixture.sh, ...)
├── vault-bridge/                        # plugin: vault-bridge
│   ├── .claude-plugin/plugin.json
│   ├── agents/                          # vault-searcher (haiku, 3 modes, read-only)
│   ├── skills/                          # 3개 스킬 (vault-link, vault-manifest-refresh, vault-commit; commands/→skills/ 마이그레이션 #94)
│   ├── hooks/                           # 3개 hook handler (session-start-manifest, pre-access-guard, pre-write-guard)
│   └── scripts/                         # generate-manifest.py + tests/
├── feedback-loop/                       # plugin: feedback-loop (⑤ 자기개선, 외부 배포 — #217)
│   ├── .claude-plugin/plugin.json       # hooks 키: 8 event-type 등록 (opt-in telemetry)
│   ├── skills/                          # retro (#123 — E8 승격 + 3갈래 출력 + dedup + 회고예산)
│   ├── scripts/                         # telemetry: event-logger.sh, report.py, sequence.py, validate-schema.py, plugin-map.json + test/
│   └── README.md                        # measure→review→keep, opt-in·local-only·per-turn LLM 0
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

Full validation command list moved to [docs/VALIDATION.md](docs/VALIDATION.md) — loaded
on demand instead of on every turn. `scripts/check-ci-coverage.py` and
`scripts/check-test-exitcode.py` read that file's `## Validation` heading + fenced block
directly.

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

Files written to `~/vault/` by OVM or vault-bridge follow a unified convention (vault second brain v4, extended by v5 — see `docs/design/vault-second-brain-v4.md` and `docs/design/vault-second-brain-v5.md`).

**Folder layout** (v4 §3.1; v5 §3 adds `wiki/`): four top-level folders — `inbox/` (raw input), `notes/` (all content; free sub-folders allowed), `wiki/` (LLM-compiled domain knowledge — the v5 A layer, AI-recall primary; free sub-folders allowed), `assets/` (attachments).

**Filename pattern** (v4 §3.6): `{type}-YYYY-MM-DD[-{topic}][-vN].md` for dated types, `{slug}.md` for evergreen notes and wiki pages.

| Type | Example | Path |
|------|---------|------|
| `session` | `session-2026-04-12.md` | `inbox/` |
| `capture` | `capture-2026-04-12-api-changes.md` | `inbox/` |
| `note` | `{topic}.md` (no date) | `notes/` |
| `decision` | `decision-2026-04-12-{topic}.md` | `notes/` |
| `plan` | `plan-2026-04-12-{topic}.md` | `notes/{project}/` (linked via `.vault-link`) |
| `wiki` | `{topic}.md` (no date) | `wiki/` (v5 A layer; written by the `wiki` skill) |

Same-date collisions: `-v2`, `-v3` increment. For `wiki`, same-topic is an **update** (compounding), never a `-vN` duplicate.

**Frontmatter standard**:
```yaml
created: YYYY-MM-DD                            # required, all files
tags: [{type}, {domain}]                       # required
type: capture|note|decision|session|plan|wiki  # required — type opt-in (v4 §2.2): files without `type:` are invisible to claude-kit
status: raw|draft|evergreen|archived           # required for note/decision (status machine, v4 §3.3); session/capture/plan: optional; wiki: OMITTED (A is outside the status machine, v5 §4.1)
anchor: <local path/URL>                       # wiki only, optional — present only for source-anchored (cache-type) pages; absent = source-free (store-type). Staleness classification axis (#305)
verified: YYYY-MM-DD                           # wiki only, auto-stamped on every write — last-touched, not an active verification; exposes page age for staleness hedging (#305)
provenance: <query/session>                    # wiki only, required (v5 §4.1 U3 traceability — the exploration that produced the page)
source: web-clipper|manual|...                 # capture only, optional
url: ...                                       # capture only, optional
```

**type opt-in** (v4 §2.2): a `type:` field is the marker that opts a note into claude-kit's management. Files without it remain invisible — users keep diary, book notes, free folders untouched.

## vault-bridge Hooks & Commands

vault-bridge registers 5 hook handlers + 3 slash commands. All hooks are **deterministic shell scripts** unless explicitly noted otherwise — no per-turn LLM cost.

**Read/write asymmetry (Write Role Contract)**: vault-bridge is a "haiku delivery" layer for **reads only**. Vault *reads* are delegated to the haiku `vault-searcher` agent; vault *writes* cannot be delegated — `pre-write-guard.sh` (default `enforce`) blocks subagent writes, so all writes are main-context user-initiated skills. Both vault-content ③ delivery adapters that vault-bridge once carried are now retired: the `session` adapter (`docs/design/output-adapter-contract.md` §2 row #5 — formerly `/save-session`) was **retired 2026-07-10 (#331)** when the session-knowledge path was redefined wiki-first (session knowledge → OVM `/wiki` + native memory), and the `handoff` adapter (row #4 — formerly `/handoff`, vault-bypassing) was **retired in G26 (decision G25 D4)**; the handoff function now lives in the machine-level `session-close` skill, outside claude-kit. vault-bridge's remaining write command is `/vault-commit` (git commit); vault *content* authoring (capture/note/wiki) belongs to obsidian-vault-manager. vault-bridge is still claude-kit's **③ delivery layer** (`claude-kit-boundary.md` line 26). Per the G3 #102 ADR the output layer is **distributed in-place**, so these delivery adapters live here rather than in a separate plugin.

**Vault root configuration** (all hooks + Python scripts share the same 3-level priority):
1. `VAULT_BRIDGE_VAULT_ROOT` env var — explicit runtime override (CI/scripts, highest priority)
2. `VAULT_BRIDGE_VAULT_PATH` env var — set from `userConfig.vault_path` in plugin settings
3. `~/vault` — built-in default. Tilde in either var is expanded to `$HOME`.

**Hooks**:

- **SessionStart** (`hooks/session-start-manifest.sh`, deterministic): incremental manifest refresh — checks staleness and updates `{vault_root}/.vault-bridge/manifest.json` only for changed files (background, never blocks session start).
- **PreToolUse Read|Grep|Glob** (`hooks/pre-access-guard.sh`, deterministic): emits `systemMessage` warning when the configured vault root is accessed directly. Soft warning, never blocks. As of v1.9.0, this hook exempts vault-searcher's own reads to avoid the self-reference loop that previously caused haiku to misinterpret its own warning as a denial.
- **PreToolUse Write|Edit** (`hooks/pre-write-guard.sh`, deterministic): validates vault file naming conventions AND enforces the **Write Role Contract** — the read/write asymmetry at the core of vault-bridge. Vault *reads* are haiku-delegable (the `vault-searcher` agent), but vault *writes* are NOT: they must be user-initiated (main context, executed by skills). Subagent vault writes (any non-empty agent identifier in the PreToolUse payload) are denied or warned per `VAULT_BRIDGE_WRITE_CONTRACT` mode (default `enforce` — deny; supports `warn` / `off`). Naming convention is log-only by default; `VAULT_BRIDGE_STRICT_NAMING=1` blocks on violation.

**Skills** (`skills/*/SKILL.md`; migrated from `commands/*.md` in #94):

- **`/vault-link`**: creates a `.vault-link` pointer file binding the current project to a vault location.
- **`/vault-manifest-refresh`**: forces a full manifest rebuild (skips staleness check).
- **`/vault-commit`**: commits uncommitted vault changes with user-approved message.

(`/handoff` was retired in G26 — the next-session continuation function moved to the machine-level `session-close` skill, outside claude-kit.)

The remaining hooks (deterministic SessionStart manifest refresh + PreToolUse guards) and explicit slash commands ensure zero per-turn LLM cost, no loops. The session-lifecycle auto-hooks (Stop capture suggestion, SessionEnd safety-net auto-save) were cut in G24; capture ore is written only via obsidian-vault-manager's explicit `/capture` command.

## Cross-Plugin MECE Boundaries

Skills across `obsidian-vault-manager` and `vault-bridge` share overlapping domains. Boundaries:

| Area | obsidian-vault-manager | vault-bridge |
|------|----------------------|--------------|
| Note creation | `note` skill (evergreen notes + decision records, `notes/`) | N/A |
| Session record | `/capture` (raw session ore → `inbox/`) · `wiki` (compiled session knowledge → `wiki/`) — `/save-session` retired #331, wiki-first | N/A (session-record command retired 2026-07-10 #331; `/vault-commit` commits the vault) |
| Domain context search | `vault-knowledge-manager` (direct mdfind/grep, OVM-internal) | `vault-searcher` Mode 2 (external, read-only lightweight) |

Within `thinking-tools`:
- `diverse-sampling`: creative generation (brainstorming, alternatives)
- `expert-panel`: evaluative debate (multi-perspective assessment, decision-making)
- Trigger "여러 관점" → `expert-panel` only (evaluative, not creative)

## Adding a New Skill

1. 해당 플러그인의 `skills/{skill-name}/SKILL.md` 생성
2. `plugin.json`의 `keywords`에 스킬명 추가
3. `description`/`keywords`를 바꿨다면 `marketplace.json`에 동기화 (`python3 scripts/check-version-sync.py --fix`). 버전은 직접 올리지 않습니다 — lockstep 릴리스(RELEASING.md)가 전 플러그인을 일괄 범프
4. 에이전트가 해당 스킬을 사용해야 하면: 에이전트 `.md`의 `skills:` frontmatter에 추가
5. **트리거 안내 컨벤션 (#173)** — 사용자 대면 카탈로그에 진입점을 추가해 발견성을 확보합니다: 루트 `README.md`의 플러그인 스킬 표(이럴 때 → 스킬) **(필수)**, 그리고 `docs/design/4-flow-catalog.md`의 "흐름별 대표 기능" **(4-흐름에 맞을 때만)**. 트리거 문구의 단일 소스는 SKILL.md `description`이고(thinking-tools는 `check-trigger-regression.py`가 드롭을 강제 감지), 카탈로그는 그걸 사용자 언어로 노출하는 뷰입니다.

## Adding a New Agent

1. 해당 플러그인의 `agents/{agent-name}.md` 생성 (frontmatter: name, description, model, skills)
2. `plugin.json`의 `keywords`에 에이전트명 추가
3. `description`/`keywords`를 바꿨다면 `marketplace.json`에 동기화 (`python3 scripts/check-version-sync.py --fix`). 버전은 직접 올리지 않습니다 — lockstep 릴리스(RELEASING.md)가 전 플러그인을 일괄 범프

## Version Sync Rule

`plugin.json`이 단일 소스(source of truth), `marketplace.json`은 거기서 derived입니다.
다음 필드는 항상 양쪽이 일치해야 하고, `check-version-sync.py`가 CI block 가드로 강제합니다:
- `version`, `description`, `keywords` (+ `name`은 매칭 키)

운영 규칙:
- **버전은 lockstep** — 모든 플러그인이 같은 버전을 공유하고, 단일 태그 `vX.Y.Z`로 함께
  배포됩니다. 개별 작업에서 버전을 직접 올리지 마세요. 릴리스 워크플로가 `bump-version.py`로
  전 매니페스트(4개 `plugin.json` + `marketplace.json` 루트·항목)를 한 번에 같은 값으로 씁니다.
- **drift 동기화**: `description`/`keywords`를 `plugin.json`에서 바꿨다면
  `python3 scripts/check-version-sync.py --fix`로 `marketplace.json`을 맞춥니다 (plugin.json이 이김).
- 자세한 버전 정책·릴리스 절차: [RELEASING.md](RELEASING.md).

## Adding a New Plugin

1. `{plugin-name}/` 디렉토리 생성
2. `{plugin-name}/.claude-plugin/plugin.json` 작성
3. `{plugin-name}/skills/` 하위에 스킬 추가
4. `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목 추가 (`source` 경로 지정)
5. `{plugin-name}/README.md` 작성
6. 루트 `README.md`에 플러그인 소개 추가
