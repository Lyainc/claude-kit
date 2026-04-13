---
topic: 3
title: Always-On graphify in Vault — Feasibility
rounds: 1
result: consensus
---

# TOPIC 3: Always-On graphify Feasibility

**[Optimistic Practitioner]**: graphify --update processes only changed files (SHA256 cache). Daily 5 notes = 5 extractions only, not full vault re-scan. Not as expensive as feared. Could trigger after OVM skill execution rather than --watch mode.

**[Critical Practitioner]**: Per-note graphify adds 10-30s latency + API cost to each skill invocation. Current /note takes 2-3s. Proposed: 2-3s + 10-30s + cost. UX degradation significant. graphify value comes from multi-note batch analysis, not single-note incremental updates.

**[LLM Engineering Expert]**: Realistic alternatives: (A) Session-end async — /wrapup triggers graphify --update in background, graph ready for next session. (B) Manual trigger — /vault-lint --deep includes graphify update. (C) Threshold-based — suggest graphify when Inbox reaches N items. Option A most natural, aligns with existing session lifecycle.

**[Obsidian Ecosystem Expert]**: If graphify-out/ lives inside vault, Obsidian indexes graph.json/html. Need .obsidianignore or place graphify-out/ outside vault root. Minor but easy to miss.

**Result**: Consensus. Always-on impractical. Session-end async update (wrapup integration) is the realistic model.
