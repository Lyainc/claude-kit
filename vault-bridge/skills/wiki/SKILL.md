---
name: wiki
description: "Compile domain knowledge learned during work into a ~/vault/wiki/ page (the LLM wiki, A layer for AI recall). Gated, explicit compile — never always-on. Examples: '/wiki Defuddle CLI extracts the first H1 as the title', '이거 위키에 정리해줘', '방금 알아낸 거 wiki로 저장'. KR triggers: 'wiki에 정리', '위키 페이지로', '알아낸 거 저장', '도메인 지식 컴파일'. EN triggers: 'compile to wiki', 'save to wiki', 'add wiki page'."
allowed-tools: Read Write Bash AskUserQuestion
effort: medium
---

**User language: Korean.** All user-facing output (responses, AskUserQuestion prompts, generated content, file contents) MUST be in Korean.

Compile the domain knowledge in `$ARGUMENTS` into a page under `~/vault/wiki/` — the **A layer** of vault second-brain v5 (`docs/design/vault-second-brain-v5.md`). The wiki is plain-markdown knowledge written *for the model to read on the human's behalf* — the write target is the model, not a browsing UI, but humans remain a secondary consumer of the same pages (v5 §3); to browse them directly, use OVM `/base` rather than this skill. This skill is the **query-driven compounding** entry point: what you learned while working becomes a recall-able wiki page with near-zero friction.

**This is a gated, explicit compile action — never always-on.** The gate is the explicit invocation itself (v4 §9.1 "no always-on push" is preserved). Run inline in the main context — do NOT fork to a subagent (vault writes from subagents are blocked by the Write Role Contract; `pre-write-guard.sh` denies them).

When formatting body or frontmatter, follow `../../reference/obsidian-format.md` for Obsidian-native wikilinks, callouts, comments, and YAML properties. Prefer wikilinks for internal vault references.

---

## Pipeline

```
SYNTHESIZE → U7 ROUTE → DEDUP → PLAN → WRITE
```

Do not collapse phases. The U7 route and dedup checks run BEFORE any write.

---

## Phase 1 — SYNTHESIZE

Turn `$ARGUMENTS` (and the relevant exploration context from the current session) into a self-contained piece of **domain knowledge** — a fact/model/lesson that is true and reusable, written so a future model can act on it without re-deriving. Not a transcript dump, not a question; a compiled answer.

If `$ARGUMENTS` is empty or only a question (no knowledge to compile), use AskUserQuestion to ask what they learned that's worth saving — do not invent content.

---

## Phase 2 — U7 ROUTE (2-step decision tree, v5 §10)

Before writing, apply the two-step routing test (v5 §10) — a decision-check first, the domain-knowledge check second. This reflects the 3-way destination set v5 §3 declares (GitHub issue / wiki A / AGENTS.md), not a 2-way split.

**Step 1 — is this a repo-bound decision (needs a GitHub-issue trail)?**

- **Yes** — a design/architecture decision scoped to *this* repo. → **do NOT write a wiki page.** Redirect (emission only, no write): tell the user in Korean that repo-bound decisions go to a GitHub issue, not the wiki — e.g. "이건 이 레포의 설계 결정이라 wiki가 아니라 GitHub 이슈로 남기는 게 맞아요. 이슈로 만들까요?" Stop here for this fragment — do not proceed to Step 2.
- **No** — not a decision (a fact, a lesson, a reusable model, or this-repo structure knowledge). → proceed to Step 2.

**Step 2 — is this true / useful in OTHER repos too?**

- **Yes** — repo-transcending *domain knowledge* (e.g. "Defuddle extracts the first H1 as the title", "Obsidian Bases `.base` files are YAML view definitions"). → proceed to DEDUP and write a wiki page.
- **No** — *this repo's structure* (where things live, this project's wiring). → **do NOT write a wiki page.** Redirect (emission only, no write): tell the user in Korean that this belongs in the repo's `AGENTS.md` / deepinit, not the cross-repo wiki — e.g. "이건 이 레포 구조라 wiki(레포 초월 도메인 지식)가 아니라 AGENTS.md/deepinit에 넣는 게 맞아요. 거기 추가할까요?" The skill never writes outside the vault.

**Mixed** — split per fragment (one wiki page = one kind of knowledge, one GitHub issue = one decision). Apply the two-step tree independently to each fragment: write cross-repo domain-knowledge fragments to wiki; redirect repo-structure fragments to AGENTS.md; redirect decision fragments to a GitHub issue. The skill only ever writes inside the wiki — issue creation and AGENTS.md edits are both emission-only guidance for the user to act on.

State the routing decision briefly before continuing, so the user can correct it.

---

## Phase 3 — DEDUP (compounding, not duplication)

The wiki *compounds* — a topic that already has a page is **updated**, never duplicated.

