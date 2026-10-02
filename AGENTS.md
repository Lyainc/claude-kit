# claude-kit contributor instructions

These instructions govern development of this repository, not plugin behavior in consuming
projects. A plugin's skill/agent description owns discovery; its body owns the procedure.
Personal machine policy is optional and must never become a runtime/build dependency.

- Use Korean for user-facing output and PR descriptions. Skill/agent bodies, metadata keys,
  and maintainer instructions are English; preserve the requested artifact language and
  Korean examples. README prose defaults to English; reference docs, examples, and vault-content
  templates remain Korean. User-facing trigger examples may be Korean.
- Use Conventional Commits in English. Keep commits atomic and delegates free of Git side
  effects; `rules/RULES.md` owns the repository's execution contracts. Branch defaults are
  `feat/`, `fix/`, `docs/`, `refactor/`, unless the caller specifies another convention.
- Rebase-merge by default. Never force-push main to repair a merge strategy. For stacked PRs,
  WIP, or a merge-method exception, read `docs/contributor-authoring.md` → PR Workflow.
- Reuse skills/scripts. Add dependencies or compatibility layers only for a demonstrated gap.
  The architectural boundary and dependency direction live in `docs/design/claude-kit-boundary.md`;
  consult it when changing plugin ownership or orchestration.
- Each requested output has one skill owner; choose by object, operation, and side effects,
  not a shared trigger word. Compose stages only when the request needs them. See
  `docs/skill-boundaries.md` when changing discovery or ownership; edit the actual skill
  description/body, not just this documentation. Ordinary edits need no specialist workflow.
- Before adding/changing skills, agents, hooks, or manifests, read the relevant sections of
  `docs/contributor-authoring.md`. It preserves tool declarations, frontmatter, manifest sync,
  and catalog-registration requirements. Detailed history stays outside startup instructions.
- Claude `.claude-plugin/plugin.json` owns Claude metadata; root `plugin.json` owns portable
  Codex metadata. Keep names/versions in lockstep, but do not bump versions manually. Follow
  `RELEASING.md`; run only the checks relevant to changed behavior from `docs/VALIDATION.md`.
- Claude-only tools/hooks/settings need an explicit runtime adapter; do not assume Codex has
  equivalent enforcement. Codex supplies `CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` compatibility
  variables. No equivalent to Claude `plugin.json userConfig` is verified: use a plugin's
  documented environment override (vault-bridge: `VAULT_BRIDGE_VAULT_ROOT`) on Codex.
