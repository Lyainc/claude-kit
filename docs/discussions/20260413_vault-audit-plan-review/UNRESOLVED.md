# Unresolved — Plan Review

All topics reached consensus. Outstanding items inherited from 1st panel remain open and are tracked there:

1. Embedding model selection (local vs API) — decide during Phase B implementation
2. Wikilink bulk rename safety — Phase B v1 ships detection only; execution (`--rename`) requires separate design review
3. Folder-level flag scope — projects-only for v1; expand after real-usage observation

New items deferred to implementation:

4. **Git detection heuristic** — whether `.git` alone is sufficient or also check `git rev-parse` succeeds. Decide in Phase B coding.
5. **AskUserQuestion response serialization** — how to represent multiSelect + free-text fallback within a single question. Revisit in Phase A prototype.
