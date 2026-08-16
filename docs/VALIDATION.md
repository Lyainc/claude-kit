# claude-kit Validation Commands

Full command list for validating claude-kit changes. Split out of `CLAUDE.md` (2026-07-06) so the
project's always-loaded memory file stays lean — this doc is loaded on demand, not on every turn.
`CLAUDE.md`'s `## Validation` section now just points here.

Run the commands relevant to whatever you touched; `check-test-exitcode.py` (below) runs the whole
list in one shot as a local pre-push convenience. `scripts/check-ci-coverage.py` and
`scripts/check-test-exitcode.py` read the `## Validation` heading + fenced block below directly —
keep that heading text and the fence intact if you edit this file.

## Validation

```bash
# JSON 유효성 검사
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool feedback-loop/.claude-plugin/plugin.json > /dev/null

# 마켓플레이스 거버넌스 가드 (#134): version-sync drift(block) + CI 커버리지(block — #175 --strict 승격)
python3 scripts/check-version-sync.py --self-test
# Expected: OK: all 7 version-sync self-test cases passed (+ missing-manifest mode + --fix reconcile check)
python3 scripts/check-version-sync.py
# Expected: OK: version-sync clean — 4 plugin(s), no drift (root: ...)
# drift 시 exit 1, manifest 누락 시 exit 3 = 릴리스 차단.
# marketplace.json은 plugin.json에서 derived — drift 시 `--fix`로 plugin.json 기준 동기화:
#   python3 scripts/check-version-sync.py --fix
python3 scripts/check-ci-coverage.py --self-test
# Expected: OK: all check-ci-coverage self-test cases passed
python3 scripts/check-ci-coverage.py
# Expected: CI coverage: N/N docs/VALIDATION.md-registered tests run in validate.yml.
#   OK: every registered test is wired into CI.
# (gap=0.) CI runs this as `check-ci-coverage.py --strict` (#175): a coverage gap now BLOCKS
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
# Expected: OK: banned-words clean — N file(s) checked, no violations (N banned term(s) enforced)
python3 scripts/check-error-label-drift.py --self-test
# Expected: OK: all check-error-label-drift self-test cases passed
python3 scripts/check-error-label-drift.py
# Expected: OK: error-label-drift clean — N file(s) checked, every E1-EN label matches
#   source-of-truth max E12 (obsidian-vault-manager/reference/vault-audit-rules.md)
# #385: E1-EN audit-error-type range guard. obsidian-vault-manager/reference/vault-audit-rules.md's
# `## E<N> —` headers are the single source of truth; every other E1-E<N> range label in the
# repo must match its max, judged per-paragraph so a partial range that mentions the current
# max elsewhere in the same paragraph (a versioned breakdown, a `--dod` scope note, a
# multi-line priority mapping) is not flagged — only docs/plans/** and docs/discussions/**
# (dated historical records) are excluded by path.
python3 scripts/check-claude-md-attribution.py --self-test
# Expected: OK: all check-claude-md-attribution self-test cases passed
python3 scripts/check-claude-md-attribution.py
# Expected: OK: claude-md-attribution clean — N single-plugin script attribution(s)
#   checked against 4 plugin(s), all exclusive as claimed
# #601: root CLAUDE.md single-plugin script-attribution drift guard. Same bug class as
# #385 above and #380 (hook count miscount) — CLAUDE.md's descriptive scope stops
# tracking reality once a guard/feature spreads from one plugin to several. Flags any
# `<plugin>는/은/가/이 \`<script>\`` mention in CLAUDE.md whose named script is NOT
# exclusively owned by that plugin's scripts/ tree (e.g. #601's `check-trigger-regression.py`
# called thinking-tools-only when all 4 plugins carry a copy).
python3 scripts/check-agent-tools-field.py --self-test
# Expected: OK: all check-agent-tools-field self-test cases passed
python3 scripts/check-agent-tools-field.py
# Expected: OK: all N agent(s) declare `tools:`
# #472 BLOCK guard: an agent with no `tools:` frontmatter inherits every tool in the harness,
# regardless of what its body says it may do. Checks key existence only, on purpose — whether
# the listed tools match the body is the sibling guard below. Registered here by #577; before
# that it lived in scripts/ but ran in neither CI nor this list. #611's review found the
# emptiness half was never enforced: `^tools:\s*(.*)$` let `\s*` cross the newline, so a bare
# `tools:` followed by any other key captured THAT line as the value and passed — the exact
# #472 harm, green. Narrowed to `[ \t]*`, with the YAML block-list form checked separately so
# `tools:\n  - Read` still counts as non-empty.
python3 scripts/check-effort-field.py --self-test
# Expected: OK: all check-effort-field self-test cases passed
python3 scripts/check-effort-field.py
# Expected: OK: all N skill(s)/agent(s) declare `effort:`
# #648 BLOCK guard: same shape as check-agent-tools-field.py above, widened to
# */skills/*/SKILL.md + */agents/*.md and the `effort:` key. Without it, a skill/agent
# inherits the whole session's effort dial instead of a value tuned to what it actually
# does — #448 established effort-over-model-tier, but 11 skills and all 4 agents shipped
# with no `effort:` at all. Key existence + non-emptiness only; the value itself is a
# manual judgment call (see #648's issue body).
python3 scripts/check-agent-tools-usage.py --self-test
# Expected: OK: all 50 check-agent-tools-usage self-test cases passed
python3 scripts/check-agent-tools-usage.py
# Expected: OK: all N agent(s)/skill(s) declare exactly the tools their body uses
# #577: the declared set and the body must agree, in both directions. UNDECLARED (body says
# "use AskUserQuestion" but `tools:` omits it) makes that branch dead prose — found live in
# vault-searcher.md's .vault-link recovery. UNUSED (`tools:` grants Write/Grep that the body
# never names) re-creates the over-permission #472 exists to prevent — found live in
# vault-file-organizer.md. The two directions match on deliberately different signals: an
# imperative (`use X`, `call X`, `X(`, negations excluded sentence-wide) for UNDECLARED, a bare
# mention anywhere for UNUSED. Fenced code and HTML comments are stripped first, and usage is
# never inferred from a shell command — a body must NAME the tools it relies on, which is what
# CLAUDE.md's "Adding a New Agent" §2 already asks for. A third finding, CONTRACT, covers what
# the weak UNUSED signal structurally cannot: a body claiming the Write Role Contract while
# `tools:` grants Write/Edit/NotebookEdit — the sentence stating the prohibition contains the
# word `Write`, so a bare-mention check always passes it.
# #611 widened the same guard to `*/skills/*/SKILL.md` and its `allowed-tools:` key, which had
# no equivalent check at all: adversarial-review and expert-panel were directing a mandatory
# backlog-prefilter shell step with no Bash grant, and 17 skills across all 4 plugins carried
# grants their bodies never name. One splitter reads both conventions (agents comma-separated,
# skills space-separated) by breaking on commas AND whitespace outside parentheses. Two rules
# differ by scope: MISSING (no usable `allowed-tools:` — absent, or present but empty — so the
# skill inherits every tool in the harness) is skills-only because check-agent-tools-field.py
# above already owns the agent side (an agent instead falls through with an empty set, so
# UNDECLARED still reports what its body reaches for),
# and CONTRACT is agents-only because the skills that name the Write Role Contract are the
# main-context writers it authorises — firing there would block exactly the right holders.
# #634 added the one exception to "never infer a tool from a shell command": a SKILL.md with a
# ```bash/```sh/```shell TAGGED fence and no Bash grant is UNDECLARED on the fence alone, which
# closes #611's own recurrence path (its headline pair hid in exactly that blind spot and was
# found by hand). Untagged fences are excluded — YAML and output templates dominate them. The
# scan walks fences rather than regex-matching lines, because two shapes are not calls at all:
# a fence inside an HTML comment (a commented-out step) and a ```bash nested in a longer
# ````markdown block (sample text). The asymmetry is deliberate and pinned by self-test — a
# fence exposes a MISSING grant but never evidences a declared one, so a fenced skill that
# never names Bash in prose still reports UNUSED.
# Measured at introduction: 11 of 19 skills carry a tagged shell fence and all 11 already
# declared Bash, so the rule flags nothing; the same scan over agents also flagged nothing
# (2 of 4 have a tagged fence, both with Bash), which is why extending it later is one line.
# #620 added UNCONTRACTED, CONTRACT's inverse: CONTRACT only fires on a body that CLAIMS the
# contract, so an agent that never heard of it stayed invisible while documenting vault writes
# the hook denies. An agent holding Write/Edit/NotebookEdit whose body names the vault PATH
# (`~/vault`, not the bare word — that fires on an agent merely routing vault work to
# vault-searcher, which could then only go green by reciting a contract it has no duty under)
# and never names the contract is now reported — vault-file-organizer.md was the live find,
# and fixing it to the draft-handoff shape is what took the rule back to zero.
# pre-commit shim install-path guard (#651): scripts/hooks/pre-commit (#637) never runs
# anywhere until something writes .git/hooks/pre-commit, and .git/hooks is untracked.
# scripts/install-hooks.sh is the one documented install path (CONTRIBUTING.md
# Prerequisites); this re-extracts the shim verbatim from scripts/hooks/pre-commit's own
# header comment and compares it against whatever is actually installed (P12 — existence
# is not enough). MISSING (fresh clone, CI, not-yet-installed) is exit 0, informational —
# a hook that legitimately cannot be installed must not fail the check. STALE (installed
# but content drifted) is exit 1.
python3 scripts/check-hooks-installed.py --self-test
# Expected: OK: all 8 check-hooks-installed self-test cases passed
python3 scripts/check-hooks-installed.py
# Expected: ...

