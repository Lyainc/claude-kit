# Vault Audit Design — Expert Panel Summary

- Date: 2026-04-13
- Panel: PKM Expert, Architecture Expert, Performance Expert, UX Expert, Data Integrity Expert
- Topics: 4 (all reached consensus)

## Consensus Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Flag storage | Sidecar `.obsidian/audit-state.json` | Avoids frontmatter pollution, respects Obsidian conventions, no self-referential hash loop |
| Change detection | mtime-based (`find -newer .audit-state/LAST_SCAN`) | Cheaper than tree-hash; `--force` flag for full rescan when mtime corrupted |
| Frame sharing (inbox-review vs vault-audit) | Share primitives, separate UX | Same time/intent characteristics differ; primitives = `scanner`, `proposer`, `confirmer`, `audit-state` |
| Output consistency | Standardize evidence lines, progress indicator, rationale format | Achieves "same feel" without forcing UX merge |
| graphify dependency | Soft dependency with `--use-graphify` flag | Most vault users do not install graphify; fallback = native wikilink regex parser |
| Token reduction target | Commit 3–5x, aspire 10x | 10x unverified; measurement infra required for validation |
| Implementation order | (0) Primitives + metrics → (A) inbox-review refactor → (B) vault-audit + flag → (C) graphify-vault (backlog) | Phase 0 prevents double rework; (C) downgraded to optional |

## Action Items

1. Design `audit-state` sidecar schema and primitive library (Phase 0)
2. Add token/scan-time measurement hooks to OVM (Phase 0)
3. Refactor inbox-review to SCAN/PROPOSE/CONFIRM using primitives (Phase A)
4. Build vault-audit skill on same primitives with flag system (Phase B)
5. Validate 3–5x token reduction with real vault measurements (during Phase B)
6. graphify-vault wrapper moved to backlog (Phase C, optional)

## Output Format Standard (applies to both skills)

- Evidence line per proposal: `근거: {type}={value}` (e.g., `근거: wikilink-count=2, domain-match=api-gateway`)
- Progress indicator: `[N/Total]`
- Rollback: single commit per session for reversibility
- AskUserQuestion: batch-approval for high-confidence, multi-choice for ambiguous

## Flag System Spec (Phase B)

- Location: `.obsidian/audit-state.json`
- Schema: `{paths: {<relpath>: {last_audited: ISO8601, mtime_at_audit: epoch, status: clean|dirty}}, last_full_scan: ISO8601}`
- Invalidation: current mtime != mtime_at_audit → status auto-dirty
- Folder-level flag: optional `audit_status: clean` in `_index.md` frontmatter (human-readable mirror)
- Override: `--force` ignores all flags

## graphify Integration Rule

- If `graphify-out/graph.json` exists and mtime newer than last vault change → use as orphan/community source
- Otherwise fall back to native `[[wikilink]]` regex parser
- Never require graphify installation

───
*4 topics discussed · 4 consensus reached · 3 unresolved issues filed*
