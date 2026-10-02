# Contributor procedures

Read the relevant section when changing plugin definitions or handling PRs.
Shared always-loaded conventions live in `../AGENTS.md`. This file is not a runtime router.

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


## SKILL.md Frontmatter

```yaml
---
name: skill-name              # 필수: kebab-case
description: "One-line summary"  # Required: skill purpose + usage example
allowed-tools: Read Write Bash  # 필수: 스킬이 사용하는 도구 목록
# context: fork                # Optional: fresh skill subagent, not a conversation-history fork
# agent: Explore               # 선택: fork 시 사용할 에이전트 타입
# model: haiku                 # 선택: 스킬 실행 시 사용할 모델 (haiku|sonnet|opus|inherit)
# effort: low                   # 선택 — 캐시 영향은 환경마다 달라요, 아래 설명(#751·#770) 참고
---
```

`effort:`의 캐시 영향은 실행 환경마다 달라요 (#751, #770). Claude Code 문서(2026-09-30 확인)를 보면 Sonnet 5.5·Opus 5.5를 Claude 구독이나 Anthropic API 키로 쓸 때는 effort를 바꿔도 캐시가 유지돼요. Amazon Bedrock·Google Cloud Agent Platform·Claude apps gateway, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`, HIPAA 구성은 예외라서, 여기서는 SKILL.md `effort:`가 세션 ambient와 다르면 메인 messages 캐시가 다시 만들어질 수 있어요. #751의 캐시 붕괴 측정은 Opus 5·Sonnet 5 시절 기록이라 5.5에 그대로 옮기지 않아요. 그래서 일반 5.5 환경에서는 캐시 보호만을 이유로 SKILL.md `effort:`를 빼거나 서브에이전트로 옮기지 않고, 품질과 전체 사용량으로 정해요. 예외 환경이면 모델 전환·TTL 만료·압축 같은 다른 원인을 통제하고 확인한 다음에 정해요. 에이전트 정의(`*/agents/*.md`)의 `effort:`와 Workflow `agent()`의 `opts.effort`는 서브에이전트 자체 컨텍스트라 어느 환경에서든 메인 캐시와 무관해요.

## Vault File Conventions

Files written to `~/vault/` by OVM or vault-bridge follow a unified convention (vault second brain v4, extended by v5 — see `docs/design/vault-second-brain-v4.md` and `docs/design/vault-second-brain-v5.md`). Folder layout, filename pattern, and the frontmatter schema table: [docs/REFERENCE.md](REFERENCE.md#vault-file-conventions).

## vault-bridge Hooks & Skills

vault-bridge registers 2 hook handlers (SessionStart manifest refresh, PreToolUse Write|Edit|Bash write-role-contract enforcement) + 5 skills (`/vault-save`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`, `/wiki`). All hooks are deterministic shell scripts — no per-turn LLM cost. Full hook/skill detail + the Write Role Contract (vault reads are haiku-delegable, writes are not): [docs/REFERENCE.md](REFERENCE.md#vault-bridge-hooks--skills).

## Cross-Plugin MECE Boundaries

Use [skill-boundaries.md](skill-boundaries.md) to review ownership changes. Actual runtime
triggers remain in each skill/agent description; do not add a second routing table here.

## Adding a New Skill

1. 해당 플러그인의 `skills/{skill-name}/SKILL.md` 생성
2. **`allowed-tools:`를 명시** (#611) — 생략하면 하네스에 연결된 도구 전부를 상속합니다 (에이전트 `tools:`와 같은 #472 위험). 본문이 실제로 호출하는 도구만 나열하세요. `scripts/check-agent-tools-usage.py`가 에이전트와 같은 양방향 검사를 스킬에도 적용합니다: 선언에만 있고 본문이 이름을 안 부르면 UNUSED, 본문이 부르는데 선언에 없으면 UNDECLARED, 키 자체가 없으면 MISSING. 코드펜스 안은 근거로 안 쳐주므로, 셸 커맨드로만 쓰는 `Bash`도 본문 산문에 이름을 적으세요.
3. `.claude-plugin/plugin.json`의 `keywords`에 스킬명 추가
4. Claude `description`/`keywords`를 바꿨다면 `.claude-plugin/marketplace.json`에 동기화 (`python3 scripts/check-version-sync.py --fix`). Codex root `plugin.json` 메타데이터는 별도로 관리합니다. 버전은 직접 올리지 않습니다 — lockstep 릴리스(RELEASING.md)가 전 플러그인을 일괄 범프
5. 에이전트가 해당 스킬을 사용해야 하면: 에이전트 `.md`의 `skills:` frontmatter에 추가
6. **트리거 안내 컨벤션 (#173)** — 사용자 대면 카탈로그에 진입점을 추가해 발견성을 확보합니다: 루트 `README.md`의 플러그인 스킬 표(이럴 때 → 스킬) **(필수)**, 그리고 `docs/design/4-flow-catalog.md`의 "흐름별 대표 기능" **(4-흐름에 맞을 때만)**. 트리거 문구의 단일 소스는 SKILL.md `description`이고(각 플러그인의 `check-trigger-regression.py`가 드롭을 강제 감지), 카탈로그는 그걸 사용자 언어로 노출하는 뷰입니다.

## Adding a New Agent

1. 해당 플러그인의 `agents/{agent-name}.md` 생성 (frontmatter: name, description, model, skills)
2. **`tools:`를 명시** (#472) — 생략하면 하네스에 연결된 도구 전부를 상속합니다. 에이전트 본문이 실제로 호출하는 도구만 나열하세요 (Bash 커맨드·Read·Grep·Glob·Write 등을 본문에서 grep해 확인). `scripts/check-agent-tools-field.py`가 `tools:` 필드 존재를, `scripts/check-agent-tools-usage.py`가 선언 목록과 본문 사용의 일치를 양방향으로 검사합니다 (#577). 후자는 본문이 도구를 **이름으로 언급**해야 근거로 인정하므로, 셸 커맨드로만 쓰는 도구도 본문에 이름을 적으세요.
3. `.claude-plugin/plugin.json`의 `keywords`에 에이전트명 추가
4. Claude `description`/`keywords`를 바꿨다면 `.claude-plugin/marketplace.json`에 동기화 (`python3 scripts/check-version-sync.py --fix`). Codex root `plugin.json` 메타데이터는 별도로 관리합니다. 버전은 직접 올리지 않습니다 — lockstep 릴리스(RELEASING.md)가 전 플러그인을 일괄 범프

## Version Sync Rule

Claude `.claude-plugin/plugin.json`이 Claude marketplace의 단일 source of truth이고,
`.claude-plugin/marketplace.json`은 거기서 derived입니다. Codex root `plugin.json`은
portable metadata를 소유하며 Claude manifest와 `name`/`version`만 lockstep입니다.
다음 필드는 항상 양쪽이 일치해야 하고, `check-version-sync.py`가 CI block 가드로 강제합니다:
- `version`, `description`, `keywords` (+ `name`은 매칭 키)

운영 규칙:
- **버전은 lockstep** — 모든 플러그인이 같은 버전을 공유하고, 단일 태그 `vX.Y.Z`로 함께
  배포됩니다. 개별 작업에서 버전을 직접 올리지 마세요. 릴리스 워크플로가 `bump-version.py`로
  전 매니페스트(4개 root portable manifest + 4개 Claude manifest + Claude marketplace)를 한 번에 같은 값으로 씁니다.
- **drift 동기화**: Claude `description`/`keywords`를 `.claude-plugin/plugin.json`에서 바꿨다면
  `python3 scripts/check-version-sync.py --fix`로 `.claude-plugin/marketplace.json`을 맞춥니다 (Claude manifest가 이김).
- 자세한 버전 정책·릴리스 절차: [RELEASING.md](../RELEASING.md).

## Adding a New Plugin

1. `{plugin-name}/` 디렉토리 생성
2. `{plugin-name}/plugin.json`에 portable Codex metadata 작성
3. `{plugin-name}/.claude-plugin/plugin.json`에 Claude metadata 작성 (`name`/`version`은 portable manifest와 lockstep)
4. `{plugin-name}/skills/` 하위에 스킬 추가
5. `.claude-plugin/marketplace.json`과 `.agents/plugins/marketplace.json`의 `plugins` 배열에 항목 추가 (각 source 경로·Codex policy/category 포함)
6. `{plugin-name}/README.md` 작성
7. 루트 `README.md`에 플러그인 소개 추가