python3 scripts/check-skill-reference-drift.py --self-test
# Expected: OK: all 36 check-skill-reference-drift self-test cases passed
python3 scripts/check-skill-reference-drift.py
# Expected: OK: all N skill reference(s) resolve — N file(s) across N root(s), N external
#   root(s) absent, N deliberate fallback(s) exempt
# #637: a hardcoded skill name must resolve to a skill that exists. #562 renamed
# `completion-condition` -> `next-goal`; every reference inside this repo was updated, and the
# one that crossed the repo boundary — local-harness's skills/session-close/SKILL.md, which
# calls the skill by hardcoded qualified name — sat broken for 7 DAYS before being found by
# hand, with the documented fallback text stale in the same edit (it pointed at the dead name
# too, so the recovery path was broken as well). Nothing failed at runtime only because installs
# are pinned at a release predating the rename, where the OLD name still resolves — the break is
# armed for the next release, not absent.
# The external consumer is therefore the point, not an extra: every sibling guard scans this
# checkout only, which is exactly why check-trigger-regression.py missed it. EXTERNAL_ROOTS
# (default `~/dev/prj/local-harness/skills`) is the configurable list, and a path that does not
# exist is skipped SILENTLY — no other machine has that checkout, so failing there would make
# the guard unrunnable for everyone else.
# Two failure modes: a CALL fails loudly at runtime (`Unknown skill`), while a hook MATCHER
# (`case "$skill" in thinking-tools:next-goal|next-goal)`) fails OPEN and SILENT — the arm stops
# matching, the hook still exits 0, and nothing reports that its reason for existing is off.
# The scan is deliberately wider outside this repo than inside it, on measurement: a repo-wide
# prose scan flags 6 qualified mentions and all 6 are legitimate past-tense records (a CHANGELOG
# line for a retired skill, two dated docs/discussions transcripts, a reference doc describing a
# deleted agent), so in-repo only the call form plus qualified names in *.sh count. A consumer's
# skill file has no historical archive behind it, so there EVERY qualified token counts, prose
# included — which is what catches the stale-fallback half of #562, since that sentence had no
# call syntax at all. Agents share the catalogue (`<plugin>:<name>` is the qualified form for
# both), and a plugin this repo does not ship is skipped rather than judged.
# Two more surfaces, both added after a fresh-context review found the guard blind to them.
# (a) An agent's `skills:` frontmatter list hardcodes 9 names in thinking-facilitator.md alone,
# and it fails open and silent exactly like a hook matcher: rename the skill and the entry just
# stops granting it. Structured, so it is parsed, not pattern-matched off prose.
# (b) The slash form (`` `/next-goal` ``) is how a consumer names a skill in prose, and it is
# the shape the stale #562 fallback sentence has TODAY — the qualified-token rule would leave
# it silent through the next rename. It cannot be scanned bare: of the 7 distinct slash names
# in the live external root, 4 are legitimately unresolvable (native `/goal`, `/code-review`;
# retired `/handoff`, `/capture` named as history), so EXTERNAL_SLASH_IGNORE carries those with
# a reason each, and the consumer's own skills resolve against its own declarations.
# A version-skew bridge that deliberately names both the old and the new skill is exempted by
# the DELIBERATE_FALLBACKS allowlist, reason inline; an entry that stops firing while its file
# is still scanned is reported as STALE, so an exemption cannot outlive its reason. The list is
# empty today — local-harness dropped its bridge once this guard existed to catch the next one.
python3 scripts/check-plugin-root-paths.py --self-test
# Expected: OK: all 14 check-plugin-root-paths self-test cases passed
python3 scripts/check-plugin-root-paths.py
# Expected: OK: plugin-root-paths clean — N SKILL.md + N agents/*.md checked, every
#   bundled-script invocation / plugin-internal pointer is ${CLAUDE_PLUGIN_ROOT}-anchored
# A SKILL.md code block runs with CWD = the CONSUMER's project, so a repo-relative call like
# `python3 feedback-loop/scripts/report.py 2>/dev/null` resolves ONLY inside this checkout —
# for every plugin-installed user it silently no-ops. Found live in retro/SKILL.md (4 call
# sites, shipped in v4.0.0). Scans source plugins only (dirs with a plugin.json), so any
# vendored third-party plugin cache is never touched. Markdown `../../reference/*.md` links are NOT
# flagged — those resolve relative to the SKILL.md file and stay correct once installed.
# #579 widens the same guard to agents/*.md with the OPPOSITE markdown-link judgment: an
# agent body is injected as a subagent's system prompt, not read relative to a file on disk,
# so `../reference/foo.md` or a bare `foo.md` (same directory) resolves nowhere once
# installed — found live in vault-searcher.md (#566). Scoped to agents whose `tools:` grants
# Read or Bash (no other tool can act on the pointer) and to backtick paths anchored at
# reference/scripts/hooks/, so human doc links, vault paths, and another plugin's own path
# are never flagged; fenced examples and HTML comments are stripped before scanning.
# Always-loaded/always-attached instruction budget guard (#454/#461 SKILL.md, widened to
# CLAUDE.md + agents/*.md by #473). For SKILL.md: auto-compaction re-attaches only the FIRST
# 5,000 TOKENS of an invoked skill and drops the rest silently, so a confirmation gate or an
# invariant living in the tail stops being in the instructions after one compaction. For
# CLAUDE.md (an always-loaded prefix) and agents/*.md: the rationale is dilution, not
# compaction — an unguarded instruction file only ever grows, and every line taxes compliance
# with every other instruction in it (obsidian-mind's CLAUDE.md hit 36KB/~9-10k tokens with no
# guard). Blocks on the whole file over 5,000 tokens for all three kinds, plus — SKILL.md
# only — any compaction-critical anchor (`## Rules`, every body `AskUserQuestion`) starting
# past that boundary. CLAUDE.md's own #473 overage (5,510 tokens) was fixed by moving
# lookup-only sections to docs/REFERENCE.md per its abandon-priority table, never by trimming.
# Counts with tiktoken `o200k_base` — the tokenizer #447's own measurements used — fetched
# ephemerally by `uv run --with`, so it is a dependency of this command and of nothing else.
# WITHOUT tiktoken the guard exits 2 and refuses a verdict rather than downgrading quietly;
# `--allow-estimate` opts into an indicative char-class run (0.86x-1.14x measured error).
# #454 preferred a dependency-free proxy; that was built first and rejected on measurement —
# the best two-parameter char model still spans 0.86x-1.14x, wide enough that it passed
# `add-policy` at a real 5,304 tokens and `audit` at 5,286 while reporting ~4,990/~4,870.
# `--list` prints every file's count and anchor offsets.
uv run --with tiktoken python3 scripts/check-skill-token-budget.py --self-test
# Expected: OK: all 25 check-skill-token-budget self-test cases passed
uv run --with tiktoken python3 scripts/check-skill-token-budget.py
# Expected: OK: skill-token-budget clean — N file(s) checked (SKILL.md/agents/*.md/CLAUDE.md),
#   every one within 5000 tokens, SKILL.md gates inside the window [o200k_base] (largest ...)

