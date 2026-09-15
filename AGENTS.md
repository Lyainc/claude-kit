# claude-kit

This repository packages four independent plugins: `thinking-tools`,
`obsidian-vault-manager`, `vault-bridge`, and `feedback-loop`.

- Keep user-facing output in Korean; keep skill and agent instruction bodies in English.
- Reuse existing skills and scripts; do not add a dependency or a compatibility layer unless the current layout cannot express the need.
- Plugin metadata is the source of truth; keep the corresponding marketplace metadata in sync. Do not bump versions outside the lockstep release workflow.
- Use Conventional Commit messages in English and write PR descriptions in Korean. Rebase-merge by default.
- Run only the relevant commands from `docs/VALIDATION.md` for the files changed.
- Treat Claude-only hooks, agents, and tool names as optional integrations: document or omit them for Codex unless an equivalent is verified.
- Skill/agent shell calls that reference `${CLAUDE_PLUGIN_ROOT}` need no change: Codex sets `CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` itself for compatibility with existing plugin hooks, alongside its own `PLUGIN_ROOT`/`PLUGIN_DATA` (source: [developers.openai.com/codex/plugins/build](https://developers.openai.com/codex/plugins/build)).
- `plugin.json` `userConfig` (e.g. vault-bridge's `vault_path`) has no verified Codex equivalent — treat it as Claude-only. On Codex, set the plugin's documented override env var directly instead (vault-bridge: `VAULT_BRIDGE_VAULT_ROOT`).
