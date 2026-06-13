# Changelog

## [3.0.0](https://github.com/Lyainc/claude-kit/compare/v2.0.0...v3.0.0) (2026-06-13)


### ⚠ BREAKING CHANGES

* **vault-bridge:** vault-bridge configs using `auto_capture` in .vault-link or _index.md no longer enable plan-doc autosync. Use `snapshot_export` (.vault-link) and `snapshot_import` (_index.md) instead.
* **thinking-tools:** thinking-tools skills no longer accept CLI-style flags; use natural language instead. Migration:
    - spec-first: --quick→"빠르게"/"스펙만"/"quick"; --with-repo→name repo root in prose;
      --refine→"이 스펙 다듬어줘"+path; --with-ralph→"ralph로 이어줘"
    - adversarial-review: --auto→"자동으로 돌려줘"; --deep→"엄격하게"/"격리해서";
      --brief→"요약만"; --quick→"빠르게"/"간단히"/"quick"
    - diverse-sampling: --all→"전부 보여줘"; --best→"제일 나은 것"; --count N→"N개 만들어줘"
    - expert-panel: --deep→"엄격하게"/"격리해서"; --brief→"요약만"/"transcript 없이"
    - unknown-discovery: --quick→"빠르게"/"간단히"/"quick"
    doc-polish keeps --fix (operational auto-correction toggle), out of scope.

### Features