python3 scripts/check-release-failure-notify.py --self-test
# Expected: OK: all check-release-failure-notify self-test cases passed
python3 scripts/check-release-failure-notify.py
# Expected: OK: .github/workflows/auto-release.yml has a failure-notify job
#   (`notify-failure`) gated on failure() with issues:write + gh issue create.
# #642: auto-release.yml is push-triggered, so a failure never shows up as a PR check —
# it failed silently on every main push for 12 days (40 runs) before a human noticed main
# had drifted ahead of the last tag. Guards that the workflow's `notify-failure` job (gated
# on `if: failure()`, holding `issues: write`, calling `gh issue create`) stays wired.

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
# #456: a per-linter skip is graceful, but a run where EVERY linter skipped inspected
# nothing, and exits 2 refusing a verdict rather than reporting the exit 0 it used to.
# Real mode therefore exits 2 on a machine with no ruff/prettier/shellcheck — which is why
# only `--self-test` is registered here: the self-test pins the refusal (verdict function +
# its wiring through main(), including --json) without needing a linter installed. Same
# refuse-rather-than-degrade shape as check-skill-token-budget.py's exit 2 above (#454).

# claude-review 침묵 방지 가드 회귀 (#451): 리뷰 job이 코멘트를 0개 남기고도 초록불이던
# 문제 — Checks 탭에서 "리뷰했는데 지적이 없음"과 "리뷰가 안 돎"이 같은 체크로 보였다.
# workflow의 verify step이 이번 라운드 코멘트를 세서 0이면 job을 실패시키는데, 그 세는
# 로직(jq 필터)을 워크플로에서 EXTRACT해 실제 jq로 픽스처에 돌린다 — 특히 이전 라운드
# 코멘트가 이번 라운드를 만족시키면 안 된다(createdAt 절이 빠지면 synchronize 재실행마다
# 통과해 가드가 꺼짐). 나머지는 정적 확인: step 존재 + `if: always()` + 0에서 nonzero,
# 프롬프트의 짝(깨끗해도 LGTM 코멘트 필수) — 워크플로만 넣으면 깨끗한 PR이 전부 빨간불,
# 그리고 `paths:` 필터 부재(required check가 스킵되면 상태를 리포트 안 해 영구 pending).
# jq 부재는 skip이 아니라 exit 2 — 스스로 꺼지는 검사가 이 파일이 잡으려는 바로 그 실패다.
python3 scripts/test/test-review-silence-guard.py --self-test
# Expected: OK: all 6 review-silence-guard self-test cases passed
python3 scripts/test/test-review-silence-guard.py
# Expected: OK: all 18 review-silence-guard checks passed.
# 라운드 스코핑이 기대는 두 조건도 함께 핀: 빈 SINCE는 필터를 넓히지 말고 실패할 것
# (jq의 `>`는 ""에 대해 항상 참), 그리고 concurrency 그룹 — 한 PR에 겹쳐 도는 두 실행은
# 나중 것의 창이 먼저 것의 코멘트보다 앞서서 형제 실행의 리뷰로 통과할 수 있다.

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

# 워크트리 격리 가드 회귀 (#594): scripts/worktree-isolation-guard.sh PreToolUse Write|Edit
# 훅이 "메인 체크아웃 + 기본 브랜치" 쓰기만 경고하는지 — 실제 git repo와 실제 linked worktree를
# 임시 디렉토리에 만들어 검증한다 (탐지가 git-dir vs git-common-dir와 기본 브랜치 해석에
# 전적으로 기대므로 손으로 만든 fixture로는 정직하게 안 걸린다). 침묵해야 하는 세 경우
# (linked worktree·feature 브랜치·gitignore 경로) + 모드 매트릭스 + (세션, repo)당 1회 dedup을 핀.
bash scripts/test/test-worktree-isolation-guard.sh
# Expected: OK: all worktree-isolation-guard cases passed (N)

# build-spec Phase 0 백로그 prefilter (#489): open+closed 전량을 셸에서 읽고 예산 안의
# 다이제스트만 내보내는지 — 특히 (1) 닫힌 후보가 다이제스트에 실제로 렌더되는지(#489의 요지),
# (2) 코퍼스를 못 읽었을 때 빈 문자열이 아니라 `[backlog-scan SKIPPED]` 줄을 내는지.
# (2)가 빠지면 "스캔했는데 충돌 없음"과 "스캔이 안 돎"이 출력상 구분되지 않는다(#443·#447 클래스).
python3 thinking-tools/scripts/backlog-prefilter.py --self-check
# Expected: self-check ok

