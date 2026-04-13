---
date: 2026-04-11
name: MOC vs graphify Graph — Automated Knowledge Structure
participants:
  fixed: [Moderator, Optimistic Practitioner, Critical Practitioner]
  experts: [Knowledge Management Expert, LLM Engineering Expert, Obsidian Ecosystem Expert]
topics: 4
consensus: 4
held: 0
---

# SUMMARY — MOC vs graphify (2026-04-11)

## Key Premise Correction

Previous analysis assumed MOC is "user-curated." In reality, OVM auto-generates MOCs (domain inference, MOC creation, backlink addition, Home.md update). Both OVM MOC and graphify are LLM-automated systems — the question is which automation layer is more effective, not "manual vs automated."

## Consensus Items

### 1. OVM MOC and graphify Automate Different Layers

| | OVM MOC | graphify |
|---|---|---|
| Automation layer | Classification (belongs-to) | Association (related-to, typed edges) |
| Granularity | Note-level | Concept-level (N concepts per note) |
| Relation types | Single (domain membership) | Multiple (imports, calls, semantically_similar) |
| Obsidian integration | Native (wikilinks) | External (graph.json/html) |
| Stability | Deterministic (once classified, stable) | Variable (re-clustering may shift communities) |

Relationship: **Complementary, not competing.** graphify discovers Layer 2 (association) that OVM's Layer 1 (classification) cannot express.

### 2. graph.json Cannot Directly Replace MOC

- graphify's `--obsidian` export format differs from OVM MOC format
- Re-running graphify may overwrite user-added MOC content
- Obsidian's native Graph View depends on wikilinks, not graph.json

**Instead**: graphify analyzes, OVM materializes in MOC format. graphify = analysis engine, OVM = execution engine.

### 3. Always-On graphify Is Impractical

- Every .md change triggers Claude API call (vault is markdown-only)
- Per-note graphify adds 10-30s latency + API cost to each skill invocation
- Value of graphify emerges from multi-note batch analysis, not single-note incremental

**Realistic model**: Async update at session end (wrapup integration), not real-time watch.

### 4. Optimal Combination Architecture — APPROVED

```
[Daily]     OVM skills (unchanged, graphify-unaware)
[Session]   /wrapup → graphify --update (optional, background)
[Periodic]  /vault-lint → reads graph.json if present
                        → reports "N missing MOC connections found"
                        → user confirms → OVM adds MOC links
[On demand] /ingest → reads graph.json if present
                    → enriches "related existing notes" with graph data
```

Design principles:
1. graphify is **optional dependency** — OVM works 100% without it
2. Integration points limited to **vault-lint + ingest only** — other skills unaffected
3. graphify updates are **async (post-session)** — no real-time cost
4. Missing graph.json → section **auto-skipped** — graceful degradation

## Action Items

| Priority | Item | Scope |
|----------|------|-------|
| P1 | Design vault-lint with optional graph.json reference | vault-lint skill spec |
| P2 | Design ingest with optional graph.json reference | ingest skill spec |
| P3 | Add graphify --update trigger to wrapup (optional, background) | wrapup skill extension |
| P3 | Document graphify integration in CLAUDE.md | CLAUDE.md |

## Minority Dissent

None — all 4 topics reached full consensus.

## Superseded Decisions

This discussion refines the 20260411_mece-validation SUMMARY:
- vault-lint P1 scope now includes optional graphify integration
- ingest P2 scope now includes optional graph.json reference
- wrapup P3 scope now includes optional graphify --update trigger
