---
topic: 1
title: New Skills (vault-lint, ingest) MECE with Existing Skills
rounds: 1
result: consensus
---

# TOPIC 1: New Skills MECE Verification

**[Optimistic Practitioner]**:
Current OVM skill map — 8 skills by primary verb: capture(save), note(create), project(create/manage), inbox-review(classify/move), wrapup(summarize), context(query), archive(store), vault-daily(create). New skills: vault-lint(inspect/diagnose) is entirely new verb. ingest(absorb/integrate) has partial overlap with context(query) in "related note search" step, but purpose differs — context is read-only, ingest produces change proposals.

**[Critical Practitioner]**:
ingest and inbox-review share the same input space (Inbox files). User scenario conflict: Web Clipper saves article → user runs inbox-review OR ingest on same file. Which takes priority? Two skills competing for same input creates confusion.

**[Knowledge Management Expert]**:
In PKM, triage and synthesis are fundamentally different cognitive tasks. inbox-review = triage ("where does this go?"). ingest = synthesis ("how does this connect to existing knowledge?"). In Zettelkasten terms, ingest converts Fleeting→Literature, inbox-review places Literature→Permanent location. Natural order: ingest first, inbox-review second.

**[Plugin Architecture Expert]**:
Separate by input type for clean MECE: capture(user text), ingest(external source files), inbox-review(batch file list). Pipeline: capture → ingest → inbox-review. ingest = single source deep analysis, inbox-review = multi-file batch organization.

**[Obsidian Ecosystem Expert]**:
vault-lint should focus on semantic inspection that Obsidian's built-in "Dangling links" cannot do. LLM-only value: detecting "semantic orphans" — notes with links but low actual relevance.

**Result**: Consensus. Both new skills MECE-valid with boundary conditions defined.
