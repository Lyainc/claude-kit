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
python3 scripts/check-plugin-root-paths.py --self-test
# Expected: OK: all 6 check-plugin-root-paths self-test cases passed
python3 scripts/check-plugin-root-paths.py
# Expected: OK: plugin-root-paths clean — N SKILL.md checked, every bundled-script
#   invocation is ${CLAUDE_PLUGIN_ROOT}-anchored
# A SKILL.md code block runs with CWD = the CONSUMER's project, so a repo-relative call like
# `python3 feedback-loop/scripts/report.py 2>/dev/null` resolves ONLY inside this checkout —
# for every plugin-installed user it silently no-ops. Found live in retro/SKILL.md (4 call
# sites, shipped in v4.0.0). Scans source plugins only (dirs with a plugin.json), so the
# vendored .codex/ caches are never touched. Markdown `../../reference/*.md` links are NOT
# flagged — those resolve relative to the SKILL.md file and stay correct once installed.
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

# vault-bridge agent trigger-regression check (#338 — sibling to the thinking-tools
# check below, adapted for vault-bridge's single-line quoted `description: "..."`
# agent frontmatter with inline "KR triggers: ... EN triggers: ..." labels).
# Self-test the extractor:
python3 vault-bridge/scripts/test/check-trigger-regression.py --self-test
# Expected: OK: all 7 self-test cases passed
# Diff trigger sets between a base ref and the working tree (exit 1 = removals found):
python3 vault-bridge/scripts/test/check-trigger-regression.py origin/main
# Removals are reported (not hard-gated) — reviewer decides if intentional.

# feedback-loop telemetry schema self-test (#217 — telemetry absorbed into feedback-loop)
python3 feedback-loop/scripts/validate-schema.py --self-test

# feedback-loop report.py latency_by_event regression gate (#164)
# + per-skill lifecycle view (never-fired / stale / bottom-N vs */skills/*/SKILL.md catalog, #203)
python3 feedback-loop/scripts/test/test-report.py
# Expected: OK: all cases passed
# event-logger meta-extractor unit test (extract_end_meta / extract_stop_meta)
bash feedback-loop/scripts/test/test-event-logger.sh
# Expected: OK: all event-logger meta-extractor cases passed

# retro-telemetry helper regression (#294 — retro Phase-1 stamp + Phase-4 emit
# extracted from the SKILL.md inline bash to scripts/retro-telemetry.sh; this
# pins the schema-shaped emit line + duration null-fallback against drift).
bash feedback-loop/scripts/test/test-retro-telemetry.sh
# Expected: OK: all retro-telemetry cases passed

# add-policy layer-routing regression (G28 — add-policy is a prose skill, so this is a
# static-content check on the live SKILL.md: the SOFT reminder channel is routed by layer
# (stance/voice→~/.claude/CLAUDE.md, work-rule→~/.claude/rules) with a vanilla fallback
# (rules absent→CLAUDE.md) and a never-hardcode-the-rules/-structure clause. Guards the
# "both rules-present and rules-absent branches are described" claim against drift.)
python3 feedback-loop/scripts/test/test-add-policy-routing.py --self-test
# Expected: OK: all 12 self-test cases passed
python3 feedback-loop/scripts/test/test-add-policy-routing.py
# Expected: OK: all 6 add-policy-routing checks passed.

# add-policy §6 conflict-check Edit bucket regression (#303 — an explicit "change this
# existing entry" request is its own conflict-check outcome, distinct from Duplicate
# (strengthen) and Contradiction (refuse); guards against it collapsing back into either.)
python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py --self-test
# Expected: OK: all 7 self-test cases passed
python3 feedback-loop/scripts/test/test-add-policy-conflict-edit.py
# Expected: OK: all 3 add-policy-conflict-edit checks passed.

