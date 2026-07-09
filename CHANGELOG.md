# Changelog

## Unreleased

### Removed

* **vault-bridge:** retire the `/save-session` command ([#331](https://github.com/Lyainc/claude-kit/issues/331)). The session-knowledge path is redefined **wiki-first** ([#215](https://github.com/Lyainc/claude-kit/issues/215) 3-axis: local context → native memory (auto), active recall → `wiki` (`/wiki`), option → B): with native memory covering the local axis and `/wiki` the global-knowledge axis, a dedicated session-capture command was redundant. `vault-bridge/commands/save-session.md` is removed; vault-bridge no longer ships any content-authoring command (its remaining writes are `/vault-commit` and `/vault-link`). Raw session ore is still `/capture`, compiled session knowledge is `/wiki` (both obsidian-vault-manager). The machine-level `wrap` orchestrator's first stage moves from capture to `/wiki` accordingly. History of this command: it began as `/wrapup`'s successor, was repurposed from session-note authoring to a capture-ore door (2026-07-08), and is now retired entirely.

* **thinking-tools:** remove the `thought-chain` skill (BREAKING, [#105](https://github.com/Lyainc/claude-kit/issues/105)). Its original removal rationale (a `goal-doc` recipe superseding the fixed 4-stage pipeline) was itself retired ([#282](https://github.com/Lyainc/claude-kit/issues/282)), but ~2 weeks of self-usage telemetry showed 0 invocations of `thought-chain` while its component skills — `expert-panel`, `unknown-discovery`, `doc-concretize` — were each called standalone. An expert-panel review concluded the orchestration wasn't undiscoverable, it was unnecessary: the component skills are already MECE, so users pick the one skill they need directly instead of reaching for a 4-stage pipeline. No thin alias is kept. `expert-panel`, `unknown-discovery`, and `doc-concretize` remain fully available as standalone skills — no functionality is lost.

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
