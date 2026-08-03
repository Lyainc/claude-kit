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

Even with the prefilter running out-of-context, a caller must never trust a candidate
list it cannot verify is complete: if the printed JSON fails to parse, or
`len(candidates) != candidate_count`, something still went wrong between the script and
the caller (a size limit on the Bash tool's own stdout capture, a truncated pipe, an
unexpected editor injection) — the agent instructions (`vault-searcher.md` Mode 2 step
2b, Mode 3 step 1) fall through to the standard full-scan path rather than silently
searching a partial candidate set. This is the actual gate; this doc only explains why
it exists.
