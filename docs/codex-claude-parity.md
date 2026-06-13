# Codex/OMX parity for Claude Code project surfaces

This document tracks the migration path for running `claude-kit` from Codex/OMX while preserving the contributor and plugin-development behavior expected by Claude Code.

## Goal

Create **operational parity**, not byte-for-byte identity. Claude Code and Codex differ in native plugin schema, slash-command rendering, tool names, hook event timing, model families, and permission semantics. A surface is considered migrated when Codex/OMX has one of:

- an active equivalent instruction,
- a native skill/agent/plugin wrapper,
- a deterministic command fallback, or
- an explicit documented limitation.

## Current parity matrix

| Claude Code surface | Purpose | Codex/OMX equivalent | Status | Verification |
| --- | --- | --- | --- | --- |
| Root `CLAUDE.md` | Contributor guidance for this marketplace repo | Migrated into `AGENTS.md` under “Project guidance migrated from root `CLAUDE.md`” | Active | Read `AGENTS.md`; run project validation commands below |
| `.claude/CLAUDE.md` | OMC runtime contract for Claude Code | Root `AGENTS.md` OMX runtime contract and `.codex/skills/*` | Active equivalent | `omx doctor`; inspect `.codex/config.toml` and `.codex/hooks.json` |
| `.claude/settings.json` | Claude plugin enablement | `.codex/config.toml` plugin entries | Active equivalent | Check `[plugins.*]` entries in `.codex/config.toml` |
| `.claude/settings.local.json` | Claude local permissions | Codex trust + sandbox/runtime policy; not copied directly | Documented limitation | Codex permissions are controlled by runtime config, not Claude allowlists |
| `.claude-plugin/marketplace.json` | Claude marketplace manifest | Still canonical marketplace manifest; Codex plugin cache/install reads equivalent local plugin surfaces | Shared source | `python3 -m json.tool .claude-plugin/marketplace.json` |
| `{plugin}/.claude-plugin/plugin.json` | Plugin metadata and Claude hook declarations | Still canonical plugin metadata; Codex wrappers must preserve metadata intent | Shared source | `python3 -m json.tool */.claude-plugin/plugin.json` |
| `{plugin}/skills/*/SKILL.md` | Claude Code skills | Codex plugin skills exposed with plugin prefixes or local `.codex/skills` wrappers | Active equivalent for installed plugins | Check skill list in Codex session; `find */skills -name SKILL.md` |
| `feedback-loop/skills/*` (`retro`) + `feedback-loop/.claude-plugin/plugin.json` | Layer ⑤ self-improvement (measure→review→keep — #217): E8 retro promotion + opt-in local telemetry. **Externally distributed.** | Codex drives the same retro loop; `retro` is exposed as a Codex plugin skill or documented fallback. Parity is behavioral (same measure→improve closure), not a literal skill-name copy | Active equivalent for installed plugin | `find feedback-loop/skills -name SKILL.md`; `python3 -m json.tool feedback-loop/.claude-plugin/plugin.json` |
| `dev-harness/skills/*` (`handoff-plan`, `slice-router`) + `workflows/feature-full.js` | Layer ⑤ dev-governance (goal-doc routing/validation INV-4, backlog→goal-doc handoff, feature-full DELEGATE carrier). **DEV-ONLY — not in marketplace.json, not externally distributed (#217).** | Not an external parity surface: governs claude-kit's own build loop. Codex contributors run the same dev tooling by plain script path | Dev-only (not distributed) | `python3 dev-harness/scripts/test/test-router.py` + `test-invariant.py` (local dev) |
| `{plugin}/agents/*.md` | Claude Code agents | Codex native agents/prompts when directly mapped; otherwise route to OMX roles | Partial equivalent | Inspect `.codex/agents` and skill descriptions |
| `vault-bridge/commands/*.md` | Claude slash commands | Codex skills or documented command fallbacks | Partial equivalent | Confirm available skills; keep shell fallbacks for missing command UI |
| `vault-bridge/hooks/*.sh` | Deterministic hook helpers | Codex hook bridge plus direct shell smoke tests | Partial equivalent | Run hook smoke tests before claiming parity |
| `.omc/state`, `.omc/plans`, `.omc/logs` | OMC runtime state | `.omx/state`, `.omx/plans`, `.omx/logs` | Active equivalent | Inspect `.omx/` during workflows |
| OMC `haiku` | Low-cost quick lookup lane | OMX `explore` / spark / low-effort lane | Equivalent class | Use `omx explore` for simple repo lookup |
| OMC `sonnet` | Standard implementation lane | OMX `executor`, `debugger`, `test-engineer` / medium-effort lane | Equivalent class | Role routing in `AGENTS.md` |
| OMC `opus` | Deep architecture/review lane | OMX `architect`, `critic`, `verifier` / high-effort lane | Equivalent class | Role routing in `AGENTS.md` |
| OMC `ralph`, `team`, `ultrawork`, `ralplan` | Workflow orchestration | OMX `$ralph`, `$team`, `$ultrawork`, `$ralplan` | Equivalent workflow names | Load corresponding `.codex/skills/*/SKILL.md` |

## Migrated root `CLAUDE.md` rules

The following root `CLAUDE.md` rules are now active for Codex/OMX through `AGENTS.md`:

- project overview and plugin boundaries,
- language policy for skill/agent instructions, metadata, READMEs, examples, and Korean user-facing output,
- marketplace layout and source-of-truth boundaries,
- skill/agent/plugin addition workflow,
- version/description/keyword synchronization between plugin manifests and marketplace manifest,
- vault file naming and frontmatter conventions,
- cross-plugin MECE boundaries,
- validation commands.

One rule is intentionally conditional rather than copied as-is:

- `CLAUDE.md` asks Claude Code contributors to use Conventional Commits. `AGENTS.md` has a stronger Codex/OMX Lore Commit Protocol. In Codex/OMX sessions, use Lore for agent-authored commits; when documenting Claude Code contributor expectations, preserve the Conventional Commit wording.

## Remaining non-identical areas

### Claude permissions

Claude `.claude/settings.local.json` allowlists are not portable to Codex. Codex uses trust level, sandbox, configured MCP/app tools, and runtime permissions. Do not copy the Claude allowlist as a security policy.

### Slash commands

Claude slash commands under `vault-bridge/commands/*.md` do not automatically become Codex slash commands. They need one of:

1. a Codex skill wrapper,
2. an OMX workflow mapping, or
3. a documented shell/manual fallback.

### Session lifecycle hooks

`vault-bridge` uses Claude `Stop`, `SessionStart`, `SessionEnd`, and `PreToolUse` hooks. Codex has hook support through `.codex/hooks.json`, but exact event payloads and timing may differ. Treat session-note and plan-doc sync parity as smoke-test required.

### Agent models

Claude model names (`haiku`, `sonnet`, `opus`) are not literal Codex model names. Use capability classes instead: fast lookup, standard implementation, and high-reasoning review/architecture.

## Standard validation

Run after changing marketplace manifests, plugin metadata, root guidance, or parity wrappers:

```bash
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null
python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null
find thinking-tools/skills -name "SKILL.md" | sort
find obsidian-vault-manager/skills -name "SKILL.md" | sort
find vault-bridge/commands vault-bridge/hooks -type f | sort
```

For vault-audit definition-of-done checks:

```bash
rm -rf /tmp/ovm-fixture-audit-recheck
OVM_FIXTURE_DIR=/tmp/ovm-fixture-audit-recheck \
  bash obsidian-vault-manager/scripts/test/gen-fixture.sh --with-audit-errors
python3 obsidian-vault-manager/scripts/test/audit-validate.py \
  /tmp/ovm-fixture-audit-recheck --dod
```

For Codex/OMX runtime checks:

```bash
omx doctor
```

## Migration stop condition

The migration is complete when:

1. `AGENTS.md` contains the root `CLAUDE.md` contributor rules that should affect Codex/OMX behavior.
2. This parity matrix has an entry for every Claude-specific project surface.
3. Manifest JSON validation passes.
4. Skill/command/hook presence checks pass.
5. Any unsupported Claude-only behavior is listed under “Remaining non-identical areas”.
