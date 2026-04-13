---
date: 2026-04-11
name: MECE Validation — New Skills, graphify, Plugin Boundaries, Draft Folder
participants:
  fixed: [Moderator, Optimistic Practitioner, Critical Practitioner]
  experts: [Knowledge Management Expert, Plugin Architecture Expert, Obsidian Ecosystem Expert]
topics: 4
consensus: 4
held: 0
---

# SUMMARY — MECE Validation (2026-04-11)

## Consensus Items

### 1. New Skills (vault-lint, ingest) MECE with Existing Skills — APPROVED

Both new skills occupy unique responsibility areas:

| Boundary | Definition |
|----------|-----------|
| capture vs ingest | capture = user short memo, instant save / ingest = external source deep analysis + connection proposals |
| ingest vs inbox-review | ingest = single source deep synthesis / inbox-review = batch file triage |
| ingest vs context | context = read-only query / ingest = comparative analysis + change proposal generation |
| vault-lint vs Obsidian built-in | vault-lint = LLM-based semantic inspection focus (structural checks are supplementary) |

**Action**: Add above boundaries to CLAUDE.md Cross-Plugin MECE Boundaries table.

### 2. graphify — No Absorption, Natural Compatibility

- graphify is an independent tool with a different tech stack (Python/NetworkX vs Claude Code plugin)
- graphify markdown output is naturally processable via OVM's existing pipeline (`00_Inbox/` → `/ingest` or `/inbox-review`)
- No dedicated integration skill needed at this time
- graphify MCP server can be optionally added to `.mcp.json` for graph query access

**Action**: None required now. Revisit if user demand emerges.

### 3. vault-reader → vault-bridge Rename — APPROVED

| Aspect | obsidian-vault-manager (Management) | vault-bridge (Access) |
|--------|-------------------------------------|----------------------|
| Core role | Modify vault structure and content | Connect vault with external context |
| Note creation | note, capture, ingest | handoff creation only (Inbox-scoped) |
| Classification | inbox-review, archive, vault-lint | None |
| Query | context (internal, deep, rich options) | search (external, lightweight, keyword) |
| Session mgmt | wrapup (session summary) | handoff (cross-session continuity) |
| MOC management | Exclusive owner | Read-only |

Rationale: "reader" conflicts with handoff write behavior. "bridge" accurately reflects access + cross-session bridging role. v0.1.0 makes this the lowest-cost moment for a rename.

**Action**: Rename vault-reader → vault-bridge (plugin.json, marketplace.json, CLAUDE.md, README, agent file).

### 4. `05_Draft/` Folder Addition — APPROVED

Lifecycle definition:
```
00_Inbox/ (fleeting) → 05_Draft/ (literature, in-progress) → 30_Notes/ (permanent)
```

Movement responsibilities:
- Inbox → Draft: `/ingest` skill
- Draft → Notes: user decision + `/inbox-review` extension
- Direct Inbox → Notes: still possible via `/inbox-review` (skip Draft for simple memos)

Frontmatter convention:
```yaml
status: draft
source: "{original URL or file path}"
```

vault-lint integration: `status: draft` + `created` > 14 days → "stale draft" warning.

**Action**: Update vault structure in vault-knowledge-manager agent, add `05_Draft/` handling to affected skills.

## Recommendations (Priority Order)

| Priority | Item | Scope |
|----------|------|-------|
| P0 | vault-reader → vault-bridge rename | vault-reader plugin, CLAUDE.md, marketplace.json |
| P1 | `/vault-lint` skill creation | obsidian-vault-manager |
| P1 | `05_Draft/` folder + vault structure update | vault-knowledge-manager agent |
| P2 | `/ingest` skill creation (with Draft integration) | obsidian-vault-manager |
| P3 | `/wrapup` extension (vault-log) | obsidian-vault-manager |
| P3 | CLAUDE.md MECE boundary table update | CLAUDE.md |

## Unresolved Issues

None — all 4 topics reached consensus.

## Minority Dissent Record

- **Topic 3 (rename)**: Critical Practitioner noted rename cost may exceed value. Counter: v0.1.0 minimizes migration burden. Accepted as conditional — migration guide required.
- **Topic 4 (draft)**: Critical Practitioner raised Inbox vs Draft boundary confusion risk. Counter: `/ingest` skill ownership of Inbox → Draft movement provides clear automation boundary. Accepted with frontmatter `status: draft` requirement for disambiguation.
