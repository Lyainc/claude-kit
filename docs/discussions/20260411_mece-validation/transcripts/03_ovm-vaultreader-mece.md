---
topic: 3
title: OVM vs vault-reader MECE + Rename
rounds: 1
result: consensus (weighted vote)
---

# TOPIC 3: OVM vs vault-reader MECE + Naming

**[Optimistic Practitioner]**:
Current boundary principle is "internal vs external": OVM for working inside vault, vault-reader for accessing vault from outside. This works conceptually but has friction points.

**[Critical Practitioner]**:
Three problems: (1) vault-searcher Mode 4 (handoff creation) writes files — contradicts "reader" name. (2) vault-searcher Mode 2 (domain context) and OVM context skill do nearly the same thing — "internal/external" distinction is not intuitive to users. (3) New skills (vault-lint, ingest) increase overlap with vault-reader's search capabilities.

**[Plugin Architecture Expert]**:
Proposed new separation criterion: "management vs access". OVM (management) = all operations that modify vault structure/content. vault-bridge (access) = operations connecting vault with external context. Under this criterion, handoff creation belongs in vault-bridge as "cross-session bridge". Rename "vault-reader" → "vault-bridge" to reflect this.

**[Knowledge Management Expert]**:
Librarian vs visitor metaphor: OVM = librarian (classifies, catalogs, processes new books). vault-reader = visitor (searches, borrows via handoff, returns). "bridge" better captures handoff inclusion than "reader".

**[Obsidian Ecosystem Expert]**:
Community naming precedents: Vault Access, Vault Gateway, Vault Connector, Vault Courier. "vault-bridge" is technically accurate. Note: rename is a breaking change requiring migration of plugin.json, marketplace.json, CLAUDE.md, README, and user installations.

**[Moderator]**: Weighted vote on rename:

| Panelist | Position | Confidence | Points |
|----------|----------|------------|--------|
| Optimistic Practitioner | For (vault-bridge) | Medium | 2 |
| Critical Practitioner | Against (cost > value) | Medium | 2 |
| Knowledge Mgmt Expert | For (vault-bridge) | Low | 1 |
| Plugin Architecture Expert | For (vault-bridge) | High | 3 |
| Obsidian Ecosystem Expert | For (vault-courier) | Low | 1 |

For: 7 points vs Against: 2 points → Rename approved.
vault-bridge: 6 points vs vault-courier: 1 point → "vault-bridge" selected.

**Result**: Consensus via weighted vote. Rename vault-reader → vault-bridge. Redefined MECE boundary table documented in SUMMARY.md.