# issue-raise 템플릿 헤딩 기계적 검증 가드 (#563): Phase 2(조립)와 Phase 3(승인) 사이에서
# 초안의 `## ` 헤딩을 템플릿의 `## ` 헤딩과 텍스트·순서·개수(`(선택)` 마커 포함)로 1:1 diff.
# LLM 호출 없는 순수 파이썬(backlog-prefilter.py와 같은 철학). #562에서 실제 발생한 결함
# (`## 제안 (선택)` → `## 제안`, 마커 누락)을 self-test 회귀 케이스로 고정.
python3 thinking-tools/scripts/check-heading-match.py --self-test
# Expected: OK: all check-heading-match self-test cases passed

# 릴리스 도구 self-test (lockstep bump + 플러그인별 노트 생성) — RELEASING.md 참조
python3 scripts/bump-version.py --self-test
# Expected: OK: all bump-version self-test cases passed
python3 scripts/gen-release-notes.py --self-test
# Expected: OK: all gen-release-notes self-test cases passed
# 릴리스 트리거 정책 (#382): `release` 라벨 = 주 트리거, 미릴리스 user-visible 커밋 10개 =
# 백스톱, docs/chore는 세지도 트리거하지도 않음. bump는 커밋에서 도출(breaking>feat>나머지).
# 순수 함수로 핀 — git 없이 합성 커밋 리스트로 정책 자체를 테스트한다.
python3 scripts/next-version.py --self-test
# Expected: OK: all 23 self-test cases passed

# auto-release.yml 트리거 회귀 (#493): 머지 후에 붙인 `release` 라벨이 어떤 경로로도 안
# 읽히던 결함 — `pull_request: closed`는 머지 순간 한 번만 발화하고, 라벨을 나중에 붙여도
# `pull_request: labeled`가 트리거 목록에 없어 워크플로가 아예 안 깨어났다(실증: PR #488).
# 고침은 `types: [closed, labeled]`뿐 — 기존 `if:`(merged==true + release 라벨 포함)가
# `labeled` 이벤트에서도 그대로 안전하게 맞아떨어진다(payload가 라벨 추가 후 상태를 반영).
# 라이브 YAML을 정적으로 파싱해 그 3가지(types에 labeled 포함, if가 merged+라벨 조건 유지,
# decide 스텝이 pull_request 이벤트에 대해 무조건 --labeled를 넘기는지)를 핀한다.
python3 scripts/test/test-auto-release-trigger.py --self-test
# Expected: OK: all 10 self-test cases passed
python3 scripts/test/test-auto-release-trigger.py
# Expected: OK: auto-release.yml #493 fix intact (7 checks)

# 플러그인 스펙 전체 검증 (frontmatter·hooks 스키마 포함)
# claude plugin validate  # Claude Code 설치 환경에서 실행

# 스킬 파일 존재 확인
find thinking-tools/skills -name "SKILL.md" | sort
find obsidian-vault-manager/skills -name "SKILL.md" | sort

# vault-bridge pre-write-guard regression (Write Role Contract + naming, incl. notes/*.base ext for #118
# /base skill, and the #381 Bash bypass: subagent `echo > vault/x.md`/mv/tee/cd+redirect are denied while
# reads — grep/cat/`cd vault && git status`/`cp vault/x.md /tmp/` — must stay FP-free)
python3 vault-bridge/scripts/test/test-pre-write-guard.py

# vault path resolution regression (#613/#616) — VAULT_BRIDGE_VAULT_ROOT > VAULT_BRIDGE_VAULT_PATH
# > ~/vault must resolve identically across pre-write-guard.sh, the Python helpers, and
# obsidian-vault-manager's ovm-primitives.sh (the one place that used to fall straight to
# $HOME/vault, ignoring both env vars — breaking /audit for non-default vaults and writing
# audit state to the wrong one).
python3 vault-bridge/scripts/test/test-vault-path.py
# Expected: OK: all 5 vault-path cases passed

# vault-bridge manifest atomic-write self-test (#582) — manifest.json is written via
# temp-file + os.replace so a hard kill mid-write can never leave a torn manifest on
# disk; the two call paths that regenerate it (hooks/session-start-manifest.sh's
# automatic refresh, skills/vault-manifest-refresh's manual --force) both funnel through
# this same write. Simulates the kill at both boundaries (mid temp-file write, exactly
# at the replace) by monkeypatching os.fdopen/os.replace to raise, and asserts the
# original manifest content survives untouched in both cases.
python3 vault-bridge/scripts/generate-manifest.py --self-test
# Expected: OK: all generate-manifest self-test cases passed

# vault-bridge manifest type opt-in regression (v4 §2.2)
python3 vault-bridge/scripts/test/test-manifest-type-optin.py

# vault-bridge manifest-candidates regression (#523, mirrors #468's OVM test-manifest-reads.py)
# — vault-searcher.md used to `Read` the whole manifest, overflowing the Read tool's 2,000-line
# cap and silently dropping 100% of wiki/ entries (alphabetically sorted last by
# generate-manifest.py). Pins: the real-scale repro precondition, that both
# manifest-domain-candidates.py and manifest-keyword-candidates.py recover every wiki/ entry by
# reading the manifest off disk directly, and that a downstream truncation of their own compact
# output is detectable (parse failure or candidate_count/length mismatch) rather than silent.
# #663 moved the truncation-observability + Mode 2 ranking contracts out of vault-searcher.md
# (token-budget saturation) into reference/manifest-recall.md; the pins followed. The self-test
# corrupts the canonical contract text in the reference doc and asserts the guards still FAIL.
python3 vault-bridge/scripts/test/test-manifest-candidates.py --self-test
# Expected: OK: all 12 manifest-candidate self-test cases passed
python3 vault-bridge/scripts/test/test-manifest-candidates.py
# Expected: OK: all manifest-candidate checks passed

# vault-bridge manifest global meta fields (references_in/out, recent_commits, type
# opt-in, in-place schema upgrade) — was never wired into docs/VALIDATION.md (#618 audit).
python3 vault-bridge/scripts/test/test-manifest-meta.py
# Expected: OK: all cases passed

# vault-commit message generation (status-transition aware)
python3 vault-bridge/scripts/test/test-vault-commit-message.py
# Expected: OK: all cases passed

# vault-bridge agent trigger-regression check (#338 — sibling to the thinking-tools
# check below, adapted for vault-bridge's single-line quoted `description: "..."`
# agent frontmatter with inline "KR triggers: ... EN triggers: ..." labels).
# Self-test the extractor:
python3 vault-bridge/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 13 self-test cases passed
# Diff trigger sets between a base ref and the working tree (exit 1 = removals found):
python3 vault-bridge/scripts/test/check-trigger-regression.py origin/main
# Removals are reported (not hard-gated) — reviewer decides if intentional.

# vault-bridge SKILL.md trigger-regression check (#471 — routing-SSOT drift guard extended
# to the face the two checks above didn't cover: vault-bridge/skills/*/SKILL.md. 3 of its 4
# skills carry `disable-model-invocation: true` and are structurally skipped — no
# natural-language trigger surface to regress — leaving only vault-save guarded.)
python3 vault-bridge/scripts/test/check-skill-trigger-regression.py --self-test
# Expected: OK: all 7 self-test cases passed
python3 vault-bridge/scripts/test/check-skill-trigger-regression.py origin/main
# Removals are reported (not hard-gated) — reviewer decides if intentional.