* add per-skill model tiering across OVM and thinking-tools ([1650ee6](https://github.com/Lyainc/claude-kit/commit/1650ee6b295a70f8c6099aad50e738fe777d8bae))
* **adversarial-review:** ground Evidence Attack in vault decision records via vault-searcher ([f4eb69f](https://github.com/Lyainc/claude-kit/commit/f4eb69f9a50703a6590826140c78dc84c4c8319d))
* **agents:** add example blocks to thinking-facilitator, vault-knowledge-manager, vault-file-organizer, vault-searcher ([8b29d9e](https://github.com/Lyainc/claude-kit/commit/8b29d9e84478dae2613f9e334a02d7e96b03821e))
* **ci:** add severity gate + nit defer + no-re-flag to claude review ([#169](https://github.com/Lyainc/claude-kit/issues/169)) ([471a47e](https://github.com/Lyainc/claude-kit/commit/471a47e3a222093bd13b833435c8e84133636d49))
* **ci:** add version-sync + CI-coverage governance guards ([#134](https://github.com/Lyainc/claude-kit/issues/134)) ([abc4f36](https://github.com/Lyainc/claude-kit/commit/abc4f364f8ee049c7a15045703c554a6042d5c79))
* **expert-panel:** add isolated-mode multi-turn rebuttal exchanges ([#143](https://github.com/Lyainc/claude-kit/issues/143)) ([88043e6](https://github.com/Lyainc/claude-kit/commit/88043e6656d07cab567a1fb0c2288d7d6ae36c18))
* **expert-panel:** add STATE block for resumability across topic rounds ([79781d1](https://github.com/Lyainc/claude-kit/commit/79781d1ca66c2572f3b33e06d6db4edf4a3c89fa))
* master plan phase 1 — W0/W1/W2/W3/W7/W8/W10 ([ab0af4e](https://github.com/Lyainc/claude-kit/commit/ab0af4ee97931f51326c98da2c2346555185a4a2))
* **obsidian-vault-manager:** add note↔project bidirectional binding ([df17ecc](https://github.com/Lyainc/claude-kit/commit/df17ecc1de4ad3fba2b5b4e4521ea0c98de28406))
* **obsidian-vault-manager:** add ovm-primitives shell CLI (W2 Phase 0) ([6a526a5](https://github.com/Lyainc/claude-kit/commit/6a526a57ee24c99f44f39dba5933457c88d38f2b))
* **obsidian-vault-manager:** add vault-audit skill with 8-error taxonomy (W2 Phase B) ([d9d7579](https://github.com/Lyainc/claude-kit/commit/d9d757905f5fcd0aa02adbb6ce297be1ded83cb3))
* **obsidian-vault-manager:** tighten vault-audit detection logic and fixture coverage ([3a7ecf7](https://github.com/Lyainc/claude-kit/commit/3a7ecf710a14ec444836ce76e833018b12fe3d39))
* **obsidian-vault-manager:** U7 resolved — explicit auto_capture opt-in (v0.11.0) ([abfdf4d](https://github.com/Lyainc/claude-kit/commit/abfdf4d21af32e8153646e0a975ac2f58674d139))
* **obsidian-vault-manager:** W5 obsidian refs + CLI helpers, hold ingest ([1b01041](https://github.com/Lyainc/claude-kit/commit/1b01041f4a69ee9811b9bb9548734c49d8782c85))
* **obsidian-vault-manager:** W7 note skill bidirectional back-reference ([f0940f9](https://github.com/Lyainc/claude-kit/commit/f0940f9a490364d07aa5f5d7ebb717c0a85b5110))
* **ovm/audit:** add E10/E11 checks + E3 rename suggestion + E5 link candidates ([9baddcc](https://github.com/Lyainc/claude-kit/commit/9baddcc61e226662fd28ea6f0b4815fc0a18feed))
* **ovm/audit:** batch E2 infer-tags + OSError exit-code policy ([#152](https://github.com/Lyainc/claude-kit/issues/152)) ([20ccd3a](https://github.com/Lyainc/claude-kit/commit/20ccd3a786b5a4c026fc095d24c75e9294a8a3df))
* **ovm/audit:** E9 tag/property vocabulary consistency check ([#119](https://github.com/Lyainc/claude-kit/issues/119)) ([8c8d03b](https://github.com/Lyainc/claude-kit/commit/8c8d03bb2108dc6a238545ee2f1bc209a8556171))
* **ovm/audit:** infer E2 auto-fix tags from type/filename/folder ([33de22f](https://github.com/Lyainc/claude-kit/commit/33de22f7c366fdcbb4fc3113ecf106f852a6b240))
* **ovm/audit:** Phase 1 expansion — priority mapping, manifest display, E2 status fixture ([c388542](https://github.com/Lyainc/claude-kit/commit/c3885420c139c2509dafb149f1c52ed2b0ac66ac))
* **ovm/audit:** Phase 2 — P1 stagnation checks (E6 stale_inbox, E7 stale_draft) ([2b1cc13](https://github.com/Lyainc/claude-kit/commit/2b1cc13a1316e73b23359a168ead9c2915d451f5))
* **ovm/audit:** surface 7-day git activity in REPORT header ([bda10b9](https://github.com/Lyainc/claude-kit/commit/bda10b914917955b15be89a548ed387a0bc6c04a))
* **ovm/audit:** surface promotion candidates as E8 findings (PR 4d) ([4d050a6](https://github.com/Lyainc/claude-kit/commit/4d050a60a2bb520fc2f0baa2f3d66a7918e351d4))
* **ovm/audit:** surface promotion_candidate count in REPORT header ([07e66a2](https://github.com/Lyainc/claude-kit/commit/07e66a20f4222b6558a1d59c75894b05fb03a328))
* **ovm:** /base skill — generate Obsidian Bases (.base) views ([#118](https://github.com/Lyainc/claude-kit/issues/118)) ([8b98e50](https://github.com/Lyainc/claude-kit/commit/8b98e5036041eab1655e44dd58174e1cca35e5a0))
* **ovm+vault-bridge:** capture URL metadata + web-clipper template + resume visibility ([04d718f](https://github.com/Lyainc/claude-kit/commit/04d718f9c383cbe9def717f1213d275df0cac11a))
* **ovm:** rename vault-audit → audit, v4 paths, E1-E5 only ([ec9312e](https://github.com/Lyainc/claude-kit/commit/ec9312e3a35c0f7b7e634d84e2f950c9c57bec2a))
* subagent return-contract + vault manifest access-ranking ([#211](https://github.com/Lyainc/claude-kit/issues/211)) ([8849322](https://github.com/Lyainc/claude-kit/commit/88493227446a9921d578a9d67e05465d5c2a8d0e))
* **telemetry:** activate latency report + stop-meta synthetic tests ([#153](https://github.com/Lyainc/claude-kit/issues/153)) ([f6b319f](https://github.com/Lyainc/claude-kit/commit/f6b319f00cd711dc8c3dea1660c0af2cafdd4d73))
* **telemetry:** per-event-type latency breakdown + stop-meta dogfooding ([#159](https://github.com/Lyainc/claude-kit/issues/159)) ([4c3d5ad](https://github.com/Lyainc/claude-kit/commit/4c3d5ade1de9b88db2c395f0bed8f2c3374de2ff))
* **telemetry:** per-skill lifecycle derived view — never-fired/stale/bottom-N ([#203](https://github.com/Lyainc/claude-kit/issues/203)) ([d811c7c](https://github.com/Lyainc/claude-kit/commit/d811c7c3b774b85788dc1a5657383da1a0e312be))
* **telemetry:** populate event meta with token counts and duration_ms ([c181db7](https://github.com/Lyainc/claude-kit/commit/c181db710da5a6937a6a77606ae79efa9609f37e))
* **telemetry:** scaffold W1 MVP for Phase 1 dogfooding ([04ed77d](https://github.com/Lyainc/claude-kit/commit/04ed77d49507b60ed4e8908dfd05b6b5f2cde4d3))
* **thinking-tools:** add adversarial-review skill ([6dcc005](https://github.com/Lyainc/claude-kit/commit/6dcc00511f05ac438aea132e8107e9aab1693821))
* **thinking-tools:** add spec-first skill + 5-stage thought-chain pipeline ([#78](https://github.com/Lyainc/claude-kit/issues/78)) ([5818186](https://github.com/Lyainc/claude-kit/commit/58181868658c44914c2e90fb14ea58e030b61981))
* **thinking-tools:** execution modes + visibility contracts (v1.8.1) ([#77](https://github.com/Lyainc/claude-kit/issues/77)) ([bd18d39](https://github.com/Lyainc/claude-kit/commit/bd18d39b8cdd62d16a4e8f6b53f8fe885e6437c8))
* **thinking-tools:** slim skill descriptions — KR 3-5 + EN 2-3 triggers, ≤1000 chars each ([40182d4](https://github.com/Lyainc/claude-kit/commit/40182d46d69bd7bc3ca8ce819f5a01cb888b6277))
* **thought-chain:** add 5-option checkpoint and vault save integration ([30d9b07](https://github.com/Lyainc/claude-kit/commit/30d9b072753d2f5cb0f00d5ee69604f5b0d0ab7f))
* **vault-bridge/handoff:** compact resume display on SessionStart ([1a6faa2](https://github.com/Lyainc/claude-kit/commit/1a6faa2703b7ca3a0914dd271e453b5f6481cb3f))
* **vault-bridge:** add --recent mtime filter and --summary breakdown ([1d540e3](https://github.com/Lyainc/claude-kit/commit/1d540e331ba542df7ec0ae5a1f0091ac19bd7644))
* **vault-bridge:** add .vault-link pointer-based project binding ([af15ad7](https://github.com/Lyainc/claude-kit/commit/af15ad70c6987fa19c88871b9f6fea5bd43a6bab))
* **vault-bridge:** add /handoff command and resume.md session handoff ([c4ac038](https://github.com/Lyainc/claude-kit/commit/c4ac03829e950c5741f97b479f267154a5b21c4b))
* **vault-bridge:** add /vault-commit slash command for approved auto-commits ([93d6872](https://github.com/Lyainc/claude-kit/commit/93d687255fe99b2a7af578651d2a7eb08ddf747d))
* **vault-bridge:** add direct-access guard with soft warnings ([dee4e34](https://github.com/Lyainc/claude-kit/commit/dee4e34e463e4ed0723e2e6e743bca1a7ad25e3a))
* **vault-bridge:** add disable-model-invocation to all slash commands ([b10759a](https://github.com/Lyainc/claude-kit/commit/b10759a008eaf3598765cd47280e98b22eb1609e))
* **vault-bridge:** add plan-doc autosync with 2-layer opt-in gate (W8) ([a6e2d35](https://github.com/Lyainc/claude-kit/commit/a6e2d35f3c40b15a7809d469c2001e6f5b14d49f))
* **vault-bridge:** add references, access_count, promotion_candidate to manifest (PR 4c) ([ddc1674](https://github.com/Lyainc/claude-kit/commit/ddc1674a5a902ea92d1fe5c59c657e20b6be755a))
* **vault-bridge:** add vault manifest generator for 97% token savings ([7553d17](https://github.com/Lyainc/claude-kit/commit/7553d17afdd115622d1a9b901e06d054c1edaac0))
* **vault-bridge:** add VAULT_BRIDGE_DUMP_PAYLOAD gate for W1 D5 preflight ([e122976](https://github.com/Lyainc/claude-kit/commit/e12297692247f7336e64d6f8bc6ae20862528136))
* **vault-bridge:** cap pre-access-guard systemMessage at N=1,5,10 (Q2.1) ([76dce8f](https://github.com/Lyainc/claude-kit/commit/76dce8f09d03138d3ba89a0226721ec756683c48))
* **vault-bridge:** CC 2.1.142 compat — terminalSequence bell + exec-form hooks ([b11d185](https://github.com/Lyainc/claude-kit/commit/b11d1853fa22b5edf65e2052a02567b60e36afee))
* **vault-bridge:** enforce Write Role Contract via pre-write-guard ([5025298](https://github.com/Lyainc/claude-kit/commit/50252989acd1635f26d8896e599d7701a9a0a872))
* **vault-bridge:** flip WRITE_CONTRACT default warn→enforce, bump to v1.10.0 ([40e1aaa](https://github.com/Lyainc/claude-kit/commit/40e1aaa4cdf9aff6e0526e9394c2d5d0cda802dd))
* **vault-bridge:** formalize write role + file naming convention ([102052c](https://github.com/Lyainc/claude-kit/commit/102052c0be74a3ac5180593249a673282626f265))
* **vault-bridge:** split snapshot_export/snapshot_import gate keys ([076104b](https://github.com/Lyainc/claude-kit/commit/076104bc682b3773af59ffdc366409b3268fed93))
* **vault-bridge:** status-transition aware commit message for /vault-commit ([d34fe2a](https://github.com/Lyainc/claude-kit/commit/d34fe2a426c4c804445d6e9deb4e503611d6fe38))
* **vault-bridge:** support userConfig.vault_path for portable vault location ([fa737d3](https://github.com/Lyainc/claude-kit/commit/fa737d3365033a4feddce7b5fc9b30f8b0c039f8))
* **vault-bridge:** W8 autosync_paths v1.1 + plan-doc-sync jq emit fix ([10457e2](https://github.com/Lyainc/claude-kit/commit/10457e292c76d26e7a4f1b528eafa34f013e5fed))
* work-rules minimal core — OMC-free, plugin-free rule enforcement ([#216](https://github.com/Lyainc/claude-kit/issues/216)) ([02ad24a](https://github.com/Lyainc/claude-kit/commit/02ad24ab6ca2afc8b12fc867943c63ef6e0d0587))
* **workflow-harness:** add handoff-plan skill — backlog chunking → goal-doc slice binding ([#171](https://github.com/Lyainc/claude-kit/issues/171)) ([246e79b](https://github.com/Lyainc/claude-kit/commit/246e79b6b51a6a92c96f37d836bfebfa75072c14))
* **workflow-harness:** add retro skill — E8 promotion + 3-branch output + dedup + budget (v0.2.0) ([5aa052f](https://github.com/Lyainc/claude-kit/commit/5aa052fd54070053d4fc7f97a5625c3a17b154d8))
* **workflow-harness:** add slice-router — 4-way slice router + D5 invariant enforcement ([#183](https://github.com/Lyainc/claude-kit/issues/183)) ([d28580b](https://github.com/Lyainc/claude-kit/commit/d28580b5b7230b412c5f51f74e61d44cfa26ea0f))
* **workflow-harness:** add v0.1.0 thin scaffold (layer ⑤ execution harness) ([e898006](https://github.com/Lyainc/claude-kit/commit/e898006280817f5a553f6a106509f1d9530e48af))
* **workflow-harness:** promote feature-full DELEGATE to structural workflow script ([#201](https://github.com/Lyainc/claude-kit/issues/201)) ([7d256bd](https://github.com/Lyainc/claude-kit/commit/7d256bdac92b4504c4036f49c296a9806d85f1fc))
* 마켓플레이스 매니페스트 누락과 필드 불일치(drift) 실패 상태 분리 및 CI/CD 문서화 ([8876695](https://github.com/Lyainc/claude-kit/commit/8876695de15873c59f10f91d5ec3b926583719c0))


### Bug Fixes

* address PR [#57](https://github.com/Lyainc/claude-kit/issues/57) review findings (review-bot R2) ([82cc36e](https://github.com/Lyainc/claude-kit/commit/82cc36e0489c4639b6900702bfd5d1215bf99e77))
* address PR [#57](https://github.com/Lyainc/claude-kit/issues/57) third-pass review findings ([23b0021](https://github.com/Lyainc/claude-kit/commit/23b00214925febe8976b1d01e7884d6c3a535c34))
* address PR [#60](https://github.com/Lyainc/claude-kit/issues/60) review feedback (8 of 11) ([037ce0e](https://github.com/Lyainc/claude-kit/commit/037ce0e0b1bd16c1afb5792d7332676c4e2cb4b1))
* address PR [#95](https://github.com/Lyainc/claude-kit/issues/95) review feedback ([c824c7f](https://github.com/Lyainc/claude-kit/commit/c824c7f9cbd4d72e6e5cf238826425a6f51704f5))
* address PR [#95](https://github.com/Lyainc/claude-kit/issues/95) second-round review ([aa426b4](https://github.com/Lyainc/claude-kit/commit/aa426b495533bd78125e801bfcf9beb94784bfa5))
* address PR [#95](https://github.com/Lyainc/claude-kit/issues/95) third-round review ([953c719](https://github.com/Lyainc/claude-kit/commit/953c719f64a90640a0526ab0afb0155c140e4796))
* align audit schema with real OVM field names + minor review polish ([8591ad2](https://github.com/Lyainc/claude-kit/commit/8591ad2b04c44f28ef0c62ee25383847c2d18eca))
* **audit-p0:** PR-A — description compression, dead-code removal, count sync ([ad91e1b](https://github.com/Lyainc/claude-kit/commit/ad91e1b45e853de45cf70deca119e01c1ab75f2a))
* **audit-p0:** PR-B — thinking-tools routing description patches ([62c2cb4](https://github.com/Lyainc/claude-kit/commit/62c2cb4ae2af5d8e9c0d20f5d97fef772b6e8704))
* **audit-p0:** ship 2026-05-10 critique P0 actions ([0cd5c87](https://github.com/Lyainc/claude-kit/commit/0cd5c875b56d0d3e1fe32f8268c1303af3ca3ecd))
* **audit:** vault-searcher tier routing + skill audit follow-ups ([04776d6](https://github.com/Lyainc/claude-kit/commit/04776d65a278ee7b37210eabb7917b29d6e956b6))
* **diverse-sampling:** remove dead Opus/Sonnet model-capability branching ([e3b64bb](https://github.com/Lyainc/claude-kit/commit/e3b64bb26386a70b1776d4a37fbbf9e40bc1b5e1))
* **handoff:** replace && conditional with if/then/fi to prevent exit 1 on PROJECT_NAME set ([481cbcd](https://github.com/Lyainc/claude-kit/commit/481cbcd7dd505c93da96b04ce88e57d5994380e4))
* **obsidian-vault-manager:** align error-taxonomy with canonical W7 schema ([0528cff](https://github.com/Lyainc/claude-kit/commit/0528cff872eedfcf7085c1f9d34df371aaf189ba))
* **obsidian-vault-manager:** bump 0.9.3 → 0.9.4 for absorbs detection support ([8158dce](https://github.com/Lyainc/claude-kit/commit/8158dcea881379e76195a622b6148815e40bcbff))
* **obsidian-vault-manager:** case-insensitive paths + absorbs E6/E7 coverage ([3bc4ee3](https://github.com/Lyainc/claude-kit/commit/3bc4ee3072f30247acf8550332e7cb7cf2f0b7db))
* **obsidian-vault-manager:** correct vault-knowledge-manager color purple → magenta ([3b71a18](https://github.com/Lyainc/claude-kit/commit/3b71a18d3918cc5e50a86ced8359d7c942291e68))
* **obsidian-vault-manager:** E5 case-insensitive lookup + log message accuracy ([9b66be9](https://github.com/Lyainc/claude-kit/commit/9b66be90ce1d80dbbd1b9c9069d58f2f54106da2))
* **obsidian-vault-manager:** tighten path-validation prefix and gen-fixture mode reuse ([accf6ee](https://github.com/Lyainc/claude-kit/commit/accf6ee2eca2a8a205d739aec595b391f2dbe095))
* **obsidian-vault-manager:** vault-audit schema drift + E8/E9 coverage ([de2425e](https://github.com/Lyainc/claude-kit/commit/de2425eb3c21dd412751a20d2b19a1ed6efd477b))
* **ovm/audit:** address PR [#86](https://github.com/Lyainc/claude-kit/issues/86) review feedback ([ce54442](https://github.com/Lyainc/claude-kit/commit/ce544422cd23b59503bc603ca7694068fccc6b2e))
* **ovm/audit:** address PR [#91](https://github.com/Lyainc/claude-kit/issues/91) review feedback ([a41447b](https://github.com/Lyainc/claude-kit/commit/a41447be317f8ed827461365387e9039f23feba4))
* **ovm/audit:** catch UnicodeDecodeError in read_manifest_summary() ([7794237](https://github.com/Lyainc/claude-kit/commit/77942376e340f40f729d4a12ae8328cd3f2d29b9))
* **ovm/audit:** honor VAULT_ROOT in E9 scan + E9b clarity comment ([#162](https://github.com/Lyainc/claude-kit/issues/162) review) ([1a61f0d](https://github.com/Lyainc/claude-kit/commit/1a61f0dcaa74739f871b014bd3d188414bcdd97f))
* **ovm/audit:** resolve infer-tags paths against VAULT_ROOT + batch regression test ([#152](https://github.com/Lyainc/claude-kit/issues/152) review) ([1ff1b2a](https://github.com/Lyainc/claude-kit/commit/1ff1b2a3ba8ef1601993830781a8c0f10acbb11a))
* **ovm/audit:** skip phantom E8 entries from stale manifest ([850c032](https://github.com/Lyainc/claude-kit/commit/850c032b7197c8e904c204b7575b60e3861f2187))
* **ovm+vault-bridge:** address PR [#84](https://github.com/Lyainc/claude-kit/issues/84)/[#85](https://github.com/Lyainc/claude-kit/issues/85) review feedback ([5fb9710](https://github.com/Lyainc/claude-kit/commit/5fb9710d8ec9c136596cbb7fef0839f2a00e43b8))
* **ovm+vault-bridge:** address PR [#87](https://github.com/Lyainc/claude-kit/issues/87) review feedback ([4ed96f3](https://github.com/Lyainc/claude-kit/commit/4ed96f3908b4d2524381bdd6bdc771cad5414e2d))
* **ovm+vault-bridge:** apply missed PR [#85](https://github.com/Lyainc/claude-kit/issues/85) review fixes ([794dfaa](https://github.com/Lyainc/claude-kit/commit/794dfaa7a43c6851a8d4afbd3c3c8f6bc93118ee))
* **ovm:** address PR [#84](https://github.com/Lyainc/claude-kit/issues/84) review feedback ([624f613](https://github.com/Lyainc/claude-kit/commit/624f613c3593e624520686cdf9510711099be29e))
* **ovm:** address PR [#85](https://github.com/Lyainc/claude-kit/issues/85) review feedback round 2 ([6c0e364](https://github.com/Lyainc/claude-kit/commit/6c0e3641947c84afb643a1e5d32bb6ac956bd8fd))
* **ovm:** unify audit skill identifier (vault-audit → audit) ([d7d318e](https://github.com/Lyainc/claude-kit/commit/d7d318e79b14c194bfb67fa98bc0e8853561f653))
* **pr4d:** address PR [#90](https://github.com/Lyainc/claude-kit/issues/90) review feedback ([16508a6](https://github.com/Lyainc/claude-kit/commit/16508a61679f706dedfdf28d7904b7ff568167b9))
* **telemetry:** sanitize dump path + dynamic latency column width ([#161](https://github.com/Lyainc/claude-kit/issues/161) review) ([48a5bdc](https://github.com/Lyainc/claude-kit/commit/48a5bdcac1e0cd63d79447a343797e59b571a833))
* **thinking-tools:** address PR [#82](https://github.com/Lyainc/claude-kit/issues/82) review feedback ([7912f15](https://github.com/Lyainc/claude-kit/commit/7912f150eb9f609b29e3b842359a3a37520c5f0d))
* **thinking-tools:** address PR [#82](https://github.com/Lyainc/claude-kit/issues/82) second review (sidecar load + sample math + vault path) ([1102f50](https://github.com/Lyainc/claude-kit/commit/1102f50ff488024cb468dab71f44e5addaaa80cb))
* **thinking-tools:** restore critical triggers and routing boundaries lost in over-slimming ([748cafb](https://github.com/Lyainc/claude-kit/commit/748cafbe104fc0f0559a254b80e25290da73333d))
* **thought-chain:** extend --auto-vault plan fallback to include snapshot_export=false ([25b6a7f](https://github.com/Lyainc/claude-kit/commit/25b6a7fe1c0abb59da5e149d4363145ba5643feb))
* **thought-chain:** remove residual --skip/--start flag refs in fallback contracts table ([a1562a1](https://github.com/Lyainc/claude-kit/commit/a1562a15c9e5d08e0ada6e0cc1d1dc549eddbfba))
* **vault-bridge,ovm:** address PR [#89](https://github.com/Lyainc/claude-kit/issues/89) follow-up review ([bb7f0ec](https://github.com/Lyainc/claude-kit/commit/bb7f0ecffe3377478be990edc99cd938391822c2))
* **vault-bridge,ovm:** address PR [#89](https://github.com/Lyainc/claude-kit/issues/89) review feedback ([fc65f1e](https://github.com/Lyainc/claude-kit/commit/fc65f1ec70a496f30ac99fa334f18200b454ed20))
* **vault-bridge/handoff:** accept language-tagged code fences in resume parser ([8759c0c](https://github.com/Lyainc/claude-kit/commit/8759c0cb4e0ac22485ceed4310188d24101c6056))
* **vault-bridge:** add missing title field to userConfig.vault_path ([3ab4020](https://github.com/Lyainc/claude-kit/commit/3ab40203643d53f5144ae71a84dfb7f5fa533cab))
* **vault-bridge:** address PR [#64](https://github.com/Lyainc/claude-kit/issues/64) review — gate scope, env suppression, L2 test ([c31e77a](https://github.com/Lyainc/claude-kit/commit/c31e77a9d559e3620b1e2ee368b349af24f4a740))
* **vault-bridge:** address PR [#65](https://github.com/Lyainc/claude-kit/issues/65) review — flag validation, mtime flakiness ([fa8d051](https://github.com/Lyainc/claude-kit/commit/fa8d051c82aad0c73510f9ce77e0beb30c3e4f37))
* **vault-bridge:** address PR [#66](https://github.com/Lyainc/claude-kit/issues/66)/[#68](https://github.com/Lyainc/claude-kit/issues/68) review — L2 example key, count placeholder, re-run carve-out ([7d50be3](https://github.com/Lyainc/claude-kit/commit/7d50be30f6064fe961437fad6c906dfd33eb920e))
* **vault-bridge:** address PR [#83](https://github.com/Lyainc/claude-kit/issues/83) review feedback ([3804fb7](https://github.com/Lyainc/claude-kit/commit/3804fb7df74b236c63a1c5674f3a61e52b2fe35d))
* **vault-bridge:** address PR [#92](https://github.com/Lyainc/claude-kit/issues/92) review feedback ([3b95452](https://github.com/Lyainc/claude-kit/commit/3b95452a30bfd641be0f398f0ec7e837877a59ba))
* **vault-bridge:** address PR [#92](https://github.com/Lyainc/claude-kit/issues/92) second-round review ([a1488d0](https://github.com/Lyainc/claude-kit/commit/a1488d05ddef5b0fc61d116a6fc2f467c70eac37))
* **vault-bridge:** CC 2.1.143 compat — revert to command-string hooks schema ([c284ef0](https://github.com/Lyainc/claude-kit/commit/c284ef03c0e40912304b739779862409cb42cf21))
* **vault-bridge:** clarify recipe and vault-link wording ([4d6ea59](https://github.com/Lyainc/claude-kit/commit/4d6ea59c08afb758ae321ca88ca6b4579ac9f2f1))
* **vault-bridge:** code-review bundle — 1 CRITICAL + 4 HIGH + 4 MEDIUM ([9c8190b](https://github.com/Lyainc/claude-kit/commit/9c8190b062d7cc5fe6366c3bc03a9372c1b078b3))
* **vault-bridge:** code-review bundle 2 + parser parity ([8cc68e7](https://github.com/Lyainc/claude-kit/commit/8cc68e74548fa78aa78b70967ee5ecce437c342c))
* **vault-bridge:** correct decision(update) label in vault-commit-message ([3207825](https://github.com/Lyainc/claude-kit/commit/3207825277c41b0f9bd484c4e1bf18bfd1077018))
* **vault-bridge:** exempt vault-searcher from pre-access-guard self-warning ([159f98a](https://github.com/Lyainc/claude-kit/commit/159f98a1090150ee7505bbbde32ccdcdae6c454c))
* **vault-bridge:** extract resolve-resume-path helper, prevent vault routing in /handoff ([f8ecaad](https://github.com/Lyainc/claude-kit/commit/f8ecaad7fdfa8b79683eb11aaca1e81525efb4b5))
* **vault-bridge:** harden pre-access-guard systemMessage to policy directive ([718c5b6](https://github.com/Lyainc/claude-kit/commit/718c5b616ee9477fca52e43e10c6ef4f41a22990))
* **vault-bridge:** harden stop-check.sh + add regression test ([9539538](https://github.com/Lyainc/claude-kit/commit/95395388b9fb0b6c51a506067523dd80c19c8a75))
* **vault-bridge:** harden stop-check.sh + add regression test ([a17768b](https://github.com/Lyainc/claude-kit/commit/a17768bf4470c5410fb5785cb3b3a607844067ec))
* **vault-bridge:** make resolve-resume-path.sh executable ([b0ac5c1](https://github.com/Lyainc/claude-kit/commit/b0ac5c15f130ede6f6d5c752b98bb05824a2d8c2))
* **vault-bridge:** manifest summary skips H1 echo, captures callout body ([3da9f6e](https://github.com/Lyainc/claude-kit/commit/3da9f6ee2907a4a6c287091199cf6bfcd3f16c7c))
* **vault-bridge:** narrow /save-plan-doc discussions capture to depth-3 only ([9199bbd](https://github.com/Lyainc/claude-kit/commit/9199bbda8c0a336d2ae9ef4742f9ad3921422936))
* **vault-bridge:** PR [#60](https://github.com/Lyainc/claude-kit/issues/60) round 2 review — 3 of 8 ([77286b0](https://github.com/Lyainc/claude-kit/commit/77286b0b079a62feefd7bf13829d653fe6ec21bc))
* **vault-bridge:** PR [#60](https://github.com/Lyainc/claude-kit/issues/60) round 3 review — 6 of 10 ([2634cf8](https://github.com/Lyainc/claude-kit/commit/2634cf8da619050b4ab3388f432fce779f548367))
* **vault-bridge:** prevent spurious resume backup warning after handoff injection ([57ced53](https://github.com/Lyainc/claude-kit/commit/57ced53f07dfa98583f7ddfac7460a4e8236fe41))
* **vault-bridge:** protect resume.md from accidental session loss ([5aff498](https://github.com/Lyainc/claude-kit/commit/5aff4984fc3938284103e003964dbfd8a76cdb44))
* **vault-bridge:** quote CLAUDE_PLUGIN_ROOT in hook command paths ([e83b4c7](https://github.com/Lyainc/claude-kit/commit/e83b4c71431a90fd37a59a592ac541a4e55fed28))
* **vault-bridge:** scope SUMMARY/UNRESOLVED excludes to discussions path + add tests ([9ea1b8e](https://github.com/Lyainc/claude-kit/commit/9ea1b8e31b07d335045b7ff5cdf841bd670967a4))
* **vault-bridge:** SessionEnd safety-net writes to inbox/ ([4cc4833](https://github.com/Lyainc/claude-kit/commit/4cc4833b894476b52928361b74bfb852d88b251f))
* **vault-bridge:** surface plan-doc syncer failures + adversarial test cases ([7df2be8](https://github.com/Lyainc/claude-kit/commit/7df2be8451372fcc30e4c5d4bba53b8c286af17d))
* **vault-bridge:** surface resume.md/prev.md content via top-level additionalContext ([e7d6191](https://github.com/Lyainc/claude-kit/commit/e7d6191153dc0338ebfe5817b54aed1a9988c7e2))
* **vault-bridge:** sync marketplace.json version + strengthen test assertions ([c8ec995](https://github.com/Lyainc/claude-kit/commit/c8ec995e5b1d77848f49aeb096d02e02ceb494f5))
* **vault-bridge:** use CLAUDE_PLUGIN_ROOT for vault-commit-message.py path ([0ddb8a6](https://github.com/Lyainc/claude-kit/commit/0ddb8a659f8042b385b7a116fe62973d53dc4e82))
* **workflow-harness:** address PR [#184](https://github.com/Lyainc/claude-kit/issues/184) review nits N1/N3 ([#187](https://github.com/Lyainc/claude-kit/issues/187)) ([8f4178f](https://github.com/Lyainc/claude-kit/commit/8f4178f725ebf64fa8b238e5fe73e8c085f3220d))
* **workflow-harness:** address PR [#188](https://github.com/Lyainc/claude-kit/issues/188) review nits — plan aliasing + INV-5 commented-import FP ([#189](https://github.com/Lyainc/claude-kit/issues/189)) ([dec94b4](https://github.com/Lyainc/claude-kit/commit/dec94b43c4ea75f86252745ee2d723bbb2a94ccd))
* **workflow-harness:** correct test-invariant case count 34→35 ([#189](https://github.com/Lyainc/claude-kit/issues/189)) ([8600110](https://github.com/Lyainc/claude-kit/commit/8600110853406b8c65fafe037e13ade3a2bff796))
* **workflow-harness:** meta export must be the first statement in feature-full.js ([#201](https://github.com/Lyainc/claude-kit/issues/201)) ([103d0ad](https://github.com/Lyainc/claude-kit/commit/103d0ad894ec732291a8ed1b4d651dfe367bd6d2))
* **workflow-harness:** normalize JSON-string args in feature-full.js ([#201](https://github.com/Lyainc/claude-kit/issues/201)) ([387df0b](https://github.com/Lyainc/claude-kit/commit/387df0b9aa14ff661ed1fa51b222b9d839e0154b))
* **workflow-harness:** null-return guards on both agent() stages + goal_id fallback ([#206](https://github.com/Lyainc/claude-kit/issues/206)) ([7d08625](https://github.com/Lyainc/claude-kit/commit/7d08625ae0c792811024be35f4b08e1c86aa8be0))
* **workflow-harness:** reject empty `issues: []` in INV-4, scoped so `depends_on: []` stays legal ([#190](https://github.com/Lyainc/claude-kit/issues/190)) ([80c1875](https://github.com/Lyainc/claude-kit/commit/80c187523ad7c1476ab8a57e8b1c36eb441aa349))
* **workflow-harness:** restructure feature-full.js to top-level workflow body ([#201](https://github.com/Lyainc/claude-kit/issues/201)) ([298836e](https://github.com/Lyainc/claude-kit/commit/298836e557ad4b6f96ffc64261b852a945fa8c2a))
* **workflow-harness:** retro telemetry — emit duration_ms + CLAUDE_PROJECT_ROOT anchor ([#182](https://github.com/Lyainc/claude-kit/issues/182)) ([3a888e9](https://github.com/Lyainc/claude-kit/commit/3a888e9f7f0bb660da7911deea27ecaf585d1330))


### Reverts

* **ovm:** restore audit/note SKILL.md descriptions ([6303025](https://github.com/Lyainc/claude-kit/commit/6303025fde8fd286e7f89b558d285e2c21a4ce4d))


### Code Refactoring

* **thinking-tools:** remove user-facing flags, suppress numeric scores ([32cefcf](https://github.com/Lyainc/claude-kit/commit/32cefcfc98131296ff914c783fccc3b4196ba988))
* **vault-bridge:** remove auto_capture deprecation alias (E3) ([69bcf1c](https://github.com/Lyainc/claude-kit/commit/69bcf1c8734eea2700be29425d5b39ce52c327a1))

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
