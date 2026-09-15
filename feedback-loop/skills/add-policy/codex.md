# Codex deterministic hook branch

Use only for add-policy's hook site. The classification, source, conflict, necessity, approval,
and user-authored-skill gates remain in SKILL.md; this is native registration detail only.

Codex CLI 0.154 supports command hooks. A blocking PreToolUse guard can return
`hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny",
permissionDecisionReason: "..."}` or exit 2 with stderr. A recovery PostToolUse hook can exit 2
with stderr; the completed tool's effects cannot be undone. Do not translate PreToolUse `ask`
into `allow`: `ask` is unsupported, so leave the runtime's normal approval flow intact and
report the gap if the requested rule requires exactly that behavior.

1. Resolve `$CODEX_ROOT/hooks.json` and the guard script's chosen path. Read existing JSON;
   malformed or unreadable content stops the write. Scan matching registrations for duplicate
   and conflicting enforcement. Preserve every unrelated group/key/script.
2. Include the exact script and event/matcher registration in the existing single placement
   confirmation. Use native tool names: shell matches `Bash`; edits match `apply_patch`, `Edit`,
   or `Write` but payload uses `tool_input.command`. Do not invent `tool_input.file_path` for
   apply_patch. Other local/MCP tools need their observed argument schema.
3. After approval, write the script and merge the selected handler into the existing `hooks`
   object. Command handlers use `type: command`, `command`, and an appropriate timeout.
4. Validate JSON, script syntax, and a direct safe payload fixture for both matching/nonmatching
   cases. Report **written, not activated** until the definition is reviewed in native `/hooks`.
   Changed definitions require trust again. Never bypass trust in user configuration.

For a disposable, already inspected test fixture, native CLI
`--dangerously-bypass-hook-trust` can run the fixture only for that invocation; this does not
bypass tool permissions or persist trust. A fixture run must observe deny before side effects,
and recovery feedback after a safe command. Plain script tests do not prove native execution.

Source: [official Codex hooks documentation](https://learn.chatgpt.com/docs/hooks).