# feedback-loop telemetry schema self-test (#217 — telemetry absorbed into feedback-loop)
python3 feedback-loop/scripts/validate-schema.py --self-test

# feedback-loop report.py latency_by_event regression gate (#164)
# + per-skill lifecycle view (never-fired / stale / bottom-N vs */skills/*/SKILL.md catalog, #203)
# + scan_skill_catalog cache-layout regression (#522): the plugin-cache install path
# (cache/{marketplace}/{plugin}/{version}/scripts/report.py) inserts a semver version
# dir the naive repo-shape glob reads as the plugin name (`4.0.1:retro`), so every
# real qualified_name match fails and the lifecycle view reports 100% never_fired —
# #477's "'/capture'·'/note' 호출 0회" citation traces back to exactly this view.
python3 feedback-loop/scripts/test/test-report.py
# Expected: OK: all cases passed
# event-logger meta-extractor unit test (extract_end_meta / extract_stop_meta)
bash feedback-loop/scripts/test/test-event-logger.sh
# Expected: OK: all event-logger meta-extractor cases passed

# retro-telemetry helper regression (#294 — retro Phase-1 stamp + Phase-3 emit
# extracted from the SKILL.md inline bash to scripts/retro-telemetry.sh; this
# pins the schema-shaped emit line + duration null-fallback against drift).
# #580 rewrite: `stamp` no longer writes a /tmp file — it prints the start
# time to stdout and `emit` takes it as an explicit `start_ms` argument
# (Phase 1 and Phase 3 are separate Bash-tool calls, so no process/session id
# was ever stable enough to key a shared file on; $PPID drifted between the
# two calls within a single retro run, corrupting duration_ms to null and
# orphaning stamp files). Also pins the SKILL.md Phase-3 call site actually
# passing `$START_MS` first (#580) and the #528 batching shape.
bash feedback-loop/scripts/test/test-retro-telemetry.sh
# Expected: OK: all retro-telemetry cases passed

# retro-telemetry concurrent-session isolation (#529, #580). #529's original
# bug — concurrent sid-less sessions colliding on one shared /tmp stamp file —
# is now structurally impossible: #580 removed the file entirely, so there is
# no shared state left for two sessions to collide on. This drives N genuinely
# concurrent OS processes (not a forced interleaving of file operations, since
# there is no longer any file state to force an interleaving of) through
# stamp+emit and asserts no /tmp file ever appears, every session's
# duration_ms survives non-null, and the one thing that IS still shared — N
# processes appending to the same events-*.jsonl log at once — never produces
# a torn/corrupted line.
python3 feedback-loop/scripts/test/test-retro-telemetry-stamp-isolation.py
# Expected: OK: 6 concurrent stamp+emit sessions isolated, no /tmp file, no cross-session null, no torn writes

# events-dir resolution regression gate. The fallback was once plain `$PWD`, so a
# hook firing from a subdirectory built its own .claude-kit/telemetry/ there (5 stray
# copies accumulated, one under .github/ISSUE_TEMPLATE/). The rule is duplicated
# across 4 leaf-standalone scripts, so this asserts all of them together — a partial
# revert would silently split writers from readers. Case 6 pins #533: the primary
# override was misspelled CLAUDE_PROJECT_ROOT (the harness sets CLAUDE_PROJECT_DIR),
# so it silently never fired and every hook fell to git-toplevel-of-CWD — a session
# that `cd`s into an unrelated repo mid-session (e.g. ~/vault for /vault-commit)
# then wrote telemetry there instead, measured live 2026-08-03.
bash feedback-loop/scripts/test/test-events-dir-resolution.sh
# Expected: OK: all events-dir resolution cases passed

# gh-issues-cache.sh regression (#528 cache, #618 fail-open/fail-empty fix) — was
# never wired into docs/VALIDATION.md, so the #618 bug (a failed `gh` fetch and a
# genuinely-zero-open-issue backlog both printed bare "[]", which retro's dedup step
# then read as "no duplicates" and re-filed an already-open issue) shipped without CI
# catching it. Pins: fresh cache served without touching `gh`, a failed fetch is never
# cached AND is distinguishable from a genuine "[]" (nonzero exit + FAILED marker), a
# genuine zero-open-issue backlog still exits 0/caches/prints bare "[]", and an expired
# cache falls back to a live fetch.
bash feedback-loop/scripts/test/test-gh-issues-cache.sh
# Expected: OK: all gh-issues-cache cases passed

# feedback-loop SKILL.md trigger-regression check (#471 — routing-SSOT drift guard extended
# to a previously-unguarded face). feedback-loop's skills use a third description shape
# (single-line quoted, inline `Trigger: <phrase list>. Routing: ...` label) that neither the
# thinking-tools nor vault-bridge extractor's regex matches, hence its own script.
python3 feedback-loop/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 7 self-test cases passed
python3 feedback-loop/scripts/test/check-trigger-regression.py origin/main
# Removals are reported (not hard-gated) — reviewer decides if intentional.

# sequence.py lifecycle-pair regression (#458) + same-label run-collapse (#598). The
# stream logs `started` and then `success`/`error` for the SAME call, and both rows used
# to enter the in-session n-gram window — so every single call produced an `X -> X`
# self-transition, and retro read that output as a WASTE signal, so the waste detector
# was reporting its own instrumentation as waste (`retro -> retro` = 19 over 7d for a
# skill that ran once per session). A second inflation survived that fix: N genuinely
# consecutive real calls to the same label still produced N-1 adjacent-pair matches, so
# one long isolated-subagent fan-out burst (expert-panel dispatching 9 personas in a row)
# outscored every real repeat in `--top=N`. count_ngrams now excludes same-label windows
# entirely; count_self_transition_runs reports them separately as ONE (label, run length)
# entry, so a length-2 run (real re-delegation candidate) and a length-9 run (fan-out)
# land in different buckets instead of one inflated count. The filter lives in
# sequence.py, NOT load_events: report.py's outcome mix legitimately counts both rows
# (calls vs completions). Pins the other direction too — real consecutive calls, `error`
# outcomes, and session boundaries must still count.
python3 feedback-loop/scripts/test/test-sequence.py
# Expected: OK: all 16 sequence lifecycle-pair + run-collapse checks passed.

# add-policy source gate + distill anti-capture floor + retro rule-branch routing (#459).
# add-policy by design never re-judges worth-keeping, because its input contract assumed every
# candidate arrived already judged (user-stated, or distill-ruled). A third kind — one the AGENT
# inferred from the session — looked like a user one-liner and inherited that free pass: measured
# 8 add-policy runs vs 2 distill runs (2,245 events, 2026-06-23~07-30), 6 of the 8 through no
# distill at all. Three prose skills, so this is a static-content check like
# test-add-policy-routing.py: the gate's test must be OBSERVABLE (point at the user's utterance
# in the transcript) and run BEFORE classification/§6, the never-re-judge invariant must be
# restated where the gate is introduced (else the next editor reads it as a contradiction and
# reverts), distill's DROP list must carry the recurrence floor + default-behavior + a bounded
# already-landed grep, and retro's rule branch/Rules/description must all point at /distill.
# §1 must also exempt the two already-judged kinds IN §1 ITSELF: a distill proposal carries no
# user utterance stating the rule, so a gate read as a bare binary bounces it back to the skill
# that sent it — and §1 is what compaction re-attaches, so a reference.md-only carve-out is not
# in front of the engine when the test is applied.
python3 feedback-loop/scripts/test/test-distill-gate-routing.py --self-test
# Expected: OK: all 35 self-test cases passed
python3 feedback-loop/scripts/test/test-distill-gate-routing.py
# Expected: OK: all 14 distill-gate-routing checks passed.