# add-policy §6 index+detail split regression (#340 — when the target landfill site
# already uses a thin index + per-entry detail-file shape, add-policy must match that
# shape (one index row + a linked detail file) instead of appending a new inline block,
# and must never invent this split on a site that doesn't already use it.)
python3 feedback-loop/scripts/test/test-add-policy-index-detail.py --self-test
# Expected: OK: all 8 self-test cases passed
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

# expert-panel mode-compose regression (#228) — verifies the SKILL.md's "all combinations
# compose silently" claim: every declared mode toggle (격리/요약 + citation grounding +
# Phase 2 inline path) is described and non-contradictory. Run after editing expert-panel
# mode/Phase structure or the Citation Contract.
python3 thinking-tools/scripts/test/test-mode-compose.py --self-test
# Expected: OK: all 16 self-test cases passed
python3 thinking-tools/scripts/test/test-mode-compose.py
# Expected: OK: all 9 mode-compose checks passed. (static check against the live SKILL.md)

# session-start onboarding hook regression (#117) — first-run discoverability hint
# hosted in thinking-tools SessionStart (vault-independent entry plugin; C-2 forbids a
# 4th "welcome" plugin). Verifies 3-session grace, kill switch, corrupt-counter recovery,
# and valid systemMessage JSON. State = single integer file under CLAUDE_CONFIG_DIR.
bash thinking-tools/scripts/test/test-session-start-welcome.sh
# Expected: OK: all session-start-welcome cases passed

# Shell hook syntax check
bash -n vault-bridge/hooks/*.sh
bash -n thinking-tools/hooks/session-start-welcome.sh   # #117 first-run onboarding hint
bash -n feedback-loop/scripts/event-logger.sh
bash -n feedback-loop/scripts/retro-telemetry.sh   # #294 retro stamp/emit helper
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
# Expected: OK: all 9 cases passed

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

# E12 wiki self-audit staleness scoping unit test (#330) — pins detect_stale_wiki's
# wiki-only + type:wiki scope, the strict-> staleness boundary, and the graceful skip
# on missing/unparseable `verified:`. Complements the DoD end-to-end (which only counts
# seeded/fp). E12b cross-page contradiction is the deferred --deep path, not tested here.
python3 obsidian-vault-manager/scripts/test/test-wiki-self-audit.py
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
#   dod.seeded_detected = {E1:5, E2:10, E3:5, E4:5, E5:6, E6:5, E7:5, E8:2, E9:2, E10:5, E11:5, E12:5}
#     (E2 has 10: 5 base + 5 status-missing; E5 has 6: 5 w/ tag candidates +
#      1 empty-tags graceful orphan; E6=stale_inbox; E7=stale_draft;
#      E8 has 2: promotion-target via refs_in=3, access-target via manifest patch;
#      E9 has 2: vault-level vocabulary pairs (E9a api/apis singular-plural +
#      E9b sourceUrl/source_url camel/snake), path-less findings, P2/no-autofix,
#      counted per pair, FP-guarded by both forms appearing in >=3 files;
#      E10=misplaced_file (type:session in notes/); E11=unstructured_path
#      (2 root-direct + 3 in 20_Projects/), root _index.md exempt;
#      E12 has 5: wiki/ pages with verified:2020 > STALE_WIKI_DAYS (90) — the
#      DETERMINISTIC half of the wiki self-audit rule; cross-page semantic
#      contradiction (E12b) is the deferred --deep LLM path, not seeded)
#   dod.fp_on_clean per type = 0   (incl. E9/E10/E11/E12; root _index.md exercises E11
#     exempt guard; 2 fresh wiki pages stamped with the run date exercise E12 fp=0)
#   dod.findings_missing_priority = 0
#   dod.priority_mismatches = []
#   dod.e3_with_suggestion >= 5    (E3 권장 파일명 present); dod.e5_with_candidates > 0
#   dod.e2_tags_missing = 10; dod.e2_with_inferred_tags = 10   (#127 — every E2
#     tags-missing finding carries a deterministic inferred tag proposal)
# Note: dod.priority_counts is informational only (P1 includes existing
# fixture inbox captures with old created: dates, varies by run date).
```
