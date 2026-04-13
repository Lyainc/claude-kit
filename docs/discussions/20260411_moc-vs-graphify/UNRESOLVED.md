---
date: 2026-04-11
discussion: MOC vs graphify Graph
---

# UNRESOLVED — MOC vs graphify (2026-04-11)

No unresolved issues. All 4 topics reached consensus.

## Deferred Items (Future Scope)

| Item | Condition for Revisit |
|------|----------------------|
| graphify --obsidian export → OVM MOC format converter | If users request automated MOC regeneration from graph data |
| graphify MCP server as OVM backend | If graph.json file-based integration proves insufficient for query-heavy workflows |
| vault-lint + graphify confidence threshold tuning | After initial implementation, tune INFERRED edge confidence cutoff (currently proposed: 0.7) |
| graphify cost benchmarking on real vault | Measure actual API cost of --update on vault with 200+ notes to validate async model |

## Open Questions Noted During Discussion

1. Does the user ever manually edit MOC files, or is it 100% OVM-generated? (Assumed 100% auto-generated based on user statement)
2. What is the practical latency of `graphify --update` on a vault of 200+ markdown files with 3-5 changed files? (Unknown, needs benchmarking)
3. Should graphify-out/ live inside ~/vault/ or alongside it? (Inside risks Obsidian index pollution; outside risks path confusion)
