---
description: Capture this session's essentials as raw ore in the vault inbox (type:capture)
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

# /save-session

Session-scoped capture door — writes `type:capture` raw ore to `~/vault/inbox/`, the same artifact shape as obsidian-vault-manager's `/capture` (`docs/design/output-adapter-contract.md` §2 row #5). No session-note authoring, no mode routing: repurposed per `docs/design/claude-kit-boundary.md` §2 (D1 — overturns the prior #304 "session note survives independently" conclusion).

**User language: Korean.** All user-facing output MUST be in Korean.

1. Kill switch: `echo "${VAULT_BRIDGE_DISABLE:-0}"` — if `1`, output and stop: "vault-bridge가 비활성화되어 있어요 (`VAULT_BRIDGE_DISABLE=1`)."
2. Summarize this session's essentials (what happened, key decisions, files touched) in 3-5 lines.
3. Resolve `~/vault/inbox/` (`mkdir -p` if missing). Filename: `capture-YYYY-MM-DD-{slug}.md` (`{slug}`: 2-4 kebab-case words from the session topic). On collision, try `-v2`, `-v3`, …
4. Frontmatter:
   ```yaml
   ---
   created: YYYY-MM-DD
   tags: [capture, session]
   type: capture
   ---
   ```
5. Write the summary as the body. Save immediately, no confirmation — mirrors `/capture`'s "save immediately" core behavior.
6. Output only: `저장 완료: {save_dir}/{filename}` followed by `vault에 미커밋 변경이 생겼어요. /vault-commit으로 커밋할 수 있어요.`
