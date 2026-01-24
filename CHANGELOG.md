# Changelog

## 1.0.0 (2026-01-24)


### Features

* add doc-polish skill for document quality validation ([d79be61](https://github.com/Lyainc/claude-kit/commit/d79be6186f223bc9bbed849d3e9108d4b7aed326))
* Add docx skill from Anthropic official implementation ([6be269e](https://github.com/Lyainc/claude-kit/commit/6be269e165ac921d40c58e9afad60974e79136f6))
* Add docx skill from Anthropic official implementation ([6ede6f4](https://github.com/Lyainc/claude-kit/commit/6ede6f47f90382699aaf16f2639f218c71ae9e5a))
* Add manifest-based version management system ([3e4c88f](https://github.com/Lyainc/claude-kit/commit/3e4c88faa34cd102fbfc2e8fd039077c5d6914e4))
* add marketplace.json for GitHub distribution ([2ed9687](https://github.com/Lyainc/claude-kit/commit/2ed9687d009168055b4ab54c446cdd6a0674574b))
* Add pptx skill based on Anthropic official implementation ([eec1780](https://github.com/Lyainc/claude-kit/commit/eec17803e6cda8c537031f8b3be16808eecd2deb))
* add shared llm-expression-blacklist reference ([f7e62f9](https://github.com/Lyainc/claude-kit/commit/f7e62f9f6bf86c58c8815bab6d859c3dccc35291))
* Add validation hooks and CI/CD automation ([06c0c0b](https://github.com/Lyainc/claude-kit/commit/06c0c0b9ef142ba6aa72f9c528951061633d5a6e))
* Add validation hooks and CI/CD automation ([bfcce9f](https://github.com/Lyainc/claude-kit/commit/bfcce9fa9028ebb2ec5a7c51e675b4069aefe266))
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
* update broken reference in GIT_WORKFLOW.md ([cec06fc](https://github.com/Lyainc/claude-kit/commit/cec06fc2a1b8323190c4824413eb2447e83d160e))
* update paths in validation script and CI workflow ([9cdcec6](https://github.com/Lyainc/claude-kit/commit/9cdcec6df3334d115b06e2db04c838282127bcbb))
* use ./ for root-level plugin source path ([0425de8](https://github.com/Lyainc/claude-kit/commit/0425de8039ae6b53ff4e452d397e38d2121ac827))
* use repo reference instead of relative path in marketplace source ([697d5fd](https://github.com/Lyainc/claude-kit/commit/697d5fd8bf58e0b45bf471cb9a5f2412751d97fe))
