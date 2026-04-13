---
topic: 4
title: Draft Folder Addition to Vault Structure
rounds: 1
result: consensus
---

# TOPIC 4: Draft Folder Addition

**[Optimistic Practitioner]**:
Current problem: "work-in-progress documents" have no clear home. Inbox is for unsorted content, not in-progress content. Notes is for finished content. Projects only covers project-scoped docs. Proposed: `05_Draft/` between Inbox and MOC. Maps to Zettelkasten 3-stage lifecycle: Fleeting(Inbox) → Literature(Draft) → Permanent(Notes). Strong synergy with /ingest skill.

**[Critical Practitioner]**:
Concerns: (1) 8th top-level folder increases cognitive load. (2) Inbox vs Draft boundary unclear — "Web Clipper article + my comments" goes where? (3) Existing workflow disruption: capture→Inbox, inbox-review→Notes pipeline needs revision. (4) Numbering convention: 05 sits between 00 and 10, implies processing-stage ordering which may not match the category-based numbering intent.

**[Knowledge Management Expert]**:
Precise Zettelkasten mapping: Fleeting Note (00_Inbox), Literature Note in progress (05_Draft), Permanent Note (30_Notes). Current problem: Literature Notes and Fleeting Notes cohabit in 00_Inbox, making inbox-review judgment difficult. Draft folder resolves this. Movement ownership: Inbox→Draft by /ingest skill, Draft→Notes by user judgment.

**[Plugin Architecture Expert]**:
Impact analysis: vault-knowledge-manager agent (add 05_Draft/ to structure), vault-file-organizer (add Draft paths), vault-bridge/vault-searcher (include Draft in search scope), ingest skill (output to Draft), inbox-review (add Draft movement option), vault-lint (detect stale drafts), context (include Draft with label). Most changes are minor. Best introduced alongside /ingest skill.

**[Obsidian Ecosystem Expert]**:
Draft folders are extremely common in Obsidian community. PARA methodology also recommends Inbox→Processing→Storage stages. Number 05 positions naturally between Inbox(00) and MOC(10) in Obsidian's alphabetical folder sort. Recommendation: require `status: draft` frontmatter for vault-lint stale detection.

**Result**: Consensus. Add 05_Draft/ with defined lifecycle, movement responsibilities, and frontmatter conventions. Stale draft threshold: 14 days.