# add-policy layer-routing regression (G28 — add-policy is a prose skill, so this is a
# static-content check on the live SKILL.md: the SOFT reminder channel is routed by layer
# (stance/voice→~/.claude/CLAUDE.md, work-rule→~/.claude/rules) with a vanilla fallback
# (rules absent→CLAUDE.md) and a never-hardcode-the-rules/-structure clause. Guards the
# "both rules-present and rules-absent branches are described" claim against drift.
# #377 extends it to §6's native-memory duplicate scan — and since that scan ships as runnable
# bash (in add-policy/reference.md §6-snippet since the #469 split moved the executable text
# out of the compaction window), the snippet is EXTRACTED and EXECUTED against temp-HOME fixtures
# (no projects dir / projects-but-no-memory-dir / zero-hit / populated) under every shell
# present. The populated fixture carries adversarial near-misses — `type: feedback-loop`,
# `type: feedbackx`, `type: feedback` quoted in a note's BODY, a file with NO frontmatter whose
# body `---` could open a fake one, and MEMORY.md itself — so a loosened matcher fails the check
# instead of passing it. An unreadable memory file must reach stderr: a duplicate check that
# fails silently reports "no duplicates", which is the wrong direction to fail.) The live run
# reads BOTH files — every prose claim against SKILL.md, only the snippet against reference.md —
# and pins the seam the split created: SKILL.md must name §6-snippet AND say to run it (#469).
python3 feedback-loop/scripts/test/test-add-policy-routing.py --self-test
# Expected: OK: all 28 self-test cases passed
python3 feedback-loop/scripts/test/test-add-policy-routing.py
# Expected: OK: all 13 add-policy-routing checks passed.

# NOTE: three regions of add-policy/SKILL.md are pinned VERBATIM by these two suites — §6's
# preamble and its Supersede verdict (here), and §6's necessity-gate block (necessity-gate).
# Editing any of them, including a token-budget trim, FAILS CI by design: the failure names the
# constant to update, and the paired edit belongs in the same commit. Patterns were tried first
# and defeated four times (a presence check, a negation regex, a suffix anchor, and a file-wide
# noun scan); every pattern is a blocklist of the last wording tried, so the text is the pin.

# add-policy §6 conflict-check Edit bucket + Supersede exit regression (#303 — an explicit
# "change this existing entry" request is its own conflict-check outcome, distinct from
# Duplicate (strengthen) and Contradiction (refuse); guards against it collapsing back into
# either. #429 adds the exit path: every other verdict leaves the entry count flat, so the
# catalogue grew monotonically; Supersede absorbs the redundant entry and retires it in the
# SAME write, on the SAME confirmation, and a retired number is never reused.)
# #609 adds the never-fired exit beside Supersede — both choices (delete / narrow the
# firing condition) under the recommends-only ceiling, since rules/lint-catalogue.sh caps
# the framing but deliberately not the row count, leaving absorption as the only way out.
python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py --self-test
# Expected: OK: all 51 self-test cases passed
python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py
# Expected: OK: all 10 add-policy-conflict-edit checks passed.

# add-policy necessity-gate regression (#450 — before #450 the engine had an entry path and
# no "don't land this" verdict: only Contradiction stopped a write, and it stops it for
# disagreeing with an existing rule, so a rule that contradicts nothing and is simply
# unnecessary passed straight through. Pins the four questions each by its own content, the
# three outcomes, and the gate's ceiling: it recommends as the first option of the SAME
# 1-click confirmation, adds no second prompt, and never blocks a landing the user asked for
# explicitly. Also pins the distill boundary — artifact cost is the gate's question, reuse
# value stays distill's — without which the skill contradicts its own description.)
# #609 adds the narrowing clause: one occurrence scopes the condition to that occurrence's
# own situation, with NO occurrence counter — telemetry carries no failure-type label a
# threshold could be judged against, so a count reads stricter while judging looser.
python3 feedback-loop/scripts/test/test-add-policy-necessity-gate.py --self-test
# Expected: OK: all 36 self-test cases passed
python3 feedback-loop/scripts/test/test-add-policy-necessity-gate.py
# Expected: OK: all 7 add-policy-necessity-gate checks passed.

# add-policy §6 index+detail split regression (#340 — when the target landfill site
# already uses a thin index + per-entry detail-file shape, add-policy must match that
# shape (one index row + a linked detail file) instead of appending a new inline block,
# and must never invent this split on a site that doesn't already use it.)
python3 feedback-loop/scripts/test/test-add-policy-index-detail.py --self-test
# Expected: OK: all 19 self-test cases passed
python3 feedback-loop/scripts/test/test-add-policy-index-detail.py
# Expected: OK: all 4 add-policy-index-detail checks passed.

# thinking-tools trigger-regression check (run after editing any SKILL.md description)
# Self-test the extractor:
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 9 self-test cases passed
# Diff trigger sets between a base ref and the working tree (exit 1 = removals found):
python3 thinking-tools/scripts/test/check-trigger-regression.py origin/main
# A char-count check does NOT catch dropped triggers; ALWAYS run this when slimming
# descriptions. Removals are reported (not hard-gated) — reviewer decides if intentional.
# Restore any CLAUDE.md-mandated trigger (e.g. expert-panel "다양한 관점에서 평가해줘").

# thinking-tools AGENT trigger-regression check (#471 — routing-SSOT drift guard extended to
# the face the check above doesn't cover: thinking-tools/agents/*.md. thinking-facilitator.md
# has no `Trigger when user mentions:` block — its only structured trigger surface is an
# inline `(e.g., '구체화', '검사해줘', '반증해줘')` illustrative-example clause, so this
# extractor targets that shape instead of forcing the skill-level marker onto it.
python3 thinking-tools/scripts/test/check-agent-trigger-regression.py --self-test
# Expected: OK: all 5 self-test cases passed
python3 thinking-tools/scripts/test/check-agent-trigger-regression.py origin/main
# Removals are reported (not hard-gated) — reviewer decides if intentional.

# expert-panel mode-compose regression (#228) — verifies the SKILL.md's "all combinations
# compose silently" claim: every declared mode toggle (격리/요약 + citation grounding +
# Phase 2 inline path) is described and non-contradictory. Run after editing expert-panel
# mode/Phase structure or the Citation Contract.
python3 thinking-tools/scripts/test/test-mode-compose.py --self-test
# Expected: OK: all 16 self-test cases passed
python3 thinking-tools/scripts/test/test-mode-compose.py
# Expected: OK: all 9 mode-compose checks passed.
# (static check against the live SKILL.md)

