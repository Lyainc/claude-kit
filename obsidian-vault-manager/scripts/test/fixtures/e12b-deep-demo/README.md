# E12b `--deep` demo fixtures (#336)

Four `wiki/` pages, two pairs, used to demonstrate that `audit/SKILL.md` Phase 2.5
DEEP catches a real cross-page contradiction and does not flag a topically-related
but non-contradictory pair. This is **not** a `--dod`-gated fixture — E12b has no
`audit-validate.py` function to seed/measure (see `vault-audit-rules.md`'s E12b
section for why) — it is a manual walkthrough of the skill-only `--deep` LLM path.

## Pairs

- **Contradiction pair**: `db-connection-pool.md` vs `db-config-notes.md`.
  Both tagged `[db, config]` (candidate-pair prefilter hit via shared tags) and
  both make a claim about the exact same subject — DB connection pool max size —
  with mutually exclusive numbers (20 vs 50).
- **Non-contradiction pair**: `auth-flow.md` vs `session-timeout.md`.
  Both tagged `[auth, security]` (candidate-pair prefilter also hits — this pair
  is deliberately topically overlapping, not excluded by the prefilter) but the
  claims are about different subjects (login flow vs. session timeout duration),
  so nothing conflicts. This pair is the false-positive check: a naive "same
  tags → contradiction" heuristic would wrongly flag it; the LLM judgment step
  must not.

## Walkthrough performed (2026-07-10, against SKILL.md Phase 2.5 as written in this PR)

1. **Candidate-pair prefilter** (deterministic, shared-tag/wikilink check):
   - `db-connection-pool.md` ↔ `db-config-notes.md` → shared tags `{db, config}` → candidate.
   - `auth-flow.md` ↔ `session-timeout.md` → shared tags `{auth, security}` → candidate.
   - All 4 cross pairs between the two groups → no shared tags, no wikilinks → not candidates.
   - Result: 2 of the possible 6 pairs reach the LLM judgment step.

2. **LLM judgment** (Read both bodies, judge same-subject conflict):
   - `db-connection-pool.md` ("최대 크기는 20") vs `db-config-notes.md` ("최대 크기는 50") →
     same subject (DB connection pool max size), mutually exclusive claims → **CONTRADICTION**.
   - `auth-flow.md` (OAuth2 login flow) vs `session-timeout.md` (30-minute session
     timeout) → different subjects, no overlapping claim → **not a contradiction**,
     despite sharing both tags.

3. **FP-mitigation confirm gate**: only the db pair is staged as a DEEP candidate
   and offered to the user via `AskUserQuestion`. The auth pair never reaches the
   gate at all (Step 2 correctly declined to flag it) — confirmed "실제 상충" by
   the user for the db pair.

4. **Finding emitted**:
   ```json
   {"error_type": "wiki_contradiction", "severity": "Warning", "priority": "P1",
    "path": "wiki/db-connection-pool.md ↔ wiki/db-config-notes.md",
    "detail": "커넥션 풀 최대 크기: 20 (db-connection-pool.md) vs 50 (db-config-notes.md) — 같은 설정값에 대해 상충하는 숫자를 주장",
    "auto_fix_eligible": false}
   ```
   No finding for the auth pair.

**Outcome**: `--deep` catches the intentional contradiction and does not flag the
non-contradictory (but topically overlapping) pair — the acceptance criterion for #336.

## Reproducing live

Point a vault root at this directory's `wiki/` (e.g. `VAULT_BRIDGE_VAULT_ROOT` set
to this fixture dir) and run `/audit --deep` in a session with the
`obsidian-vault-manager` plugin installed. Phase 2.5 DEEP re-derives the same two
candidate pairs from `frontmatter_records`/`inbound_links` and performs the same
judgment live.