0. **Vault-absent guard (#645 B1) — runs BEFORE the manifest read, and the order matters.**
   Resolve the vault root the same way `hooks/pre-write-guard.sh` does — `VAULT_BRIDGE_VAULT_ROOT`
   (env override) > `VAULT_BRIDGE_VAULT_PATH` (userConfig) > `~/vault` — then test it:
   ```bash
   _vr="${VAULT_BRIDGE_VAULT_ROOT:-${VAULT_BRIDGE_VAULT_PATH:-}}"
   [ -z "$_vr" ] && _vr="$HOME/vault"
   VAULT_ROOT="${_vr/#\~/$HOME}"
   if [ -d "$VAULT_ROOT" ]; then echo "$VAULT_ROOT"; else echo "VAULT_ABSENT"; fi
   ```
   **Each Bash tool call is its own shell — `$VAULT_ROOT` does not survive to the next one.** The
   printed line is the resolved vault root (or the literal string `VAULT_ABSENT`); read it and
   substitute that value for every `$VAULT_ROOT` in the bash fences below, in this same run (the
   `manifest-wiki-match.py` call, the `ls` fallback, and Phase 5's `mkdir`/page path) — same
   substitution contract `vault-link/SKILL.md` Step 2 uses for the same reason.

   `VAULT_ABSENT` → **stop without writing anything.** Tell the user in Korean that no vault was
   found and where to configure one — e.g. "볼트가 없어서 wiki 컴파일을 멈췄어요. 볼트 경로를
   `VAULT_BRIDGE_VAULT_ROOT`(환경변수)나 플러그인 설정 `VAULT_BRIDGE_VAULT_PATH`로 지정해 주세요."
   **Never `mkdir` the vault root**, here or in Phase 5.

   This keeps the contract the rest of vault-bridge already holds — `pre-write-guard.sh:52-54` and
   `session-start-manifest.sh` both do nothing when the vault directory is missing. Creating it
   would leave a vault nobody knows about, and since `session-start-manifest.sh` already exited for
   this session, that vault never receives a manifest: step 1 below would then take the exit-3
   branch on **every** later run, making DEDUP permanently blind.

   **Why before the manifest read**: a missing vault guarantees a missing manifest, so running
   step 1 first would report "manifest unusable" for what is really "no vault at all" and send the
   user to fix the wrong thing. One cause, one message, in cause order.

1. Find existing pages on the same topic. **Primary: the manifest** — when it exists and is reasonably fresh, match `type:wiki` entries on title + tags (catches same-topic pages on a different slug, e.g. `defuddle.md` vs `defuddle-cli.md`, which slug-only matching misses). **Never `cat` the manifest directly** — on a real vault it can run past 100 KB, and the harness truncates large Bash output to a 2 KB preview before this reads it, so a raw `cat` silently degrades to whichever few entries survive the cut (#468, same defect class as #460). Use the filter script instead, which reads the full file on disk and returns only `type:wiki` entries (`path`/`title`/`tags`):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manifest-wiki-match.py" ~/vault/.vault-bridge/manifest.json
   ```
   Exit 0 → parse stdout as `{scanned, wiki_entries[]}` and match `wiki_entries` on title + tags.
   Exit 3 (manifest absent, unparseable, or malformed) → same as a hard-absent manifest, fall
   through to the slug/filename fallback below — never re-attempt with a raw `cat`.

   **Exit 3 also emits one warning line to the user (#645 B2)** — in Korean, before continuing:
   e.g. "manifest를 못 읽어서(`$VAULT_ROOT/.vault-bridge/manifest.json`) 슬러그 이름 매칭으로만
   중복을 확인해요. 같은 주제가 다른 슬러그로 있으면 못 잡을 수 있어요. `/vault-manifest-refresh`로
   다시 만들 수 있어요." Then proceed with the fallback — this warns, it does not abort.

   The warning is the whole point of the branch being visible: on the fallback path DEDUP silently
   loses same-topic-different-slug matching, so `/wiki` keeps *succeeding* while quietly writing
   duplicates. Without the line, the only way to notice is an `/audit` E12 run days later.

   **Fallback (manifest absent or exit 3 above):** list pages and match by slug / filename:
   ```bash
   ls ~/vault/wiki/ 2>/dev/null
   ```
2. **Existing page on the same topic** → Read that page first, then plan an **update/merge**: integrate the new knowledge into what is already there (add/refine sections, keep it coherent) and extend the `provenance:` trail with the new originating query. Do NOT create a `-v2`.
   - **Lazy anchor check (#305 staleness defense)**: if the existing page has an `anchor:` field, and that anchor is a local path, `stat` it and compare its mtime against the page's `verified:` date. Anchor unchanged since `verified:` → the anchored claim is still current, skip re-deriving it (just fold in the new knowledge and bump `verified:` at write time). Anchor changed → recompile the anchored claim from the current session context, same as any other update. If the anchor is a URL instead of a local path, skip the mtime comparison entirely and always recompile as a normal update — checking a URL for changes means fetching it, and that fetch is exactly the ferry-style re-pull this design avoids (§3 pull-mostly). This is a lazy check on an already-local anchor, never a network round-trip. **Known gap**: `verified:` is date-only (`YYYY-MM-DD`) while mtime is a full timestamp, so an anchor edited later on the *same calendar day* as the last `verified:` stamp can still compare as "unchanged" and skip a re-derive it should have caught — a narrow, same-day race, not a fix.
3. **No existing page** → plan a **new** page `~/vault/wiki/{slug}.md`. `{slug}` = 2–4 kebab-case words from the topic.
4. A `-v2`/`-v3` suffix is ONLY for a genuinely *different* topic that collides on slug — never for the same topic (that's an update).

---

## Phase 4 — PLAN

Show the user, before writing:
- Target path (and whether it's a **new** page or an **update** to an existing one).
- Frontmatter.
- The compiled body (or, for an update, the merge result / the sections being added).

Then write after confirmation. (The compounding KB rewards one human glance — U3 contamination compounds, so the confirmation is the cheap defense, not friction for its own sake.)

**Frontmatter** (wiki page):
```yaml
---
created: YYYY-MM-DD
tags: [{domain}]              # at least one domain tag; no `wiki` literal needed, type carries it
type: wiki
anchor: <local path/URL>      # optional — only when this page's dominant claim traces to one checkable source; omit for source-free pages
verified: YYYY-MM-DD          # always written, auto-stamped to today on every write (new or update)
provenance: <one line: the query / exploration that produced this page; multiple updates joined with `; `>
---
```

- **No `status:` field.** The status machine (raw→draft→evergreen) is the B layer's (human review). A is outside it (v5 §4.1) — wiki pages are AI-authored, provenance-tracked, not review-status pages.
- **`provenance:` is required and always written** — it records *which exploration produced this page* (U3 traceability: a bad synthesis can be traced back to its source). For an update, append the new originating query to the existing provenance with the `; ` delimiter (`provenance: query-A; query-B`) rather than overwriting it — keep the canonical single-line, `; `-joined format so it stays consistent across update cycles.
- **`anchor:`/`verified:` (#305 staleness defense)** — classification unit is the page (dominant-type, not per-claim): a page with one checkable source anchor (a local file this vault/session can `stat`) gets `anchor:` set; a page synthesized from judgment/discussion with no single checkable source stays anchor-free. `verified:` is written on every compile (new page or update), unconditionally — it is a last-touched timestamp, not an active verification act, so neither a human nor the model is ever asked to "re-verify" a page on a schedule.

---

## Phase 5 — WRITE

1. `mkdir -p "$VAULT_ROOT/wiki"` — the `wiki/` sub-directory only, and only because Phase 3 step 0
   already proved `$VAULT_ROOT` itself exists. **Never `mkdir` the vault root** (#645 B1): if
   Phase 3 step 0 was skipped or reported `VAULT_ABSENT`, this skill has already stopped.
2. **New page**: write `~/vault/wiki/{slug}.md` with the frontmatter above and the compiled body. Stamp `verified:` to today.
3. **Update**: rewrite the existing page with merged content and the extended `provenance:`. Preserve the original `created:` date; do not reset it. Stamp `verified:` to today regardless of whether the anchor check (Phase 3) found the anchor changed or unchanged — the page was touched, so the freshness signal moves forward either way.
4. Output only the created/updated file path and whether it was new or merged. No follow-up questions.

---

## Rules

- **Gated, explicit, main-context.** Never an always-on hook. Never fork to a subagent — vault writes must originate in the main context (Write Role Contract; `pre-write-guard.sh` blocks subagent writes).
- **U7 route first.** Repo-structure knowledge is redirected to AGENTS.md/deepinit, never written to wiki. The wiki holds only cross-repo domain knowledge.
- **Compound, don't duplicate.** Same topic → update the existing page. `-v2` is only for a slug collision between genuinely different topics.
- **Always write `provenance:`.** Every wiki page carries the exploration that produced it.
- **Always stamp `verified:` to today on write.** No exceptions, no schedule, no "re-verify" step — it is a last-touched signal, not a verification action (#305).
- **No `status:` on wiki pages.** A is outside the status machine.
- **Filename**: `{slug}.md`, lowercase kebab — matches the `wiki/` naming convention enforced by `pre-write-guard.sh`.
- **Vault writes only inside `~/vault/wiki/`.** This skill never touches repo files (AGENTS.md redirect is guidance, not a write).
- AI recall is primary, human reading is secondary (v5 §3 — browse via OVM `/base`, not this skill): write for a future model to act on, plain markdown, no embedding/DB (constitution — file-over-app).