# persona-pool selection guard (#418) — executes reference/personas.md's Selection Rule
# against the live tag table: Latin tags must be word-start-safe (raw substring matching
# had `ui` hitting "build", `db` hitting "feedback", `doc` hitting "docker"), no
# single-character Hangul tags, fixture topics select the expected personas, and the
# 5-entry ceiling / 3-expert floor hold. Also guards the shared input (#423): both consuming
# skills must run the rule on the user's original topic text, never on the model-authored
# Steelman. Run after editing the pool's tag list or either skill's Selection Rule wording.
python3 thinking-tools/scripts/test/test-persona-selection.py --self-test
# Expected: OK: all 17 test-persona-selection self-test cases passed
python3 thinking-tools/scripts/test/test-persona-selection.py
# Expected: OK: all persona-selection checks passed (10 pool entries, 7 topic fixtures, ...)

# session-start onboarding hook regression (#117) — first-run discoverability hint
# hosted in thinking-tools SessionStart (vault-independent entry plugin; C-2 forbids a
# 4th "welcome" plugin). Verifies 3-session grace, kill switch, corrupt-counter recovery,
# and valid systemMessage JSON. State = single integer file under CLAUDE_CONFIG_DIR.
bash thinking-tools/scripts/test/test-session-start-welcome.sh
# Expected: OK: all session-start-welcome cases passed

# next-goal 후보 풀 훅 회귀 (#517) — 두 실패가 프로덕션에서 조용하다.
# (1) matcher가 안 맞기 시작하는 것: 플러그인 스킬은 `plugin:skill`, 머신 스킬은 bare로
#     도착한다. 이 훅은 bare 키로 된 머신 훅에서 이식됐고, #406이 그 키를 그대로 옮기면
#     "영영 발화하지 않는다"고 기록했다 — 발화 안 하는 훅은 할 말 없는 훅과 구분되지 않는다.
# (2) 백로그 조회 실패가 빈 백로그로 읽히는 것: "열린 이슈 0개"와 "조회 못 함"은 정반대
#     판단으로 이어지는데 한 칸에 합치면 gh 부재가 정리된 백로그로 읽힌다(#443·#447 클래스).
# gh를 PATH에 스텁으로 깔아 네트워크 없이 결정적으로 돈다. 페이로드가 판정문(임팩트 바닥 등)을
# 싣지 않는지도 함께 핀 — 판정은 SKILL.md 소유고 양쪽에 두면 경계를 가로지른 중복이다.
bash thinking-tools/scripts/test/test-next-goal-hook.sh
# Expected: OK: all 19 next-goal-hook cases passed

# next-candidate.py chain_depth()/top_areas() unit tests (#521) — the hook test above only
# exercises these through single-commit e2e fixtures; this asserts the edges directly:
# zero commits, a bare root file's `·`-prefixed area, and multi-area branching (including a
# commit whose changed files span more than one area).
python3 thinking-tools/scripts/test/test-next-candidate.py
# Expected: OK: all 6 test-next-candidate checks passed

# Shell hook syntax check
bash -n vault-bridge/hooks/*.sh
bash -n thinking-tools/hooks/session-start-welcome.sh   # #117 first-run onboarding hint
bash -n thinking-tools/hooks/next-goal-context.sh   # #517 candidate-pool injection
bash -n feedback-loop/scripts/event-logger.sh
bash -n feedback-loop/scripts/retro-telemetry.sh   # #294 retro stamp/emit helper
bash -n scripts/rules-checklist-hook.sh   # #216 work-rules task-end reminder hook
bash -n scripts/subagent-git-guard.sh     # #209 subagent git side-effect deny hook
bash -n scripts/no-pyyaml-guard.sh        # #259 no-PyYAML guard (add-policy dogfood + rule_fire emitter)
bash -n scripts/worktree-isolation-guard.sh  # #594 P1 self-isolation warn hook

# parse_created_date unit test (audit-validate Phase 2 helper)
python3 obsidian-vault-manager/scripts/test/test-parse-created-date.py
# Expected: OK: all 13 cases passed

# git activity summary unit test
python3 obsidian-vault-manager/scripts/test/test-git-activity.py
# Expected: OK: all 18 cases passed

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

# notes/ filename convention parity gate (#531): audit-validate.py's filename_conforms()
# (report-time E3) and vault-bridge/hooks/pre-write-guard.sh's notes/ pattern (write-time)
# must agree on the same filename set, e.g. a bare YYYY-MM- date under notes/.
python3 obsidian-vault-manager/scripts/test/test-notes-filename-consistency.py
# Expected: OK: all cases passed

# E5 orphan connection-candidate ranking regression (#495) — pins the rarity-weighted
# score (score(P,Q) = Sum 1/log(1+df(t)), E9a-style vault-wide df aggregation) ranking a
# rare-tag match above a common-tag-only match, the top-N cap, and the E5_MIN_CANDIDATE_SCORE
# floor collapsing an all-common-tag pool to candidates:[] instead of force-filling top-3.
python3 obsidian-vault-manager/scripts/test/test-e5-candidate-ranking.py
# Expected: OK: all cases passed

# E5 orphan connection-candidate PRODUCTION primitive parity gate (#619): before this,
# the rarity-weighted score above shipped only inside audit-validate.py's reference
# oracle (test-e5-candidate-ranking.py, still oracle-only), with no primitive backing
# it in production — CLASSIFY had nothing to call and had to hand-execute the scoring
# itself. Drives `ovm-primitives.sh e5-candidates` via subprocess and asserts it agrees
# with the oracle exactly (case-sensitive tags, floor_gated, top-3 tie-break), plus the
# `_index.md` exclusion guard.
python3 obsidian-vault-manager/scripts/test/test-e5-candidates-primitive.py
# Expected: OK: all cases passed

# `--path`-scoped scan-frontmatter/scan-filename path-basis regression (#619 follow-up,
# #631): before this, `cmd_scan_frontmatter`/`cmd_scan_filename` keyed `path` relative to
# the `<dir>` argument they were called with, so a `--path notes` scoped call (argument =
# `$VAULT_ROOT/notes`) emitted bare `x.md` instead of `notes/x.md` — a different basis than
# `e5-candidates`, which #619 already made unconditionally `$VAULT_ROOT`-relative. CLASSIFY
# joins an orphan's `frontmatter_records` entry against `e5_candidates` by `path`; the
# mismatched basis meant that join always missed under `--path` scope, so a real orphan
# with a real shared-tag candidate reported "연결 후보 없음". Both primitives now key `path`
# `$VAULT_ROOT`-relative regardless of scope.
python3 obsidian-vault-manager/scripts/test/test-scan-scoped-path-basis.py
# Expected: OK: all cases passed

# audit-state `stats`/`status` op + `list-dirty-since` untracked-file regression (#619):
# before this, no `audit-state` op answered the skill's documented `status` flag
# (any call errored "unknown audit-state op"), and `list-dirty-since` only walked its
# own sidecar `paths` dict — a file the sidecar had never recorded could not surface
# under any reason, so "untracked" was documented but structurally unreachable. Both
# ops now walk the live vault; `status` is accepted as an alias for `stats`.
python3 obsidian-vault-manager/scripts/test/test-audit-state-stats-and-untracked.py
# Expected: OK: all cases passed

# E12 wiki self-audit staleness scoping unit test (#330, #494) — pins detect_stale_wiki's
# wiki-only + type:wiki scope and the strict-> staleness boundary, and pins that a
# missing/unparseable `verified:` is skipped by detect_stale_wiki but surfaced instead by
# detect_unverifiable_wiki (E12_wiki_unverified) — never silently dropped. Complements the
# DoD end-to-end (which only counts seeded/fp). E12b cross-page contradiction is the
# deferred --deep path, not tested here.
python3 obsidian-vault-manager/scripts/test/test-wiki-self-audit.py
# Expected: OK: all cases passed

# manifest-summary.py + manifest-wiki-match.py regression (#468, mirrors #460's retired
# e8-candidates.py pattern) — audit/SKILL.md and wiki/SKILL.md both used to `cat` the raw
# .vault-bridge/manifest.json (100+ KB on a real vault), silently truncated to a 2 KB harness
# preview before the model ever saw it. Runs both filter scripts against real temp fixtures
# (missing/unparseable/malformed/valid), asserts the wiki filter's output stays under the 2 KB
# cut and serializes `scanned` before `wiki_entries`, then statically greps the live SKILL.md
# call sites to pin that neither ever regresses back to a raw `cat`. #663 moved audit's copy of
# that rationale into reference/vault-audit-rules.md -> "Reading the manifest"; the pins followed,
# and the self-test corrupts the canonical text there to prove they still FAIL.
python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py --self-test
# Expected: OK: all 18 self-test cases passed
python3 obsidian-vault-manager/scripts/test/test-manifest-reads.py
# Expected: OK: all manifest-read checks passed

# obsidian-vault-manager trigger-regression check (#471 — routing-SSOT drift guard extended
# to a previously-unguarded face: obsidian-vault-manager/skills/*/SKILL.md +
# obsidian-vault-manager/agents/*.md, one script for both since the issue's face table lists
# them as a single 5+2-item row). Reuses the vault-bridge KR/EN-triggers extractor where a
# file has that label (wiki/SKILL.md); audit/base/vault-file-organizer carry no structured
# trigger list at all and correctly extract an empty set rather than a false regression.
python3 obsidian-vault-manager/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 7 self-test cases passed
python3 obsidian-vault-manager/scripts/test/check-trigger-regression.py origin/main
# Removals are reported (not hard-gated) — reviewer decides if intentional.

