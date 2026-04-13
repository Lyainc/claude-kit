---
topic: 2
title: Can graph.json Replace MOC in Obsidian Context?
rounds: 1
result: consensus
---

# TOPIC 2: graph.json Replacing MOC

**[Optimistic Practitioner]**: Reframe as "graphify generates MOC" not "graph.json replaces MOC." graphify --obsidian export produces wikilinked markdown. If it generates MOC-format files in 10_MOC/, graph.json becomes internal intermediate, final output is Obsidian-native markdown MOC.

**[Critical Practitioner]**: graphify --obsidian export generates community-level documents, not domain MOCs. Cluster names may not match domain names. Cluster structure may shift on re-run. Re-generation would overwrite any user additions to MOC files. Biggest risk: every graphify re-run potentially regenerates entire MOC structure.

**[Knowledge Management Expert]**: Two types of MOC content: (a) auto-generated links (safe to regenerate), (b) user-added context notes (destroyed by regeneration). User confirmed relying on OVM auto-generation — implies (b) is minimal. Under this premise, regeneration is safer.

**[LLM Engineering Expert]**: Alternative approach: OVM reads graph.json as reference during MOC generation. graphify = analysis engine, OVM = execution engine. MOC format stays OVM-controlled, graphify enriches the judgment. No format conflict, no overwrite risk.

**[Obsidian Ecosystem Expert]**: graphify --obsidian format differs from OVM MOC format. Conversion layer needed for direct replacement. OVM-controlled MOC generation with graph.json reference avoids this entirely.

**Result**: Consensus. Direct replacement inappropriate. graphify analyzes, OVM materializes in MOC format. Separation of analysis engine and execution engine.
