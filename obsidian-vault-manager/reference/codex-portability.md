# Codex portability contract

This contract applies only when a bundled skill runs in Codex. It overrides a source skill's
Claude-only mechanics while preserving its decision rules and safety gates.

1. The current user request and conversation are the input. `$ARGUMENTS` is never read.
2. Resolve bundled files relative to the installed plugin directory that contains this skill.
   Codex supplies `CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` alongside `PLUGIN_ROOT`/`PLUGIN_DATA`;
   retain existing shell variables, using the resolved directory for direct script execution.
3. For every user interview, clarification or confirmation (including `AskUserQuestion`), use
   the available Codex native user-input tool before plain chat. Follow its actual schema,
   current-mode and purpose restrictions; never invent a tool or switch modes to enable it.
   - Prefer `request_user_input_async` when available and permitted. A successful submission
     only queues the question: keep dependent interview steps, scoring and approval gates
     pending until the actual user reply arrives; continue only independent work meanwhile.
   - Otherwise use `request_user_input` only when available and permitted for this question
     in the current mode. A listed tool may still be restricted (for example to Plan mode,
     optional clarification, or non-approval questions); its runtime contract wins.
   - Preserve the question's meaning and choices within the tool's limits. If multi-select
     is unsupported, use separate short choices or a free-text question accepting item IDs;
     never silently turn independent keep/dismiss choices into a single-choice decision.
   - Reuse explicit prior answers and approvals. Tool acceptance, preselected options,
     missing/empty replies and elapsed time are not user answers or approval. Preserve each
     skill's required-answer and approval gates. Only a clarification the runtime lets you skip
     may be skipped; a skip is never an answer or approval and never advances a gate.
   - If no native tool is usable, ask in a normal user turn and wait for the actual reply.
     Keep required unanswered questions pending; never claim the interview completed.
4. Use only tools available in the current Codex runtime. For `Agent` or `Skill`, do the work in
   the current context or delegate only through an available Codex subagent facility. Never name a
   Claude agent type, model, or workflow.
5. For `WebFetch`, use an available Codex web capability. If none is available, state that the
   fact is unverified and continue only when the source permits it.
6. Do not assume Claude hook registration or payload coverage. Codex supports native lifecycle
   hooks, but non-managed definitions require trust and not every Claude tool/event is equivalent.
   Reuse supplied data or run existing scripts directly when useful; otherwise label it unavailable
   rather than empty. Read runtime-specific references only for the branch being executed.
7. Do not emit Claude slash-command, hook, model-routing, or tool-call syntax. Render the source
   skill's user-facing result directly in the requested language.
8. When a skill tells the user how to set the vault root, name only the `VAULT_BRIDGE_VAULT_ROOT`
   environment variable. Drop the plugin setting `vault_path`/`VAULT_BRIDGE_VAULT_PATH`: it is
   Claude `userConfig`, which has no verified Codex equivalent.
