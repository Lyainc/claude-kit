# Codex portability contract

This contract applies only when a bundled skill runs in Codex. It overrides a source skill's
Claude-only mechanics while preserving its decision rules and safety gates.

1. The current user request and conversation are the input. `$ARGUMENTS` is never read.
2. Resolve bundled files relative to the installed plugin directory that contains this skill.
   Replace `${CLAUDE_PLUGIN_ROOT}` in source commands with that resolved directory.
3. Ask a normal user-facing question when the source says `AskUserQuestion`; keep its stated
   approval gate and do not assume an answer.
4. Use only tools available in the current Codex runtime. For `Agent` or `Skill`, do the work in
   the current context or delegate only through an available Codex subagent facility. Never name a
   Claude agent type, model, or workflow.
5. For `WebFetch`, use an available Codex web capability. If none is available, state that the
   fact is unverified and continue only when the source permits it.
6. Claude hooks and hook payloads do not run. Collect their data directly when cheap; otherwise
   label it unavailable rather than empty.
7. Do not emit Claude slash-command, hook, model-routing, or tool-call syntax. Render the source
   skill's user-facing result directly in the requested language.
