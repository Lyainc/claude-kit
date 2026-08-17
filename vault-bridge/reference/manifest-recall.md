# vault-searcher — manifest recall truncation (#523)

Why `vault-searcher`'s Mode 2 (Domain Context) and Mode 3 (Keyword Search) run a
candidate-prefilter script instead of `Read`-ing `.vault-bridge/manifest.json` directly.

## The defect

A full-file `Read` overflows the Read tool's default 2,000-line cap on any real vault —
measured 2026-08-03 on `~/vault`: 180 entries, manifest 3,338 lines (~18.6 lines/entry).
`generate-manifest.py`'s `generate()` sorts entries with `sorted(md_files.items())` —
alphabetical by `rel_path`. `wiki/` sorts after `.legacy/`, `inbox/`, and `notes/`, so it
always lands in the last block. At 180 entries, the 2,000-line cut falls inside that
block: **39/39 wiki/ entries (100%)** were truncated away, silently.

This inverts the agent's own contract — `wiki/` entries are documented as "always
included regardless of path-prefix scoping" (#272) because the A-layer wiki is the
primary recall target, but a raw `Read` drops the entire layer before that logic ever
runs. A keyword that only matched a wiki page could never surface it; a domain search
would never propose one.

## The fix

`manifest-domain-candidates.py` / `manifest-keyword-candidates.py` read the manifest
file directly off disk — untruncated — and apply the candidate filter (type/tags/path/
status for domain; title/summary substring for keyword) *before* anything crosses into
the calling agent's context. Each prints one JSON line:
`{"candidate_count": N, "candidates": [...]}`.

## `status == active` is unconditional, on purpose (for now)

Mode 2's `status == active` match arm fires regardless of `domain`/`vault_path` — this
is a literal carry-over of the pre-#523 prose ("any combination of: type, tags,
workstream, path prefix, or status"), not a new behavior this fix introduced. On a
vault with several concurrent active projects it means an unrelated active note can
surface as a domain-context candidate. Not addressed here because #523's scope is the
truncation defect, not a redesign of the match semantics — tracked as a follow-up
if it proves noisy in practice.

## The truncation-check invariant

**Canonical text.** `vault-searcher.md` (Mode 2 step 2b, Mode 3 step 1) points here; this
section is the binding contract, and the agent must apply it as written. Its whole text —
heading to the next heading, so nothing unpinned may be parked at the bottom — is pinned
VERBATIM by `_REF_TRUNCATION_SECTION` in
`vault-bridge/scripts/test/test-manifest-candidates.py`. Editing anything below is a deliberate
contract change and updates that constant in the same commit; a reflow is free (the comparison
is whitespace-normalised).

Even with the prefilter running out-of-context, a caller must never trust a candidate
list it cannot verify is complete: if the printed JSON fails to parse, or
`len(candidates) != candidate_count`, something still went wrong between the script and
the caller (a size limit on the Bash tool's own stdout capture, a truncated pipe, an
unexpected editor injection) — don't trust a partial set.

On any of those, log "manifest 후보 목록이 잘렸을 수 있어 전체 스캔으로 대체합니다." and fall
through to the standard full-scan path rather than silently searching a partial candidate
set. The same fallback applies when `python3` or the script is unavailable, or the script
exits 3 (manifest absent/unparseable) — which is distinct from a legitimately empty vault
(`candidate_count: 0`, exit 0), where there is nothing to fall back for.

## Candidate ranking order (Mode 2 step 2c)

**Canonical text.** `vault-searcher.md` Mode 2 step 2c points here; this section is the
binding sort contract. Its whole text — heading to the next heading (here, end of file), so
nothing unpinned may be parked at the bottom — is pinned VERBATIM by `_REF_RANKING_SECTION` in
`vault-bridge/scripts/test/test-manifest-candidates.py`. Editing anything below is a deliberate
contract change and updates that constant in the same commit; a reflow is free (the comparison
is whitespace-normalised).

Sort the returned candidates:

1. `status=active` first.
2. Then by the Question-Type Routing tier (`vault-searcher.md` § Question-Type Routing) —
   wiki candidates surface before notes/sources for a 정의/사실 질문, and vice versa for a
   경위/이력 질문; `type: discussion` counts as notes/sources-tier; no reordering for 분류 불가.
3. Then by the recall-weight signals already in the manifest entry: `recent_commits`
   descending — the count of git commits touching the file in the **last 7 days**, i.e.
   recent activity, not all-time work. It measures *writing*, never reads, and a vault left
   uncommitted for a week scores 0 everywhere — silent, not meaningful, so never read a 0 as
   "this page is cold".
4. Then `references_in` descending (cross-note wikilink weight).
5. Then `type: wiki` preferred — the A layer is the primary recall target, so a wiki page
   wins a tie over an equally-scored note. A *tiebreaker only*, never an override that
   buries a more relevant non-wiki hit.
6. Finally `mtime` descending as the last tiebreaker.

These signals are free: `generate-manifest.py`'s `_enrich` already populates them.

Then select the top ≤ 5 candidates by this priority.
