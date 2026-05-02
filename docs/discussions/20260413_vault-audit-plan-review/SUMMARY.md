# Vault Audit Plan Review — 2nd Expert Panel

- Date: 2026-04-13
- Target: `/Users/Lyainc/.claude/plans/sunny-tumbling-dream.md`
- Panel: Architecture, Data Integrity, UX, Security, DevEx, Performance
- Topics: 5 (all consensus)

## Consensus Amendments to Plan

| Topic | Amendment |
|-------|-----------|
| A. Blind spots | Single `scripts/ovm-primitives.sh` with subcommand dispatch; sidecar → `~/vault/.ovm/audit-state.json` (avoid Obsidian-managed `.obsidian/`); Python stdlib only; add `scripts/test/gen-fixture.sh` (300-note synthetic vault); path-traversal guards |
| B. Phase scope | Phase 0 MVP = only what Phase A needs (frontmatter/filename/wikilink parsers + audit-state CRUD + metrics). Orphan/MOC/community moved to Phase B. Phase A on `feature/inbox-review-pipeline` branch with 5-case dogfood before merge. Phase A→B handoff checklist (JSON schema / AskUserQuestion pattern / output format / mark-clean callsites) |
| C. UX | AskUserQuestion ≤ 3 per session (Q1 bulk, Q2 ambiguous top-N, Q3 apply-confirmation). Progress format `[스캔 N/Total \| 이슈 K건]` with Total never changing. Start-of-session summary shows flag stats. `--reset-flags` requires confirmation |
| D. Security / integrity | Dry-run default, `--apply` required. Git-vault auto-detect → single commit; non-git → `.ovm/backups/SESSION/`. Sidecar `.bak` rotation, parse-failure graceful fallback, `--reset-state`. Phase B v1 = rename detection only; execution split to `--rename` after review |
| E. Success criteria | Measure baseline BEFORE Phase A (`scripts/test/baseline-measure.sh` → `docs/baseline.md`). Phase A exit: 5 input grammars equivalent + token ≥ 3x reduction + ≤ 5 interactions + 4/5 dogfood positive. Phase B exit: detection ≥ 93% on fixture + FP < 10% + rescan ≥ 50% saving + dry-run→apply integrity + rollback verified on both git/non-git |

## Key CLI Option Set

```
/vault-audit                    # dry-run, flag-aware
/vault-audit --apply
/vault-audit --force
/vault-audit --path <subdir>
/vault-audit --reset-flags [path]
/vault-audit --reset-state
/vault-audit --use-graphify
/vault-audit status <path>
```

## Branch Strategy

```
main
 └── feature/ovm-primitives         # Phase 0
       └── feature/inbox-review-pipeline  # Phase A
             └── feature/vault-audit      # Phase B
```

## Outstanding from 1st Panel (still open)

1. Embedding model (local vs API) — benchmark during Phase B
2. Wikilink bulk rename safety — defer to `--rename` sub-feature
3. Folder flag scope — projects-only for v1

───
*5 topics · 5 consensus · plan doc updated to v2*
