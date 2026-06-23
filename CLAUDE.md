# CLAUDE.md (for claude-kit contributors)

This file provides guidance to Claude Code when **developing/contributing to this repository**. Runtime behavior rules (how Claude should act when these plugins are active in external projects) live in each plugin's agent/skill `description` fields, which are the single source of truth for runtime delegation.

Codex/OMX parity note: the Codex-active migration of this root guidance lives in `AGENTS.md`, with the surface-by-surface parity matrix in `docs/codex-claude-parity.md`.

Design Principles & boundary: the single source of truth for the claude-kit↔harness boundary (evolutionary boundary A), the 5-layer model, the one-way dependency rule, and the constitutional/policy rule lists is `docs/design/claude-kit-boundary.md`. Downstream specs (#100 goal-doc schema, #122 thin harness, #125 3-tier rules) reference it — they do not redefine these rules here.

## Project Overview

**claude-kit**: Claude Code 스킬 플러그인 마켓플레이스. 네 개의 독립 플러그인을 포함합니다.

- **thinking-tools** (`thinking-tools/`): 사고 도구 스킬 8개 + 에이전트 1개 (diverse-sampling, doc-concretize, doc-polish, expert-panel, unknown-discovery, thought-chain, adversarial-review, spec-first + thinking-facilitator agent)
- **obsidian-vault-manager** (`obsidian-vault-manager/`): Obsidian vault 지식 관리 — 에이전트 2개 (vault-knowledge-manager, vault-file-organizer) + 스킬 5개 (capture, note, wiki, audit, base) + reference docs (`reference/vault-audit-rules.md`, `reference/obsidian-bases-schema.md` 등) + shell primitives (`scripts/ovm-primitives.sh`). wiki = v5 A-layer LLM wiki 컴파일(`vault/wiki/`, AI recall 主, provenance 추적, 게이트된 명시 액션).
- **vault-bridge** (`vault-bridge/`): Obsidian vault I/O 브릿지 플러그인 — 에이전트 1개 (vault-searcher, haiku) + 훅 5종 (Stop / SessionEnd command+prompt / SessionStart / PreToolUse Read|Grep|Glob / PreToolUse Write|Edit) + 슬래시 커맨드 5개 (`/save-session`, `/vault-link`, `/vault-manifest-refresh`, `/vault-commit`, `/handoff`) + Python scripts (`generate-manifest.py`, `vault-commit-message.py`). vault 검색 + slash command 기반 session-note/capture 작성 + 세션 생명주기 안전망.
- **feedback-loop** (`feedback-loop/`): layer ⑤ 자기개선 루프 (measure→review→keep, **실행/이터레이션 엔진 아님** — #217로 ⑤ 하네스에서 분리된 **외부 배포** 단위). 스킬 3개 (retro — audit E8 user-confirmed 승격 + 3갈래 출력 + dedup + 회고예산, #123 / distill — 세션 절차 기법의 user-confirmed **발견**: 자연어 제안 객체 emit, 저작은 안 함(매립은 add-policy 소유), SIS 이식, #202 / add-policy — **매립 엔진**(G19/#255): 자연어 규칙·distill 제안을 분류해 매립지 3개(CLAUDE.md/hook/skill) 중 한 곳에 1클릭 배치, 머신-중립·커밋 안 함, user-authored 스킬 inviolable) + telemetry 흡수 (event-logger hooks 8 event-type, report.py lifecycle, opt-in `CLAUDE_KIT_TELEMETRY=1` 아니면 silent·per-turn LLM 0·외부 유출 0). **단방향 의존(CON-5)**: feedback-loop은 leaf OUTPUT(audit·manifest·telemetry events)만 읽고 leaf code import 0; 외부 배포지만 ⑤ harness 계열(배포단위≠레이어).
- **dev-harness** (`dev-harness/`): layer ⑤ 개발 거버넌스 (claude-kit 자체 빌드 전용 — **DEV-ONLY, marketplace 미등록**, #217). 스킬 2개 (handoff-plan — 열린 이슈 의존·도메인 청킹 → user-confirmed 에픽 후보 → goal-doc 슬라이스 바인딩, #171 / slice-router — goal-doc 실행 라우터: #100 스키마 검증(INV-4) + 4종 work_type 슬라이스 라우팅 + D5 헌법 invariant enforcement, #183). `workflows/feature-full.js` (#201): feature-full DELEGATE carrier — impl→critique를 별도 agent() 스테이지로 분리하는 workflow script (structural CON-3). **단방향 의존(CON-5)**: dev-harness → leaf(vault-bridge·obsidian-vault-manager) + feedback-loop(rule_fire emit-only 데이터 계약). 역방향 금지. 전체 OMC-strangler 아닌 thin 진입.

## Git Conventions

- **Commits**: English, Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
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
│   └── scripts/                         # ovm-primitives.sh, audit-validate.py, gen-fixture.sh
├── vault-bridge/                        # plugin: vault-bridge
│   ├── .claude-plugin/plugin.json
│   ├── agents/                          # vault-searcher (haiku, 3 modes, read-only)
│   ├── commands/                        # 5개 슬래시 커맨드 정의
│   ├── hooks/                           # 5개 hook handler (stop-check, session-end-pre, session-start-manifest, pre-access-guard, pre-write-guard)
│   └── scripts/                         # generate-manifest.py + tests/
├── feedback-loop/                       # plugin: feedback-loop (⑤ 자기개선, 외부 배포 — #217)
│   ├── .claude-plugin/plugin.json       # hooks 키: 8 event-type 등록 (opt-in telemetry)
│   ├── skills/                          # retro (#123 — E8 승격 + 3갈래 출력 + dedup + 회고예산)
│   ├── scripts/                         # telemetry: event-logger.sh, report.py, sequence.py, validate-schema.py, plugin-map.json + test/
│   └── README.md                        # measure→review→keep, opt-in·local-only·per-turn LLM 0
├── dev-harness/                         # layer ⑤ dev-거버넌스 (DEV-ONLY, marketplace 미등록 — #217)
│   ├── .claude-plugin/plugin.json       # OPTIONAL (dev-only; marketplace 미등록 — anti-drift fence 강제)
│   ├── skills/                          # handoff-plan (#171), slice-router (#183)
│   ├── workflows/                       # feature-full.js (#201 DELEGATE carrier: impl→critique separate agent() stages)
│   ├── scripts/                         # slice_router.py (Gap-ROUTE), invariant_guard.py (Gap-INV) + test/
│   └── README.md                        # 단방향 의존(CON-5) dev-harness→leaf+feedback-loop 명시
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
python3 -m json.tool feedback-loop/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool dev-harness/.claude-plugin/plugin.json > /dev/null

# 마켓플레이스 거버넌스 가드 (#134): version-sync drift(block) + CI 커버리지(block — #175 --strict 승격)
python3 scripts/check-version-sync.py --self-test
# Expected: OK: all 7 version-sync self-test cases passed (+ missing-manifest mode + --fix reconcile check + dev-drift fence)
# (#217 anti-drift fence: a dev-only token — e.g. dev-harness — appearing in marketplace.plugins[] FAILs)
python3 scripts/check-version-sync.py
# Expected: OK: version-sync clean — 4 plugin(s), no drift (drift 시 exit 1, manifest 누락 시 exit 3 = 릴리스 차단)
# marketplace.json은 plugin.json에서 derived — drift 시 `--fix`로 plugin.json 기준 동기화:
#   python3 scripts/check-version-sync.py --fix
python3 scripts/check-ci-coverage.py --self-test
# Expected: OK: all check-ci-coverage self-test cases passed
python3 scripts/check-ci-coverage.py
# Expected: "CI coverage: N/N ... OK: every registered test is wired into CI." (gap=0).
# CI runs this as `check-ci-coverage.py --strict` (#175): a coverage gap now BLOCKS
# (warn-mode 도입은 #134, gap 0 도달 후 #175에서 --strict 승격).

# 작업 규칙 minimal core 가드 (#216): claude-kit 특화 결정론 가드 + 외부 린터 위임.
# 각 check는 --self-test(인메모리 위반+clean fixture)로 검증, 실모드는 레포 스캔 FP=0.
# 규칙 본문/정책vs취향 기준은 rules/RULES.md, 재발 시 RCA는 rules/rca-checklist.md.
python3 scripts/check-type-optin.py --self-test
# Expected: OK: all check-type-optin self-test cases passed
python3 scripts/check-type-optin.py
# Expected: OK: check-type-optin clean — N markdown file(s) checked, ... no missing `type:`
python3 scripts/check-language-policy.py --self-test
# Expected: OK: all check-language-policy self-test cases passed
python3 scripts/check-language-policy.py
# Expected: OK: language-policy clean — 8 metadata source(s) checked, no Hangul ...
python3 scripts/check-banned-words.py --self-test
# Expected: OK: all check-banned-words self-test cases passed
python3 scripts/check-banned-words.py
# Expected: OK: banned-words clean — N file(s) checked, no violations (terms from rules/banned-terms.txt)
python3 scripts/check-test-exitcode.py --self-test
# Expected: OK: all check-test-exitcode self-test cases passed
# (real mode `python3 scripts/check-test-exitcode.py` RUNS every registered Validation
#  command — local pre-push convenience; intentionally NOT wired into CI to avoid re-running
#  the suite recursively. `--list` prints the extracted commands without running them.)
python3 scripts/run-linters.py --self-test
# Expected: OK: all run-linters self-test cases passed
# (real mode `python3 scripts/run-linters.py` delegates to ruff/prettier/shellcheck IF
#  installed + configured, else graceful-skips; style/taste lives in ruff.toml/.prettierrc,
#  never hardcoded — #216 c4/c6.)

# 서브에이전트 git 부수효과 가드 회귀 (#209): scripts/subagent-git-guard.sh PreToolUse Bash
# 훅이 subagent context의 git commit/push·gh pr create|merge를 deny하는지 검증 (인메모리
# 위반 + clean fixture, FP=0; 메인 컨텍스트·git 읽기·따옴표 멘션은 통과). 규칙은 rules/RULES.md §1.
# 활성화는 per-developer: rules-checklist-hook.sh처럼 .claude/settings.json에 PreToolUse(Bash)로
# 직접 배선 (스니펫은 scripts/subagent-git-guard.sh 헤더 주석 참조 — .claude/는 gitignore).
python3 scripts/test/test-subagent-git-guard.py
# Expected: OK: all cases passed

# no-PyYAML guard 회귀 (#259 review P1): scripts/no-pyyaml-guard.sh가 .py 쓰기의 PyYAML
# import를 deny + (telemetry opt-in 시) rule_fire emit하는지 — deny/allow/warn/off + regex
# 경계(yamllint 등 FP) + emit on/off. G19 add-policy dogfood 산출이자 G20 rule_fire reference
# emitter라, 다른 가드(subagent-git-guard/event-logger)처럼 회귀 게이트를 보유.
bash scripts/test/test-no-pyyaml-guard.sh
# Expected: OK: all no-pyyaml-guard cases passed (12)

# 릴리스 도구 self-test (lockstep bump + 플러그인별 노트 생성) — RELEASING.md 참조
python3 scripts/bump-version.py --self-test
# Expected: OK: all bump-version self-test cases passed
python3 scripts/gen-release-notes.py --self-test
# Expected: OK: all gen-release-notes self-test cases passed

# 플러그인 스펙 전체 검증 (frontmatter·hooks 스키마 포함)
# claude plugin validate  # Claude Code 설치 환경에서 실행

# 스킬 파일 존재 확인
find thinking-tools/skills -name "SKILL.md" | sort
find obsidian-vault-manager/skills -name "SKILL.md" | sort

# vault-bridge pre-write-guard regression (Write Role Contract + naming, incl. notes/*.base ext for #118 /base skill)
python3 vault-bridge/scripts/test/test-pre-write-guard.py

# vault-bridge pre-access-guard regression (vault-searcher self-exemption + counter)
python3 vault-bridge/scripts/test/test-pre-access-guard.py

# vault-bridge manifest type opt-in regression (v4 §2.2)
python3 vault-bridge/scripts/test/test-manifest-type-optin.py

# vault-commit message generation (status-transition aware)
python3 vault-bridge/scripts/test/test-vault-commit-message.py
# Expected: OK: all cases passed (currently 14 cases)

# feedback-loop telemetry schema self-test (#217 — telemetry absorbed into feedback-loop)
python3 feedback-loop/scripts/validate-schema.py --self-test

# feedback-loop report.py latency_by_event regression gate (#164)
# + per-skill lifecycle view (never-fired / stale / bottom-N vs */skills/*/SKILL.md catalog, #203)
python3 feedback-loop/scripts/test/test-report.py
# Expected: OK: all cases passed
# event-logger meta-extractor unit test (extract_end_meta / extract_stop_meta)
bash feedback-loop/scripts/test/test-event-logger.sh
# Expected: OK: all event-logger meta-extractor cases passed

# dev-harness slice router + D5 invariant guard (#183 — Gap-ROUTE + Gap-INV; #217 → dev-harness)
# test-router: 4-way work_type routing (feature-full/decision-only/doc-only/bug-light)
# + INV-4 block + native-fallback. test-invariant: one negative case per
# constitutional invariant (INV-4 schema / INV-1 new-file-only / INV-2·3 isolated
# critique / INV-5 one-way). Both also dogfood the real G16 goal-doc (repo-root, parents[1]).
python3 dev-harness/scripts/test/test-router.py
# Expected: OK: all 11 cases passed
python3 dev-harness/scripts/test/test-invariant.py
# Expected: OK: all 42 cases passed
# (+5 static checks for #201 feature-full.js: agentType disjoint / VERDICT schema /
#  separate agent() stages / CON-3 runtime assert / forbidden resume-breaking APIs)

# thinking-tools trigger-regression check (run after editing any SKILL.md description)
# Self-test the extractor:
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 9 self-test cases passed
# Diff trigger sets between a base ref and the working tree (exit 1 = removals found):
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
# A char-count check does NOT catch dropped triggers; ALWAYS run this when slimming
# descriptions. Removals are reported (not hard-gated) — reviewer decides if intentional.
# Restore any CLAUDE.md-mandated trigger (e.g. expert-panel "다양한 관점에서 평가해줘").

# expert-panel mode-compose regression (#228) — verifies the SKILL.md's "all combinations
# compose silently" claim: every declared mode toggle (격리/요약 + citation grounding +
# Phase 2 inline path) is described and non-contradictory. Run after editing expert-panel
# mode/Phase structure or the Citation Contract.
python3 thinking-tools/scripts/test/test-mode-compose.py --self-test
# Expected: OK: all 16 self-test cases passed
python3 thinking-tools/scripts/test/test-mode-compose.py
# Expected: OK: all 9 mode-compose checks passed. (static check against the live SKILL.md)

# Shell hook syntax check
bash -n vault-bridge/hooks/*.sh
bash -n feedback-loop/scripts/event-logger.sh
bash -n scripts/rules-checklist-hook.sh   # #216 work-rules task-end reminder hook
bash -n scripts/subagent-git-guard.sh     # #209 subagent git side-effect deny hook
bash -n scripts/no-pyyaml-guard.sh        # #259 no-PyYAML guard (add-policy dogfood + rule_fire emitter)

# parse_created_date unit test (audit-validate Phase 2 helper)
python3 obsidian-vault-manager/scripts/test/test-parse-created-date.py
# Expected: OK: all 13 cases passed

# git activity summary unit test
python3 obsidian-vault-manager/scripts/test/test-git-activity.py
# Expected: OK: all 18 cases passed

# read_manifest_summary schema_version gate (None vs 0 semantics)
python3 obsidian-vault-manager/scripts/test/test-read-manifest-summary.py
# Expected: OK: all cases passed (7 cases)

# E8 promotion candidate finding regression
python3 obsidian-vault-manager/scripts/test/test-promotion-finding.py
# Expected: OK: all 8 cases passed

# E2 auto-fix tag inference regression (#127)
python3 obsidian-vault-manager/scripts/test/audit-validate.py --infer-self-test
# Expected: OK: all 6 infer-tags cases + E2 auto-fix simulation passed

# infer-tags batch-mode regression (#152, shell-level — complements --infer-self-test:
# covers multi-path/stdin array shape, partial-failure exit codes, and the security
# hard-fail for traversal / out-of-vault paths that the Python reference impl can't reach)
bash obsidian-vault-manager/scripts/test/test-infer-tags-batch.sh
# Expected: OK: all infer-tags batch cases passed

# E9 vocabulary pairs unit test + ovm-primitives↔audit-validate parser parity gate (#165)
python3 obsidian-vault-manager/scripts/test/test-vocabulary-pairs.py
# Expected: OK: all cases passed

# audit DoD 측정 (mechanical reference impl)
# gen-fixture.sh --with-audit-errors now internally calls generate-manifest.py
# and patches access_count=5 for the E8 access-target seed.
rm -rf /tmp/ovm-fixture-audit-recheck
OVM_FIXTURE_DIR=/tmp/ovm-fixture-audit-recheck \
  bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod > /tmp/dod.json
# Assert the date-independent DoD invariants (#175 — the CI `audit-dod` job runs this
# exact gate; `--dod` itself always exits 0, assert-dod.py turns it into a real gate).
python3 obsidian-vault-manager/scripts/test/assert-dod.py /tmp/dod.json
# Expected: OK: audit DoD invariants hold (...)
# Expected (G8+) — the values assert-dod.py enforces:
#   dod.seeded_detected = {E1:5, E2:10, E3:5, E4:5, E5:6, E6:5, E7:5, E8:2, E9:2, E10:5, E11:5}
#     (E2 has 10: 5 base + 5 status-missing; E5 has 6: 5 w/ tag candidates +
#      1 empty-tags graceful orphan; E6=stale_inbox; E7=stale_draft;
#      E8 has 2: promotion-target via refs_in=3, access-target via manifest patch;
#      E9 has 2: vault-level vocabulary pairs (E9a api/apis singular-plural +
#      E9b sourceUrl/source_url camel/snake), path-less findings, P2/no-autofix,
#      counted per pair, FP-guarded by both forms appearing in >=3 files;
#      E10=misplaced_file (type:session in notes/); E11=unstructured_path
#      (2 root-direct + 3 in 20_Projects/), root _index.md exempt)
#   dod.fp_on_clean per type = 0   (incl. E9/E10/E11; root _index.md exercises E11 exempt guard)
#   dod.findings_missing_priority = 0
#   dod.priority_mismatches = []
#   dod.e3_with_suggestion >= 5    (E3 권장 파일명 present); dod.e5_with_candidates > 0
#   dod.e2_tags_missing = 10; dod.e2_with_inferred_tags = 10   (#127 — every E2
#     tags-missing finding carries a deterministic inferred tag proposal)
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
provenance: <query/session>                    # wiki only, required (v5 §4.1 U3 traceability — the exploration that produced the page)
source: web-clipper|manual|...                 # capture only, optional
url: ...                                       # capture only, optional
```

**type opt-in** (v4 §2.2): a `type:` field is the marker that opts a note into claude-kit's management. Files without it remain invisible — users keep diary, book notes, free folders untouched.

## vault-bridge Hooks & Commands

vault-bridge registers 5 hook handlers + 5 slash commands. All hooks are **deterministic shell scripts** unless explicitly noted otherwise — no per-turn LLM cost.

**Read/write asymmetry (Write Role Contract)**: vault-bridge is a "haiku delivery" layer for **reads only**. Vault *reads* are delegated to the haiku `vault-searcher` agent; vault *writes* cannot be delegated — `pre-write-guard.sh` (default `enforce`) blocks subagent writes, so all writes are main-context user-initiated slash commands. The write-authoring slash commands are the runtime entry points for the output-adapter contract (`docs/design/output-adapter-contract.md` §2): `/save-session` is the `session` **③ delivery** adapter (row #5 — vault delivery, `gated`), and `/handoff` implements the `handoff` adapter but is **vault-bypassing** (row #4 — outside ③ delivery, not CON-1 gated). vault-bridge is claude-kit's **③ delivery layer** (`claude-kit-boundary.md` line 26). Per the G3 #102 ADR the output layer is **distributed in-place**, so these delivery adapters live here rather than in a separate plugin.

**Vault root configuration** (all hooks + Python scripts share the same 3-level priority):
1. `VAULT_BRIDGE_VAULT_ROOT` env var — explicit runtime override (CI/scripts, highest priority)
2. `VAULT_BRIDGE_VAULT_PATH` env var — set from `userConfig.vault_path` in plugin settings
3. `~/vault` — built-in default. Tilde in either var is expanded to `$HOME`.

**Hooks**:

- **Stop** (`hooks/stop-check.sh`, deterministic): per-turn. Reads transcript JSONL, regex-matches the last user text against closing keywords (`세션 끝`, `마무리`, `wrap up`, `end session`, etc.), and emits a `systemMessage` suggesting `/save-session` only on match. **No LLM call** → no per-turn cost, no infinite-loop risk (the prior prompt-based hook looped because every response — even "(silent pass-through)" — re-fired the Stop hook).
- **SessionEnd** (chained `hooks/session-end-pre.sh` → prompt): session close. Shell pre-hook collects deterministic state (vault-link presence, direct-access counter) and writes JSON to `/tmp/vault-bridge-session-${SID}/session-end-state.json`; prompt then reads it via `jq`, decides whether work was meaningful, writes the safety-net session-note. Pre-hook uses `${CLAUDE_PROJECT_ROOT:-$PWD}` so a session-internal `cd` doesn't break `.vault-link` discovery. The prompt body is compressed (~1000 chars) to keep token overhead minimal.
- **SessionStart** (`hooks/session-start-manifest.sh`, deterministic): incremental manifest refresh — checks staleness and updates `{vault_root}/.vault-bridge/manifest.json` only for changed files (background, never blocks session start).
- **PreToolUse Read|Grep|Glob** (`hooks/pre-access-guard.sh`, deterministic): emits `systemMessage` warning when the configured vault root is accessed directly; counts direct-access events for the SessionEnd summary. Soft warning, never blocks. As of v1.9.0, this hook exempts vault-searcher's own reads to avoid the self-reference loop that previously caused haiku to misinterpret its own warning as a denial.
- **PreToolUse Write|Edit** (`hooks/pre-write-guard.sh`, deterministic): validates vault file naming conventions AND enforces the **Write Role Contract** — the read/write asymmetry at the core of vault-bridge. Vault *reads* are haiku-delegable (the `vault-searcher` agent), but vault *writes* are NOT: they must be user-initiated (main context, executed by slash commands). Subagent vault writes (any non-empty agent identifier in the PreToolUse payload) are denied or warned per `VAULT_BRIDGE_WRITE_CONTRACT` mode (default `enforce` — deny; supports `warn` / `off`). Naming convention is log-only by default; `VAULT_BRIDGE_STRICT_NAMING=1` blocks on violation.

**Slash commands** (`commands/*.md`):

- **`/save-session`**: executes the session-note recipe inline in main context (record/quick mode selection). As of v1.9.0, no longer delegates to vault-searcher — vault writes are user-initiated slash commands only.
- **`/vault-link`**: creates a `.vault-link` pointer file binding the current project to a vault location.
- **`/vault-manifest-refresh`**: forces a full manifest rebuild (skips staleness check).
- **`/vault-commit`**: commits uncommitted vault changes with user-approved message.
- **`/handoff`**: generates a continuation prompt for the next session — paste-ready one-liner, structured summary, or saved as `.claude-kit/vault-bridge/resume.md`. Does not write to vault paths; resume.md is a local gitignored file only.

The split (deterministic Stop + 2-step SessionEnd + explicit slash commands) ensures zero per-turn LLM cost, no loops, safety-net auto-save on `/exit`, and a clear user-driven path for full session notes.

## Cross-Plugin MECE Boundaries

Skills across `obsidian-vault-manager` and `vault-bridge` share overlapping domains. Boundaries:

| Area | obsidian-vault-manager | vault-bridge |
|------|----------------------|--------------|
| Note creation | `note` skill (evergreen notes + decision records, `notes/`) | N/A |
| Session record | N/A (use vault-bridge's session-note) | `/save-session` slash command (inline in main context — record/quick modes) |
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
