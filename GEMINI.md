# Gemini CLI Instructions for claude-kit

This repository (`claude-kit`) is a multi-agent environment actively developed using **Claude Code**, **Codex (OMX)**, and **Gemini CLI**. To ensure seamless collaboration and zero conflicts across all AI agents, Gemini CLI MUST strictly adhere to the following project mandates.

## Core Directives

1. **Single Source of Truth:** The primary project architecture, language policies, file naming conventions (especially for vault files), and git conventions are defined in `CLAUDE.md` and `AGENTS.md`. Treat the rules defined in those files as your own foundational instructions.
2. **Read Before Act:** If you are asked to create a new skill, agent, or plugin, ALWAYS review `CLAUDE.md` first to ensure you follow the exact marketplace structure, validation steps, and directory layouts required by the project.
3. **Language Policy Parity:** 
   - Write skill/agent instruction bodies (`SKILL.md`, `agents/*.md`) in **English** for LLM parsing.
   - User-facing output (e.g., within skill execution, reference docs) MUST be in **Korean**.
   - Pull Request descriptions MUST be in **Korean**.
4. **Git & Commits:** Adhere to the established Git conventions (branch prefixes: `feature/`, `fix/`, `docs/`, `refactor/`). For commit messages, follow the **Lore Commit Protocol** defined in `AGENTS.md` (or standard Conventional Commits if acting purely as a Claude Code contributor).
5. **No Clutter:** Do not generate Gemini-specific workflow files or `.gemini/` state files that conflict with or duplicate the existing `.claude/` or `.codex/` states. Keep your footprint limited to the standard workspace files unless explicitly requested.

## Boundaries and Domains

- `thinking-tools/`: Logic and reasoning skills (e.g., `diverse-sampling`, `expert-panel`).
- `obsidian-vault-manager/`: Obsidian vault knowledge-management and organization skills (e.g., `capture`, `note`, `project`, `archive`, `vault-audit`).
- `vault-bridge/`: Obsidian vault I/O, search, session-notes, and lifecycle hooks.

When taking on tasks, align your tool choices and structural modifications with these established cross-plugin boundaries.

## Skill Emulation (Gemini CLI Workflow)

Since Gemini CLI does not natively load Claude Code plugins or trigger lifecycle hooks automatically, you MUST emulate this behavior when fulfilling user requests:

1. **Skill Execution:** When the user asks you to perform a task that maps to an existing skill (e.g., "Run the capture skill", "Create a new project note", "Archive the project"), you MUST first find and read the corresponding `SKILL.md` file (e.g., `obsidian-vault-manager/skills/capture/SKILL.md`).
2. **Follow Procedures Strictly:** Treat the `Procedure` and `Rules` sections inside the `SKILL.md` file as explicit, mandatory instructions. Follow the steps sequentially, using `run_shell_command`, `write_file`, or `replace` to execute the logic exactly as the skill describes.
3. **Use Shell Primitives & CLIs:** If a skill definition references project-local shell scripts (like `scripts/ovm-primitives.sh`) or specifies CLI commands (like `obsidian property:set` or `defuddle parse`), execute them using the `run_shell_command` tool exactly as instructed in the skill or reference documents.
4. **Hooks Constraint:** Gemini CLI will not automatically trigger `Stop` or `SessionEnd` hooks. Do not attempt to run these lifecycle scripts unless explicitly instructed by the user.