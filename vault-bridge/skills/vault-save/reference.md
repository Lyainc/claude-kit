# vault-save — reference detail

Rationale and edge-case detail moved out of `SKILL.md` (Codex truncates an invoked SKILL.md at 8,000 bytes, #750).
Destination rules, approval behavior, and the vault-root guard stay in `SKILL.md`; this file only refines them.

## Destination notes

The split is **authorship, not quality**. Nothing here judges whether the material is good enough to keep; that judgment happens when you go looking for it again.

- Unsure which side? If the text would survive unchanged without you, it is source → `sources/`.
- `--type decision` is KEEP, confirmed (#477 item 2, 2026-08-04) — for non-repo-bound decisions only (e.g. a personal tool choice). A **repo-bound** design decision belongs in a GitHub issue, not here (v5 §10) — say so and stop rather than writing one.
- `--type discussion` is the one case that writes to `wiki/` (#586 c1) — the content is an AI compilation, not raw authorship, so it belongs with the rest of the A-layer even though it reads as history rather than fact (vault-discussion-history-wiring Seed, #586). Filename carries no date prefix — `wiki/`'s naming convention is evergreen kebab slugs, same as any other page there (`pre-write-guard.sh`); the date lives only in `created:`.

## Frontmatter notes

- **`provenance` is required on every file.** There is no gate at the entrance, so being able to trace a file back to its origin is the whole defense at retrieval time (v5 §5, #480). Never write a file without it; if the origin is genuinely just "this conversation", say that.
- **No `status:` field.** The `raw→draft→evergreen→archived` machine and the promotion gate are abolished (v5 §5/§6, #480). Do not write `status:` and do not offer to promote anything.
- `type: discussion` keeps rejected alternatives and the assumptions behind them in the body, not just the conclusion — a one-line verdict doesn't answer "was this still valid" or "what didn't we know yet" later (#586 c4/c5). Link related `wiki/` pages with `[[wikilinks]]` in the body rather than a dedicated frontmatter field.

## Procedure step 3 — vault-absent guard rationale (#697)

This is the same contract the rest of vault-bridge already keeps — `hooks/pre-write-guard.sh` and `hooks/session-start-manifest.sh` both treat a missing vault directory as "do nothing". Creating the root here would produce a vault nobody knows about, and because `session-start-manifest.sh` already exited for this session, that vault never receives a manifest — every later manifest-dependent path (recall, dedup) then degrades silently.

## Rules — rationale

- **Save immediately, without confirmation.** Friction at the entrance is what killed the previous two entries (#477).
- Never write to `{vault_root}/wiki/` except for `--type discussion` — every other type stays out of `/wiki`'s A layer (sibling skill in this plugin, #645).
