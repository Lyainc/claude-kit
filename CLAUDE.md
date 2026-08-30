# CLAUDE.md (for claude-kit contributors)

This file provides guidance to Claude Code when **developing/contributing to this repository**. Runtime behavior rules (how Claude should act when these plugins are active in external projects) live in each plugin's agent/skill `description` fields, which are the single source of truth for runtime delegation.

Design Principles & boundary: the single source of truth for the claude-kit↔harness boundary (evolutionary boundary A), the 5-layer model, and the one-way dependency rule is `docs/design/claude-kit-boundary.md`.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 네 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 9개 + 에이전트 2개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, adversarial-review, build-spec, issue-raise, next-goal + thinking-facilitator, requirement-gap-reviewer agents)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 (vault-knowledge-manager, vault-file-organizer) + 스킬 3개 (wiki, audit, base — 입구 `/capture`·`/note`는 #480으로 retire, vault-bridge `/vault-save`가 승계) + reference docs (`reference/vault-audit-rules.md`, `reference/obsidian-bases-schema.md` 등) + shell primitives (`scripts/ovm-primitives.sh`). wiki = v5 A-layer LLM wiki 컴파일(`vault/wiki/`, AI recall 主, provenance 추적, 게이트된 명시 액션).
- **vault-bridge** (`vault-bridge/`): Obsidian vault I/O 브릿지 플러그인 — 에이전트 1개 (vault-searcher, haiku) + 훅 2종 (SessionStart / PreToolUse Write|Edit|Bash) + 스킬 4개 (`/vault-save`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`) + Python scripts (`generate-manifest.py`, `vault-commit-message.py`). vault 검색 + git 커밋. vault 참고자료 입구(`/vault-save`)는 이 플러그인, 컴파일(`/wiki`)은 OVM 소유.
- **feedback-loop** (`feedback-loop/`): layer ⑤ 자기개선 루프 (measure→review→keep, **실행/이터레이션 엔진 아님** — ⑤ 하네스에서 분리된 **외부 배포** 단위). 스킬 3개 (retro — telemetry 낭비 패턴 user-confirmed 이슈화(action 단일 출력) + dedup / distill — 세션 절차 기법의 user-confirmed **발견**: 자연어 제안 객체 emit, 저작은 안 함(매립은 add-policy 소유) / add-policy — **매립 엔진**: 자연어 규칙·distill 제안을 분류해 매립지 3개(CLAUDE.md/hook/skill) 중 한 곳에 1클릭 배치, 머신-중립·커밋 안 함, user-authored 스킬 inviolable) + telemetry 흡수 (event-logger hooks 8 event-type, report.py lifecycle, opt-in `CLAUDE_KIT_TELEMETRY=1` 아니면 silent·per-turn LLM 0·외부 유출 0). **단방향 의존(CON-5)**: feedback-loop은 leaf OUTPUT(audit·manifest·telemetry events)만 읽고 leaf code import 0; 외부 배포지만 ⑤ harness 계열(배포단위≠레이어).

변경 이력(마이그레이션·retire·컷 결정, 이슈 번호): [docs/REFERENCE.md](docs/REFERENCE.md#project-overview--변경-이력).

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
- **WIP across rebases**: stash unrelated WIP (`.gitignore`, untracked files etc.) with `git stash push -u -m <msg> -- <paths>` before rebasing, restore after. Rebasing with a dirty tree fails.
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

전체 디렉토리 트리: [docs/REFERENCE.md](docs/REFERENCE.md#directory-structure).

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
# effort: low                   # 선택: reasoning effort 오버라이드 (low|medium|high|xhigh|max) — 티어 다운그레이드(model:)보다 이걸 우선 (#448)
---
```

## Vault File Conventions

Files written to `~/vault/` by OVM or vault-bridge follow a unified convention (vault second brain v4, extended by v5 — see `docs/design/vault-second-brain-v4.md` and `docs/design/vault-second-brain-v5.md`). Folder layout, filename pattern, and the frontmatter schema table: [docs/REFERENCE.md](docs/REFERENCE.md#vault-file-conventions).

## vault-bridge Hooks & Skills

vault-bridge registers 2 hook handlers (SessionStart manifest refresh, PreToolUse Write|Edit|Bash write-role-contract enforcement) + 4 skills (`/vault-save`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`). All hooks are deterministic shell scripts — no per-turn LLM cost. Full hook/skill detail + the Write Role Contract (vault reads are haiku-delegable, writes are not): [docs/REFERENCE.md](docs/REFERENCE.md#vault-bridge-hooks--skills).

## Cross-Plugin MECE Boundaries

Skills across `obsidian-vault-manager` and `vault-bridge` share overlapping domains. Boundaries:

| Area | obsidian-vault-manager | vault-bridge |
|------|----------------------|--------------|
| 참고자료 저장 (B 입구) | N/A (#480으로 `/capture`·`/note` retire) | `/vault-save` — 원문 → `sources/`, 내가 쓴 것 → `notes/`, status 없음·provenance 필수 |
| Session record | `wiki` (compiled session knowledge → `wiki/`) — `/save-session` retired #331, wiki-first | `/vault-save` (raw session ore → `sources/`); `/vault-commit` commits the vault |
| Domain context search | `vault-knowledge-manager` (direct mdfind/grep, OVM-internal) | `vault-searcher` Mode 2 (external, read-only lightweight) |

Within `thinking-tools`:
- `diverse-sampling`: creative generation (brainstorming, alternatives)
- `expert-panel`: evaluative debate (multi-perspective assessment, decision-making)
- Trigger "여러 관점" → `expert-panel` only (evaluative, not creative)

## Adding a New Skill

1. 해당 플러그인의 `skills/{skill-name}/SKILL.md` 생성
2. **`allowed-tools:`를 명시** (#611) — 생략하면 하네스에 연결된 도구 전부를 상속합니다 (에이전트 `tools:`와 같은 #472 위험). 본문이 실제로 호출하는 도구만 나열하세요. `scripts/check-agent-tools-usage.py`가 에이전트와 같은 양방향 검사를 스킬에도 적용합니다: 선언에만 있고 본문이 이름을 안 부르면 UNUSED, 본문이 부르는데 선언에 없으면 UNDECLARED, 키 자체가 없으면 MISSING. 코드펜스 안은 근거로 안 쳐주므로, 셸 커맨드로만 쓰는 `Bash`도 본문 산문에 이름을 적으세요.
3. `plugin.json`의 `keywords`에 스킬명 추가
4. `description`/`keywords`를 바꿨다면 `marketplace.json`에 동기화 (`python3 scripts/check-version-sync.py --fix`). 버전은 직접 올리지 않습니다 — lockstep 릴리스(RELEASING.md)가 전 플러그인을 일괄 범프
5. 에이전트가 해당 스킬을 사용해야 하면: 에이전트 `.md`의 `skills:` frontmatter에 추가
6. **트리거 안내 컨벤션 (#173)** — 사용자 대면 카탈로그에 진입점을 추가해 발견성을 확보합니다: 루트 `README.md`의 플러그인 스킬 표(이럴 때 → 스킬) **(필수)**, 그리고 `docs/design/4-flow-catalog.md`의 "흐름별 대표 기능" **(4-흐름에 맞을 때만)**. 트리거 문구의 단일 소스는 SKILL.md `description`이고(각 플러그인의 `check-trigger-regression.py`가 드롭을 강제 감지), 카탈로그는 그걸 사용자 언어로 노출하는 뷰입니다.

## Adding a New Agent

1. 해당 플러그인의 `agents/{agent-name}.md` 생성 (frontmatter: name, description, model, skills)
2. **`tools:`를 명시** (#472) — 생략하면 하네스에 연결된 도구 전부를 상속합니다. 에이전트 본문이 실제로 호출하는 도구만 나열하세요 (Bash 커맨드·Read·Grep·Glob·Write 등을 본문에서 grep해 확인). `scripts/check-agent-tools-field.py`가 `tools:` 필드 존재를, `scripts/check-agent-tools-usage.py`가 선언 목록과 본문 사용의 일치를 양방향으로 검사합니다 (#577). 후자는 본문이 도구를 **이름으로 언급**해야 근거로 인정하므로, 셸 커맨드로만 쓰는 도구도 본문에 이름을 적으세요.
3. `plugin.json`의 `keywords`에 에이전트명 추가
4. `description`/`keywords`를 바꿨다면 `marketplace.json`에 동기화 (`python3 scripts/check-version-sync.py --fix`). 버전은 직접 올리지 않습니다 — lockstep 릴리스(RELEASING.md)가 전 플러그인을 일괄 범프

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
