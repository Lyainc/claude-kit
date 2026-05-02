# Unresolved Issues — Vault Audit Design

## 1. Embedding model choice (local vs API)

- Context: Pass B uses embeddings to narrow LLM candidates for duplicate/similarity detection
- Blocker: local model = zero marginal cost but setup friction; API model = cost per call
- Next step: benchmark both on a sample vault before committing

## 2. Wikilink back-reference update safety at scale

- Context: vault-file-organizer renames must update all `[[oldname]]` occurrences
- Blocker: mass rewrite risk (regex false positives, aliased links `[[target|alias]]`, embeds `![[...]]`, block refs `[[note#^id]]`)
- Next step: separate design review with rollback plan before Phase B ships rename support

## 3. Folder-level flag scope

- Context: should flags apply only to `20_Projects/*/_index.md` or also arbitrary folders?
- Blocker: unclear user workflow; over-generalization risks confusion
- Next step: ship Phase B with projects-only flag, observe usage, expand if requested