# audit-state corrupt-input handling (#443) — parse failure and shape mismatch take the
# SAME path: exit 3, original copied to `audit-state.json.corrupt-<ISO8601>`, the state
# file itself untouched, no `.bak` rotation. The two-ops case is the single-slot `.bak`
# regression guard (the old fallback wrote an empty state and the 2nd write erased the
# original). A healthy state file is the FP guard: exit 0, no sidecar.
python3 obsidian-vault-manager/scripts/test/test-audit-state-corrupt.py
# Expected: OK: all cases passed

# wikilink-masking regression: wikilinks in code are not links (#434, originally the E4
# false-positive story — 27/82 findings (33%) on a 158-note vault were already-backticked
# syntax examples; #482 removed E4 itself, but E5 orphan detection reads the same masked
# inbound-link index, so the masking accuracy this test guards still matters). Drives BOTH
# extractors (ovm-primitives.sh extract-wikilinks via subprocess + audit-validate.py
# collect in-process, the #165 parity pattern) over one fixture, asserts the extracted
# set is EXACTLY the real prose links, and unit-tests mask_code's fence/inline edges.
python3 obsidian-vault-manager/scripts/test/test-wikilink-code-masking.py
# Expected: OK: all cases passed

# audit/SKILL.md vault-root wiring (#619, following #613/#616) — Phase 1 SCAN used to
# hardcode ~/vault for scan-frontmatter/scan-filename/find regardless of
# VAULT_BRIDGE_VAULT_ROOT/VAULT_BRIDGE_VAULT_PATH (the #613 symptom, still reachable
# end-to-end through the skill even after ovm-primitives.sh itself was fixed), and the
# documented --path flag was inert. Pins the SKILL.md wiring (Step 1 resolves $VAULT_ROOT,
# Steps 5-6 use --path-scoped $scan_dir, the link index/E9 check stay vault-wide by design)
# plus the functional --path-scoping behavior against ovm-primitives.sh directly.
python3 obsidian-vault-manager/scripts/test/test-audit-vault-root-wiring.py
# Expected: OK: all 3 audit-vault-root-wiring cases passed

# audit DoD 측정 (mechanical reference impl)
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
#   dod.seeded_detected = {E1:5, E2:5, E3:5, E5:6, E6:5, E9:2, E10:5, E11:5, E12:5,
#     E12_wiki_unverified:2}
#     (E2 has 5: base only — the 5 status-missing seeds went away with the status
#      machine (#480), since a note with no `status:` now conforms; E5 has 6: 5 orphans
#      sharing only the vault-wide `note` tag (candidates:[] under the #495 rarity-weighted
#      floor — see dod.e5_with_candidates below) + 1 empty-tags graceful orphan; E6=stale_inbox
#      (E7/E8 retired with the B-layer
#      promotion gate, v5 §5/§6, #480 — no manifest patch step, no promotion seeds);
#      E9 has 2: vault-level vocabulary pairs (E9a api/apis singular-plural +
#      E9b sourceUrl/source_url camel/snake), path-less findings, P2/no-autofix,
#      counted per pair, FP-guarded by both forms appearing in >=3 files;
#      E10=misplaced_file (type:session in notes/); E11=unstructured_path
#      (2 root-direct + 3 in 20_Projects/), root _index.md exempt;
#      E12 has 5: wiki/ pages with verified:2020 > STALE_WIKI_DAYS (90) — the
#      DETERMINISTIC half of the wiki self-audit rule; cross-page semantic
#      contradiction (E12b) is the deferred --deep LLM path, not seeded;
#      E12_wiki_unverified has 2 (#494): wiki/ pages whose `verified:` is missing
#      or unparseable — a case detect_stale_wiki cannot compute staleness for and
#      used to skip forever; now surfaced as its own finding instead)
#   dod.fp_on_clean per type = 0   (incl. E9/E10/E11/E12/E12_wiki_unverified; root
#     _index.md exercises E11 exempt guard; 2 fresh wiki pages stamped with the run
#     date exercise E12 fp=0)
#   dod.findings_missing_priority = 0
#   dod.priority_mismatches = []
#   dod.e3_with_suggestion >= 5    (E3 권장 파일명 present); dod.e5_with_candidates == 0
#     (#495 — the fixture's 5 tag-bearing orphans all connect only through the vault-wide
#      `note` tag, which no longer clears E5_MIN_CANDIDATE_SCORE alone; candidate-ranking
#      + the floor's non-empty branch are unit-tested directly by
#      test-e5-candidate-ranking.py, not by this fixture)
#   dod.e2_tags_missing = 10; dod.e2_with_inferred_tags = 10   (#127 — every E2
#     tags-missing finding carries a deterministic inferred tag proposal)
# Note: dod.priority_counts is informational only (P1 includes existing
# fixture sources captures with old created: dates, varies by run date).
```
