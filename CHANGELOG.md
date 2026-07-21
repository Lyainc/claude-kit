# Changelog

## Unreleased

### Enhanced

* **thinking-tools:** `build-spec` gains an issue-authoring pipeline — adapter, blind-spot pass, isolated gate verdict, backlog scan ([#407](https://github.com/Lyainc/claude-kit/issues/407)). `build-spec` had been classified as a *goal-doc* authoring tool since [#113](https://github.com/Lyainc/claude-kit/issues/113); that format was withdrawn wholesale in [#282](https://github.com/Lyainc/claude-kit/issues/282)/[PR #283](https://github.com/Lyainc/claude-kit/pull/283), leaving the skill with no consumer, which is what "Phase 4: Handoff (out of scope)" had really been describing. A GitHub issue body carries exactly the Seed's fields under different headings, and `docs/design/output-adapter-contract.md` §2 row 8 already registered `format=issue` × `destination=github` with body *authoring* marked as the gap. Four changes land as one cohesive unit, all inside the existing skill — no new plugin, no new skill, so [#140](https://github.com/Lyainc/claude-kit/issues/140)/[#113](https://github.com/Lyainc/claude-kit/issues/113)'s "third authoring primitive" trigger never fires. **Phase 4 (issue adapter)**: opt-in, offered once after the Seed file is written; a fixed field-mapping table (goal+stack→배경, integration points→스코프, constraints→제약, success criteria→`- [ ]` Acceptance, backlog scan+deps→의존/참조, kept blind spots→열린 질문) plus `gh issue create` behind an approval step. The Seed YAML stays Phase 3's terminal artifact and still assumes no *execution* runtime — an output adapter is a rendering, not a runtime. **Phase 2.5 (blind-spot pass)**: exactly once, after the gate opens and before the Seed is written — one `Agent` call for at most 3 findings the interview never covered, surfaced in a single `AskUserQuestion`. It sits after the gate on purpose: earlier, every finding becomes new interview rounds and the skill gets abandoned in real use. It exists because the clarity gate only scores dimensions that were *asked*, so all four can sit at 0.9 while the spec collides with a decision made elsewhere. **Phase 2 (isolated gate verdict)**: the round that would open the gate is re-judged in a separate `Agent` subagent receiving only the Q&A transcript and the `reference.md` §1 checklist — never the running scores — the same isolation `adversarial-review` uses for its Judge ([#115](https://github.com/Lyainc/claude-kit/issues/115)) and `unknown-discovery` for Depth ([PR #416](https://github.com/Lyainc/claude-kit/pull/416)); every other round stays inline (cheap by default), and an `Agent` failure falls back inline with `scoring_isolated: false`. The judge returns **per-dimension** clarity, never one Ambiguity number: floors bind independently of the weighted sum, so a collapsed verdict silently deletes them (brownfield 0.9/0.9/0.9/0.5 gives Ambiguity 0.16, under threshold, with Context below its 0.60 floor) — the same trap PR #416 hit from the other side. **Phase 0 (backlog scan)**: brownfield intake also reads `gh issue list --state open`, because code and manifests carry only what already shipped while a repo's decided-but-unbuilt constraints live in the backlog, leaving X3 (conflicts) with no source; the verdict lands in `context.backlog_scan` and an empty field is not a pass. Self-applied end to end: the fixed skill authored [#418](https://github.com/Lyainc/claude-kit/issues/418) from `docs/specs/thinking-tools-persona-library.yaml`, where the isolated judge scored Success 0.75 by catching that the goal had two axes but the criteria verified one, and all 3 blind-spot findings folded back into the spec (one of them killed an acceptance criterion that was unsatisfiable by construction).

### Fixed

* **thinking-tools:** close improvement-matrix W1 · W2 · W7 ([PR #416](https://github.com/Lyainc/claude-kit/pull/416)). `unknown-discovery` carried all three at once. **W1 (자가검증 순환)**: Exploration Depth scoring and finding verification now run in a separate `Agent` subagent that receives only the area Q&A, the checklist, and the claimed findings — the same mechanical isolation `adversarial-review` uses for its Judge and automated Defender ([#115](https://github.com/Lyainc/claude-kit/issues/115), [PR #403](https://github.com/Lyainc/claude-kit/pull/403)); inline scoring remains the fallback and is flagged via `scoring_isolated: false`. **W2 (게이트 수학 약함)**: Depth moves from a free 0-100% judgement to a 6-item Y/N checklist (D1-D6, fixed weights summing to 100), so `area_score = Σ(weights of Y items)` — the shape `build-spec` already used for Ambiguity — with per-item Y/N and a one-line reason recorded in STATE `scoring_rationale`; the old "-10% on uncertainty signal" rule folds into item D5. The Depth Gate also gains a hard prerequisite — `Depth ≥ 65% AND D4 (발견 1건 이상 도출) = Y in every entered Core area` — because D1+D2+D3 sum to exactly 65, so weight math alone would open the gate with zero discoveries in a skill whose whole purpose is finding them (same shape as `build-spec`'s dimension floors, which gate independently of the Ambiguity sum). **W7 (코드베이스 블라인드)**: `allowed-tools` gains `Agent`, `Grep`, `Glob`, and Phase 0 gains a Repo Context Intake step (`reference.md` §15) that grounds interview questions in README/manifest/code. Both W1 and W7 also name a second skill, so those halves land here too: `doc-concretize` adds one isolated final Verify pass over the assembled document (per-segment inline loop unchanged), and `build-spec` gains `Grep` plus a brownfield content-intake step, since a manifest's existence proves only that the repo is brownfield while X1-X3 can be scored solely off what the code says.

### Removed

* **vault-bridge:** retire the `/save-session` command ([#331](https://github.com/Lyainc/claude-kit/issues/331)). The session-knowledge path is redefined **wiki-first** ([#215](https://github.com/Lyainc/claude-kit/issues/215) 3-axis: local context → native memory (auto), active recall → `wiki` (`/wiki`), option → B): with native memory covering the local axis and `/wiki` the global-knowledge axis, a dedicated session-capture command was redundant. `vault-bridge/commands/save-session.md` is removed; vault-bridge no longer ships any content-authoring command (its remaining writes are `/vault-commit` and `/vault-link`). Raw session ore is still `/capture`, compiled session knowledge is `/wiki` (both obsidian-vault-manager). The machine-level `wrap` orchestrator's first stage moves from capture to `/wiki` accordingly. History of this command: it began as `/wrapup`'s successor, was repurposed from session-note authoring to a capture-ore door (2026-07-08), and is now retired entirely.

* **thinking-tools:** remove the `thought-chain` skill (BREAKING, [#105](https://github.com/Lyainc/claude-kit/issues/105)). Its original removal rationale (a `goal-doc` recipe superseding the fixed 4-stage pipeline) was itself retired ([#282](https://github.com/Lyainc/claude-kit/issues/282)), but ~2 weeks of self-usage telemetry showed 0 invocations of `thought-chain` while its component skills — `expert-panel`, `unknown-discovery`, `doc-concretize` — were each called standalone. An expert-panel review concluded the orchestration wasn't undiscoverable, it was unnecessary: the component skills are already MECE, so users pick the one skill they need directly instead of reaching for a 4-stage pipeline. No thin alias is kept. `expert-panel`, `unknown-discovery`, and `doc-concretize` remain fully available as standalone skills with their analysis capability intact, but the orchestration layer itself has no replacement: checkpoint UX (automatic stage handoff), the partial-pipeline `--skip`/`--start` flags, the deepen mechanic, and `thought_chain:` metadata aggregation (`stages_run` etc.) are gone. Full GO/NO-GO decision record (5-expert-panel review, telemetry evidence): [#105 comment](https://github.com/Lyainc/claude-kit/issues/105#issuecomment-4933546564).

* **vault-bridge:** retire the `/handoff` command and its `resume.md` mechanism (G26, decision G25 D4). The next-session handoff function — authoring a continuation / START-PROMPT — is superseded by the machine-level `session-close` skill, which lives in the owner's personal kit and is not shipped in claude-kit. `vault-bridge/commands/handoff.md`, `scripts/resolve-resume-path.sh`, and `test/test-handoff-guard.sh` are removed; `/save-session` (record/quick) and the manifest system are unaffected.

* **vault-bridge:** remove the `/save-plan-doc` command and the `plan-doc-syncer.py` "③ delivery" intake (G21, [#215](https://github.com/Lyainc/claude-kit/issues/215)). The plan-doc snapshot path was a dual-source antipattern with three weeks of zero telemetry, so it is cut. The `snapshot_export` / `snapshot_import` opt-in gates (boundary POL-5) and the `autosync_paths_include` / `autosync_paths_exclude` `.vault-link` keys are removed with it; the SessionEnd hook no longer scans for plan-doc candidates. `/save-session` (record/quick) and the manifest system are unaffected. thought-chain's vault destination now routes to `vault-bridge:save-session` (with a `plan` arg for plan docs), gated only on `.vault-link` presence.

## [2.0.0](https://github.com/Lyainc/claude-kit/compare/v1.2.0...v2.0.0) (2026-04-13)


### ⚠ BREAKING CHANGES

* plugin name changed from "vault-reader" to "vault-bridge" (v1.0.0). The plugin's scope expanded beyond read-only search (now includes session-note creation, Stop/SessionEnd hooks, /save-session command), so the new name reflects the two-way bridge role between external projects and the Obsidian vault.
* **obsidian-vault-manager:** vault-daily skill is removed from obsidian-vault-manager v0.5.0. Use capture for quick memos or session-note for session records. Existing daily-*.md files in vault remain readable but no longer created via slash command.

### Features

* **obsidian-vault-manager:** remove vault-daily skill ([#53](https://github.com/Lyainc/claude-kit/issues/53)) ([715cea0](https://github.com/Lyainc/claude-kit/commit/715cea042c1fc458bd884d6ea6398bf2c09d843e))


### Code Refactoring

* rename vault-reader plugin to vault-bridge ([#56](https://github.com/Lyainc/claude-kit/issues/56)) ([b65c243](https://github.com/Lyainc/claude-kit/commit/b65c2431f5feb24d4f79d83dcb5049baec5cc787))

## [1.2.0](https://github.com/Lyainc/claude-kit/compare/v1.1.0...v1.2.0) (2026-04-13)


### Features

* add Stop hook for session-note suggestion ([44d6085](https://github.com/Lyainc/claude-kit/commit/44d6085e2f0560a3e29b93049f45a41d0d296b53))
* replace handoff with session-note in vault-reader ([65deb2e](https://github.com/Lyainc/claude-kit/commit/65deb2e728aeff5dd2fb3518049d29bf6a64011a))
* **vault-reader:** make vault-searcher proactively invoked for vault access ([5157b73](https://github.com/Lyainc/claude-kit/commit/5157b7375f8c802db23c28e4123c14600ef89d89))
* vault-searcher proactive invocation + hook refinement + cleanup ([2946e53](https://github.com/Lyainc/claude-kit/commit/2946e53d7f46cbb6f01fe1239268d3f2a1270e44))


### Bug Fixes

* address PR [#50](https://github.com/Lyainc/claude-kit/issues/50) review feedback ([131e4c2](https://github.com/Lyainc/claude-kit/commit/131e4c2949d1d3266e3bbcc3b68fb46e1cc896d3))
* address PR [#50](https://github.com/Lyainc/claude-kit/issues/50) second review feedback ([34bee92](https://github.com/Lyainc/claude-kit/commit/34bee92a4967099a1fb7e1cf28291e8b7c997ddb))
* refine session-note hooks to avoid per-turn prompt fatigue ([a6e051f](https://github.com/Lyainc/claude-kit/commit/a6e051ffa6c93dfb193469223b0b135706c3dc42))
* **vault-reader:** expand hook signal coverage and tighten sessionend threshold ([75a6a6c](https://github.com/Lyainc/claude-kit/commit/75a6a6caa54848ee2805e7508ac3c7e9e7e126c5))
* **vault-reader:** probe UTF-8 locale in stop-check.sh + document jq dep ([b2198e9](https://github.com/Lyainc/claude-kit/commit/b2198e908327c724cba4698c60817793c3bf044d))
* **vault-reader:** replace prompt-based Stop hook with deterministic shell script ([2ee8691](https://github.com/Lyainc/claude-kit/commit/2ee869135c0e8f8db8d71a811729edeb931d7f3a))
* **vault-reader:** replace prompt-based Stop hook with deterministic shell script ([3d04628](https://github.com/Lyainc/claude-kit/commit/3d046288c180d1d418bbd3eec206bd27549caca6))

## [1.1.0](https://github.com/Lyainc/claude-kit/compare/v1.0.1...v1.1.0) (2026-04-07)


### Features

* add vault-reader plugin and handoff integration ([eb321f6](https://github.com/Lyainc/claude-kit/commit/eb321f6255b7b45cc5acdac4da65aa86a078afb4))
* add vault-reader plugin with vault-searcher I/O agent ([54f0394](https://github.com/Lyainc/claude-kit/commit/54f0394163c83b76bd2a566a781430fc3e2aec28))
* improve thinking-tools and obsidian-vault-manager plugins ([#45](https://github.com/Lyainc/claude-kit/issues/45)) ([8036c92](https://github.com/Lyainc/claude-kit/commit/8036c929acf1f35e4ac12750b76004bd07144282))
* integrate handoff support into context, vault-daily, wrapup skills ([7168ea1](https://github.com/Lyainc/claude-kit/commit/7168ea1f4864fca24ac0530bfc50ef6cb7b3d4cb))


### Bug Fixes

* add packages block to release-please config ([6c45556](https://github.com/Lyainc/claude-kit/commit/6c45556b008b49623f5577dce44089560c54edf8))
* address PR [#43](https://github.com/Lyainc/claude-kit/issues/43) review feedback ([da73098](https://github.com/Lyainc/claude-kit/commit/da73098e875e3b9e5430ca913d78f6b306095c09))
* address PR [#46](https://github.com/Lyainc/claude-kit/issues/46) review feedback ([955b8b8](https://github.com/Lyainc/claude-kit/commit/955b8b82087a49ea99d690cb32200d0ad559ce9a))
* address PR [#46](https://github.com/Lyainc/claude-kit/issues/46) second review feedback ([7d3d22c](https://github.com/Lyainc/claude-kit/commit/7d3d22cd4484748bca00d4c6837cf8c6b26793d3))
* address PR [#47](https://github.com/Lyainc/claude-kit/issues/47) review feedback ([87fbd0c](https://github.com/Lyainc/claude-kit/commit/87fbd0c25223bdbbec382242d0346b02b41d7955))
* restore Korean output template headers in context/SKILL.md ([e828881](https://github.com/Lyainc/claude-kit/commit/e828881fa1d1e815d108a6545de42c92d035c143))

## [1.0.1](https://github.com/Lyainc/claude-kit/compare/v1.0.0...v1.0.1) (2026-04-05)


### Bug Fixes

* address PR [#41](https://github.com/Lyainc/claude-kit/issues/41) review feedback ([3b32c0b](https://github.com/Lyainc/claude-kit/commit/3b32c0b61c596ecf87b4f5def11c721ce9231456))

## 1.0.0 (2026-03-17)


### Features

* add devstarter skill ([0f94c5e](https://github.com/Lyainc/claude-kit/commit/0f94c5e27b870255c931994dd5468aae0cd4392e))
* add devstarter skill for consistent development workflow ([16b8488](https://github.com/Lyainc/claude-kit/commit/16b84883c14962f99eec26a0ca084303104a4dec))
* add doc-polish skill for document quality validation ([d79be61](https://github.com/Lyainc/claude-kit/commit/d79be6186f223bc9bbed849d3e9108d4b7aed326))
* Add docx skill from Anthropic official implementation ([6be269e](https://github.com/Lyainc/claude-kit/commit/6be269e165ac921d40c58e9afad60974e79136f6))
* Add docx skill from Anthropic official implementation ([6ede6f4](https://github.com/Lyainc/claude-kit/commit/6ede6f47f90382699aaf16f2639f218c71ae9e5a))
* Add manifest-based version management system ([3e4c88f](https://github.com/Lyainc/claude-kit/commit/3e4c88faa34cd102fbfc2e8fd039077c5d6914e4))
* add marketplace.json for GitHub distribution ([2ed9687](https://github.com/Lyainc/claude-kit/commit/2ed9687d009168055b4ab54c446cdd6a0674574b))
* Add pptx skill based on Anthropic official implementation ([eec1780](https://github.com/Lyainc/claude-kit/commit/eec17803e6cda8c537031f8b3be16808eecd2deb))
* add shared llm-expression-blacklist reference ([f7e62f9](https://github.com/Lyainc/claude-kit/commit/f7e62f9f6bf86c58c8815bab6d859c3dccc35291))
* Add validation hooks and CI/CD automation ([06c0c0b](https://github.com/Lyainc/claude-kit/commit/06c0c0b9ef142ba6aa72f9c528951061633d5a6e))
* Add validation hooks and CI/CD automation ([bfcce9f](https://github.com/Lyainc/claude-kit/commit/bfcce9fa9028ebb2ec5a7c51e675b4069aefe266))
* **devstarter:** add Language Behavior, Output Format sections and examples ([5f9ebe4](https://github.com/Lyainc/claude-kit/commit/5f9ebe4bc3fc9bcae7b826d6beeb424f6e3112d6))
* doc-concretize 개선 및 doc-polish 신규 스킬 추가 ([eb14d4f](https://github.com/Lyainc/claude-kit/commit/eb14d4fc56da1e70b19899f04f6043d767623a21))
* **plugin:** Convert repository to Claude Code plugin structure ([#14](https://github.com/Lyainc/claude-kit/issues/14)) ([679ae27](https://github.com/Lyainc/claude-kit/commit/679ae2797372ebe5ac7f078036225d87b8770c38))
* **skills:** Add diverse-sampling skill ([72cf5f5](https://github.com/Lyainc/claude-kit/commit/72cf5f5091f8991b497e8ffd631e1646c498995f))
* **skills:** Add diverse-sampling skill using Verbalized Sampling technique ([9e6b47b](https://github.com/Lyainc/claude-kit/commit/9e6b47b8f38d62a4e3b596929ac49593a16ab0fe))
* **skills:** add output terminology and mark internal sections ([a3a12e7](https://github.com/Lyainc/claude-kit/commit/a3a12e7cd7f16010fb8a9f50a3300af3be65bf22))
* **skills:** Add unknown-discovery skill for blind spot detection ([6f23928](https://github.com/Lyainc/claude-kit/commit/6f239284f5f6ca5a0d11d2849d650e63be7750f4))
* **skills:** Add unknown-discovery skill for blind spot detection ([1640a75](https://github.com/Lyainc/claude-kit/commit/1640a75f3bc3d042293ff255e7d13de3bc6df3a4))
* **skills:** Improve doc-concretize with English instructions and quality gates ([#13](https://github.com/Lyainc/claude-kit/issues/13)) ([622b555](https://github.com/Lyainc/claude-kit/commit/622b5558433e00672aad74228814b0fc3b524590))
* **skills:** Improve DOCX/PPTX skill workflows for better quality ([9d50305](https://github.com/Lyainc/claude-kit/commit/9d503054c15e143e076aab7aa35f7c3059234d51))
* **skills:** Improve DOCX/PPTX skill workflows for better quality ([0c4d703](https://github.com/Lyainc/claude-kit/commit/0c4d7036691006e7e3fec906e20bd3046177f4cc))
* **skills:** update output format and add model capabilities ([d76dd74](https://github.com/Lyainc/claude-kit/commit/d76dd74a3cea47a8c0abeec23fae3164adbc12fc))


### Bug Fixes

* Add "문제 발견 시" guidance to quality checklists ([4f3ab4b](https://github.com/Lyainc/claude-kit/commit/4f3ab4bf48229c3e56dbb01b94c91ea3b72512ff))
* Add || true to all arithmetic expressions for set -e compatibility ([fdbfbd6](https://github.com/Lyainc/claude-kit/commit/fdbfbd6299de0ad46570e782666397b9ea1594e3))
* add missing "skills" keyword to marketplace.json ([fbaf33f](https://github.com/Lyainc/claude-kit/commit/fbaf33f001f0b61bc1b63c77706c0feea038baf3))
* address additional PR review high-priority items ([fe6ede9](https://github.com/Lyainc/claude-kit/commit/fe6ede973d15411e2727d1ceb67d259239fc650f))
* address Architect review feedback ([9ef1b3f](https://github.com/Lyainc/claude-kit/commit/9ef1b3fe172657408084b993fcd5267ae64d7b34))
* address PR [#39](https://github.com/Lyainc/claude-kit/issues/39) review feedback for unknown-discovery skill ([083d4ee](https://github.com/Lyainc/claude-kit/commit/083d4eef8011f2185778e186f1c573ed3af40bd3))
* address PR review feedback ([883e87a](https://github.com/Lyainc/claude-kit/commit/883e87a08df94efca8278e05a325a1d68b8d2c17))
* address PR review feedback on devstarter skill ([9fd5bfa](https://github.com/Lyainc/claude-kit/commit/9fd5bfae729060221802b52b4c6f35399070d24d))
* address second round PR [#39](https://github.com/Lyainc/claude-kit/issues/39) review feedback ([efa0f19](https://github.com/Lyainc/claude-kit/commit/efa0f193e05ade03a4b62e77f9d3c51a9992933c))
* Completely resolve race condition and add jq dependency check ([5d5da4e](https://github.com/Lyainc/claude-kit/commit/5d5da4e1e7a5e6fa0ae96dd994bfd81495bcce0a))
* **diverse-sampling:** change percentage normalization base to 100% ([9a9d837](https://github.com/Lyainc/claude-kit/commit/9a9d8379bf6c287f83e2770d2c273c2ed1d5d32f))
* exclude _TEMPLATE from skill/agent list ([4738a14](https://github.com/Lyainc/claude-kit/commit/4738a1469af5867fc33e61bf6913777ec90acfa3))
* Limit orphaned file detection to managed paths only ([4a97b98](https://github.com/Lyainc/claude-kit/commit/4a97b9885d86b12a6cc73c651401ba8f714dd404))
* remove unsupported changelog-types from release-please workflow ([9277547](https://github.com/Lyainc/claude-kit/commit/9277547d827095ba3512ca8df1721ef64d159bac))
* rename template files to prevent auto-loading ([acc73d7](https://github.com/Lyainc/claude-kit/commit/acc73d7d5bbd97dedc77f294734c2ffa5515d467))
* Resolve race conditions and permission issues in validation hooks ([18a128b](https://github.com/Lyainc/claude-kit/commit/18a128b787bca378d7c867fe07e189ec1eff0716))
* Resolve set -e conflict in validation script ([83b5546](https://github.com/Lyainc/claude-kit/commit/83b554697bf93e81e6a82f0775759853808bb0fa))
* Resolve set -e conflict with && continue patterns ([812ccc6](https://github.com/Lyainc/claude-kit/commit/812ccc6b7e02b0384e166d0675f1392a6b751051))
* restructure marketplace.json to match valid schema ([8773e70](https://github.com/Lyainc/claude-kit/commit/8773e70dce2119a53c1fef04c1094f999663d1c4))
* **skills:** Apply code review feedback for unknown-discovery ([b4c827e](https://github.com/Lyainc/claude-kit/commit/b4c827e3adb5ab9cf75daeb27f8a10dbefa4397d))
* sync marketplace.json version and description with plugin.json ([5d81d6a](https://github.com/Lyainc/claude-kit/commit/5d81d6a1de9b37a23ae8482b69c4f7474facf8f7))
* **unknown-discovery:** correct cross-reference §2 → §3 in SKILL.md ([b4463e3](https://github.com/Lyainc/claude-kit/commit/b4463e3ea0d4d00688548dd7342d815fc6fcca03))
* **unknown-discovery:** restore Domain Presets table and fix section numbering ([1258709](https://github.com/Lyainc/claude-kit/commit/1258709553277997153367d3370b6adb01d8e0a4))
* update broken reference in GIT_WORKFLOW.md ([cec06fc](https://github.com/Lyainc/claude-kit/commit/cec06fc2a1b8323190c4824413eb2447e83d160e))
* update paths in validation script and CI workflow ([9cdcec6](https://github.com/Lyainc/claude-kit/commit/9cdcec6df3334d115b06e2db04c838282127bcbb))
* use ./ for root-level plugin source path ([0425de8](https://github.com/Lyainc/claude-kit/commit/0425de8039ae6b53ff4e452d397e38d2121ac827))
* use repo reference instead of relative path in marketplace source ([697d5fd](https://github.com/Lyainc/claude-kit/commit/697d5fd8bf58e0b45bf471cb9a5f2412751d97fe))
