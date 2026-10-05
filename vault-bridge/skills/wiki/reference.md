# wiki — reference detail

Rationale and edge-case detail moved out of `SKILL.md` (Codex truncates an invoked SKILL.md at 8,000 bytes, #750).
Gates, prohibitions, and the output contract stay in `SKILL.md`; this file only refines them.

## Purpose and positioning

The wiki is plain-markdown knowledge written *for the model to read on the human's behalf* — the write target is the model, not a browsing UI, but humans remain a secondary consumer of the same pages (v5 §3); to browse them directly, use OVM `/base` rather than this skill. This skill is the **query-driven compounding** entry point: what you learned while working becomes a recall-able wiki page with near-zero friction.

The gate is the explicit invocation itself (v4 §9.1 "no always-on push" is preserved).

## Phase 2 — U7 route, redirect wording and mixed input

Redirect examples (emission only, no write):

- Repo-bound decision: "이건 이 레포의 설계 결정이라 wiki가 아니라 GitHub 이슈로 남기는 게 맞아요. 이슈로 만들까요?"
- This-repo structure: "이건 이 레포 구조라 wiki(레포 초월 도메인 지식)가 아니라 AGENTS.md/deepinit에 넣는 게 맞아요. 거기 추가할까요?"

Cross-repo domain-knowledge examples: "Defuddle extracts the first H1 as the title", "Obsidian Bases `.base` files are YAML view definitions".

**Mixed** — split per fragment (one wiki page = one kind of knowledge, one GitHub issue = one decision). Apply the two-step tree independently to each fragment: write cross-repo domain-knowledge fragments to wiki; redirect repo-structure fragments to AGENTS.md; redirect decision fragments to a GitHub issue. The skill only ever writes inside the wiki — issue creation and AGENTS.md edits are both emission-only guidance for the user to act on.

## Phase 3 — DEDUP detail

### Step 0 rationale (vault-absent guard, #645 B1)

Each Bash tool call is its own shell — `$VAULT_ROOT` does not survive to the next one. The printed line is the resolved vault root (or the literal string `VAULT_ABSENT`); read it and substitute that value for every `$VAULT_ROOT` in the bash fences, in this same run — same substitution contract `vault-link/SKILL.md` Step 2 uses for the same reason.

This keeps the contract the rest of vault-bridge already holds — `pre-write-guard.sh:52-54` and `session-start-manifest.sh` both do nothing when the vault directory is missing. Creating the root would leave a vault nobody knows about, and since `session-start-manifest.sh` already exited for this session, that vault never receives a manifest: the manifest step would then take the exit-3 branch on **every** later run, making DEDUP permanently blind.

**Why before the manifest read**: a missing vault guarantees a missing manifest, so running the manifest step first would report "manifest unusable" for what is really "no vault at all" and send the user to fix the wrong thing. One cause, one message, in cause order.

### Manifest read rationale (#468, #460)

Never `cat` the manifest: on a real vault it can run past 100 KB, and the harness truncates large Bash output to a 2 KB preview before the model reads it, so a raw `cat` silently degrades to whichever few entries survive the cut. The filter script reads the full file on disk and returns only `type:wiki` entries. Matching on title + tags catches same-topic pages on a different slug (e.g. `defuddle.md` vs `defuddle-cli.md`), which slug-only matching misses.

### Exit-3 warning rationale (#645 B2)

The warning is the whole point of the branch being visible: on the fallback path DEDUP silently loses same-topic-different-slug matching, so `/wiki` keeps *succeeding* while quietly writing duplicates. Without the line, the only way to notice is an `/audit` E12 run days later.

### Lazy anchor check (#305 staleness defense)

If the existing page has an `anchor:` field that is a local path, `stat` it and compare its mtime against the page's `verified:` date. Anchor unchanged since `verified:` → the anchored claim is still current, skip re-deriving it (just fold in the new knowledge and bump `verified:` at write time). Anchor changed → recompile the anchored claim from the current session context, like any other update. If the anchor is a URL, skip the mtime comparison and always recompile as a normal update — checking a URL means fetching it, which is the ferry-style re-pull this design avoids (§3 pull-mostly). This is a lazy check on an already-local anchor, never a network round-trip. **Known gap**: `verified:` is date-only (`YYYY-MM-DD`) while mtime is a full timestamp, so an anchor edited later on the *same calendar day* as the last `verified:` stamp can still compare as "unchanged" — a narrow, same-day race, not a fix.

## Phase 4 — frontmatter field notes

- **No `status:` field.** The status machine (raw→draft→evergreen) is the B layer's (human review). A is outside it (v5 §4.1) — wiki pages are AI-authored, provenance-tracked, not review-status pages.
- **`provenance:`** records *which exploration produced this page* (U3 traceability: a bad synthesis can be traced back to its source). For an update, append the new originating query with the `; ` delimiter (`provenance: query-A; query-B`) rather than overwriting — keep the canonical single-line, `; `-joined format across update cycles.
- **`anchor:`/`verified:` (#305)** — classification unit is the page (dominant-type, not per-claim): a page with one checkable source anchor (a local file this vault/session can `stat`) gets `anchor:` set; a page synthesized from judgment/discussion with no single checkable source stays anchor-free. `verified:` is written on every compile (new page or update), unconditionally — it is a last-touched timestamp, not an active verification act, so neither a human nor the model is ever asked to "re-verify" a page on a schedule.
- The compounding KB rewards one human glance — U3 contamination compounds, so the confirmation is the cheap defense, not friction for its own sake.

## Rules — rationale

- **Vault writes only inside `$VAULT_ROOT/wiki/`**: every executable line (manifest read, `ls` fallback, page path, `mkdir`) uses `$VAULT_ROOT`; hardcoding `~/vault` in any of them makes the guard check one directory while the write lands in another, so with `VAULT_BRIDGE_VAULT_ROOT` set the page is written outside the vault entirely (#613/#616 defect class). The skill never touches repo files (the AGENTS.md redirect is guidance, not a write).
- AI recall is primary, human reading is secondary (v5 §3): write for a future model to act on, plain markdown, no embedding/DB (constitution — file-over-app).
