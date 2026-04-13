---
topic: 1
title: OVM MOC Automation vs graphify Automation — Essential Difference
rounds: 1
result: consensus
---

# TOPIC 1: OVM MOC vs graphify — Essential Difference

**[Optimistic Practitioner]**: Both systems are LLM-automated. OVM: note creation → LLM domain inference → MOC file creation/link. graphify: file scan → LLM concept extraction → graph nodes/edges. Output format differs (markdown vs JSON), but both are "LLM auto-organizes knowledge."

**[Critical Practitioner]**: "Essentially the same" is overstatement. Key differences: (1) Timing: OVM is real-time incremental, graphify is batch. (2) Classification basis: OVM uses keyword-table rule inference, graphify uses Leiden edge-density clustering. (3) Relation type: OVM expresses "belongs-to" only, graphify expresses typed edges (related-to, calls, imports, semantically-similar). (4) Granularity: OVM = note-level, graphify = concept-level. (5) Stability: OVM classification is deterministic once set, graphify clusters may shift on re-run. Most important: relation type difference is a modeling capability gap, not just format.

**[Knowledge Management Expert]**: Three layers of knowledge organization: (1) Classification — OVM automates this, (2) Association — graphify is stronger here, (3) Synthesis — neither does well. OVM MOC is strong at Layer 1, graphify at Layer 2. Relationship is "complement," not "replace."

**[LLM Engineering Expert]**: OVM domain inference is near rule-based (keyword table + LLM judgment). graphify reads entire content and extracts concepts. Same LLM, different extraction depth. OVM decides "where to put," graphify decides "what's inside and what connects."

**[Obsidian Ecosystem Expert]**: Obsidian Graph View already visualizes wikilink-based graphs. OVM auto-generated MOC links feed this natively. graphify's graph.html is a completely separate visualization. User would need to look at two different graphs.

**Result**: Consensus. OVM MOC and graphify automate different layers (Classification vs Association). Complementary, not competing.
